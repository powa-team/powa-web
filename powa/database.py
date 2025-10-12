"""
Module containing the by-database dashboard.
"""

from powa.config import ConfigChangesDatabase
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
from powa.framework import AuthHandler
from powa.server import ServerOverview
from powa.sql.utils import (
    block_size,
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
    powa_get_database_sample,
    powa_get_pgsa_sample,
    powa_get_user_fct_sample,
    powa_getstatdata_sample,
    powa_getwaitdata_sample,
)
from powa.sql.views_grid import (
    powa_getstatdata_detailed_db,
    powa_getuserfuncdata_detailed_db,
    powa_getwaitdata_detailed_db,
)
from powa.wizard import Wizard, WizardMetricGroup
from tornado.web import HTTPError


class DatabaseSelector(AuthHandler):
    """Page allowing to choose a database."""

    def get(self):
        self.redirect(
            self.reverse_url(
                "DatabaseOverview",
                self.get_argument("server"),
                self.get_argument("database"),
            )
        )


class DatabaseOverviewMetricGroup(MetricGroupDef):
    """Metric group for the database global graphs."""

    name = "database_overview"
    xaxis = "ts"
    data_url = r"/server/(\d+)/metrics/database_overview/([^\/]+)/"
    avg_runtime = MetricDef(
        label="Avg runtime", type="duration", desc="Average query duration"
    )
    calls = MetricDef(
        label="Queries per sec",
        type="number",
        desc="Number of time the query has been executed, per second",
    )
    planload = MetricDef(
        label="Plantime per sec",
        type="duration",
        desc="Total planning duration",
    )
    load = MetricDef(
        label="Runtime per sec",
        type="duration",
        desc="Total duration of queries executed, per second",
    )
    total_blks_hit = MetricDef(
        label="Total shared buffers hit",
        type="sizerate",
        desc="Amount of data found in shared buffers",
    )
    total_blks_read = MetricDef(
        label="Total shared buffers miss",
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
        # Fetch the base query for sample, and filter them on the database
        query = powa_getstatdata_sample("db", ["datname = %(database)s"])

        cols = [
            "srvid",
            to_epoch("ts"),
            sum_per_sec("calls", prefix="sub"),
            "sum(runtime) / greatest(sum(calls), 1) AS avg_runtime",
            sum_per_sec("runtime", prefix="sub", alias="load"),
            total_read("sub"),
            total_hit("sub"),
        ]

        if self.has_extension_version(
            self.path_args[0], "pg_stat_statements", "1.8"
        ):
            cols.extend(
                [
                    sum_per_sec("plantime", prefix="sub", alias="planload"),
                    sum_per_sec("wal_records", prefix="sub"),
                    sum_per_sec("wal_fpi", prefix="sub"),
                    sum_per_sec("wal_bytes", prefix="sub"),
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
            kcache_query = kcache_getstatdata_sample(
                "db", ["datname = %(database)s"]
            )

            total_sys_hit = (
                "greatest({total_read} - sum(sub.reads)"
                "/ greatest(extract(epoch FROM sub.mesure_interval), 1),0)"
                " AS total_sys_hit"
                "".format(total_read=total_read("sub", True))
            )
            total_disk_read = (
                "sum(sub.reads)"
                " / greatest(extract(epoch FROM sub.mesure_interval), 1)"
                " AS total_disk_read"
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
            cols=", ".join(cols), from_clause=from_clause, bs=block_size
        )


class DatabasePGSAOverview(MetricGroupDef):
    """
    Metric group used by pg_stat_activity graphs
    """

    name = "pgsa"
    xaxis = "ts"
    desc = "All backends, except autovacuum workers, are included"
    data_url = r"/server/(\d+)/metrics/pgsa_overview/([^\/]+)/"
    backend_xid_age = MetricDef(label="Backend xid age")
    backend_xmin_age = MetricDef(label="Backend xmin age")
    oldest_backend = MetricDef(label="Oldest backend", type="duration")
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
        query = powa_get_pgsa_sample(per_db=True)
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


class DatabaseWaitOverviewMetricGroup(MetricGroupDef):
    """Metric group for the database global wait events graphs."""

    name = "database_waits_overview"
    xaxis = "ts"
    data_url = r"/server/(\d+)/metrics/database_waits_overview/([^\/]+)/"
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
        query = powa_getwaitdata_sample("db", ["datname = %(database)s"])

        cols = [to_epoch("ts")]

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


class DatabaseAllRelMetricGroup(MetricGroupDef):
    """
    Metric group used by "Database objects" graphs.
    """

    name = "all_relations"
    xaxis = "ts"
    data_url = r"/server/(\d+)/metrics/database_all_relations/([^\/]+)/"
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
        AND datname = %(database)s
        GROUP BY sub.srvid, sub.ts, sub.mesure_interval
        ORDER BY sub.ts""".format(
            cols=", ".join(cols), query1=query1, query2=query2
        )


class DatabaseUserFuncMetricGroup(MetricGroupDef):
    """
    Metric group used by "pg_stat_user_functions" graph.
    """

    name = "user_functions"
    xaxis = "ts"
    data_url = r"/server/(\d+)/metrics/database_user_functions/([^\/]+)/"
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
        AND datname = %(database)s
        GROUP BY sub.srvid, sub.ts, sub.mesure_interval
        ORDER BY sub.ts""".format(
            cols=", ".join(cols), from_clause=from_clause
        )


class DatabaseDbActivityMetricGroup(MetricGroupDef):
    """
    Metric group used by "Database Activity" graphs.
    """

    name = "db_activity"
    xaxis = "ts"
    data_url = r"/server/(\d+)/metrics/db_activity/([^\/]+)/"
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
        "were terminated by fatal errors per "
        "second",
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
        query = powa_get_database_sample(True)

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


class ByQueryMetricGroup(MetricGroupDef):
    """Metric group for indivual query stats (displayed on the grid)."""

    name = "all_queries"
    xaxis = "queryid"
    axis_type = "category"
    data_url = r"/server/(\d+)/metrics/database_all_queries/([^\/]+)/"
    plantime = MetricDef(label="Plantime", type="duration")
    calls = MetricDef(label="#", type="integer")
    runtime = MetricDef(label="Time", type="duration", direction="descending")
    avg_runtime = MetricDef(label="Avg time", type="duration")
    shared_blks_read = MetricDef(label="Read", type="size")
    shared_blks_hit = MetricDef(label="Hit", type="size")
    shared_blks_dirtied = MetricDef(label="Dirtied", type="size")
    shared_blks_written = MetricDef(label="Written", type="size")
    temp_blks_read = MetricDef(label="Read", type="size")
    temp_blks_written = MetricDef(label="Written", type="size")
    blks_read_time = MetricDef(label="Total Read", type="duration")
    blks_write_time = MetricDef(label="Total Write", type="duration")
    wal_records = MetricDef(label="#Wal records", type="integer")
    wal_fpi = MetricDef(label="#Wal FPI", type="integer")
    wal_bytes = MetricDef(label="Wal bytes", type="size")
    jit_functions = MetricDef(label="#Functions", type="integer")
    jit_time = MetricDef(label="Time", type="duration")

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

    # TODO: refactor with GlobalDatabasesMetricGroup
    @property
    def query(self):
        # Working from the statdata detailed_db base query
        inner_query = powa_getstatdata_detailed_db()

        # Multiply each measure by the size of one block.
        cols = [
            "sub.srvid",
            "sub.queryid",
            "ps.query",
            "sum(sub.calls) AS calls",
            "sum(sub.runtime) AS runtime",
            mulblock("shared_blks_read", fn="sum"),
            mulblock("shared_blks_hit", fn="sum"),
            mulblock("shared_blks_dirtied", fn="sum"),
            mulblock("shared_blks_written", fn="sum"),
            mulblock("temp_blks_read", fn="sum"),
            mulblock("temp_blks_written", fn="sum"),
            "sum(sub.runtime) / greatest(sum(sub.calls), 1) AS avg_runtime",
            "sum(sub.shared_blk_read_time "
            + "+ sub.local_blk_read_time "
            + "+ sub.temp_blk_read_time) AS blks_read_time",
            "sum(sub.shared_blk_write_time "
            + "+ sub.local_blk_write_time "
            + "+ sub.temp_blk_write_time) AS blks_write_time",
        ]

        if self.has_extension_version(
            self.path_args[0], "pg_stat_statements", "1.8"
        ):
            cols.extend(
                [
                    "sum(sub.plantime) AS plantime",
                    "sum(sub.wal_records) AS wal_records",
                    "sum(sub.wal_fpi) AS wal_fpi",
                    "sum(sub.wal_bytes) AS wal_bytes",
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

        from_clause = """(
                {inner_query}
            ) AS sub
            JOIN {{powa}}.powa_statements AS ps
                USING (srvid, queryid, userid, dbid)
            CROSS JOIN {bs}""".format(inner_query=inner_query, bs=block_size)

        return """SELECT {cols}
                FROM {from_clause}
                whERE datname = %(database)s
                GROUP BY srvid, queryid, query, block_size
                ORDER BY sum(runtime) DESC""".format(
            cols=", ".join(cols), from_clause=from_clause
        )

    def process(self, val, database=None, **kwargs):
        val["url"] = self.reverse_url(
            "QueryOverview", val["srvid"], database, val["queryid"]
        )
        return val


class ByQueryWaitSamplingMetricGroup(MetricGroupDef):
    """
    Metric group for indivual query wait events stats (displayed on the grid).
    """

    name = "all_queries_waits"
    xaxis = "query"
    axis_type = "category"
    data_url = r"/server/(\d+)/metrics/database_all_queries_waits/([^\/]+)/"
    counts = MetricDef(
        label="# of events", type="integer", direction="descending"
    )

    @property
    def query(self):
        # Working from the waitdata detailed_db base query
        inner_query = powa_getwaitdata_detailed_db()

        cols = [
            "srvid",
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
            WHERE datname = %(database)s
            GROUP BY srvid, queryid, query, event_type, event
            ORDER BY sum(count) DESC""".format(
            cols=", ".join(cols), from_clause=from_clause
        )

    def process(self, val, database=None, **kwargs):
        val["url"] = self.reverse_url(
            "QueryOverview", val["srvid"], database, val["queryid"]
        )
        return val


class ByFuncUserFuncMetricGroup(MetricGroupDef):
    """
    Metric group for indivual function stats (displayed on the grid).
    """

    name = "all_functions_stats"
    xaxis = "funcname"
    axis_type = "category"
    data_url = r"/server/(\d+)/metrics/database_all_functions_stats/([^\/]+)/"
    lanname = MetricDef(label="Language", type="string")
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
        # Working from the waitdata detailed_db base query
        inner_query = powa_getuserfuncdata_detailed_db()

        return inner_query + " ORDER BY calls DESC"

    def process(self, val, database=None, **kwargs):
        val["url"] = self.reverse_url(
            "FunctionOverview", val["srvid"], database, val["funcid"]
        )
        return val


class WizardThisDatabase(ContentWidget):
    title = "Apply wizardry to this database"

    data_url = r"/server/(\d+)/database/([^\/]+)/wizardthisdatabase/"

    def get(self, database):
        self.render_json(dict(url=self.reverse_url("WizardPage", database)))


class DatabaseOverview(DashboardPage):
    """DatabaseOverview Dashboard."""

    base_url = r"/server/(\d+)/database/([^\/]+)/overview"
    datasources = [
        DatabaseOverviewMetricGroup,
        ByQueryMetricGroup,
        ByQueryWaitSamplingMetricGroup,
        WizardMetricGroup,
        DatabaseWaitOverviewMetricGroup,
        ConfigChangesDatabase,
        DatabaseAllRelMetricGroup,
        DatabaseUserFuncMetricGroup,
        ByFuncUserFuncMetricGroup,
        DatabasePGSAOverview,
        DatabaseDbActivityMetricGroup,
    ]
    params = ["server", "database"]
    parent = ServerOverview
    title = "%(database)s"
    timeline = ConfigChangesDatabase

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

        self._dashboard = Dashboard("Database overview for %(database)s")

        db_metrics = [
            DatabaseOverviewMetricGroup.avg_runtime,
            DatabaseOverviewMetricGroup.load,
            DatabaseOverviewMetricGroup.calls,
        ]
        if pgss18:
            db_metrics.extend([DatabaseOverviewMetricGroup.planload])
        block_graph = Graph(
            "Blocks (On database %(database)s)",
            metrics=[DatabaseOverviewMetricGroup.total_blks_hit],
            color_scheme=None,
        )

        db_graphs = [
            [
                Graph("Calls (On database %(database)s)", metrics=db_metrics),
                block_graph,
            ]
        ]

        if "nb_parallel_query" in DatabasePGSAOverview._get_metrics(self):
            parallel_metrics = ["nb_parallel_query", "nb_parallel_worker"]
        else:
            parallel_metrics = []

        pgsa_metrics = DatabasePGSAOverview.split(
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
        db_graphs.append(
            [
                Graph(
                    "Global activity (On database %(database)s)",
                    metrics=pgsa_metrics[0],
                    desc=DatabasePGSAOverview.desc,
                    renderer="bar",
                    stack=True,
                )
            ]
        )
        if len(pgsa_metrics[2]) > 0:
            db_graphs[1].append(
                Graph(
                    "Parallel query (On database %(database)s)",
                    metrics=pgsa_metrics[2],
                )
            )
        db_graphs[1].append(
            Graph(
                "Backend age (On database %(database)s)",
                metrics=pgsa_metrics[1],
                desc=DatabasePGSAOverview.desc,
            )
        )

        graphs_dash = [Dashboard("General Overview", db_graphs)]
        graphs = [TabContainer("All databases", graphs_dash)]

        if pgss18:
            # Add WALs graphs
            wals_graphs = [
                [
                    Graph(
                        "WAL activity",
                        metrics=[
                            DatabaseOverviewMetricGroup.wal_records,
                            DatabaseOverviewMetricGroup.wal_fpi,
                            DatabaseOverviewMetricGroup.wal_bytes,
                        ],
                    ),
                ]
            ]
            graphs_dash.append(Dashboard("WALs", wals_graphs))

        # Add JIT graphs
        if pgss110:
            jit_tim = [
                DatabaseOverviewMetricGroup.jit_inlining_time,
                DatabaseOverviewMetricGroup.jit_optimization_time,
                DatabaseOverviewMetricGroup.jit_emission_time,
            ]

            if pgss111:
                jit_tim.extend(
                    [
                        DatabaseOverviewMetricGroup.jit_deform_time,
                        DatabaseOverviewMetricGroup.jit_expr_time,
                    ]
                )
            else:
                jit_tim.append(DatabaseOverviewMetricGroup.jit_generation_time)

            jit_cnt = [
                DatabaseOverviewMetricGroup.jit_functions,
                DatabaseOverviewMetricGroup.jit_inlining_count,
                DatabaseOverviewMetricGroup.jit_optimization_count,
                DatabaseOverviewMetricGroup.jit_emission_count,
            ]

            if pgss111:
                jit_cnt.append(DatabaseOverviewMetricGroup.jit_deform_count)

            jit_graphs = [
                [Graph("JIT timing", metrics=jit_tim, stack=True)],
                [Graph("JIT scheduling", metrics=jit_cnt)],
            ]

            graphs_dash.append(Dashboard("JIT", jit_graphs))

        # Add pg_stat_database graphs
        global_db_graphs = [
            [
                Graph(
                    "Transactions per second",
                    metrics=[
                        DatabaseDbActivityMetricGroup.xact_commit,
                        DatabaseDbActivityMetricGroup.xact_rollback,
                    ],
                    renderer="bar",
                    stack=True,
                ),
                Graph(
                    "Conflicts & deadlocks",
                    metrics=[
                        DatabaseDbActivityMetricGroup.conflicts,
                        DatabaseDbActivityMetricGroup.deadlocks,
                    ],
                ),
            ]
        ]
        if "sessions" in DatabaseDbActivityMetricGroup._get_metrics(self):
            global_db_graphs.append(
                [
                    Graph(
                        "Cumulated time per second",
                        metrics=[
                            DatabaseDbActivityMetricGroup.session_time,
                            DatabaseDbActivityMetricGroup.active_time,
                            DatabaseDbActivityMetricGroup.idle_in_transaction_time,
                        ],
                    ),
                    Graph(
                        "Sessions per second",
                        metrics=[
                            DatabaseDbActivityMetricGroup.sessions,
                            DatabaseDbActivityMetricGroup.sessions_abandoned,
                            DatabaseDbActivityMetricGroup.sessions_fatal,
                            DatabaseDbActivityMetricGroup.sessions_killed,
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
                        DatabaseAllRelMetricGroup.seq_scan,
                        DatabaseAllRelMetricGroup.idx_scan,
                        DatabaseAllRelMetricGroup.idx_ratio,
                    ],
                ),
                Graph(
                    "DML activity",
                    metrics=[
                        DatabaseAllRelMetricGroup.n_tup_del,
                        DatabaseAllRelMetricGroup.n_tup_hot_upd,
                        DatabaseAllRelMetricGroup.n_tup_upd,
                        DatabaseAllRelMetricGroup.n_tup_ins,
                    ],
                ),
            ],
            [
                Graph(
                    "Vacuum activity",
                    metrics=[
                        DatabaseAllRelMetricGroup.autoanalyze_count,
                        DatabaseAllRelMetricGroup.analyze_count,
                        DatabaseAllRelMetricGroup.autovacuum_count,
                        DatabaseAllRelMetricGroup.vacuum_count,
                    ],
                ),
                Graph(
                    "Object size",
                    metrics=[
                        DatabaseAllRelMetricGroup.tbl_size,
                        DatabaseAllRelMetricGroup.idx_size,
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
                metrics=DatabaseUserFuncMetricGroup.all(self),
            )
        ]
        user_fct_grid = [
            Grid(
                "User functions activity",
                columns=[
                    {
                        "name": "func_name",
                        "label": "Function name",
                        "url_attr": "url",
                    }
                ],
                metrics=ByFuncUserFuncMetricGroup.all(self),
            )
        ]
        graphs_dash.append(
            Dashboard("User functions", [user_fct_graph, user_fct_grid])
        )

        if self.has_extension(self.path_args[0], "pg_stat_kcache"):
            block_graph.metrics.insert(
                0, DatabaseOverviewMetricGroup.total_sys_hit
            )
            block_graph.metrics.insert(
                0, DatabaseOverviewMetricGroup.total_disk_read
            )
            block_graph.color_scheme = ["#cb513a", "#65b9ac", "#73c03a"]

            sys_graphs = [
                Graph(
                    "System resources (events per sec)",
                    url=self.docs_stats_url + "pg_stat_kcache.html",
                    metrics=[
                        DatabaseOverviewMetricGroup.majflts,
                        DatabaseOverviewMetricGroup.minflts,
                        # DatabaseOverviewMetricGroup.nswaps,
                        # DatabaseOverviewMetricGroup.msgsnds,
                        # DatabaseOverviewMetricGroup.msgrcvs,
                        # DatabaseOverviewMetricGroup.nsignals,
                        DatabaseOverviewMetricGroup.nvcsws,
                        DatabaseOverviewMetricGroup.nivcsws,
                    ],
                )
            ]

            graphs_dash.append(Dashboard("System resources", [sys_graphs]))
        else:
            block_graph.metrics.insert(
                0, DatabaseOverviewMetricGroup.total_blks_read
            )
            block_graph.color_scheme = ["#cb513a", "#73c03a"]

        if self.has_extension(self.path_args[0], "pg_wait_sampling"):
            metrics = None
            pg_version_num = self.get_pg_version_num(self.path_args[0])
            # if we can't connect to the remote server, assume pg10 or above
            if pg_version_num is not None and pg_version_num < 100000:
                metrics = [
                    DatabaseWaitOverviewMetricGroup.count_lwlocknamed,
                    DatabaseWaitOverviewMetricGroup.count_lwlocktranche,
                    DatabaseWaitOverviewMetricGroup.count_lock,
                    DatabaseWaitOverviewMetricGroup.count_bufferpin,
                ]
            else:
                metrics = [
                    DatabaseWaitOverviewMetricGroup.count_lwlock,
                    DatabaseWaitOverviewMetricGroup.count_lock,
                    DatabaseWaitOverviewMetricGroup.count_bufferpin,
                    DatabaseWaitOverviewMetricGroup.count_activity,
                    DatabaseWaitOverviewMetricGroup.count_client,
                    DatabaseWaitOverviewMetricGroup.count_extension,
                    DatabaseWaitOverviewMetricGroup.count_ipc,
                    DatabaseWaitOverviewMetricGroup.count_timeout,
                    DatabaseWaitOverviewMetricGroup.count_io,
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
                # query
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
                {"name": "I/O Time", "colspan": 2},
            ]
        )

        if pgss18:
            toprow.extend([{"name": "WALs", "colspan": 3}])

        if pgss110:
            toprow.extend([{"name": "JIT", "colspan": 2}])
        self._dashboard.widgets.extend(
            [
                graphs,
                [
                    Grid(
                        "Details for all queries",
                        toprow=toprow,
                        columns=[
                            {
                                "name": "query",
                                "label": "Query",
                                "type": "query",
                                "url_attr": "url",
                                "max_length": 70,
                            }
                        ],
                        metrics=ByQueryMetricGroup.all(self),
                    )
                ],
            ]
        )

        if self.has_extension(self.path_args[0], "pg_wait_sampling"):
            self._dashboard.widgets.extend(
                [
                    [
                        Grid(
                            "Wait events for all queries",
                            url=self.docs_stats_url + "pg_wait_sampling.html",
                            columns=[
                                {
                                    "name": "query",
                                    "label": "Query",
                                    "type": "query",
                                    "url_attr": "url",
                                    "max_length": 70,
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
                            metrics=ByQueryWaitSamplingMetricGroup.all(),
                        )
                    ]
                ]
            )

        self._dashboard.widgets.extend([[Wizard("Index suggestions")]])
        return self._dashboard

    @classmethod
    def breadcrum_title(cls, handler, param):
        return param["database"]
