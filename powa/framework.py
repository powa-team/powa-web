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
        raw = self.get_secure_cookie('username')
        if raw:
            user = raw.decode('utf8')
            try:
                self.connect()
                return user
            except Exception as _:
                return None

    @property
    def menu(self):
        return None

    @property
    def database(self):
        """Return the current database."""
        return None

    @property
    def databases(self, **kwargs):
        """
        Return the list of databases in this instance.
        """
        if self.current_user:
            if self._databases is None:
                self._databases = [d[0] for d in self.execute(
                    "SELECT datname FROM pg_database WHERE datallowconn ORDER BY DATNAME",
                    **kwargs)]
            return self._databases

    def on_finish(self):
        for engine in self._connections.values():
            engine.dispose()

    def connect(self, server=None, username=None, password=None,
                database=None):
        """
        Connect to a specific database.
        Parameters default values are taken from the cookies and the server
        configuration file.
        """
        server = server or self.get_secure_cookie('server').decode('utf8')
        username = username or self.get_secure_cookie('username').decode('utf8')
        password = (password or
                    self.get_secure_cookie('password').decode('utf8'))
        if server not in options.servers:
            raise HTTPError(404)
        connoptions = options.servers[server].copy()
        connoptions['username'] = username
        connoptions['password'] = password
        if database is not None:
            connoptions['database'] = database
        engineoptions = {'_initialize': False}
        if self.application.settings['debug']:
            engineoptions['echo'] = True
        url = URL("postgresql+psycopg2", **connoptions)
        if url in self._connections:
            return self._connections.get(url)
        engine = create_engine(url, **engineoptions)
        engine.connect()
        self._connections[url] = engine
        return engine

    def has_extension(self, extname):
        """
        Returns whether the database has the specific extension installed.
        """
        return self.execute(text(
            """
            SELECT true FROM pg_extension WHERE extname = :extname
            """), params={"extname": extname}).rowcount > 0

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
            return pickle.loads(value)

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
