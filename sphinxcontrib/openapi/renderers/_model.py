from . import abc
from .. import utils

import re
import hashlib
import json
import textwrap

import jsonschema
from jsonschema import validate
from docutils.parsers.rst import directives

from sphinx.locale import get_translation
_ = get_translation('openapi')


def _get_description(obj, convert):
    D = convert(obj.get('description', '')).strip()
    if 'default' in obj:
        if D and D[-1] != '.':
            D += '.'
        if D:
            D += ' '
        D += 'Default: ``' + json.dumps(obj['default']) + "``."
    return D


def _get_contraints(obj):
    c = []
    if 'minItems' in obj:
        c.append(_('minItems is {}').format(obj['minItems']))
    if 'maxItems' in obj:
        c.append(_('maxItems is {}').format(obj['maxItems']))
    if 'minLength' in obj:
        c.append(_('minLength is {}').format(obj['minLength']))
    if 'maxLength' in obj:
        c.append(_('maxLength is {}').format(obj['maxLength']))
    if 'minimum' in obj:
        c.append(_('minimum is {}').format(obj['minimum']))
    if 'maximum' in obj:
        c.append(_('maximum is {}').format(obj['maximum']))
    if 'uniqueItems' in obj:
        c.append(_("items must be unique"))
    if "pattern" in obj:
        c.append(_("pattern ``{}``").format(obj["pattern"]))
    if 'enum' in obj:
        c.append(_('possible values are {}').format(
                 ', '.join(
                    [
                        '``{}``'.format(x) for x in obj['enum']
                    ]
                 )))
    if 'readOnly' in obj:
        c.append(_("read only"))
    if 'writeOnly' in obj:
        c.append(_("write only"))
    s = '; '.join(c)
    return s


def _add_constraints(obj, D, C):
    if C:
        if _('Constraints') not in D:
            C = _("Constraints: {}").format(C)
            if D and D[-1] != '.':
                D += '.'
        else:
            if C and D and D[-1] != ';':
                D += ';'
        if D and C and C[0] != '\n':
            D += ' '
        D += C
    else:
        if D and D[-1] != '.':
            D += '.'
    if 'deprecated' in obj:
        D += "\n\n**{}**".format(_("DEPRECATED"))
    return D


def _get_multi_type(schema, entities):
    T = []
    duplicate = set()
    if 'oneOf' in schema:
        k = 'oneOf'
    elif 'allOf' in schema:
        k = 'allOf'
    else:
        k = 'anyOf'
    for t in schema[k]:
        type = t.get('type', 'object')
        if '$entity_ref' in t and type == 'object':
            T.append(ref2link(entities, t['$entity_ref']))
        else:
            if type == 'string' and 'enum' in t:
                type = 'enumerate'
                vals = ', '.join(
                    [
                        '``{}``'.format(x) for x in t['enum']
                    ]
                )
                if vals:
                    type += ' (' + vals + ')'
            if type not in duplicate:
                T.append(type)
                duplicate.add(type)
    return T


def _process_one(prefix, schema, mandatory, entities, convert):
    if 'oneOf' in schema:
        type = 'oneOf'
    elif 'allOf' in schema:
        type = 'allOf'
    elif 'anyOf' in schema:
        type = 'anyOf'
    else:
        type = schema.get('type', 'object')
    if '$entity_ref' in schema and type == 'object' and prefix:
        # does not apply to first level types (prefix empty)
        T = _('Object of type {}').format(ref2link(entities, schema['$entity_ref']))
        D = _get_description(schema, convert)
        C = _get_contraints(schema)
        D = _add_constraints(schema, D, C)
        ret = ['.'.join(prefix), T, D, mandatory]
        yield ret
    elif type == 'array':
        ref = schema['items'].get('$entity_ref', None)
        type_items = schema['items'].get('type', None)
        if ref:
            D = _get_description(schema, convert)
            C = _get_contraints(schema)
            D = _add_constraints(schema, D, C)
            if type_items not in ['object', 'array']:
                # Since only object and array are described on their own
                # Add here the constraints of the referenced type
                D = _get_description(schema['items'], convert)
                C = _get_contraints(schema['items'])
                D = _add_constraints(schema['items'], D, C)
                C = _get_contraints(schema)
                D = _add_constraints(schema, D, C)
                yield [
                    '.'.join(prefix),
                    _('Array of {}').format(type_items),
                    D,
                    mandatory
                ]
            else:
                yield [
                    '.'.join(prefix),
                    _('Array of {}').format(ref2link(entities, ref)),
                    D,
                    mandatory
                ]
        elif type_items == 'object':
            T = _("Array")
            D = _get_description(schema, convert)
            C = _get_contraints(schema)
            D = _add_constraints(schema, D, C)
            yield ['.'.join(prefix), T, D, mandatory]
            if prefix:
                prefix[-1] += '[]'
            else:
                prefix = ['[]']
            for x in _process_one(prefix, schema['items'], False, entities, convert):
                yield x
        else:
            # Support array of simple types (string, etc.)
            D = _get_description(schema, convert)
            C = _get_contraints(schema)
            for x in _process_one(prefix, schema['items'], False, entities, convert):
                # Add C to x[2] now and not before (to avoid double "Constraints:")
                if D and x[2]:
                    DD = D + ' ' + x[2]
                else:
                    DD = D + x[2]
                DD = _add_constraints(schema, DD, C)
                yield [x[0], _('Array of {}').format(x[1]), DD, mandatory]
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
        if 'additionalProperties' in schema:
            D = _('Additional properties')
            if schema['additionalProperties'] is True:
                T = ''
            elif schema['additionalProperties'] is False:
                return
            else:
                if 'oneOf' in schema['additionalProperties']:
                    T = _("One of {}").format(
                        ", ".join(_get_multi_type(schema['additionalProperties'], entities)))
                elif 'allOf' in schema['additionalProperties']:
                    T = _("All of {}").format(
                        ", ".join(_get_multi_type(schema['additionalProperties'], entities)))
                elif 'anyOf' in schema['additionalProperties']:
                    T = _("Any of {}").format(
                        ", ".join(_get_multi_type(schema['additionalProperties'], entities)))
                else:
                    T = schema['additionalProperties'].get('type', 'object')
            yield ['.'.join(prefix+['*']), T, D, '']
    elif 'oneOf' in schema:
        # One of the subtype, must be basic types or ref
        D = _get_description(schema, convert)
        C = _get_contraints(schema)
        D = _add_constraints(schema, D, C)
        T = _get_multi_type(schema, entities)
        T = _("One of {}").format(", ".join(T))
        yield ['.'.join(prefix), T, D, mandatory]
    elif 'allOf' in schema:
        # All of the subtype, must be basic types or ref
        D = _get_description(schema, convert)
        C = _get_contraints(schema)
        D = _add_constraints(schema, D, C)
        T = _get_multi_type(schema, entities)
        T = _("All of {}").format(", ".join(T))
        yield ['.'.join(prefix), T, D, mandatory]
    elif 'anyOf' in schema:
        # Any of the subtype, must be basic types or ref
        D = _get_description(schema, convert)
        C = _get_contraints(schema)
        D = _add_constraints(schema, D, C)
        T = _get_multi_type(schema, entities)
        T = _("Any of {}").format(", ".join(T))
        yield ['.'.join(prefix), T, D, mandatory]
    elif type in ['string', 'integer', 'number', 'boolean']:
        T = type
        if schema.get('format', ''):
            T += '/' + schema.get('format', '')
        D = _get_description(schema, convert)
        C = _get_contraints(schema)
        D = _add_constraints(schema, D, C)
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
    yield '    * - ' + _('Attribute')
    yield '      - ' + _('Type')
    yield '      - ' + _('Description')
    yield '      - ' + _('Required')

    for item in _process_one([], schema, False, entities, convert):
        if str(item[0]):
            yield '    * - ``' + str(item[0]) + '``'
        else:
            yield '    * - ' + _('N/A')
        yield '      - ' + textwrap.indent(str(item[1]), '        ').lstrip()
        yield '      - ' + textwrap.indent(str(item[2]), '        ').lstrip()
        yield '      - ' + _('Yes') if item[3] else '      -'

    if 'example' in schema or 'examples' in schema:
        N = 1
        for ex in [schema.get('example', None)] + schema.get('examples', []):
            if ex is None:
                continue
            yield ''
            yield _('Example #{}:').format(N)
            N += 1
            # validate the example against this schema
            try:
                validate(instance=ex, schema=schema)
                yield ''
                yield '.. code-block:: json'
                yield ''
                for line in json.dumps(ex, indent=2).splitlines():
                    yield '    ' + line
            except jsonschema.ValidationError:
                yield ''
                yield '**{}**'.format(_('Invalid example'))


def ref2link(entities, ref):
    if ref in ['object', 'string']:
        return ref
    name = ref.split('/')[-1]
    if ref[0] == '#':
        ref = ref[1:]
    if callable(entities):
        ref = entities(ref)
        return ':ref:`{name} <{ref}>`'.format(**locals())
    else:
        return '{name}'.format(**locals())


def _entities(spec, ref):
    m = hashlib.md5()
    m.update(spec.get('info', {}).get('title', '').encode('utf-8'))
    m.update(spec.get('info', {}).get('version', '0.0').encode('utf-8'))
    key = m.hexdigest()
    # for unit tests
    if key == '30565a8911a6bb487e3745c0ea3c8224':
        key = ''
    if '#' in ref:
        ref = ref.split('#')[1]
    return key + ref


class ModelRenderer(abc.RestructuredTextRenderer):

    option_spec = {
        # prefix (components/schemas)
        "prefix": str,
        # header marker (')
        "header": directives.single_char_or_unicode,
        # Markup format to render OpenAPI descriptions.
        "format": str,
        # A list of entities to be rendered. Must be whitespace delimited.
        "entities": lambda s: s.split(),
        # Regular expression patterns to include/exclude entities to/from
        # rendering. The patterns must be whitespace delimited.
        "include": lambda s: s.split(),
        "exclude": lambda s: s.split(),
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

        schemas = spec
        for p in filter(None, self._options["prefix"].split('/')):
            schemas = schemas.get(p, {})

        # Entities list to be processed
        entities = []

        # If 'entities' are passed we've got to ensure they exist within an OpenAPI
        # spec; otherwise raise error and ask user to fix that.
        if 'entities' in self._options:
            if not set(self._options['entities']).issubset(schemas.keys()):
                raise ValueError(
                    'One or more entities are not defined in the spec: %s.' % (
                        ', '.join(set(self._options['entities']) - set(schemas.keys())),
                    )
                )
            entities = self._options['entities']

        # Check against regular expressions to be included
        if 'include' in self._options:
            for i in self._options['include']:
                ir = re.compile(i)
                for entity in schemas.keys():
                    if ir.match(entity):
                        entities.append(entity)

        # If no include nor entities option, then take full entity
        if 'include' not in self._options and 'entities' not in self._options:
            entities = schemas.keys()

        # Remove entities matching regexp
        if 'exclude' in self._options:
            tmp_entities = []
            for e in self._options['exclude']:
                er = re.compile(e)
                for entity in entities:
                    if not er.match(entity):
                        tmp_entities.append(entity)
            entities = tmp_entities

        def __entities(x):
            return _entities(spec, x)

        for name in entities:
            schema = schemas[name]
            for line in _build(name, schema, __entities, convert, self._options):
                yield line.rstrip()
            yield ''
