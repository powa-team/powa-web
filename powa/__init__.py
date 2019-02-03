from __future__ import print_function
"""
Powa main application.
"""
import os
import re

__VERSION__ = '4.0.0beta1'

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
from powa.wizard import IndexSuggestionHandler


class IndexHandler(AuthHandler):
    """
    Handler for the main page.
    """

    def get(self):
        return self.redirect(options.index_url)


URLS = [
    U(r"/login/", LoginHandler, name="login"),
    U(r"/logout/", LogoutHandler, name="logout"),
    U(r"/server/select", ServerSelector, name="server_selector"),
    U(r"/database/select", DatabaseSelector, name="database_selector"),
    U(r"/", IndexHandler, name="index"),
    U(r"/server/(\d+)/database/([^\/]+)/suggest/", IndexSuggestionHandler,
      name="index_suggestion")
]


for dashboard in (Overview,
                  ServerOverview,
                  DatabaseOverview,
                  QueryOverview,
                  QualOverview,
                  RepositoryConfigOverview,
                  RemoteConfigOverview):
    URLS.extend(dashboard.url_specs())


def make_app(**kwargs):
    """
    Parse the config file and instantiate a tornado app.
    """
    parse_options()
    _cls = Application
    if 'legacy_wsgi' in kwargs:
        from tornado.wsgi import WSGIApplication
        _cls = WSGIApplication

    return _cls(
        URLS,
        ui_modules=ui_modules,
        ui_methods=ui_methods,
        login_url="/login/",
        static_path=os.path.join(POWA_ROOT, "static"),
        cookie_secret=options.cookie_secret,
        template_path=os.path.join(POWA_ROOT, "templates"),
        **kwargs)
