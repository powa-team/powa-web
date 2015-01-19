from powa.dashboards import (
    Dashboard, Graph, Grid,
    MetricGroupDef, MetricDef,
    DashboardPage,
    ContentWidget)
from sqlalchemy.sql import (
    text, ColumnCollection, bindparam, table, select,
    literal_column, column, cast, case)
from sqlalchemy.types import Numeric
from powa.sql import qual_constants, resolve_quals, func
from powa.query import QueryOverview
from powa.sql.views import qualstat_getstatdata, qualstat_getstatdata


class QualConstantsMetricGroup(MetricGroupDef):
    """
    Metric group used for the qual charts.
    """
    name = "QualConstants"
    data_url = r"/metrics/database/(\w+)/query/(\w+)/qual/(\w+)/constants"
    xaxis = "rownumber"
    count = MetricDef(label="<%=group%>")
    grouper = "constants"

    @property
    def query(self):
        query = (qual_constants("most_executed",
                                text("""
            datname = :database AND
            s.queryid = :query AND
            qn.qualid = :qual AND
            coalesce_range && tstzrange(:from, :to)"""), top=10))
        base = qualstat_getstatdata()
        c = ColumnCollection(*base.inner_columns)
        base = base.where(c.queryid == bindparam("query")).alias()
        totals = (base.select()
                  .where((c.qualid == bindparam("qual")) &
                         (c.queryid == bindparam("query")))).alias()
        return (query.alias().select()
                .column(totals.c.count.label('total_count'))
                .column(base.c.queryid)
                .correlate(query))


    def post_process(self, data, database, query, qual, **kwargs):
        if not data['data']:
            return data
        conn = self.connect(database=database)
        max_rownumber = 0
        total_top10 = 0
        total = None
        d = {'total_count': 0}
        for d in data['data']:
            max_rownumber = max(max_rownumber, d['rownumber'])
            total_top10 += d['count']
        else:
            total = d['total_count']
        data['data'].append({'count': total - total_top10,
                     'rownumber': max_rownumber + 1,
                     'constants': 'Others'})
        return data


class QualDetail(ContentWidget):
    """
    Content widget showing detail for a specific qual.
    """
    title = "Detail for this Qual"
    data_url = r"/database/(\w+)/query/(\w+)/qual/(\w+)/detail"

    def get(self, database, query, qual):
        stmt = qualstat_getstatdata()
        c = ColumnCollection(*stmt.inner_columns)
        stmt = stmt.alias()
        stmt = (stmt.select()
            .where((c.qualid == bindparam("qualid")) &
                   (c.queryid== bindparam("query")))
            .where(stmt.c.count > 0)
            .column((c.queryid == bindparam("query")).label("is_my_query")))
        quals = list(self.execute(
            stmt,
            params={"query": query,
                    "from": self.get_argument("from"),
                    "to": self.get_argument("to"),
                    "qualid": qual}))
        quals = resolve_quals(self.connect(database=database), quals)
        my_qual = None
        other_queries = {}
        for qual in quals:
            if qual['is_my_query']:
                my_qual = qual
            else:
                other_queries[qual['queryid']] = qual['query']
        if my_qual is None:
            self.render("xhr.html", content="nodata")
            return
        self.render("database/query/qualdetail.html",
                    qual=my_qual,
                    database=database,
                    other_queries=other_queries)


class QualOverview(DashboardPage):
    """
    Dashboard page for a specific qual.
    """

    base_url = r"/database/(\w+)/query/(\w+)/qual/(\w+)"

    params = ["database", "query", "qual"]

    parent = QueryOverview

    datasources = [QualDetail, QualConstantsMetricGroup]

    dashboard = Dashboard(
        "Qual %(qual)s",
        [[QualDetail],
         [Graph("Most executed values",
               metrics=[QualConstantsMetricGroup.count],
               x_label_attr="constants",
               renderer="pie")]])
