"""
Datasource template used for the various IO pages.
"""

from powa.dashboards import MetricDef, MetricGroupDef
from powa.sql.utils import sum_per_sec
from powa.sql.views_graph import powa_get_io_sample
from powa.sql.views_grid import powa_getiodata


class TemplateIoGraph(MetricGroupDef):
    """
    Template metric group for IO graph.
    """

    xaxis = "ts"
    query_qual = None

    reads = MetricDef(
        label="Reads", type="sizerate", desc="Amount of data read per second"
    )
    read_time = MetricDef(
        label="Read time",
        type="duration",
        desc="Total time spend reading data per second",
    )
    writes = MetricDef(
        label="Write",
        type="sizerate",
        desc="Amount of data written per second",
    )
    write_time = MetricDef(
        label="Write time",
        type="duration",
        desc="Total time spend writing data per second",
    )
    writebacks = MetricDef(
        label="Writebacks",
        type="sizerate",
        desc="Amount of data writeback per second",
    )
    writeback_time = MetricDef(
        label="Writeback time",
        type="duration",
        desc="Total time spend doing writeback per second",
    )
    extends = MetricDef(
        label="Extends",
        type="sizerate",
        desc="Amount of data extended per second",
    )
    extend_time = MetricDef(
        label="Extend time",
        type="duration",
        desc="Total time spend extending relations per second",
    )
    hits = MetricDef(
        label="Hits",
        type="sizerate",
        desc="Amount of data found in shared_buffers per second",
    )
    evictions = MetricDef(
        label="Eviction",
        type="sizerate",
        desc="Amount of data evicted from shared_buffers per second",
    )
    reuses = MetricDef(
        label="Reuses",
        type="sizerate",
        desc="Amount of data reused in shared_buffers per second",
    )
    fsyncs = MetricDef(
        label="Fsyncs", type="sizerate", desc="Blocks flushed per second"
    )
    fsync_time = MetricDef(
        label="Fsync time",
        type="duration",
        desc="Total time spend flushing block per second",
    )

    @classmethod
    def _get_metrics(cls, handler, **params):
        base = cls.metrics.copy()

        pg_version_num = handler.get_pg_version_num(handler.path_args[0])
        # if we can't connect to the remote server, assume pg15 or less
        if pg_version_num is None or pg_version_num < 160000:
            return {}
        return base

    @property
    def query(self):
        query = powa_get_io_sample(self.query_qual)

        from_clause = query

        cols = [
            "sub.srvid",
            "extract(epoch FROM sub.ts) AS ts",
            sum_per_sec("reads"),
            sum_per_sec("read_time"),
            sum_per_sec("writes"),
            sum_per_sec("write_time"),
            sum_per_sec("writebacks"),
            sum_per_sec("writeback_time"),
            sum_per_sec("extends"),
            sum_per_sec("extend_time"),
            sum_per_sec("hits"),
            sum_per_sec("evictions"),
            sum_per_sec("reuses"),
            sum_per_sec("fsyncs"),
            sum_per_sec("fsync_time"),
        ]

        return """SELECT {cols}
        FROM (
            {from_clause}
        ) AS sub
        WHERE sub.mesure_interval != '0 s'
        GROUP BY sub.srvid, sub.ts, sub.mesure_interval
        ORDER BY sub.ts""".format(
            cols=", ".join(cols),
            from_clause=from_clause,
        )


class TemplateIoGrid(MetricGroupDef):
    """
    Template metric group for IO grid.
    """

    axis_type = "category"
    query_qual = None

    reads = MetricDef(
        label="Reads", type="size", desc="Total amount of data read"
    )
    read_time = MetricDef(
        label="Read time",
        type="duration",
        desc="Total amount of time reading data",
    )
    writes = MetricDef(
        label="Writes", type="size", desc="Total amount of data write"
    )
    write_time = MetricDef(
        label="Write time",
        type="duration",
        desc="Total amount of time writing data",
    )
    writebacks = MetricDef(
        label="Writebacks", type="size", desc="Total amount of data writeback"
    )
    writeback_time = MetricDef(
        label="Writeback time",
        type="duration",
        desc="Total amount of time doing data writeback",
    )
    extends = MetricDef(
        label="Extends", type="size", desc="Total amount of data extension"
    )
    extend_time = MetricDef(
        label="Extend time",
        type="duration",
        desc="Total amount of time extending data",
    )
    hits = MetricDef(
        label="Hits", type="size", desc="Total amount of data hit"
    )
    evictions = MetricDef(
        label="Evictions", type="size", desc="Total amount of data evicted"
    )
    reuses = MetricDef(
        label="Reuses", type="size", desc="Total amount of data reused"
    )
    fsyncs = MetricDef(
        label="Fsyncs", type="size", desc="Total amount of data flushed"
    )
    fsync_time = MetricDef(
        label="Fsync time",
        type="duration",
        desc="Total amount of time flushing data",
    )

    @property
    def query(self):
        query = powa_getiodata(self.query_qual)

        return query

    def process(self, val, **kwargs):
        val["backend_type_url"] = self.reverse_url(
            "ByBackendTypeIoOverview", val["srvid"], val["backend_type"]
        )

        val["obj_url"] = self.reverse_url(
            "ByObjIoOverview", val["srvid"], val["object"]
        )

        val["context_url"] = self.reverse_url(
            "ByContextIoOverview", val["srvid"], val["context"]
        )

        return val
