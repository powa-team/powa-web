"""
Index page presenting the list of available servers.
"""

from powa.ui_modules import MenuEntry
from powa.dashboards import (
    Dashboard, Grid,
    MetricGroupDef, MetricDef,
    DashboardPage)
from sqlalchemy.sql import (text)

from powa.server import ServerOverview
try:
    from collections import OrderedDict
except:
    from ordereddict import OrderedDict


class OverviewMetricGroup(MetricGroupDef):
    """
    Metric group used by the "all servers" grid
    """
    name = "all_servers"
    xaxis = "srvid"
    axis_type = "category"
    data_url = r"/server/all_servers/"
    hostname = MetricDef(label="Hostname", type="text")
    port = MetricDef(label="Port", type="text")
    version = MetricDef(label="Version", type="text")

    @property
    def query(self):

        sql = text("""SELECT id AS srvid,
                CASE WHEN id = 0 THEN
                   '<local>'
                ELSE
                   COALESCE(alias, hostname || ':' || port)
                END AS alias,
                CASE WHEN id = 0 THEN :host ELSE hostname END as hostname,
                CASE WHEN id = 0 THEN :port ELSE port END AS port,
                CASE WHEN id = 0 THEN set.setting
                    ELSE s.version::text
                END AS version
                FROM powa_servers s
                LEFT JOIN pg_settings set ON set.name = 'server_version'
                    AND s.id = 0""")

        sql = sql.params(host=self.current_host, port=self.current_port)
        return sql

    def process(self, val, **kwargs):
        val = dict(val)
        val["url"] = self.reverse_url("ServerOverview", val["srvid"])
        return val


class Overview(DashboardPage):
    """
    Overview dashboard page.
    """
    base_url = r"/server/"
    datasources = [OverviewMetricGroup]
    title = 'All servers'

    def dashboard(self):
        # This COULD be initialized in the constructor, but tornado < 3 doesn't
        # call it
        if getattr(self, '_dashboard', None) is not None:
            return self._dashboard

        dashes = [[Grid("All servers",
                        columns=[{
                            "name": "alias",
                            "label": "Instance",
                            "url_attr": "url",
                            "direction": "descending"
                        }],
                        metrics=OverviewMetricGroup.all())]]

        self._dashboard = Dashboard("All servers", dashes)
        return self._dashboard

    @classmethod
    def get_childmenu(cls, handler, params):
        children = []
        for s in list(handler.servers):
            new_params = params.copy()
            new_params["server"] = s[0]
            entry = ServerOverview.get_selfmenu(handler, new_params)
            entry.title = s[1]
            children.append(entry)
        return children
