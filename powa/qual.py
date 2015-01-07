from powa.dashboards import (
    Dashboard, Graph, Grid,
    MetricGroupDef, MetricDef,
    DashboardPage,
    ContentWidget)
from sqlalchemy.sql import text, ColumnCollection, bindparam
from powa.sql import aggregate_qual_values, resolve_quals, func
from powa.query import QueryOverview
from powa.sql.views import qualstat_getstatdata_sample


class QualConstantsMetricGroup(MetricGroupDef):
    """
    Metric group used for the qual charts.
    """
    name = "QualConstants"
    data_url = r"/metrics/database/(\w+)/query/(\w+)/qual/(\w+)/constants"
    xaxis = "rownumber"
    mffr = MetricDef(label="Most Filtering")
    lffr = MetricDef(label="Least Filtering")
    mec = MetricDef(label="Most Executed")
    query = (aggregate_qual_values(text("""
        s.dbname = :database AND
        s.md5query = :query AND
        qn.nodehash = :qual AND
        coalesce_range && tstzrange(:from, :to)"""), top=10)
             .with_only_columns(['rownumber',
                                '(mf).filter_ratio as mffr',
                                '(mf).constants as mfconstants',
                                '(lf).filter_ratio as lffr',
                                '(lf).constants as lfconstants',
                                '(me).count as mec',
                                '(me).constants as meconstants']))


    def post_process(self, data, database, query, qual, **kwargs):
        conn = self.connect(database=database)
        return data


class QualDetail(ContentWidget):
    """
    Content widget showing detail for a specific qual.
    """
    title = "Detail for this Qual"
    data_url = r"/database/(\w+)/query/(\w+)/qual/(\w+)/detail"

    def get(self, database, query, qual):
        stmt = qualstat_getstatdata_sample()
        c = ColumnCollection(*stmt.inner_columns)
        stmt = (stmt
            .where((c.nodehash == bindparam("nodehash")) &
                   (c.md5query == bindparam("query")))
            .column((c.md5query == bindparam("query")).label("is_my_query")))
        quals = list(self.execute(
            stmt,
            params={"query": query,
                    "from": self.get_argument("from"),
                    "to": self.get_argument("to"),
                    "nodehash": qual}))
        quals = resolve_quals(self.connect(database=database), quals)
        my_qual = None
        other_queries = {}
        for qual in quals:
            if qual['is_my_query']:
                my_qual = qual
            else:
                other_queries[qual['md5query']] = qual['query']
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
               metrics=[QualConstantsMetricGroup.mec],
               x_label_attr="mfconstants",
               renderer="pie")]])
