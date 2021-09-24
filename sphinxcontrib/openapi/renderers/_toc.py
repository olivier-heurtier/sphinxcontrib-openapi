
import re
from . import abc
from .. import utils


class TocRenderer(abc.RestructuredTextRenderer):

    option_spec = {
        # nb columns
    }

    def __init__(self, state, options):
        self._state = state
        self._options = options

    def render_restructuredtext_markup(self, spec):

        utils.normalize_spec(spec, **self._options)

        yield ""
        yield ".. hlist::"
        yield "    :columns: 2"
        yield ""

        for path in spec["paths"].keys():
            cpath = re.sub(r"[{}]", "", re.sub(r"[<>:/]", "-", path))
            for verb, ope in spec["paths"][path].items():
                yield "    - `{} <#{}>`_".format(
                    ope.get("operationId", verb + " " + path),
                    verb.lower() + "-" + cpath
                )
        yield ""
