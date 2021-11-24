"""
    sphinxcontrib.openapi.openapi30
    -------------------------------

    The OpenAPI 3.0.0 spec renderer. Based on ``sphinxcontrib-httpdomain``.

    :copyright: (c) 2016, Ihor Kalnytskyi.
    :license: BSD, see LICENSE for details.
"""

import copy

import collections
import collections.abc
import textwrap

from datetime import datetime
import itertools
import json
import re
from urllib import parse
from http.client import responses as http_status_codes
from sphinxcontrib.openapi.renderers._model import _process_one, _entities

from sphinx.util import logging

from sphinxcontrib.openapi import utils


LOG = logging.getLogger(__name__)

# https://github.com/OAI/OpenAPI-Specification/blob/3.0.2/versions/3.0.0.md#data-types
_TYPE_MAPPING = {
    ('integer', 'int32'): 1,  # integer
    ('integer', 'int64'): 1,  # long
    ('number', 'float'): 1.0,  # float
    ('number', 'double'): 1.0,  # double
    ('boolean', None): True,  # boolean
    ('string', None): 'string',  # string
    ('string', 'byte'): 'c3RyaW5n',  # b'string' encoded in base64,  # byte
    ('string', 'binary'): '01010101',  # binary
    ('string', 'date'): datetime.now().date().isoformat(),  # date
    ('string', 'date-time'): datetime.now().isoformat(),  # dateTime
    ('string', 'password'): '********',  # password

    # custom extensions to handle common formats
    ('string', 'email'): 'name@example.com',
    ('string', 'zip-code'): '90210',
    ('string', 'uri'): 'https://example.com',

    # additional fallthrough cases
    ('integer', None): 1,  # integer
    ('number', None): 1.0,  # <fallthrough>
}

_READONLY_PROPERTY = object()  # sentinel for values not included in requests


def _dict_merge(dct, merge_dct):
    """Recursive dict merge.

    Inspired by :meth:``dict.update()``, instead of updating only top-level
    keys, dict_merge recurses down into dicts nested to an arbitrary depth,
    updating keys. The ``merge_dct`` is merged into ``dct``.

    From https://gist.github.com/angstwad/bf22d1822c38a92ec0a9

    Arguments:
        dct: dict onto which the merge is executed
        merge_dct: dct merged into dct
    """
    for k in merge_dct.keys():
        if (k in dct and isinstance(dct[k], dict)
                and isinstance(merge_dct[k], collections.abc.Mapping)):
            _dict_merge(dct[k], merge_dct[k])
        else:
            dct[k] = merge_dct[k]


def _parse_schema(schema, method):
    """
    Convert a Schema Object to a Python object.

    Args:
        schema: An ``OrderedDict`` representing the schema object.
    """
    if method and schema.get('readOnly', False):
        return _READONLY_PROPERTY

    # allOf: Must be valid against all of the subschemas
    if 'allOf' in schema:
        schema_ = copy.deepcopy(schema['allOf'][0])
        for x in schema['allOf'][1:]:
            _dict_merge(schema_, x)

        return _parse_schema(schema_, method)

    # anyOf: Must be valid against any of the subschemas
    # TODO(stephenfin): Handle anyOf

    # oneOf: Must be valid against exactly one of the subschemas
    if 'oneOf' in schema:
        # we only show the first one since we can't show everything
        return _parse_schema(schema['oneOf'][0], method)

    if 'enum' in schema:
        if 'example' in schema:
            return schema['example']
        # we show the first one
        return schema['enum'][0]

    schema_type = schema.get('type', 'object')

    if schema_type == 'array':
        # special case oneOf and anyOf so that we can show examples for all
        # possible combinations
        if 'oneOf' in schema['items']:
            return [
                _parse_schema(x, method) for x in schema['items']['oneOf']
            ]

        if 'anyOf' in schema['items']:
            return [
                _parse_schema(x, method) for x in schema['items']['anyOf']
            ]

        return [_parse_schema(schema['items'], method)]

    if schema_type == 'object':
        if 'example' in schema:
            example = schema.get('example')
            if example:
                example = copy.deepcopy(example)
                # filters out readonly properties
                if method and 'properties' in schema:
                    for k, v in schema.get('properties', {}).items():
                        if v.get('readOnly', False):
                            del example[k]
                ret = collections.OrderedDict(example)
                # XXX should be True to be compliant with OpenAPI
                if schema.get('additionalProperties', False) and '...' not in example:
                    # materialize in the example the fact that additional properties can be added
                    ret['...'] = '...'
                return ret
        if method and 'properties' in schema and \
                all(v.get('readOnly', False)
                    for v in schema['properties'].values()):
            return _READONLY_PROPERTY

        results = []
        for name, prop in schema.get('properties', {}).items():
            result = _parse_schema(prop, method)
            if result != _READONLY_PROPERTY:
                results.append((name, result))

        # XXX should be True to be compliant with OpenAPI
        if schema.get('additionalProperties', False):
            # materialize in the example the fact that additional properties can be added
            results.append(("...", "..."))

        return collections.OrderedDict(results)

    if 'example' in schema:
        return schema['example']
    if (schema_type, schema.get('format')) in _TYPE_MAPPING:
        return _TYPE_MAPPING[(schema_type, schema.get('format'))]

    return _TYPE_MAPPING[(schema_type, None)]  # unrecognized format


def _example(media_type_objects, method=None, endpoint=None, status=None,
             reqheader_examples={},
             resheader_examples={},
             nb_indent=0):
    """
    Format examples in `Media Type Object` openapi v3 to HTTP request or
    HTTP response example.
    If method and endpoint is provided, this function prints a request example
    else status should be provided to print a response example.

    Arguments:
        media_type_objects (Dict[str, Dict]): Dict containing
            Media Type Objects.
        method: The HTTP method to use in example.
        endpoint: The HTTP route to use in example.
        status: The HTTP status to use in example.
    """
    indent = '   '
    extra_indent = indent * nb_indent

    if method is not None:
        method = method.upper()
    else:
        try:
            # one of possible values for status might be 'default'.
            # in the case, just fallback to '-'
            status_text = http_status_codes[int(status)]
        except (ValueError, KeyError):
            status_text = '-'

    # Provide request samples for GET requests
    if method == 'GET':
        media_type_objects[''] = {
            'examples': {'Example request': {'value': '\n'}}}

    for content_type, content in media_type_objects.items():
        examples = content.get('examples')
        example = content.get('example')

        # Try to get the example from the schema
        if example is None and 'schema' in content:
            example = content['schema'].get('example')
            if example:
                example = copy.deepcopy(example)
                # filters out readonly properties
                if method and 'properties' in content['schema']:
                    for k, v in content['schema'].get('properties', {}).items():
                        if v.get('readOnly', False):
                            del example[k]
                # XXX should be True to be compliant with OpenAPI
                if content['schema'].get('additionalProperties', False) and '...' not in example:
                    # materialize in the example the fact that additional properties can be added
                    example['...'] = '...'

        if examples is None:
            examples = {}
            if not example:
                if re.match(r"application/[a-zA-Z\+]*json", content_type) is \
                        None:
                    LOG.info('skipping non-JSON example generation.')
                    continue
                example = _parse_schema(content['schema'], method=method)

            if method is None:
                examples['Example response'] = {
                    'value': example,
                }
            else:
                examples['Example request'] = {
                    'value': example,
                }

        for example in examples.values():
            # According to OpenAPI v3 specs, string examples should be left unchanged
            if not isinstance(example['value'], str):
                example['value'] = json.dumps(
                    example['value'], indent=4, separators=(',', ': '))

        for example_name, example in examples.items():
            if 'summary' in example:
                example_title = '{example_name} - {example[summary]}'.format(
                    **locals())
            else:
                example_title = example_name

            yield ''
            yield '{extra_indent}**{example_title}:**'.format(**locals())
            yield ''
            yield '{extra_indent}.. sourcecode:: http'.format(**locals())
            yield ''

            # Print http request example
            if method:
                yield '{extra_indent}{indent}{method} {endpoint} HTTP/1.1' \
                    .format(**locals())
                yield '{extra_indent}{indent}Host: example.com' \
                    .format(**locals())
                if content_type:
                    yield '{extra_indent}{indent}Content-Type: {content_type}'\
                        .format(**locals())
                for k, v in reqheader_examples.items():
                    yield '{extra_indent}{indent}{k}: {v}'\
                        .format(**locals())
            # Print http response example
            else:
                yield '{extra_indent}{indent}HTTP/1.1 {status} {status_text}' \
                    .format(**locals())
                yield '{extra_indent}{indent}Content-Type: {content_type}' \
                    .format(**locals())
                for k, v in resheader_examples.items():
                    yield '{extra_indent}{indent}{k}: {v}'\
                        .format(**locals())

            if content_type:
                yield ''
                for example_line in example['value'].splitlines():
                    yield '{extra_indent}{indent}{example_line}'.format(
                        **locals()
                        )
            if example['value'].splitlines():
                yield ''


def ref2link(entities, ref):
    name = ref.split('/')[-1]
    ref = entities(ref)
    return ':ref:`{name} <{ref}>`'.format(**locals())


def _httpresource(endpoint, method, properties, convert, render_examples,
                  render_request, group_examples=False, entities=False):
    # https://github.com/OAI/OpenAPI-Specification/blob/3.0.2/versions/3.0.0.md#operation-object
    parameters = properties.get('parameters', [])
    responses = properties['responses']
    query_param_examples = []
    indent = '   '

    yield '.. http:{0}:: {1}'.format(method, endpoint)
    yield '   :synopsis: {0}'.format(properties.get('summary', 'null'))
    yield ''

    if 'summary' in properties:
        for line in properties['summary'].splitlines():
            yield '{indent}**{line}**'.format(**locals())
        yield ''

    if 'description' in properties:
        for line in convert(properties['description']).splitlines():
            yield '{indent}{line}'.format(**locals())
        yield ''

    if properties.get('deprecated', False):
        yield '{indent}**DEPRECATED**'.format(**locals())
        yield ''

    if 'security' in properties:
        for sec_schema in properties['security']:
            sec_scope = ' or '.join([
                '``{}``'.format(s) for sch in sec_schema.values() for s in sch
            ])
            yield '{indent}**Scope required**: {sec_scope}'.format(**locals())
        yield ''

    def get_desc(desc, schema, indent, deep=True):
        if entities:
            doc = next(_process_one(['R'], schema, False, entities, convert))
            if desc:
                if not desc[-1] == '.':
                    desc = desc + '.'
            if doc[1]:
                if not doc[1].startswith("Object of") and not doc[1].startswith("Array of"):
                    doc[1] = "Object of type " + doc[1]
                if not doc[1][-1] == '.':
                    doc[1] = doc[1] + '.'
                desc += '\n' + doc[1]
            if deep and doc[2] and doc[2] != 'Additional properties':
                if not doc[2][-1] == '.':
                    doc[2] = doc[2] + '.'
                desc += '\n' + doc[2]
            desc = desc.rstrip()
        else:
            doc = next(_process_one(['R'], schema, False, entities, convert))
            if desc:
                if not desc[-1] == '.':
                    desc = desc + '.'
            if doc[2] and doc[2] != 'Additional properties':
                if not doc[2][-1] == '.':
                    doc[2] = doc[2] + '.'
                desc += '\n' + doc[2]
            desc = desc.rstrip()
        desc = textwrap.indent(desc, '{indent}{indent}'.format(**locals())).lstrip()
        return desc

    # print request's path params
    for param in filter(lambda p: p['in'] == 'path', parameters):
        yield indent + ':param {type} {name}:'.format(
            type=param['schema']['type'],
            name=param['name'])

        desc = param.get('description', '')
        desc = get_desc(desc, param['schema'], indent)
        if desc:
            yield '{indent}{indent}{desc}'.format(**locals())

    # print request's query params
    for param in filter(lambda p: p['in'] == 'query', parameters):
        yield indent + ':query {type} {name}:'.format(
            type=param['schema']['type'],
            name=param['name'])
        desc = param.get('description', '')
        desc = get_desc(desc, param['schema'], indent)
        if desc:
            yield '{indent}{indent}{desc}'.format(**locals())
        if param.get('required', False):
            yield '{indent}{indent}(Required)'.format(**locals())
        example = _parse_schema(param['schema'], method)
        example = param.get('example', example)
        if param.get('explode', False) and isinstance(example, list):
            for v in example:
                query_param_examples.append((param['name'], v))
        elif param.get('explode', False) and isinstance(example, dict):
            for k, v in example.items():
                query_param_examples.append((k, v))
        else:
            query_param_examples.append((param['name'], example))

    # print request content
    if render_request:
        request_content = properties.get('requestBody', {}).get('content', {})
        if request_content and 'application/json' in request_content:
            schema = request_content['application/json']['schema']
            req_properties = json.dumps(schema['properties'], indent=2,
                                        separators=(',', ':'))
            yield '{indent}**Request body:**'.format(**locals())
            yield ''
            yield '{indent}.. sourcecode:: json'.format(**locals())
            yield ''
            for line in req_properties.splitlines():
                # yield indent + line
                yield '{indent}{indent}{line}'.format(**locals())
                # yield ''
    else:
        desc = properties.get('requestBody', {}).get('description', '')
        request_content = properties.get('requestBody', {}).get('content', {})
        if request_content and 'application/json' in request_content:
            schema = request_content['application/json'].get('schema', {})
            if '$entity_ref' in schema or schema.get('type', 'object') == 'array':
                desc = get_desc(desc, schema, indent, deep=False)
                if desc:
                    yield '{indent}:form body: {desc}'.format(**locals())
            else:
                for prop, v in schema.get('properties', {}).items():
                    ptype = v.get('type', '')
                    desc = v.get('description', '')
                    yield '{indent}:jsonparam {ptype} {prop}: {desc}'.format(**locals()).rstrip()
        else:
            if desc:
                yield '{indent}:form body: {desc}.'.format(**locals())

    # print request header params
    reqheader_examples = {}
    for param in filter(lambda p: p['in'] == 'header', parameters):
        yield indent + ':reqheader {name}:'.format(**param)
        desc = param.get('description', '')
        desc = get_desc(desc, param['schema'], indent)
        if desc:
            yield '{indent}{indent}{desc}'.format(**locals())
        if param.get('required', False):
            yield '{indent}{indent}(Required)'.format(**locals())
        ex = param.get('example', param.get('schema', {}).get('example', None))
        if ex is None:
            # try examples
            ex = param.get('examples', param.get('schema', {}).get('examples', [None]))[0]
        if ex:
            reqheader_examples[param['name']] = ex

    # print request example
    if render_examples and not group_examples:
        endpoint_examples = endpoint
        if query_param_examples:
            endpoint_examples = endpoint + "?" + \
                parse.urlencode(query_param_examples)

        # print request example
        request_content = properties.get('requestBody', {}).get('content', {})
        for line in _example(
                request_content,
                method,
                endpoint=endpoint_examples,
                reqheader_examples=reqheader_examples,
                nb_indent=1):
            yield line

    # print response headers
    resheader_examples = {}
    for status, response in responses.items():
        for headername, header in response.get('headers', {}).items():
            yield indent + ':resheader {name}:'.format(name=headername)
            desc = header.get('description', '')
            desc = get_desc(desc, header.get('schema', {}), indent)
            if desc:
                yield '{indent}{indent}{desc}'.format(**locals())
            ex = header.get('example', header.get('schema', {}).get('example', None))
            if ex is None:
                # try examples
                ex = header.get('examples', header.get('schema', {}).get('examples', [None]))[0]
            if ex:
                resheader_examples[param['name']] = ex

    # print response status codes
    for status, response in responses.items():
        yield '{indent}:status {status}:'.format(**locals())
        content = response.get('content', {})
        if entities and content and 'application/json' in content:
            schema = content['application/json']['schema']
            desc = response.get('description', '')
            desc = get_desc(desc, schema, indent, deep=False)
            if desc:
                yield '{indent}{indent}{desc}'.format(**locals())
        else:
            desc = response.get('description', '')
            if desc and desc[-1] != '.':
                desc += '.'
            for line in convert(desc.splitlines()):
                yield '{indent}{indent}{line}'.format(**locals())

        # print response example
        if render_examples and not group_examples:
            for line in _example(
                    response.get('content', {}),
                    status=status,
                    resheader_examples=resheader_examples,
                    nb_indent=2):
                yield line

    if render_examples and group_examples:
        endpoint_examples = endpoint
        if query_param_examples:
            endpoint_examples = endpoint + "?" + \
                parse.urlencode(query_param_examples)

        # print request example
        request_content = properties.get('requestBody', {}).get('content', {})
        for line in _example(
                request_content,
                method,
                endpoint=endpoint_examples,
                reqheader_examples=reqheader_examples,
                resheader_examples=resheader_examples,
                nb_indent=1):
            yield line

        # print response example
        for status, response in responses.items():
            for line in _example(
                    response.get('content', {}),
                    status=status,
                    reqheader_examples=reqheader_examples,
                    resheader_examples=resheader_examples,
                    nb_indent=1):
                yield line

    for cb_name, cb_specs in properties.get('callbacks', {}).items():
        yield ''
        yield indent + '.. admonition:: Callback: ' + cb_name
        yield ''

        for cb_endpoint in cb_specs.keys():
            for cb_method, cb_properties in cb_specs[cb_endpoint].items():
                for line in _httpresource(
                        cb_endpoint,
                        cb_method,
                        cb_properties,
                        convert=convert,
                        render_examples=render_examples,
                        render_request=render_request,
                        group_examples=group_examples,
                        entities=entities):
                    if line:
                        yield indent+indent+line
                    else:
                        yield ''

    yield ''


def _header(title):
    yield title
    yield '=' * len(title)
    yield ''


def openapihttpdomain(spec, **options):
    generators = []

    # OpenAPI spec may contain JSON references, common properties, etc.
    # Trying to render the spec "As Is" will require to put multiple
    # if-s around the code. In order to simplify flow, let's make the
    # spec to have only one (expected) schema, i.e. normalize it.
    utils.normalize_spec(spec, **options)

    # Paths list to be processed
    paths = []

    # If 'paths' are passed we've got to ensure they exist within an OpenAPI
    # spec; otherwise raise error and ask user to fix that.
    if 'paths' in options:
        if not set(options['paths']).issubset(spec['paths']):
            raise ValueError(
                'One or more paths are not defined in the spec: %s.' % (
                    ', '.join(set(options['paths']) - set(spec['paths'])),
                )
            )
        paths = options['paths']

    # Check against regular expressions to be included
    if 'include' in options:
        for i in options['include']:
            ir = re.compile(i)
            for path in spec['paths']:
                if ir.match(path):
                    paths.append(path)

    # If no include nor paths option, then take full path
    if 'include' not in options and 'paths' not in options:
        paths = spec['paths']

    # Remove paths matching regexp
    if 'exclude' in options:
        _paths = []
        for e in options['exclude']:
            er = re.compile(e)
            for path in paths:
                if not er.match(path):
                    _paths.append(path)
        paths = _paths

    render_request = False
    if 'request' in options:
        render_request = True

    convert = utils.get_text_converter(options)

    if 'entities' in options:
        def f_entities(x):
            return _entities(spec, x)
        entities = f_entities
    else:
        entities = False

    # https://github.com/OAI/OpenAPI-Specification/blob/3.0.2/versions/3.0.0.md#paths-object
    if 'group' in options:
        groups = collections.OrderedDict(
            [(x['name'], []) for x in spec.get('tags', {})]
            )

        for endpoint in paths:
            for method, properties in spec['paths'][endpoint].items():
                key = properties.get('tags', [''])[0]
                groups.setdefault(key, []).append(_httpresource(
                    endpoint,
                    method,
                    properties,
                    convert,
                    render_examples='examples' in options,
                    render_request=render_request,
                    group_examples='group_examples' in options,
                    entities=entities))

        for key in groups.keys():
            if key:
                generators.append(_header(key))
            else:
                generators.append(_header('default'))

            generators.extend(groups[key])
    else:
        for endpoint in paths:
            for method, properties in spec['paths'][endpoint].items():
                generators.append(_httpresource(
                    endpoint,
                    method,
                    properties,
                    convert,
                    render_examples='examples' in options,
                    render_request=render_request,
                    group_examples='group_examples' in options,
                    entities=entities))

    return iter(itertools.chain(*generators))
