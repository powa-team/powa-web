from __future__ import absolute_import
from powa.framework import AuthHandler
from powa.dashboards import (
    Dashboard, DashboardPage, ContentWidget,
    Widget, MetricGroupDef, MetricDef)

from powa.database import DatabaseOverview
from powa.sql import (resolve_quals, possible_indexes, get_sample_query,
                      format_jumbled_query, get_hypoplans)
import json
from powa.sql.compat import JSONB, JSON
from powa.sql.views import qualstat_getstatdata, TEXTUAL_INDEX_QUERY
from powa.sql.utils import inner_cc
from powa.sql.tables import pg_database, powa_statements
from sqlalchemy.sql import (bindparam, literal, literal_column, join, select,
                            alias, text, func, column, cast)


class IndexSuggestionHandler(AuthHandler):

    def post(self, database):
        qual_to_resolve = json.loads(self.request.body.decode("utf8"))
        qual_id = qual_to_resolve['qual']['id']
        from_date = qual_to_resolve['from_date']
        to_date = qual_to_resolve['to_date']
        attnum_order = qual_to_resolve['attnums']
        base_query = qualstat_getstatdata()
        c = inner_cc(base_query)
        base_query.append_from(text("""LATERAL unnest(quals) as qual"""))
        base_query = (base_query
                      .where(c.qualid == qual_id)
                      .params(**{'from': from_date,
                                 'to': to_date}))
        optimizable = list(self.execute(base_query))
        optimizable = resolve_quals(self.connect(database=database),
                                    optimizable,
                                    'quals')
        indexes = possible_indexes(optimizable[0], order=attnum_order)
        # Get every query associated with it.
        powa_conn = self.connect(database="powa")
        conn = self.connect(database=database)
        queries = list(powa_conn.execute(text("""
            SELECT DISTINCT query, ps.queryid
            FROM powa_statements ps
            JOIN powa_qualstats_quals q ON q.queryid = ps.queryid
            WHERE q.qualid = :qualid
        """), qualid=qual_id))
        # Create all possible indexes for this qual
        not_tested = []
        plans = {}
        hypo_version = self.has_extension("hypopg", database=database)
        hypoplans = {}
        if hypo_version and hypo_version >= "0.0.3":
            # identify indexes
            # create them
            hypo_index_names = []
            for ind in indexes:
                ddl = ind.hypo_ddl
                if ddl is not None:
                    ind.name = self.execute(ddl, database=database).scalar()[1]
            # Build the query and fetch the plans
            for query in queries:
                querystr = get_sample_query(self, database, query.queryid,
                                            from_date,
                                            to_date)
                if querystr:
                    hypoplans[query.queryid] = get_hypoplans(
                        self.connect(database=database), querystr,
                        indexes)
            # To value of a link is the the reduction in cost
        self.render_json(hypoplans)



class WizardMetricGroup(MetricGroupDef):
    """Metric group for the wizard."""
    name = "wizard"
    xaxis = "quals"
    axis_type = "category"
    data_url = r"/metrics/database/(\w+)/wizard/"

    @property
    def query(self):
        pq = qualstat_getstatdata(column("eval_type") == "f")
        c = inner_cc(pq)
        base = alias(pq)
        query = (select([
            func.array_agg(column("queryid")).label("queryids"),
            "qualid",
            cast(column("quals"), JSONB).label('quals'),
            "count",
            func.array_agg(column("query")).label("queries"),
            "avg_filter",
            "filter_ratio"
        ]).select_from(
            join(base, pg_database,
                 onclause=(
                     pg_database.c.oid == literal_column("dbid"))))
            .where(pg_database.c.datname == bindparam("database"))
            .where(column("avg_filter") > 1000)
            .where(column("filter_ratio") > 0.3)
            .group_by(column("qualid"), column("count"), cast(column("quals"), JSONB),
                     column("avg_filter"), column("filter_ratio"))
            .order_by(column("count").desc())
            .limit(200))
        return query

    def post_process(self, data, database, **kwargs):
        conn = self.connect(database=database)
        data["data"] = resolve_quals(conn, data["data"])
        return data


class Wizard(Widget):

    def __init__(self, title):
        self.title = title

    def to_json(self):
        values = self.__dict__.copy()
        values['metrics'] = []
        values['type'] = 'wizard'
        values['datasource'] = 'wizard'
        return values

class NoWizard(ContentWidget):

    title = 'Can not apply wizardry'

    data_url = r"/database/(\w+)/nowizard/"

    #def __init__(self, title):
    #    self.title = title

    def get(self, database):
        self.render("database/nowizard.html", database = database)
        #self.render("xhr.html", content="nodata")
        return
    #def to_json(self):
    #    return ()

class WizardPage(DashboardPage):

    base_url = r"/database/(\w+)/wizard/"

    params = ["database"]

    parent = DatabaseOverview

    datasources = [WizardMetricGroup, NoWizard]

    @classmethod
    def get_menutitle(cls, handler, params):
        return "Wizard index suggestion"

    @property
    def dashboard(self):
        # This COULD be initialized in the constructor, but tornado < 3 doesn't
        # call it
        if getattr(self, '_dashboard', None) is not None:
            return self._dashboard

        self._dashboard = Dashboard("Optimizer for %(database)s")

        hypo_version = self.has_extension("hypopg", database = self.database)
        if hypo_version and hypo_version >= "0.0.3":
            self._dashboard.widgets.extend(
                [[Wizard("Apply wizardry index suggestion to database \"%(database)s\"")]])
        else:
            self._dashboard.widgets.extend(
                [[NoWizard]])

        return self._dashboard
