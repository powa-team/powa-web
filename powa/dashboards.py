from powa.json import JSONizable, to_json
from abc import ABCMeta
from powa.framework import AuthHandler
from powa.compat import with_metaclass, classproperty, hybridmethod
from tornado.web import URLSpec
from operator import attrgetter
from collections import OrderedDict

GLOBAL_COUNTER = 0


class DashboardHandler(AuthHandler):
    """
    Handler for a specific dashboard
    """

    def initialize(self, template, dashboardpage, params):
        self.template = template
        self.dashboardpage = dashboardpage
        self.params = params

    def get(self, *args):
        params = OrderedDict(zip(self.dashboardpage.params,
                          args))
        param_rows = []
        for row in self.dashboardpage.dashboard.widgets:
            param_row = []
            for widget in row:
                param_row.append(widget.parameterized_json(self, **params))
            param_rows.append(param_row)
        param_datasource = []
        for datasource in self.dashboardpage.datasources:
            value = datasource.to_json()
            value['data_url'] = self.reverse_url(datasource.url_name,
                                                 *args)
            param_datasource.append(value)
        return self.render(self.template,
                           widgets=param_rows,
                           datasources=param_datasource,
                           title=self.dashboardpage.dashboard.title % params)

    @property
    def database(self):
        params = dict(zip(self.params, self.path_args))
        return params.get("database", None)

class MetricGroupHandler(AuthHandler):
    """
    Handler for a metric group.
    """

    def initialize(self, datasource, params):
        self.query = datasource.query
        self.params = params
        self.metric_group = datasource

    def get(self, *params):
        url_params = dict(zip(self.params, params))
        url_query_params = {
            key: value[0].decode('utf8')
            for key, value
            in self.request.arguments.items()}
        url_params.update(url_query_params)
        query = self.query
        values = self.execute(query, params=url_params)
        data = {"data": [self.metric_group.process(self, val,
                                                   **url_params) for val in values]}
        self.render_json(data)




class DataSource(JSONizable):

    def __init__(self, name=None, query=None, data_url=None):
        self.name = name
        self._query = query
        self.data_url = data_url

    @classproperty
    def url_name(cls):
        return "datasource_%s" % cls.__name__


class MetricGroup(DataSource):

    datasource_handler_cls = MetricGroupHandler

    def __init__(self, name=None, query=None, data_url=None,
                 xaxis="ts", metrics=None, axis_type="time",
                 category_attr=None, **kwargs):
        super(MetricGroup, self).__init__(name, query, data_url)
        self.xaxis = xaxis
        self.axis_type = axis_type
        self.metrics = metrics or {}
        self.category_attr = category_attr
        for key, metric in self.metrics.items():
            metric._bind(self)

    def to_json(self):
        vals = super(MetricGroup, self).to_json()
        vals['metrics'] = list(self.metrics.values())
        vals['type'] = 'metric_group'
        return vals

    @classmethod
    def process(cls, handler, val, **kwargs):
        return dict(val)


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

    def parameterized_json(self, handler, **params):
        base = params.copy()
        base.update(self.to_json())
        base["title"] = base["title"] % params
        return base


class ContentHandler(object):

    def initialize(self, datasource=None, params=None):
        self.params = params

class ContentWidget(Widget, DataSource):


    def __init__(self, title, content=None, **kwargs):
        self.title = title
        self.content = content
        super(ContentWidget, self).__init__(title, content, **kwargs)


    @classproperty
    def datasource_handler_cls(cls):
        return type("%sHandler" % cls.__name__,
                    (ContentHandler, AuthHandler,), dict(cls.__dict__))


    @hybridmethod
    def to_json(cls):
        return {
            'data_url': cls.data_url,
            'name': cls.__name__,
            'type': 'contentsource'
        }

    def initialize(self, datasource=None, params=None):
        self.params = params

    @to_json.instance_method
    def to_json(self):
        values = {}
        values['title'] = self.title
        values['type'] = 'content'
        values['content'] = self.__class__.__name__
        return values


class Grid(Widget):

    def __init__(self, title, columns=None, metrics=None, **kwargs):
        self.title = title
        self.metrics = metrics or []
        self.columns = columns or []
        for key, value in kwargs.items():
            setattr(self, key, value)
        self._validate()

    def _validate(self):
        if len(self.metrics) > 0:
            mg1 = self.metrics[0]._group
            if any(m._group != mg1 for m in self.metrics):
                raise ValueError(
                    "A grid is not allowed to have metrics from different "
                    "groups. (title: %s)" % self.title)


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


class Declarative(object):

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        global GLOBAL_COUNTER
        self.kwargs.setdefault('_order', GLOBAL_COUNTER)
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
        return sorted(cls.metrics.values(), key=attrgetter("_order"))


class DashboardPage(object):

    template = "fullpage_dashboard.html"
    params = []
    datasource_handler_cls = MetricGroupHandler
    dashboard_handler_cls = DashboardHandler

    @classmethod
    def url_specs(cls):
        url_specs = []
        url_specs.append(URLSpec(
            r"%s/" % cls.base_url.rstrip("/"),
            cls.dashboard_handler_cls, {
                "dashboardpage": cls,
                "template": cls.template,
                "params": cls.params},
            name=cls.__name__))
        for datasource in cls.datasources:
            url_specs.append(URLSpec(
                datasource.data_url,
                datasource.datasource_handler_cls, {
                    "datasource": datasource,
                    "params": cls.params
                }, name=datasource.url_name))
        return url_specs
