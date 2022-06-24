
from . import abc
from .. import utils


class DescriptionRenderer(abc.RestructuredTextRenderer):

    option_spec = {
        # Markup format to render OpenAPI descriptions.
        "format": str,
    }

    def __init__(self, state, options):
        self._state = state
        self._options = options

    def render_restructuredtext_markup(self, spec):

        utils.normalize_spec(spec, **self._options)

        convert = utils.get_text_converter(self._options)
        if 'info' in spec:
            if 'description' in spec['info']:
                for line in convert(spec['info']['description']).splitlines():
                    yield '{line}'.format(**locals())
                yield ''
