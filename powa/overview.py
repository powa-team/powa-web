from powa.dashboards import (
    Dashboard, Graph, Grid,
    MetricGroupDef, MetricDef,
    DashboardPage)
from powa.metrics import Detail, Totals

from powa.sql import *


class ByDatabaseMetricGroup(Detail, MetricGroupDef):
    name = "by_database"
    xaxis = "datname"
    data_url = r"/metrics/by_databases/"
    axis_type = "category"
    io_time = MetricDef(label="I/O time")
    query = text("""
        SELECT datname, sum(total_calls) AS total_calls,
            sum(total_runtime) AS total_runtime,
            round(sum(total_runtime)/sum(total_calls),2) AS avg_runtime,
            sum(total_blks_read) * b.blocksize AS total_blks_read,
            sum(total_blks_hit) * b.blocksize AS total_blks_hit,
            sum(total_blks_dirtied) * b.blocksize AS total_blks_dirtied,
            sum(total_blks_written) * b.blocksize AS total_blks_written,
            sum(total_temp_blks_written) * b.blocksize AS total_temp_blks_written,
            round(sum(total_blk_read_time+total_blk_write_time)::numeric,2) AS io_time
        FROM (
                 SELECT datname, (powa_getstatdata_db(:from, :to, datname)).*
            FROM pg_database
        ) s
        JOIN (SELECT current_setting('block_size')::int AS blocksize) b ON true
        GROUP BY datname, b.blocksize
        ORDER BY sum(total_calls) DESC
    """)

    @classmethod
    def process(cls, handler, val, **kwargs):
        val = dict(val)
        val["url"] = handler.reverse_url("DatabaseOverview", val["datname"])
        return val

class GlobalDatabasesMetricGroup(Totals, MetricGroupDef):
    name = "all_databases"
    data_url = r"/metrics/databases_globals/"

    query = text("""
        SELECT
        extract(epoch from ts) AS ts,
        sum(total_runtime) /  %(tmi)s as avg_runtime,
        sum(shared_blks_read+local_blks_read+temp_blks_read)*blksize/ %(tmi)s  as total_blks_read,
        sum(shared_blks_hit+local_blks_hit)*blksize/ %(tmi)s as total_blks_hit
        FROM (
        SELECT datname, (powa_getstatdata_sample_db(:from, :to, datname::text, 300)).*
        FROM pg_database
        ) s
        , (SELECT current_setting('block_size')::int AS blksize) b
        GROUP BY ts, blksize
        ORDER BY ts
        """ % {"tmi": TOTAL_MEASURE_INTERVAL})


class Overview(DashboardPage):
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
                 "name": "datname",
                 "label": "Database",
                  "url_attr": "url"
               }],
               metrics=ByDatabaseMetricGroup.all())]])
