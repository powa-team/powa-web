"""
Module containing the by-database dashboard.
"""
from sqlalchemy.sql import bindparam, column, select, extract, case, cast
from sqlalchemy.sql.functions import sum
from sqlalchemy.types import Numeric
from tornado.web import HTTPError
from powa.framework import AuthHandler
from powa.dashboards import (
    Dashboard, Graph, Grid, ContentWidget,
    MetricGroupDef, MetricDef,
    DashboardPage, TabContainer)

from powa.sql.views import (powa_getstatdata_detailed_db,
                            powa_getwaitdata_detailed_db,
                            powa_getstatdata_sample,
                            kcache_getstatdata_sample,
                            powa_getwaitdata_sample,
                            powa_get_all_tbl_sample)
from powa.wizard import WizardMetricGroup, Wizard
from powa.server import ServerOverview
from powa.sql.utils import (greatest, block_size, mulblock,
                            total_read, total_hit, to_epoch,
                            inner_cc)
from powa.sql.tables import powa_statements
from powa.config import ConfigChangesDatabase


class DatabaseSelector(AuthHandler):
    """Page allowing to choose a database."""

    def get(self):
        self.redirect(self.reverse_url(
            'DatabaseOverview',
            self.get_argument("server"),
            self.get_argument("database")))


class DatabaseOverviewMetricGroup(MetricGroupDef):
    """Metric group for the database global graphs."""
    name = "database_overview"
    xaxis = "ts"
    data_url = r"/server/(\d+)/metrics/database_overview/([^\/]+)/"
    avg_runtime = MetricDef(label="Avg runtime", type="duration",
                            desc="Average query duration")
    calls = MetricDef(label="Queries per sec", type="number",
                      desc="Number of time the query has been executed, "
                            "per second")
    planload = MetricDef(label="Plantime per sec", type="duration",
                         desc="Total planning duration")
    load = MetricDef(label="Runtime per sec", type="duration",
                     desc="Total duration of queries executed, per second")
    total_blks_hit = MetricDef(label="Total shared buffers hit",
                               type="sizerate",
                               desc="Amount of data found in shared buffers")
    total_blks_read = MetricDef(label="Total shared buffers miss",
                                type="sizerate",
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
        # Fetch the base query for sample, and filter them on the database
        bs = block_size.c.block_size
        subquery = powa_getstatdata_sample("db", bindparam("server"))
        # Put the where clause inside the subquery
        subquery = subquery.where(column("datname") == bindparam("database"))
        query = subquery.alias()
        c = query.c

        cols = [c.srvid,
                to_epoch(c.ts),
                (sum(c.calls) / greatest(extract("epoch", c.mesure_interval),
                                         1)).label("calls"),
                (sum(c.runtime) / greatest(sum(c.calls),
                                           1.)).label("avg_runtime"),
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
                    (kc.srvid == bindparam("server")) &
                    (kc.datname == bindparam("database"))
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
                kcache_query.c.ts == c.ts)

        return (select(cols)
                .select_from(from_clause)
                .where(c.calls != '0')
                .group_by(c.srvid, c.ts, bs, c.mesure_interval)
                .order_by(c.ts)
                .params(samples=100))


class DatabaseWaitOverviewMetricGroup(MetricGroupDef):
    """Metric group for the database global wait events graphs."""
    name = "database_waits_overview"
    xaxis = "ts"
    data_url = r"/server/(\d+)/metrics/database_waits_overview/([^\/]+)/"
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
        query = query.where(column("datname") == bindparam("database"))
        query = query.alias()
        c = query.c

        def wps(col):
            ts = extract("epoch", greatest(c.mesure_interval, '1 second'))
            return (col / ts).label(col.name)

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
                .order_by(c.ts)
                .params(samples=100))


class DatabaseAllRelMetricGroup(MetricGroupDef):
    """
    Metric group used by "Database objects" graphs.
    """
    name = "all_relations"
    xaxis = "ts"
    data_url = r"/server/(\d+)/metrics/database_all_relations/([^\/]+)/"
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
                .where(c.datname == bindparam("database"))
                .where(c.mesure_interval != '0')
                .group_by(c.srvid, c.ts, c.mesure_interval)
                .order_by(c.ts)
                .params(samples=100))


class ByQueryMetricGroup(MetricGroupDef):
    """Metric group for indivual query stats (displayed on the grid)."""
    name = "all_queries"
    xaxis = "queryid"
    axis_type = "category"
    data_url = r"/server/(\d+)/metrics/database_all_queries/([^\/]+)/"
    calls = MetricDef(label="#", type="integer")
    plantime = MetricDef(label="Plantime", type="duration")
    runtime = MetricDef(label="Time", type="duration", direction="descending")
    avg_runtime = MetricDef(label="Avg time", type="duration")
    blks_read_time = MetricDef(label="Read", type="duration")
    blks_write_time = MetricDef(label="Write", type="duration")
    shared_blks_read = MetricDef(label="Read", type="size")
    shared_blks_hit = MetricDef(label="Hit", type="size")
    shared_blks_dirtied = MetricDef(label="Dirtied", type="size")
    shared_blks_written = MetricDef(label="Written", type="size")
    temp_blks_read = MetricDef(label="Read", type="size")
    temp_blks_written = MetricDef(label="Written", type="size")
    wal_records = MetricDef(label="#Wal records", type="integer")
    wal_fpi = MetricDef(label="#Wal FPI", type="integer")
    wal_bytes = MetricDef(label="Wal bytes", type="size")

    @classmethod
    def _get_metrics(cls, handler, **params):
        base = cls.metrics.copy()

        if not handler.has_extension_version(handler.path_args[0],
                                             'pg_stat_statements', '1.8'):
            for key in ("plantime", "wal_records", "wal_fpi", "wal_bytes"):
                base.pop(key)
        return base

    # TODO: refactor with GlobalDatabasesMetricGroup
    @property
    def query(self):
        # Working from the statdata detailed_db base query
        inner_query = powa_getstatdata_detailed_db(bindparam("server"))
        inner_query = inner_query.alias()
        c = inner_query.c
        ps = powa_statements
        # Multiply each measure by the size of one block.
        columns = [c.srvid,
                   c.queryid,
                   ps.c.query,
                   sum(c.calls).label("calls"),
                   sum(c.runtime).label("runtime"),
                   sum(mulblock(c.shared_blks_read)).label("shared_blks_read"),
                   sum(mulblock(c.shared_blks_hit)).label("shared_blks_hit"),
                   sum(mulblock(c.shared_blks_dirtied)).label("shared_blks_dirtied"),
                   sum(mulblock(c.shared_blks_written)).label("shared_blks_written"),
                   sum(mulblock(c.temp_blks_read)).label("temp_blks_read"),
                   sum(mulblock(c.temp_blks_written)).label("temp_blks_written"),
                   (sum(c.runtime) / greatest(sum(c.calls), 1)).label("avg_runtime"),
                   sum(c.blk_read_time).label("blks_read_time"),
                   sum(c.blk_write_time).label("blks_write_time")
                   ]

        if self.has_extension_version(self.path_args[0], 'pg_stat_statements',
                                      '1.8'):
            columns.extend([
                            sum(c.plantime).label("plantime"),
                            sum(c.wal_records).label("wal_records"),
                            sum(c.wal_fpi).label("wal_fpi"),
                            sum(c.wal_bytes).label("wal_bytes")
                ])

        from_clause = inner_query.join(ps,
                                       (ps.c.srvid == c.srvid) &
                                       (ps.c.queryid == c.queryid) &
                                       (ps.c.userid == c.userid) &
                                       (ps.c.dbid == c.dbid))
        return (select(columns)
                .select_from(from_clause)
                .where(c.datname == bindparam("database"))
                .group_by(c.srvid, c.queryid, ps.c.query)
                .order_by(sum(c.runtime).desc()))

    def process(self, val, database=None, **kwargs):
        val = dict(val)
        val["url"] = self.reverse_url(
            "QueryOverview", val["srvid"], database, val["queryid"])
        return val


class ByQueryWaitSamplingMetricGroup(MetricGroupDef):
    """
    Metric group for indivual query wait events stats (displayed on the grid).
    """
    name = "all_queries_waits"
    xaxis = "query"
    axis_type = "category"
    data_url = r"/server/(\d+)/metrics/database_all_queries_waits/([^\/]+)/"
    counts = MetricDef(label="# of events", type="integer",
                       direction="descending")

    @property
    def query(self):
        # Working from the waitdata detailed_db base query
        inner_query = powa_getwaitdata_detailed_db(bindparam("server"))
        inner_query = inner_query.alias()
        c = inner_query.c
        ps = powa_statements

        columns = [c.srvid,
                   c.queryid,
                   ps.c.query,
                   c.event_type,
                   c.event,
                   sum(c.count).label("counts")]
        from_clause = inner_query.join(ps,
                                       (ps.c.srvid == c.srvid) &
                                       (ps.c.queryid == c.queryid) &
                                       (ps.c.dbid == c.dbid))
        return (select(columns)
                .select_from(from_clause)
                .where(c.datname == bindparam("database"))
                .group_by(c.srvid, c.queryid, ps.c.query, c.event_type, c.event)
                .order_by(sum(c.count).desc()))

    def process(self, val, database=None, **kwargs):
        val = dict(val)
        val["url"] = self.reverse_url(
            "QueryOverview", val["srvid"], database, val["queryid"])
        return val

class WizardThisDatabase(ContentWidget):

    title = 'Apply wizardry to this database'

    data_url = r"/server/(\d+)/database/([^\/]+)/wizardthisdatabase/"

    def get(self, database):
        self.render("database/wizardthisdatabase.html", database=database,
                    url=self.reverse_url("WizardPage", database))
        return


class DatabaseOverview(DashboardPage):
    """DatabaseOverview Dashboard."""
    base_url = r"/server/(\d+)/database/([^\/]+)/overview"
    datasources = [DatabaseOverviewMetricGroup, ByQueryMetricGroup,
                   ByQueryWaitSamplingMetricGroup, WizardMetricGroup,
                   DatabaseWaitOverviewMetricGroup, ConfigChangesDatabase,
                   DatabaseAllRelMetricGroup]
    params = ["server", "database"]
    parent = ServerOverview
    title = '%(database)s'
    timeline = ConfigChangesDatabase

    def dashboard(self):
        # This COULD be initialized in the constructor, but tornado < 3 doesn't
        # call it
        if getattr(self, '_dashboard', None) is not None:
            return self._dashboard

        pgss18 = self.has_extension_version(self.path_args[0],
                                            'pg_stat_statements', '1.8')

        self._dashboard = Dashboard("Database overview for %(database)s")

        db_metrics = [DatabaseOverviewMetricGroup.avg_runtime,
                      DatabaseOverviewMetricGroup.load,
                      DatabaseOverviewMetricGroup.calls]
        if pgss18:
            db_metrics.extend([DatabaseOverviewMetricGroup.planload])
        block_graph = Graph("Blocks (On database %(database)s)",
                            metrics=[DatabaseOverviewMetricGroup.
                                     total_blks_hit],
                            color_scheme=None)

        db_graphs = [Graph("Calls (On database %(database)s)",
                     metrics=db_metrics),
                     block_graph]

        graphs_dash = [Dashboard("General Overview", [db_graphs])]
        graphs = [TabContainer("All databases", graphs_dash)]

        if pgss18:
            # Add WALs graphs
            wals_graphs = [[Graph("WAL activity",
                            metrics=[DatabaseOverviewMetricGroup.wal_records,
                                     DatabaseOverviewMetricGroup.wal_fpi,
                                     DatabaseOverviewMetricGroup.wal_bytes]),
                            ]]
            graphs_dash.append(Dashboard("WALs", wals_graphs))

        # Add powa_stat_all_relations graphs
        all_rel_graphs = [Graph("Access pattern",
                          metrics=[DatabaseAllRelMetricGroup.seq_scan,
                                   DatabaseAllRelMetricGroup.idx_scan,
                                   DatabaseAllRelMetricGroup.idx_ratio]),
                          Graph("DML activity",
                          metrics=[DatabaseAllRelMetricGroup.n_tup_del,
                                   DatabaseAllRelMetricGroup.n_tup_hot_upd,
                                   DatabaseAllRelMetricGroup.n_tup_upd,
                                   DatabaseAllRelMetricGroup.n_tup_ins]),
                          Graph("Vacuum activity",
                          metrics=[DatabaseAllRelMetricGroup.autoanalyze_count,
                                   DatabaseAllRelMetricGroup.analyze_count,
                                   DatabaseAllRelMetricGroup.autovacuum_count,
                                   DatabaseAllRelMetricGroup.vacuum_count])]
        graphs_dash.append(Dashboard("Database Objects", [all_rel_graphs]))

        if self.has_extension(self.path_args[0], "pg_stat_kcache"):
            block_graph.metrics.insert(0, DatabaseOverviewMetricGroup.
                                       total_sys_hit)
            block_graph.metrics.insert(0, DatabaseOverviewMetricGroup.
                                       total_disk_read)
            block_graph.color_scheme = ['#cb513a', '#65b9ac', '#73c03a']

            sys_graphs = [Graph("System resources (events per sec)",
                                url=self.docs_stats_url + "pg_stat_kcache.html",
                                metrics=[DatabaseOverviewMetricGroup.majflts,
                                         DatabaseOverviewMetricGroup.minflts,
                                         # DatabaseOverviewMetricGroup.nswaps,
                                         # DatabaseOverviewMetricGroup.msgsnds,
                                         # DatabaseOverviewMetricGroup.msgrcvs,
                                         # DatabaseOverviewMetricGroup.nsignals,
                                         DatabaseOverviewMetricGroup.nvcsws,
                                         DatabaseOverviewMetricGroup.nivcsws])]

            graphs_dash.append(Dashboard("System resources", [sys_graphs]))
        else:
            block_graph.metrics.insert(0, DatabaseOverviewMetricGroup.
                                       total_blks_read)
            block_graph.color_scheme = ['#cb513a', '#73c03a']

        if (self.has_extension(self.path_args[0], "pg_wait_sampling")):
            metrics = None
            pg_version_num = self.get_pg_version_num(self.path_args[0])
            # if we can't connect to the remote server, assume pg10 or above
            if pg_version_num is None or pg_version_num < 100000:
                metrics = [DatabaseWaitOverviewMetricGroup.count_lwlocknamed,
                           DatabaseWaitOverviewMetricGroup.count_lwlocktranche,
                           DatabaseWaitOverviewMetricGroup.count_lock,
                           DatabaseWaitOverviewMetricGroup.count_bufferpin]
            else:
                metrics = [DatabaseWaitOverviewMetricGroup.count_lwlock,
                           DatabaseWaitOverviewMetricGroup.count_lock,
                           DatabaseWaitOverviewMetricGroup.count_bufferpin,
                           DatabaseWaitOverviewMetricGroup.count_activity,
                           DatabaseWaitOverviewMetricGroup.count_client,
                           DatabaseWaitOverviewMetricGroup.count_extension,
                           DatabaseWaitOverviewMetricGroup.count_ipc,
                           DatabaseWaitOverviewMetricGroup.count_timeout,
                           DatabaseWaitOverviewMetricGroup.count_io]

            graphs_dash.append(Dashboard("Wait Events",
                [[Graph("Wait Events (per second)",
                        url=self.docs_stats_url + "pg_wait_sampling.html",
                        metrics=metrics)]]))

        toprow = [{
                       'merge': True
                   }, {
                       'name': 'Execution',
                       'merge': False,
                       'colspan': 3
                   }, {
                       'name': 'I/O Time',
                       'merge': False,
                       'colspan': 2
                   }, {
                       'name': 'Blocks',
                       'merge': False,
                       'colspan': 4,
                   }, {
                       'name': 'Temp blocks',
                       'merge': False,
                       'colspan': 2
                   }]
        if pgss18:
            toprow.extend([{
                       'name': 'WALs',
                       'merge': False,
                       'colspan': 3
                       }])
        self._dashboard.widgets.extend(
            [graphs,
             [Grid("Details for all queries",
                   toprow=toprow,
                   columns=[{
                       "name": "query",
                       "label": "Query",
                       "type": "query",
                       "url_attr": "url",
                       "max_length": 70
                   }],
                   metrics=ByQueryMetricGroup.all(self))]])

        if self.has_extension(self.path_args[0], "pg_wait_sampling"):
            self._dashboard.widgets.extend([[
                Grid("Wait events for all queries",
                     url=self.docs_stats_url + "pg_wait_sampling.html",
                     columns=[{
                       "name": "query",
                       "label": "Query",
                       "type": "query",
                       "url_attr": "url",
                       "max_length": 70
                     }, {
                         "name": "event_type",
                         "label": "Event Type",
                     }, {
                         "name": "event",
                         "label": "Event",
                     }],
                     metrics=ByQueryWaitSamplingMetricGroup.all())]])

        self._dashboard.widgets.extend([[Wizard("Index suggestions")]])
        return self._dashboard
