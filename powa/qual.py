"""
Dashboard for the qual page
"""
from sqlalchemy.sql import text, bindparam
from tornado.web import HTTPError
from powa.dashboards import (
    Dashboard, Graph,
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
            s.queryid = :query AND
            qn.qualid = :qual AND
            coalesce_range && tstzrange(:from, :to)"""), top=10))
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
                .column((c.queryid == bindparam("query")).label("is_my_query")))
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

        other_queries = {r['queryid']: r['query'] for r in self.execute(text("""
            SELECT DISTINCT queryid, query
            FROM powa_qualstats_quals
            JOIN powa_statements USING (queryid)
            WHERE qualid = :qual
            LIMIT 5"""),
            params={"qual": qual})}
        for qual in quals:
            if qual['is_my_query']:
                my_qual = resolve_quals(remote_conn, [qual])[0]

        if my_qual is None:
            self.render("xhr.html", content="No data")
            return

        self.render("database/query/qualdetail.html",
                    qual=my_qual,
                    database=database,
                    server=server,
                    other_queries=other_queries)


class QualOverview(DashboardPage):
    """
    Dashboard page for a specific qual.
    """

    base_url = r"/server/(\d+)/database/([^\/]+)/query/(-?\d+)/qual/(\d+)"
    params = ["server", "database", "query", "qual"]
    datasources = [QualDetail, QualConstantsMetricGroup]
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
             [Graph("Most executed values",
                    metrics=[QualConstantsMetricGroup.occurences],
                    x_label_attr="constants",
                    renderer="pie")]])

        return self._dashboard
