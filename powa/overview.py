"""
Index page presenting an overview of the cluster stats.
"""

from powa.dashboards import (
    Dashboard, Graph, Grid,
    MetricGroupDef, MetricDef,
    DashboardPage)

from powa.sql.views import (
    powa_getstatdata_db,
    powa_getstatdata_sample)
from sqlalchemy.sql.functions import sum
from sqlalchemy.sql import select, cast, extract
from sqlalchemy.types import Numeric
from powa.sql.utils import (total_read, total_hit, mulblock, round, greatest,
                            block_size)
from powa.sql.tables import powa_databases


class ByDatabaseMetricGroup(MetricGroupDef):
    """
    Metric group used by the "by database" grid
    """
    name = "by_database"
    xaxis = "datname"
    data_url = r"/metrics/by_databases/"
    axis_type = "category"
    calls = MetricDef(label="#Calls", type="string", direction="descending")
    runtime = MetricDef(label="Runtime", type="duration")
    avg_runtime = MetricDef(label="Avg runtime", type="duration")
    shared_blks_read = MetricDef(label="Blocks read", type="size")
    shared_blks_hit = MetricDef(label="Blocks hit", type="size")
    shared_blks_dirtied = MetricDef(label="Blocks dirtied", type="size")
    shared_blks_written = MetricDef(label="Blocks written", type="size")
    temp_blks_written = MetricDef(label="Temp Blocks written", type="size")
    io_time = MetricDef(label="I/O time", type="duration")

    @property
    def query(self):
        bs = block_size.c.block_size
        inner_query = powa_getstatdata_db().alias()
        c = inner_query.c
        from_clause = inner_query.join(
            powa_databases,
            c.dbid == powa_databases.c.oid)

        return (select([
            powa_databases.c.datname,
            sum(c.calls).label("calls"),
            sum(c.runtime).label("runtime"),
            round(cast(sum(c.runtime), Numeric) / greatest(sum(c.calls), 1), 2).label("avg_runtime"),
            mulblock(sum(c.shared_blks_read).label("shared_blks_read")),
            mulblock(sum(c.shared_blks_hit).label("shared_blks_hit")),
            mulblock(sum(c.shared_blks_dirtied).label("shared_blks_dirtied")),
            mulblock(sum(c.shared_blks_written).label("shared_blks_written")),
            mulblock(sum(c.temp_blks_written).label("temp_blks_written")),
            round(cast(sum(c.blk_read_time + c.blk_write_time), Numeric), 2).label("io_time")
        ])
            .select_from(from_clause)
            .order_by(sum(c.calls).desc())
            .group_by(powa_databases.c.datname, bs))


    def process(self, val, **kwargs):
        val = dict(val)
        val["url"] = self.reverse_url("DatabaseOverview", val["datname"])
        return val


class GlobalDatabasesMetricGroup(MetricGroupDef):
    """
    Metric group used by summarized graphs.
    """
    name = "all_databases"
    data_url = r"/metrics/databases_globals/"
    avg_runtime = MetricDef(label="Avg runtime", type="duration")
    load = MetricDef(label="Runtime per sec", type="duration")
    total_blks_hit = MetricDef(label="Total hit", type="sizerate")
    total_blks_read = MetricDef(label="Total read", type="sizerate")

    @property
    def query(self):
        bs = block_size.c.block_size
        query = powa_getstatdata_sample("db")
        query = query.alias()
        c = query.c
        return (select([
                extract("epoch", c.ts).label("ts"),
                (sum(c.runtime) / greatest(sum(c.calls), 1)).label("avg_runtime"),
                (sum(c.runtime) / greatest(extract("epoch", c.mesure_interval),1)).label("load"),
                total_read(c),
                total_hit(c)])
            .where(c.calls != None)
            .group_by(c.ts, bs, c.mesure_interval)
            .order_by(c.ts)
            .params(samples=100))



class Overview(DashboardPage):
    """
    Overview dashboard page.
    """
    base_url = r"/overview/"
    datasources = [GlobalDatabasesMetricGroup, ByDatabaseMetricGroup]
    dashboard = Dashboard(
        "All databases",
        [[Graph("Query runtime per second (all databases)",
                metrics=[GlobalDatabasesMetricGroup.avg_runtime,
                         GlobalDatabasesMetricGroup.load]),
          Graph("Block access in Bps",
                metrics=[GlobalDatabasesMetricGroup.total_blks_hit,
                         GlobalDatabasesMetricGroup.total_blks_read],
                color_scheme=['#73c03a','#cb513a'])],
         [Grid("Details for all databases",
               columns=[{
                   "name": "datname",
                   "label": "Database",
                   "url_attr": "url"
               }],
               metrics=ByDatabaseMetricGroup.all())]])

    @classmethod
    def get_menutitle(cls, handler, params):
        return "All databases"

    @classmethod
    def get_childmenu(cls, handler, params):
        from powa.database import DatabaseOverview
        children = []
        for d in list(handler.databases):
            new_params = params.copy()
            new_params["database"] = d
            children.append(DatabaseOverview.get_selfmenu(handler, new_params))
        return children
