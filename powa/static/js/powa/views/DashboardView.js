define([
    'jquery',
    'foundation/foundation.equalizer',
    'backbone',
    'powa/views/LineGraphView',
    'powa/views/BarGraphView',
    'powa/views/PieGraphView',
    'powa/views/GridView',
    'powa/views/ContentView',
    'foundation-daterangepicker',
    'moment',
    'powa/utils/timeurls'
], function(jquery, foundation, Backbone, LineGraphView, BarGraphView,
    PieGraphView,
    GridView, ContentView, daterangepicker,
    moment, timeurls){
    return Backbone.View.extend({
        tagName: "div",

        initialize: function(args){
            var self = this;
            this.widgets = args.widgets;
            this.data_sources = args.data_sources;
            this.views = [];
            this.layout();
            this.picker = args.picker;
            this.listenTo(this.picker, "pickerChanged", this.updatePeriod, this);
            this.updatePeriod(this.picker.start_date, this.picker.end_date);
        },

        layout: function(){
            var maxy = this.widgets.max(function(wg){
                return wg.get("y");
            });
            for(var y = 0; y <= maxy.get("y"); y++){
                var newrow = $('<div>').addClass("row"),
                    rowwidgets = this.widgets.where({y: y});
                if(rowwidgets.length > 1){
                    newrow.attr("data-equalizer", "");
                }
                this.$('.widgets').append(newrow);
                var    len = 12 / rowwidgets.length;
                _.each(rowwidgets, function(widget) {
                    var panel = $('<div>').addClass('widget columns large-' + len),
                        widgetcontainer = $('<div>').addClass('widget panel').attr("data-equalizer-watch", ""),
                        view;
                    newrow.append(panel);
                    panel.append(widgetcontainer);
                    widget.set({
                        from_date: this.from_date,
                        to_date: this.to_date
                    });
                    try{
                        view = this.makeView(widget);
                        view.from_date = this.from_date;
                        view.to_date = this.to_date;
                        this.listenTo(view, "widget:update", this.postRender, this);
                        this.listenTo(view, "widget:zoomin", this.zoomIn, this);
                        this.listenTo(view, "widget:updateperiod", this.updatePeriod, this);
                        widgetcontainer.append(view.render().el);
                        this.views.push(view);
                    } catch(e) {
                        console.error("Could not instantiate widget " + widget.get("title"), e);
                        return;
                    }
                }, this);
            }
            this.$el.foundation('equalizer', 'reflow');
        },

        postRender: function(){
            this.$el.foundation();
            this.picker.updateUrls(this.from_date, this.to_date);
        },

        makeView: function(widget){
            // TODO: refactor this abomination
            if(widget.get("type") == "graph"){
                var renderer = widget.get("renderer") || "line";
                if(renderer == "line"){
                    return new LineGraphView({model: widget});
                }
                if(renderer == "bar"){
                    return new BarGraphView({model: widget});
                }
                if(renderer == "pie"){
                    return new PieGraphView({model: widget});
                }
            } else if (widget.get("type") == "grid"){
                return new GridView({model: widget});
            } else if (widget.get("type") == "content"){
                return new ContentView({model: widget});
            }
        },

        addWidget: function(graph){
            this.layout();
        },

        refreshSources: function(startDate, endDate){
            this.data_sources.each(function(data_source){
                data_source.update(startDate, endDate);
            });
        },

        zoomIn: function(startDate, endDate){
            _.each(this.views, function(widget){
                widget.zoomIn(startDate, endDate);
            }, this);
            this.refreshSources(startDate, endDate);
        },

        updatePeriod: function(startDate, endDate){
            var self = this;
            if(startDate.isValid()){
                this.from_date = startDate;
            }
            if(endDate.isValid()){
                this.to_date = endDate;
            }
            _.each(this.views, function(widget){
                widget.updatePeriod(this.from_date, this.to_date);
            }, this);
            this.refreshSources(this.from_date, this.to_date);
        },

    });
});
