__VERSION__ = '0.0.1'

from tornado.web import Application, URLSpec as U
from tornado.options import define, parse_config_file
from powa import ui_modules, ui_methods

from powa.user import *
from powa.overview import *
from powa.database import *
from powa.query import *

class IndexHandler(AuthHandler):

    def get(self):
        return self.redirect("/overview/")


URLS = [
    U(r"/login/", LoginHandler, name="login"),
    U(r"/logout/", LogoutHandler, name="logout"),
    U(r"/database/select", DatabaseSelector, name="database_selector"),
    U(r"/database/(\w+)/query/(\w+)/indexes", QueryIndexes, name="QueryIndexes"),
    U(r"/", IndexHandler, name="index")
]



for dashboard in (Overview,
                  DatabaseOverview,
                  QueryOverview):
    URLS.extend(dashboard.url_specs())


def make_app(**kwargs):
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
