"""
Dashboard for the qual page
"""
from sqlalchemy.sql import text, bindparam
from tornado.web import HTTPError
from powa.dashboards import (
    Dashboard, Graph, Grid,
    MetricGroupDef, MetricDef,
    DashboardPage, ContentWidget)
from powa.sql import qual_constants, resolve_quals
from powa.sql.utils import inner_cc
from powa.query import QueryOverview
from powa.sql.views import qualstat_getstatdata


class QualConstantsMetricGroup(MetricGroupDef):
    """
    Metric group used for the qual charts.
    """
    name = "QualConstants"
    data_url = r"/server/(\d+)/metrics/database/([^\/]+)/query/(-?\d+)/qual/(\d+)/constants"
    xaxis = "rownumber"
    occurences = MetricDef(label="<%=group%>")
    grouper = "constants"

    @property
    def query(self):
        query = (qual_constants(bindparam("server"), "most_used",
                                bindparam("from"),
                                bindparam("to"),
                                text("""
            datname = :database AND
            coalesce_range && tstzrange(:from, :to)"""), ":query", ":qual", top=10))
        base = qualstat_getstatdata(bindparam("server"))
        c = inner_cc(base)
        base = base.where(c.queryid == bindparam("query")).alias()
        totals = (base.select()
                  .where((c.qualid == bindparam("qual")) &
                         (c.queryid == bindparam("query")))).alias()
        return (query.alias().select()
                .column(totals.c.occurences.label('total_occurences'))
                .correlate(query))

    def add_params(self, params):
        params['queryids'] = [int(params['query'])]
        return params

    def post_process(self, data, server, database, query, qual, **kwargs):
        if not data['data']:
            return data
        max_rownumber = 0
        total_top10 = 0
        total = None
        d = {'total_occurences': 0}
        for d in data['data']:
            max_rownumber = max(max_rownumber, d['rownumber'])
            total_top10 += d['occurences']
        else:
            total = d['total_occurences']
        data['data'].append({'occurences': total - total_top10,
                     'rownumber': max_rownumber + 1,
                     'constants': 'Others'})
        return data


class QualDetail(ContentWidget):
    """
    Content widget showing detail for a specific qual.
    """
    title = "Detail for this Qual"
    data_url = r"/server/(\d+)/database/([^\/]+)/query/(-?\d+)/qual/(\d+)/detail"

    def get(self, server, database, query, qual):
        try:
            # Check remote access first
            remote_conn = self.connect(server, database=database,
                                       remote_access=True)
        except Exception as e:
            raise HTTPError(501, "Could not connect to remote server: %s" %
                                 str(e))
        stmt = qualstat_getstatdata(server)
        c = inner_cc(stmt)
        stmt = stmt.alias()
        stmt = (stmt.select()
                .where((c.qualid == bindparam("qualid")))
                .where(stmt.c.occurences > 0)
                .column((stmt.c.queryid == bindparam("query")).label("is_my_query")))
        quals = list(self.execute(
            stmt,
            params={"server": server,
                    "query": query,
                    "from": self.get_argument("from"),
                    "to": self.get_argument("to"),
                    "queryids": [query],
                    "qualid": qual}))

        my_qual = None
        other_queries = {}

        for qual in quals:
            if qual['is_my_query']:
                my_qual = resolve_quals(remote_conn, [qual])[0]

        if my_qual is None:
            self.render("xhr.html", content="No data")
            return

        self.render("database/query/qualdetail.html",
                    qual=my_qual,
                    database=database,
                    server=server)

class OtherQueriesMetricGroup(MetricGroupDef):
    """Metric group showing other queries for this qual."""
    name = "other_queries"
    xaxis = "queryid"
    axis_type = "category"
    data_url = r"/server/(\d+)/metrics/database/([^\/]+)/query/(-?\d+)/qual/(\d+)/other_queries"
    query_str = MetricDef(label="Query", type="query", url_attr="url")


    @property
    def query(self):
        return text("""
            SELECT distinct queryid, query,
            query as query_str, pd.srvid
            FROM powa_qualstats_quals pqs
            JOIN powa_statements USING (queryid, dbid, srvid, userid)
            JOIN powa_databases pd ON pd.oid = pqs.dbid AND pd.srvid =
            pqs.srvid
            WHERE qualid = :qual
                AND pqs.queryid != :query
                AND pd.srvid = :server
                AND pd.datname = :database""")

    def process(self, val, database=None, **kwargs):
        val = dict(val)
        val["url"] = self.reverse_url(
            "QueryOverview", val["srvid"], database, val["queryid"])
        return val


class QualOverview(DashboardPage):
    """
    Dashboard page for a specific qual.
    """

    base_url = r"/server/(\d+)/database/([^\/]+)/query/(-?\d+)/qual/(\d+)"
    params = ["server", "database", "query", "qual"]
    datasources = [QualDetail, OtherQueriesMetricGroup, QualConstantsMetricGroup]
    parent = QueryOverview
    title = 'Predicate Overview'

    def dashboard(self):
        # This COULD be initialized in the constructor, but tornado < 3 doesn't
        # call it
        if getattr(self, '_dashboard', None) is not None:
            return self._dashboard

        self._dashboard = Dashboard(
            "Qual %(qual)s",
            [[QualDetail],
             [Grid("Other queries",
                   metrics=OtherQueriesMetricGroup.all(),
                   columns=[])],
             [Graph("Most executed values",
                    metrics=[QualConstantsMetricGroup.occurences],
                    x_label_attr="constants",
                    renderer="pie")]])

        return self._dashboard
