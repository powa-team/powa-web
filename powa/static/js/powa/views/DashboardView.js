define([
    'backbone',
    'powa/views/GraphView',
    'powa/views/GridView',
    'powa/views/ContentView',
    'foundation-daterangepicker',
    'moment',
    'jquery',
    'foundation'
], function(Backbone, GraphView, GridView, ContentView, daterangepicker, moment, foundation){
    return Backbone.View.extend({
        tagName: "div",

        initialize: function(args){
            var self = this;
            this.widgets = args.widgets;
            this.data_sources = args.data_sources;
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
                newrow.attr("data-equalizer", "");
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
                        this.listenTo(view, "widget:update", function(){
                            this.$el.foundation('equalizer', 'reflow');
                        }, this);
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


        makeView: function(widget){
            if(widget.get("type") == "graph"){
                return new GraphView({model: widget});
            } else if (widget.get("type") == "grid"){
                return new GridView({model: widget});
            } else if (widget.get("type") == "content"){
                return new ContentView({model: widget});
            }
        },

        addWidget: function(graph){
            this.layout();
        },

        updatePeriod: function(startDate, endDate){
            this.from_date = startDate;
            this.to_date = endDate;
            _.each(this.views, function(widget){
                widget.from_date = this.from_date;
                widget.to_date = this.to_date;
                widget.showload();
            }, this);
            this.data_sources.each(function(data_source){
                data_source.update(startDate, endDate);
            });
        },

    });
});
