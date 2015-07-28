from __future__ import unicode_literals
from powa.framework import AuthHandler
from powa.dashboards import (
    Dashboard, DashboardPage,
    Widget, MetricGroupDef, MetricDef)

from powa.database import DatabaseOverview
from powa.sql import (resolve_quals, possible_indexes, get_sample_query,
                      format_jumbled_query, get_hypoplans)
import json
from powa.sql.views import qualstat_getstatdata, TEXTUAL_INDEX_QUERY
from powa.sql.utils import inner_cc
from powa.sql.tables import pg_database, powa_statements
from sqlalchemy.sql import (bindparam, literal, literal_column, join, select,
                            alias, text, func)


class IndexSuggestionHandler(AuthHandler):

    def post(self, database):
        qual_to_resolve = json.loads(self.request.body.decode("utf8"))
        qual_id = qual_to_resolve['qual']['id']
        from_date = qual_to_resolve['from_date']
        to_date = qual_to_resolve['to_date']
        base_query = qualstat_getstatdata()
        c = inner_cc(base_query)
        base_query.append_from(text("""LATERAL unnest(quals) as qual"""))
        base_query = (base_query
                      .where(c.qualid == qual_id)
                      .params(**{'from': '-infinity',
                                 'to': 'infinity'}))
        optimizable = list(self.execute(base_query))
        optimizable = resolve_quals(self.connect(database=database),
                                    optimizable,
                                    'quals')
        indexes = possible_indexes(optimizable[0])
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
        pq = qualstat_getstatdata()
        c = inner_cc(pq)
        base = alias(pq)
        query = (select([
            "queryid",
            "qualid",
            "quals",
            "count",
            "query",
            "nbfiltered",
            "filter_ratio"
        ]).select_from(
            join(base, pg_database,
                 onclause=(
                     pg_database.c.oid == literal_column("dbid"))))
            .where(pg_database.c.datname == bindparam("database"))
            .order_by(c.count.desc())
            .limit(20))
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


class WizardPage(DashboardPage):

    base_url = r"/database/(\w+)/wizard/"

    params = ["database"]

    parent = DatabaseOverview

    datasources = [WizardMetricGroup]

    dashboard = Dashboard(
        "Optimizer for %(database)s",
        [[Wizard("Apply wizardry to database '%(database)s'")]])
