"""
Index page presenting an overview of the cluster stats.
"""

from powa.config import ConfigChangesGlobal
from powa.dashboards import (
    Dashboard,
    DashboardPage,
    Graph,
    Grid,
    MetricDef,
    MetricGroupDef,
    TabContainer,
)
from powa.framework import AuthHandler
from powa.io_template import TemplateIoGraph, TemplateIoGrid
from powa.overview import Overview
from powa.sql.utils import (
    block_size,
    byte_per_sec,
    get_ts,
    mulblock,
    sum_per_sec,
    to_epoch,
    total_hit,
    total_read,
    wps,
)
from powa.sql.views_graph import (
    kcache_getstatdata_sample,
    powa_get_all_idx_sample,
    powa_get_all_tbl_sample,
    powa_get_archiver_sample,
    powa_get_bgwriter_sample,
    powa_get_checkpointer_sample,
    powa_get_database_conflicts_sample,
    powa_get_database_sample,
    powa_get_pgsa_sample,
    powa_get_replication_sample,
    powa_get_slru_sample,
    powa_get_subscription_sample,
    powa_get_user_fct_sample,
    powa_get_wal_receiver_sample,
    powa_get_wal_sample,
    powa_getstatdata_sample,
    powa_getwaitdata_sample,
)
from powa.sql.views_grid import (
    powa_getslrudata,
    powa_getstatdata_db,
    powa_getuserfuncdata_db,
    powa_getwaitdata_db,
)
from tornado.web import HTTPError


class ServerSelector(AuthHandler):
    """Page allowing to choose a server."""

    def get(self):
        self.redirect(
            self.reverse_url("ServerOverview", self.get_argument("srvid"))
        )


class ByDatabaseMetricGroup(MetricGroupDef):
    """
    Metric group used by the "by database" grid
    """

    name = "by_database"
    xaxis = "datname"
    data_url = r"/server/(\d+)/metrics/by_databases/"
    axis_type = "category"
    plantime = MetricDef(label="Plantime", type="duration")
    calls = MetricDef(label="#Calls", type="integer", direction="descending")
    runtime = MetricDef(label="Runtime", type="duration")
    avg_runtime = MetricDef(label="Avg runtime", type="duration")
    shared_blks_read = MetricDef(label="Read", type="size")
    shared_blks_hit = MetricDef(label="Hit", type="size")
    shared_blks_dirtied = MetricDef(label="Dirtied", type="size")
    shared_blks_written = MetricDef(label="Written", type="size")
    temp_blks_read = MetricDef(label="Read", type="size")
    temp_blks_written = MetricDef(label="Written", type="size")
    io_time = MetricDef(label="Time", type="duration")
    wal_records = MetricDef(label="#records", type="integer")
    wal_fpi = MetricDef(label="#FPI", type="integer")
    wal_bytes = MetricDef(label="Bytes", type="size")
    jit_functions = MetricDef(label="Functions", type="integer")
    jit_time = MetricDef(label="Time", type="duration")
    params = ["server"]

    @classmethod
    def _get_metrics(cls, handler, **params):
        base = cls.metrics.copy()

        if not handler.has_extension_version(
            handler.path_args[0], "pg_stat_statements", "1.8"
        ):
            for key in ("plantime", "wal_records", "wal_fpi", "wal_bytes"):
                base.pop(key)

        if not handler.has_extension_version(
            handler.path_args[0], "pg_stat_statements", "1.10"
        ):
            base.pop("jit_functions")
            base.pop("jit_time")

        return base

    @property
    def query(self):
        bs = block_size
        inner_query = powa_getstatdata_db("%(server)s")
        from_clause = """({inner_query}) AS sub
        JOIN {{powa}}.powa_databases pd ON pd.oid = sub.dbid
            AND pd.srvid = sub.srvid""".format(inner_query=inner_query)

        cols = [
            "pd.srvid",
            "pd.datname",
            "sum(calls) AS calls",
            "sum(runtime) AS runtime",
            "round(cast(sum(runtime) AS numeric) / greatest(sum(calls), 1), 2) AS avg_runtime",
            mulblock("shared_blks_read", fn="sum"),
            mulblock("shared_blks_hit", fn="sum"),
            mulblock("shared_blks_dirtied", fn="sum"),
            mulblock("shared_blks_written", fn="sum"),
            mulblock("temp_blks_read", fn="sum"),
            mulblock("temp_blks_written", fn="sum"),
            "round(cast(sum(shared_blk_read_time + shared_blk_write_time"
            + " + local_blk_read_time + local_blk_write_time"
            + " + temp_blk_read_time + temp_blk_write_time"
            + ") AS numeric), 2) AS io_time",
        ]

        if self.has_extension_version(
            self.path_args[0], "pg_stat_statements", "1.8"
        ):
            cols.extend(
                [
                    "sum(plantime) AS plantime",
                    "sum(wal_records) AS wal_records",
                    "sum(wal_fpi) AS wal_fpi",
                    "sum(wal_bytes) AS wal_bytes",
                ]
            )

        if self.has_extension_version(
            self.path_args[0], "pg_stat_statements", "1.10"
        ):
            cols.extend(
                [
                    "sum(jit_functions) AS jit_functions",
                    "sum(jit_generation_time + jit_inlining_time"
                    + " + jit_optimization_time + jit_emission_time)"
                    + " AS jit_time",
                ]
            )

        return """SELECT {cols}
        FROM {from_clause}
        CROSS JOIN {bs}
        GROUP BY pd.srvid, pd.datname, block_size""".format(
            cols=", ".join(cols), from_clause=from_clause, bs=bs
        )

    def process(self, val, **kwargs):
        val["url"] = self.reverse_url(
            "DatabaseOverview", val["srvid"], val["datname"]
        )
        return val


class ByDatabaseWaitSamplingMetricGroup(MetricGroupDef):
    """
    Metric group used by the "wait sampling by database" grid
    """

    name = "wait_sampling_by_database"
    xaxis = "datname"
    data_url = r"/server/(\d+)/metrics/wait_event_by_databases/"
    axis_type = "category"
    counts = MetricDef(
        label="# of events", type="integer", direction="descending"
    )

    @property
    def query(self):
        inner_query = powa_getwaitdata_db()

        from_clause = """({inner_query}) AS sub
            JOIN {{powa}}.powa_databases pd ON pd.oid = sub.dbid
            AND pd.srvid = sub.srvid""".format(inner_query=inner_query)

        return """SELECT pd.srvid, pd.datname, sub.event_type, sub.event,
            sum(sub.count) AS counts
            FROM {from_clause}
            GROUP BY pd.srvid, pd.datname, sub.event_type, sub.event
            ORDER BY sum(sub.count) DESC""".format(from_clause=from_clause)

    def process(self, val, **kwargs):
        val["url"] = self.reverse_url(
            "DatabaseOverview", val["srvid"], val["datname"]
        )
        return val


class ByDatabaseUserFuncMetricGroup(MetricGroupDef):
    """
    Metric group used by the pg_stat_user_functions grid
    """

    name = "user_functions_by_database"
    xaxis = "datname"
    data_url = r"/server/(\d+)/metrics/user_functions_by_databases/"
    axis_type = "category"
    calls = MetricDef(
        label="# of calls", type="integer", direction="descending"
    )
    total_time = MetricDef(
        label="Cumulated total execution time", type="duration"
    )
    self_time = MetricDef(
        label="Cumulated self execution time", type="duration"
    )

    @property
    def query(self):
        query = powa_getuserfuncdata_db()

        return query + " ORDER BY calls DESC"

    def process(self, val, **kwargs):
        val["url"] = self.reverse_url(
            "DatabaseOverview", val["srvid"], val["datname"]
        )
        return val


class GlobalDatabasesMetricGroup(MetricGroupDef):
    """
    Metric group used by summarized graphs.
    """

    name = "all_databases"
    xaxis = "ts"
    data_url = r"/server/(\d+)/metrics/databases_globals/"
    avg_runtime = MetricDef(
        label="Avg runtime", type="duration", desc="Average query duration"
    )
    calls = MetricDef(
        label="Queries per sec",
        type="number",
        desc="Number of time the query has been executed",
    )
    planload = MetricDef(
        label="Plantime per sec",
        type="duration",
        desc="Total planning duration",
    )
    load = MetricDef(
        label="Runtime per sec",
        type="duration",
        desc="Total duration of queries executed",
    )
    total_blks_hit = MetricDef(
        label="Total hit",
        type="sizerate",
        desc="Amount of data found in shared buffers",
    )
    total_blks_read = MetricDef(
        label="Total read",
        type="sizerate",
        desc="Amount of data found in OS cache or read from disk",
    )
    wal_records = MetricDef(
        label="#Wal records",
        type="integer",
        desc="Number of WAL records generated",
    )
    wal_fpi = MetricDef(
        label="#Wal FPI",
        type="integer",
        desc="Number of WAL full-page images generated",
    )
    wal_bytes = MetricDef(
        label="Wal bytes", type="size", desc="Amount of WAL bytes generated"
    )

    total_sys_hit = MetricDef(
        label="Total system cache hit",
        type="sizerate",
        desc="Amount of data found in OS cache",
    )
    total_disk_read = MetricDef(
        label="Total disk read",
        type="sizerate",
        desc="Amount of data read from disk",
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
                "total_sys_hit",
                "total_disk_read",
                "minflts",
                "majflts",
                # "nswaps", "msgsnds", "msgrcvs", "nsignals",
                "nvcsws",
                "nivcsws",
            ):
                base.pop(key)
        else:
            base.pop("total_blks_read")

        if not handler.has_extension_version(
            params["server"], "pg_stat_statements", "1.8"
        ):
            for key in ("planload", "wal_records", "wal_fpi", "wal_bytes"):
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
        bs = block_size
        query = powa_getstatdata_sample("db")

        cols = [
            "sub.srvid",
            "extract(epoch FROM ts) AS ts",
            sum_per_sec("calls"),
            "sum(runtime) / greatest(sum(calls), 1) AS avg_runtime",
            sum_per_sec("runtime", alias="load"),
            total_read("sub"),
            total_hit("sub"),
        ]

        if self.has_extension_version(
            self.path_args[0], "pg_stat_statements", "1.8"
        ):
            cols.extend(
                [
                    sum_per_sec("plantime", alias="planload"),
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
            from_clause = "({query}) AS sub2".format(query=query)

            # Add system metrics from pg_stat_kcache,
            kcache_query = kcache_getstatdata_sample("db")

            total_sys_hit = "greatest({total_read} - sum(sub.reads)/ {ts},0) AS total_sys_hit".format(
                total_read=total_read("sub", True), ts=get_ts()
            )
            total_disk_read = (
                "sum(sub.reads) / " + get_ts() + " AS total_disk_read"
            )
            minflts = sum_per_sec("minflts", prefix="sub")
            majflts = sum_per_sec("majflts", prefix="sub")
            # nswaps = sum_per_sec('nswaps', prefix="sub")
            # msgsnds = sum_per_sec('msgsnds', prefix="sub")
            # msgrcvs = sum_per_sec('msgrcvs', prefix="sub")
            # nsignals = sum_per_sec(.nsignals', prefix="sub")
            nvcsws = sum_per_sec("nvcsws", prefix="sub")
            nivcsws = sum_per_sec("nivcsws", prefix="sub")

            cols.extend(
                [
                    total_sys_hit,
                    total_disk_read,
                    minflts,
                    majflts,
                    # nswaps, msgsnds, msgrcvs, nsignals,
                    nvcsws,
                    nivcsws,
                ]
            )

            from_clause += """
            LEFT JOIN ({kcache_query}) AS kc USING (dbid, ts, srvid)""".format(
                kcache_query=kcache_query
            )

        return """SELECT {cols}
        FROM (
            {from_clause}
        ) AS sub
        CROSS JOIN {bs}
        WHERE sub.calls != 0
        GROUP BY sub.srvid, sub.ts, block_size, sub.mesure_interval
        ORDER BY sub.ts""".format(
            cols=", ".join(cols), from_clause=from_clause, bs=bs
        )


class GlobalWaitsMetricGroup(MetricGroupDef):
    """Metric group for global wait events graphs."""

    name = "all_databases_waits"
    xaxis = "ts"
    data_url = r"/server/(\d+)/metrics/databases_waits/"
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
        query = powa_getwaitdata_sample("db")

        cols = [to_epoch("ts", "sub")]

        pg_version_num = self.get_pg_version_num(self.path_args[0])
        # if we can't connect to the remote server, assume pg10 or above
        if pg_version_num is not None and pg_version_num < 100000:
            cols += [
                wps("count_lwlocknamed"),
                wps("count_lwlocktranche"),
                wps("count_lock"),
                wps("count_bufferpin"),
            ]
        else:
            cols += [
                wps("count_lwlock"),
                wps("count_lock"),
                wps("count_bufferpin"),
                wps("count_activity"),
                wps("count_client"),
                wps("count_extension"),
                wps("count_ipc"),
                wps("count_timeout"),
                wps("count_io"),
            ]

        from_clause = "({query}) AS sub".format(query=query)

        return """SELECT {cols}
        FROM {from_clause}
        -- WHERE sub.count IS NOT NULL
        GROUP BY sub.ts, sub.mesure_interval
        ORDER BY sub.ts""".format(
            cols=", ".join(cols), from_clause=from_clause
        )


class GlobalPGSAMetricGroup(MetricGroupDef):
    """
    Metric group used by pg_stat_activity graphs
    """

    name = "pgsa"
    xaxis = "ts"
    desc = "All backends, excluding autovacuum workers, are included"
    data_url = r"/server/(\d+)/metrics/pgsa/"
    backend_xid_age = MetricDef(label="Backend xid age")
    backend_xmin_age = MetricDef(label="Backend xmin age")
    oldest_backend = MetricDef(
        label="Oldest backend",
        type="duration",
        desc="Age of the oldest backend, excluding replication backends",
    )
    oldest_xact = MetricDef(label="Oldest transaction", type="duration")
    oldest_query = MetricDef(label="Oldest query", type="duration")
    nb_idle = MetricDef(label="# of idle connections")
    nb_active = MetricDef(label="# of active connections")
    nb_idle_xact = MetricDef(label="# of idle in transaction connections")
    nb_fastpath = MetricDef(label="# of connections in fastpath function call")
    nb_idle_xact_abort = MetricDef(
        label="# of idle in transaction (aborted) connections"
    )
    nb_disabled = MetricDef(label="# of disabled connections")
    nb_unknown = MetricDef(label="# of connections in unknown state")
    nb_parallel_query = MetricDef(label="# of parallel queries")
    nb_parallel_worker = MetricDef(label="# of parallel workers")

    @classmethod
    def _get_metrics(cls, handler, **params):
        base = cls.metrics.copy()

        remote_pg_ver = handler.get_pg_version_num(handler.path_args[0])
        if remote_pg_ver is not None and remote_pg_ver < 130000:
            for key in ("nb_parallel_query", "nb_parallel_worker"):
                base.pop(key)
        return base

    @property
    def query(self):
        query = powa_get_pgsa_sample()
        # Those greatests are to avoid having negative values returned, see https://github.com/powa-team/powa-archivist/issues/98
        cols = [
            "extract(epoch FROM ts) AS ts",
            "greatest(max(backend_xid_age),0) AS backend_xid_age",
            "greatest(max(backend_xmin_age),0) AS backend_xmin_age",
            "greatest(max(backend_start_age) FILTER (WHERE datid IS NOT NULL),0) AS oldest_backend",
            "greatest(max(xact_start_age) FILTER (WHERE datid IS NOT NULL),0) AS oldest_xact",
            "greatest(max(query_start_age) FILTER (WHERE datid IS NOT NULL AND state !~ 'idle'),0) AS oldest_query",
            "count(*) FILTER (WHERE state = 'idle') AS nb_idle",
            "count(*) FILTER (WHERE state = 'active') AS nb_active",
            "count(*) FILTER (WHERE state = 'idle in transaction') AS nb_idle_xact",
            "count(*) FILTER (WHERE state = 'fastpath function call') AS nb_fastpath",
            "count(*) FILTER (WHERE state = 'idle in transaction (aborted)') AS nb_idle_xact_abort",
            "count(*) FILTER (WHERE state = 'disabled') AS nb_disabled",
            "count(*) FILTER (WHERE state IS NULL) AS nb_unknown",
            "count(DISTINCT leader_pid) AS nb_parallel_query",
            "count(*) FILTER (WHERE leader_pid IS NOT NULL) AS nb_parallel_worker",
        ]

        return """SELECT {cols}
            FROM ({query}) AS sub
            GROUP BY ts
            """.format(cols=", ".join(cols), query=query)


class GlobalArchiverMetricGroup(MetricGroupDef):
    """
    Metric group used by pg_stat_archiver graphs.
    """

    name = "archiver"
    xaxis = "ts"
    data_url = r"/server/(\d+)/metrics/archiver/"
    nb_arch = MetricDef(
        label="# of archived WAL per second",
        type="number",
        desc="Number of WAL archived per second",
    )
    nb_to_arch = MetricDef(
        label="# of WAL to archive",
        type="number",
        desc="Number of WAL that needs to be archived",
    )

    @property
    def query(self):
        query = powa_get_archiver_sample()
        ts = get_ts()

        cols = [
            "extract(epoch FROM ts) AS ts",
            "round((nb_arch::numeric / " + ts + ")::numeric, 2) AS nb_arch",
            "nb_to_arch",
        ]

        return """SELECT {cols}
        FROM (
            {from_clause}
        ) AS sub""".format(cols=", ".join(cols), from_clause=query)


class GlobalBgwriterMetricGroup(MetricGroupDef):
    """
    Metric group used by bgwriter graphs.
    """

    name = "bgwriter"
    xaxis = "ts"
    data_url = r"/server/(\d+)/metrics/bgwriter/"
    buffers_clean = MetricDef(
        label="Buffers clean",
        type="sizerate",
        desc="Number of buffers written by the background writer",
    )
    maxwritten_clean = MetricDef(
        label="Maxwritten clean",
        type="number",
        desc="Number of times the background writer"
        " stopped a cleaning scan because it had"
        " written too many buffers",
    )
    buffers_backend = MetricDef(
        label="Buffers backend",
        type="sizerate",
        desc="Number of buffers written directly by a backend",
    )
    buffers_backend_fsync = MetricDef(
        label="Buffers backend fsync",
        type="number",
        desc="Number of times a backend had to"
        " execute its own fsync call"
        " (normally the background writer handles"
        " those even when the backend does its"
        " own write",
    )
    buffers_alloc = MetricDef(
        label="Buffers alloc",
        type="sizerate",
        desc="Number of buffers allocated",
    )

    @property
    def query(self):
        bs = block_size
        query = powa_get_bgwriter_sample()

        from_clause = query

        cols = [
            "sub.srvid",
            "extract(epoch FROM sub.ts) AS ts",
            byte_per_sec("buffers_clean", prefix="sub"),
            sum_per_sec("maxwritten_clean", prefix="sub"),
            byte_per_sec("buffers_backend", prefix="sub"),
            sum_per_sec("buffers_backend_fsync", prefix="sub"),
            byte_per_sec("buffers_alloc", prefix="sub"),
        ]

        return """SELECT {cols}
        FROM (
            {from_clause}
        ) AS sub
        CROSS JOIN {bs}
        WHERE sub.mesure_interval != '0 s'
        GROUP BY sub.srvid, sub.ts, block_size, sub.mesure_interval
        ORDER BY sub.ts""".format(
            cols=", ".join(cols), from_clause=from_clause, bs=bs
        )


class GlobalCheckpointerMetricGroup(MetricGroupDef):
    """
    Metric group used by bgwriter graphs.
    """

    name = "checkpointer"
    xaxis = "ts"
    data_url = r"/server/(\d+)/metrics/checkpointer/"
    num_timed = MetricDef(
        label="# of scheduled checkpoints",
        type="number",
        desc="Number of scheduled checkpoints that have been performed",
    )
    num_requested = MetricDef(
        label="# of requested checkpoints",
        type="number",
        desc="Number of requested checkpoints that have been performed",
    )
    write_time = MetricDef(
        label="Write time",
        type="duration",
        desc="Total amount of time that has been"
        " spent in the portion of checkpoint"
        " processing where files are written to"
        " disk, in milliseconds",
    )
    sync_time = MetricDef(
        label="Sync time",
        type="duration",
        desc="Total amount of time that has been"
        " spent in the portion of checkpoint"
        " processing where files are synchronized"
        " to disk, in milliseconds",
    )
    buffers_written = MetricDef(
        label="Buffers checkpoint",
        type="sizerate",
        desc="Number of buffers written during checkpoints",
    )

    @property
    def query(self):
        bs = block_size
        query = powa_get_checkpointer_sample()

        from_clause = query

        cols = [
            "sub.srvid",
            "extract(epoch FROM sub.ts) AS ts",
            "sum(sub.num_timed) AS num_timed",
            "sum(sub.num_requested) AS num_requested",
            sum_per_sec("write_time", prefix="sub"),
            sum_per_sec("sync_time", prefix="sub"),
            byte_per_sec("buffers_written", prefix="sub"),
        ]

        return """SELECT {cols}
        FROM (
            {from_clause}
        ) AS sub
        CROSS JOIN {bs}
        WHERE sub.mesure_interval != '0 s'
        GROUP BY sub.srvid, sub.ts, block_size, sub.mesure_interval
        ORDER BY sub.ts""".format(
            cols=", ".join(cols), from_clause=from_clause, bs=bs
        )


class GlobalIoMetricGroup(TemplateIoGraph):
    """
    Metric group used by pg_stat_io graphs.
    """

    name = "io"
    xaxis = "ts"
    data_url = r"/server/(\d+)/metrics/io/"


class ByAllIoMetricGroup(TemplateIoGrid):
    """
    Metric group used by the pg_stat_io grid, with full detail (by
    backend_type, object and context).
    """

    name = "io_by_all"
    xaxis = "backend_type"
    data_url = r"/server/(\d+)/metrics/io_by_all/"


class GlobalSlruMetricGroup(MetricGroupDef):
    """
    Metric group used by pg_stat_slru graph.
    """

    pass
    name = "slru"
    xaxis = "name"
    data_url = r"/server/(\d+)/metrics/slru/"
    blks_zeroed = MetricDef(
        label="Zeroed",
        type="sizerate",
        desc="Number of blocks zeroed during initializations",
    )
    blks_hit = MetricDef(
        label="Hit",
        type="sizerate",
        desc="Number of times disk blocks were found already"
        " in the SLRU, so that a read was not necessary"
        " (this only includes hits in the SLRU, not the"
        " operating system's file system cache)",
    )
    blks_read = MetricDef(
        label="Read",
        type="sizerate",
        desc="Number of disk blocks read for this SLRU",
    )
    blks_written = MetricDef(
        label="Written",
        type="sizerate",
        desc="Number of disk blocks written for this SLRU",
    )
    blks_exists = MetricDef(
        label="Exists",
        type="sizerate",
        desc="Number of blocks checked for existence for this SLRU",
    )
    flushes = MetricDef(
        label="Flushes",
        type="number",
        desc="Number of flushes of dirty data for this SLRU",
    )
    truncates = MetricDef(
        label="Truncates",
        type="number",
        desc="Number of truncates for this SLRU",
    )

    @classmethod
    def _get_metrics(cls, handler, **params):
        base = cls.metrics.copy()

        pg_version_num = handler.get_pg_version_num(handler.path_args[0])
        # if we can't connect to the remote server, assume pg13 or more
        if pg_version_num is not None and pg_version_num < 130000:
            return {}
        return base

    @property
    def query(self):
        query = powa_get_slru_sample()

        from_clause = query

        cols = [
            "sub.srvid",
            "extract(epoch FROM sub.ts) AS ts",
            sum_per_sec("blks_zeroed"),
            sum_per_sec("blks_hit"),
            sum_per_sec("blks_read"),
            sum_per_sec("blks_written"),
            sum_per_sec("blks_exists"),
            sum_per_sec("flushes"),
            sum_per_sec("truncates"),
        ]

        return """SELECT {cols}
        FROM (
            {from_clause}
        ) AS sub
        WHERE sub.mesure_interval != '0 s'
        GROUP BY sub.srvid, sub.ts, sub.mesure_interval
        ORDER BY sub.ts""".format(
            cols=", ".join(cols),
            from_clause=from_clause,
        )


class ByAllSlruMetricGroup(MetricGroupDef):
    """
    Metric group used by pg_stat_slru grid.
    """

    name = "slru_by_all"
    xaxis = "ts"
    data_url = r"/server/(\d+)/metrics/slru_by_all/"
    blks_zeroed = MetricDef(
        label="Zeroed",
        type="size",
        desc="Total number of blocks zeroed during initializations",
    )
    blks_hit = MetricDef(
        label="Hit",
        type="size",
        desc="Total number of times disk blocks were found"
        " already in the SLRU, so that a read was not"
        " necessary (this only includes hits in the SLRU,"
        " not the operating system's file system cache)",
    )
    blks_read = MetricDef(
        label="Read",
        type="size",
        desc="Total number of disk blocks read for this SLRU",
    )
    blks_written = MetricDef(
        label="Written",
        type="size",
        desc="Total number of disk blocks written for this SLRU",
    )
    blks_exists = MetricDef(
        label="Exists",
        type="size",
        desc="Total number of blocks checked for existence for this SLRU",
    )
    flushes = MetricDef(
        label="Flushes",
        type="number",
        desc="Total number of flushes of dirty data for this SLRU",
    )
    truncates = MetricDef(
        label="Truncates",
        type="number",
        desc="Total number of truncates for this SLRU",
    )

    @property
    def query(self):
        query = powa_getslrudata()

        return query

    def process(self, val, **kwargs):
        val["url"] = self.reverse_url(
            "ByNameSlruOverview", val["srvid"], val["name"]
        )

        return val


class GlobalSubMetricGroup(MetricGroupDef):
    """
    Metric group used by pg_stat_subscription(_stats) graphs.
    """

    pass
    name = "subscriptions"
    xaxis = "name"
    data_url = r"/server/(\d+)/metrics/subscriptions/"
    last_msg_lag = MetricDef(
        label="Last message latency",
        type="duration",
        desc="Time spent transmitting the last message"
        " received from origin WAL sender",
    )
    report_lag = MetricDef(
        label="Report lag",
        type="duration",
        desc="Time elapsed since since last reporting of"
        " WAL location to origin WAL sender",
    )
    apply_error_count = MetricDef(
        label="# apply error",
        type="number",
        desc="Total number of times an error occurred while applying changes",
    )
    sync_error_count = MetricDef(
        label="# sync error",
        type="number",
        desc="Total number of times an error"
        " occurred during the inital table"
        " synchronization",
    )

    @classmethod
    def _get_metrics(cls, handler, **params):
        base = cls.metrics.copy()

        pg_version_num = handler.get_pg_version_num(handler.path_args[0])
        # if we can't connect to the remote server, assume pg15 or more
        if pg_version_num is None:
            return base

        # pg_stat_subscription was added in pg10 and pg_stat_subscription_stats
        # was added in pg15.
        # leader_pid was added in pg16 and worker_type in pg17 but we don't use
        # those for now.
        if pg_version_num < 100000:
            return {}
        elif pg_version_num < 150000:
            base.pop("apply_error_count")
            base.pop("sync_error_count")

        return base

    @property
    def query(self):
        query = powa_get_subscription_sample()

        from_clause = query

        cols = [
            "sub.srvid",
            "extract(epoch FROM sub.ts) AS ts",
            "max(last_msg_lag) AS last_msg_lag",
            "max(report_lag) AS report_lag",
            "sum(apply_error_count) AS apply_error_count",
            "sum(sync_error_count) AS sync_error_count",
        ]

        return """SELECT {cols}
        FROM (
            {from_clause}
        ) AS sub
        WHERE sub.mesure_interval != '0 s'
        GROUP BY sub.srvid, sub.ts, sub.mesure_interval
        ORDER BY sub.ts""".format(
            cols=", ".join(cols),
            from_clause=from_clause,
        )


class GlobalWalMetricGroup(MetricGroupDef):
    """
    Metric group used by pg_stat_wal graph.
    """

    name = "wal"
    xaxis = "name"
    data_url = r"/server/(\d+)/metrics/wal/"
    wal_records = MetricDef(
        label="# records",
        type="number",
        desc="Total number of WAL records generated",
    )
    wal_fpi = MetricDef(
        label="# fpi",
        type="number",
        desc="Total number of WAL full page images generated",
    )
    wal_bytes = MetricDef(
        label="Generated",
        type="sizerate",
        desc="Total amount of WAL generated in bytes",
    )
    wal_buffers_full = MetricDef(
        label="# buffers full",
        type="number",
        desc="Number of times WAL data was written to"
        " disk because WAL buffers became full",
    )
    wal_write = MetricDef(
        label="# writes",
        type="number",
        desc="Number of times WAL buffers were written out"
        " to disk via XLogWrite request",
    )
    wal_sync = MetricDef(
        label="# sync",
        type="number",
        desc="Number of times WAL files were synced to disk"
        " via issue_xlog_fsync request",
    )
    wal_write_time = MetricDef(
        label="Write time",
        type="duration",
        desc="Total amount of time spent writing WAL buffers"
        " to disk via XLogWrite request",
    )
    wal_sync_time = MetricDef(
        label="Sync time",
        type="duration",
        desc="Total amount of time spent syncing WAL files to"
        " disk via issue_xlog_fsync request",
    )

    @classmethod
    def _get_metrics(cls, handler, **params):
        base = cls.metrics.copy()

        pg_version_num = handler.get_pg_version_num(handler.path_args[0])
        # if we can't connect to the remote server, assume pg14 or more
        if pg_version_num is not None and pg_version_num < 140000:
            return {}
        return base

    @property
    def query(self):
        query = powa_get_wal_sample()

        from_clause = query

        cols = [
            "sub.srvid",
            "extract(epoch FROM sub.ts) AS ts",
            sum_per_sec("wal_records"),
            sum_per_sec("wal_fpi"),
            sum_per_sec("wal_bytes"),
            sum_per_sec("wal_buffers_full"),
            sum_per_sec("wal_write"),
            sum_per_sec("wal_sync"),
            sum_per_sec("wal_write_time"),
            sum_per_sec("wal_sync_time"),
        ]

        return """SELECT {cols}
        FROM (
            {from_clause}
        ) AS sub
        WHERE sub.mesure_interval != '0 s'
        GROUP BY sub.srvid, sub.ts, sub.mesure_interval
        ORDER BY sub.ts""".format(
            cols=", ".join(cols),
            from_clause=from_clause,
        )


class GlobalWalReceiverMetricGroup(MetricGroupDef):
    """
    Metric group used by pg_stat_wal_receiver graphs.
    """

    name = "wal_receiver"
    xaxis = "ts"
    data_url = r"/server/(\d+)/metrics/wal_receiver/"
    write_delta = MetricDef(
        label="Write delta",
        type="size",
        desc="Total amount of data received from the"
        " primary but not written yet",
    )
    flush_delta = MetricDef(
        label="Flush delta",
        type="size",
        desc="Total amount of data received and written but not flushed yet",
    )
    last_msg_lag = MetricDef(
        label="Last message latency",
        type="duration",
        desc="Time spent transmitting the last message"
        " received from origin WAL sender",
    )
    report_delta = MetricDef(
        label="Report delta",
        type="size",
        desc="Total amount of data not yet reported to origin WAL sender",
    )
    report_lag = MetricDef(
        label="Report lag",
        type="duration",
        desc="Time elapsed since since last reporting of"
        " WAL location to origin WAL sender",
    )
    received_bytes = MetricDef(
        label="WAL receiver bandwidth",
        type="sizerate",
        desc="Amount of data received from original WAL sender",
    )

    @classmethod
    def _get_metrics(cls, handler, **params):
        base = cls.metrics.copy()

        pg_version_num = handler.get_pg_version_num(handler.path_args[0])
        # if we can't connect to the remote server, assume pg9.6 or more
        if pg_version_num is not None and pg_version_num < 90600:
            return {}
        return base

    @property
    def query(self):
        query = powa_get_wal_receiver_sample()

        from_clause = query

        cols = [
            "sub.srvid",
            "extract(epoch FROM sub.ts) AS ts",
            "last_received_lsn - written_lsn AS write_delta",
            "written_lsn - flushed_lsn AS flush_delta",
            "extract(epoch FROM ((last_msg_receipt_time - last_msg_send_time) * 1000)) AS last_msg_lag",
            "last_received_lsn - latest_end_lsn AS report_delta",
            "greatest(extract(epoch FROM ((ts - latest_end_time) * 1000)), 0) AS report_lag",
            "received_bytes",
        ]

        return """SELECT {cols}
        FROM (
            {from_clause}
        ) AS sub
        WHERE sub.mesure_interval != '0 s'
        --GROUP BY sub.srvid, sub.ts, sub.mesure_interval
        ORDER BY sub.ts""".format(
            cols=", ".join(cols),
            from_clause=from_clause,
        )


class GlobalReplicationMetricGroup(MetricGroupDef):
    """
    Metric group used by pg_stat_replication graphs.
    """

    name = "replication"
    xaxis = "ts"
    data_url = r"/server/(\d+)/metrics/replication/"
    sent_lsn = MetricDef(
        label="Sent delta",
        type="size",
        desc="Maximum amount of data not sent to the replica",
    )
    write_lsn = MetricDef(
        label="Write delta",
        type="size",
        desc="Maximum amount of data sent to the replica but"
        " not written locally",
    )
    flush_lsn = MetricDef(
        label="Flush delta",
        type="size",
        desc="Maximum amount of data written on the replica"
        " but not flushed locally",
    )
    replay_lsn = MetricDef(
        label="Replay delta",
        type="size",
        desc="Maximum amount of data flushed on the replica"
        " but not replayed locally",
    )
    write_lag = MetricDef(
        label="Write lag", type="duration", desc="Maximum write lag in s"
    )
    flush_lag = MetricDef(
        label="Flush lag", type="duration", desc="Maximum flush lag in s"
    )
    replay_lag = MetricDef(
        label="Replay lag", type="duration", desc="Maximum replay lag in s"
    )
    nb_async = MetricDef(
        label="# of async replication connections",
        type="number",
        desc="Number of asynchronous replication connections",
    )
    nb_sync = MetricDef(
        label="# of sync replication connections",
        type="number",
        desc="Number of synchronous replication connections",
    )
    nb_physical_act = MetricDef(
        label="# physical slots (active)",
        type="number",
        desc="Number of active physical replication slots",
    )
    nb_physical_not_act = MetricDef(
        label="# physical slots (disconnected)",
        type="number",
        desc="Number of disconnected physical replication slots",
    )
    nb_logical_act = MetricDef(
        label="# logical slots (active)",
        type="number",
        desc="Number of active logical replication slots",
    )
    nb_logical_not_act = MetricDef(
        label="# logical slots (disconnected)",
        type="number",
        desc="Number of inactive logical replication slots",
    )

    @property
    def query(self):
        query = powa_get_replication_sample()

        from_clause = query

        cols = [
            "extract(epoch FROM sub.ts) AS ts",
            # the datasource retrieves the current lsn first and then the
            # rest of the counters, so it's entirely possible to get a
            # slightly negative number here.  If that happens it just means
            # that there was some activity happening and everything is
            # working as expected.
            "greatest(rep_current_lsn - sent_lsn, 0) AS sent_lsn",
            "sent_lsn - write_lsn AS write_lsn",
            "write_lsn - flush_lsn AS flush_lsn",
            "flush_lsn - replay_lsn AS replay_lsn",
            "coalesce(extract(epoch from write_lag), 0) AS write_lag",
            "coalesce(extract(epoch from flush_lag - write_lag), 0) AS flush_lag",
            "coalesce(extract(epoch from replay_lag - flush_lag), 0) AS replay_lag",
            "nb_async",
            "nb_repl - nb_async AS nb_sync",
            "nb_physical_act",
            "nb_physical_not_act",
            "nb_logical_act",
            "nb_logical_not_act",
        ]

        return """SELECT {cols}
        FROM (
            {from_clause}
        ) AS sub
        WHERE sub.mesure_interval != '0 s'
        ORDER BY sub.ts""".format(
            cols=", ".join(cols),
            from_clause=from_clause,
        )


class GlobalDbActivityMetricGroup(MetricGroupDef):
    """
    Metric group used by "Database Activity" graphs.
    """

    name = "all_db_activity"
    xaxis = "ts"
    data_url = r"/server/(\d+)/metrics/all_db_activity/"
    numbackends = MetricDef(
        label="# of connections", desc="Total number of connections"
    )
    xact_commit = MetricDef(
        label="# of commits", desc="Total number of commits per second"
    )
    xact_rollback = MetricDef(
        label="# of rollbacks", desc="Total number of rollbacks per second"
    )
    conflicts = MetricDef(
        label="# of conflicts", desc="Total number of conflicts"
    )
    deadlocks = MetricDef(
        label="# of deadlocks", desc="Total number of deadlocks"
    )
    checksum_failures = MetricDef(
        label="# of checkum_failures", desc="Total number of checkum_failures"
    )
    session_time = MetricDef(
        label="Session time",
        type="duration",
        desc="Total time spent by database sessions per second",
    )
    active_time = MetricDef(
        label="Active time",
        type="duration",
        desc="Total time spent executing SQL statements per second",
    )
    idle_in_transaction_time = MetricDef(
        label="idle in xact time",
        type="duration",
        desc="Total time spent idling while in a transaction per second",
    )
    sessions = MetricDef(
        label="# sessions",
        desc="Total number of sessions established per second",
    )
    sessions_abandoned = MetricDef(
        label="# sessions abandoned",
        desc="Number of database sessions that "
        "were terminated because connection to "
        "the client was lost per second",
    )
    sessions_fatal = MetricDef(
        label="# sessions fatal",
        desc="Number of database sessions that "
        "were terminated by fatal errors",
    )
    sessions_killed = MetricDef(
        label="# sessions killed per second",
        desc="Number of database sessions that "
        "were terminated by operator intervention "
        "per second",
    )

    @classmethod
    def _get_metrics(cls, handler, **params):
        base = cls.metrics.copy()

        pg_version_num = handler.get_pg_version_num(handler.path_args[0])
        # if we can't connect to the remote server, assume pg14 or above
        if pg_version_num is not None and pg_version_num < 140000:
            for key in (
                "session_time",
                "active_time",
                "idle_in_transaction_time",
                "sessions",
                "sessions_abandoned",
                "sessions_fatal",
                "sessions_killed",
            ):
                base.pop(key)
        return base

    @property
    def query(self):
        query = powa_get_database_sample()

        cols = [
            "sub.srvid",
            "extract(epoch FROM sub.ts) AS ts",
            "numbackends",
            wps("xact_commit", do_sum=False),
            wps("xact_rollback", do_sum=False),
            "conflicts",
            "deadlocks",
            "checksum_failures",
            wps("session_time", do_sum=False),
            wps("active_time", do_sum=False),
            wps("idle_in_transaction_time", do_sum=False),
            wps("sessions", do_sum=False),
            wps("sessions_abandoned", do_sum=False),
            wps("sessions_fatal", do_sum=False),
            wps("sessions_killed", do_sum=False),
        ]

        return """SELECT {cols}
        FROM ({query}) sub
        WHERE sub.mesure_interval != '0 s'
        ORDER BY sub.ts""".format(
            cols=", ".join(cols),
            query=query,
        )


class GlobalDbActivityConflMetricGroup(MetricGroupDef):
    """
    Metric group used by the "Recovery conflicts" graph.
    """

    name = "all_db_activity_conf"
    xaxis = "ts"
    data_url = r"/server/(\d+)/metrics/all_db_activity_conf/"
    confl_tablespace = MetricDef(
        label="Tablespaces",
        desc="Total number of queries that have been"
        " been canceled due to drop tablespaces",
    )
    confl_lock = MetricDef(
        label="Locks",
        desc="Total number of queries that have been "
        "canceled due to lock timeouts",
    )
    confl_snapshot = MetricDef(
        label="Snapshots",
        desc="Total number of queries that have been"
        " canceled due to old snapshots",
    )
    confl_bufferpin = MetricDef(
        label="Pinned buffers",
        desc="Total number of queries that have been"
        " canceled due to pinned buffers",
    )
    confl_deadlock = MetricDef(
        label="Deadlocks",
        desc="Total number of queries that have been"
        " canceled due to deadlocks",
    )
    confl_active_logicalslot = MetricDef(
        label="Logical slots",
        desc="Total number of uses of logical slots that"
        " have canceled due to old snapshots or too"
        " low wal_level on the primary",
    )

    @classmethod
    def _get_metrics(cls, handler, **params):
        base = cls.metrics.copy()

        pg_version_num = handler.get_pg_version_num(handler.path_args[0])
        # if we can't connect to the remote server, assume pg15 or below
        if pg_version_num is None or pg_version_num < 160000:
            base.pop("confl_active_logicalslot")
        return base

    @property
    def query(self):
        query = powa_get_database_conflicts_sample()

        cols = [
            "sub.srvid",
            "extract(epoch FROM sub.ts) AS ts",
            "confl_tablespace",
            "confl_lock",
            "confl_snapshot",
            "confl_bufferpin",
            "confl_deadlock",
            "confl_active_logicalslot",
        ]

        return """SELECT {cols}
        FROM ({query}) sub
        WHERE sub.mesure_interval != '0 s'
        ORDER BY sub.ts""".format(
            cols=", ".join(cols),
            query=query,
        )


class GlobalAllRelMetricGroup(MetricGroupDef):
    """
    Metric group used by "Database objects" graphs.
    """

    name = "all_relations"
    xaxis = "ts"
    data_url = r"/server/(\d+)/metrics/all_relations/"
    idx_size = MetricDef(
        label="Indexes size", type="size", desc="Size of all indexes"
    )
    tbl_size = MetricDef(
        label="Tables size", type="size", desc="Size of all tables"
    )
    idx_ratio = MetricDef(
        label="Index scans ratio",
        type="percent",
        desc="Ratio of index scan / seq scan",
    )
    idx_scan = MetricDef(
        label="Index scans",
        type="number",
        desc="Number of index scan per second",
    )
    seq_scan = MetricDef(
        label="Sequential scans",
        type="number",
        desc="Number of sequential scan per second",
    )
    n_tup_ins = MetricDef(
        label="Tuples inserted",
        type="number",
        desc="Number of tuples inserted per second",
    )
    n_tup_upd = MetricDef(
        label="Tuples updated",
        type="number",
        desc="Number of tuples updated per second",
    )
    n_tup_hot_upd = MetricDef(
        label="Tuples HOT updated",
        type="number",
        desc="Number of tuples HOT updated per second",
    )
    n_tup_del = MetricDef(
        label="Tuples deleted",
        type="number",
        desc="Number of tuples deleted per second",
    )
    vacuum_count = MetricDef(
        label="# Vacuum", type="number", desc="Number of vacuum per second"
    )
    autovacuum_count = MetricDef(
        label="# Autovacuum",
        type="number",
        desc="Number of autovacuum per second",
    )
    analyze_count = MetricDef(
        label="# Analyze", type="number", desc="Number of analyze per second"
    )
    autoanalyze_count = MetricDef(
        label="# Autoanalyze",
        type="number",
        desc="Number of autoanalyze per second",
    )

    @property
    def query(self):
        query1 = powa_get_all_tbl_sample("db")
        query2 = powa_get_all_idx_sample("db")

        cols = [
            "sub.srvid",
            "extract(epoch FROM sub.ts) AS ts",
            "sum(tbl_size) AS tbl_size",
            "sum(idx_size) AS idx_size",
            "CASE WHEN sum(sub.idx_scan + sub.seq_scan) = 0"
            " THEN 0"
            " ELSE sum(sub.idx_scan) * 100"
            " / sum(sub.idx_scan + sub.seq_scan)"
            " END AS idx_ratio",
            sum_per_sec("idx_scan", prefix="sub"),
            sum_per_sec("seq_scan", prefix="sub"),
            sum_per_sec("n_tup_ins", prefix="sub"),
            sum_per_sec("n_tup_upd", prefix="sub"),
            sum_per_sec("n_tup_hot_upd", prefix="sub"),
            sum_per_sec("n_tup_del", prefix="sub"),
            sum_per_sec("vacuum_count", prefix="sub"),
            sum_per_sec("autovacuum_count", prefix="sub"),
            sum_per_sec("analyze_count", prefix="sub"),
            sum_per_sec("autoanalyze_count", prefix="sub"),
        ]

        return """SELECT {cols}
        FROM (
            ({query1}) q1
            JOIN (SELECT srvid, dbid, ts, idx_size FROM ({query2})s ) q2
                USING (srvid, dbid, ts)
        ) AS sub
        WHERE sub.mesure_interval != '0 s'
        GROUP BY sub.srvid, sub.ts, sub.mesure_interval
        ORDER BY sub.ts""".format(
            cols=", ".join(cols), query1=query1, query2=query2
        )


class GlobalUserFctMetricGroup(MetricGroupDef):
    """
    Metric group used by "pg_stat_user_function" graph.
    """

    name = "user_functions"
    xaxis = "ts"
    data_url = r"/server/(\d+)/metrics/user_functions/"
    calls = MetricDef(
        label="# of calls",
        type="number",
        desc="Number of function calls per second",
    )
    total_load = MetricDef(
        label="Total time per sec",
        type="number",
        desc="Total execution time duration",
    )
    self_load = MetricDef(
        label="Self time per sec",
        type="number",
        desc="Self execution time duration",
    )

    @property
    def query(self):
        query = powa_get_user_fct_sample("db")

        from_clause = query

        cols = [
            "sub.srvid",
            "extract(epoch FROM sub.ts) AS ts",
            sum_per_sec("calls"),
            sum_per_sec("total_time", alias="total_load"),
            sum_per_sec("self_time", alias="self_load"),
        ]

        return """SELECT {cols}
        FROM (
            {from_clause}
        ) AS sub
        WHERE sub.mesure_interval != '0 s'
        GROUP BY sub.srvid, sub.ts, sub.mesure_interval
        ORDER BY sub.ts""".format(
            cols=", ".join(cols), from_clause=from_clause
        )


class ServerOverview(DashboardPage):
    """
    ServerOverview dashboard page.
    """

    base_url = r"/server/(\d+)/overview/"
    datasources = [
        GlobalDatabasesMetricGroup,
        ByDatabaseMetricGroup,
        ByDatabaseWaitSamplingMetricGroup,
        GlobalWaitsMetricGroup,
        GlobalBgwriterMetricGroup,
        GlobalCheckpointerMetricGroup,
        GlobalAllRelMetricGroup,
        GlobalUserFctMetricGroup,
        ByDatabaseUserFuncMetricGroup,
        ConfigChangesGlobal,
        GlobalPGSAMetricGroup,
        GlobalArchiverMetricGroup,
        GlobalReplicationMetricGroup,
        GlobalDbActivityMetricGroup,
        GlobalDbActivityConflMetricGroup,
        GlobalIoMetricGroup,
        ByAllIoMetricGroup,
        GlobalSlruMetricGroup,
        ByAllSlruMetricGroup,
        GlobalWalMetricGroup,
        GlobalWalReceiverMetricGroup,
        GlobalSubMetricGroup,
    ]
    params = ["server"]
    parent = Overview
    title = "All databases"
    timeline = ConfigChangesGlobal

    def dashboard(self):
        # This COULD be initialized in the constructor, but tornado < 3 doesn't
        # call it
        if getattr(self, "_dashboard", None) is not None:
            return self._dashboard

        pg_version_num = self.get_pg_version_num(self.path_args[0])
        pgss18 = self.has_extension_version(
            self.path_args[0], "pg_stat_statements", "1.8"
        )
        pgss110 = self.has_extension_version(
            self.path_args[0], "pg_stat_statements", "1.10"
        )
        pgss111 = self.has_extension_version(
            self.path_args[0], "pg_stat_statements", "1.11"
        )

        all_db_metrics = [
            GlobalDatabasesMetricGroup.avg_runtime,
            GlobalDatabasesMetricGroup.load,
            GlobalDatabasesMetricGroup.calls,
        ]
        if pgss18:
            all_db_metrics.extend([GlobalDatabasesMetricGroup.planload])

        block_graph = Graph(
            "Block access in Bps",
            metrics=[GlobalDatabasesMetricGroup.total_blks_hit],
            color_scheme=None,
        )

        all_db_graphs = [
            [
                Graph(
                    "Query runtime per second (all databases)",
                    metrics=all_db_metrics,
                ),
                block_graph,
            ]
        ]

        if "nb_parallel_query" in GlobalPGSAMetricGroup._get_metrics(self):
            parallel_metrics = ["nb_parallel_query", "nb_parallel_worker"]
        else:
            parallel_metrics = []

        pgsa_metrics = GlobalPGSAMetricGroup.split(
            self,
            [
                [
                    "backend_xid_age",
                    "backend_xmin_age",
                    "oldest_backend",
                    "oldest_xact",
                    "oldest_query",
                ],
                parallel_metrics,
            ],
        )
        all_db_graphs.append(
            [
                Graph(
                    "Global activity (all databases)",
                    metrics=pgsa_metrics[0],
                    desc=GlobalPGSAMetricGroup.desc,
                    renderer="bar",
                    stack=True,
                )
            ]
        )
        if len(pgsa_metrics[2]) > 0:
            all_db_graphs[1].append(
                Graph(
                    "Parallel query (all databases)", metrics=pgsa_metrics[2]
                )
            )
        all_db_graphs[1].append(
            Graph(
                "Backend age (all databases)",
                metrics=pgsa_metrics[1],
                desc=GlobalPGSAMetricGroup.desc,
            )
        )

        graphs_dash = [Dashboard("General Overview", all_db_graphs)]
        graphs = [TabContainer("All databases", graphs_dash)]

        # Add WALs graphs

        # if we can't connect to the remote server, assume pg14 or above
        if pg_version_num is None or pg_version_num >= 140000:
            wal_metrics = GlobalWalMetricGroup.split(
                self, [["wal_write_time", "wal_sync_time"]]
            )
            wals_graphs = [
                [
                    Graph(
                        "WAL activity",
                        url="https://www.postgresql.org/docs/current/monitoring-stats.html#MONITORING-PG-STAT-WAL-VIEW",
                        metrics=wal_metrics[0],
                    ),
                    Graph(
                        "WAL timing",
                        url="https://www.postgresql.org/docs/current/monitoring-stats.html#MONITORING-PG-STAT-WAL-VIEW",
                        metrics=wal_metrics[1],
                    ),
                ]
            ]
            graphs_dash.append(Dashboard("WALs", wals_graphs))
        elif pgss18:
            wals_graphs = [
                [
                    Graph(
                        "WAL activity",
                        metrics=[
                            GlobalDatabasesMetricGroup.wal_records,
                            GlobalDatabasesMetricGroup.wal_fpi,
                            GlobalDatabasesMetricGroup.wal_bytes,
                        ],
                    ),
                ]
            ]
            graphs_dash.append(Dashboard("WALs", wals_graphs))

        # Add JIT graphs
        if pgss110:
            jit_tim = [
                GlobalDatabasesMetricGroup.jit_inlining_time,
                GlobalDatabasesMetricGroup.jit_optimization_time,
                GlobalDatabasesMetricGroup.jit_emission_time,
            ]

            if pgss111:
                jit_tim.extend(
                    [
                        GlobalDatabasesMetricGroup.jit_deform_time,
                        GlobalDatabasesMetricGroup.jit_expr_time,
                    ]
                )
            else:
                jit_tim.append(GlobalDatabasesMetricGroup.jit_generation_time)

            jit_cnt = [
                GlobalDatabasesMetricGroup.jit_functions,
                GlobalDatabasesMetricGroup.jit_inlining_count,
                GlobalDatabasesMetricGroup.jit_optimization_count,
                GlobalDatabasesMetricGroup.jit_emission_count,
            ]

            if pgss111:
                jit_cnt.append(GlobalDatabasesMetricGroup.jit_deform_count)

            jit_graphs = [
                [Graph("JIT timing", metrics=jit_tim, stack=True)],
                [Graph("JIT scheduling", metrics=jit_cnt)],
            ]

            graphs_dash.append(Dashboard("JIT", jit_graphs))

        # Add pg_stat_bgwriter / pg_stat_checkpointer graphs
        bgw_graphs = [
            [
                Graph(
                    "Checkpointer scheduling",
                    metrics=[
                        GlobalCheckpointerMetricGroup.num_timed,
                        GlobalCheckpointerMetricGroup.num_requested,
                    ],
                ),
                Graph(
                    "Checkpointer activity",
                    metrics=[
                        GlobalCheckpointerMetricGroup.write_time,
                        GlobalCheckpointerMetricGroup.sync_time,
                        GlobalCheckpointerMetricGroup.buffers_written,
                    ],
                ),
            ],
            [
                Graph(
                    "Background writer",
                    metrics=[
                        GlobalBgwriterMetricGroup.buffers_clean,
                        GlobalBgwriterMetricGroup.maxwritten_clean,
                        GlobalBgwriterMetricGroup.buffers_alloc,
                    ],
                ),
                Graph(
                    "Backends",
                    metrics=[
                        GlobalBgwriterMetricGroup.buffers_backend,
                        GlobalBgwriterMetricGroup.buffers_backend_fsync,
                    ],
                ),
            ],
        ]
        graphs_dash.append(
            Dashboard("Background Writer / Checkpointer", bgw_graphs)
        )

        # Add archiver / replication graphs
        sub_metrics = GlobalSubMetricGroup.split(
            self, [["last_msg_lag", "report_lag"]]
        )
        sub_graphs = []

        sub_graphs.append(
            Graph(
                "Subscriptions message & report",
                url="https://www.postgresql.org/docs/current/monitoring-stats.html#MONITORING-PG-STAT-SUBSCRIPTION",
                metrics=sub_metrics[1],
            )
        )

        if len(sub_metrics[0]) > 0:
            sub_graphs.append(
                Graph(
                    "Subscriptions errors",
                    url="https://www.postgresql.org/docs/current/monitoring-stats.html#MONITORING-PG-STAT-SUBSCRIPTION-STATS",
                    metrics=sub_metrics[0],
                )
            )

        arch_graphs = [
            [
                Graph("Archiver", metrics=GlobalArchiverMetricGroup.all(self)),
                Graph(
                    "Replication connections",
                    metrics=[
                        GlobalReplicationMetricGroup.nb_async,
                        GlobalReplicationMetricGroup.nb_sync,
                    ],
                    renderer="bar",
                    stack=True,
                ),
                Graph(
                    "Replication slots",
                    metrics=[
                        GlobalReplicationMetricGroup.nb_physical_act,
                        GlobalReplicationMetricGroup.nb_physical_not_act,
                        GlobalReplicationMetricGroup.nb_logical_act,
                        GlobalReplicationMetricGroup.nb_logical_not_act,
                    ],
                    renderer="bar",
                    stack=True,
                ),
            ],
            [
                Graph(
                    "Replication delta in B",
                    metrics=[
                        GlobalReplicationMetricGroup.sent_lsn,
                        GlobalReplicationMetricGroup.write_lsn,
                        GlobalReplicationMetricGroup.flush_lsn,
                        GlobalReplicationMetricGroup.replay_lsn,
                    ],
                    renderer="bar",
                    stack=True,
                ),
                Graph(
                    "Replication lag in s",
                    metrics=[
                        GlobalReplicationMetricGroup.write_lag,
                        GlobalReplicationMetricGroup.flush_lag,
                        GlobalReplicationMetricGroup.replay_lag,
                    ],
                    renderer="bar",
                    stack=True,
                ),
                Graph(
                    "Recovery conflicts",
                    stack=True,
                    metrics=GlobalDbActivityConflMetricGroup.all(self),
                    # metrics=[GlobalDbActivityConflMetricGroup.confl_tablespace]
                ),
            ],
            [
                Graph(
                    "WAL receiver bandwidth",
                    metrics=[GlobalWalReceiverMetricGroup.received_bytes],
                ),
                Graph(
                    "WAL receiver Delta",
                    url="https://www.postgresql.org/docs/current/monitoring-stats.html#MONITORING-PG-STAT-WAL-RECEIVER-VIEW",
                    metrics=[
                        GlobalWalReceiverMetricGroup.write_delta,
                        GlobalWalReceiverMetricGroup.flush_delta,
                    ],
                    renderer="bar",
                    stack=True,
                ),
            ],
            [
                Graph(
                    "WAL receiver message",
                    url="https://www.postgresql.org/docs/current/monitoring-stats.html#MONITORING-PG-STAT-WAL-RECEIVER-VIEW",
                    metrics=[GlobalWalReceiverMetricGroup.last_msg_lag],
                    renderer="bar",
                    stack=True,
                ),
                Graph(
                    "WAL receiver report",
                    url="https://www.postgresql.org/docs/current/monitoring-stats.html#MONITORING-PG-STAT-WAL-RECEIVER-VIEW",
                    metrics=[
                        GlobalWalReceiverMetricGroup.report_delta,
                        GlobalWalReceiverMetricGroup.report_lag,
                    ],
                    renderer="bar",
                    stack=True,
                ),
            ],
            sub_graphs,
        ]
        graphs_dash.append(Dashboard("Archiver / Replication", arch_graphs))

        # Add pg_stat_database graphs
        global_db_graphs = [
            [
                Graph(
                    "Transactions per second",
                    metrics=[
                        GlobalDbActivityMetricGroup.xact_commit,
                        GlobalDbActivityMetricGroup.xact_rollback,
                    ],
                    renderer="bar",
                    stack=True,
                ),
                Graph(
                    "Conflicts & deadlocks",
                    metrics=[
                        GlobalDbActivityMetricGroup.conflicts,
                        GlobalDbActivityMetricGroup.deadlocks,
                    ],
                ),
            ]
        ]
        if "sessions" in GlobalDbActivityMetricGroup._get_metrics(self):
            global_db_graphs.append(
                [
                    Graph(
                        "Cumulated time per second",
                        metrics=[
                            GlobalDbActivityMetricGroup.session_time,
                            GlobalDbActivityMetricGroup.active_time,
                            GlobalDbActivityMetricGroup.idle_in_transaction_time,
                        ],
                    ),
                    Graph(
                        "Sessions per second",
                        metrics=[
                            GlobalDbActivityMetricGroup.sessions,
                            GlobalDbActivityMetricGroup.sessions_abandoned,
                            GlobalDbActivityMetricGroup.sessions_fatal,
                            GlobalDbActivityMetricGroup.sessions_killed,
                        ],
                    ),
                ]
            )
        graphs_dash.append(Dashboard("Database activity", global_db_graphs))

        # Add powa_stat_all_relations graphs
        all_rel_graphs = [
            [
                Graph(
                    "Access pattern",
                    metrics=[
                        GlobalAllRelMetricGroup.seq_scan,
                        GlobalAllRelMetricGroup.idx_scan,
                        GlobalAllRelMetricGroup.idx_ratio,
                    ],
                ),
                Graph(
                    "DML activity",
                    metrics=[
                        GlobalAllRelMetricGroup.n_tup_del,
                        GlobalAllRelMetricGroup.n_tup_hot_upd,
                        GlobalAllRelMetricGroup.n_tup_upd,
                        GlobalAllRelMetricGroup.n_tup_ins,
                    ],
                ),
            ],
            [
                Graph(
                    "Vacuum activity",
                    metrics=[
                        GlobalAllRelMetricGroup.autoanalyze_count,
                        GlobalAllRelMetricGroup.analyze_count,
                        GlobalAllRelMetricGroup.autovacuum_count,
                        GlobalAllRelMetricGroup.vacuum_count,
                    ],
                ),
                Graph(
                    "Object size",
                    metrics=[
                        GlobalAllRelMetricGroup.tbl_size,
                        GlobalAllRelMetricGroup.idx_size,
                    ],
                    renderer="bar",
                    stack=True,
                    color_scheme=["#73c03a", "#65b9ac"],
                ),
            ],
        ]
        graphs_dash.append(Dashboard("Database Objects", all_rel_graphs))

        # Add powa_stat_user_functions graphs
        user_fct_graph = [
            Graph(
                "User functions activity",
                metrics=GlobalUserFctMetricGroup.all(self),
            )
        ]
        user_fct_grid = [
            Grid(
                "User functions activity for all databases",
                columns=[
                    {"name": "datname", "label": "Database", "url_attr": "url"}
                ],
                metrics=ByDatabaseUserFuncMetricGroup.all(self),
            )
        ]
        graphs_dash.append(
            Dashboard("User functions", [user_fct_graph, user_fct_grid])
        )

        sys_graphs = []
        if self.has_extension(self.path_args[0], "pg_stat_kcache"):
            block_graph.metrics.insert(
                0, GlobalDatabasesMetricGroup.total_sys_hit
            )
            block_graph.metrics.insert(
                0, GlobalDatabasesMetricGroup.total_disk_read
            )
            block_graph.color_scheme = ["#cb513a", "#65b9ac", "#73c03a"]

            sys_graphs.append(
                [
                    Graph(
                        "System resources (events per sec)",
                        url=self.docs_stats_url + "pg_stat_kcache.html",
                        metrics=[
                            GlobalDatabasesMetricGroup.majflts,
                            GlobalDatabasesMetricGroup.minflts,
                            # GlobalDatabasesMetricGroup.nswaps,
                            # GlobalDatabasesMetricGroup.msgsnds,
                            # GlobalDatabasesMetricGroup.msgrcvs,
                            # GlobalDatabasesMetricGroup.nsignals,
                            GlobalDatabasesMetricGroup.nvcsws,
                            GlobalDatabasesMetricGroup.nivcsws,
                        ],
                    )
                ]
            )

        else:
            block_graph.metrics.insert(
                0, GlobalDatabasesMetricGroup.total_blks_read
            )
            block_graph.color_scheme = ["#cb513a", "#73c03a"]

        # Add pg_stat_io graphs
        if "reads" in GlobalIoMetricGroup._get_metrics(self):
            io_metrics = GlobalIoMetricGroup.split(
                self,
                [
                    ["reads", "writes", "writebacks", "extends", "fsyncs"],
                    ["hits", "evictions", "reuses"],
                ],
            )
            sys_graphs.append(
                [
                    Graph(
                        "IO blocks",
                        metrics=io_metrics[1],
                    ),
                    Graph(
                        "IO timing",
                        metrics=io_metrics[0],
                    ),
                    Graph(
                        "IO misc",
                        metrics=io_metrics[2],
                    ),
                ]
            )

            sys_graphs.append(
                [
                    Grid(
                        "IO summary",
                        columns=[
                            {
                                "name": "backend_type",
                                "label": "Backend Type",
                                "url_attr": "backend_type_url",
                            },
                            {
                                "name": "object",
                                "label": "Object Type",
                                "url_attr": "obj_url",
                            },
                            {
                                "name": "context",
                                "label": "Context",
                                "url_attr": "context_url",
                            },
                        ],
                        metrics=ByAllIoMetricGroup.all(),
                    )
                ]
            )

        if len(sys_graphs) != 0:
            graphs_dash.append(Dashboard("System resources", sys_graphs))

        # if we can't connect to the remote server, assume pg13 or above
        if pg_version_num is None or pg_version_num >= 130000:
            graphs_dash.append(
                Dashboard(
                    "SLRU",
                    [
                        [
                            Graph(
                                "All SLRUs (per second)",
                                metrics=GlobalSlruMetricGroup.all(self),
                            )
                        ],
                        [
                            Grid(
                                "All SLRUs",
                                columns=[
                                    {
                                        "name": "name",
                                        "label": "SLRU name",
                                        "url_attr": "url",
                                    }
                                ],
                                metrics=ByAllSlruMetricGroup.all(self),
                            )
                        ],
                    ],
                )
            )

        if self.has_extension(self.path_args[0], "pg_wait_sampling"):
            metrics = None
            # if we can't connect to the remote server, assume pg10 or above
            if pg_version_num is not None and pg_version_num < 100000:
                metrics = [
                    GlobalWaitsMetricGroup.count_lwlocknamed,
                    GlobalWaitsMetricGroup.count_lwlocktranche,
                    GlobalWaitsMetricGroup.count_lock,
                    GlobalWaitsMetricGroup.count_bufferpin,
                ]
            else:
                metrics = [
                    GlobalWaitsMetricGroup.count_lwlock,
                    GlobalWaitsMetricGroup.count_lock,
                    GlobalWaitsMetricGroup.count_bufferpin,
                    GlobalWaitsMetricGroup.count_activity,
                    GlobalWaitsMetricGroup.count_client,
                    GlobalWaitsMetricGroup.count_extension,
                    GlobalWaitsMetricGroup.count_ipc,
                    GlobalWaitsMetricGroup.count_timeout,
                    GlobalWaitsMetricGroup.count_io,
                ]

            graphs_dash.append(
                Dashboard(
                    "Wait Events",
                    [
                        [
                            Graph(
                                "Wait Events (per second)",
                                url=self.docs_stats_url
                                + "pg_wait_sampling.html",
                                metrics=metrics,
                            )
                        ]
                    ],
                )
            )

        toprow = [
            {
                # database
            }
        ]

        if pgss18:
            toprow.extend(
                [
                    {
                        # plan time
                    }
                ]
            )

        toprow.extend(
            [
                {"name": "Execution", "colspan": 3},
                {
                    "name": "Blocks",
                    "colspan": 4,
                },
                {"name": "Temp blocks", "colspan": 2},
                {
                    "name": "I/O",
                },
            ]
        )

        if pgss18:
            toprow.extend([{"name": "WAL", "colspan": 3}])

        if pgss110:
            toprow.extend([{"name": "JIT", "colspan": 2}])

        dashes = [
            graphs,
            [
                Grid(
                    "Details for all databases",
                    toprow=toprow,
                    columns=[
                        {
                            "name": "datname",
                            "label": "Database",
                            "url_attr": "url",
                        }
                    ],
                    metrics=ByDatabaseMetricGroup.all(self),
                )
            ],
        ]

        if self.has_extension(self.path_args[0], "pg_wait_sampling"):
            dashes.append(
                [
                    Grid(
                        "Wait events for all databases",
                        url=self.docs_stats_url + "pg_wait_sampling.html",
                        columns=[
                            {
                                "name": "datname",
                                "label": "Database",
                                "url_attr": "url",
                            },
                            {
                                "name": "event_type",
                                "label": "Event Type",
                            },
                            {
                                "name": "event",
                                "label": "Event",
                            },
                        ],
                        metrics=ByDatabaseWaitSamplingMetricGroup.all(),
                    )
                ]
            )

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
