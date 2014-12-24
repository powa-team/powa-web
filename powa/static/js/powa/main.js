define([
        'jquery',
        'underscore',
        'backbone',
        'foundation/foundation',
        'powa/views/DashboardView',
        'powa/models/Graph',
        'powa/models/Grid',
        'powa/models/MetricGroupCollection',
        'powa/models/MetricGroup'],
        function($, _, BackBone, foundation, DashboardView,
            Graph,
            Grid,
            MetricGroupCollection,
            MetricGroup) {
    $(document).foundation();
    var aggregates = {
        sum: function(){
            var total = 0;
            $.each(arguments, function(){
                total += this;
            });
            return total;
        }
    }

    var colors = ["#c05020", "#30c020", "#6060c0"];
    var mg = MetricGroupCollection.get_instance();
    $('script[type="text/metric_groups"]').each(function(){
        var metric_groups = JSON.parse($(this).text());
        $.each(metric_groups, function(){
            mg.add(MetricGroup.fromJSON(this));
        });
    });


    $('#db_selector select').on("change", function(){
        $(this).parents("form").submit();
    });

    $('.dashboard').each(function(){
        var widgets = new Backbone.Collection();
        $(this).find('script[type="text/dashboard"]').each(function(){
            var raw_widgets = JSON.parse($(this).text());
            $.each(raw_widgets, function(y){
                $.each(this, function(x){
                    this.x = x;
                    this.y = y;
                    if(this.type == "graph"){
                        widgets.add(Graph.fromJSON(this));
                    } else if (this.type == "grid") {
                        widgets.add(Grid.fromJSON(this));
                    }
                });
            });
        });
        var dashboard = new DashboardView({el: this, widgets: widgets, metric_groups: mg});
    });
    return {};
});
