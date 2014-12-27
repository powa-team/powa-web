from powa.dashboards import MetricGroupDef, MetricDef

class Detail(MetricGroupDef):
    total_calls = MetricDef(label="#Calls", type="string")
    total_runtime = MetricDef(label="Runtime", type="duration")
    avg_runtime = MetricDef(label="Avg runtime", type="duration")
    total_blks_read = MetricDef(label="Blocks read", type="size")
    total_blks_hit = MetricDef(label="Blocks hit", type="size")
    total_blks_dirtied = MetricDef(label="Blocks dirtied", type="size")
    total_blks_written = MetricDef(label="Blocks written", type="size")
    total_temp_blks_written = MetricDef(label="Temp Blocks written", type="size")


class Totals(MetricGroupDef):
    avg_runtime = MetricDef(label="Total runtime", type="duration")
    total_blks_hit = MetricDef(label="Total hit", type="sizerate")
    total_blks_read = MetricDef(label="Total read", type="sizerate")
