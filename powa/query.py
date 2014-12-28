from powa.dashboards import (
    Dashboard, Graph, Grid,
    MetricGroupDef, MetricDef,
    DashboardPage, ContentWidget)
from powa.metrics import Detail, Totals
from powa.framework import AuthHandler
from tornado.web import HTTPError

from powa.sql import *

MEASURE_INTERVAL = """
extract (epoch FROM CASE WHEN total_mesure_interval = '0 second' THEN '1 second'::interval ELSE total_mesure_interval END)
"""

class QueryOverviewMetricGroup(Totals, MetricGroupDef):
    name = "query_overview"
    xaxis = "ts"
    data_url = r"/metrics/database/(\w+)/query/(\w+)"
    rows = MetricDef(label="#Rows")
    shared_blks_read = MetricDef(label="Shared read", type="sizerate")
    shared_blks_hit = MetricDef(label="Shared hit", type="sizerate")
    shared_blks_dirtied = MetricDef(label="Shared dirtied", type="sizerate")
    shared_blks_written = MetricDef(label="Shared written", type="sizerate")
    local_blks_read = MetricDef(label="Local read", type="sizerate")
    local_blks_hit = MetricDef(label="Local hit", type="sizerate")
    local_blks_dirtied = MetricDef(label="Local dirtied", type="sizerate")
    local_blks_written = MetricDef(label="Local written", type="sizerate")
    temp_blks_read = MetricDef(label="Temp read", type="sizerate")
    temp_blks_written = MetricDef(label="Temp written", type="sizerate")
    blk_read_time = MetricDef(label="Read time", type="duration")
    blk_write_time = MetricDef(label="Write time", type="duration")


    total_temp_blks_written = MetricDef(label="Temp Blocks written", type="size")
    # TODO: refactor with GlobalDatabasesMetricGroup
    query = text("""
        SELECT
        extract(epoch from ts) AS ts,
        rows as rows,
        total_calls as total_calls,
        total_runtime as total_runtime,
        round((total_runtime/CASE total_calls WHEN 0 THEN 1 ELSE total_calls END)::numeric,2)::float as avg_runtime,
        (shared_blks_read * blksize) / %(mi)s  as shared_blks_read,
        (shared_blks_hit * blksize) / %(mi)s  as shared_blks_hit,
        (shared_blks_dirtied * blksize) / %(mi)s  as shared_blks_dirtied,
        (shared_blks_written * blksize) / %(mi)s  as shared_blks_written,
        (local_blks_read * blksize) / %(mi)s  as local_blks_read,
        (local_blks_hit * blksize) / %(mi)s  as local_blks_hit,
        (local_blks_dirtied * blksize) / %(mi)s  as local_blks_dirtied,
        (local_blks_written * blksize) / %(mi)s  as local_blks_written,
        (temp_blks_read * blksize) / %(mi)s  as temp_blks_read,
        (temp_blks_written * blksize) / %(mi)s  as temp_blks_written,
        blk_read_time as blk_read_time,
        blk_write_time as blk_write_time
        FROM
          powa_getstatdata_sample(:from, :to, :query, 300)
        , (SELECT current_setting('block_size')::int AS blksize) b
        ORDER BY ts
        """ % {"mi": MEASURE_INTERVAL})



class QueryQualsMetricGroup(MetricGroupDef):
    name = "query_quals_overview"
    xaxis = "ts"
    data_url = r"/metrics/database/(\w+)/query/(\w+)/quals"
    avg_exec_by_call = MetricDef(label="Avg number of qual execution by query execution")

    query = text("""
        SELECT extract(epoch from pgqs.ts) as ts,
                 (CASE WHEN sum(total_calls) = 0 THEN 0 ELSE sum(count) / sum(total_calls) END)::float as avg_exec_by_call
        FROM powa_qualstats_getstatdata_sample(tstzrange(:from, :to), :query, 300) as pgqs
        JOIN powa_getstatdata_sample(:from, :to, :query, 300) as pgss ON pgss.ts = pgqs.ts
        GROUP BY pgqs.ts
    """)


class QueryIndexes(ContentWidget):

    data_url = r"/metrics/database/(\w+)/query/(\w+)/indexes"

    def get(self, database, query):
        if not self.has_extension("pg_qualstats"):
            self.flash("Install the pg_qualstats extension for more info !")
            self.render("xhr.html")
            return
        self.render("database/query/indexes.html")


class QueryDetail(ContentWidget):

    data_url = r"/metrics/database/(\w+)/query/(\w+)/detail"

    DETAIL_QUERY = text("""
        SELECT query,
             sum(total_calls) as total_calls,
             to_timestamp(sum(total_runtime)) as total_runtime,
             sum(shared_blks_read * blksize) as total_read_blocks,
             sum(shared_blks_hit * blksize) as total_hit_blocks,
             sum((shared_blks_read + shared_blks_hit) * blksize) as total_blocks
        FROM powa_statements,
        powa_getstatdata_sample(:from, :to, :query, 300),
        (SELECT current_setting('block_size')::int AS blksize) b
        WHERE md5query = :query AND dbname = :database
        GROUP BY query
    """)

    def get(self, database, query):
        value = self.execute(self.DETAIL_QUERY, params={
            "query": query,
            "database": database,
            "from": self.get_argument("from"),
            "to": self.get_argument("to")
        })
        if value.rowcount < 1:
            raise HTTPError(404)
        self.render("database/query/detail.html", stats=value.first())


class QueryOverview(DashboardPage):
    base_url = r"/database/(\w+)/query/(\w+)/overview"
    params = ["database", "query"]
    datasources = [QueryOverviewMetricGroup, QueryQualsMetricGroup, QueryDetail,
                   QueryIndexes]
    dashboard = Dashboard(
        "Query %(query)s on database %(database)s",
        [[QueryDetail("Query Detail")],
            [Graph("General",
                metrics=[QueryOverviewMetricGroup.avg_runtime,
                         QueryOverviewMetricGroup.rows
                         ]),
          Graph("Shared block (in Bps)",
                metrics=[QueryOverviewMetricGroup.shared_blks_read,
                         QueryOverviewMetricGroup.shared_blks_hit,
                         QueryOverviewMetricGroup.shared_blks_dirtied,
                         QueryOverviewMetricGroup.shared_blks_written])],
          [Graph("Local block (in Bps)",
                metrics=[QueryOverviewMetricGroup.local_blks_read,
                         QueryOverviewMetricGroup.local_blks_hit,
                         QueryOverviewMetricGroup.local_blks_dirtied,
                         QueryOverviewMetricGroup.local_blks_written]),
          Graph("Temp block (in Bps)",
                metrics=[QueryOverviewMetricGroup.temp_blks_read,
                         QueryOverviewMetricGroup.temp_blks_written]),
          Graph("Read / Write time",
                metrics=[QueryOverviewMetricGroup.blk_read_time,
                         QueryOverviewMetricGroup.blk_write_time])],
         [QueryIndexes("Query Indexes")]
         ])
