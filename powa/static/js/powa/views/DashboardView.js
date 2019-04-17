define([
    'jquery',
    'foundation/foundation.equalizer',
    'backbone',
    'powa/views/WidgetView',
    'foundation-daterangepicker',
    'moment',
    'powa/utils/timeurls'
], function(jquery, foundation, Backbone, WidgetView, daterangepicker,
    moment, timeurls){
    return WidgetView.extend({
        tagName: "div",
        typname: "dashboard",

        initialize: function(args){
            var self = this;
            this.dashboard = args.model;
            this.data_sources = args.data_sources;
            this.views = [];
            this.render();
        },

        render: function(){
            var wc = this.$el;
            wc.html("");
            var widgets = this.dashboard.get("widgets");
            var maxy = widgets.max(function(wg){
                return wg.get("y");
            });
            this.views = [];
            for(var y = 0; y <= maxy.get("y"); y++){
                var newrow = $('<div>').addClass("row"),
                    rowwidgets = widgets.where({y: y});
                if(rowwidgets.length > 1){
                    newrow.attr("data-equalizer", "");
                }
                wc.append(newrow);
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
            return this;
        },

        show: function(){
            _.each(this.views, function(view){
                view.show();
            });
        },

        postRender: function(){
            this.$el.foundation();
        },

        makeView: function(widget){
            return WidgetView.makeView(widget);
        },

        addWidget: function(graph){
            this.layout();
        },

        refreshSources: function(startDate, endDate){
          var self = this;
            this.dashboard.data_sources.each(function(data_source){
                if(data_source.get("enabled") != false){
                    data_source.update(startDate, endDate);
                }
            });

            // display config changes if URL was provided
            raw = $('script[type="text/datasource_timeline"]').first();
            url = JSON.parse($(raw).text());
            if (url !== undefined && url !== null) {
              var params = {from: startDate.format("YYYY-MM-DD HH:mm:ssZZ"),
                            to: endDate.format("YYYY-MM-DD HH:mm:ssZZ")};
              url += "?" + jQuery.param(params);
              $.ajax({
                  url: url,
                  type: 'GET'
              }).done(function(changes) {
                self.dashboard.data_sources.each(function(data_source){
                    if(data_source.get("enabled") != false){
                      data_source.update_timeline(changes["data"]);
                    }
                });
              });
            }
            this.updatePeriod(startDate, endDate);
        },

        zoomIn: function(startDate, endDate){
            _.each(this.views, function(widget){
                widget.zoomIn(startDate, endDate);
            }, this);
            this.refreshSources(startDate, endDate);
            this.trigger("dashboard:updatePeriod", startDate, endDate);
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
        },

    });
});
