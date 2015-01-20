require(['jquery',
        'foundation/foundation',
        'underscore',
        'backbone',
        'powa/views/DashboardView',
        'powa/models/Graph',
        'powa/models/Grid',
        'powa/models/Content',
        'powa/models/DataSourceCollection',
        'powa/models/MetricGroup',
        'powa/models/ContentSource',
        'powa/utils/timeurls',
        'highlight',
        'modernizr',
        'foundation/foundation.tooltip',
        'foundation/foundation.dropdown',
        'foundation/foundation.alert'],
        function($, Foundation, _, BackBone, DashboardView,
            Graph,
            Grid,
            Content,
            DataSourceCollection,
            MetricGroup,
            ContentSource,
            timeurls,
            highlight) {
    $(function(){
        $(document).foundation();
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
            $(this).find('script[type="text/dashboard"]').each(function(){
                try{
                var raw_widgets = JSON.parse($(this).text());
                $.each(raw_widgets, function(y){
                    $.each(this, function(x){
                        this.x = x;
                        this.y = y;
                        if(this.type == "graph"){
                            widgets.add(Graph.fromJSON(this));
                        } else if (this.type == "grid") {
                            widgets.add(Grid.fromJSON(this));
                        } else if (this.type == "content") {
                            widgets.add(Content.fromJSON(this));
                        }
                    });
                });
                } catch(e){
                    console.error("Could not instantiate widgets. Check the dashboard definition");
                    console.error(e);
                }
            });
            var dashboard = new DashboardView({el: this, widgets: widgets, data_sources:ds, picker: picker});
            dashboards.push(dashboard);
        });
    });
    return {};
});
