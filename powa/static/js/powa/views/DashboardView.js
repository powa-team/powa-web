define([
    'backbone',
    'powa/models/MetricGroupCollection',
    'powa/models/Graph',
    'powa/models/Grid',
    'powa/models/Metric',
    'powa/models/MetricGroup',
    'powa/models/MetricCollection',
    'powa/views/GraphView',
    'powa/views/GridView',
    'foundation-daterangepicker',
    'moment'
], function(Backbone, MetricGroupCollection, Graph, Grid, Metric, MetricGroup, MetricCollection, GraphView, GridView, daterangepicker, moment){
    return Backbone.View.extend({
        tagName: "div",
        events: {
            "daterangepicker.change .daterangepicker": "updatePeriod"
        },

        initialize: function(args){
            var self = this;
            this.widgets = args.widgets;
            this.metric_groups = args.metric_groups;
            this.$daterangepicker = this.$('[name="daterangepicker"]');
            this.$daterangepicker.daterangepicker({
                timePicker: true,
                timePicker12Hour: false,
                timePickerIncrement: 1,
                format: 'YYYY-MM-DD HH:mm',
                ranges: {
                    'hour': [moment().subtract('hour', 1), moment()],
                    'day': [moment().subtract('day', 1), moment()],
                    'week': [moment().subtract('week', 1), moment()],
                    'month': [moment().subtract('month', 1), moment()],
                }
            }, function(start_date, end_date){
                self.updatePeriod(start_date, end_date);
            });
            this.daterangepicker = this.$daterangepicker.data('daterangepicker');
            this.daterangepicker.hide();
            this.daterangepicker.container.removeClass('hide');
            this.$daterangepicker.on("apply.daterangepicker", function(){dashboard.updatePeriodFromDateRange.apply(dashboard, arguments)});
            this.views = [];
            this.layout();
            this.updatePeriod(moment().subtract('hour', 1), moment());
        },

        layout: function(){
            var maxy = this.widgets.max(function(wg){
                return wg.get("y");
            });
            for(var y = 0; y <= maxy.get("y"); y++){
                var newrow = $('<div>').addClass("row"),
                    rowwidgets = this.widgets.where({y: y});
                this.$('.widgets').append(newrow);
                var    len = 12 / rowwidgets.length;
                _.each(rowwidgets, function(widget) {
                    var widgetcontainer = $('<div>').addClass('widget columns large-' + len),
                        view;
                    newrow.append(widgetcontainer);
                    widget.set({
                        from_date: this.from_date,
                        to_date: this.to_date
                    });
                    view = this.makeView(widget);
                    view.from_date = this.from_date;
                    view.to_date = this.to_date;
                    this.views.push(view);
                    widgetcontainer.append(view.render().el);
                }, this);
            }
        },


        makeView: function(widget){
            if(widget.get("type") == "graph"){
                return new GraphView({model: widget});
            } else if (widget.get("type") == "grid"){
                return new GridView({model: widget});
            }
        },

        addWidget: function(graph){
            this.layout();
        },

        updatePeriod: function(startDate, endDate){
            this.from_date = startDate;
            this.to_date = endDate;
            _.each(this.views, function(widget){
                widget.showload();
            });
            this.metric_groups.each(function(metric_group){
                metric_group.update(startDate, endDate);
            });
        },

        updatePeriodFromDateRange: function(event, data){
            this.updatePeriod(data.startDate, data.endDate);
        }
    });
});
