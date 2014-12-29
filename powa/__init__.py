"""
Powa main application.
"""

__VERSION__ = '0.0.1'

from tornado.web import Application, URLSpec as U
from tornado.options import define, parse_config_file
from powa import ui_modules, ui_methods
from powa.framework import AuthHandler
from powa.user import LoginHandler, LogoutHandler
from powa.overview import Overview
from powa.database import DatabaseSelector, DatabaseOverview
from powa.query import QueryOverview

class IndexHandler(AuthHandler):
    """
    Handler for the main page.
    """

    def get(self):
        return self.redirect("/overview/")


URLS = [
    U(r"/login/", LoginHandler, name="login"),
    U(r"/logout/", LogoutHandler, name="logout"),
    U(r"/database/select", DatabaseSelector, name="database_selector"),
    U(r"/", IndexHandler, name="index")
]



for dashboard in (Overview,
                  DatabaseOverview,
                  QueryOverview):
    URLS.extend(dashboard.url_specs())


def make_app(**kwargs):
    """
    Parse the config file and instantiate a tornado app.
    """
    define("servers", type=dict)
    parse_config_file("powa.conf")
    return Application(
        URLS,
        ui_modules=ui_modules,
        ui_methods=ui_methods,
        login_url="/login/",
        static_path="powa/static",
        cookie_secret="kaljlkdjqlk",
        template_path="powa/templates",
        **kwargs)
