from powa.framework import AuthHandler
from powa.dashboards import (
    Dashboard, Graph, Grid,
    MetricGroupDef, MetricDef,
    DashboardPage,
    DashboardHandler)
from tornado.web import URLSpec

from powa.sql import *

from powa.metrics import Detail, Totals


class DatabaseSelector(AuthHandler):

    def get(self):
        self.redirect(self.reverse_url(
            'DatabaseOverview',
             self.get_argument("database")))

class DatabaseOverviewMetricGroup(Totals, MetricGroupDef):
    name = "database_overview"
    xaxis = "ts"
    data_url = r"/metrics/database_overview/(\w+)/"
    # TODO: refactor with GlobalDatabasesMetricGroup
    query = text("""
        SELECT
        extract(epoch from ts) AS ts,
        sum(total_runtime) /  %(tmi)s as avg_runtime,
        sum(shared_blks_read+local_blks_read+temp_blks_read)*blksize/ %(tmi)s  as total_blks_read,
        sum(shared_blks_hit+local_blks_hit)*blksize/ %(tmi)s as total_blks_hit
        FROM
          powa_getstatdata_sample_db(:from, :to, :database, 300)
        , (SELECT current_setting('block_size')::int AS blksize) b
        GROUP BY ts, blksize
        ORDER BY ts
        """ % {"tmi": TOTAL_MEASURE_INTERVAL})

class ByQueryMetricGroup(Detail, MetricGroupDef):
    name = "all_queries"
    xaxis = "md5query"
    axis_type = "category"
    data_url = r"/metrics/database_all_queries/(\w+)/"
    total_blk_read_time = MetricDef(label="Block read time", type="duration")
    total_blk_write_time = MetricDef(label="Block write time", type="duration")
    # TODO: refactor with GlobalDatabasesMetricGroup
    query = text("""
        SELECT total_calls, total_runtime,
            total_runtime/total_calls AS avg_runtime,
            total_blks_read * b.blocksize AS total_blks_read,
            total_blks_hit * b.blocksize AS total_blks_hit,
            total_blks_dirtied * b.blocksize AS total_blks_dirtied,
            total_blks_written * b.blocksize AS total_blks_written,
            total_temp_blks_read * b.blocksize AS total_temp_blks_read,
            total_temp_blks_written * b.blocksize AS total_temp_blks_written,
            coalesce(total_blk_read_time, 0) AS total_blk_read_time,
            coalesce(total_blk_write_time, 0) AS total_blk_write_time,
            md5query,
            query
                 FROM powa_getstatdata_detailed_db(:from, :to, :database) s
        JOIN (SELECT current_setting('block_size')::int AS blocksize) b ON true
        ORDER BY total_calls DESC
    """)

    @classmethod
    def process(cls, handler, val, database=None, **kwargs):
        val = dict(val)
        val["url"] = handler.reverse_url("QueryOverview", database, val["md5query"])
        return val


class DatabaseOverview(DashboardPage):
    base_url = r"/database/(\w+)/overview"
    datasources = [DatabaseOverviewMetricGroup, ByQueryMetricGroup]
    params = ["database"]
    dashboard = Dashboard(
        "Database overview for %(database)s",
        [[Graph("Calls (On database %(database)s)",
                metrics=[DatabaseOverviewMetricGroup.avg_runtime]),
          Graph("Blocks (On database %(database)s)",
                metrics=[DatabaseOverviewMetricGroup.total_blks_read,
                        DatabaseOverviewMetricGroup.total_blks_hit])],
         [Grid("Details for all queries",
               x_label="Query",
               columns=[{
                "name": "query",
                "label": "Query",
                "cell": "query",
                "url_attr": "url"
               }],
               metrics=ByQueryMetricGroup.all())]])
