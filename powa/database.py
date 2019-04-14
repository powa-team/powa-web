"""
Module containing the by-database dashboard.
"""
from powa.framework import AuthHandler
from powa.dashboards import (
    Dashboard, Graph, Grid, ContentWidget,
    MetricGroupDef, MetricDef,
    DashboardPage, TabContainer)

from powa.sql.views import (powa_getstatdata_detailed_db,
                            powa_getwaitdata_detailed_db,
                            powa_getstatdata_sample,
                            kcache_getstatdata_sample)
from powa.wizard import WizardMetricGroup, Wizard
from powa.server import ServerOverview
from sqlalchemy.sql import bindparam, column, select, extract
from sqlalchemy.sql.functions import sum
from powa.sql.utils import (greatest, block_size, mulblock,
                            total_read, total_hit, to_epoch,
                            inner_cc)
from powa.sql.tables import powa_statements


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
    avg_runtime = MetricDef(label="Avg runtime", type="duration")
    load = MetricDef(label="Runtime per sec", type="duration")
    total_blks_hit = MetricDef(label="Total shared buffers hit", type="sizerate")
    total_blks_read = MetricDef(label="Total shared buffers miss", type="sizerate")

    total_sys_hit = MetricDef(label="Total system cache hit", type="sizerate")
    total_disk_read = MetricDef(label="Total disk read", type="sizerate")
    minflts = MetricDef(label="Soft page faults", type="integer")
    majflts = MetricDef(label="Hard page faults", type="integer")
    nswaps = MetricDef(label="Swaps", type="integer")
    msgsnds = MetricDef(label="IPC messages sent", type="integer")
    msgrcvs = MetricDef(label="IPC messages received", type="integer")
    nsignals = MetricDef(label="Signals received", type="integer")
    nvcsws = MetricDef(label="Voluntary context switches", type="integer")
    nivcsws = MetricDef(label="Involuntary context switches", type="integer")

    @classmethod
    def _get_metrics(cls, handler, **params):
        base = cls.metrics.copy()
        if not handler.has_extension(params["server"], "pg_stat_kcache"):
            for key in ("total_sys_hit", "total_disk_read", "minflts",
                        "majflts", "nswaps", "msgsnds", "msgrcvs", "nsignals",
                        "nvcsws", "nivcsws"):
                base.pop(key)
        else:
            base.pop("total_blks_read")

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
                (sum(c.runtime) / greatest(sum(c.calls),
                                           1.)).label("avg_runtime"),
                (sum(c.runtime) / greatest(extract("epoch", c.mesure_interval),
                                           1)).label("load"),
                total_read(c),
                total_hit(c)]

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
            total_sys_hit = (total_read(c) - sum(kc.reads) /
                             greatest(sum(c.calls), 1.)).label("total_sys_hit")
            total_disk_read = (sum(kc.reads) / greatest(sum(c.calls), 1.)
                               ).label("total_disk_read")
            minflts = (sum(kc.minflts) / greatest(sum(c.calls), 1.)
                       ).label("minflts")
            majflts = (sum(kc.majflts) / greatest(sum(c.calls), 1.)
                       ).label("majflts")
            nswaps = (sum(kc.nswaps) / greatest(sum(c.calls), 1.)
                      ).label("nswaps")
            msgsnds = (sum(kc.msgsnds) / greatest(sum(c.calls), 1.)
                       ).label("msgsnds")
            msgrcvs = (sum(kc.msgrcvs) / greatest(sum(c.calls), 1.)
                       ).label("msgrcvs")
            nsignals = (sum(kc.nsignals) / greatest(sum(c.calls), 1.)
                        ).label("nsignals")
            nvcsws = (sum(kc.nvcsws) / greatest(sum(c.calls), 1.)
                      ).label("nvcsws")
            nivcsws = (sum(kc.nivcsws) / greatest(sum(c.calls), 1.)
                       ).label("nivcsws")

            cols.extend([total_sys_hit, total_disk_read, minflts, majflts,
                         nswaps, msgsnds, msgrcvs, nsignals, nvcsws, nivcsws])
            from_clause = from_clause.join(
                kcache_query,
                kcache_query.c.ts == c.ts)

        return (select(cols)
                .select_from(from_clause)
                .where(c.calls is not None)
                .group_by(c.srvid, c.ts, bs, c.mesure_interval)
                .order_by(c.ts)
                .params(samples=100))


class ByQueryMetricGroup(MetricGroupDef):
    """Metric group for indivual query stats (displayed on the grid)."""
    name = "all_queries"
    xaxis = "queryid"
    axis_type = "category"
    data_url = r"/server/(\d+)/metrics/database_all_queries/([^\/]+)/"
    calls = MetricDef(label="#", type="integer")
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
                   sum(c.blk_write_time).label("blks_write_time")]
        from_clause = inner_query.join(ps,
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
    counts = MetricDef(label="# of events", type="integer", direction="descending")

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
                   ByQueryWaitSamplingMetricGroup, WizardMetricGroup]
    params = ["server", "database"]
    parent = ServerOverview
    title = '%(database)s'

    def dashboard(self):
        # This COULD be initialized in the constructor, but tornado < 3 doesn't
        # call it
        if getattr(self, '_dashboard', None) is not None:
            return self._dashboard

        self._dashboard = Dashboard("Database overview for %(database)s")

        block_graph = Graph("Blocks (On database %(database)s)",
                            metrics=[DatabaseOverviewMetricGroup.
                                     total_blks_hit],
                            color_scheme=None)

        graphs = [Graph("Calls (On database %(database)s)",
                    metrics=[DatabaseOverviewMetricGroup.avg_runtime,
                             DatabaseOverviewMetricGroup.load]),
              block_graph]

        if self.has_extension(self.path_args[0], "pg_stat_kcache"):
            block_graph.metrics.insert(0, DatabaseOverviewMetricGroup.
                                       total_sys_hit)
            block_graph.metrics.insert(0, DatabaseOverviewMetricGroup.
                                       total_disk_read)
            block_graph.color_scheme = ['#cb513a', '#65b9ac', '#73c03a']

            sys_graphs = [Graph("System resources",
                                metrics=[DatabaseOverviewMetricGroup.majflts,
                                         DatabaseOverviewMetricGroup.minflts,
                                         DatabaseOverviewMetricGroup.nswaps,
                                         DatabaseOverviewMetricGroup.msgsnds,
                                         DatabaseOverviewMetricGroup.msgrcvs,
                                         DatabaseOverviewMetricGroup.nsignals,
                                         DatabaseOverviewMetricGroup.nvcsws,
                                         DatabaseOverviewMetricGroup.nivcsws])]

            graphs_dash = []
            graphs_dash.append(Dashboard("General Overview", [graphs]))
            graphs_dash.append(Dashboard("System resources", [sys_graphs]))
            graphs = [TabContainer("All databases", graphs_dash)]
        else:
            block_graph.metrics.insert(0, DatabaseOverviewMetricGroup.
                                       total_blks_read)
            block_graph.color_scheme = ['#cb513a', '#73c03a']

        self._dashboard.widgets.extend(
            [graphs,
             [Grid("Details for all queries",
                   toprow=[{
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
                   }],
                   columns=[{
                       "name": "query",
                       "label": "Query",
                       "type": "query",
                       "url_attr": "url",
                       "max_length": 70
                   }],
                   metrics=ByQueryMetricGroup.all())]])

        if self.has_extension(self.path_args[0], "pg_wait_sampling"):
            self._dashboard.widgets.extend([[
                Grid("Wait events for all queries",
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
