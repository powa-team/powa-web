from powa.dashboards import (
    Dashboard, Grid,
    MetricGroupDef, MetricDef,
    DashboardPage)

class PgSettingsMetricGroup(MetricGroupDef):
    """
    Metric group for the pg_settings grid.
    """

    name = "pg_settings"
    xaxis = "setting_name"
    data_url = r"/config/pg_settings/"
    axis_type = "category"
    setting_value = MetricDef(label="Value", type="string")
    setting_unit = MetricDef(label="Unit", type="string")
    query = """
            SELECT name as setting_name, setting as setting_value, COALESCE(unit,'') AS setting_unit
            FROM pg_settings
            --WHERE name like 'powa%%'
            ORDER BY name"""

class PgExtensionsMetricGroup(MetricGroupDef):
    """
    Metric group for the pg_settings grid.
    """

    name = "pg_extensions"
    xaxis = "extname"
    data_url = r"/config/pg_extensions/"
    axis_type = "category"
    available = MetricDef(label="Extension available", type="bool")
    installed = MetricDef(label="Extension installed", type="bool")
    handled = MetricDef(label="Extension handled", type="bool")
    query = """
           SELECT DISTINCT s.extname,
             CASE WHEN avail.name IS NULL then false ELSE true END AS available,
             CASE WHEN ins.extname IS NULL then false ELSE true END AS installed,
             CASE WHEN f.module IS NULL then false ELSE true END AS handled
           FROM (SELECT 'pg_stat_statements' AS extname UNION SELECT 'pg_qualstats' UNION SELECT 'pg_stat_kcache') s
           LEFT JOIN pg_available_extensions avail on s.extname = avail.name
           LEFT JOIN pg_extension ins on s.extname = ins.extname
           LEFT JOIN powa_functions f ON s.extname = f.module
            """


class ConfigOverview(DashboardPage):
    """
    Dashboard page for configuration page.
    """

    base_url = r"/config/"

    datasources = [PgSettingsMetricGroup, PgExtensionsMetricGroup]

    dashboard = Dashboard(
        "Configuration overview",
         [[Grid("Extensions",
               columns=[{
                   "name": "extname",
                   "label": "Extensions",
                   "url_attr": "url"
               }],
               metrics=PgExtensionsMetricGroup.all()
          ),
          Grid("PostgreSQL settings",
               columns=[{
                   "name": "setting_name",
                   "label": "Setting",
                   "url_attr": "url"
               }],
               metrics=PgSettingsMetricGroup.all()
               )
         ]]
    )

    @classmethod
    def get_menutitle(cls, handler, params):
        return "Configuration overview"
