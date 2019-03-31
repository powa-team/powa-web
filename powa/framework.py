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
import select
import random


class BaseHandler(RequestHandler):
    """
    Subclass of Tornado RequestHandler adding a bunch
    of utility methods.
    """

    def __init__(self, *args, **kwargs):
        super(BaseHandler, self).__init__(*args, **kwargs)
        self.flashed_messages = {}
        self._databases = None
        self._servers = None
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
            except Exception:
                return None

    @property
    def current_server(self):
        """
        Return the server connected to if any
        """
        return self.get_secure_cookie('server')

    @property
    def current_host(self):
        """
        Return the host connected to if any
        """
        server = self.current_server.decode('utf8')
        if server is None:
            return None
        connoptions = options.servers[server].copy()
        host = "localhost"
        if 'host' in connoptions:
            host = connoptions['host']
        return "%s" % (host)

    @property
    def current_port(self):
        """
        Return the port connected to if any
        """
        server = self.current_server.decode('utf8')
        if server is None:
            return None
        connoptions = options.servers[server].copy()
        port = "5432"
        if 'port' in connoptions:
            port = connoptions['port']
        return "%s" % (port)

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
    def database(self):
        """Return the current database."""
        return None

    def get_powa_version(self, **kwargs):
        version = self.execute(text(
            """
            SELECT replace(extversion, 'dev', '') FROM pg_extension WHERE extname = 'powa'
            """), **kwargs).scalar()
        if version is None:
            return None
        return [int(part) for part in version.split('.')]

    def get_pg_version_num(self, **kwargs):
        return int(self.execute(text(
            """
            SELECT setting FROM pg_settings WHERE name = 'server_version_num'
            """), **kwargs).scalar())

    def get_databases(self, srvid):
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
                    AND srvid = %(srvid)s
                    ORDER BY DATNAME
                    """, params={'srvid': srvid})]
            return self._databases

    def deparse_srvid(self, srvid):
        if (srvid == '0'):
            return self.current_connection
        else:
            return self.execute("""
                                   SELECT hostname || ':' || port
                                   FROM powa_servers
                                   WHERE id = %(srvid)s
                                   """, params={'srvid': int(srvid)}
                                ).scalar()

    @property
    def servers(self, **kwargs):
        """
        Return the list of servers.
        """
        if self.current_user:
            if self._servers is None:
                self._servers = [[s[0], s[1]] for s in self.execute(
                    """
                    SELECT s.id, CASE WHEN s.id = 0 THEN
                        %(default)s
                    ELSE
                        s.hostname || ':' || s.port
                    END
                    FROM powa_servers s
                    ORDER BY hostname
                    """, params={'default': self.current_connection})]
            return self._servers

    def on_finish(self):
        for engine in self._connections.values():
            engine.dispose()

    def connect(self, srvid=None, server=None, username=None, password=None,
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

        if (srvid is not None and srvid != "0"):
            tmp = self.connect()
            rows = tmp.execute("""
            SELECT hostname, port, username, password, dbname
            FROM powa_servers WHERE id = %(srvid)s
            """, {'srvid': srvid})
            row = rows.fetchone()
            rows.close()

            connoptions['host'] = row[0]
            connoptions['port'] = row[1]
            connoptions['username'] = row[2]
            connoptions['password'] = row[3]
            connoptions['database'] = row[4]
        else:
            if 'username' not in connoptions:
                connoptions['username'] = username
            if 'password' not in connoptions:
                connoptions['password'] = password

        if database is not None:
            connoptions['database'] = database
        # engineoptions = {'_initialize': False}
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

    def has_extension(self, srvid, extname, database=None):
        """
        Returns the version of the specific extension on the specific server
        and database, or None if the extension is not installed.
        """
        try:
            extversion = self.execute(text(
                """
                SELECT extversion
                FROM pg_extension
                WHERE extname = :extname
                LIMIT 1
                """), srvid=srvid, database=database,
                params={"extname": extname}).scalar()
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

    def execute(self, query, srvid=None, params=None, server=None,
                username=None,
                database=None,
                password=None):
        """
        Execute a query against a database, with specific bind parameters.
        """
        if params is None:
            params = {}

        engine = self.connect(srvid, server, username, password, database)
        return engine.execute(query, **params)

    def notify_collector(self, command, args=[], timeout=3):
        """
        Notify powa-collector and get its answer.
        """
        engine = self.connect()

        conn = engine.connect()
        trans = conn.begin()

        # we shouldn't listen on anything else than our own channel, but just
        # in case discard everything
        conn.execute("UNLISTEN *")

        random.seed()
        channel = "r%d" % random.randint(1, 99999)
        conn.execute("LISTEN %s" % channel)
        conn.execute("NOTIFY powa_collector, '%s %s %s'" %
                     (command, channel, ' '.join(args)))
        trans.commit()

        # wait for activity on the connection up to given timeout
        select.select([conn.connection], [], [], timeout)

        trans = conn.begin()
        # we shouldn't listen on anything else than our own channel, but just
        # in case discard everything
        conn.execute("UNLISTEN *")
        trans.commit()

        conn.connection.poll()
        res = []
        while (conn.connection.notifies):
            notif = conn.connection.notifies.pop(0)

            payload = notif.payload.split(' ')

            received_command = payload.pop(0)
            # we shouldn't received unexpected messages, but ignore them if any
            if (received_command != command):
                continue

            status = payload.pop(0)
            payload = ' '.join(payload)

            # we should get a single answer, but if multiple are received
            # append them and let the caller handle it.
            res.append({status: payload})

        return res

    def get_pickle_cookie(self, name):
        """
        Deserialize a cookie value using the pickle protocol.
        """
        value = self.get_secure_cookie(name)
        if value:
            try:
                return pickle.loads(value)
            except Exception:
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
