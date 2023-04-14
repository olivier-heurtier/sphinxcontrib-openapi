
import re
from urllib.parse import urlparse

from . import abc
from .. import utils
from docutils.parsers.rst import directives


class TocRenderer(abc.RestructuredTextRenderer):

    option_spec = {
        # nb columns
        "nb_columns": directives.positive_int,
        "contextpath": directives.flag,     # use the server path as prefix in service URL
    }

    def __init__(self, state, options):
        self._state = state
        self._options = options
        if 'nb_columns' not in self._options:
            self._options["nb_columns"] = 2

    def render_restructuredtext_markup(self, spec):

        utils.normalize_spec(spec, **self._options)

        contextpath = ''
        if 'contextpath' in self._options:
            if 'servers' in spec:
                h = spec['servers'][0]['url']
                contextpath = urlparse(h).path
                if contextpath and contextpath[-1] == '/':
                    contextpath = contextpath[:-1]

        yield ""
        yield ".. hlist::"
        yield "    :columns: {}".format(self._options["nb_columns"])
        yield ""

        for path in spec["paths"].keys():
            cpath = re.sub(r"[{}]", "", re.sub(r"[<>:/]", "-", contextpath+path))
            for verb, ope in spec["paths"][path].items():
                yield "    - `{} <#{}>`_".format(
                    ope.get("operationId", verb + " " + path),
                    verb.lower() + "-" + cpath
                )
        yield ""
