"""
Powa main application.
"""

import os
import re

__VERSION__ = "5.0.1"

ver_tmp = re.sub("(alpha|beta|dev)[0-9]*", "", __VERSION__)
__VERSION_NUM__ = [int(part) for part in (ver_tmp.split("."))]

POWA_ROOT = os.path.dirname(__file__)

# Import from powa.options must go before tornado.options
from powa.options import parse_options  # noqa: I001
from tornado.options import options
from tornado.web import Application
from tornado.web import URLSpec as U

from powa import ui_methods, ui_modules
from powa.collector import (
    CollectorDbCatRefreshHandler,
    CollectorForceSnapshotHandler,
    CollectorReloadHandler,
)
from powa.config import (
    RemoteConfigOverview,
    RepositoryConfigOverview,
)
from powa.database import DatabaseOverview, DatabaseSelector
from powa.framework import AuthHandler
from powa.function import FunctionOverview
from powa.io import (
    ByBackendTypeIoOverview,
    ByContextIoOverview,
    ByObjIoOverview,
)
from powa.overview import Overview
from powa.qual import QualOverview
from powa.query import QueryOverview
from powa.server import ServerOverview, ServerSelector
from powa.slru import ByNameSlruOverview
from powa.user import LoginHandler, LogoutHandler
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
        U(rf"{options.url_prefix}login/", LoginHandler, name="login"),
        U(rf"{options.url_prefix}logout/", LogoutHandler, name="logout"),
        U(
            rf"{options.url_prefix}reload_collector/",
            CollectorReloadHandler,
            name="reload_collector",
        ),
        U(
            rf"{options.url_prefix}force_snapshot/(\d+)",
            CollectorForceSnapshotHandler,
            name="force_snapshot",
        ),
        U(
            rf"{options.url_prefix}refresh_db_cat/",
            CollectorDbCatRefreshHandler,
            name="refresh_db_cat",
        ),
        U(
            rf"{options.url_prefix}server/select",
            ServerSelector,
            name="server_selector",
        ),
        U(
            rf"{options.url_prefix}database/select",
            DatabaseSelector,
            name="database_selector",
        ),
        U(rf"{options.url_prefix}", IndexHandler, name="index"),
        U(
            rf"{options.url_prefix}server/(\d+)/database/([^\/]+)/suggest/",
            IndexSuggestionHandler,
            name="index_suggestion",
        ),
    ]

    for dashboard in (
        Overview,
        ServerOverview,
        DatabaseOverview,
        QueryOverview,
        QualOverview,
        FunctionOverview,
        RepositoryConfigOverview,
        RemoteConfigOverview,
        ByBackendTypeIoOverview,
        ByObjIoOverview,
        ByContextIoOverview,
        ByNameSlruOverview,
    ):
        URLS.extend(dashboard.url_specs(options.url_prefix))

    _cls = Application
    if "legacy_wsgi" in kwargs:
        from tornado.wsgi import WSGIApplication

        _cls = WSGIApplication

    return _cls(
        URLS,
        ui_modules=ui_modules,
        ui_methods=ui_methods,
        login_url=(f"{options.url_prefix}login/"),
        static_path=os.path.join(POWA_ROOT, "static"),
        static_url_prefix=(f"{options.url_prefix}static/"),
        cookie_secret=options.cookie_secret,
        template_path=os.path.join(POWA_ROOT, "templates"),
        **kwargs,
    )
