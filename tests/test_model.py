import textwrap
import collections

import yaml
from sphinxcontrib.openapi import renderers


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
                                'readOnly': True,
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
                                'writeOnly': True,
                                'deprecated': True,
                            }),
                            ('instanceType', {
                                '$ref': '#/components/schemas/InstanceType',
                            }),
                            ('dep', {
                                'description': 'Deprecation',
                                'type': 'string',
                                'deprecated': True,
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
              - Required
            * - ``kind``
              - string
              - Kind. Constraints: read only
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
              - Required
            * - ``instance``
              - string
              - Instance. Constraints: possible values are ``A``, ``B``; write only

                **DEPRECATED**
              -
            * - ``instanceType``
              - string
              - Constraints: possible values are ``T1``, ``T2``
              -
            * - ``dep``
              - string
              - Deprecation.

                **DEPRECATED**
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
              - Required
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
              - Required
            * - ``kind``
              - string
              - Kind.
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
                  default: false
                field5:
                  type: array
                  items:
                    type: string
                    maxLength: 255
                  minItems: 1
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
              - Required
            * - ``field1``
              - integer/int32
              - Signed 32 bits.
              -
            * - ``field2``
              - number/float
              - Float.
              -
            * - ``field3``
              - string/byte
              - base64 encoded characters.
              -
            * - ``field4``
              - boolean
              - Default: ``false``.
              -
            * - ``field5``
              - Array of string
              - Constraints: maxLength is 255; minItems is 1
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
                        pattern: "a-zA-Z0-9"
                      field3:
                        type: array
                        items:
                          $ref: '#/components/schemas/Test1'
                        minItems: 1
                      field4:
                        type: array
                        items:
                          type: string
                        minItems: 1
                        maxItems: 10
                        uniqueItems: True
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
              - Required
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
              - Required
            * - ``table``
              - Array
              -
              -
            * - ``table[].field2``
              - string
              - Constraints: pattern ``a-zA-Z0-9``
              - Yes
            * - ``table[].field3``
              - Array of :ref:`Test1 </components/schemas/Test1>`
              - Constraints: minItems is 1
              -
            * - ``table[].field4``
              - Array of string
              - Constraints: minItems is 1; maxItems is 10; items must be unique
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
                  default: 5
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
              - Required
            * - ``field1``
              - integer/int32
              - Signed *32* bits. Default: ``5``.
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
              - Required
            * - ``field1``
              - integer/int32
              -
              -

        Example #1:

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
              - Required
            * - ``field1``
              - integer/int32
              -
              -

        Example #1:

        .. code-block:: json

            {
              "field1": 12
            }

        Example #2:

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
              - Required
            * - ``field1``
              - integer/int32
              -
              -

        Example #1:

        **Invalid example**
        """)

    def test_oneof(self):
        renderer = renderers.ModelRenderer(None, {})
        spec = yaml.safe_load(textwrap.dedent("""
        ---
        openapi: 3.0.0
        paths: {}
        components:
          schemas:
            Test1:
              type: object
              additionalProperties:
                oneOf:
                - type: string
                - type: integer
                - type: number
                - type: boolean
                - $ref: '#/components/schemas/Test4'
                - $ref: '#/components/schemas/Test5'
            Test2:
              type: object
              properties:
                field2:
                  oneOf:
                  - type: string
                  - type: integer
                  - type: number
                  - type: boolean
            Test3:
              oneOf:
                - $ref: '#/components/schemas/Test4'
                - type: object
                  required:
                    - field4
            Test4:
              type: object
              properties:
                field4:
                  type: string
              additionalProperties: false
            Test5:
              type: string
              enum: [A, B]
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
              - Required
            * - ``*``
              - One of string, integer, number, boolean, """ +
                                       """:ref:`Test4 </components/schemas/Test4>`, enumerate (``A``, ``B``)
              - Additional properties
              -


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
              - Required
            * - ``field2``
              - One of string, integer, number, boolean
              -
              -


        .. _/components/schemas/Test3:

        Test3
        '''''

        .. list-table:: Test3
            :header-rows: 1
            :widths: 25 25 45 15
            :class: longtable

            * - Attribute
              - Type
              - Description
              - Required
            * - N/A
              - One of :ref:`Test4 </components/schemas/Test4>`, object
              -
              -


        .. _/components/schemas/Test4:

        Test4
        '''''

        .. list-table:: Test4
            :header-rows: 1
            :widths: 25 25 45 15
            :class: longtable

            * - Attribute
              - Type
              - Description
              - Required
            * - ``field4``
              - string
              -
              -

        """)

    def test_allof(self):
        renderer = renderers.ModelRenderer(None, {})
        spec = yaml.safe_load(textwrap.dedent("""
        ---
        openapi: 3.0.0
        paths: {}
        components:
          schemas:
            Test1:
              type: object
              additionalProperties:
                allOf:
                - type: string
                - type: integer
                - type: number
                - type: boolean
                - $ref: '#/components/schemas/Test4'
            Test2:
              type: object
              properties:
                field2:
                  allOf:
                  - type: string
                  - type: integer
                  - type: number
                  - type: boolean
            Test3:
              allOf:
                - $ref: '#/components/schemas/Test4'
                - type: object
                  required:
                    - field4
            Test4:
              type: object
              properties:
                field4:
                  type: string
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
              - Required
            * - ``*``
              - All of string, integer, number, boolean, :ref:`Test4 </components/schemas/Test4>`
              - Additional properties
              -


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
              - Required
            * - ``field2``
              - All of string, integer, number, boolean
              -
              -


        .. _/components/schemas/Test3:

        Test3
        '''''

        .. list-table:: Test3
            :header-rows: 1
            :widths: 25 25 45 15
            :class: longtable

            * - Attribute
              - Type
              - Description
              - Required
            * - N/A
              - All of :ref:`Test4 </components/schemas/Test4>`, object
              -
              -


        .. _/components/schemas/Test4:

        Test4
        '''''

        .. list-table:: Test4
            :header-rows: 1
            :widths: 25 25 45 15
            :class: longtable

            * - Attribute
              - Type
              - Description
              - Required
            * - ``field4``
              - string
              -
              -
        """)

    def test_anyof(self):
        renderer = renderers.ModelRenderer(None, {})
        spec = yaml.safe_load(textwrap.dedent("""
        ---
        openapi: 3.0.0
        paths: {}
        components:
          schemas:
            Test1:
              type: object
              additionalProperties:
                anyOf:
                - type: string
                - type: integer
                - type: number
                - type: boolean
                - $ref: '#/components/schemas/Test4'
            Test2:
              type: object
              properties:
                field2:
                  anyOf:
                  - type: string
                  - type: integer
                  - type: number
                  - type: boolean
            Test3:
              anyOf:
                - $ref: '#/components/schemas/Test4'
                - type: object
                  required:
                    - field4
            Test4:
              type: object
              properties:
                field4:
                  type: string
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
              - Required
            * - ``*``
              - Any of string, integer, number, boolean, :ref:`Test4 </components/schemas/Test4>`
              - Additional properties
              -


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
              - Required
            * - ``field2``
              - Any of string, integer, number, boolean
              -
              -


        .. _/components/schemas/Test3:

        Test3
        '''''

        .. list-table:: Test3
            :header-rows: 1
            :widths: 25 25 45 15
            :class: longtable

            * - Attribute
              - Type
              - Description
              - Required
            * - N/A
              - Any of :ref:`Test4 </components/schemas/Test4>`, object
              -
              -


        .. _/components/schemas/Test4:

        Test4
        '''''

        .. list-table:: Test4
            :header-rows: 1
            :widths: 25 25 45 15
            :class: longtable

            * - Attribute
              - Type
              - Description
              - Required
            * - ``field4``
              - string
              -
              -
        """)

    def test_others_additional(self):
        renderer = renderers.ModelRenderer(None, {})
        spec = yaml.safe_load(textwrap.dedent("""
        ---
        openapi: 3.0.0
        paths: {}
        components:
          schemas:
            Test1:
              type: object
              required:
                - field1
              properties:
                field1:
                  type: string
                  example: F1
                others:
                  type: object
                  additionalProperties: true
              additionalProperties: false
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
              - Required
            * - ``field1``
              - string
              -
              - Yes
            * - ``others.*``
              -
              - Additional properties
              -
        """)

    def test_filtering(self):
        spec = yaml.safe_load(textwrap.dedent("""
        ---
        openapi: 3.0.0
        paths: {}
        components:
          schemas:
            A:
              properties:
                a:
                  type: string
            B:
              properties:
                b:
                  type: string
            AB:
              properties:
                ab:
                  type: string
        """))

        renderer = renderers.ModelRenderer(None, {"include": ["A.*"]})
        text = '\n'.join(renderer.render_restructuredtext_markup(spec))
        assert text == textwrap.dedent("""
        .. _/components/schemas/A:

        A
        '

        .. list-table:: A
            :header-rows: 1
            :widths: 25 25 45 15
            :class: longtable

            * - Attribute
              - Type
              - Description
              - Required
            * - ``a``
              - string
              -
              -


        .. _/components/schemas/AB:

        AB
        ''

        .. list-table:: AB
            :header-rows: 1
            :widths: 25 25 45 15
            :class: longtable

            * - Attribute
              - Type
              - Description
              - Required
            * - ``ab``
              - string
              -
              -
        """)

        renderer = renderers.ModelRenderer(None, {"include": ["A.*"], "exclude": [".*B"]})
        text = '\n'.join(renderer.render_restructuredtext_markup(spec))
        assert text == textwrap.dedent("""
        .. _/components/schemas/A:

        A
        '

        .. list-table:: A
            :header-rows: 1
            :widths: 25 25 45 15
            :class: longtable

            * - Attribute
              - Type
              - Description
              - Required
            * - ``a``
              - string
              -
              -
        """)

        renderer = renderers.ModelRenderer(None, {"entities": ["AB", "B"], "exclude": ["AB"]})
        text = '\n'.join(renderer.render_restructuredtext_markup(spec))
        assert text == textwrap.dedent("""
        .. _/components/schemas/B:

        B
        '

        .. list-table:: B
            :header-rows: 1
            :widths: 25 25 45 15
            :class: longtable

            * - Attribute
              - Type
              - Description
              - Required
            * - ``b``
              - string
              -
              -
        """)
