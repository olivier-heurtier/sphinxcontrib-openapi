import textwrap
import collections

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
              - :ref:`Instance </components/schemas/Instance>`
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
              - Instance Possible values are: ``A``, ``B``
              -
            * - ``instanceType``
              - string
              -  Possible values are: ``T1``, ``T2``
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
              - array of :ref:`Instance </components/schemas/Instance>`
              -
              -

        """)
