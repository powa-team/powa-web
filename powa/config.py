"""
Dashboard for the configuration summary page.
"""

from __future__ import absolute_import

import json
from powa.collector import CollectorServerDetail
from powa.dashboards import (
    ContentWidget,
    Dashboard,
    DashboardPage,
    Grid,
    MetricDef,
    MetricGroupDef,
)
from powa.sql.views import get_config_changes


def get_pgts_query(handler, restrict_database=False):
    # avoid pg errors if the extension hasn't been installed, or is not
    # installed in version 2.0.0 or more.  We check for local installation
    # only, as query will look in local table.  If the extension isn't setup
    # remotely, the check will be pretty quick.
    pgts = handler.has_extension_version(
        "0", "pg_track_settings", "2.0.0", remote_access=False
    )
    if not pgts:
        return None

    return get_config_changes(restrict_database)


class ConfigChangesGlobal(MetricGroupDef):
    name = "Config Changes"
    data_url = r"/server/(\d+)/config_changes"
    xaxis = "ts"
    axis_type = "category"
    setting = MetricDef(label="Name", type="string")
    previous = MetricDef(label="Previous", type="string")
    new = MetricDef(label="New", type="string")
    params = ["server"]

    @property
    def query(self):
        return get_pgts_query(self)


class ConfigChangesDatabase(MetricGroupDef):
    name = "Config Changes"
    data_url = r"/server/(\d+)/database/([^\/]+)/config_changes"
    xaxis = "ts"
    axis_type = "category"
    setting = MetricDef(label="Name", type="string")
    previous = MetricDef(label="Previous", type="string")
    new = MetricDef(label="New", type="string")
    params = ["server", "database"]

    @property
    def query(self):
        return get_pgts_query(self, True)


class ConfigChangesQuery(MetricGroupDef):
    name = "Config Changes"
    data_url = r"/server/(\d+)/database/([^\/]+)/query/(-?\d+)/config_changes"
    xaxis = "ts"
    axis_type = "category"
    setting = MetricDef(label="Name", type="string")
    previous = MetricDef(label="Previous", type="string")
    new = MetricDef(label="New", type="string")
    params = ["server", "database", "query"]

    @property
    def query(self):
        return get_pgts_query(self, True)


class ServersErrors(ContentWidget):
    """
    Detail widget showing the various errors related to servers logged
    """

    title = "Errors"
    data_url = r"/config/errors"

    def get(self):
        sql = """SELECT srvid,
            CASE WHEN id = 0 THEN
               '<local>'
            ELSE
               username || '@' || hostname || ':' || port || '/' || dbname
            END AS server_alias,
            errors
            FROM {powa}.powa_servers s
            JOIN {powa}.powa_snapshot_metas m ON m.srvid = s.id
            WHERE errors IS NOT NULL
            ORDER BY 1
        """

        rows = self.execute(sql)

        self.render_json(rows)


class AllCollectorsDetail(ContentWidget):
    """
    Detail widget showing summarized information for the background worker and
    the remote collector daemon.
    """

    title = "Collector Detail"
    data_url = r"/config/allcollectors"

    def get(self):
        sql = """SELECT id,
            CASE WHEN id = 'collector'
                THEN 'Remote collector'
                  || coalesce(
                    substring(application_name,
                        length('PoWA collector - main thread ')
                    ), '')
                ELSE 'Backgound worker'
            END AS powa_kind,
            date_trunc('second', backend_start) as start,
            datname, usename,
            coalesce(host(client_addr), '<local>') AS client_addr,
            count(datname) OVER () AS nb_found,
            (
                SELECT count(*) > 0
                FROM pg_stat_activity
                WHERE query = '<insufficient privilege>'
            ) AS not_authorized
            FROM (
                SELECT 'bgworker' AS id, 'PoWA - %%' AS val,
                    'powa' AS backend_type
                UNION ALL
                SELECT 'collector', 'PoWA collector - main thread (%%',
                    'client backend' AS backend_type
            ) n
            LEFT JOIN pg_stat_activity a ON
                a.application_name LIKE n.val
                AND a.backend_type = n.backend_type
            ORDER BY 1"""

        rows = self.execute(sql)

        self.logger.warn("%r", rows[0])
        if rows[0]["not_authorized"] is True:
            collector = None
        if rows[0]["nb_found"] == 0:
            collector = []
        else:
            collector = rows
        self.render_json(collector)


class PowaServersMetricGroup(MetricGroupDef):
    """
    Metric group for the servers list grid.
    """

    name = "powa_servers"
    xaxis = "server_alias"
    data_url = r"/config/powa_servers/"
    axis_type = "category"
    hostname = MetricDef(label="Hostname", type="string")
    port = MetricDef(label="Port", type="string")
    username = MetricDef(label="User name", type="string")
    password = MetricDef(label="Password", type="string")
    dbname = MetricDef(label="Database name", type="string")
    frequency = MetricDef(label="Frequency", type="string")
    retention = MetricDef(label="Retention", type="string")
    powa_coalesce = MetricDef(label="Powa coalesce", type="string")
    allow_ui_connection = MetricDef(label="Allow UI connection", type="bool")
    snapts = MetricDef(label="Last snapshot", type="string")
    no_err = MetricDef(label="Error", type="bool")
    collector_status = MetricDef(label="Collector Status", type="string")

    query = """SELECT id,
     CASE WHEN s.id = 0 THEN
        '<local>'
     ELSE
        COALESCE(alias,
          s.username || '@' || s.hostname || ':' || s.port || '/' || s.dbname)
     END AS server_alias,
     s.hostname, s.port, s.username,
     CASE WHEN s.password IS NULL THEN '<NULL>' ELSE '********' END AS password,
     s.dbname, s.frequency, s.retention::text AS retention,
     s.powa_coalesce::text AS powa_coalesce, s.allow_ui_connection,
     CASE WHEN coalesce(m.snapts, '-infinity') = '-infinity'::timestamptz THEN
        NULL
     ELSE
        clock_timestamp() - m.snapts
     END::text AS last_snapshot,
     CASE WHEN coalesce(m.snapts, '-infinity') = '-infinity'::timestamptz THEN
        NULL
     ELSE
        m.snapts
     END AS snapts,
     errors IS NULL AS no_err,
     CASE WHEN s.id = 0 THEN
       coalesce(a.val, 'stopped')
     ELSE
       'unknown'
     END AS collector_status
     FROM {powa}.powa_servers s
     LEFT JOIN {powa}.powa_snapshot_metas m ON s.id = m.srvid
     LEFT JOIN (SELECT
        CASE WHEN current_setting('powa.frequency') = '-1' THEN 'disabled'
            ELSE 'running'
        END AS val, application_name
       FROM pg_stat_activity
       WHERE backend_type = 'powa'
     ) a ON a.application_name LIKE 'PoWA - %%'
     ORDER BY 2"""

    def process(self, val, **kwargs):
        val["url"] = self.reverse_url("RemoteConfigOverview", val["id"])
        return val

    def post_process(self, data, **kwargs):
        if len(data["data"]):
            raw = self.notify_collector("WORKERS_STATUS", timeout=1)
            if not raw:
                return data

            line = None
            # get the first correct response only, if multiple answers were
            # returned
            while line is None and len(raw) > 0:
                tmp = raw.pop(0)
                if "OK" in tmp:
                    line = tmp["OK"]

            # nothing correct, give up
            if line is None or line == {}:
                return data

            stats = json.loads(line)

            for row in data["data"]:
                srvid = str(row["id"])
                if srvid in stats:
                    row["collector_status"] = stats[srvid]

        return data


class PgSettingsMetricGroup(MetricGroupDef):
    """
    Metric group for the pg_settings grid.
    """

    name = "pg_settings"
    xaxis = "setting_name"
    data_url = r"/config/(\d+)/pg_settings/"
    axis_type = "category"
    setting_value = MetricDef(label="Value", type="string")
    setting_unit = MetricDef(label="Unit", type="string")
    category_value = MetricDef(label="Category", type="string")
    __query = """
             SELECT name as setting_name, setting as setting_value,
             COALESCE(unit,'') AS setting_unit, category as category_value
             FROM pg_settings
             --WHERE name like 'powa%%'
             ORDER BY name"""
    params = ["server"]

    @property
    def query(self):
        if self.path_args[0] == "0":
            return self.__query
        else:
            # we'll get the data on the foreign server in post_process
            return None

    def post_process(self, data, server, **kwargs):
        # For local server we can return data already retrieved
        if server == "0":
            return data

        values = None

        # Check first if the info is available locally
        if self.has_extension_version(server, "pg_track_settings", "2.0.0"):
            try:
                values = self.execute(
                    """
                        SELECT t.name AS setting_name,
                            t.setting AS setting_value,
                            s.unit AS setting_unit,
                            s.category AS category_value
                        FROM {pg_track_settings}.pg_track_settings(now(),
                                                                   %(srvid)s) t
                        LEFT JOIN pg_catalog.pg_settings s
                            ON s.name = t.name
                        """,
                    params={"srvid": server},
                )

                # If no rows were retrieved, it probably means that
                # pg_tracksettings isn't sampled even if the extension exists.
                # Reset values so we can try to fetch info from the remote
                # server.
                if values.rowcount == 0:
                    values = None
            except Exception:
                # ignore any error, we'll just fallback on remote check
                pass

        if values is None:
            try:
                values = self.execute(self.__query, srvid=server)
            except Exception:
                # ignore any connection or remote execution error
                pass

        if values is not None:
            data = {"data": [self.process(val) for val in values]}
        else:
            data = {
                "data": [],
                "messages": {
                    "alert": [
                        "Could not retrieve PostgreSQL"
                        + " settings "
                        + "on remote server"
                    ]
                },
            }

        return data


class PgStatExtensionsMetricGroup(MetricGroupDef):
    """
    Metric group for the stat extensions grid.
    """

    name = "pg_stat_extensions"
    xaxis = "extname"
    data_url = r"/config/(\d+)/pg_stat_extensions/"
    axis_type = "category"
    available = MetricDef(label="Available", type="bool")
    installed = MetricDef(label="Installed", type="bool")
    handled = MetricDef(label="Sampled", type="bool")
    extversion = MetricDef(label="Version", type="string")
    params = ["server"]

    @property
    def query(self):
        if self.path_args[0] == "0":
            return """SELECT pe.extname, pae.name IS NOT NULL AS available,
                        pae.installed_version IS NOT NULL AS installed,
                    pec.enabled AS handled,
                    coalesce(pae.installed_version , '-') AS extversion
                FROM {powa}.powa_extensions pe
                JOIN {powa}.powa_extension_functions pef USING (extname)
                LEFT JOIN pg_catalog.pg_available_extensions pae
                    ON pae.name = pe.extname
                LEFT JOIN {powa}.powa_extension_config pec
                    ON pec.extname = pe.extname AND pec.srvid = %(server)s
                WHERE operation = 'snapshot'
                """
        else:
            return """SELECT DISTINCT pe.extname,
                        CASE
                            WHEN pec.version IS NOT NULL THEN true
                            ELSE NULL::bool
                        END AS available,
                        NULL::bool AS installed,
                    pec.enabled AS handled,
                    coalesce(pec.version, '-') AS extversion
                FROM {powa}.powa_extensions pe
                JOIN {powa}.powa_extension_functions pef USING (extname)
                LEFT JOIN pg_catalog.pg_available_extensions pae
                    ON pae.name = pe.extname
                LEFT JOIN {powa}.powa_extension_config pec
                    ON pec.extname = pe.extname AND pec.srvid = %(server)s
                WHERE operation = 'snapshot'
                """

    def post_process(self, data, server, **kwargs):
        """
        Get the missing metadata of the extensions on the remote servers if
        needed
        """
        # We already have all the data for the local server
        if server == "0":
            return data

        res = None
        errmsg = None

        extnames = []

        for row in data["data"]:
            extnames.append(row["extname"])

        try:
            res = self.execute(
                """
            SELECT name AS extname, installed_version
            FROM pg_available_extensions
            WHERE name = ANY(%(extnames)s)""",
                srvid=server,
                params={"extnames": extnames},
            )
        except Exception as e:
            # ignore any connection or remote execution error, but keep the
            # error message
            errmsg = str(e)
            pass

        # if we couldn't get any data, send what we have
        if res is None or len(res) == 0:
            data["messages"] = {
                "alert": [
                    "Could not retrieve extensions"
                    + " on remote server: %s" % errmsg
                ]
            }
            return data

        remote_exts = res

        alerts = []
        for ext in data["data"]:
            found = False

            for r in remote_exts:
                if r["extname"] == ext["extname"]:
                    found = True
                    break

            if not found:
                ext["available"] = False
                ext["installed"] = None
            else:
                ext["available"] = True
                ext["installed"] = r["installed_version"] is not None

            if ext["handled"] and ext["installed"] is None:
                alerts.append(ext["extname"])

        if len(alerts) > 0:
            data["messages"] = {
                "alert": [
                    (
                        "%d extensions need to be installed:%s"
                        % (len(alerts), " ".join(alerts))
                    )
                ]
            }

        return data


class PgSupportExtensionsMetricGroup(MetricGroupDef):
    """
    Metric group for the support extensions grid.
    """

    name = "pg_support_extensions"
    xaxis = "extname"
    data_url = r"/config/(\d+)/pg_support_extensions/"
    axis_type = "category"
    available = MetricDef(label="Available", type="bool")
    installed = MetricDef(label="Installed", type="bool")
    extversion = MetricDef(label="Version", type="string")
    params = ["server"]

    @property
    def query(self):
        if self.path_args[0] == "0":
            return """SELECT pe.extname, pae.name IS NOT NULL AS available,
                        pae.installed_version IS NOT NULL AS installed,
                    coalesce(pae.installed_version , '-') AS extversion
                FROM {powa}.powa_extensions pe
                LEFT JOIN {powa}.powa_extension_functions pef USING (extname)
                LEFT JOIN pg_catalog.pg_available_extensions pae
                    ON pae.name = pe.extname
                WHERE operation IS NULL
                """
        else:
            return """SELECT pe.extname,
                        NULL::bool AS available, NULL::bool AS installed,
                        NULL::text AS extversion
                FROM {powa}.powa_extensions pe
                LEFT JOIN {powa}.powa_extension_functions pef USING (extname)
                WHERE operation IS NULL
                """

    def post_process(self, data, server, **kwargs):
        """
        Get the missing metadata of the extensions on the remote servers
        """
        # We already have all the data for the local server
        if server == "0":
            return data

        res = None
        errmsg = None

        extnames = []

        for row in data["data"]:
            extnames.append(row["extname"])

        try:
            res = self.execute(
                """
            SELECT name AS extname, installed_version
            FROM pg_available_extensions
            WHERE name = ANY(%(extnames)s)""",
                srvid=server,
                params={"extnames": extnames},
            )
        except Exception as e:
            # ignore any connection or remote execution error, but keep the
            # error message
            errmsg = str(e)
            pass

        # if we couldn't get any data, send what we have
        if res is None or len(res) == 0:
            data["messages"] = {
                "alert": [
                    "Could not retrieve extensions"
                    + " on remote server: %s" % errmsg
                ]
            }
            return data

        remote_exts = res

        for ext in data["data"]:
            found = False

            for r in remote_exts:
                if r["extname"] == ext["extname"]:
                    found = True
                    break

            if not found:
                ext["available"] = False
                ext["installed"] = None
                ext["extversion"] = "-"
            else:
                ext["available"] = True
                ext["installed"] = r["installed_version"] is not None
                ext["extversion"] = r["installed_version"]

        return data


class PgDbModulesMetricGroup(MetricGroupDef):
    """
    Metric group for the per-db modules grid.
    """

    name = "pg_db_modules"
    xaxis = "db_module"
    data_url = r"/config/(\d+)/pg_db_modules/"
    axis_type = "category"
    dbnames = MetricDef(label="Database restriction", type="string")
    enabled = MetricDef(label="Enabled", type="bool")
    params = ["server"]

    @property
    def query(self):
        return """SELECT db_module, dbnames::text AS dbnames, enabled
            FROM {powa}.powa_db_module_config
            WHERE srvid = %(server)s
            """


class PgCatalogsMetricGroup(MetricGroupDef):
    """
    Metric group for the per-db catalogs grid.
    """

    name = "pg_catalogs"
    xaxis = "datname"
    data_url = r"/config/(\d+)/pg_catalogs/"
    axis_type = "category"
    last_refresh = MetricDef(label="Last refresh", type="string")
    params = ["server"]

    @property
    def query(self):
        # We combine the database list from powa_databases and
        # powa_cat_database in case some databases are missing in one or the
        # other.
        return """SELECT coalesce(pd.datname, pcd.datname) AS datname,
                last_refresh
            FROM {powa}.powa_databases pd
            FULL OUTER JOIN {powa}.powa_catalog_databases pcd
                USING (srvid, oid)
            WHERE srvid = %(server)s
            """


class RepositoryConfigOverview(DashboardPage):
    """
    Dashboard page for configuration page.
    """

    base_url = r"/config/"
    datasources = [PowaServersMetricGroup, AllCollectorsDetail, ServersErrors]
    title = "Configuration"

    def dashboard(self):
        # This COULD be initialized in the constructor, but tornado < 3 doesn't
        # call it
        if getattr(self, "_dashboard", None) is not None:
            return self._dashboard

        self._dashboard = Dashboard(
            "Server list",
            [
                [AllCollectorsDetail],
                [
                    Grid(
                        "Servers",
                        columns=[
                            {
                                "name": "server_alias",
                                "label": "Server",
                                "url_attr": "url",
                                "direction": "ascending",
                            }
                        ],
                        metrics=PowaServersMetricGroup.all(),
                    )
                ],
                [ServersErrors],
            ],
        )
        return self._dashboard


class RemoteConfigOverview(DashboardPage):
    """
    Dashboard page for configuration page.
    """

    base_url = r"/config/(\d+)"
    datasources = [
        PgSettingsMetricGroup,
        PgStatExtensionsMetricGroup,
        PgSupportExtensionsMetricGroup,
        PgDbModulesMetricGroup,
        PgCatalogsMetricGroup,
        CollectorServerDetail,
    ]
    params = ["server"]
    parent = RepositoryConfigOverview
    # title = 'Remote server configuration'

    @classmethod
    def breadcrum_title(cls, handler, param):
        return handler.deparse_srvid(param["server"])

    def dashboard(self):
        # This COULD be initialized in the constructor, but tornado < 3 doesn't
        # call it
        if getattr(self, "_dashboard", None) is not None:
            return self._dashboard

        grids = [
            [
                Grid(
                    "Stats Extensions",
                    columns=[
                        {
                            "name": "extname",
                            "label": "Extension",
                        }
                    ],
                    metrics=PgStatExtensionsMetricGroup.all(),
                ),
                Grid(
                    "Support Extensions",
                    columns=[
                        {
                            "name": "extname",
                            "label": "Extension",
                        }
                    ],
                    metrics=PgSupportExtensionsMetricGroup.all(),
                ),
            ]
        ]

        if self.path_args[0] != "0":
            grids.append(
                [
                    Grid(
                        "Database modules",
                        columns=[
                            {
                                "name": "db_module",
                                "label": "DB module",
                            }
                        ],
                        metrics=PgDbModulesMetricGroup.all(),
                    ),
                    Grid(
                        "Catalogs",
                        columns=[
                            {
                                "name": "datname",
                                "label": "Database",
                            }
                        ],
                        metrics=PgCatalogsMetricGroup.all(),
                    ),
                ]
            )

        grids.append(
            [
                Grid(
                    "PostgreSQL settings",
                    columns=[
                        {
                            "name": "setting_name",
                            "label": "Setting",
                        }
                    ],
                    metrics=PgSettingsMetricGroup.all(),
                )
            ]
        )

        self._dashboard = Dashboard("Configuration overview", grids)
        return self._dashboard
