"""
Dashboard for the by-function page.
"""

from powa.dashboards import ContentWidget, Dashboard, DashboardPage
from powa.database import DatabaseOverview
from powa.sql.views_grid import powa_getuserfuncdata_detailed_db


class FunctionDetail(ContentWidget):
    """
    Detail widget showing summarized information for the function.
    """

    title = "Function Detail"
    data_url = r"/server/(\d+)/metrics/database/([^\/]+)/function/(\d+)/detail"

    def get(self, server, database, function):
        stmt = powa_getuserfuncdata_detailed_db("%(funcid)s")

        value = self.execute(
            stmt,
            params={
                "server": server,
                "database": database,
                "funcid": function,
                "from": self.get_argument("from"),
                "to": self.get_argument("to"),
            },
        )
        if value is None or len(value) < 1:
            self.render_json(None)
            return
        self.render_json(value[0])


class FunctionOverview(DashboardPage):
    """
    Dashboard page for a function.
    """

    base_url = r"/server/(\d+)/database/([^\/]+)/function/(\d+)/overview"
    params = ["server", "database", "function"]
    datasources = [FunctionDetail]
    parent = DatabaseOverview
    title = "Function overview"

    def dashboard(self):
        # This COULD be initialized in the constructor, but tornado < 3 doesn't
        # call it
        if getattr(self, "_dashboard", None) is not None:
            return self._dashboard

        self._dashboard = Dashboard(
            "Function %(function)s on database %(database)s",
            [[FunctionDetail]],
        )

        return self._dashboard
