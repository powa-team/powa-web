"""
Index page presenting an overview of the cluster stats.
"""

from sqlalchemy import and_
from sqlalchemy.sql.functions import sum
from sqlalchemy.sql import select, case, cast, extract, bindparam
from sqlalchemy.types import Numeric
from tornado.web import HTTPError
from powa.framework import AuthHandler
from powa.dashboards import (
    Dashboard, Graph, Grid,
    MetricGroupDef, MetricDef,
    DashboardPage, TabContainer)
from powa.config import ConfigChangesGlobal

from powa.sql.views import (
    powa_getstatdata_db,
    powa_getwaitdata_db,
    powa_getstatdata_sample,
    kcache_getstatdata_sample,
    powa_getwaitdata_sample,
    powa_get_bgwriter_sample,
    powa_get_all_tbl_sample)
from powa.sql.utils import (total_read, total_hit, mulblock, round, greatest,
                            block_size, inner_cc, to_epoch)
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
    plantime = MetricDef(label="Plantime", type="duration")
    runtime = MetricDef(label="Runtime", type="duration")
    avg_runtime = MetricDef(label="Avg runtime", type="duration")
    shared_blks_read = MetricDef(label="Blocks read", type="size")
    shared_blks_hit = MetricDef(label="Blocks hit", type="size")
    shared_blks_dirtied = MetricDef(label="Blocks dirtied", type="size")
    shared_blks_written = MetricDef(label="Blocks written", type="size")
    temp_blks_written = MetricDef(label="Temp Blocks written", type="size")
    io_time = MetricDef(label="I/O time", type="duration")
    wal_records = MetricDef(label="#Wal records", type="integer")
    wal_fpi = MetricDef(label="#Wal FPI", type="integer")
    wal_bytes = MetricDef(label="Wal bytes", type="size")
    params = ["server"]

    @classmethod
    def _get_metrics(cls, handler, **params):
        base = cls.metrics.copy()

        if not handler.has_extension_version(handler.path_args[0],
                                             'pg_stat_statements', '1.8'):
            for key in ("plantime", "wal_records", "wal_fpi", "wal_bytes"):
                base.pop(key)
        return base

    @property
    def query(self):
        bs = block_size.c.block_size
        inner_query = powa_getstatdata_db(bindparam("server")).alias()
        c = inner_query.c
        from_clause = inner_query.join(
            powa_databases,
            and_(c.dbid == powa_databases.c.oid,
                 c.srvid == powa_databases.c.srvid))

        cols = [powa_databases.c.srvid,
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
                ]

        if self.has_extension_version(self.path_args[0], 'pg_stat_statements',
                                      '1.8'):
            cols.extend([
                sum(c.plantime).label("plantime"),
                sum(c.wal_records).label("wal_records"),
                sum(c.wal_fpi).label("wal_fpi"),
                sum(c.wal_bytes).label("wal_bytes")
                ])

        return (select(cols)
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
    xaxis = "ts"
    data_url = r"/server/(\d+)/metrics/databases_globals/"
    avg_runtime = MetricDef(label="Avg runtime", type="duration",
                            desc="Average query duration")
    calls = MetricDef(label="Queries per sec", type="number",
                      desc="Number of time the query has been executed")
    planload = MetricDef(label="Plantime per sec", type="duration",
                         desc="Total planning duration")
    load = MetricDef(label="Runtime per sec", type="duration",
                     desc="Total duration of queries executed")
    total_blks_hit = MetricDef(label="Total hit", type="sizerate",
                               desc="Amount of data found in shared buffers")
    total_blks_read = MetricDef(label="Total read", type="sizerate",
                                desc="Amount of data found in OS cache or"
                                     " read from disk")
    wal_records = MetricDef(label="#Wal records", type="integer",
                            desc="Number of WAL records generated")
    wal_fpi = MetricDef(label="#Wal FPI", type="integer",
                        desc="Number of WAL full-page images generated")
    wal_bytes = MetricDef(label="Wal bytes", type="size",
                          desc="Amount of WAL bytes generated")

    total_sys_hit = MetricDef(label="Total system cache hit", type="sizerate",
                              desc="Amount of data found in OS cache")
    total_disk_read = MetricDef(label="Total disk read", type="sizerate",
                                desc="Amount of data read from disk")
    minflts = MetricDef(label="Soft page faults", type="number",
                        desc="Memory pages not found in the processor's MMU")
    majflts = MetricDef(label="Hard page faults", type="number",
                        desc="Memory pages not found in memory and loaded"
                             " from storage")
    # not maintained on GNU/Linux, and not available on Windows
    # nswaps = MetricDef(label="Swaps", type="number")
    # msgsnds = MetricDef(label="IPC messages sent", type="number")
    # msgrcvs = MetricDef(label="IPC messages received", type="number")
    # nsignals = MetricDef(label="Signals received", type="number")
    nvcsws = MetricDef(label="Voluntary context switches", type="number",
                       desc="Number of voluntary context switches")
    nivcsws = MetricDef(label="Involuntary context switches", type="number",
                        desc="Number of involuntary context switches")

    @classmethod
    def _get_metrics(cls, handler, **params):
        base = cls.metrics.copy()
        if not handler.has_extension(params["server"], "pg_stat_kcache"):
            for key in ("total_sys_hit", "total_disk_read", "minflts",
                        "majflts",
                        # "nswaps", "msgsnds", "msgrcvs", "nsignals",
                        "nvcsws", "nivcsws"):
                base.pop(key)
        else:
            base.pop("total_blks_read")

        if not handler.has_extension_version(params["server"],
                                             'pg_stat_statements', '1.8'):
            for key in ("planload", "wal_records", "wal_fpi", "wal_bytes"):
                base.pop(key)
        return base

    @property
    def query(self):
        bs = block_size.c.block_size
        query = powa_getstatdata_sample("db", bindparam("server"))
        query = query.alias()
        c = query.c

        cols = [c.srvid,
                extract("epoch", c.ts).label("ts"),
                (sum(c.calls) / greatest(extract("epoch", c.mesure_interval),
                                         1)).label("calls"),
                (sum(c.runtime) / greatest(sum(c.calls),
                                           1)).label("avg_runtime"),
                (sum(c.runtime) / greatest(extract("epoch", c.mesure_interval),
                                           1)).label("load"),
                total_read(c),
                total_hit(c)
                ]

        if self.has_extension_version(self.path_args[0],
                                      'pg_stat_statements', '1.8'):
            cols.extend([
                (sum(c.plantime) / greatest(extract("epoch", c.mesure_interval),
                                            1)).label("planload"),
                (sum(c.wal_records) / greatest(extract("epoch",
                                                       c.mesure_interval),
                                               1)).label("wal_records"),
                (sum(c.wal_fpi) / greatest(extract("epoch",
                                                   c.mesure_interval),
                                           1)).label("wal_fpi"),
                (sum(c.wal_bytes) / greatest(extract("epoch",
                                                     c.mesure_interval),
                                             1)).label("wal_bytes")
                ])

        from_clause = query
        if self.has_extension(self.path_args[0], "pg_stat_kcache"):
            # Add system metrics from pg_stat_kcache,
            kcache_query = kcache_getstatdata_sample("db")
            kc = inner_cc(kcache_query)
            kcache_query = (
                kcache_query
                .where(
                    (kc.srvid == bindparam("server"))
                    )
                .alias())
            kc = kcache_query.c

            def sum_per_sec(col):
                ts = extract("epoch", greatest(c.mesure_interval, '1 second'))
                return (sum(col) / ts).label(col.name)

            total_sys_hit = (total_read(c) - sum(kc.reads) /
                             greatest(extract("epoch", c.mesure_interval), 1.)
                             ).label("total_sys_hit")
            total_disk_read = (sum(kc.reads) /
                               greatest(extract("epoch", c.mesure_interval), 1.)
                               ).label("total_disk_read")
            minflts = sum_per_sec(kc.minflts)
            majflts = sum_per_sec(kc.majflts)
            # nswaps = sum_per_sec(kc.nswaps)
            # msgsnds = sum_per_sec(kc.msgsnds)
            # msgrcvs = sum_per_sec(kc.msgrcvs)
            # nsignals = sum_per_sec(kc.nsignals)
            nvcsws = sum_per_sec(kc.nvcsws)
            nivcsws = sum_per_sec(kc.nivcsws)

            cols.extend([total_sys_hit, total_disk_read, minflts, majflts,
                         # nswaps, msgsnds, msgrcvs, nsignals,
                         nvcsws, nivcsws])
            from_clause = from_clause.join(
                kcache_query,
                and_(kcache_query.c.dbid == c.dbid,
                     kcache_query.c.ts == c.ts))

        return (select(cols)
                .select_from(from_clause)
                .where(c.calls != '0')
                .group_by(c.srvid, c.ts, bs, c.mesure_interval)
                .order_by(c.ts)
                .params(samples=100))


class GlobalWaitsMetricGroup(MetricGroupDef):
    """Metric group for global wait events graphs."""
    name = "all_databases_waits"
    xaxis = "ts"
    data_url = r"/server/(\d+)/metrics/databases_waits/"
    # pg 9.6 only metrics
    count_lwlocknamed = MetricDef(label="Lightweight Named",
                                  desc="Number of named lightweight lock"
                                       " wait events")
    count_lwlocktranche = MetricDef(label="Lightweight Tranche",
                                    desc="Number of lightweight lock tranche"
                                         " wait events")
    # pg 10+ metrics
    count_lwlock = MetricDef(label="Lightweight Lock",
                             desc="Number of wait events due to lightweight"
                                  " locks")
    count_lock = MetricDef(label="Lock",
                           desc="Number of wait events due to heavyweight"
                                " locks")
    count_bufferpin = MetricDef(label="Buffer pin",
                                desc="Number of wait events due to buffer pin")
    count_activity = MetricDef(label="Activity",
                               desc="Number of wait events due to postgres"
                                    " internal processes activity")
    count_client = MetricDef(label="Client",
                             desc="Number of wait events due to client"
                                  " activity")
    count_extension = MetricDef(label="Extension",
                                desc="Number wait events due to third-party"
                                " extensions")
    count_ipc = MetricDef(label="IPC",
                          desc="Number of wait events due to inter-process"
                               "communication")
    count_timeout = MetricDef(label="Timeout",
                              desc="Number of wait events due to timeouts")
    count_io = MetricDef(label="IO",
                         desc="Number of wait events due to IO operations")

    def prepare(self):
        if not self.has_extension(self.path_args[0], "pg_wait_sampling"):
            raise HTTPError(501, "pg_wait_sampling is not installed")

    @property
    def query(self):
        query = powa_getwaitdata_sample(bindparam("server"), "db")
        query = query.alias()
        c = query.c

        def wps(col):
            ts = extract("epoch", greatest(c.mesure_interval, '1 second'))
            return (sum(col) / ts).label(col.name)

        cols = [to_epoch(c.ts)]

        pg_version_num = self.get_pg_version_num(self.path_args[0])
        # if we can't connect to the remote server, assume pg10 or above
        if pg_version_num is None or pg_version_num < 100000:
            cols += [wps(c.count_lwlocknamed), wps(c.count_lwlocktranche),
                     wps(c.count_lock), wps(c.count_bufferpin)]
        else:
            cols += [wps(c.count_lwlock), wps(c.count_lock),
                     wps(c.count_bufferpin), wps(c.count_activity),
                     wps(c.count_client), wps(c.count_extension),
                     wps(c.count_ipc), wps(c.count_timeout), wps(c.count_io)]

        from_clause = query

        return (select(cols)
                .select_from(from_clause)
                #.where(c.count != None)
                .group_by(c.ts, c.mesure_interval)
                .order_by(c.ts)
                .params(samples=100))


class GlobalBgwriterMetricGroup(MetricGroupDef):
    """
    Metric group used by bgwriter graphs.
    """
    name = "bgwriter"
    xaxis = "ts"
    data_url = r"/server/(\d+)/metrics/bgwriter/"
    checkpoints_timed = MetricDef(label="# of scheduled checkpoints",
                                  type="number",
                                  desc="Number of scheduled checkpoints that"
                                       " have been performed")
    checkpoints_req = MetricDef(label="# of requested checkpoints",
                                type="number",
                                desc="Number of requested checkpoints that"
                                     " have been performed")
    checkpoint_write_time = MetricDef(label="Write time",
                                      type="duration",
                                      desc="Total amount of time that has been"
                                      " spent in the portion of checkpoint"
                                      " processing where files are written to"
                                      " disk, in milliseconds")
    checkpoint_sync_time = MetricDef(label="Sync time",
                                     type="duration",
                                     desc="Total amount of time that has been"
                                     " spent in the portion of checkpoint"
                                     " processing where files are synchronized"
                                     " to disk, in milliseconds")
    buffers_checkpoint = MetricDef(label="Buffers checkpoint",
                                   type="sizerate",
                                   desc="Number of buffers written during"
                                   " checkpoints")
    buffers_clean = MetricDef(label="Buffers clean",
                              type="sizerate",
                              desc="Number of buffers written by the"
                                   " background writer")
    maxwritten_clean = MetricDef(label="Maxwritten clean",
                                 type="number",
                                 desc="Number of times the background writer"
                                      " stopped a cleaning scan because it had"
                                      " written too many buffers")
    buffers_backend = MetricDef(label="Buffers backend",
                                type="sizerate",
                                desc="Number of buffers written directly by a"
                                      " backend")
    buffers_backend_fsync = MetricDef(label="Buffers backend fsync",
                                      type="number",
                                      desc="Number of times a backend had to"
                                      " execute its own fsync call"
                                      " (normally the background writer handles"
                                      " those even when the backend does its"
                                      " own write")
    buffers_alloc = MetricDef(label="Buffers alloc",
                                type="sizerate",
                                desc="Number of buffers allocated")

    @property
    def query(self):
        bs = block_size.c.block_size
        query = powa_get_bgwriter_sample(bindparam("server"))
        query = query.alias()
        c = query.c

        def sum_per_sec(col):
            ts = extract("epoch", greatest(c.mesure_interval, '1 second'))
            return (sum(col) / ts).label(col.name)

        from_clause = query

        cols = [c.srvid,
                extract("epoch", c.ts).label("ts"),
                sum(c.checkpoints_timed).label("checkpoints_timed"),
                sum(c.checkpoints_req).label("checkpoints_req"),
                sum_per_sec(c.checkpoint_write_time),
                sum_per_sec(c.checkpoint_sync_time),
                sum_per_sec(mulblock(c.buffers_checkpoint)),
                sum_per_sec(mulblock(c.buffers_clean)),
                sum_per_sec(c.maxwritten_clean),
                sum_per_sec(mulblock(c.buffers_backend)),
                sum_per_sec(c.buffers_backend_fsync),
                sum_per_sec(mulblock(c.buffers_alloc))]

        return (select(cols)
                .select_from(from_clause)
                .where(c.mesure_interval != '0')
                .group_by(c.srvid, c.ts, bs, c.mesure_interval)
                .order_by(c.ts)
                .params(samples=100))


class GlobalAllRelMetricGroup(MetricGroupDef):
    """
    Metric group used by "Database objects" graphs.
    """
    name = "all_relations"
    xaxis = "ts"
    data_url = r"/server/(\d+)/metrics/all_relations/"
    idx_ratio = MetricDef(label="Index scans ratio", type="percent",
                          desc="Ratio of index scan / seq scan")
    idx_scan = MetricDef(label="Index scans", type="number",
                         desc="Number of index scan per second")
    seq_scan = MetricDef(label="Sequential scans", type="number",
                         desc="Number of sequential scan per second")
    n_tup_ins = MetricDef(label="Tuples inserted", type="number",
                          desc="Number of tuples inserted per second")
    n_tup_upd = MetricDef(label="Tuples updated", type="number",
                          desc="Number of tuples updated per second")
    n_tup_hot_upd = MetricDef(label="Tuples HOT updated", type="number",
                              desc="Number of tuples HOT updated per second")
    n_tup_del = MetricDef(label="Tuples deleted", type="number",
                          desc="Number of tuples deleted per second")
    vacuum_count = MetricDef(label="# Vacuum", type="number",
                             desc="Number of vacuum per second")
    autovacuum_count = MetricDef(label="# Autovacuum", type="number",
                                 desc="Number of autovacuum per second")
    analyze_count = MetricDef(label="# Analyze", type="number",
                              desc="Number of analyze per second")
    autoanalyze_count = MetricDef(label="# Autoanalyze", type="number",
                                  desc="Number of autoanalyze per second")

    @property
    def query(self):
        query = powa_get_all_tbl_sample("db", bindparam("server"))
        query = query.alias()
        c = query.c

        def sum_per_sec(col):
            ts = extract("epoch", greatest(c.mesure_interval, '1 second'))
            return (sum(col) / ts).label(col.name)

        from_clause = query

        cols = [c.srvid,
                extract("epoch", c.ts).label("ts"),
                case([(sum(c.idx_scan + c.seq_scan) == 0, 0)],
                     else_=cast(sum(c.idx_scan), Numeric) * 100 /
                     sum(c.idx_scan + c.seq_scan)).label("idx_ratio"),
                sum_per_sec(c.idx_scan),
                sum_per_sec(c.seq_scan),
                sum_per_sec(c.n_tup_ins),
                sum_per_sec(c.n_tup_upd),
                sum_per_sec(c.n_tup_hot_upd),
                sum_per_sec(c.n_tup_del),
                sum_per_sec(c.vacuum_count),
                sum_per_sec(c.autovacuum_count),
                sum_per_sec(c.analyze_count),
                sum_per_sec(c.autoanalyze_count)]

        return (select(cols)
                .select_from(from_clause)
                .where(c.mesure_interval != '0')
                .group_by(c.srvid, c.ts, c.mesure_interval)
                .order_by(c.ts)
                .params(samples=100))


class ServerOverview(DashboardPage):
    """
    ServerOverview dashboard page.
    """
    base_url = r"/server/(\d+)/overview/"
    datasources = [GlobalDatabasesMetricGroup, ByDatabaseMetricGroup,
                   ByDatabaseWaitSamplingMetricGroup, GlobalWaitsMetricGroup,
                   GlobalBgwriterMetricGroup, GlobalAllRelMetricGroup,
                   ConfigChangesGlobal]
    params = ["server"]
    title = "All databases"
    timeline = ConfigChangesGlobal

    def dashboard(self):
        # This COULD be initialized in the constructor, but tornado < 3 doesn't
        # call it
        if getattr(self, '_dashboard', None) is not None:
            return self._dashboard

        pgss18 = self.has_extension_version(self.path_args[0],
                                            'pg_stat_statements', '1.8')

        all_db_metrics = [GlobalDatabasesMetricGroup.avg_runtime,
                          GlobalDatabasesMetricGroup.load,
                          GlobalDatabasesMetricGroup.calls]
        if pgss18:
            all_db_metrics.extend([GlobalDatabasesMetricGroup.planload])

        block_graph = Graph("Block access in Bps",
                            metrics=[GlobalDatabasesMetricGroup.
                                     total_blks_hit],
                            color_scheme=None)

        all_db_graphs = [Graph("Query runtime per second (all databases)",
                               metrics=all_db_metrics),
                         block_graph]

        graphs_dash = [Dashboard("General Overview", [all_db_graphs])]
        graphs = [TabContainer("All databases", graphs_dash)]

        # Add WALs graphs
        if pgss18:
            wals_graphs = [[Graph("WAL activity",
                            metrics=[GlobalDatabasesMetricGroup.wal_records,
                                     GlobalDatabasesMetricGroup.wal_fpi,
                                     GlobalDatabasesMetricGroup.wal_bytes]),
                            ]]
            graphs_dash.append(Dashboard("WALs", wals_graphs))

        # Add pg_stat_bgwriter graphs
        bgw_graphs = [[Graph("Checkpointer scheduling",
                      metrics=[GlobalBgwriterMetricGroup.checkpoints_timed,
                               GlobalBgwriterMetricGroup.checkpoints_req]),
                      Graph("Checkpointer activity",
                      metrics=[GlobalBgwriterMetricGroup.checkpoint_write_time,
                               GlobalBgwriterMetricGroup.checkpoint_sync_time,
                               GlobalBgwriterMetricGroup.buffers_checkpoint,
                               GlobalBgwriterMetricGroup.buffers_alloc])],
                      [Graph("Background writer",
                       metrics=[GlobalBgwriterMetricGroup.buffers_clean,
                                GlobalBgwriterMetricGroup.maxwritten_clean]),
                       Graph("Backends",
                       metrics=[GlobalBgwriterMetricGroup.buffers_backend,
                                GlobalBgwriterMetricGroup.buffers_backend_fsync
                                ])
                       ]]
        graphs_dash.append(Dashboard("Background Writer", bgw_graphs))

        # Add powa_stat_all_relations graphs
        all_rel_graphs = [Graph("Access pattern",
                          metrics=[GlobalAllRelMetricGroup.seq_scan,
                                   GlobalAllRelMetricGroup.idx_scan,
                                   GlobalAllRelMetricGroup.idx_ratio]),
                          Graph("DML activity",
                          metrics=[GlobalAllRelMetricGroup.n_tup_del,
                                   GlobalAllRelMetricGroup.n_tup_hot_upd,
                                   GlobalAllRelMetricGroup.n_tup_upd,
                                   GlobalAllRelMetricGroup.n_tup_ins]),
                          Graph("Vacuum activity",
                          metrics=[GlobalAllRelMetricGroup.autoanalyze_count,
                                   GlobalAllRelMetricGroup.analyze_count,
                                   GlobalAllRelMetricGroup.autovacuum_count,
                                   GlobalAllRelMetricGroup.vacuum_count])]
        graphs_dash.append(Dashboard("Database Objects", [all_rel_graphs]))

        if self.has_extension(self.path_args[0], "pg_stat_kcache"):
            block_graph.metrics.insert(0, GlobalDatabasesMetricGroup.
                                       total_sys_hit)
            block_graph.metrics.insert(0, GlobalDatabasesMetricGroup.
                                       total_disk_read)
            block_graph.color_scheme = ['#cb513a', '#65b9ac', '#73c03a']

            sys_graphs = [Graph("System resources (events per sec)",
                                url=self.docs_stats_url + "pg_stat_kcache.html",
                                metrics=[GlobalDatabasesMetricGroup.majflts,
                                         GlobalDatabasesMetricGroup.minflts,
                                         # GlobalDatabasesMetricGroup.nswaps,
                                         # GlobalDatabasesMetricGroup.msgsnds,
                                         # GlobalDatabasesMetricGroup.msgrcvs,
                                         # GlobalDatabasesMetricGroup.nsignals,
                                         GlobalDatabasesMetricGroup.nvcsws,
                                         GlobalDatabasesMetricGroup.nivcsws])]

            graphs_dash.append(Dashboard("System resources", [sys_graphs]))
        else:
            block_graph.metrics.insert(0, GlobalDatabasesMetricGroup.
                                       total_blks_read)
            block_graph.color_scheme = ['#cb513a', '#73c03a']

        if (self.has_extension(self.path_args[0], "pg_wait_sampling")):
            metrics=None
            pg_version_num = self.get_pg_version_num(self.path_args[0])
            # if we can't connect to the remote server, assume pg10 or above
            if pg_version_num is None or pg_version_num < 100000:
                metrics = [GlobalWaitsMetricGroup.count_lwlocknamed,
                           GlobalWaitsMetricGroup.count_lwlocktranche,
                           GlobalWaitsMetricGroup.count_lock,
                           GlobalWaitsMetricGroup.count_bufferpin]
            else:
                metrics = [GlobalWaitsMetricGroup.count_lwlock,
                           GlobalWaitsMetricGroup.count_lock,
                           GlobalWaitsMetricGroup.count_bufferpin,
                           GlobalWaitsMetricGroup.count_activity,
                           GlobalWaitsMetricGroup.count_client,
                           GlobalWaitsMetricGroup.count_extension,
                           GlobalWaitsMetricGroup.count_ipc,
                           GlobalWaitsMetricGroup.count_timeout,
                           GlobalWaitsMetricGroup.count_io]

            graphs_dash.append(Dashboard("Wait Events",
                [[Graph("Wait Events (per second)",
                        url=self.docs_stats_url + "pg_wait_sampling.html",
                        metrics=metrics)]]))

        dashes = [graphs,
                  [Grid("Details for all databases",
                        columns=[{
                            "name": "datname",
                            "label": "Database",
                            "url_attr": "url"
                        }],
                        metrics=ByDatabaseMetricGroup.all(self))]]

        if self.has_extension(self.path_args[0], "pg_wait_sampling"):
            dashes.append([Grid("Wait events for all databases",
                                url=self.docs_stats_url + "pg_wait_sampling.html",
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
