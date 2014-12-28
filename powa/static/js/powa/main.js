define([
        'jquery',
        'underscore',
        'backbone',
        'foundation/foundation',
        'powa/views/DashboardView',
        'powa/models/Graph',
        'powa/models/Grid',
        'powa/models/Content',
        'powa/models/DataSourceCollection',
        'powa/models/MetricGroup',
        'powa/models/ContentSource',
        'modernizr',
        'foundation/foundation.tooltip'],
        function($, _, BackBone, Foundation, DashboardView,
            Graph,
            Grid,
            Content,
            DataSourceCollection,
            MetricGroup,
            ContentSource) {
    $(function(){
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
    var ds = DataSourceCollection.get_instance();
    $('script[type="text/datasources"]').each(function(){
        var metric_groups = JSON.parse($(this).text());
        $.each(metric_groups, function(){
            try{
                if(this.type == "metric_group"){
                    ds.add(MetricGroup.fromJSON(this));
                } else if (this.type == "contentsource") {
                    ds.add(ContentSource.fromJSON(this));
                }
            }
            catch(e){
                console.error("Could not instantiate metric group. Check the metric group definition");
            }

        });
    });

    $('#db_selector select').on("change", function(){
        $(this).parents("form").submit();
    });
    var $daterangepicker = $('#daterangepicker'),
        dashboards = [];
    $daterangepicker.daterangepicker({
                timePicker: true,
                timePicker12Hour: false,
                timePickerIncrement: 1,
                format: 'YYYY-MM-DD HH:mm',
                opens: "left",
                ranges: {
                    'hour': [moment().subtract('hour', 1), moment()],
                    'day': [moment().subtract('day', 1), moment()],
                    'week': [moment().subtract('week', 1), moment()],
                    'month': [moment().subtract('month', 1), moment()],
                }
            }, function(start_date, end_date){
                $.each(dashboards, function(){
                    this.updatePeriod(start_date, end_date);
                });
            });

    var daterangepicker = $daterangepicker.data('daterangepicker');
    daterangepicker.hide();
    daterangepicker.container.removeClass('hide');

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
        var dashboard = new DashboardView({el: this, widgets: widgets, data_sources:ds});
        dashboards.push(dashboard);
    });
    });
    return {};
});
