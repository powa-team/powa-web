
require(['jquery',
        'foundation/foundation',
        'underscore',
        'backbone',
        'powa/views/DashboardView',
        'powa/models/Widget',
        'powa/models/Dashboard',
        'powa/models/DataSourceCollection',
        'powa/models/MetricGroup',
        'powa/models/ContentSource',
        'powa/utils/timeurls',
        'highlight',
        'powa/views/LineGraphView',
        'powa/views/BarGraphView',
        'powa/views/PieGraphView',
        'powa/views/GridView',
        'powa/views/ContentView',
        'powa/views/WizardView',
        'powa/models/Graph',
        'powa/models/Grid',
        'powa/models/Content',
        'powa/models/Wizard',
        'modernizr',
        'foundation/foundation.tab',
        'foundation/foundation.tooltip',
        'foundation/foundation.dropdown',
        'foundation/foundation.offcanvas',
        'foundation/foundation.topbar',
        'foundation/foundation.alert'],
        function($, Foundation, _, BackBone, DashboardView,
            Widget,
            Dashboard,
            DataSourceCollection,
            MetricGroup,
            ContentSource,
            timeurls,
            highlight) {

    $(function(){
        $(document).foundation({
            offcanvas: {
                open_method: 'overlap',
                close_on_click: true
            }
        });

        $('.side-nav a.close').click(function(){
            $('.off-canvas-wrap').foundation('offcanvas', 'toggle', 'offcanvas-overlap-right');
        });

        $('#menu-toggle').click(function(){
            $('.off-canvas-wrap').foundation('offcanvas', 'toggle', 'offcanvas-overlap-right');
        });

        var colors = ["#c05020", "#30c020", "#6060c0"];
        var ds = DataSourceCollection.get_instance();
        var picker = new timeurls({$el: $('#daterangepicker')});
        var dashboards = [];

        $('script[type="text/datasources"]').each(function(){
            var metric_groups = JSON.parse($(this).text());
            $.each(metric_groups, function(){
                try{
                    if(this.type == "metric_group"){
                        ds.add(MetricGroup.fromJSON(this));
                    } else if (this.type == "content") {
                        ds.add(ContentSource.fromJSON(this));
                    }
                }
                catch(e){
                    console.error("Could not instantiate metric group. Check the metric group definition");
                }

            });
        });

        $('.dashboard').each(function(){
            var widgets = new Backbone.Collection();
            var self = this;
            $(this).find('script[type="text/dashboard"]').each(function(){
                var dashboard = Widget.fromJSON(JSON.parse(this.text));
                var dashboardview = dashboard.makeView({picker: picker, el: self});
                dashboards.push(dashboard);
            });
        });
    });
    return {};
});
