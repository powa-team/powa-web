"""
Dashboard definition classes.

This module provides several classes to define a Dashboard.
"""

from powa.json import JSONizable
from powa.framework import AuthHandler
from powa.ui_modules import MenuEntry, GlobalMenu
from powa.compat import with_metaclass, classproperty, hybridmethod
from tornado.web import URLSpec
from operator import attrgetter
from collections import OrderedDict
from inspect import isfunction

GLOBAL_COUNTER = 0


class DashboardHandler(AuthHandler):
    """
    Handler for a specific dashboard
    """

    def initialize(self, template, params):
        self.template = template
        self.params = params

    def get(self, *args):
        params = OrderedDict(zip(self.params,
                                 args))
        param_rows = []
        for row in self.dashboard.widgets:
            param_row = []
            for widget in row:
                param_row.append(widget.parameterized_json(self, **params))
            param_rows.append(param_row)
        param_datasource = []
        for datasource in self.datasources:
            value = datasource.parameterized_json(self, **params)
            value['data_url'] = self.reverse_url(datasource.url_name,
                                                 *args)
            param_datasource.append(value)
        return self.render(self.template,
                           widgets=param_rows,
                           datasources=param_datasource,
                           title=self.dashboard.title % params)

    @property
    def database(self):
        params = dict(zip(self.params, self.path_args))
        return params.get("database", None)

    @property
    def menu(self):
        params = OrderedDict(zip(self.params, self.path_args))
        new_top_level = list(GlobalMenu)
        menu = self.get_menu(self, params)
        for i, child in enumerate(GlobalMenu):
            if child.url_name == menu.url_name:
                new_top_level[i] = menu
                break
        else:
            new_top_level.append(menu)
        return MenuEntry(None, None, None, new_top_level, active=True)


class MetricGroupHandler(AuthHandler):
    """
    Handler for a metric group.
    """

    def initialize(self, datasource, params):
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
        data = {"data": [self.process(val, **url_params) for val in values]}
        data = self.post_process(data, **url_params)
        self.render_json(data)

    def process(self, val, **kwargs):
        """
        Callback used to process each individual row fetched from the query.

        Arguments:
            handler (tornado.web.RequestHandler):
                the current request handler
            val (sqlalchemy.engine.result.RowProxy):
                the row to process
            kwargs (dict):
                the current url_parameters
        Returns:
            A dictionary containing the processed values.
        """
        return dict(val)

    def post_process(self, data, **kwargs):
        """
        Callback used to process the whole set of rows before returning
        it to the browser.

        Arguments:
            handler (tornado.web.RequestHandler):
                the current request handler
            val (sqlalchemy.engine.result.RowProxy):
                the row to process
            kwargs (dict):
                the current url_parameters
        Returns:
            A dictionary containing the processed values.
        """
        return data



class DataSource(JSONizable):
    """
    Base class for various datasources

    Attributes:
        datasource_handler_cls (type):
            a subclass of RequestHandler used to process this DataSource.

    """
    datasource_handler_cls = None
    data_url = None

    @classproperty
    def url_name(cls):
        """
        Returns the default url_name for this data source.
        """
        return "datasource_%s" % cls.__name__


    @classproperty
    def parameterized_json(cls, handler, **parms):
        return cls.to_json()



class Metric(JSONizable):
    """
    An indivudal Metric.
    A Metric is an abstraction for a series of data.

    Attributes:
        name: the name of the metric
        label: its label, as displayed in the ui
        type: a type of unit, as referenced in the widget using the type.
              See GraphView.js for example
    """

    def __init__(self, name, label=None, yaxis=None, **kwargs):
        self.name = name
        self.label = label or name.title()
        self.yaxis = yaxis or name
        self._group = None
        for key, value in kwargs.items():
            setattr(self, key, value)

    def bind(self, group):
        """
        Bind the metric to a metric group. Each metric belong to
        only one MetricGroup.
        """

        if self._group is not None:
            raise ValueError("Already bound to %s" % self._group)
        self._group = group

    def _fqn(self):
        """
        Return the fully qualified name of this metric.
        """
        return "%s.%s" % (self._group.name, self.name)


class Dashboard(JSONizable):
    """
    A Dashboard definition.

    Attributes:
        title (str):
            the dashboard title
        _widgets (list of list):
            A list of rows, with each row containing a list of widgets.
    """

    def __init__(self, title, widgets=None):
        self.title = title
        self._widgets = widgets or []
        self._validate_layout()

    def _validate_layout(self):
        """
        Validate that the layout is consistent.
        """
        if not isinstance(self._widgets, list):
            raise ValueError("Widgets must be a list of list of widgets")
        for row in self._widgets:
            if (12 % len(row)) != 0:
                raise ValueError(
                    "Each widget row length must be a "
                    "divisor of 12 (have: %d)" % len(row))

    @property
    def widgets(self):
        """
        Returns this dashboard widgets.
        """
        return self._widgets

    @widgets.setter
    def set_widgets(self, widgets):
        """
        Widgets setter.
        """
        self._validate_layout()
        self._widgets = widgets

    def to_json(self):
        return {'title': self.title,
                'widgets': self.widgets}


class Widget(JSONizable):
    """
    Base class for every Widget.
    """

    def parameterized_json(self, _, **params):
        base = params.copy()
        base.update(self.to_json())
        base["title"] = base["title"] % params
        return base


class ContentHandler(AuthHandler):
    """
    Base class for ContentHandlers.

    ContentHandler subclasses are generated on the fly by ContentWidgets,
    when they are registered.
    """

    def initialize(self, datasource=None, params=None):
        self.params = params


class ContentWidget(Widget, DataSource, AuthHandler):
    """
    A widget showing HTML fetched from the server.

    This widget acts as both a Widget and DataSource, since the Data used is
    simplistic.
    """

    datasource_handler_cls = ContentHandler

    def initialize(self, datasource=None, params=None):
        self.params = params


    @classmethod
    def to_json(cls):
        """
        to_json is an hybridmethod, the goal is to provide two different
        implementations when it is used as a class (DataSource) or as
        an instance (Widget).
        """
        return {
            'data_url': cls.data_url,
            'name': cls.__name__,
            'type': 'content',
            'content': cls.__name__,
            'title': cls.title
        }

    @classmethod
    def parameterized_json(cls,  _, **params):
        return cls.to_json()



class Grid(Widget):
    """
    A rich table Widget, backed by a BackGrid component.

    Attributes:
        columns (list):
            a list of column definitions, excluding metrics
        metrics (list):
            a list of metrics to be included as columns
    """

    def __init__(self, title, columns=None, metrics=None, **kwargs):
        self.title = title
        self.metrics = metrics or []
        self.columns = columns or []
        for key, value in kwargs.items():
            setattr(self, key, value)
        self._validate()

    def _validate(self):
        """
        Validate that the metrics are coherent.
        """
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
    """
    A widget backed by a Rickshaw graph.
    """

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
    """
    Base class for declarative classes.
    """

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        global GLOBAL_COUNTER
        self.kwargs.setdefault('_order', GLOBAL_COUNTER)
        GLOBAL_COUNTER += 1


class MetricDef(Declarative):
    """
    A metric definition.
    """
    _cls = Metric


class MetaMetricGroup(type, JSONizable):
    """
    Meta class for Metric Groups.
    This meta class parses its MetricDef attributes, and instantiates
    real Metrics from them.
    """

    def __new__(meta, name, bases, dct):
        dct['metrics'] = {}
        dct['_stubs'] = {}
        if not isinstance(dct.get('name', ''), str):
            raise ValueError("The metric group name must be of type str")
        for base in bases:
            if hasattr(base, '_stubs'):
                for key, stub in base._stubs.items():
                    dct[key] = stub.__class__(*stub.args,
                                              **stub.kwargs)
        for key, val in list(dct.items()):
            if isinstance(val, Declarative):
                dct['_stubs'][key] = val
                val.kwargs['name'] = key
                dct[key] = val = val._cls(*val.args, **val.kwargs)
            if isinstance(val, Metric):
                dct.pop(key)
                dct['metrics'][key] = val
        return super(MetaMetricGroup, meta).__new__(meta, name, bases, dct)


    def __init__(cls, name, bases, dct):
        for metric in dct.get("metrics").values():
            metric.bind(cls)
        super(MetaMetricGroup, cls).__init__(name, bases, dct)

    def __getattr__(cls, key):
        if key not in cls.metrics:
            raise AttributeError
        return cls.metrics.get(key)

    def __hasattr__(cls, key):
        return key in cls.metrics




class MetricGroupDef(with_metaclass(MetaMetricGroup, DataSource)):
    """
    Base class for MetricGroupDef.

    A MetricGroupDef provides syntactic sugar for instantiating MetricGroups.
    """
    _inst = None
    metrics = {}
    datasource_handler_cls = MetricGroupHandler

    @classmethod
    def to_json(cls):
        values = {key: val for key, val in cls.__dict__.items()
                if not key.startswith("_") and not isfunction(val)}
        values['type'] = 'metric_group'
        values.setdefault("xaxis", "ts")
        values['metrics'] = list(cls.metrics.values())
        values.pop("query")
        return values

    @classmethod
    def _get_metrics(cls, handler, **params):
        return cls.metrics

    @classmethod
    def parameterized_json(cls, handler, **params):
        base = cls.to_json()
        base["metrics"] = list(cls._get_metrics(handler, **params).values())
        return base


    @classmethod
    def all(cls):
        return sorted(cls.metrics.values(), key=attrgetter("_order"))

    @property
    def metrics(self):
        return self._metrics


class DashboardPage(object):
    """
    A Dashboard page ties together a set of datasources, and a dashboard.

    Attributes:
        template (str):
            the template to use to render the dashboard
        params (list):
            a list of parameter names mapped to groups in the url regexp
        base_url (str):
            the url to this page
        dashboard_handler_cls (RequestHandler):
            the RequestHandler class used to display this page
        datasources (list):
            the list of datasources to include in the page.
    """

    template = "fullpage_dashboard.html"
    params = []
    dashboard_handler_cls = DashboardHandler
    base_url = None
    datasources = []
    parent = None

    @classmethod
    def url_specs(cls):
        """
        Return the URLSpecs to be register on the application.
        This usually includes one URLSpec for the page itself, and one for
        each datasource.
        """

        url_specs = []
        url_specs.append(URLSpec(
            r"%s/" % cls.base_url.rstrip("/"),
            type(cls.__name__, (cls.dashboard_handler_cls, cls), {}),{
                "template": cls.template,
                "params": cls.params},
            name=cls.__name__))
        for datasource in cls.datasources:
            if datasource.data_url is None:
                raise KeyError("A Datasource must have a data_url: %s" %
                               datasource.__name__)
            url_specs.append(URLSpec(
                datasource.data_url,
                type(datasource.__name__, (datasource, datasource.datasource_handler_cls),
                    dict(datasource.__dict__)),
                {"datasource": datasource, "params": cls.params}, name=datasource.url_name))
        return url_specs

    @classmethod
    def get_menutitle(cls, handler, params):
        return cls.__name__

    @classmethod
    def get_childmenu(cls, handler, params):
        return []

    @classmethod
    def get_selfmenu(cls, handler, params):
        my_params = OrderedDict((key, params.get(key))
                                for key in cls.params)
        return MenuEntry(cls.get_menutitle(handler, params),
                         cls.__name__,
                         my_params)

    @classmethod
    def get_menu(cls, handler, params, parent=None):
        if cls.parent is not None:
            base = cls.parent.get_menu(handler, params)
            self_entry = base.findMenu(cls.__name__, params)
            if self_entry is None:
                self_entry = cls.get_selfmenu(handler, params)
                parent = base.findMenu(cls.parent.__name__, params)
                parent.children.append(self_entry)
        else:
            self_entry = base = cls.get_selfmenu(handler, params)
        self_entry.active = True
        self_entry.children.extend(cls.get_childmenu(handler, params))
        return base
