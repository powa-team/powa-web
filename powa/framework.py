from tornado.web import RequestHandler, authenticated, HTTPError
from powa import ui_methods
from powa.json import to_json
from sqlalchemy import create_engine, text
from sqlalchemy.engine.url import URL
from tornado.options import options
import pickle


class BaseHandler(RequestHandler):

    def __init__(self, *args, **kwargs):
        super(BaseHandler, self).__init__(*args, **kwargs)
        self._flashed_messages = {}
        self._databases = None
        self._connections = {}

    def render_json(self, value):
        self.set_header('Content-Type', 'application/json')
        self.write(to_json(value))

    @property
    def current_user(self):
        raw = self.get_secure_cookie('username')
        if raw:
            user = raw.decode('utf8')
            try:
                self.connect()
                return user
            except Exception as e:
                return None

    @property
    def database(self):
        return self.get_secure_cookie("database")

    @database.setter
    def database_setter(self, dbname):
        return self.set_secure_cookie("database", dbname)

    @property
    def databases(self, **kwargs):
        if self.current_user:
            if self._databases is None:
                self._databases = self.execute(
                "SELECT datname FROM pg_database ORDER BY DATNAME",
                **kwargs)
            return [d[0] for d in self._databases]

    def connect(self, server=None, username=None, password=None):
        server = server or self.get_secure_cookie('server').decode('utf8')
        username = username or self.get_secure_cookie('username').decode('utf8')
        password = (password or
                    self.get_secure_cookie('password').decode('utf8'))
        if server not in options.servers:
            raise HTTPError(403)
        connoptions = options.servers[server].copy()
        connoptions['username'] = username
        connoptions['password'] = password
        engineoptions = {'_initialize': False}
        if self.application.settings['debug']:
            engineoptions['echo'] = True
        url = URL("postgresql+psycopg2", **connoptions)
        if url in self._connections:
            return self._connections.get(url)
        try:
            engine = create_engine(url, **engineoptions)
            engine.connect()
            self._connections[url] = engine
            return engine
        except Exception as e:
            raise HTTPError(403)

    def has_extension(self, extname):
        return self.execute(text(
            """
            SELECT true FROM pg_extension WHERE extname = :extname
            """), params={"extname": extname}).rowcount > 0

    def write_error(self, status_code, **kwargs):
        if status_code == 403:
            self.clear_all_cookies()
            self.flash("Authentification failed", "alert")
            self.render("login.html", title="Login")
            return
        super(BaseHandler, self).write_error(status_code, **kwargs)

    def execute(self, query, params=None, server=None, username=None,
                password=None):
        if params is None:
            params = {}
        engine = self.connect(server, username, password)
        return engine.execute(query, **params)

    def get_pickle_cookie(self, name):
        value = self.get_secure_cookie(name)
        if value:
            return pickle.loads(value)

    def set_pickle_cookie(self, name, value):
        self.set_secure_cookie(name, pickle.dumps(value))

    flash = ui_methods.flash


class AuthHandler(BaseHandler):

    @authenticated
    def prepare(self):
        pass
