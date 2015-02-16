from __future__ import print_function
"""
Powa main application.
"""

__VERSION__ = '0.0.4'

from tornado.web import Application, URLSpec as U
from tornado.options import define, parse_config_file, options
from powa import ui_modules, ui_methods
from powa.framework import AuthHandler
from powa.user import LoginHandler, LogoutHandler
from powa.overview import Overview
from powa.database import DatabaseSelector, DatabaseOverview
from powa.query import QueryOverview
from powa.qual import QualOverview
from powa.config import ConfigOverview
import os
import sys

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
                  QueryOverview,
                  QualOverview,
                  ConfigOverview):
    URLS.extend(dashboard.url_specs())


POWA_ROOT = os.path.dirname(__file__)
CONF_LOCATIONS=['/etc/powa-web.conf',
        os.path.expanduser('~/.config/powa-web.conf'),
        os.path.expanduser('~/.powa-web.conf'),
        './powa-web.conf']


SAMPLE_CONFIG_FILE="""
servers={
  'main': {
    'host': 'localhost',
    'port': '5432',
    'database': 'powa'
  }
}
cookie_secret="SUPERSECRET_THAT_YOU_SHOULD_CHANGE"
"""

def make_app(**kwargs):
    """
    Parse the config file and instantiate a tornado app.
    """
    define("servers", type=dict)
    define("cookie_secret", type=str)
    for possible_config in CONF_LOCATIONS:
        try:
            parse_config_file(possible_config)
        except Exception as e:
            pass
    for key in ('servers', 'cookie_secret'):
        if getattr(options, key, None) is None:
            print("You should define a server and cookie_secret in your configuration file.")
            print("""Place and adapt the following content in one of those locations:""")
            print("\n\t".join([""] + CONF_LOCATIONS))
            print(SAMPLE_CONFIG_FILE)
            sys.exit(-1)

    return Application(
        URLS,
        ui_modules=ui_modules,
        ui_methods=ui_methods,
        login_url="/login/",
        static_path=os.path.join(POWA_ROOT, "static"),
        cookie_secret=options.cookie_secret,
        template_path=os.path.join(POWA_ROOT,  "templates"),
        **kwargs)
