from __future__ import print_function
"""
Powa main application.
"""
import os
import re

__VERSION__ = '4.1.1'

ver_tmp = re.sub("(alpha|beta)[0-9]*", "", __VERSION__)
__VERSION_NUM__ = [int(part) for part in (ver_tmp.split('.'))]

POWA_ROOT = os.path.dirname(__file__)

from tornado.web import Application, URLSpec as U
from powa.options import parse_options
from tornado.options import options
from powa import ui_modules, ui_methods
from powa.framework import AuthHandler
from powa.user import LoginHandler, LogoutHandler
from powa.overview import Overview
from powa.server import ServerSelector, ServerOverview
from powa.database import DatabaseSelector, DatabaseOverview
from powa.query import QueryOverview
from powa.qual import QualOverview
from powa.config import RepositoryConfigOverview, RemoteConfigOverview
from powa.collector import CollectorReloadHandler
from powa.wizard import IndexSuggestionHandler


class IndexHandler(AuthHandler):
    """
    Handler for the main page.
    """

    def get(self):
        return self.redirect(options.index_url)


def make_app(**kwargs):
    """
    Parse the config file and instantiate a tornado app.
    """
    parse_options()

    URLS = [
        U(r"%slogin/" % options.url_prefix, LoginHandler, name="login"),
        U(r"%slogout/" % options.url_prefix, LogoutHandler, name="logout"),
        U(r"%sreload_collector/" % options.url_prefix, CollectorReloadHandler,
          name="reload_collector"),
        U(r"%sserver/select" % options.url_prefix, ServerSelector,
          name="server_selector"),
        U(r"%sdatabase/select" % options.url_prefix, DatabaseSelector,
          name="database_selector"),
        U(r"%s" % options.url_prefix, IndexHandler, name="index"),
        U(r"%sserver/(\d+)/database/([^\/]+)/suggest/" % options.url_prefix,
          IndexSuggestionHandler, name="index_suggestion")
    ]

    for dashboard in (Overview,
                      ServerOverview,
                      DatabaseOverview,
                      QueryOverview,
                      QualOverview,
                      RepositoryConfigOverview,
                      RemoteConfigOverview):
        URLS.extend(dashboard.url_specs(options.url_prefix))

    _cls = Application
    if 'legacy_wsgi' in kwargs:
        from tornado.wsgi import WSGIApplication
        _cls = WSGIApplication

    return _cls(
        URLS,
        ui_modules=ui_modules,
        ui_methods=ui_methods,
        login_url=("%slogin/" % options.url_prefix),
        static_path=os.path.join(POWA_ROOT, "static"),
        static_url_prefix=("%sstatic/" % options.url_prefix),
        cookie_secret=options.cookie_secret,
        template_path=os.path.join(POWA_ROOT, "templates"),
        **kwargs)
