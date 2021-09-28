"""
    sphinxcontrib.openapi
    ---------------------

    The OpenAPI spec renderer for Sphinx. It's a new way to document your
    RESTful API. Based on ``sphinxcontrib-httpdomain``.

    :copyright: (c) 2016, Ihor Kalnytskyi.
    :license: BSD, see LICENSE for details.
"""

from pkg_resources import get_distribution, DistributionNotFound
from sphinxcontrib.openapi import renderers, directive
from sphinx.domains import Domain
import yaml
from docutils import nodes

try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
    # package is not installed
    __version__ = None


_DEFAULT_RENDERER_NAME = "httpdomain:old"


def oasversion_role(typ, rawtext, text, lineno, inliner, options={}, content=[]):
    fn = text
    env = inliner.document.settings.env
    rel_fn, fn = env.relfn2path(fn)
    y = yaml.load(open(fn, 'r').read(), Loader=yaml.FullLoader)
    s = y['info']['version']
    retnode = nodes.inline(text=s, role=typ.lower(), classes=[typ])
    return [retnode], []


class OpenAPIDomain(Domain):
    name = 'openapi'
    label = 'OpenAPI Documentation'

    directives = {
        'httpdomain:old': directive.create_directive_from_renderer(
            renderers.HttpdomainOldRenderer),
        'httpdomain': directive.create_directive_from_renderer(renderers.HttpdomainRenderer),
        'model': directive.create_directive_from_renderer(renderers.ModelRenderer),
        'toc': directive.create_directive_from_renderer(renderers.TocRenderer),
    }

    roles = {
        'version': oasversion_role
    }


def setup(app):
    app.add_config_value("openapi_default_renderer", _DEFAULT_RENDERER_NAME, "html")
    app.add_config_value("openapi_renderers", {}, "html")

    from sphinxcontrib import httpdomain

    for idx, fieldtype in enumerate(httpdomain.HTTPResource.doc_field_types):
        if fieldtype.name == 'requestheader':
            httpdomain.HTTPResource.doc_field_types[idx] = httpdomain.TypedField(
                fieldtype.name,
                label=fieldtype.label,
                names=fieldtype.names,
                typerolename='header',
                typenames=('reqheadertype', ),
            )

        if fieldtype.name == 'responseheader':
            httpdomain.HTTPResource.doc_field_types[idx] = httpdomain.TypedField(
                fieldtype.name,
                label=fieldtype.label,
                names=fieldtype.names,
                typerolename='header',
                typenames=('resheadertype', ),
            )

    app.setup_extension("sphinxcontrib.httpdomain")
    app.add_domain(OpenAPIDomain)
    app.add_directive(
        "openapi",
        directive.create_directive_from_renderer(renderers.HttpdomainOldRenderer)
    )

    return {"version": __version__, "parallel_read_safe": True}
