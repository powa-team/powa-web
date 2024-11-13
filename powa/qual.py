"""
Dashboard for the qual page
"""

from powa.dashboards import (
    ContentWidget,
    Dashboard,
    DashboardPage,
    Grid,
    MetricDef,
    MetricGroupDef,
)
from powa.query import QueryOverview
from powa.sql import qual_constants, resolve_quals
from powa.sql.views import qualstat_getstatdata
from tornado.web import HTTPError


class QualConstantsMetricGroup(MetricGroupDef):
    """
    Metric group used for the qual charts.
    """

    name = "QualConstants"
    data_url = r"/server/(\d+)/metrics/database/([^\/]+)/query/(-?\d+)/qual/(\d+)/constants"
    xaxis = "rownumber"
    occurences = MetricDef(label="Occurences")
    grouper = "constants"

    @property
    def query(self):
        most_used = qual_constants(
            "%(server)s",
            "most_used",
            """
            datname = %(database)s AND
            coalesce_range && tstzrange(%(from)s, %(to)s)""",
            "%(query)s",
            "%(qual)s",
            top=10,
        )

        correlated = qualstat_getstatdata(
            extra_where=["qualid = %(qual)s", "queryid = %(query)s"]
        )
        sql = """SELECT sub.*, correlated.occurences as total_occurences
            FROM (
                SELECT *
                FROM (
                    {most_used}
                ) AS most_used
            ) AS sub, (
                {correlated}
            ) AS correlated
        """.format(most_used=most_used, correlated=correlated)

        return sql

    def add_params(self, params):
        params["queryids"] = [int(params["query"])]
        return params

    def post_process(self, data, server, database, query, qual, **kwargs):
        if not data["data"]:
            return data
        max_rownumber = 0
        total_top10 = 0
        total = None
        d = {"total_occurences": 0}
        for d in data["data"]:
            max_rownumber = max(max_rownumber, d["rownumber"])
            total_top10 += d["occurences"]
        else:
            total = d["total_occurences"]
        data["data"].append(
            {
                "occurences": total - total_top10,
                "rownumber": max_rownumber + 1,
                "constants": "Others",
            }
        )
        return data


class QualDetail(ContentWidget):
    """
    Content widget showing detail for a specific qual.
    """

    title = "Detail for this Qual"
    data_url = (
        r"/server/(\d+)/database/([^\/]+)/query/(-?\d+)/qual/(\d+)/detail"
    )

    def get(self, server, database, query, qual):
        try:
            # Check remote access first
            remote_conn = self.connect(
                server, database=database, remote_access=True
            )
        except Exception as e:
            raise HTTPError(
                501, "Could not connect to remote server: %s" % str(e)
            )
        stmt = qualstat_getstatdata(
            extra_select=["queryid = %(query)s AS is_my_query"],
            extra_where=["qualid = %(qualid)s", "occurences > 0"],
            extra_groupby=["queryid"],
        )
        quals = list(
            self.execute(
                stmt,
                params={
                    "server": server,
                    "query": query,
                    "from": self.get_argument("from"),
                    "to": self.get_argument("to"),
                    "queryids": [query],
                    "qualid": qual,
                },
            )
        )

        my_qual = None

        for qual in quals:
            if qual["is_my_query"]:
                my_qual = resolve_quals(remote_conn, [qual])[0]

        if my_qual is None:
            self.render_json(None)
            return

        self.render_json(my_qual)


class OtherQueriesMetricGroup(MetricGroupDef):
    """Metric group showing other queries for this qual."""

    name = "other_queries"
    xaxis = "queryid"
    axis_type = "category"
    data_url = r"/server/(\d+)/metrics/database/([^\/]+)/query/(-?\d+)/qual/(\d+)/other_queries"
    query_str = MetricDef(label="Query", type="query", url_attr="url")

    @property
    def query(self):
        return """
            SELECT distinct queryid, query,
            query as query_str, pd.srvid
            FROM {powa}.powa_qualstats_quals pqs
            JOIN {powa}.powa_statements USING (queryid, dbid, srvid, userid)
            JOIN {powa}.powa_databases pd ON pd.oid = pqs.dbid AND pd.srvid =
            pqs.srvid
            WHERE qualid = %(qual)s
                AND pqs.queryid != %(query)s
                AND pd.srvid = %(server)s
                AND pd.datname = %(database)s"""

    def process(self, val, database=None, **kwargs):
        val["url"] = self.reverse_url(
            "QueryOverview", val["srvid"], database, val["queryid"]
        )
        return val


class QualOverview(DashboardPage):
    """
    Dashboard page for a specific qual.
    """

    base_url = r"/server/(\d+)/database/([^\/]+)/query/(-?\d+)/qual/(\d+)"
    params = ["server", "database", "query", "qual"]
    datasources = [
        QualDetail,
        OtherQueriesMetricGroup,
        QualConstantsMetricGroup,
    ]
    parent = QueryOverview
    title = "Predicate Overview"

    def dashboard(self):
        # This COULD be initialized in the constructor, but tornado < 3 doesn't
        # call it
        if getattr(self, "_dashboard", None) is not None:
            return self._dashboard

        self._dashboard = Dashboard(
            "Qual %(qual)s",
            [
                [QualDetail],
                [
                    Grid(
                        "Other queries",
                        metrics=OtherQueriesMetricGroup.all(),
                        columns=[],
                    )
                ],
                [
                    Grid(
                        "Most executed values",
                        metrics=[QualConstantsMetricGroup.occurences],
                        x_label_attr="constants",
                        renderer="distribution",
                    )
                ],
            ],
        )

        return self._dashboard
