import textwrap
import collections
import yaml

from sphinxcontrib.openapi import renderers


class TestOpenApi3HttpDomain(object):

    def test_basic(self):
        renderer = renderers.TocRenderer(None, {})
        spec = collections.defaultdict(collections.OrderedDict)
        spec['paths']['/resource_a'] = {
            'get': {
                'description': 'resource a',
                'responses': {
                    '200': {'description': 'ok'},
                }
            }
        }
        spec['paths']['/resource_b'] = {
            'post': {
                'operationId': 'UpdateResourceB',
                'description': 'resource b',
                'responses': {
                    '404': {'description': 'error'},
                }
            }
        }

        text = '\n'.join(renderer.render_restructuredtext_markup(spec))

        assert text == textwrap.dedent("""
        .. hlist::
            :columns: 2

            - `get /resource_a <#get--resource_a>`_
            - `UpdateResourceB <#post--resource_b>`_
        """)

    def test_options(self):
        renderer = renderers.TocRenderer(None, {"nb_columns": 3})
        spec = collections.defaultdict(collections.OrderedDict)
        spec['paths']['/resource_a'] = {
            'get': {
                'description': 'resource a',
                'responses': {
                    '200': {'description': 'ok'},
                }
            }
        }
        spec['paths']['/resource_b'] = {
            'post': {
                'operationId': 'UpdateResourceB',
                'description': 'resource b',
                'responses': {
                    '404': {'description': 'error'},
                }
            }
        }

        text = '\n'.join(renderer.render_restructuredtext_markup(spec))

        assert text == textwrap.dedent("""
        .. hlist::
            :columns: 3

            - `get /resource_a <#get--resource_a>`_
            - `UpdateResourceB <#post--resource_b>`_
        """)

    def test_contextpath(self):
        spec = yaml.safe_load(textwrap.dedent("""
        ---
        openapi: 3.0.0
        servers:
        - url: https://test.org/context
        paths:
          /resources:
            get:
              summary: Summary
              responses:
                200:
                  description: Success
                  content:
                    application/json:
                      schema:
                        type: string
                      example: RESPONSE
        """))

        renderer = renderers.TocRenderer(None, {"contextpath": True})

        text = '\n'.join(renderer.render_restructuredtext_markup(spec))

        assert text == textwrap.dedent("""
        .. hlist::
            :columns: 2

            - `get /resources <#get--context-resources>`_
        """)
