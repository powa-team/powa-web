"""
Dashboards for the various IO pages.
"""

from powa.config import ConfigChangesGlobal
from powa.dashboards import Dashboard, DashboardPage, Graph, Grid
from powa.io_template import TemplateIoGraph, TemplateIoGrid
from powa.server import ServerOverview


class TemplateIoOverview(DashboardPage):
    """
    Template dashboard for IO.
    """

    parent = ServerOverview
    timeline = ConfigChangesGlobal
    timeline_params = ["server"]

    def dashboard(self):
        # This COULD be initialized in the constructor, but tornado < 3 doesn't
        # call it
        if getattr(self, "_dashboard", None) is not None:
            return self._dashboard

        io_metrics = self.ds_graph.split(
            self,
            [
                ["reads", "writes", "writebacks", "extends", "fsyncs"],
                ["hits", "evictions", "reuses"],
            ],
        )
        graphs = []
        graphs.append(
            [
                Graph(
                    "IO blocks",
                    metrics=io_metrics[1],
                ),
                Graph(
                    "IO timing",
                    metrics=io_metrics[0],
                ),
                Graph(
                    "IO misc",
                    metrics=io_metrics[2],
                ),
            ]
        )

        graphs.append(
            [
                Grid(
                    "IO summary",
                    columns=[
                        {
                            "name": "backend_type",
                            "label": "Backend Type",
                            "url_attr": "backend_type_url",
                        },
                        {
                            "name": "obj",
                            "label": "Object Type",
                            "url_attr": "obj_url",
                        },
                        {
                            "name": "context",
                            "label": "Context",
                            "url_attr": "context_url",
                        },
                    ],
                    metrics=self.ds_grid.all(),
                )
            ]
        )

        self._dashboard = Dashboard(self.title, graphs)
        return self._dashboard


class ByBackendTypeIoGraph(TemplateIoGraph):
    """
    Metric group used by per backend_type graph.
    """

    name = "backend_type_io_graph"
    data_url = r"/server/(\d+)/metrics/backend_type_graph/([a-z0-9%]+)/io/"

    query_qual = "backend_type = %(backend_type)s"


class ByBackendTypeIoGrid(TemplateIoGrid):
    """
    Metric group used by per backend_type grid.
    """

    xaxis = "backend_type"
    name = "backend_type_io_grid"
    data_url = r"/server/(\d+)/metrics/backend_type_grid/([a-z0-9%]+)/io/"

    query_qual = "backend_type = %(backend_type)s"


class ByBackendTypeIoOverview(TemplateIoOverview):
    """
    Per backend-type Dashboard page.
    """

    base_url = r"/server/(\d+)/metrics/backend_type/([a-z0-9%]+)/io/overview/"
    params = ["server", "backend_type"]
    title = 'IO for "%(backend_type)s" backend type'

    ds_graph = ByBackendTypeIoGraph
    ds_grid = ByBackendTypeIoGrid
    datasources = [ds_graph, ds_grid]


class ByObjIoGraph(TemplateIoGraph):
    """
    Metric group used by per object graph.
    """

    name = "obj_io_graph"
    data_url = r"/server/(\d+)/metrics/obj_graph/([a-z0-9%]+)/io/"

    query_qual = "object = %(obj)s"


class ByObjIoGrid(TemplateIoGrid):
    """
    Metric group used by per object grid.
    """

    xaxis = "obj"
    name = "obj_io_grid"
    data_url = r"/server/(\d+)/metrics/obj_grid/([a-z0-9%]+)/io/"

    query_qual = "object = %(obj)s"


class ByObjIoOverview(TemplateIoOverview):
    """
    Per object Dashboard page.
    """

    base_url = r"/server/(\d+)/metrics/obj/([a-z0-9%]+)/io/overview/"
    params = ["server", "obj"]
    title = 'IO for "%(obj)s" object'

    ds_graph = ByObjIoGraph
    ds_grid = ByObjIoGrid
    datasources = [ds_graph, ds_grid]


class ByContextIoGraph(TemplateIoGraph):
    """
    Metric group used by per context graph.
    """

    name = "context_io_graph"
    data_url = r"/server/(\d+)/metrics/context_graph/([a-z0-9%]+)/io/"

    query_qual = "context = %(context)s"


class ByContextIoGrid(TemplateIoGrid):
    """
    Metric group used by per context grid.
    """

    xaxis = "context"
    name = "context_io_grid"
    data_url = r"/server/(\d+)/metrics/context_grid/([a-z0-9%]+)/io/"

    query_qual = "context = %(context)s"


class ByContextIoOverview(TemplateIoOverview):
    """
    Per context Dashboard page.
    """

    base_url = r"/server/(\d+)/metrics/context/([a-z0-9%]+)/io/overview/"
    params = ["server", "context"]
    title = 'IO for "%(context)s" context'

    ds_graph = ByContextIoGraph
    ds_grid = ByContextIoGrid
    datasources = [ds_graph, ds_grid]
