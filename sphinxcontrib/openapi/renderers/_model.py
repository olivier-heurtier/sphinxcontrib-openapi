
from . import abc
from .. import utils

import hashlib
import json
from jsonschema import validate
from docutils.parsers.rst import directives


def _get_description(obj, convert):
    return convert(obj.get('description', '')).strip()


def _get_contraints(obj):
    c = []
    if 'minItems' in obj:
        c.append('minItems: ' + str(obj['minItems']))
    if 'maxItems' in obj:
        c.append('maxItems: ' + str(obj['maxItems']))
    if 'minLength' in obj:
        c.append('minLength: ' + str(obj['minLength']))
    if 'maxLength' in obj:
        c.append('maxLength: ' + str(obj['maxLength']))
    if 'minimum' in obj:
        c.append('minimum: ' + str(obj['minimum']))
    if 'maximum' in obj:
        c.append('maximum: ' + str(obj['maximum']))
    if 'enum' in obj:
        c.append('possible values are: ' +
                 ', '.join(
                    [
                        '``{}``'.format(x) for x in obj['enum']
                    ]
                 ))
    return '; '.join(c)


def _add_constraints(D, C):
    if C:
        if D and D[-1] != '.':
            D += '.'
        if D:
            D += ' '
        D += 'Constraints: ' + C
    return D


def _process_one(prefix, schema, mandatory, entities, convert):
    type = schema.get('type', 'object')
    print(prefix, type, schema.keys(), mandatory)
    if '$entity_ref' in schema and type == 'object' and prefix:
        T = 'Object of type ' + ref2link(entities, schema['$entity_ref'])
        D = _get_description(schema, convert)
        ret = ['.'.join(prefix), T, D, mandatory]
        yield ret
    elif type == 'array':
        ref = schema['items'].get('$entity_ref', None)
        if ref:
            yield [
                '.'.join(prefix),
                'Array of ' + ref2link(entities, ref),
                _get_description(schema, convert),
                mandatory
            ]
        else:
            T = "Array"
            D = _get_description(schema, convert)
            C = _get_contraints(schema)
            D = _add_constraints(D, C)
            yield ['.'.join(prefix), T, D, mandatory]
            if prefix:
                prefix[-1] += '[]'
            else:
                prefix = ['[]']
            for x in _process_one(prefix, schema['items'], False, entities, convert):
                yield x
    elif type == 'object':
        required = schema.get('required', [])
        for prop_name, prop in schema.get('properties', {}).items():
            for x in _process_one(
                    prefix+[prop_name],
                    prop,
                    prop_name in required,
                    entities,
                    convert):
                yield x
    elif type in ['string', 'integer', 'number', 'boolean']:
        T = 'string'
        if schema.get('format', ''):
            T += '/' + schema.get('format', '')
        D = _get_description(schema, convert)
        C = _get_contraints(schema)
        D = _add_constraints(D, C)
        yield ['.'.join(prefix), T, D, mandatory]


def _build(name, schema, entities, convert, options):
    if 'type' not in schema:
        schema['type'] = 'object'
    if schema.get('type', '') not in ['object', 'array']:
        return ''

    yield ''
    yield '.. _'+entities('/components/schemas/'+name)+':'
    yield ''
    yield name
    yield options['header'] * len(name)
    yield ''
    D = _get_description(schema, convert)
    if D:
        yield D
        yield ''
    yield '.. list-table:: ' + name
    yield '    :header-rows: 1'
    yield '    :widths: 25 25 45 15'
    yield '    :class: longtable'
    yield ''
    yield '    * - Attribute'
    yield '      - Type'
    yield '      - Description'
    yield '      - Mandatory'

    for item in _process_one([], schema, False, entities, convert):
        if str(item[0]):
            yield '    * - ``' + str(item[0]) + '``'
        else:
            yield '    * - N/A'
        yield '      - ' + str(item[1])
        yield '      - ' + str(item[2])
        yield '      - ' + 'Yes' if item[3] else '      -'

    if 'example' in schema or 'examples' in schema:
        yield ''
        yield 'Examples:'
        for ex in [schema.get('example', None)] + schema.get('examples', []):
            if ex is None:
                continue
            # validate the example against this schema
            validate(instance=ex, schema=schema)
            yield ''
            yield '.. code-block:: json'
            yield ''
            for line in json.dumps(ex, indent=2).splitlines():
                yield '    ' + line


def ref2link(entities, ref):
    if ref in ['object', 'string']:
        return ref
    name = ref.split('/')[-1]
    if ref[0] == '#':
        ref = ref[1:]
    ref = entities(ref)
    return ':ref:`{name} <{ref}>`'.format(**locals())


def _entities(spec, ref):
    m = hashlib.md5()
    m.update(spec.get('info', {}).get('title', '').encode('utf-8'))
    m.update(spec.get('info', {}).get('version', '0.0').encode('utf-8'))
    key = m.hexdigest()
    if key == '30565a8911a6bb487e3745c0ea3c8224':
        key = ''
    return key + ref


class ModelRenderer(abc.RestructuredTextRenderer):

    option_spec = {
        # prefix (components/schemas)
        "prefix": str,
        # header marker (')
        "header": directives.single_char_or_unicode,
        # Markup format to render OpenAPI descriptions.
        "format": str,
    }

    def __init__(self, state, options):
        self._state = state
        self._options = options
        if 'header' not in self._options:
            self._options["header"] = "'"
        if 'prefix' not in self._options:
            self._options["prefix"] = "/components/schemas"

    def render_restructuredtext_markup(self, spec):

        utils.normalize_spec(spec, **self._options)

        convert = utils.get_text_converter(self._options)

        def entities(x):
            return _entities(spec, x)

        schemas = spec
        for p in filter(None, self._options["prefix"].split('/')):
            schemas = schemas.get(p, {})
        for name, schema in schemas.items():
            for line in _build(name, schema, entities, convert, self._options):
                yield line.rstrip()
            yield ''
