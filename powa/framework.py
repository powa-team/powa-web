"""
Utilities for the basis of Powa
"""

import logging
import pickle
import psycopg2
import random
import re
import select
import time
from collections import defaultdict
from powa import ui_methods
from powa.json import JSONizable, to_json
from psycopg2.extensions import connection as _connection
from psycopg2.extensions import cursor as _cursor
from psycopg2.extras import RealDictCursor
from tornado.options import options
from tornado.web import HTTPError, RequestHandler, authenticated


class CustomConnection(_connection):
    """
    Custom psycopg2 connection class that takes care of expanding extension
    schema and optionally logs various information at debug level, both on
    successful execution and in case of error.

    Supports either plain cursor (through CustomCursor) or RealDictCursor
    (through CustomDictCursor).

    Before execution, and if a _nsps object is found cached in the connection,
    the query will be formatted using this _nsps dict, which contains a list of
    extension_name -> escaped_schema_name mapping.
    All you need to do is pass query strings of the form
    SELECT ... FROM {extension_name}.some_relation ...
    """

    def initialize(self, logger, srvid, dsn, encoding_query, debug):
        self._logger = logger
        self._srvid = srvid or 0
        self._dsn = dsn
        self._debug = debug

        if encoding_query is not None:
            self.set_client_encoding(encoding_query["client_encoding"])

    def cursor(self, *args, **kwargs):
        factory = kwargs.get("cursor_factory")

        if factory is None:
            kwargs["cursor_factory"] = CustomCursor
        elif factory == RealDictCursor:
            kwargs["cursor_factory"] = CustomDictCursor
        else:
            msg = "Unsupported cursor_factory: %s" % factory.__name__
            self._logger.error(msg)
            raise Exception(msg)

        return _connection.cursor(self, *args, **kwargs)


class CustomDictCursor(RealDictCursor):
    def execute(self, query, params=None):
        query = resolve_nsps(query, self.connection)

        self.timestamp = time.time()
        try:
            return super(CustomDictCursor, self).execute(query, params)
        except Exception as e:
            log_query(self, query, params, e)
            raise e
        finally:
            log_query(self, query, params)


class CustomCursor(_cursor):
    def execute(self, query, params=None):
        query = resolve_nsps(query, self.connection)

        self.timestamp = time.time()
        try:
            return super(CustomCursor, self).execute(query, params)
        except Exception as e:
            log_query(self, query, params, e)
        finally:
            log_query(self, query, params)


def resolve_nsps(query, connection):
    try:
        if hasattr(connection, "_nsps"):
            return query.format(**connection._nsps)
    except KeyError as e:
        raise Exception("Extension not found: " + e.args[0])

    return query


def log_query(cls, query, params=None, exception=None):
    t = round((time.time() - cls.timestamp) * 1000, 2)

    fmt = ""
    if exception is not None:
        fmt = "Error during query execution:\n{}\n".format(exception)

    fmt += "query on {dsn} (srvid {srvid}): {ms} ms\n{query}"
    if params is not None:
        fmt += "\n{params}"

    cls.connection._logger.debug(
        fmt.format(
            ms=t,
            query=query,
            params=params,
            dsn=cls.connection._dsn,
            srvid=cls.connection._srvid,
        )
    )


class BaseHandler(RequestHandler, JSONizable):
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
        self._ext_versions = defaultdict(lambda: defaultdict(dict))
        self.url_prefix = options.url_prefix
        self.logger = logging.getLogger("tornado.application")
        if self.application.settings["debug"]:
            self.logger.setLevel(logging.DEBUG)

    def __get_url(self, **connoptions):
        url = " ".join(
            [
                "%s=%s" % (k, v)
                for (k, v) in connoptions.items()
                if v is not None
            ]
        )

        return url

    def __get_safe_dsn(self, **connoptions):
        """
        Return a simplified dsn that won't leak the password if provided in the
        options, for logging purpose.
        """
        dsn = "{user}@{host}:{port}/{database}".format(**connoptions)
        return dsn

    def render_json(self, value):
        """
        Render the object as json response.
        """
        self.set_header("Content-Type", "application/json")
        self.write(to_json(value))

    @property
    def current_user(self):
        """
        Return the current_user if he is allowed to connect
        to his server of choice.
        """
        raw = self.get_str_cookie("user")
        if raw is not None:
            try:
                self.connect()
                return raw or "anonymous"
            except Exception:
                return None

    @property
    def current_server(self):
        """
        Return the server connected to if any
        """
        try:
            return self.get_secure_cookie("server").decode("utf-8")
        except AttributeError:
            return None

    @property
    def current_host(self):
        """
        Return the host connected to if any
        """
        server = self.current_server
        if server is None:
            return None
        connoptions = options.servers[server].copy()
        host = "localhost"
        if "host" in connoptions:
            host = connoptions["host"]
        return "%s" % (host)

    @property
    def current_port(self):
        """
        Return the port connected to if any
        """
        server = self.current_server
        if server is None:
            return None
        connoptions = options.servers[server].copy()
        port = "5432"
        if "port" in connoptions:
            port = connoptions["port"]
        return "%s" % (port)

    @property
    def current_connection(self):
        """
        Return the host and port connected to if any
        """
        server = self.current_server
        if server is None:
            return None
        connoptions = options.servers[server].copy()
        host = "localhost"
        port = "5432"
        if "host" in connoptions:
            host = connoptions["host"]
        if "port" in connoptions:
            port = connoptions["port"]
        return "%s:%s" % (host, port)

    @property
    def database(self):
        """Return the current database."""
        return None

    @property
    def server(self):
        """Return the current database."""
        return None

    @property
    def notify_allowed(self):
        """
        Returns whether the current user is allowed to use the NOTIFY-based
        communication with powa-collector
        """
        return False

    def get_powa_version(self, **kwargs):
        version = self.execute(
            """
            SELECT regexp_replace(extversion, '(dev|beta\d*)', '') AS version
            FROM pg_extension
            WHERE extname = 'powa'
            """,
            **kwargs,
        )

        if len(version) == 0:
            return None

        version = version[0]["version"]
        if version is None:
            return None
        return [int(part) for part in version.split(".")]

    def get_pg_version_num(self, srvid=None, **kwargs):
        try:
            return int(
                self.execute(
                    """
                SELECT setting
                FROM pg_settings
                WHERE name = 'server_version_num'
                """,
                    srvid=srvid,
                    **kwargs,
                )[0]["setting"]
            )
        except Exception:
            return None

    def get_databases(self, srvid):
        """
        Return the list of databases in this instance.
        """
        if self.current_user:
            if self._databases is None:
                self._databases = [
                    d["datname"]
                    for d in self.execute(
                        """
                    SELECT p.datname
                    FROM {powa}.powa_databases p
                    LEFT JOIN pg_database d ON p.oid = d.oid
                    WHERE COALESCE(datallowconn, true)
                    AND srvid = %(srvid)s
                    ORDER BY DATNAME
                    """,
                        params={"srvid": srvid},
                    )
                ]
            return self._databases

    def deparse_srvid(self, srvid):
        if srvid == "0":
            return self.current_connection
        else:
            return self.execute(
                """
                                SELECT COALESCE(alias,
                                                hostname || ':' || port)
                                       AS server
                                FROM {powa}.powa_servers
                                WHERE id = %(srvid)s
                                """,
                params={"srvid": int(srvid)},
            )[0]["server"]

    @property
    def servers(self, **kwargs):
        """
        Return the list of servers.
        """
        if self.current_user:
            if self._servers is None:
                self._servers = [
                    [s["id"], s["val"], s["alias"]]
                    for s in self.execute(
                        """
                    SELECT s.id, CASE WHEN s.id = 0 THEN
                        %(default)s
                    ELSE
                        s.hostname || ':' || s.port
                    END AS val,
                    s.alias
                    FROM {powa}.powa_servers s
                    ORDER BY hostname
                    """,
                        params={"default": self.current_connection},
                    )
                ]
            return self._servers

    def on_finish(self):
        for conn in self._connections.values():
            conn.close()

    def connect(
        self,
        srvid=None,
        server=None,
        user=None,
        password=None,
        database=None,
        remote_access=False,
        **kwargs,
    ):
        """
        Connect to a specific database.
        Parameters default values are taken from the cookies and the server
        configuration file.
        """
        if srvid is not None and srvid != "0":
            remote_access = True

        # Check for global connection restriction first
        if remote_access and not options["allow_ui_connection"]:
            raise Exception("UI connection globally not allowed.")

        conn_allowed = None
        server = server or self.get_str_cookie("server")
        user = user or self.get_str_cookie("user")
        password = password or self.get_str_cookie("password")
        if server not in options.servers:
            raise HTTPError(404, "Server %s not found." % server)

        connoptions = options.servers[server].copy()

        # Handle "query" parameter.  It should be a dict contain a single
        # client_encoding key.
        encoding_query = connoptions.pop("query", None)
        if encoding_query is not None:
            if not isinstance(encoding_query, dict):
                raise Exception(
                    'Invalid "query" parameter: %r, ' % encoding_query
                )

            for k in encoding_query:
                if k != "client_encoding":
                    raise Exception(
                        'Invalid "query" parameter: %r", '
                        'unexpected key "%s"' % (encoding_query, k)
                    )

        if srvid is not None and srvid != "0":
            tmp = self.connect()
            cur = tmp.cursor(cursor_factory=RealDictCursor)
            cur.execute(
                """
            SELECT hostname, port, username, password, dbname,
                allow_ui_connection
            FROM {powa}.powa_servers WHERE id = %(srvid)s
            """,
                {"srvid": srvid},
            )
            row = cur.fetchone()
            cur.close()

            connoptions["host"] = row["hostname"]
            connoptions["port"] = row["port"]
            connoptions["user"] = row["username"]
            connoptions["password"] = row["password"]
            connoptions["database"] = row["dbname"]
            conn_allowed = row["allow_ui_connection"]
        else:
            if "user" not in connoptions:
                connoptions["user"] = user
            if "password" not in connoptions:
                connoptions["password"] = password

        # If a non-powa connection is requested, check if we're allowed
        if remote_access:
            # authorization check for local connection has not been done yet
            if conn_allowed is None:
                tmp = self.connect(
                    remote_access=False,
                    server=server,
                    user=user,
                    password=password,
                )
                cur = tmp.cursor()
                cur.execute("""
                SELECT allow_ui_connection
                FROM {powa}.powa_servers WHERE id = 0
                """)
                row = cur.fetchone()
                cur.close()
                conn_allowed = row[0]

            if not conn_allowed:
                raise Exception("UI connection not allowed for this server.")

        if database is not None:
            connoptions["database"] = database

        url = self.__get_url(**connoptions)
        if url in self._connections:
            return self._connections.get(url)

        conn = psycopg2.connect(
            connection_factory=CustomConnection, **connoptions
        )
        conn.initialize(
            self.logger,
            srvid,
            self.__get_safe_dsn(**connoptions),
            encoding_query,
            self.application.settings["debug"],
        )

        # Get and cache all extensions schemas, in a dict with the extension
        # name as the key and the *quoted* schema as the value.
        cur = conn.cursor()
        cur.execute("""
            SELECT extname, quote_ident(nspname) AS nsp
            FROM pg_catalog.pg_extension e
            JOIN pg_catalog.pg_namespace n ON n.oid = e.extnamespace
        """)
        ext_nsps = {row[0]: row[1] for row in cur.fetchall()}
        cur.close()
        conn._nsps = ext_nsps

        # Cache the connection and return it
        self._connections[url] = conn
        return self._connections[url]

    def __get_extension_version(
        self, srvid, extname, database=None, remote_access=True
    ):
        """
        Returns a tuple with all digits of the version of the specific
        extension on the specific server and database, or None if the extension
        isn't install (or if we fail trying to retrieve the information).
        """
        remver = None

        # make sure we have a consistent type for the server id
        srvid = str(srvid)

        # Check for a cached version first.  Note that we do cache the lack of
        # extension (storing None), so we use an empty string to detect that no
        # caching happened yet.
        remver = self._ext_versions[srvid][database].get(extname, "")

        if remver != "":
            return remver

        # For remote server, check first if powa-collector reported a version
        # for that extension, but only for default database.
        if srvid != "0" and database is None:
            try:
                remver = self.execute(
                    """
                    SELECT version
                    FROM {powa}.powa_extension_config
                    WHERE srvid = %(srvid)s
                    AND extname = %(extname)s
                    """,
                    params={"srvid": srvid, "extname": extname},
                )[0]["version"]

            except Exception:
                return None
        else:
            # Otherwise, fall back to querying on the target database.
            try:
                remver = self.execute(
                    """
                    SELECT extversion
                    FROM pg_catalog.pg_extension
                    WHERE extname = %(extname)s
                    LIMIT 1
                    """,
                    srvid=srvid,
                    database=database,
                    params={"extname": extname},
                    remote_access=remote_access,
                )[0]["extversion"]
            except Exception:
                return None

        if remver is None:
            self._ext_versions[srvid][database][extname] = None
            return None

        # Clean up any extraneous characters
        remver = re.search(r"[0-9\.]*[0-9]", remver)

        if remver is None:
            self._ext_versions[srvid][database][extname] = None
            return None

        remver = tuple(map(int, remver.group(0).split(".")))
        self._ext_versions[srvid][database][extname] = remver

        return remver

    def has_extension(self, srvid, extname):
        """
        Returns whether the specific extensions is supposed to be installed, in
        any version, on the specific server for the default database.  This
        function is less expensive than has_extension_version for remote
        servers, as we're only checking for the metadata stored in the
        powa_functions table of the dedicated repository server instead of
        connecting to the remote server.  It also makes it possible to handle
        more widgets in the UI if the remotes servers are not accessible from
        the powa-web server.  This assumes that "module" is the name of the
        underlying extension.
        """
        if srvid == "0" or srvid == 0:
            # if local server, fallback to the full test, as it won't be more
            # expensive
            return self.has_extension_version(
                srvid, extname, "0", remote_access=False
            )
        else:
            try:
                # Look for at least an enabled snapshot function.  If a module
                # provides multiple snapshot functions and only a subset is
                # activated, let's assume that the extension is available.
                return self.execute(
                    """
                SELECT COUNT(*) != 0 AS res
                FROM {powa}.powa_functions
                WHERE srvid = %(srvid)s
                AND name = %(extname)s
                AND enabled
                """,
                    params={"srvid": srvid, "extname": extname},
                )[0]["res"]
            except Exception:
                return False

    def has_extension_version(
        self, srvid, extname, version, database=None, remote_access=True
    ):
        """
        Returns whether the version of the specific extension on the specific
        server and database is at least the given version.
        """
        if version is None:
            raise Exception("No version provided!")

        remver = self.__get_extension_version(
            srvid, extname, remote_access=remote_access
        )

        if remver is None:
            return False

        wanted = tuple(map(int, version.split(".")))

        return remver >= wanted

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

    def execute(
        self,
        query,
        srvid=None,
        params=None,
        server=None,
        user=None,
        database=None,
        password=None,
        remote_access=False,
    ):
        """
        Execute a query against a database, with specific bind parameters.
        """
        if params is None:
            params = {}

        if "samples" not in params:
            params["samples"] = 100

        conn = self.connect(
            srvid, server, user, password, database, remote_access
        )

        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SAVEPOINT powa_web")
        try:
            cur.execute(query, params)

            # Fetch all results if any, and return them.
            if cur.rowcount > 0:
                rows = cur.fetchall()
            else:
                rows = []

            cur.execute("RELEASE powa_web")

        except Exception as e:
            cur.execute("ROLLBACK TO powa_web")
            raise e
        finally:
            cur.close()
        return rows

    def notify_collector(self, command, args=[], timeout=3):
        """
        Notify powa-collector and get its answer.
        """
        conn = self.connect()

        cur = conn.cursor()

        # we shouldn't listen on anything else than our own channel, but just
        # in case discard everything
        cur.execute("UNLISTEN *")

        random.seed()
        channel = "r%d" % random.randint(1, 99999)
        cur.execute("LISTEN %s" % channel)

        # some commands will contain user-provided strings, so we need to
        # properly escape the arguments.
        payload = "%s %s %s" % (command, channel, " ".join(args))
        cur.execute("NOTIFY powa_collector, %s", (payload,))

        cur.close()
        conn.commit()

        # wait for activity on the connection up to given timeout
        select.select([conn], [], [], timeout)

        # we shouldn't listen on anything else than our own channel, but just
        # in case discard everything
        cur = conn.cursor()
        cur.execute("UNLISTEN *")
        conn.commit()

        conn.poll()
        res = []
        while conn.notifies:
            notif = conn.notifies.pop(0)

            payload = notif.payload.split(" ")

            received_command = payload.pop(0)
            # we shouldn't received unexpected messages, but ignore them if any
            if received_command != command:
                continue

            status = payload.pop(0)
            payload = " ".join(payload)

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
            return value.decode("utf8")
        return default

    def set_pickle_cookie(self, name, value):
        """
        Serialize a cookie value using the pickle protocol.
        """
        self.set_secure_cookie(name, pickle.dumps(value))

    flash = ui_methods.flash

    def to_json(self):
        return {
            "database": self.database,
            "currentPort": self.current_port,
            "currentServer": self.current_server,
            "currentUser": self.current_user,
            "currentConnection": self.current_connection,
            "notifyAllowed": self.notify_allowed,
            "server": self.server,
            "version": ui_methods.version(None),
            "year": ui_methods.year(None),
            "configUrl": self.reverse_url("RepositoryConfigOverview"),
            "logoUrl": self.static_url("img/favicon/favicon-32x32.png"),
            "homeUrl": self.reverse_url("Overview"),
        }


class AuthHandler(BaseHandler):
    """
    Base handler for urls needing authentifications.
    """

    @authenticated
    def prepare(self):
        super(AuthHandler, self).prepare()

    def to_json(self):
        return dict(
            **super(AuthHandler, self).to_json(),
            **{"logoutUrl": self.reverse_url("logout")},
        )
