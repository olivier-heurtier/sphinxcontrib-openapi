import textwrap
import collections

import pytest
import yaml
from sphinxcontrib.openapi import renderers
import jsonschema


class TestOpenApi3HttpDomain(object):

    def test_basic(self):
        renderer = renderers.ModelRenderer(None, {})
        text = '\n'.join(renderer.render_restructuredtext_markup({
            'openapi': '3.0.0',
            'paths': {},
            'components': {
                'schemas': {
                    'Resource': {
                        'type': 'object',
                        'required': ['kind'],
                        'properties': collections.OrderedDict([
                            ('kind', {
                                'description': 'Kind',
                                'type': 'string',
                            }),
                            ('instance', {
                                '$ref': '#/components/schemas/Instance',
                            }),
                        ]),
                    },
                    'Instance': {
                        'type': 'object',
                        'properties': collections.OrderedDict([
                            ('instance', {
                                'description': 'Instance',
                                'type': 'string',
                                'enum': ['A', 'B'],
                            }),
                            ('instanceType', {
                                '$ref': '#/components/schemas/InstanceType',
                            }),
                        ]),
                    },
                    'InstanceList': {
                        'type': 'array',
                        'items': {
                            '$ref':  '#/components/schemas/Instance'
                        }
                    },
                    'InstanceType': {
                        'type': 'string',
                        'enum': ['T1', 'T2'],
                    },
                },
            },
        }))

        assert text == textwrap.dedent("""
        .. _/components/schemas/Resource:

        Resource
        ''''''''

        .. list-table:: Resource
            :header-rows: 1
            :widths: 25 25 45 15
            :class: longtable

            * - Attribute
              - Type
              - Description
              - Mandatory
            * - ``kind``
              - string
              - Kind
              - Yes
            * - ``instance``
              - Object of type :ref:`Instance </components/schemas/Instance>`
              -
              -


        .. _/components/schemas/Instance:

        Instance
        ''''''''

        .. list-table:: Instance
            :header-rows: 1
            :widths: 25 25 45 15
            :class: longtable

            * - Attribute
              - Type
              - Description
              - Mandatory
            * - ``instance``
              - string
              - Instance. Constraints: possible values are: ``A``, ``B``
              -
            * - ``instanceType``
              - string
              - Constraints: possible values are: ``T1``, ``T2``
              -


        .. _/components/schemas/InstanceList:

        InstanceList
        ''''''''''''

        .. list-table:: InstanceList
            :header-rows: 1
            :widths: 25 25 45 15
            :class: longtable

            * - Attribute
              - Type
              - Description
              - Mandatory
            * - N/A
              - Array of :ref:`Instance </components/schemas/Instance>`
              -
              -

        """)

    def test_options(self):
        renderer = renderers.ModelRenderer(None, {"header": "?", "prefix": "definitions"})
        text = '\n'.join(renderer.render_restructuredtext_markup({
            'openapi': '3.0.0',
            'paths': {},
            'definitions': {
                'Resource': {
                    'type': 'object',
                    'required': ['kind'],
                    'properties': collections.OrderedDict([
                        ('kind', {
                            'description': 'Kind',
                            'type': 'string',
                        }),
                    ]),
                },
            },
        }))

        assert text == textwrap.dedent("""
        .. _/components/schemas/Resource:

        Resource
        ????????

        .. list-table:: Resource
            :header-rows: 1
            :widths: 25 25 45 15
            :class: longtable

            * - Attribute
              - Type
              - Description
              - Mandatory
            * - ``kind``
              - string
              - Kind
              - Yes
        """)

    def test_types(self):
        renderer = renderers.ModelRenderer(None, {})
        spec = yaml.safe_load(textwrap.dedent("""
        ---
        openapi: 3.0.0
        paths: {}
        components:
          schemas:
            Test1:
              type: object
              properties:
                field1:
                  type: integer
                  format: int32
                  description: Signed 32 bits
                field2:
                  type: number
                  format: float
                  description: Float
                field3:
                  type: string
                  format: byte
                  description: base64 encoded characters
                field4:
                  type: boolean

        """))
        text = '\n'.join(renderer.render_restructuredtext_markup(spec))
        assert text == textwrap.dedent("""
        .. _/components/schemas/Test1:

        Test1
        '''''

        .. list-table:: Test1
            :header-rows: 1
            :widths: 25 25 45 15
            :class: longtable

            * - Attribute
              - Type
              - Description
              - Mandatory
            * - ``field1``
              - string/int32
              - Signed 32 bits
              -
            * - ``field2``
              - string/float
              - Float
              -
            * - ``field3``
              - string/byte
              - base64 encoded characters
              -
            * - ``field4``
              - string
              -
              -
        """)

    def test_array(self):
        renderer = renderers.ModelRenderer(None, {})
        spec = yaml.safe_load(textwrap.dedent("""
        ---
        openapi: 3.0.0
        paths: {}
        components:
          schemas:
            Test1:
              type: array
              items:
                type: object
                required:
                  - field1
                properties:
                  field1:
                    type: string
            Test2:
              type: object
              properties:
                table:
                  type: array
                  items:
                    type: object
                    required:
                      - field2
                    properties:
                      field2:
                        type: string
                      field3:
                        type: array
                        items:
                          $ref: '#/components/schemas/Test1'
        """))
        text = '\n'.join(renderer.render_restructuredtext_markup(spec))
        assert text == textwrap.dedent("""
        .. _/components/schemas/Test1:

        Test1
        '''''

        .. list-table:: Test1
            :header-rows: 1
            :widths: 25 25 45 15
            :class: longtable

            * - Attribute
              - Type
              - Description
              - Mandatory
            * - N/A
              - Array
              -
              -
            * - ``[].field1``
              - string
              -
              - Yes


        .. _/components/schemas/Test2:

        Test2
        '''''

        .. list-table:: Test2
            :header-rows: 1
            :widths: 25 25 45 15
            :class: longtable

            * - Attribute
              - Type
              - Description
              - Mandatory
            * - ``table``
              - Array
              -
              -
            * - ``table[].field2``
              - string
              -
              - Yes
            * - ``table[].field3``
              - Array of :ref:`Test1 </components/schemas/Test1>`
              -
              -
        """)

    def test_markdown(self):
        renderer = renderers.ModelRenderer(None, {'format': 'markdown'})
        spec = yaml.safe_load(textwrap.dedent("""
        ---
        openapi: 3.0.0
        paths: {}
        components:
          schemas:
            Test1:
              description: This is a __bold__ description
              type: object
              properties:
                field1:
                  type: integer
                  format: int32
                  description: Signed _32_ bits
        """))
        text = '\n'.join(renderer.render_restructuredtext_markup(spec))
        assert text == textwrap.dedent("""
        .. _/components/schemas/Test1:

        Test1
        '''''

        This is a **bold** description

        .. list-table:: Test1
            :header-rows: 1
            :widths: 25 25 45 15
            :class: longtable

            * - Attribute
              - Type
              - Description
              - Mandatory
            * - ``field1``
              - string/int32
              - Signed *32* bits
              -
        """)

    def test_example(self):
        renderer = renderers.ModelRenderer(None, {})
        spec = yaml.safe_load(textwrap.dedent("""
        ---
        openapi: 3.0.0
        paths: {}
        components:
          schemas:
            Test1:
              type: object
              properties:
                field1:
                  type: integer
                  format: int32
              example:
                field1: 12
        """))
        text = '\n'.join(renderer.render_restructuredtext_markup(spec))
        assert text == textwrap.dedent("""
        .. _/components/schemas/Test1:

        Test1
        '''''

        .. list-table:: Test1
            :header-rows: 1
            :widths: 25 25 45 15
            :class: longtable

            * - Attribute
              - Type
              - Description
              - Mandatory
            * - ``field1``
              - string/int32
              -
              -

        Examples:

        .. code-block:: json

            {
              "field1": 12
            }
        """)

    def test_examples(self):
        renderer = renderers.ModelRenderer(None, {})
        spec = yaml.safe_load(textwrap.dedent("""
        ---
        openapi: 3.0.0
        paths: {}
        components:
          schemas:
            Test1:
              type: object
              properties:
                field1:
                  type: integer
                  format: int32
              examples:
                - field1: 12
                - field1: -2
        """))
        text = '\n'.join(renderer.render_restructuredtext_markup(spec))
        assert text == textwrap.dedent("""
        .. _/components/schemas/Test1:

        Test1
        '''''

        .. list-table:: Test1
            :header-rows: 1
            :widths: 25 25 45 15
            :class: longtable

            * - Attribute
              - Type
              - Description
              - Mandatory
            * - ``field1``
              - string/int32
              -
              -

        Examples:

        .. code-block:: json

            {
              "field1": 12
            }

        .. code-block:: json

            {
              "field1": -2
            }
        """)

    def test_bad_example(self):
        renderer = renderers.ModelRenderer(None, {})
        spec = yaml.safe_load(textwrap.dedent("""
        ---
        openapi: 3.0.0
        paths: {}
        components:
          schemas:
            Test1:
              type: object
              properties:
                field1:
                  type: integer
                  format: int32
              example:
                field1: true
        """))
        with pytest.raises(jsonschema.ValidationError):
            '\n'.join(renderer.render_restructuredtext_markup(spec))
