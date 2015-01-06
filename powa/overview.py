"""
Index page presenting an overview of the cluster stats.
"""

from powa.dashboards import (
    Dashboard, Graph, Grid,
    MetricGroupDef, MetricDef,
    DashboardPage)
from powa.metrics import Detail, Totals

from powa.sql import round
from powa.sql.views import (
    block_size, powa_getstatdata_db, mulblock,
    compute_total_statdata_db_samples)
from sqlalchemy.sql.functions import sum
from sqlalchemy.sql import select, cast
from sqlalchemy.types import Numeric


class ByDatabaseMetricGroup(Detail, MetricGroupDef):
    """
    Metric group used by the "by database" grid
    """
    name = "by_database"
    xaxis = "dbname"
    data_url = r"/metrics/by_databases/"
    axis_type = "category"
    io_time = MetricDef(label="I/O time")

    @property
    def query(self):
        bs = block_size.c.block_size
        inner_query = powa_getstatdata_db().alias()
        c = inner_query.c
        return (select([
            c.dbname,
            sum(c.calls).label("calls"),
            sum(c.runtime).label("runtime"),
            round(cast(sum(c.runtime), Numeric) / sum(c.calls), 2).label("avg_runtime"),
            mulblock(sum(c.shared_blks_read).label("shared_blks_read")),
            mulblock(sum(c.shared_blks_hit).label("shared_blks_hit")),
            mulblock(sum(c.shared_blks_dirtied).label("shared_blks_dirtied")),
            mulblock(sum(c.shared_blks_written).label("shared_blks_written")),
            mulblock(sum(c.temp_blks_written).label("temp_blks_written")),
            round(cast(sum(c.blk_read_time + c.blk_write_time), Numeric), 2).label("io_time")
        ])
            .order_by(sum(c.calls).desc())
            .group_by(c.dbname, bs))


    def process(self, val, **kwargs):
        val = dict(val)
        val["url"] = self.reverse_url("DatabaseOverview", val["dbname"])
        return val


class GlobalDatabasesMetricGroup(Totals, MetricGroupDef):
    """
    Metric group used by summarized graphs.
    """
    name = "all_databases"
    data_url = r"/metrics/databases_globals/"

    @property
    def query(self):
        return compute_total_statdata_db_samples()


class Overview(DashboardPage):
    """
    Overview dashboard page.
    """
    base_url = r"/overview/"
    datasources = [GlobalDatabasesMetricGroup, ByDatabaseMetricGroup]
    dashboard = Dashboard(
        "Overview",
        [[Graph("Query runtime per second (all databases)",
                metrics=[GlobalDatabasesMetricGroup.avg_runtime]),
          Graph("Block access in Bps",
                metrics=[GlobalDatabasesMetricGroup.total_blks_hit,
                         GlobalDatabasesMetricGroup.total_blks_read])],
         [Grid("Details for all databases",
               columns=[{
                   "name": "dbname",
                   "label": "Database",
                   "url_attr": "url"
               }],
               metrics=ByDatabaseMetricGroup.all())]])

    @classmethod
    def get_childmenu(cls, handler, params):
        from powa.database import DatabaseOverview
        children = []
        for d in list(handler.databases):
            new_params = params.copy()
            new_params["database"] = d
            children.append(DatabaseOverview.get_selfmenu(handler, new_params))
        return children
