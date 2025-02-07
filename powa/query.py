"""
Dashboard for the by-query page.
"""

from powa.config import ConfigChangesQuery
from powa.dashboards import (
    ContentWidget,
    Dashboard,
    DashboardPage,
    Graph,
    Grid,
    MetricDef,
    MetricGroupDef,
    TabContainer,
)
from powa.database import DatabaseOverview
from powa.sql import (
    get_any_sample_query,
    get_hypoplans,
    get_plans,
    possible_indexes,
    qualstat_get_figures,
    resolve_quals,
)
from powa.sql.utils import block_size, byte_per_sec, sum_per_sec, to_epoch, wps
from powa.sql.views import QUALSTAT_FILTER_RATIO, qualstat_getstatdata
from powa.sql.views_graph import (
    kcache_getstatdata_sample,
    powa_getstatdata_sample,
    powa_getwaitdata_sample,
)
from powa.sql.views_grid import (
    powa_getstatdata_detailed_db,
    powa_getwaitdata_detailed_db,
)
from psycopg2 import Error
from tornado.web import HTTPError


class QueryOverviewMetricGroup(MetricGroupDef):
    """
    Metric Group for the graphs on the by query page.
    """

    name = "query_overview"
    xaxis = "ts"
    data_url = r"/server/(\d+)/metrics/database/([^\/]+)/query/(-?\d+)"
    rows = MetricDef(
        label="#Rows",
        desc="Sum of the number of rows returned by the query per second",
    )
    calls = MetricDef(
        label="#Calls",
        desc="Number of time the query has been executed per second",
    )
    shared_blks_read = MetricDef(
        label="Shared read",
        type="sizerate",
        desc="Amount of data found in OS cache or read from disk",
    )
    shared_blks_hit = MetricDef(
        label="Shared hit",
        type="sizerate",
        desc="Amount of data found in shared buffers",
    )
    shared_blks_dirtied = MetricDef(
        label="Shared dirtied",
        type="sizerate",
        desc="Amount of data modified in shared buffers",
    )
    shared_blks_written = MetricDef(
        label="Shared written",
        type="sizerate",
        desc="Amount of shared buffers written to disk",
    )
    local_blks_read = MetricDef(
        label="Local read",
        type="sizerate",
        desc="Amount of local buffers found from OS cache or read from disk",
    )
    local_blks_hit = MetricDef(
        label="Local hit",
        type="sizerate",
        desc="Amount of local buffers found in shared buffers",
    )
    local_blks_dirtied = MetricDef(
        label="Local dirtied",
        type="sizerate",
        desc="Amount of data modified in local buffers",
    )
    local_blks_written = MetricDef(
        label="Local written",
        type="sizerate",
        desc="Amount of local buffers written to disk",
    )
    temp_blks_read = MetricDef(
        label="Temp read",
        type="sizerate",
        desc="Amount of data read from temporary file",
    )
    temp_blks_written = MetricDef(
        label="Temp written",
        type="sizerate",
        desc="Amount of data written to temporary file",
    )
    shared_blk_read_time = MetricDef(
        label="Shared Read time",
        type="duration",
        desc="Time spent reading shared blocks",
    )
    shared_blk_write_time = MetricDef(
        label="Shared Write time",
        type="duration",
        desc="Time spent shared blocks",
    )
    local_blk_read_time = MetricDef(
        label="Local Read time",
        type="duration",
        desc="Time spent reading temp table blocks",
    )
    local_blk_write_time = MetricDef(
        label="Local Write time",
        type="duration",
        desc="Time spent temp table blocks",
    )
    temp_blk_read_time = MetricDef(
        label="Temp Read time",
        type="duration",
        desc="Time spent reading temp file blocks",
    )
    temp_blk_write_time = MetricDef(
        label="Temp Write time",
        type="duration",
        desc="Time spent temp file blocks",
    )
    avg_plantime = MetricDef(
        label="Avg plantime",
        type="duration",
        desc="Average query planning duration",
    )
    avg_runtime = MetricDef(
        label="Avg runtime", type="duration", desc="Average query duration"
    )
    hit_ratio = MetricDef(
        label="Shared buffers hit ratio",
        type="percent",
        desc="Percentage of data found in shared buffers",
    )
    miss_ratio = MetricDef(
        label="Shared buffers miss ratio",
        type="percent",
        desc="Percentage of data found in OS cache or read from disk",
    )
    wal_records = MetricDef(
        label="#Wal records",
        type="integer",
        desc="Amount of WAL records generated",
    )
    wal_fpi = MetricDef(
        label="#Wal FPI",
        type="integer",
        desc="Amount of WAL full-page images generated",
    )
    wal_bytes = MetricDef(
        label="Wal bytes", type="size", desc="Amount of WAL bytes generated"
    )

    reads = MetricDef(
        label="Physical read",
        type="sizerate",
        desc="Amount of data read from disk",
    )
    writes = MetricDef(
        label="Physical writes",
        type="sizerate",
        desc="Amount of data written to disk",
    )
    user_time = MetricDef(
        label="CPU user time / Query time",
        type="percent",
        desc="CPU time spent executing the query",
    )
    system_time = MetricDef(
        label="CPU system time / Query time",
        type="percent",
        desc="CPU time used by the OS",
    )
    other_time = MetricDef(
        label="CPU other time / Query time",
        type="percent",
        desc="Time spent otherwise",
    )
    sys_hit_ratio = MetricDef(
        label="System cache hit ratio",
        type="percent",
        desc="Percentage of data found in OS cache",
    )
    disk_hit_ratio = MetricDef(
        label="Disk hit ratio",
        type="percent",
        desc="Percentage of data read from disk",
    )
    minflts = MetricDef(
        label="Soft page faults",
        type="number",
        desc="Memory pages not found in the processor's MMU",
    )
    majflts = MetricDef(
        label="Hard page faults",
        type="number",
        desc="Memory pages not found in memory and loaded from storage",
    )
    # not maintained on GNU/Linux, and not available on Windows
    # nswaps = MetricDef(label="Swaps", type="number")
    # msgsnds = MetricDef(label="IPC messages sent", type="number")
    # msgrcvs = MetricDef(label="IPC messages received", type="number")
    # nsignals = MetricDef(label="Signals received", type="number")
    nvcsws = MetricDef(
        label="Voluntary context switches",
        type="number",
        desc="Number of voluntary context switches",
    )
    nivcsws = MetricDef(
        label="Involuntary context switches",
        type="number",
        desc="Number of involuntary context switches",
    )
    jit_functions = MetricDef(
        label="# of JIT functions",
        type="integer",
        desc="Total number of emitted functions",
    )
    jit_generation_time = MetricDef(
        label="JIT generation time",
        type="duration",
        desc="Total time spent generating code",
    )
    jit_inlining_count = MetricDef(
        label="# of JIT inlining",
        type="integer",
        desc="Number of queries where inlining was done",
    )
    jit_inlining_time = MetricDef(
        label="JIT inlining time",
        type="duration",
        desc="Total time spent inlining code",
    )
    jit_optimization_count = MetricDef(
        label="# of JIT optimization",
        type="integer",
        desc="Number of queries where optimization was done",
    )
    jit_optimization_time = MetricDef(
        label="JIT optimization time",
        type="duration",
        desc="Total time spent optimizing code",
    )
    jit_emission_count = MetricDef(
        label="# of JIT emission",
        type="integer",
        desc="Number of queries where emission was done",
    )
    jit_emission_time = MetricDef(
        label="JIT emission time",
        type="duration",
        desc="Total time spent emitting code",
    )
    jit_deform_count = MetricDef(
        label="# of JIT tuple deforming",
        type="integer",
        desc="Number of queries where tuple deforming was done",
    )
    jit_deform_time = MetricDef(
        label="JIT tuple deforming time",
        type="duration",
        desc="Total time spent deforming tuple",
    )
    jit_expr_time = MetricDef(
        label="JIT expression generation time",
        type="duration",
        desc="Total time spent generating expressions",
    )

    @classmethod
    def _get_metrics(cls, handler, **params):
        base = cls.metrics.copy()
        if not handler.has_extension(params["server"], "pg_stat_kcache"):
            for key in (
                "reads",
                "writes",
                "user_time",
                "system_time",
                "other_time",
                "sys_hit_ratio",
                "disk_hit_ratio",
                "minflts",
                "majflts",
                # "nswaps", "msgsnds", "msgrcvs", "nsignals",
                "nvcsws",
                "nivcsws",
            ):
                base.pop(key)
        else:
            base.pop("miss_ratio")

        if not handler.has_extension_version(
            params["server"], "pg_stat_statements", "1.8"
        ):
            for key in ("avg_plantime", "wal_records", "wal_fpi", "wal_bytes"):
                base.pop(key)

        if not handler.has_extension_version(
            handler.path_args[0], "pg_stat_statements", "1.10"
        ):
            for key in (
                "jit_functions",
                "jit_generation_time",
                "jit_inlining_count",
                "jit_inlining_time",
                "jit_optimization_count",
                "jit_optimization_time",
                "jit_emission_count",
                "jit_emission_time",
            ):
                base.pop(key)

        if not handler.has_extension_version(
            handler.path_args[0], "pg_stat_statements", "1.11"
        ):
            for key in (
                "jit_deform_count",
                "jit_deform_time",
                "jit_expr_time",
            ):
                base.pop(key)

        return base

    @property
    def query(self):
        query = powa_getstatdata_sample(
            "query", ["datname = %(database)s", "queryid = %(query)s"]
        )

        total_blocks = "(sum(shared_blks_read) + sum(shared_blks_hit))"

        cols = [
            to_epoch("ts"),
            sum_per_sec("rows"),
            sum_per_sec("calls"),
            "CASE WHEN {total_blocks} = 0 THEN 0 ELSE"
            " sum(shared_blks_hit)::numeric * 100 / {total_blocks}"
            "END AS hit_ratio".format(total_blocks=total_blocks),
            byte_per_sec("shared_blks_read"),
            byte_per_sec("shared_blks_hit"),
            byte_per_sec("shared_blks_dirtied"),
            byte_per_sec("shared_blks_written"),
            byte_per_sec("local_blks_read"),
            byte_per_sec("local_blks_hit"),
            byte_per_sec("local_blks_dirtied"),
            byte_per_sec("local_blks_written"),
            byte_per_sec("temp_blks_read"),
            byte_per_sec("temp_blks_written"),
            sum_per_sec("shared_blk_read_time"),
            sum_per_sec("shared_blk_write_time"),
            sum_per_sec("local_blk_read_time"),
            sum_per_sec("local_blk_write_time"),
            sum_per_sec("temp_blk_read_time"),
            sum_per_sec("temp_blk_write_time"),
            "sum(runtime) / greatest(sum(calls), 1) AS avg_runtime",
        ]

        if self.has_extension_version(
            self.path_args[0], "pg_stat_statements", "1.8"
        ):
            cols.extend(
                [
                    "sum(plantime) / greatest(sum(calls), 1) AS avg_plantime",
                    sum_per_sec("wal_records"),
                    sum_per_sec("wal_fpi"),
                    sum_per_sec("wal_bytes"),
                ]
            )

        if self.has_extension_version(
            self.path_args[0], "pg_stat_statements", "1.10"
        ):
            cols.extend(
                [
                    sum_per_sec("jit_functions"),
                    sum_per_sec("jit_generation_time"),
                    sum_per_sec("jit_inlining_count"),
                    sum_per_sec("jit_inlining_time"),
                    sum_per_sec("jit_optimization_count"),
                    sum_per_sec("jit_optimization_time"),
                    sum_per_sec("jit_emission_count"),
                    sum_per_sec("jit_emission_time"),
                ]
            )

        if self.has_extension_version(
            self.path_args[0], "pg_stat_statements", "1.11"
        ):
            cols.extend(
                [
                    sum_per_sec("jit_deform_count"),
                    sum_per_sec("jit_deform_time"),
                    sum_per_sec(
                        "jit_generation_time - jit_deform_time",
                        alias="jit_expr_time",
                    ),
                ]
            )

        from_clause = query
        if self.has_extension(self.path_args[0], "pg_stat_kcache"):
            # Add system metrics from pg_stat_kcache,
            # and detailed hit ratio.
            kcache_query = kcache_getstatdata_sample(
                "query", ["datname = %(database)s", "queryid = %(query)s"]
            )

            sys_hits = (
                "greatest(sum(shared_blks_read) - sum(sub.reads), 0)"
                " * block_size"
            )
            sys_hit_ratio = (
                "{sys_hits}::numeric * 100 / ({total_blocks}"
                " * block_size)".format(
                    sys_hits=sys_hits, total_blocks=total_blocks
                )
            )
            disk_hit_ratio = (
                "sum(sub.reads) * 100 / ({total_blocks} * block_size)".format(
                    total_blocks=total_blocks
                )
            )
            total_time = "greatest(sum(runtime), 1)"
            other_time = (
                "sum(runtime) - (((sum(user_time) + sum(system_time))) * 1000)"
            )

            # Rusage can return values > real time due to sampling bias
            # aligned to kernel ticks. As such, we have to clamp values to 100%
            def total_time_percent(col, alias=None, noalias=False):
                val = "least(100, ({col} * 100) / {total_time})".format(
                    col=col, total_time=total_time
                )

                if not noalias:
                    val += " as " + alias

                return val

            cols.extend(
                [
                    sum_per_sec("reads"),
                    sum_per_sec("writes"),
                    sum_per_sec("minflts"),
                    sum_per_sec("majflts"),
                    # sum_per_sec("nswaps"),
                    # sum_per_sec("msgsnds"),
                    # sum_per_sec("msgrcvs"),
                    # sum_per_sec("nsignals"),
                    sum_per_sec("nvcsws"),
                    sum_per_sec("nivcsws"),
                    total_time_percent("sum(user_time) * 1000", "user_time"),
                    total_time_percent(
                        "sum(system_time) * 1000", "system_time"
                    ),
                    "greatest({other}, 0) AS other_time".format(
                        other=total_time_percent(other_time, noalias=True)
                    ),
                    "CASE WHEN {tb} = 0 THEN 0 ELSE {dhr} END AS disk_hit_ratio".format(
                        tb=total_blocks, dhr=disk_hit_ratio
                    ),
                    "CASE WHEN {tb} = 0 THEN 0 ELSE {shr} END AS sys_hit_ratio".format(
                        tb=total_blocks, shr=sys_hit_ratio
                    ),
                ]
            )

            from_clause = """SELECT *
                FROM (
                    {from_clause}
                ) sub2
                LEFT JOIN (
                    {kcache_query}
                ) AS kc
                    USING (ts, srvid, queryid, userid, dbid)""".format(
                from_clause=from_clause, kcache_query=kcache_query
            )
        else:
            cols.extend(
                [
                    """CASE WHEN {tb} = 0 THEN 0
                    ELSE sum(shared_blks_read)::numeric * 100 / {tb}
                END AS miss_ratio""".format(tb=total_blocks)
                ]
            )

        return """SELECT {cols}
        FROM (
            {from_clause}
        ) AS sub
        CROSS JOIN {bs}
        WHERE calls != 0
        GROUP BY ts, block_size, mesure_interval
        ORDER BY ts""".format(
            cols=", ".join(cols), from_clause=from_clause, bs=block_size
        )


class QueryIndexes(ContentWidget):
    """
    Content widget showing index creation suggestion.
    """

    data_url = r"/server/(\d+)/metrics/database/([^\/]+)/query/(-?\d+)/indexes"
    title = "Index Suggestions"

    def get(self, srvid, database, query):
        if not self.has_extension(srvid, "pg_qualstats"):
            raise HTTPError(501, "PG qualstats is not installed")

        try:
            # Check remote access first
            remote_conn = self.connect(
                srvid, database=database, remote_access=True
            )
        except Exception as e:
            raise HTTPError(
                501, "Could not connect to remote server: %s" % str(e)
            )

        extra_join = """,
        LATERAL unnest(quals) AS qual"""
        base_query = qualstat_getstatdata(
            extra_join=extra_join,
            extra_where=["queryid = " + query],
            extra_having=[
                "bool_or(eval_type = 'f')",
                "sum(execution_count) > 1000",
                "sum(occurences) > 0",
                QUALSTAT_FILTER_RATIO + " > 0.5",
            ],
        )
        optimizable = list(
            self.execute(
                base_query,
                params={
                    "server": srvid,
                    "query": query,
                    "from": "-infinity",
                    "to": "infinity",
                },
            )
        )
        optimizable = resolve_quals(remote_conn, optimizable, "quals")
        hypoplan = None
        indexes = {}
        for qual in optimizable:
            indexes[qual.where_clause] = possible_indexes(qual)
        hypo_version = self.has_extension_version(
            srvid, "hypopg", "0.0.3", database=database
        )
        if indexes and hypo_version:
            # identify indexes
            # create them
            allindexes = [
                ind
                for indcollection in indexes.values()
                for ind in indcollection
            ]
            for ind in allindexes:
                (sql, params) = ind.hypo_ddl
                if sql is not None:
                    try:
                        ind.name = self.execute(
                            sql,
                            params=params,
                            srvid=srvid,
                            database=database,
                            remote_access=True,
                        )[0]["indexname"]
                    except Error as e:
                        self.flash(
                            "Could not create hypothetical index: %s" % str(e)
                        )
            # Build the query and fetch the plans
            querystr = get_any_sample_query(
                self,
                srvid,
                database,
                query,
                self.get_argument("from"),
                self.get_argument("to"),
            )
            try:
                hypoplan = get_hypoplans(
                    remote_conn.cursor(), querystr, allindexes
                )
            except Error as e:
                # TODO: offer the possibility to fill in parameters from the UI
                self.flash(
                    "We couldn't get plans for this query, presumably "
                    "because some parameters are missing: %s" % str(e)
                )

        self.render_json(dict(indexes=indexes, hypoplan=hypoplan))


class QueryExplains(ContentWidget):
    """
    Content widget showing explain plans for various const values.
    """

    title = "Example Values"
    data_url = (
        r"/server/(\d+)/metrics/database/([^\/]+)/query/(-?\d+)/explains"
    )

    def get(self, server, database, query):
        if not self.has_extension(server, "pg_qualstats"):
            raise HTTPError(501, "PG qualstats is not installed")

        plans = []
        row = qualstat_get_figures(
            self,
            server,
            database,
            self.get_argument("from"),
            self.get_argument("to"),
            queries=[query],
        )
        if row is not None:
            plans = get_plans(self, server, database, row["query"], row)

        if len(plans) == 0:
            self.render_json(None)
            return

        self.render_json([plan._asdict() for plan in plans])


class WaitsQueryOverviewMetricGroup(MetricGroupDef):
    """
    Metric Group for the wait event graph on the by query page.
    """

    name = "waits_query_overview"
    xaxis = "ts"
    data_url = r"/server/(\d+)/metrics/database/([^\/]+)/query/(-?\d+)/wait_events_sampled"
    # pg 9.6 only metrics
    count_lwlocknamed = MetricDef(
        label="Lightweight Named",
        desc="Number of named lightweight lock wait events",
    )
    count_lwlocktranche = MetricDef(
        label="Lightweight Tranche",
        desc="Number of lightweight lock tranche wait events",
    )
    # pg 10+ metrics
    count_lwlock = MetricDef(
        label="Lightweight Lock",
        desc="Number of wait events due to lightweight locks",
    )
    count_lock = MetricDef(
        label="Lock", desc="Number of wait events due to heavyweight locks"
    )
    count_bufferpin = MetricDef(
        label="Buffer pin", desc="Number of wait events due to buffer pin"
    )
    count_activity = MetricDef(
        label="Activity",
        desc="Number of wait events due to postgres"
        " internal processes activity",
    )
    count_client = MetricDef(
        label="Client", desc="Number of wait events due to client activity"
    )
    count_extension = MetricDef(
        label="Extension",
        desc="Number wait events due to third-party extensions",
    )
    count_ipc = MetricDef(
        label="IPC",
        desc="Number of wait events due to inter-process communication",
    )
    count_timeout = MetricDef(
        label="Timeout", desc="Number of wait events due to timeouts"
    )
    count_io = MetricDef(
        label="IO", desc="Number of wait events due to IO operations"
    )

    def prepare(self):
        if not self.has_extension(self.path_args[0], "pg_wait_sampling"):
            raise HTTPError(501, "pg_wait_sampling is not installed")

    @property
    def query(self):
        query = powa_getwaitdata_sample(
            "query", ["datname = %(database)s", "queryid = %(query)s"]
        )
        cols = [to_epoch("ts")]

        pg_version_num = self.get_pg_version_num(self.path_args[0])
        # if we can't connect to the remote server, assume pg10 or above
        if pg_version_num is not None and pg_version_num < 100000:
            cols += [
                wps("count_lwlocknamed", do_sum=False),
                wps("count_lwlocktranche", do_sum=False),
                wps("count_lock", do_sum=False),
                wps("count_bufferpin", do_sum=False),
            ]
        else:
            cols += [
                wps("count_lwlock", do_sum=False),
                wps("count_lock", do_sum=False),
                wps("count_bufferpin", do_sum=False),
                wps("count_activity", do_sum=False),
                wps("count_client", do_sum=False),
                wps("count_extension", do_sum=False),
                wps("count_ipc", do_sum=False),
                wps("count_timeout", do_sum=False),
                wps("count_io", do_sum=False),
            ]

        from_clause = query

        return """SELECT {cols}
        FROM (
            {from_clause}
        ) AS sub
        -- WHERE count IS NOT NULL
        ORDER BY ts""".format(cols=", ".join(cols), from_clause=from_clause)


class WaitSamplingList(MetricGroupDef):
    """
    Datasource used for the wait events grid.
    """

    name = "query_wait_events"
    xaxis = "event"
    axis_type = "category"
    data_url = (
        r"/server/(\d+)/metrics/database/([^\/]+)/query/(-?\d+)/wait_events"
    )
    counts = MetricDef(
        label="# of events", type="integer", direction="descending"
    )

    def prepare(self):
        if not self.has_extension(self.path_args[0], "pg_wait_sampling"):
            raise HTTPError(501, "pg_wait_sampling is not installed")

    @property
    def query(self):
        # Working from the waitdata detailed_db base query
        inner_query = powa_getwaitdata_detailed_db()

        cols = [
            "queryid",
            "ps.query",
            "event_type",
            "event",
            "sum(count) AS counts",
        ]

        from_clause = """(
                {inner_query}
            ) AS sub
            JOIN {{powa}}.powa_statements AS ps
                USING (srvid, queryid, dbid)""".format(inner_query=inner_query)

        return """SELECT {cols}
        FROM {from_clause}
        WHERE datname = %(database)s AND queryid = %(query)s
        GROUP BY queryid, query, event_type, event
        ORDER BY sum(count) DESC""".format(
            cols=", ".join(cols), from_clause=from_clause
        )


class QualList(MetricGroupDef):
    """
    Datasource used for the Qual table.
    """

    name = "query_quals"
    xaxis = "relname"
    axis_type = "category"
    data_url = r"/server/(\d+)/metrics/database/([^\/]+)/query/(-?\d+)/quals"
    filter_ratio = MetricDef(
        label="Avg filter_ratio (excluding index)", type="percent"
    )
    execution_count = MetricDef(
        label="Execution count (excluding index)", type="integer"
    )

    def prepare(self):
        if not self.has_extension(self.path_args[0], "pg_qualstats"):
            raise HTTPError(501, "PG qualstats is not installed")

    @property
    def query(self):
        base = qualstat_getstatdata(extra_where=["queryid = %(query)s"])
        return base

    def post_process(self, data, server, database, query, **kwargs):
        try:
            remote_conn = self.connect(
                server, database=database, remote_access=True
            )
        except Exception as e:
            raise HTTPError(
                501, "Could not connect to remote server: %s" % str(e)
            )

        data["data"] = resolve_quals(remote_conn, data["data"])
        for qual in data["data"]:
            qual.url = self.reverse_url(
                "QualOverview", server, database, query, qual.qualid
            )
        return data


class QueryDetail(ContentWidget):
    """
    Detail widget showing summarized information for the query.
    """

    title = "Query Detail"
    data_url = r"/server/(\d+)/metrics/database/([^\/]+)/query/(-?\d+)/detail"

    def get(self, srvid, database, query):
        stmt = powa_getstatdata_detailed_db(
            srvid, ["datname = %(database)s", "queryid = %(query)s"]
        )

        from_clause = """{{powa}}.powa_statements AS ps
        LEFT JOIN (
            {stmt}
        ) AS sub USING (queryid, dbid, userid)
        CROSS JOIN {block_size}""".format(stmt=stmt, block_size=block_size)

        rblk = "(sum(shared_blks_read) * block_size)"
        wblk = "(sum(shared_blks_hit) * block_size)"
        cols = [
            "query",
            "sum(calls) AS calls",
            "sum(runtime) AS runtime",
            rblk + " AS shared_blks_read",
            wblk + " AS shared_blks_hit",
            rblk + " + " + wblk + " AS total_blks",
        ]

        stmt = """SELECT {cols}
        FROM {from_clause}
        WHERE sub.queryid = %(query)s
        AND sub.srvid = %(server)s
        GROUP BY query, block_size""".format(
            cols=", ".join(cols), from_clause=from_clause
        )

        value = self.execute(
            stmt,
            params={
                "server": srvid,
                "query": query,
                "database": database,
                "from": self.get_argument("from"),
                "to": self.get_argument("to"),
            },
        )
        if value is None or len(value) < 1:
            self.render_json(None)
            return
        self.render_json(value[0])


class QueryOverview(DashboardPage):
    """
    Dashboard page for a query.
    """

    base_url = r"/server/(\d+)/database/([^\/]+)/query/(-?\d+)/overview"
    params = ["server", "database", "query"]
    datasources = [
        QueryOverviewMetricGroup,
        WaitsQueryOverviewMetricGroup,
        QueryDetail,
        QueryExplains,
        QueryIndexes,
        WaitSamplingList,
        QualList,
        ConfigChangesQuery,
    ]
    parent = DatabaseOverview
    title = "Query Overview"
    timeline = ConfigChangesQuery

    def dashboard(self):
        # This COULD be initialized in the constructor, but tornado < 3 doesn't
        # call it
        if getattr(self, "_dashboard", None) is not None:
            return self._dashboard

        pgss18 = self.has_extension_version(
            self.path_args[0], "pg_stat_statements", "1.8"
        )
        pgss110 = self.has_extension_version(
            self.path_args[0], "pg_stat_statements", "1.10"
        )
        pgss111 = self.has_extension_version(
            self.path_args[0], "pg_stat_statements", "1.11"
        )

        hit_ratio_graph = Graph(
            "Hit ratio",
            metrics=[QueryOverviewMetricGroup.hit_ratio],
            renderer="bar",
            stack=True,
            color_scheme=["#73c03a", "#65b9ac", "#cb513a"],
        )

        gen_metrics = [
            QueryOverviewMetricGroup.avg_runtime,
            QueryOverviewMetricGroup.rows,
            QueryOverviewMetricGroup.calls,
        ]
        if pgss18:
            gen_metrics.extend([QueryOverviewMetricGroup.avg_plantime])

        dashes = []
        dashes.append(
            Dashboard(
                "Query detail", [[Graph("General", metrics=gen_metrics)]]
            )
        )

        if pgss18:
            # Add WALs graphs
            wals_graphs = [
                [
                    Graph(
                        "WAL activity",
                        metrics=[
                            QueryOverviewMetricGroup.wal_records,
                            QueryOverviewMetricGroup.wal_fpi,
                            QueryOverviewMetricGroup.wal_bytes,
                        ],
                    ),
                ]
            ]
            dashes.append(Dashboard("WALs", wals_graphs))

        # Add JIT graphs
        if pgss110:
            jit_tim = [
                QueryOverviewMetricGroup.jit_inlining_time,
                QueryOverviewMetricGroup.jit_optimization_time,
                QueryOverviewMetricGroup.jit_emission_time,
            ]

            if pgss111:
                jit_tim.extend(
                    [
                        QueryOverviewMetricGroup.jit_deform_time,
                        QueryOverviewMetricGroup.jit_expr_time,
                    ]
                )
            else:
                jit_tim.append(QueryOverviewMetricGroup.jit_generation_time)

            jit_cnt = [
                QueryOverviewMetricGroup.jit_functions,
                QueryOverviewMetricGroup.jit_inlining_count,
                QueryOverviewMetricGroup.jit_optimization_count,
                QueryOverviewMetricGroup.jit_emission_count,
            ]

            if pgss111:
                jit_cnt.append(QueryOverviewMetricGroup.jit_deform_count)

            jit_graphs = [
                [Graph("JIT timing", metrics=jit_tim, stack=True)],
                [Graph("JIT scheduling", metrics=jit_cnt)],
            ]

            dashes.append(Dashboard("JIT", jit_graphs))

        dashes.append(
            Dashboard(
                "PG Cache",
                [
                    [
                        Graph(
                            "Shared block (in Bps)",
                            metrics=[
                                QueryOverviewMetricGroup.shared_blks_read,
                                QueryOverviewMetricGroup.shared_blks_hit,
                                QueryOverviewMetricGroup.shared_blks_dirtied,
                                QueryOverviewMetricGroup.shared_blks_written,
                            ],
                        ),
                        Graph(
                            "Local block (in Bps)",
                            metrics=[
                                QueryOverviewMetricGroup.local_blks_read,
                                QueryOverviewMetricGroup.local_blks_hit,
                                QueryOverviewMetricGroup.local_blks_dirtied,
                                QueryOverviewMetricGroup.local_blks_written,
                            ],
                        ),
                        Graph(
                            "Temp block (in Bps)",
                            metrics=[
                                QueryOverviewMetricGroup.temp_blks_read,
                                QueryOverviewMetricGroup.temp_blks_written,
                            ],
                        ),
                    ]
                ],
            )
        )

        io_time_metrics = [
            QueryOverviewMetricGroup.shared_blk_read_time,
            QueryOverviewMetricGroup.shared_blk_write_time,
        ]

        # if we can't connect to the remote server, assume pg16 or below
        if pgss111:
            io_time_metrics.extend(
                [
                    QueryOverviewMetricGroup.local_blk_read_time,
                    QueryOverviewMetricGroup.local_blk_write_time,
                    QueryOverviewMetricGroup.temp_blk_read_time,
                    QueryOverviewMetricGroup.temp_blk_write_time,
                ]
            )
        iodash = Dashboard(
            "IO",
            [
                [
                    hit_ratio_graph,
                    Graph(
                        "Read / Write time",
                        url=self.docs_stats_url + "pg_stat_statements.html",
                        metrics=io_time_metrics,
                    ),
                ]
            ],
        )
        dashes.append(iodash)

        if self.has_extension(self.path_args[0], "pg_stat_kcache"):
            iodash.widgets.extend(
                [
                    [
                        Graph(
                            "Physical block (in Bps)",
                            url=self.docs_stats_url + "pg_stat_kcache.html",
                            metrics=[
                                QueryOverviewMetricGroup.reads,
                                QueryOverviewMetricGroup.writes,
                            ],
                        ),
                        Graph(
                            "CPU Time repartition",
                            url=self.docs_stats_url + "pg_stat_kcache.html",
                            metrics=[
                                QueryOverviewMetricGroup.user_time,
                                QueryOverviewMetricGroup.system_time,
                                QueryOverviewMetricGroup.other_time,
                            ],
                            renderer="bar",
                            stack=True,
                            color_scheme=["#73c03a", "#cb513a", "#65b9ac"],
                        ),
                    ]
                ]
            )
            hit_ratio_graph.metrics.append(
                QueryOverviewMetricGroup.sys_hit_ratio
            )
            hit_ratio_graph.metrics.append(
                QueryOverviewMetricGroup.disk_hit_ratio
            )

            sys_graphs = [
                Graph(
                    "System resources (events per sec)",
                    url=self.docs_stats_url + "pg_stat_kcache.html",
                    metrics=[
                        QueryOverviewMetricGroup.majflts,
                        QueryOverviewMetricGroup.minflts,
                        # QueryOverviewMetricGroup.nswaps,
                        # QueryOverviewMetricGroup.msgsnds,
                        # QueryOverviewMetricGroup.msgrcvs,
                        # QueryOverviewMetricGroup.nsignals,
                        QueryOverviewMetricGroup.nvcsws,
                        QueryOverviewMetricGroup.nivcsws,
                    ],
                )
            ]
            dashes.append(Dashboard("System resources", [sys_graphs]))
        else:
            hit_ratio_graph.metrics.append(QueryOverviewMetricGroup.miss_ratio)

        if self.has_extension(self.path_args[0], "pg_wait_sampling"):
            # Get the metrics depending on the pg server version
            metrics = None
            pg_version_num = self.get_pg_version_num(self.path_args[0])
            # if we can't connect to the remote server, assume pg10 or above
            if pg_version_num is not None and pg_version_num < 100000:
                metrics = [
                    WaitsQueryOverviewMetricGroup.count_lwlocknamed,
                    WaitsQueryOverviewMetricGroup.count_lwlocktranche,
                    WaitsQueryOverviewMetricGroup.count_lock,
                    WaitsQueryOverviewMetricGroup.count_bufferpin,
                ]
            else:
                metrics = [
                    WaitsQueryOverviewMetricGroup.count_lwlock,
                    WaitsQueryOverviewMetricGroup.count_lock,
                    WaitsQueryOverviewMetricGroup.count_bufferpin,
                    WaitsQueryOverviewMetricGroup.count_activity,
                    WaitsQueryOverviewMetricGroup.count_client,
                    WaitsQueryOverviewMetricGroup.count_extension,
                    WaitsQueryOverviewMetricGroup.count_ipc,
                    WaitsQueryOverviewMetricGroup.count_timeout,
                    WaitsQueryOverviewMetricGroup.count_io,
                ]
            dashes.append(
                Dashboard(
                    "Wait Events",
                    [
                        [
                            Graph(
                                "Wait Events (per second)",
                                url=self.docs_stats_url
                                + "pg_wait_sampling.html",
                                metrics=metrics,
                            ),
                            Grid(
                                "Wait events summary",
                                url=self.docs_stats_url
                                + "pg_wait_sampling.html",
                                columns=[
                                    {
                                        "name": "event_type",
                                        "label": "Event Type",
                                    },
                                    {
                                        "name": "event",
                                        "label": "Event",
                                    },
                                ],
                                metrics=WaitSamplingList.all(),
                            ),
                        ]
                    ],
                )
            )

        if self.has_extension(self.path_args[0], "pg_qualstats"):
            dashes.append(
                Dashboard(
                    "Predicates",
                    [
                        [
                            Grid(
                                "Predicates used by this query",
                                columns=[
                                    {
                                        "name": "where_clause",
                                        "label": "Predicate",
                                        "type": "query",
                                        "max_length": 60,
                                        "url_attr": "url",
                                    }
                                ],
                                metrics=QualList.all(),
                            )
                        ],
                        [QueryIndexes],
                        [QueryExplains],
                    ],
                )
            )
        self._dashboard = Dashboard(
            "Query %(query)s on database %(database)s",
            [
                [QueryDetail],
                [
                    TabContainer(
                        "Query %(query)s on database %(database)s", dashes
                    )
                ],
            ],
        )
        return self._dashboard
