"""
Dashboards for the SLRU page.
"""

from powa.config import ConfigChangesGlobal
from powa.dashboards import (
    Dashboard,
    DashboardPage,
    Graph,
    Grid,
    MetricDef,
    MetricGroupDef,
)
from powa.server import ByAllSlruMetricGroup, ServerOverview
from powa.sql.utils import sum_per_sec
from powa.sql.views_graph import powa_get_slru_sample


class NameSlruMetricGroup(MetricGroupDef):
    """
    Metric group used by pg_stat_slru graph.
    """

    name = "slru_name"
    xaxis = "name"
    data_url = r"/server/(\d+)/metrics/slru/([a-zA-Z]+)"
    blks_zeroed = MetricDef(
        label="Zeroed",
        type="sizerate",
        desc="Number of blocks zeroed during initializations",
    )
    blks_hit = MetricDef(
        label="Hit",
        type="sizerate",
        desc="Number of times disk blocks were found already"
        " in the SLRU, so that a read was not necessary"
        " (this only includes hits in the SLRU, not the"
        " operating system's file system cache)",
    )
    blks_read = MetricDef(
        label="Read",
        type="sizerate",
        desc="Number of disk blocks read for this SLRU",
    )
    blks_written = MetricDef(
        label="Written",
        type="sizerate",
        desc="Number of disk blocks written for this SLRU",
    )
    blks_exists = MetricDef(
        label="Exists",
        type="sizerate",
        desc="Number of blocks checked for existence for this SLRU",
    )
    flushes = MetricDef(
        label="Flushes",
        type="number",
        desc="Number of flushes of dirty data for this SLRU",
    )
    truncates = MetricDef(
        label="Truncates",
        type="number",
        desc="Number of truncates for this SLRU",
    )

    @classmethod
    def _get_metrics(cls, handler, **params):
        base = cls.metrics.copy()

        pg_version_num = handler.get_pg_version_num(handler.path_args[0])
        # if we can't connect to the remote server, assume pg13 or more
        if pg_version_num is not None and pg_version_num < 130000:
            return {}
        return base

    @property
    def query(self):
        query = powa_get_slru_sample("name = %(slru)s")

        from_clause = query

        cols = [
            "sub.srvid",
            "extract(epoch FROM sub.ts) AS ts",
            sum_per_sec("blks_zeroed"),
            sum_per_sec("blks_hit"),
            sum_per_sec("blks_read"),
            sum_per_sec("blks_written"),
            sum_per_sec("blks_exists"),
            sum_per_sec("flushes"),
            sum_per_sec("truncates"),
        ]

        return """SELECT {cols}
        FROM (
            {from_clause}
        ) AS sub
        WHERE sub.mesure_interval != '0 s'
        GROUP BY sub.srvid, sub.ts, sub.mesure_interval
        ORDER BY sub.ts""".format(
            cols=", ".join(cols),
            from_clause=from_clause,
        )


class ByAllSlruMetricGroup2(ByAllSlruMetricGroup):
    """
    Metric group used by pg_stat_slru grid.

    There isn't a lot of SLRU, so we want to display all lines even in the
    per-SLRU view so users can easily navigate to another one.  Neither the
    backend nor the frontend can handle a metric group used in different
    dashboard, so duplicate it with the bare minimum different information to
    make it work.  It's not a big problem since this is a different page, so we
    won't end up running the same query twice.
    """

    name = "slru_by_name2"
    data_url = r"/server/(\d+)/metrics/slru_by_name2/([a-zA-Z]+)"


class ByNameSlruOverview(DashboardPage):
    """
    Per SLRU Dashboard page.
    """

    base_url = r"/server/(\d+)/metrics/slru/([a-zA-Z]+)/overview/"
    datasources = [NameSlruMetricGroup, ByAllSlruMetricGroup2]
    params = ["server", "slru"]
    parent = ServerOverview
    title = 'Activity for "%(slru)s" SLRU'
    timeline = ConfigChangesGlobal
    timeline_params = ["server"]

    def dashboard(self):
        # This COULD be initialized in the constructor, but tornado < 3 doesn't
        # call it
        if getattr(self, "_dashboard", None) is not None:
            return self._dashboard

        graphs = [
            [
                Graph(
                    "%(slru)s SLRU (per second)",
                    metrics=NameSlruMetricGroup.all(self),
                )
            ],
            [
                Grid(
                    "All SLRUs",
                    columns=[
                        {
                            "name": "name",
                            "label": "SLRU name",
                            "url_attr": "url",
                        }
                    ],
                    metrics=ByAllSlruMetricGroup2.all(self),
                )
            ],
        ]

        self._dashboard = Dashboard(self.title, graphs)
        return self._dashboard
