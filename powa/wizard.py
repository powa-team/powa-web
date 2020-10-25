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
from sqlalchemy.types import TEXT
from sqlalchemy.exc import DBAPIError
from tornado.web import HTTPError


class IndexSuggestionHandler(AuthHandler):

    def post(self, srvid, database):
        try:
            # Check remote access first
            remote_conn = self.connect(srvid, database=database,
                                       remote_access=True)
        except Exception as e:
            raise HTTPError(501, "Could not connect to remote server: %s" %
                                 str(e))

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
        queries = list(powa_conn.execute(text("""
            SELECT DISTINCT query, ps.queryid
            FROM powa_statements ps
            WHERE srvid = :srvid
            AND queryid IN :queryids
        """), srvid=srvid, queryids=tuple(queryids)))
        # Create all possible indexes for this qual
        hypo_version = self.has_extension_version(srvid, "hypopg", "0.0.3",
                                                  database=database)
        hypoplans = {}
        indbyname = {}
        inderrors = {}
        if hypo_version:
            # identify indexes
            # create them
            for ind in indexes:
                try:
                    indname = remote_conn.execute(
                            select(["*"])
                            .select_from(func.hypopg_create_index(ind.ddl))
                    ).first()[1]
                    indbyname[indname] = ind
                except DBAPIError as e:
                    inderrors[ind.ddl] = str(e.orig)
                    continue
                except Exception:
                    # TODO handle other errors?
                    continue
            # Build the query and fetch the plans
            for query in queries:
                querystr = get_any_sample_query(self, srvid, database,
                                                query.queryid,
                                                from_date,
                                                to_date)
                if querystr:
                    try:
                        hypoplans[query.queryid] = get_hypoplans(
                            remote_conn, querystr, indbyname.values())
                    except Exception:
                        # TODO: stop ignoring the error
                        continue
            # To value of a link is the the reduction in cost
        result = {}
        result["plans"] = hypoplans
        result["inderrors"] = inderrors
        self.render_json(result)


class WizardMetricGroup(MetricGroupDef):
    """Metric group for the wizard."""
    name = "wizard"
    xaxis = "quals"
    axis_type = "category"
    data_url = r"/server/(\d+)/metrics/database/([^\/]+)/wizard/"
    enabled = False

    @property
    def query(self):
        pq = qualstat_getstatdata(bindparam("server"),
                                  column("eval_type") == "f")
        base = alias(pq)
        query = (select([
            # queryid in pg11+ is int64, so the value can exceed javascript's
            # Number.MAX_SAFE_INTEGER, which mean that the value can get
            # truncated by the browser, leading to looking for unexisting
            # queryid when processing this data.  To avoid that, simply cast
            # the value to text.
            func.array_agg(cast(column("queryid"), TEXT)).label("queryids"),
            column("qualid"),
            cast(column("quals"), JSONB).label('quals'),
            column("occurences"),
            column("execution_count"),
            func.array_agg(column("query")).label("queries"),
            column("avg_filter"),
            column("filter_ratio")
        ]).select_from(
            join(base, powa_databases,
                 onclause=(
                     powa_databases.c.oid == literal_column("dbid") and
                     powa_databases.c.srvid == literal_column("srvid")
                 )))
            .where(powa_databases.c.datname == bindparam("database"))
            .where(powa_databases.c.srvid == bindparam("server"))
            .where(column("avg_filter") > 1000)
            .where(column("filter_ratio") > 0.3)
            .group_by(column("qualid"), column("execution_count"),
                      column("occurences"),
                      cast(column("quals"), JSONB),
                     column("avg_filter"), column("filter_ratio"))
            .order_by(column("occurences").desc())
            .limit(200))
        return query

    def post_process(self, data, server, database, **kwargs):
        conn = self.connect(server, database=database, remote_access=True)
        data["data"] = resolve_quals(conn, data["data"])
        return data


class Wizard(Widget):

    def __init__(self, title):
        self.title = title

    def parameterized_json(self, handler, **parms):
        values = self.__dict__.copy()
        values['metrics'] = []
        values['type'] = 'wizard'
        values['datasource'] = 'wizard'

        # First check that we can connect on the remote server, otherwise we
        # won't be able to do anything
        try:
            remote_conn = handler.connect(parms["server"],
                                          database=parms["database"],
                                          remote_access=True)
        except Exception as e:
            values['has_remote_conn'] = False
            values['conn_error'] = str(e)
            return values

        values['has_remote_conn'] = True

        hypover = handler.has_extension_version(parms["server"],
                                                "hypopg", "0.0.3",
                                                database=parms["database"])
        qsver = handler.has_extension_version(parms["server"], "pg_qualstats",
                                              "0.0.7")
        values['has_hypopg'] = hypover
        values['has_qualstats'] = qsver
        values['server'] = parms["server"]
        values['database'] = parms["database"]
        return values
