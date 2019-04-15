"""
Dashboard for the by-query page.
"""

from tornado.web import HTTPError
from sqlalchemy.sql import (
    bindparam, text, column, select,
    case, cast, and_,
    func, extract)
from sqlalchemy.sql.functions import sum
from sqlalchemy.types import Numeric
from sqlalchemy.orm import outerjoin

from powa.dashboards import (
    Dashboard, TabContainer, Graph, Grid,
    MetricGroupDef, MetricDef,
    DashboardPage, ContentWidget)
from powa.database import DatabaseOverview

from powa.sql import (Plan, format_jumbled_query, resolve_quals,
                      qualstat_get_figures, get_hypoplans, get_any_sample_query,
                      possible_indexes)
from powa.sql.views import (powa_getstatdata_sample,
                            powa_getwaitdata_sample,
                            kcache_getstatdata_sample,
                            powa_getstatdata_detailed_db,
                            powa_getwaitdata_detailed_db,
                            qualstat_getstatdata)
from powa.sql.utils import (block_size, mulblock, greatest, least,
                            to_epoch, inner_cc)
from powa.sql.tables import powa_statements


class QueryOverviewMetricGroup(MetricGroupDef):
    """
    Metric Group for the graphs on the by query page.
    """
    name = "query_overview"
    xaxis = "ts"
    data_url = r"/server/(\d+)/metrics/database/([^\/]+)/query/(-?\d+)"
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
    hit_ratio = MetricDef(label="Shared buffers hit ratio", type="percent")
    miss_ratio = MetricDef(label="Shared buffers miss ratio", type="percent")

    reads = MetricDef(label="Physical read", type="sizerate")
    writes = MetricDef(label="Physical writes", type="sizerate")
    user_time = MetricDef(label="CPU user time / Query time", type="percent")
    system_time = MetricDef(label="CPU system time / Query time", type="percent")
    other_time = MetricDef(label="CPU other time / Query time", type="percent")
    sys_hit_ratio = MetricDef(label="System cache hit ratio", type="percent")
    disk_hit_ratio = MetricDef(label="Disk hit ratio", type="percent")
    minflts = MetricDef(label="Soft page faults", type="number")
    majflts = MetricDef(label="Hard page faults", type="number")
    nswaps = MetricDef(label="Swaps", type="number")
    msgsnds = MetricDef(label="IPC messages sent", type="number")
    msgrcvs = MetricDef(label="IPC messages received", type="number")
    nsignals = MetricDef(label="Signals received", type="number")
    nvcsws = MetricDef(label="Voluntary context switches", type="number")
    nivcsws = MetricDef(label="Involuntary context switches", type="number")

    @classmethod
    def _get_metrics(cls, handler, **params):
        base = cls.metrics.copy()
        if not handler.has_extension(params["server"], "pg_stat_kcache"):
            for key in ("reads", "writes", "user_time", "system_time",
                        "other_time", "sys_hit_ratio", "disk_hit_ratio",
                        "minflts", "majflts", "nswaps", "msgsnds", "msgrcvs",
                        "nsignals", "nvcsws", "nivcsws"):
                base.pop(key)
        else:
            base.pop("miss_ratio")

        return base

    @property
    def query(self):
        query = powa_getstatdata_sample("query", bindparam("server"))
        query = query.where(
            (column("datname") == bindparam("database")) &
            (column("queryid") == bindparam("query")))
        query = query.alias()
        c = query.c
        total_blocks = ((c.shared_blks_read + c.shared_blks_hit)
                        .label("total_blocks"))

        def bps(col):
            ts = extract("epoch", greatest(c.mesure_interval, '1 second'))
            return (mulblock(col) / ts).label(col.name)
        cols = [to_epoch(c.ts),
                c.rows,
                c.calls,
                case([(total_blocks == 0, 0)],
                     else_=cast(c.shared_blks_hit, Numeric) * 100 /
                     total_blocks).label("hit_ratio"),
                bps(c.shared_blks_read),
                bps(c.shared_blks_hit),
                bps(c.shared_blks_dirtied),
                bps(c.shared_blks_written),
                bps(c.local_blks_read),
                bps(c.local_blks_hit),
                bps(c.local_blks_dirtied),
                bps(c.local_blks_written),
                bps(c.temp_blks_read),
                bps(c.temp_blks_written),
                (c.blk_read_time /
                 extract("epoch", greatest(c.mesure_interval, '1 second'))
                 ).label("blk_read_time"),
                (c.blk_write_time /
                 extract("epoch", greatest(c.mesure_interval, '1 second'))
                 ).label("blk_write_time"),
                (c.runtime / greatest(c.calls, 1)).label("avg_runtime")]

        from_clause = query
        if self.has_extension(self.path_args[0], "pg_stat_kcache"):
            # Add system metrics from pg_stat_kcache,
            # and detailed hit ratio.
            kcache_query = kcache_getstatdata_sample("query")
            kc = inner_cc(kcache_query)
            kcache_query = (
                kcache_query
                .where(
                    (kc.srvid == bindparam("server")) &
                    (kc.datname == bindparam("database")) &
                    (kc.queryid == bindparam("query"))
                    )
                .alias())
            kc = kcache_query.c
            sys_hits = (greatest(mulblock(c.shared_blks_read) -
                                 kc.reads, 0)
                        .label("kcache_hitblocks"))
            sys_hitratio = (cast(sys_hits, Numeric) * 100 /
                            mulblock(total_blocks))
            disk_hit_ratio = (kc.reads * 100 /
                              mulblock(total_blocks))
            total_time = greatest(c.runtime, 1);
            # Rusage can return values > real time due to sampling bias
            # aligned to kernel ticks. As such, we have to clamp values to 100%
            total_time_percent = lambda x: least(100, (x * 100) /
                                                 total_time)

            def per_sec(col):
                ts = extract("epoch", greatest(c.mesure_interval, '1 second'))
                return (col / ts).label(col.name)
            cols.extend([
                per_sec(kc.reads),
                per_sec(kc.writes),
                per_sec(kc.minflts),
                per_sec(kc.majflts),
                per_sec(kc.nswaps),
                per_sec(kc.msgsnds),
                per_sec(kc.msgrcvs),
                per_sec(kc.nsignals),
                per_sec(kc.nvcsws),
                per_sec(kc.nivcsws),
                total_time_percent(kc.user_time * 1000).label("user_time"),
                total_time_percent(kc.system_time * 1000).label("system_time"),
                greatest(total_time_percent(
                    c.runtime - ((kc.user_time + kc.system_time) *
                    1000)), 0).label("other_time"),
                case([(total_blocks == 0, 0)],
                     else_=disk_hit_ratio).label("disk_hit_ratio"),
                case([(total_blocks == 0, 0)],
                     else_=sys_hitratio).label("sys_hit_ratio")])
            from_clause = from_clause.join(
                kcache_query,
                kcache_query.c.ts == c.ts)
        else:
            cols.extend([
                case([(total_blocks == 0, 0)],
                     else_=cast(c.shared_blks_read, Numeric) * 100 /
                     total_blocks).label("miss_ratio")
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

    data_url = r"/server/(\d+)/metrics/database/([^\/]+)/query/(-?\d+)/indexes"
    title = "Query Indexes"

    def get(self, srvid, database, query):
        if not self.has_extension(srvid, "pg_qualstats"):
            raise HTTPError(501, "PG qualstats is not installed")
        base_query = qualstat_getstatdata(srvid)
        c = inner_cc(base_query)
        base_query.append_from(text("""LATERAL unnest(quals) as qual"""))
        base_query = (base_query
                      .where(c.queryid == query)
                      .having(func.bool_or(column('eval_type') == 'f'))
                      .having(c.execution_count > 1000)
                      .having(c.occurences > 0)
                      .having(c.filter_ratio > 0.5)
                      .params(**{'from': '-infinity',
                                 'to': 'infinity'}))
        optimizable = list(self.execute(base_query, params={'server': srvid,
                                                            'query': query}))
        optimizable = resolve_quals(self.connect(srvid, database=database),
                                    optimizable,
                                    'quals')
        hypoplan = None
        indexes = {}
        for qual in optimizable:
            indexes[qual.where_clause] = possible_indexes(qual)
        hypo_version = self.has_extension(srvid, "hypopg", database=database)
        if indexes and hypo_version and hypo_version >= "0.0.3":
            # identify indexes
            # create them
            allindexes = [ind for indcollection in indexes.values()
                          for ind in indcollection]
            for ind in allindexes:
                ddl = ind.hypo_ddl
                if ddl is not None:
                    ind.name = self.execute(ddl, srvid=srvid,
                                            database=database).scalar()
            # Build the query and fetch the plans
            querystr = get_any_sample_query(self, srvid, database, query,
                                            self.get_argument("from"),
                                            self.get_argument("to"))
            try:
                hypoplan = get_hypoplans(self.connect(srvid,
                                                      database=database),
                                         querystr, allindexes)
            except Exception:
                # TODO: offer the possibility to fill in parameters from the UI
                self.flash("We couldn't get plans for this query, presumably "
                           "because some parameters are missing ")

        self.render("database/query/indexes.html", indexes=indexes,
                    hypoplan=hypoplan)


class QueryExplains(ContentWidget):
    """
    Content widget showing explain plans for various const values.
    """
    title = "Query Explains"
    data_url = r"/server/(\d+)/metrics/database/([^\/]+)/query/(-?\d+)/explains"

    def get(self, server, database, query):
        if not self.has_extension(server, "pg_qualstats"):
            raise HTTPError(501, "PG qualstats is not installed")

        plans = []
        row = qualstat_get_figures(self, server, database,
                                   self.get_argument("from"),
                                   self.get_argument("to"),
                                   queries=[query])
        if row is not None:
            for key in ('most filtering', 'least filtering', 'most executed', 'most used'):
                vals = row[key]
                query = format_jumbled_query(row['query'], vals['constants'])
                plan = "N/A"
                try:
                    sqlQuery = text("EXPLAIN %s" % query)
                    result = self.execute(sqlQuery,
                                          srvid=server,
                                          database=database)
                    plan = "\n".join(v[0] for v in result)
                except:
                    pass
                plans.append(Plan(key, vals['constants'], query,
                                  plan, vals["filter_ratio"],
                                  vals['execution_count'],
                                  vals['occurences']))
        if len(plans) == 0:
            self.flash("No quals found for this query", "warning")
            self.render("xhr.html", content="")
            return

        self.render("database/query/explains.html", plans=plans)


class WaitsQueryOverviewMetricGroup(MetricGroupDef):
    """
    Metric Group for the wait event graph on the by query page.
    """
    name = "waits_query_overview"
    xaxis = "ts"
    data_url = r"/server/(\d+)/metrics/database/([^\/]+)/query/(-?\d+)/wait_events_sampled"
    # pg 9.6 only metrics
    count_lwlocknamed = MetricDef(label="Lightweight Named")
    count_lwlocktranche = MetricDef(label="Lightweight Tranche")
    # pg 10+ metrics
    count_lwlock = MetricDef(label="Lightweight Lock")
    count_lock = MetricDef(label="Lock")
    count_bufferpin = MetricDef(label="Buffer pin")
    count_activity = MetricDef(label="Activity")
    count_client = MetricDef(label="Client")
    count_extension = MetricDef(label="Extension")
    count_ipc = MetricDef(label="IPC")
    count_timeout = MetricDef(label="Timeout")
    count_io = MetricDef(label="IO")

    def prepare(self):
        if not self.has_extension(self.path_args[0], "pg_wait_sampling"):
            raise HTTPError(501, "pg_wait_sampling is not installed")

    @property
    def query(self):

        query = powa_getwaitdata_sample(bindparam("server"), "query")
        query = query.where(
            (column("datname") == bindparam("database")) &
            (column("queryid") == bindparam("query")))
        query = query.alias()
        c = query.c

        def wps(col):
            ts = extract("epoch", greatest(c.mesure_interval, '1 second'))
            return (col / ts).label(col.name)

        cols = [to_epoch(c.ts)]

        pg_version_num = self.get_pg_version_num(self.path_args[0])
        if pg_version_num < 100000:
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

class WaitSamplingList(MetricGroupDef):
    """
    Datasource used for the wait events grid.
    """
    name = "query_wait_events"
    xaxis = "event"
    axis_type = "category"
    data_url = r"/server/(\d+)/metrics/database/([^\/]+)/query/(-?\d+)/wait_events"
    counts = MetricDef(label="# of events", type="number",
                       direction="descending")

    def prepare(self):
        if not self.has_extension(self.path_args[0], "pg_wait_sampling"):
            raise HTTPError(501, "pg_wait_sampling is not installed")

    @property
    def query(self):
        # Working from the waitdata detailed_db base query
        inner_query = powa_getwaitdata_detailed_db(bindparam("server"))
        inner_query = inner_query.alias()
        c = inner_query.c
        ps = powa_statements

        columns = [c.queryid,
                   ps.c.query,
                   c.event_type,
                   c.event,
                   sum(c.count).label("counts")]
        from_clause = inner_query.join(ps,
                                       (ps.c.queryid == c.queryid) &
                                       (ps.c.dbid == c.dbid))
        return (select(columns)
                .select_from(from_clause)
                .where((c.datname == bindparam("database")) &
                       (c.queryid == bindparam("query")))
                .group_by(c.queryid, ps.c.query, c.event_type, c.event)
                .order_by(sum(c.count).desc()))


class QualList(MetricGroupDef):
    """
    Datasource used for the Qual table.
    """
    name = "query_quals"
    xaxis = "relname"
    axis_type = "category"
    data_url = r"/server/(\d+)/metrics/database/([^\/]+)/query/(-?\d+)/quals"
    filter_ratio = MetricDef(label="Avg filter_ratio (excluding index)", type="percent")
    execution_count = MetricDef(label="Execution count (excluding index)")

    def prepare(self):
        if not self.has_extension(self.path_args[0], "pg_qualstats"):
            raise HTTPError(501, "PG qualstats is not installed")

    @property
    def query(self):
        base = qualstat_getstatdata(bindparam("server"))
        c = inner_cc(base)
        return (base.where(c.queryid == bindparam("query")))

    def post_process(self, data, server, database, query, **kwargs):
        conn = self.connect(server, database=database)
        data["data"] = resolve_quals(conn, data["data"])
        for qual in data["data"]:
            qual.url = self.reverse_url('QualOverview', server, database, query,
                                        qual.qualid)
        return data


class QueryDetail(ContentWidget):
    """
    Detail widget showing summarized information for the query.
    """
    title = "Query Detail"
    data_url = r"/server/(\d+)/metrics/database/([^\/]+)/query/(-?\d+)/detail"

    def get(self, srvid, database, query):
        bs = block_size.c.block_size
        stmt = powa_getstatdata_detailed_db(srvid)
        stmt = stmt.where(
            (column("datname") == bindparam("database")) &
            (column("queryid") == bindparam("query")))
        stmt = stmt.alias()
        from_clause = outerjoin(powa_statements, stmt,
                                and_(powa_statements.c.queryid ==
                                     stmt.c.queryid, powa_statements.c.dbid ==
                                     stmt.c.dbid))
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
            .select_from(from_clause)
            .where(powa_statements.c.queryid == bindparam("query"))
            .group_by(column("query"), bs))

        value = self.execute(stmt, params={
            "server": srvid,
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
    base_url = r"/server/(\d+)/database/([^\/]+)/query/(-?\d+)/overview"
    params = ["server", "database", "query"]
    datasources = [QueryOverviewMetricGroup, WaitsQueryOverviewMetricGroup,
                   QueryDetail, QueryExplains, QueryIndexes, WaitSamplingList,
                   QualList]
    parent = DatabaseOverview
    title = 'Query Overview'

    def dashboard(self):
        # This COULD be initialized in the constructor, but tornado < 3 doesn't
        # call it
        if getattr(self, '_dashboard', None) is not None:
            return self._dashboard

        hit_ratio_graph = Graph("Hit ratio",
                                metrics=[QueryOverviewMetricGroup.hit_ratio],
                                renderer="bar",
                                stack=True,
                                color_scheme=['#73c03a','#65b9ac','#cb513a'])
        dashes = []
        dashes.append(Dashboard("Query detail",
            [[Graph("General",
                    metrics=[QueryOverviewMetricGroup.avg_runtime,
                             QueryOverviewMetricGroup.rows,
                             QueryOverviewMetricGroup.calls ])]]))
        dashes.append(Dashboard(
            "PG Cache",
            [[Graph("Shared block (in Bps)",
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
                             QueryOverviewMetricGroup.temp_blks_written])]]))
        iodash = Dashboard("IO",
            [[hit_ratio_graph,
              Graph("Read / Write time",
                    url="https://powa.readthedocs.io/en/latest/stats_extensions/pg_stat_kcache.html",
                    metrics=[QueryOverviewMetricGroup.blk_read_time,
                             QueryOverviewMetricGroup.blk_write_time])]])
        dashes.append(iodash)

        if self.has_extension(self.path_args[0], "pg_stat_kcache"):
            iodash.widgets.extend([[
                Graph("Physical block (in Bps)",
                      url="https://powa.readthedocs.io/en/latest/stats_extensions/pg_stat_kcache.html",
                      metrics=[QueryOverviewMetricGroup.reads,
                               QueryOverviewMetricGroup.writes]),
                Graph("CPU Time repartition",
                      url="https://powa.readthedocs.io/en/latest/stats_extensions/pg_stat_kcache.html",
                      metrics=[QueryOverviewMetricGroup.user_time,
                               QueryOverviewMetricGroup.system_time,
                               QueryOverviewMetricGroup.other_time],
                      renderer="bar",
                      stack=True,
                      color_scheme=['#73c03a','#cb513a','#65b9ac'])]])
            hit_ratio_graph.metrics.append(
                QueryOverviewMetricGroup.sys_hit_ratio)
            hit_ratio_graph.metrics.append(
                QueryOverviewMetricGroup.disk_hit_ratio)

            sys_graphs = [Graph("System resources (events per sec)",
                                url="https://powa.readthedocs.io/en/latest/stats_extensions/pg_stat_kcache.html",
                                metrics=[QueryOverviewMetricGroup.majflts,
                                         QueryOverviewMetricGroup.minflts,
                                         QueryOverviewMetricGroup.nswaps,
                                         QueryOverviewMetricGroup.msgsnds,
                                         QueryOverviewMetricGroup.msgrcvs,
                                         QueryOverviewMetricGroup.nsignals,
                                         QueryOverviewMetricGroup.nvcsws,
                                         QueryOverviewMetricGroup.nivcsws])]
            dashes.append(Dashboard("System resources", [sys_graphs]))
        else:
            hit_ratio_graph.metrics.append(
                QueryOverviewMetricGroup.miss_ratio)

        if self.has_extension(self.path_args[0], "pg_wait_sampling"):
            # Get the metrics depending on the pg server version
            metrics=None
            if self.get_pg_version_num(self.path_args[0]) < 100000:
                metrics=[WaitsQueryOverviewMetricGroup.count_lwlocknamed,
                         WaitsQueryOverviewMetricGroup.count_lwlocktranche,
                         WaitsQueryOverviewMetricGroup.count_lock,
                         WaitsQueryOverviewMetricGroup.count_bufferpin]
            else:
                metrics=[WaitsQueryOverviewMetricGroup.count_lwlock,
                         WaitsQueryOverviewMetricGroup.count_lock,
                         WaitsQueryOverviewMetricGroup.count_bufferpin,
                         WaitsQueryOverviewMetricGroup.count_activity,
                         WaitsQueryOverviewMetricGroup.count_client,
                         WaitsQueryOverviewMetricGroup.count_extension,
                         WaitsQueryOverviewMetricGroup.count_ipc,
                         WaitsQueryOverviewMetricGroup.count_timeout,
                         WaitsQueryOverviewMetricGroup.count_io]
            dashes.append(Dashboard("Wait Events",
                [[Graph("Wait Events (per second)",
                        url="https://powa.readthedocs.io/en/latest/stats_extensions/pg_wait_sampling.html",
                        metrics=metrics),
                  Grid("Wait events summary",
                        url="https://powa.readthedocs.io/en/latest/stats_extensions/pg_wait_sampling.html",
                       columns=[{
                           "name": "event_type",
                           "label": "Event Type",
                       }, {
                           "name": "event",
                           "label": "Event",
                       }],
                       metrics=WaitSamplingList.all())]]))

        if self.has_extension(self.path_args[0], "pg_qualstats"):
            dashes.append(Dashboard("Predicates",
                [[
                Grid("Predicates used by this query",
                     columns=[{
                         "name": "where_clause",
                         "label": "Predicate",
                         "type": "query",
                         "max_length": 60,
                         "url_attr": "url"
                     }],
                     metrics=QualList.all())],
                [QueryIndexes],
                [QueryExplains]]))
        self._dashboard = Dashboard("Query %(query)s on database %(database)s",
                                    [[QueryDetail], [
                                        TabContainer("Query %(query)s on database %(database)s",
                                                     dashes)]])
        return self._dashboard
