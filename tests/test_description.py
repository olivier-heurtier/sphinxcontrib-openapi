import textwrap
import yaml

from sphinxcontrib.openapi import renderers


class TestOpenApi3HttpDomain(object):

    def test_basic(self):
        spec = yaml.safe_load(textwrap.dedent("""
        ---
        openapi: 3.0.0
        info:
          description: >-
            This is a _text_.
        paths:
          /resources:
            get:
              description: test service
              responses:
                200:
                  description: Success
        """))

        renderer = renderers.DescriptionRenderer(None, {})
        text = '\n'.join(renderer.render_restructuredtext_markup(spec))

        assert text == "This is a _text_.\n"

        renderer = renderers.DescriptionRenderer(None, {"format": "markdown"})
        text = '\n'.join(renderer.render_restructuredtext_markup(spec))

        assert text == "\nThis is a *text*.\n"
