from powa.json import JSONizable, to_json
from abc import ABCMeta
from powa.framework import AuthHandler
from powa.compat import with_metaclass
from tornado.web import URLSpec
from operator import attrgetter

GLOBAL_COUNTER = 0

class MetricGroup(JSONizable):

    def __init__(self, name=None, query=None, data_url=None,
                 xaxis="ts", metrics=None, axis_type="time",
                 category_attr=None, **kwargs):
        self.name = name
        self.xaxis = xaxis
        self.data_url = data_url
        self.axis_type = axis_type
        self.metrics = metrics or {}
        self.category_attr = category_attr
        for key, metric in self.metrics.items():
            metric._bind(self)

    def to_json(self):
        vals = super(MetricGroup, self).to_json()
        vals['metrics'] = list(self.metrics.values())
        return vals


class Metric(JSONizable):

    def __init__(self, name, label=None, yaxis=None, **kwargs):
        self.name = name
        self.label = label or name.title()
        self.yaxis = yaxis or name
        self._group = None
        for key, value in kwargs.items():
            setattr(self, key, value)


    def _bind(self, group):
        if self._group is not None:
            raise ValueError("Already bound to %s" % self._group)
        self._group = group

    def _fqn(self):
        return "%s.%s" % (self._group.name, self.name)


class Dashboard(JSONizable):

    def __init__(self, title, widgets=None):
        self.title = title
        self._widgets = widgets or []
        self._validate_layout(self._widgets)


    def _validate_layout(self, widgets):
        if not isinstance(widgets, list):
            raise ValueError("Widgets must be a list of list of widgets")
        for row in widgets:
            if (12 % len(row)) != 0:
                raise ValueError(
                    "Each widget row length must be a "
                    "divisor of 12 (have: %d)" % len(row))

    @property
    def widgets(self):
        return self._widgets

    @widgets.setter
    def set_widgets(self, widgets):
       self._validate_layout(widgets)
       self._widgets = widgets

    def to_json(self):
        return {'title': self.title,
                'widgets': self.widgets}


class Widget(JSONizable):
    pass

class Grid(Widget):

    def __init__(self, title, metrics=None, **kwargs):
        self.title = title
        self.metrics = metrics or []
        for key, value in kwargs.items():
            setattr(self, key, value)

    def to_json(self):
        values = self.__dict__.copy()
        values['metrics'] = []
        values['type'] = 'grid'
        for metric in self.metrics:
            values['metrics'].append(metric._fqn())
        return values


class Graph(Widget):

    def __init__(self, title, grouper=None,
                 axistype="time",
                 metrics=None,
                 **kwargs):
        self.title = title
        self.grouper = grouper
        self.metrics = metrics or []
        self.axistype = "time"
        for key, value in kwargs.items():
            setattr(self, key, value)

    def _validate_axis(self, metrics):
        if len(metrics) == 0:
            return
        axis_type = metrics[0].axis_type
        for metric in metrics:
            if metric.axis_type != axis_type:
                raise ValueError(
                    "Some metrics do not have the same x-axis type!")

    def to_json(self):
        values = self.__dict__.copy()
        values['metrics'] = []
        values['type'] = 'graph'
        for metric in self.metrics:
            values['metrics'].append(metric._fqn())
        return values


class DashboardHandler(AuthHandler):
    """
    Handler for a specific dashboard
    """

    def initialize(self, template, dashboardpage, params):
        self.template = template
        self.dashboardpage = dashboardpage
        self.params = params

    def get(self, *args):
        params = dict(zip(self.dashboardpage.params,
                          args))
        param_rows = []
        for row in self.dashboardpage.dashboard.widgets:
            param_row = []
            for widget in row:
                base = params.copy()
                base.update(widget.to_json())
                base["title"] = base["title"] % params
                param_row.append(base)
            param_rows.append(param_row)
        param_metric = []
        for metric in self.dashboardpage.metric_groups:
            value = metric.to_json()
            value['data_url'] = self.reverse_url("metric_%s" % metric.__name__,
                                                 *args)
            param_metric.append(value)
        return self.render(self.template,
                           widgets=param_rows,
                           metrics=param_metric,
                           title=self.dashboardpage.dashboard.title % params)

class MetricGroupHandler(AuthHandler):
    """
    Handler for a metric group.
    """

    def initialize(self, metric_group, params):
        self.query = metric_group.query
        self.params = params

    def get(self, *params):
        url_params = dict(zip(self.params, params))
        url_query_params = {
            key: value[0].decode('utf8')
            for key, value
            in self.request.arguments.items()}
        url_params.update(url_query_params)
        query = self.query
        values = self.execute(query, params=url_params)
        data = {"data": [dict(val) for val in values]}
        self.render_json(data)


class Declarative(object):

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        global GLOBAL_COUNTER
        self.kwargs['order'] = GLOBAL_COUNTER
        GLOBAL_COUNTER += 1


class MetricDef(Declarative):
    _cls = Metric



class MetaMetricGroup(type, JSONizable):


    def __new__(meta, name, bases, dct):
        dct['metrics'] = {}
        dct['stubs'] = {}
        for base in bases:
            if hasattr(base, 'stubs'):
                for key, stub in base.stubs.items():
                    dct[key] = stub.__class__(*stub.args,
                                              **stub.kwargs)
        for key, val in list(dct.items()):
            if isinstance(val, Declarative):
                dct['stubs'][key] = val
                val.kwargs['name'] = key
                dct[key] = val = val._cls(*val.args, **val.kwargs)
            if isinstance(val, Metric):
                dct.pop(key)
                dct['metrics'][key] = val
        if dct['metrics']:
            dct['_inst'] = MetricGroup(
                **{key: val
                   for key, val in dct.items()
                   if not isinstance(val, classmethod) and not key.startswith('__')})
        return super(MetaMetricGroup, meta).__new__(meta, name, bases, dct)

    def __getattr__(cls, key):
        return cls.metrics[key]


class MetricGroupDef(with_metaclass(MetaMetricGroup, MetricGroup)):
    _cls = MetricGroup

    @classmethod
    def to_json(cls):
        return cls._inst.to_json()

    @classmethod
    def all(cls):
        return sorted(cls.metrics.values(), key=attrgetter("order"))


class DashboardPage(object):

    template = "fullpage_dashboard.html"
    params = []

    @classmethod
    def url_specs(cls):
        url_specs = []
        url_specs.append(URLSpec(
            r"%s/" % cls.base_url.rstrip("/"),
            DashboardHandler, {
                "dashboardpage": cls,
                "template": cls.template,
                "params": cls.params},
            name=cls.__name__))
        for metric_group in cls.metric_groups:
            url_specs.append(URLSpec(
                metric_group.data_url,
                MetricGroupHandler, {
                    "metric_group": metric_group,
                    "params": cls.params
                }, name="metric_%s" % metric_group.__name__))
        return url_specs
