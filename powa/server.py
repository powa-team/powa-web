"""
Index page presenting an overview of the cluster stats.
"""

from sqlalchemy import and_
from sqlalchemy.sql.functions import sum
from sqlalchemy.sql import select, cast, extract, bindparam
from sqlalchemy.types import Numeric
from powa.framework import AuthHandler
from powa.dashboards import (
    Dashboard, Graph, Grid,
    MetricGroupDef, MetricDef,
    DashboardPage)

from powa.sql.views import (
    powa_getstatdata_db,
    powa_getwaitdata_db,
    powa_getstatdata_sample,
    kcache_getstatdata_sample)
from powa.sql.utils import (total_read, total_hit, mulblock, round, greatest,
                            block_size, inner_cc)
from powa.sql.tables import powa_databases


class ServerSelector(AuthHandler):
    """Page allowing to choose a server."""

    def get(self):
        self.redirect(self.reverse_url(
            'ServerOverview',
            self.get_argument("srvid")))


class ByDatabaseMetricGroup(MetricGroupDef):
    """
    Metric group used by the "by database" grid
    """
    name = "by_database"
    xaxis = "datname"
    data_url = r"/server/(\d+)/metrics/by_databases/"
    axis_type = "category"
    calls = MetricDef(label="#Calls", type="integer", direction="descending")
    runtime = MetricDef(label="Runtime", type="duration")
    avg_runtime = MetricDef(label="Avg runtime", type="duration")
    shared_blks_read = MetricDef(label="Blocks read", type="size")
    shared_blks_hit = MetricDef(label="Blocks hit", type="size")
    shared_blks_dirtied = MetricDef(label="Blocks dirtied", type="size")
    shared_blks_written = MetricDef(label="Blocks written", type="size")
    temp_blks_written = MetricDef(label="Temp Blocks written", type="size")
    io_time = MetricDef(label="I/O time", type="duration")
    params = ["server"]

    @property
    def query(self):
        bs = block_size.c.block_size
        inner_query = powa_getstatdata_db(bindparam("server")).alias()
        c = inner_query.c
        from_clause = inner_query.join(
            powa_databases,
            and_(c.dbid == powa_databases.c.oid,
                 c.srvid == powa_databases.c.srvid))

        return (select([
            powa_databases.c.srvid,
            powa_databases.c.datname,
            sum(c.calls).label("calls"),
            sum(c.runtime).label("runtime"),
            round(cast(sum(c.runtime), Numeric) /
                  greatest(sum(c.calls), 1), 2).label("avg_runtime"),
            mulblock(sum(c.shared_blks_read).label("shared_blks_read")),
            mulblock(sum(c.shared_blks_hit).label("shared_blks_hit")),
            mulblock(sum(c.shared_blks_dirtied).label("shared_blks_dirtied")),
            mulblock(sum(c.shared_blks_written).label("shared_blks_written")),
            mulblock(sum(c.temp_blks_written).label("temp_blks_written")),
            round(cast(sum(c.blk_read_time + c.blk_write_time),
                       Numeric), 2).label("io_time")
        ])
                .select_from(from_clause)
                .order_by(sum(c.calls).desc())
                .group_by(powa_databases.c.srvid,
                          powa_databases.c.datname, bs))

    def process(self, val, **kwargs):
        val = dict(val)
        val["url"] = self.reverse_url("DatabaseOverview", val["srvid"],
                                      val["datname"])
        return val


class ByDatabaseWaitSamplingMetricGroup(MetricGroupDef):
    """
    Metric group used by the "wait sampling by database" grid
    """
    name = "wait_sampling_by_database"
    xaxis = "datname"
    data_url = r"/server/(\d+)/metrics/wait_event_by_databases/"
    axis_type = "category"
    counts = MetricDef(label="# of events",
                       type="integer", direction="descending")

    @property
    def query(self):
        inner_query = powa_getwaitdata_db(bindparam("server")).alias()
        c = inner_query.c
        from_clause = inner_query.join(
            powa_databases,
            and_(c.dbid == powa_databases.c.oid,
                 c.srvid == powa_databases.c.srvid))

        return (select([
            powa_databases.c.srvid,
            powa_databases.c.datname,
            c.event_type, c.event,
            sum(c.count).label("counts"),
        ])
            .select_from(from_clause)
            .order_by(sum(c.count).desc())
            .group_by(powa_databases.c.srvid, powa_databases.c.datname,
                      c.event_type, c.event))

    def process(self, val, **kwargs):
        val = dict(val)
        val["url"] = self.reverse_url("DatabaseOverview",
                                      val["srvid"], val["datname"])
        return val


class GlobalDatabasesMetricGroup(MetricGroupDef):
    """
    Metric group used by summarized graphs.
    """
    name = "all_databases"
    data_url = r"/server/(\d+)/metrics/databases_globals/"
    avg_runtime = MetricDef(label="Avg runtime", type="duration")
    load = MetricDef(label="Runtime per sec", type="duration")
    total_blks_hit = MetricDef(label="Total hit", type="sizerate")
    total_blks_read = MetricDef(label="Total read", type="sizerate")

    @property
    def query(self):
        bs = block_size.c.block_size
        query = powa_getstatdata_sample("db", bindparam("server"))
        query = query.alias()
        c = query.c
        return (select([c.srvid,
                extract("epoch", c.ts).label("ts"),
                (sum(c.runtime) / greatest(sum(c.calls), 1)).label("avg_runtime"),
                (sum(c.runtime) / greatest(extract("epoch", c.mesure_interval),1)).label("load"),
                total_read(c),
                total_hit(c)])
            .where(c.calls is not None)
            .group_by(c.srvid, c.ts, bs, c.mesure_interval)
            .order_by(c.ts)
            .params(samples=100))



class ServerOverview(DashboardPage):
    """
    ServerOverview dashboard page.
    """
    base_url = r"/server/(\d+)/overview/"
    datasources = [GlobalDatabasesMetricGroup, ByDatabaseMetricGroup,
                   ByDatabaseWaitSamplingMetricGroup]
    params = ["server"]
    title = "All databases"

    def dashboard(self):
        # This COULD be initialized in the constructor, but tornado < 3 doesn't
        # call it
        if getattr(self, '_dashboard', None) is not None:
            return self._dashboard

        dashes = [[Graph("Query runtime per second (all databases)",
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
                        metrics=ByDatabaseMetricGroup.all())]]

        if self.has_extension(self.path_args[0], "pg_wait_sampling"):
            dashes.append([Grid("Wait events for all databases",
                                columns=[{
                                    "name": "datname",
                                    "label": "Database",
                                    "url_attr": "url"
                                }, {
                                    "name": "event_type",
                                    "label": "Event Type",
                                }, {
                                    "name": "event",
                                    "label": "Event",
                                }],
                                metrics=ByDatabaseWaitSamplingMetricGroup.
                                all())])

        self._dashboard = Dashboard("All databases", dashes)
        return self._dashboard

    @classmethod
    def breadcrum_title(cls, handler, param):
        return handler.deparse_srvid(param["server"])

    @classmethod
    def get_childmenu(cls, handler, params):
        from powa.database import DatabaseOverview
        children = []
        for d in list(handler.get_databases(params["server"])):
            new_params = params.copy()
            new_params["database"] = d
            children.append(DatabaseOverview.get_selfmenu(handler, new_params))
        return children
