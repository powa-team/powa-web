"""
Dashboard for the by-query page.
"""

from powa.dashboards import (
    Dashboard, Graph, Grid,
    MetricGroupDef, MetricDef,
    DashboardPage, ContentWidget)
from powa.metrics import Totals
from powa.database import DatabaseOverview
from sqlalchemy.sql import literal_column, bindparam, func, text
from tornado.web import HTTPError

from powa.sql import (Plan, format_jumbled_query,
                      resolve_quals, aggregate_qual_values)

MEASURE_INTERVAL = """
extract (epoch FROM CASE WHEN total_mesure_interval = '0 second' THEN '1 second'::interval ELSE total_mesure_interval END)
"""

class QueryOverviewMetricGroup(Totals, MetricGroupDef):
    """
    Metric Group for the graphs on the by query page.
    """
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


class QueryExplains(ContentWidget):
    """
    Content widget showing explain plans for various const values.
    """

    data_url = r"/metrics/database/(\w+)/query/(\w+)/explains"

    def get(self, database, query):
        if not self.has_extension("pg_qualstats"):
            raise HTTPError(501, "PG qualstats is not installed")

        sql = aggregate_qual_values(
            text("""s.dbname = :database AND s.md5query = :query
                 AND coalesce_range && tstzrange(:from, :to)"""))
        params = {"database": database, "query": query,
                  "from": self.get_argument("from"),
                  "to": self.get_argument("to")}
        quals = self.execute(sql, params=params)
        plans = []
        if quals.rowcount > 0:
            row = quals.first()
            for key in ('most filtering', 'least filtering', 'most executed'):
                vals = row[key]
                query = format_jumbled_query(row['query'], vals['constants'])
                plan = "N/A"
                try:
                    result = self.execute("EXPLAIN %s" % query,
                                          database=database)
                    plan = "\n".join(v[0] for v in result)
                except:
                    pass
                plans.append(Plan(key, vals['constants'], query,
                                  plan, vals["filter_ratio"], vals['count']))
        if len(plans) == 0:
            self.flash("No quals found for this query", "warning");
            self.render("xhr.html", content="");
            return

        self.render("database/query/explains.html", plans=plans)


class QualList(MetricGroupDef):
    """
    Datasource used for the Qual table.
    """
    name = "query_quals"
    xaxis = "quals"
    axis_type = "category"
    data_url = r"/metrics/database/(\w+)/query/(\w+)/quals"
    filter_ratio = MetricDef(label="Avg filter_ratio (excluding index)")
    count = MetricDef(label="Execution count (excluding index)")

    query = text("""
        SELECT
            to_json(quals) as quals,
            filter_ratio,
            count,
            nodehash
        FROM powa_qualstats_statements,
        LATERAL powa_qualstats_getstatdata_sample(tstzrange(:from, :to), queryid, 1)
        WHERE md5query = :query
    """)

    @classmethod
    def prepare(cls, handler, **kwargs):
        if not handler.has_extension("pg_qualstats"):
            raise HTTPError(501, "PG Qualstats is not available")

    @classmethod
    def process(cls, handler, val, database=None, query=None, **kwargs):
        row = dict(val)
        row['url'] = handler.reverse_url('QualOverview', database, query,
                                         row['nodehash'])
        return row


    @classmethod
    def post_process(cls, handler, data, database, query, **kwargs):
        conn = handler.connect(database=database)
        data["data"] = resolve_quals(conn, data["data"])
        return data


class QueryDetail(ContentWidget):
    """
    Detail widget showing summarized information for the query.
    """

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
    """
    Dashboard page for a query.
    """
    base_url = r"/database/(\w+)/query/(\w+)/overview"
    params = ["database", "query"]
    datasources = [QueryOverviewMetricGroup, QueryDetail,
                   QueryExplains, QualList]
    parent = DatabaseOverview
    dashboard = Dashboard(
        "Query %(query)s on database %(database)s",
        [[QueryDetail("Query Detail")],
         [Graph("General",
                metrics=[QueryOverviewMetricGroup.avg_runtime,
                         QueryOverviewMetricGroup.rows]),
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
         [Grid("Predicates used by this query",
               columns=[{
                   "name": "where_clause",
                   "label": "Predicate",
                   "type": "query",
                   "max_length": 60,
                   "url_attr": "url"
               }, {
                   "name": "eval_type",
                   "label": "Eval Type"
               }],
               metrics=QualList.all())],
         [QueryExplains("Query Explains")]])

    @classmethod
    def get_menutitle(cls, handler, params):
        return "Query detail"
