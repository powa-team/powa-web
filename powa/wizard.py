from __future__ import unicode_literals
from powa.framework import AuthHandler
from powa.dashboards import (
    Dashboard, DashboardPage,
    Widget, MetricGroupDef, MetricDef)

from powa.database import DatabaseOverview
from powa.sql import resolve_quals
import json
from powa.sql.views import qualstat_getstatdata, possible_indexes, TEXTUAL_INDEX_QUERY
from powa.sql.utils import inner_cc
from powa.sql.tables import pg_database, powa_statements
from sqlalchemy.sql import bindparam, literal, literal_column, join, select, alias, text


class IndexSuggestionHandler(AuthHandler):

    def post(self, database):
        qual_to_resolve = json.loads(self.request.body.decode("utf8"))
        base = qual_to_resolve['qual']
        indexes = possible_indexes(base["quals"])
        # Get every query associated with it.
        powa_conn = self.connect(database="powa")
        conn = self.connect(database=database)
        queries = list(powa_conn.execute(text("""
            SELECT query, ps.queryid
            FROM powa_statements ps
            JOIN powa_qualstats_quals q ON q.queryid = ps.queryid
            WHERE q.qualid = :qualid
        """), qualid=base['id']))
        # Create all possible indexes for this qual
        not_tested = []
        plans = {}
        for query in queries:
            plans[query.querid]['without'] = self.get_plans(query.query, database,
                                                       base)
        for ind in indexes:
            text_value = conn.execute(
                text(TEXTUAL_INDEX_QUERY),
                relid=base['relid'],
                attnums=[q['attnum'] for q in qual_to_resolve['quals']],
                indexam=ind).first().index_ddl
            try:
                conn.execute(text("""SELECT hypopg_create_index(:text_value)"""),
                            text_value=text_value)
            except:
                not_tested.append(ind)
        for query in queries:
            plans[query.querid]['with'] = self.get_plans(query.query, database,
                                                         base)
        self.render_json(plans)



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
            "nbfiltered"
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
        [[Wizard("Apply wizardry to %(database)s")]])
