"""
Module containing the by-database dashboard.
"""
from powa.framework import AuthHandler
from powa.dashboards import (
    Dashboard, Graph, Grid,
    MetricGroupDef, MetricDef,
    DashboardPage)

from powa.sql import text, TOTAL_MEASURE_INTERVAL
from powa.overview import Overview

from powa.metrics import Detail, Totals


class DatabaseSelector(AuthHandler):
    """Page allowing to choose a database."""

    def get(self):
        self.redirect(self.reverse_url(
            'DatabaseOverview',
            self.get_argument("database")))


class DatabaseOverviewMetricGroup(Totals, MetricGroupDef):
    """Metric group for the database global graphs."""
    name = "database_overview"
    xaxis = "ts"
    data_url = r"/metrics/database_overview/(\w+)/"
    # TODO: refactor with GlobalDatabasesMetricGroup


    query = text("""
        SELECT
        extract(epoch from ts) AS ts,
        sum(total_runtime) /  %(tmi)s as avg_runtime,
        sum(shared_blks_read+local_blks_read+temp_blks_read)*blksize/ %(tmi)s
                 as total_blks_read,
        sum(shared_blks_hit+local_blks_hit)*blksize/ %(tmi)s as total_blks_hit
        FROM
          powa_getstatdata_sample_db(:from, :to, :database, 300)
        , (SELECT current_setting('block_size')::int AS blksize) b
        GROUP BY ts, blksize
        ORDER BY ts
        """ % {"tmi": TOTAL_MEASURE_INTERVAL})


class ByQueryMetricGroup(Detail, MetricGroupDef):
    """Metric group for indivual query stats (displayed on the grid)."""
    name = "all_queries"
    xaxis = "md5query"
    axis_type = "category"
    data_url = r"/metrics/database_all_queries/(\w+)/"
    total_blk_read_time = MetricDef(label="Block read time", type="duration")
    total_blk_write_time = MetricDef(label="Block write time", type="duration")
    # TODO: refactor with GlobalDatabasesMetricGroup
    query = text("""
            SELECT total_calls, total_runtime::numeric,
            total_runtime/total_calls::numeric AS avg_runtime,
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

    def process(self, val, database=None, **kwargs):
        val = dict(val)
        val["url"] = self.reverse_url(
            "QueryOverview", database, val["md5query"])
        return val


class DatabaseOverview(DashboardPage):
    """DatabaseOverview Dashboard."""
    base_url = r"/database/(\w+)/overview"
    datasources = [DatabaseOverviewMetricGroup, ByQueryMetricGroup]
    params = ["database"]
    parent = Overview
    dashboard = Dashboard(
        "Database overview for %(database)s",
        [[Graph("Calls (On database %(database)s)",
                metrics=[DatabaseOverviewMetricGroup.avg_runtime]),
          Graph("Blocks (On database %(database)s)",
                metrics=[DatabaseOverviewMetricGroup.total_blks_read,
                         DatabaseOverviewMetricGroup.total_blks_hit])],
         [Grid("Details for all queries",
               columns=[{
                   "name": "query",
                   "label": "Query",
                   "type": "query",
                   "url_attr": "url",
                   "max_length": 70
               }],
               metrics=ByQueryMetricGroup.all())]])

    @classmethod
    def get_menutitle(cls, handler, params):
        return params.get("database")
