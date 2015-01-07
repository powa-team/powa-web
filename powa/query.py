"""
Dashboard for the by-query page.
"""

from tornado.web import HTTPError
from sqlalchemy.sql import (
    bindparam, text, column, select, table,
    literal_column, case, cast)
from sqlalchemy.sql.functions import sum
from sqlalchemy.types import Numeric

from powa.dashboards import (
    Dashboard, Graph, Grid,
    MetricGroupDef, MetricDef,
    DashboardPage, ContentWidget)
from powa.database import DatabaseOverview

from powa.sql import (Plan, format_jumbled_query,
                      resolve_quals, aggregate_qual_values,
                      suggest_indexes)
from powa.sql.views import powa_getstatdata_sample
from powa.sql.utils import block_size, mulblock, greatest, to_epoch


class QueryOverviewMetricGroup(MetricGroupDef):
    """
    Metric Group for the graphs on the by query page.
    """
    name = "query_overview"
    xaxis = "ts"
    data_url = r"/metrics/database/(\w+)/query/(\w+)"
    rows = MetricDef(label="#Rows")
    calls = MetricDef(label="#Calls")
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
    avg_runtime = MetricDef(label="Avg runtime", type="duration")
    kreads = MetricDef(label="Physical read", type="sizerate")
    kwrites = MetricDef(label="Physical writes", type="sizerate")
    kuser_time = MetricDef(label="CPU user time", type="percent")
    ksystem_time = MetricDef(label="CPU system time", type="percent")
    hit_ratio = MetricDef(label="Shared buffers hit ratio", type="percent")
    miss_ratio = MetricDef(label="Shared buffers miss ratio", type="percent")
    sys_hit_ratio = MetricDef(label="System cache hit ratio", type="percent")
    disk_hit_ratio = MetricDef(label="Disk hit ratio", type="percent")

    _KCACHE_QUERY = text("""
    (
        WITH src AS (
            SELECT md5(r.rolname||d.datname||s.query) AS md5query, queryid
            FROM pg_stat_statements s
                JOIN pg_database d ON d.oid = s.dbid
                JOIN pg_roles r ON r.oid = s.userid
            WHERE md5(r.rolname||d.datname||s.query) = :query
        )
        SELECT ts,
            reads_raw * 512 as kreads,
            writes_raw * 512 as kwrites,
            user_time as kuser_time,
            system_time as ksystem_time
        FROM src
        JOIN (SELECT current_setting('block_size')::numeric AS blksize) setting ON true,
        LATERAL (SELECT * FROM public.powa_kcache_getstatdata_sample(tstzrange(:from, :to), src.queryid, 300)) sample
        WHERE reads_raw IS NOT NULL
    ) as kcache
    """)

    @classmethod
    def _get_metrics(cls, handler, **params):
        base = cls.metrics.copy()
        if not handler.has_extension("pg_stat_kcache"):
            for key in ("kreads", "kwrites", "kuser_time", "ksystem_time",
                        "sys_hit_ratio", "disk_hit_ratio"):
                base.pop(key)
        else:
            base.pop("miss_ratio")

        return base

    @property
    def query(self):
        query = powa_getstatdata_sample("query")
        query = query.where(
            (column("dbname") == bindparam("database")) &
            (column("md5query") == bindparam("query")))
        query = query.alias()
        c = query.c
        total_blocks = ((c.shared_blks_read + c.shared_blks_hit)
                        .label("total_blocks"))
        cols = [to_epoch(c.ts),
                c.rows,
                c.calls,
                case([(total_blocks == 0, 0)],
                     else_=cast(c.shared_blks_hit, Numeric) * 100 / total_blocks
                     ).label("hit_ratio"),
                mulblock(c.shared_blks_read),
                mulblock(c.shared_blks_hit),
                mulblock(c.shared_blks_dirtied),
                mulblock(c.shared_blks_written),
                mulblock(c.local_blks_read),
                mulblock(c.local_blks_hit),
                mulblock(c.local_blks_dirtied),
                mulblock(c.local_blks_written),
                mulblock(c.temp_blks_read),
                mulblock(c.temp_blks_written),
                c.blk_read_time,
                c.blk_write_time,
                (c.runtime / greatest(c.calls, 1)).label("avg_runtime")]

        from_clause = query
        if self.has_extension("pg_stat_kcache"):
            # Add system metrics from pg_stat_kcache,
            # and detailed hit ratio.
            sys_hits = (greatest(mulblock(c.shared_blks_read) -
                              literal_column("kcache.kreads"), 0)
                        .label("kcache_hitblocks"))
            sys_hitratio = (cast(sys_hits, Numeric) * 100 /
                            mulblock(total_blocks))
            disk_hit_ratio = (literal_column("kcache.kreads") /
                              mulblock(total_blocks))
            cols.extend([
                literal_column("kcache.kreads"),
                literal_column("kcache.kwrites"),
                literal_column("kcache.kuser_time"),
                literal_column("kcache.ksystem_time"),
                case([(total_blocks == 0, 0)],
                     else_=disk_hit_ratio).label("disk_hit_ratio"),
                case([(total_blocks == 0, 0)],
                     else_=sys_hitratio).label("sys_hit_ratio")])
            from_clause = query.join(
                self._KCACHE_QUERY,
                literal_column("kcache.ts") == c.ts)
        else:
            cols.extend([
                case([(total_blocks == 0, 0)],
                     else_=cast(c.shared_blks_read, Numeric) * 100 / total_blocks
                     ).label("miss_ratio")
            ])

        return (select(cols)
                .select_from(from_clause)
                .where(c.calls != None)
                .order_by(c.ts)
                .params(samples=100))


class QueryIndexes(ContentWidget):
    """
    Content widget showing index creation suggestion.
    """

    data_url = r"/metrics/database/(\w+)/query/(\w+)/indexes"
    title = "Query Indexes"

    def get(self, database, query):
        if not self.has_extension("pg_qualstats"):
            raise HTTPError(501, "PG qualstats is not installed")

        indexes = suggest_indexes(self, database, query)

        self.render("database/query/indexes.html", indexes=indexes)


class QueryExplains(ContentWidget):
    """
    Content widget showing explain plans for various const values.
    """
    title = "Query Explains"
    data_url = r"/metrics/database/(\w+)/query/(\w+)/explains"

    def get(self, database, query):
        if not self.has_extension("pg_qualstats"):
            raise HTTPError(501, "PG qualstats is not installed")

        sql = (aggregate_qual_values(
            text("""s.dbname = :database AND s.md5query = :query
                 AND coalesce_range && tstzrange(:from, :to)"""))
            .with_only_columns(['quals',
                                'query',
                                'to_json(mf) as "most filtering"',
                                'to_json(lf) as "least filtering"',
                                'to_json(me) as "most executed"']))
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
            self.flash("No quals found for this query", "warning")
            self.render("xhr.html", content="")
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

    def process(self, val, database=None, query=None, **kwargs):
        row = dict(val)
        row['url'] = self.reverse_url('QualOverview', database, query,
                                      row['nodehash'])
        return row

    def post_process(self, data, database, query, **kwargs):
        conn = self.connect(database=database)
        data["data"] = resolve_quals(conn, data["data"])
        return data


class QueryDetail(ContentWidget):
    """
    Detail widget showing summarized information for the query.
    """
    title = "Query Detail"
    data_url = r"/metrics/database/(\w+)/query/(\w+)/detail"

    def get(self, database, query):
        bs = block_size.c.block_size
        stmt = powa_getstatdata_sample("query")
        stmt = stmt.where(
            (column("dbname") == bindparam("database")) &
            (column("md5query") == bindparam("query")))
        stmt = stmt.alias()
        c = stmt.c
        rblk = mulblock(sum(c.shared_blks_read).label("shared_blks_read"))
        wblk = mulblock(sum(c.shared_blks_hit).label("shared_blks_hit"))
        stmt = (select([
            column("query"),
            sum(c.calls).label("calls"),
            sum(c.runtime).label("runtime"),
            rblk,
            wblk,
            (rblk + wblk).label("total_blks")])
            .select_from(stmt.join(
                table("powa_statements"),
                c.md5query == literal_column('powa_statements.md5query')))
            .group_by(column("query"), bs)
            .params(samples=1))

        value = self.execute(stmt, params={
            "query": query,
            "database": database,
            "from": self.get_argument("from"),
            "to": self.get_argument("to")
        })
        if value.rowcount < 1:
            self.render("xhr.html", content="No data")
            return
        self.render("database/query/detail.html", stats=value.first())


class QueryOverview(DashboardPage):
    """
    Dashboard page for a query.
    """
    base_url = r"/database/(\w+)/query/(\w+)/overview"
    params = ["database", "query"]
    datasources = [QueryOverviewMetricGroup, QueryDetail,
                   QueryExplains, QueryIndexes, QualList]
    parent = DatabaseOverview

    def __init__(self, *args, **kwargs):
        self._dashboard = None
        super(QueryOverview, self).__init__(*args, **kwargs)

    @classmethod
    def get_menutitle(cls, handler, params):
        return "Query detail"

    @property
    def dashboard(self):
        if self._dashboard:
            return self._dashboard
        hit_ratio_graph = Graph("Hit ratio",
                                metrics=[QueryOverviewMetricGroup.hit_ratio],
                                renderer="bar",
                                stack=True)
        self._dashboard = Dashboard(
            "Query %(query)s on database %(database)s",
            [[QueryDetail],
             [Graph("General",
                    metrics=[QueryOverviewMetricGroup.avg_runtime,
                             QueryOverviewMetricGroup.rows,
                             QueryOverviewMetricGroup.calls]),
              hit_ratio_graph],
             [Graph("Shared block (in Bps)",
                    metrics=[QueryOverviewMetricGroup.shared_blks_read,
                             QueryOverviewMetricGroup.shared_blks_hit,
                             QueryOverviewMetricGroup.shared_blks_dirtied,
                             QueryOverviewMetricGroup.shared_blks_written]),
              Graph("Local block (in Bps)",
                    metrics=[QueryOverviewMetricGroup.local_blks_read,
                             QueryOverviewMetricGroup.local_blks_hit,
                             QueryOverviewMetricGroup.local_blks_dirtied,
                             QueryOverviewMetricGroup.local_blks_written]),
              Graph("Temp block (in Bps)",
                    metrics=[QueryOverviewMetricGroup.temp_blks_read,
                             QueryOverviewMetricGroup.temp_blks_written])],
             [Graph("Read / Write time",
                    metrics=[QueryOverviewMetricGroup.blk_read_time,
                             QueryOverviewMetricGroup.blk_write_time])]])
        if self.has_extension("pg_stat_kcache"):
            self._dashboard.widgets.extend([[
                Graph("Physical block (in Bps)",
                      metrics=[QueryOverviewMetricGroup.kreads,
                               QueryOverviewMetricGroup.kwrites]),
                Graph("CPU time",
                      metrics=[QueryOverviewMetricGroup.kuser_time,
                               QueryOverviewMetricGroup.ksystem_time])]])
            hit_ratio_graph.metrics.append(QueryOverviewMetricGroup.sys_hit_ratio)
            hit_ratio_graph.metrics.append(QueryOverviewMetricGroup.disk_hit_ratio)
        else:
            hit_ratio_graph.metrics.append(QueryOverviewMetricGroup.miss_ratio)

        if self.has_extension("pg_qualstats"):
            self._dashboard.widgets.extend([[
                Grid("Predicates used by this query",
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
                [QueryIndexes],
                [QueryExplains]])
        return self._dashboard
