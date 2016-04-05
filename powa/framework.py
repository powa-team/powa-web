"""
Utilities for the basis of Powa
"""
from tornado.web import RequestHandler, authenticated, HTTPError
from powa import ui_methods
from powa.json import to_json
from sqlalchemy import create_engine, text
from sqlalchemy.engine.url import URL
from tornado.options import options
import pickle
import logging


class BaseHandler(RequestHandler):
    """
    Subclass of Tornado RequestHandler adding a bunch
    of utility methods.
    """

    def __init__(self, *args, **kwargs):
        super(BaseHandler, self).__init__(*args, **kwargs)
        self.flashed_messages = {}
        self._databases = None
        self._connections = {}
        self.logger = logging.getLogger("tornado.application")

    def render_json(self, value):
        """
        Render the object as json response.
        """
        self.set_header('Content-Type', 'application/json')
        self.write(to_json(value))

    @property
    def current_user(self):
        """
        Return the current_user if he is allowed to connect
        to his server of choice.
        """
        raw = self.get_str_cookie('username')
        if raw is not None:
            try:
                self.connect()
                return raw or 'anonymous'
            except:
                return None

    @property
    def current_server(self):
        """
        Return the server connected to if any
        """
        return self.get_secure_cookie('server')

    @property
    def current_connection(self):
        """
        Return the host and port connected to if any
        """
        server = self.current_server.decode('utf8')
        if server is None:
            return None
        connoptions = options.servers[server].copy()
        host = "localhost"
        port = "5432"
        if 'host' in connoptions:
            host = connoptions['host']
        if 'port' in connoptions:
            port = connoptions['port']
        return "%s:%s" % ( host, port )

    @property
    def menu(self):
        return None

    @property
    def database(self):
        """Return the current database."""
        return None

    def get_powa_version(self, **kwargs):
        version = self.execute(text(
            """
            SELECT extversion FROM pg_extension WHERE extname = 'powa'
            """), **kwargs).scalar()
        if version is None:
            return None
        return [int(part) for part in version.split('.')]

    @property
    def databases(self, **kwargs):
        """
        Return the list of databases in this instance.
        """
        if self.current_user:
            if self._databases is None:
                self._databases = [d[0] for d in self.execute(
                    """
                    SELECT p.datname
                    FROM powa_databases p
                    LEFT JOIN pg_database d ON p.oid = d.oid
                    WHERE COALESCE(datallowconn, true)
                    ORDER BY DATNAME
                    """,
                    **kwargs)]
            return self._databases

    def on_finish(self):
        for engine in self._connections.values():
            engine.dispose()

    def connect(self, server=None, username=None, password=None,
                database=None, **kwargs):
        """
        Connect to a specific database.
        Parameters default values are taken from the cookies and the server
        configuration file.
        """
        server = server or self.get_str_cookie('server')
        username = username or self.get_str_cookie('username')
        password = (password or
                    self.get_str_cookie('password'))
        if server not in options.servers:
            raise HTTPError(404)
        connoptions = options.servers[server].copy()
        if 'username' not in connoptions:
            connoptions['username'] = username
        if 'password' not in connoptions:
            connoptions['password'] = password
        if database is not None:
            connoptions['database'] = database
        #engineoptions = {'_initialize': False}
        engineoptions = {}
        engineoptions.update(**kwargs)
        if self.application.settings['debug']:
            engineoptions['echo'] = True
        url = URL("postgresql+psycopg2", **connoptions)
        if url in self._connections:
            return self._connections.get(url)
        engine = create_engine(url, **engineoptions)
        engine.connect()
        self._connections[url] = engine
        return engine

    def has_extension(self, extname, database=None):
        """
        Returns the version of the specific extension on the specific database,
        or None if the extension is not installed.
        """
        try:
            extversion = self.execute(text(
                """
                SELECT extversion FROM pg_extension WHERE extname = :extname LIMIT 1
                """), database=database, params={"extname": extname}).scalar()
        except Exception:
            return None

        return extversion

    def write_error(self, status_code, **kwargs):
        if status_code == 403:
            self._status_code = status_code
            self.clear_all_cookies()
            self.flash("Authentification failed", "alert")
            self.render("login.html", title="Login")
            return
        if status_code == 501:
            self._status_code = status_code
            self.render("xhr.html", content=kwargs["exc_info"][1].log_message)
            return
        super(BaseHandler, self).write_error(status_code, **kwargs)

    def execute(self, query, params=None, server=None, username=None,
                database=None,
                password=None):
        """
        Execute a query against a database, with specific bind parameters.
        """
        if params is None:
            params = {}
        engine = self.connect(server, username, password, database)
        return engine.execute(query, **params)

    def get_pickle_cookie(self, name):
        """
        Deserialize a cookie value using the pickle protocol.
        """
        value = self.get_secure_cookie(name)
        if value:
            try:
                return pickle.loads(value)
            except:
                self.clear_all_cookies()

    def get_str_cookie(self, name, default=None):
        value = self.get_secure_cookie(name)
        if value is not None:
            return value.decode('utf8')
        return default

    def set_pickle_cookie(self, name, value):
        """
        Serialize a cookie value using the pickle protocol.
        """
        self.set_secure_cookie(name, pickle.dumps(value))

    flash = ui_methods.flash
    reverse_url_with_params = ui_methods.reverse_url_with_params


class AuthHandler(BaseHandler):
    """
    Base handler for urls needing authentifications.
    """

    @authenticated
    def prepare(self):
        super(AuthHandler, self).prepare()
