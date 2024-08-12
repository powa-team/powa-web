import os
import sys
from tornado.options import (
    Error,
    define,
    options,
    parse_command_line,
    parse_config_file,
)

SAMPLE_CONFIG_FILE = """
servers={
  'main': {
    'host': 'localhost',
    'port': '5432',
    'database': 'powa'
  }
}
cookie_secret="SUPERSECRET_THAT_YOU_SHOULD_CHANGE"
"""

CONF_LOCATIONS = [
    "/etc/powa-web.conf",
    os.path.expanduser("~/.config/powa-web.conf"),
    os.path.expanduser("~/.powa-web.conf"),
    "./powa-web.conf",
]


define("cookie_secret", type=str, help="Secret key for cookies")
define(
    "cookie_expires_days",
    type=int,
    default=30,
    help="Cookie retention in days",
)
define("port", type=int, default=8888, metavar="port", help="Listen on <port>")
define(
    "address",
    type=str,
    default="0.0.0.0",
    metavar="address",
    help="Listen on <address>",
)
define("config", type=str, help="path to config file")
define("url_prefix", type=str, help="optional prefix URL", default="/")
define(
    "allow_ui_connection",
    type=bool,
    help="Allow UI to connect to databases",
    default=True,
)
define("certfile", type=str, help="Path to certificate file", default=None)
define("keyfile", type=str, help="Path to key file", default=None)


def parse_file(filepath):
    try:
        parse_config_file(filepath)
    except IOError:
        pass
    except Error as e:
        print("Error parsing config file %s:" % filepath)
        print("\t%s" % e)
        sys.exit(-1)


def parse_options():
    define("servers", type=dict, help="Not available from the command line.")
    for possible_config in CONF_LOCATIONS:
        parse_file(possible_config)
    try:
        parse_command_line()
        if options.config:
            parse_file(options.config)
    except Error as e:
        print("Error parsing command line options:")
        print("\t%s" % e)
        sys.exit(1)

    for key in ("servers", "cookie_secret"):
        if getattr(options, key, None) is None:
            print(
                "You should define a server and cookie_secret in your "
                "configuration file."
            )
            print(
                "Place and adapt the following content in one of those "
                "locations:"
                ""
            )
            print("\n\t".join([""] + CONF_LOCATIONS))
            print(SAMPLE_CONFIG_FILE)
            sys.exit(-1)

    if getattr(options, "url_prefix", "") == "":
        setattr(options, "url_prefix", "/")
    elif getattr(options, "url_prefix", "/") != "/":
        prefix = getattr(options, "url_prefix", "/")
        if prefix[0] != "/":
            prefix = "/" + prefix
        if prefix[-1] != "/":
            prefix = prefix + "/"
        setattr(options, "url_prefix", prefix)
    define(
        "index_url",
        type=str,
        default="%sserver/" % getattr(options, "url_prefix", "/"),
    )

    # we used to expect a field named "username", so accept "username" as an
    # alias for "user"
    for key, conf in getattr(options, "servers", {}).items():
        if "username" in conf.keys():
            conf["user"] = conf["username"]
            del conf["username"]
