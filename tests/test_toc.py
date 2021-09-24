import textwrap
import collections

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
