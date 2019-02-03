"""
Dashboard for the configuration summary page.
"""
from __future__ import absolute_import
from powa.dashboards import (
    Dashboard, Grid,
    MetricGroupDef, MetricDef,
    DashboardPage, ContentWidget)


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
            FROM powa_servers s
            JOIN powa_snapshot_metas m ON m.srvid = s.id
            WHERE errors IS NOT NULL
            ORDER BY 1
        """

        rows = self.execute(sql).fetchall()

        self.render("config/error.html", errors=rows)


class CollectorDetail(ContentWidget):
    """
    Detail widget showing summarized information for the remote collector
    daemon.
    """
    title = "Collector Detail"
    data_url = r"/config/collector"

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
            count(datname) OVER () AS nb_found
            FROM (
                SELECT 'bgworker' AS id, 'PoWA - %%' AS val
                UNION ALL
                SELECT 'collector', 'PoWA collector - main thread (%%'
            ) n
            LEFT JOIN pg_stat_activity a ON a.application_name LIKE n.val
            ORDER BY 1"""

        rows = self.execute(sql).fetchall()

        if (rows[0]["nb_found"] == 0):
            self.render("config/collector.html", collector=None)
        else:
            self.render("config/collector.html", collector=rows)


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
    snapts = MetricDef(label="Last snapshot", type="string")
    no_err = MetricDef(label="Status", type="bool")

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
     errors IS NULL AS no_err
     FROM powa_servers s
     LEFT JOIN powa_snapshot_metas m ON s.id = m.srvid
     ORDER BY 2"""

    def process(self, val, **kwargs):
        val = dict(val)
        val["url"] = self.reverse_url("RemoteConfigOverview", val["id"])
        return val


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
        if (self.path_args[0] == '0'):
            return self.__query
        else:
            # we'll get the data on the foreign server in post_process
            return None

    def post_process(self, data, server, **kwargs):
        if (server != '0'):
            values = None
            try:
                values = self.execute(self.__query, srvid=server)
            except Exception:
                # ignore any connection or remote execution error
                pass

            if (values is not None):
                data = {"data": [self.process(val) for val in values]}
            else:
                data = {"data": [],
                        "alerts": ["Could not retrieve PostgreSQL settings "
                                   + "on remote server"]}

        return data


class PgExtensionsMetricGroup(MetricGroupDef):
    """
    Metric group for the pg_settings grid.
    """

    name = "pg_extensions"
    xaxis = "extname"
    data_url = r"/config/(\d+)/pg_extensions/"
    axis_type = "category"
    available = MetricDef(label="Available", type="bool")
    installed = MetricDef(label="Installed", type="bool")
    handled = MetricDef(label="Sampled", type="bool")
    extversion = MetricDef(label="Version", type="string")
    params = ["server"]

    @property
    def query(self):
        if (self.path_args[0] == '0'):
            return """
            SELECT DISTINCT s.extname,
              CASE WHEN avail.name IS NULL then false ELSE true END AS available,
              CASE WHEN ins.extname IS NULL then false ELSE true END AS installed,
              CASE WHEN f.module IS NULL then false ELSE true END AS handled,
              COALESCE(ins.extversion, '-') AS extversion
            FROM (
                 SELECT 'pg_stat_statements' AS extname
                 UNION SELECT 'pg_qualstats'
                 UNION SELECT 'pg_stat_kcache'
                 UNION SELECT 'pg_track_settings'
                 UNION SELECT 'hypopg'
                 UNION SELECT 'powa'
                 UNION SELECT 'pg_wait_sampling'
            ) s
            LEFT JOIN pg_available_extensions avail on s.extname = avail.name
            LEFT JOIN pg_extension ins on s.extname = ins.extname
            LEFT JOIN powa_functions f ON s.extname = f.module
                AND f.srvid = 0
            ORDER BY 1
             """
        else:
            return """
            SELECT DISTINCT s.extname,
              '-' AS extversion,
              CASE WHEN f.module IS NULL then false ELSE true END AS handled
            FROM (
                 SELECT 'pg_stat_statements' AS extname
                 UNION SELECT 'pg_qualstats'
                 UNION SELECT 'pg_stat_kcache'
                 UNION SELECT 'pg_track_settings'
                 UNION SELECT 'hypopg'
                 UNION SELECT 'powa'
                 UNION SELECT 'pg_wait_sampling'
            ) s
            LEFT JOIN powa_functions f ON s.extname = f.module
                AND f.srvid = %(server)s
            ORDER BY 1
             """

    def post_process(self, data, server, **kwargs):
        if (server == '0'):
            return data

        res = None
        try:
            res = self.execute("""
            SELECT DISTINCT s.extname,
              CASE WHEN avail.name IS NULL then false ELSE true END AS available,
              CASE WHEN ins.extname IS NULL then false ELSE true END AS installed,
              COALESCE(ins.extversion, '-') AS extversion
            FROM (
                 SELECT 'pg_stat_statements' AS extname
                 UNION SELECT 'pg_qualstats'
                 UNION SELECT 'pg_stat_kcache'
                 UNION SELECT 'pg_track_settings'
                 UNION SELECT 'hypopg'
                 UNION SELECT 'powa'
                 UNION SELECT 'pg_wait_sampling'
            ) s
            LEFT JOIN pg_available_extensions avail on s.extname = avail.name
            LEFT JOIN pg_extension ins on s.extname = ins.extname
            ORDER BY 1
                    """, srvid=server)
        except Exception:
            # ignore any connection or remote execution error
            pass

        # if we couldn't connect to the remote server, send what we have
        if (res is None):
            data["alerts"] = ["Could not retrieve extensions on remote server"]
            return data

        remote_exts = res.fetchall()

        alerts = []
        for ext in data["data"]:
            for r in remote_exts:
                if (r["extname"] == ext["extname"]):
                    ext["available"] = r["available"]
                    ext["installed"] = r["installed"]
                    ext["extversion"] = r["extversion"]
                    break

            if (ext["handled"] and not ext["installed"]):
                alerts.append(ext["extname"])

        if (len(alerts) > 0):
            data["alerts"] = [("%d extensions need to be installed:%s"
                              % (len(alerts), ' '.join(alerts)))]

        return data


class RepositoryConfigOverview(DashboardPage):
    """
    Dashboard page for configuration page.
    """

    base_url = r"/config/"
    datasources = [PowaServersMetricGroup, CollectorDetail, ServersErrors]
    title = 'Configuration'

    def dashboard(self):
        # This COULD be initialized in the constructor, but tornado < 3 doesn't
        # call it
        if getattr(self, '_dashboard', None) is not None:
            return self._dashboard

        self._dashboard = Dashboard(
            "Server list",
            [[CollectorDetail],
             [Grid("Servers",
                   columns=[{
                    "name": "server_alias",
                    "label": "Server",
                    "url_attr": "url",
                    "direction": "ascending"
                    }],
                   metrics=PowaServersMetricGroup.all())],
             [ServersErrors]]
        )
        return self._dashboard


class RemoteConfigOverview(DashboardPage):
    """
    Dashboard page for configuration page.
    """

    base_url = r"/config/(\d+)"
    datasources = [PgSettingsMetricGroup, PgExtensionsMetricGroup]
    params = ["server"]
    parent = RepositoryConfigOverview
    # title = 'Remote server configuration'

    @classmethod
    def breadcrum_title(cls, handler, param):
        return handler.deparse_srvid(param["server"])

    def dashboard(self):
        # This COULD be initialized in the constructor, but tornado < 3 doesn't
        # call it
        if getattr(self, '_dashboard', None) is not None:
            return self._dashboard

        self._dashboard = Dashboard(
            "Configuration overview",
            [[Grid("Extensions",
                   columns=[{
                    "name": "extname",
                    "label": "Extension",
                    }],
                   metrics=PgExtensionsMetricGroup.all()
                   )],
             [Grid("PostgreSQL settings",
                   columns=[{
                    "name": "setting_name",
                    "label": "Setting",
                    }],
                   metrics=PgSettingsMetricGroup.all()
                   )]
             ]
        )
        return self._dashboard
