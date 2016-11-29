"""
Module containing the by-database dashboard.
"""
from powa.framework import AuthHandler
from powa.dashboards import (
    Dashboard, Graph, Grid, ContentWidget,
    MetricGroupDef, MetricDef,
    DashboardPage)

from powa.sql.views import (powa_getstatdata_detailed_db,
                            powa_getstatdata_sample)
from powa.wizard import WizardMetricGroup, Wizard
from powa.overview import Overview
from sqlalchemy.sql import bindparam, column, select, extract
from sqlalchemy.sql.functions import sum
from powa.sql.utils import (greatest, block_size, mulblock,
                            total_read, total_hit, to_epoch)
from powa.sql.tables import powa_statements


class DatabaseSelector(AuthHandler):
    """Page allowing to choose a database."""

    def get(self):
        self.redirect(self.reverse_url(
            'DatabaseOverview',
            self.get_argument("database")))


class DatabaseOverviewMetricGroup(MetricGroupDef):
    """Metric group for the database global graphs."""
    name = "database_overview"
    xaxis = "ts"
    data_url = r"/metrics/database_overview/([^\/]+)/"
    avg_runtime = MetricDef(label="Avg runtime", type="duration")
    load = MetricDef(label="Runtime per sec", type="duration")
    total_blks_hit = MetricDef(label="Total hit", type="sizerate")
    total_blks_read = MetricDef(label="Total read", type="sizerate")

    @property
    def query(self):
        # Fetch the base query for sample, and filter them on the database
        bs = block_size.c.block_size
        subquery = powa_getstatdata_sample("db")
        # Put the where clause inside the subquery
        subquery = subquery.where(column("datname") == bindparam("database"))
        query = subquery.alias()
        c = query.c
        return (select([
            to_epoch(c.ts),
            (sum(c.runtime) / greatest(sum(c.calls), 1.)).label("avg_runtime"),
            (sum(c.runtime) / greatest(extract("epoch", c.mesure_interval),
                                       1)).label("load"),
            total_read(c),
            total_hit(c)])
                .where(c.calls != None)
                .group_by(c.ts, bs, c.mesure_interval)
                .order_by(c.ts)
                .params(samples=100))



class ByQueryMetricGroup(MetricGroupDef):
    """Metric group for indivual query stats (displayed on the grid)."""
    name = "all_queries"
    xaxis = "queryid"
    axis_type = "category"
    data_url = r"/metrics/database_all_queries/([^\/]+)/"
    calls = MetricDef(label="#", type="string")
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
        inner_query = powa_getstatdata_detailed_db()
        inner_query = inner_query.alias()
        c = inner_query.c
        ps = powa_statements
        # Multiply each measure by the size of one block.
        columns = [c.queryid,
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
                .group_by(c.queryid, ps.c.query)
                .order_by(sum(c.runtime).desc()))


    def process(self, val, database=None, **kwargs):
        val = dict(val)
        val["url"] = self.reverse_url(
            "QueryOverview", database, val["queryid"])
        return val

class WizardThisDatabase(ContentWidget):

    title = 'Apply wizardry to this database'

    data_url = r"/database/([^\/]+)/wizardthisdatabase/"

    def get(self, database):
        self.render("database/wizardthisdatabase.html", database=database,
                    url=self.reverse_url("WizardPage", database))
        return


class DatabaseOverview(DashboardPage):
    """DatabaseOverview Dashboard."""
    base_url = r"/database/([^\/]+)/overview"
    datasources = [DatabaseOverviewMetricGroup, ByQueryMetricGroup,
                   WizardMetricGroup]
    params = ["database"]
    parent = Overview

    @property
    def dashboard(self):
        # This COULD be initialized in the constructor, but tornado < 3 doesn't
        # call it
        if getattr(self, '_dashboard', None) is not None:
            return self._dashboard

        self._dashboard = Dashboard("Database overview for %(database)s")


        self._dashboard.widgets.extend(
            [[Graph("Calls (On database %(database)s)",
                    metrics=[DatabaseOverviewMetricGroup.avg_runtime,
                             DatabaseOverviewMetricGroup.load]),
              Graph("Blocks (On database %(database)s)",
                    metrics=[DatabaseOverviewMetricGroup.total_blks_read,
                             DatabaseOverviewMetricGroup.total_blks_hit])],
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

        self._dashboard.widgets.extend([[Wizard("Index suggestions")]])
        return self._dashboard

    @classmethod
    def get_menutitle(cls, handler, params):
        return params.get("database")
