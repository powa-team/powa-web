"""
Global optimization widget
"""
from __future__ import absolute_import
from powa.framework import AuthHandler
from powa.dashboards import (
    Widget, MetricGroupDef)

from powa.sql import (resolve_quals, get_any_sample_query,
                      get_hypoplans, HypoIndex)
import json
from powa.sql.compat import JSONB
from powa.sql.views import qualstat_getstatdata
from powa.sql.tables import powa_databases
from sqlalchemy.sql import (bindparam, literal_column, join, select,
                            alias, text, func, column, cast)



class IndexSuggestionHandler(AuthHandler):

    def post(self, database):
        payload = json.loads(self.request.body.decode("utf8"))
        from_date = payload['from_date']
        to_date = payload['to_date']
        indexes = []
        for ind in payload['indexes']:
            hypoind = HypoIndex(ind['nspname'],
                                ind['relname'],
                                ind['ams'])
            hypoind._ddl = ind['ddl']
            indexes.append(hypoind)
        queryids = payload['queryids']
        powa_conn = self.connect(database="powa")
        conn = self.connect(database=database)
        queries = list(powa_conn.execute(text("""
            SELECT DISTINCT query, ps.queryid
            FROM powa_statements ps
            WHERE queryid IN :queryids
        """), queryids=tuple(queryids)))
        # Create all possible indexes for this qual
        hypo_version = self.has_extension("hypopg", database=database)
        hypoplans = {}
        indbyname = {}
        if hypo_version and hypo_version >= "0.0.3":
            # identify indexes
            # create them
            for ind in indexes:
                indname = self.execute(
                    select(["*"])
                    .select_from(func.hypopg_create_index(ind.ddl)),
                    database=database).first()[1]
                indbyname[indname] = ind
            # Build the query and fetch the plans
            for query in queries:
                querystr = get_any_sample_query(self, database, query.queryid,
                                                from_date,
                                                to_date)
                if querystr:
                    try:
                        hypoplans[query.queryid] = get_hypoplans(
                            self.connect(database=database), querystr,
                            indbyname.values())
                    except:
                        # TODO: stop ignoring the error
                        continue
            # To value of a link is the the reduction in cost
        self.render_json(hypoplans)



class WizardMetricGroup(MetricGroupDef):
    """Metric group for the wizard."""
    name = "wizard"
    xaxis = "quals"
    axis_type = "category"
    data_url = r"/metrics/database/([^\/]+)/wizard/"
    enabled = False

    @property
    def query(self):
        pq = qualstat_getstatdata(column("eval_type") == "f")
        base = alias(pq)
        query = (select([
            func.array_agg(column("queryid")).label("queryids"),
            "qualid",
            cast(column("quals"), JSONB).label('quals'),
            "occurences",
            "execution_count",
            func.array_agg(column("query")).label("queries"),
            "avg_filter",
            "filter_ratio"
        ]).select_from(
            join(base, powa_databases,
                 onclause=(
                     powa_databases.c.oid == literal_column("dbid"))))
            .where(powa_databases.c.datname == bindparam("database"))
            .where(column("avg_filter") > 1000)
            .where(column("filter_ratio") > 0.3)
            .group_by(column("qualid"), column("execution_count"),
                      column("occurences"),
                      cast(column("quals"), JSONB),
                     column("avg_filter"), column("filter_ratio"))
            .order_by(column("occurences").desc())
            .limit(200))
        return query

    def post_process(self, data, database, **kwargs):
        conn = self.connect(database=database)
        data["data"] = resolve_quals(conn, data["data"])
        return data


class Wizard(Widget):

    def __init__(self, title):
        self.title = title

    def parameterized_json(self, handler, database):
        values = self.__dict__.copy()
        values['metrics'] = []
        values['type'] = 'wizard'
        values['datasource'] = 'wizard'
        hypover = handler.has_extension("hypopg", database=database)
        qsver = handler.has_extension("pg_qualstats")
        values['has_hypopg'] = hypover and hypover  >= '0.0.3'
        values['has_qualstats'] = qsver and qsver >= '0.0.7'
        values['database'] = database
        return values
