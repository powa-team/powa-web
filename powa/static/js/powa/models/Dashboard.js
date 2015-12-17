define([
        'backbone',
        'powa/models/DataSourceCollection',
        'powa/models/Content',
        'powa/models/Grid',
        'powa/models/Widget',
        'powa/models/Wizard',
        'powa/models/Graph',
        'powa/views/DashboardView'
], function(
            Backbone,
            DataSourceCollection,
            Content,
            Grid,
            Widget,
            Wizard,
            Graph,
            DashboardView){
    return Widget.extend({
        typname: "dashboard",
        initialize: function(){
            this.data_sources = DataSourceCollection.get_instance();
        },

        makeView: function(options){
            options.model = this;
            return new DashboardView(options);
        }

    }, {
        fromJSON: function(jsonobj){
                var widgets = new Backbone.Collection();
                var self = this;
                _.each(jsonobj.widgets, function(row, y){
                    _.each(row, function(widget, x){
                        var widgetmodel; 
                        widget.x = x;
                        widget.y = y;
                        widget.dashboard = self;
                        widgetmodel = Widget.fromJSON(widget);
                        widgetmodel.set("x", x);
                        widgetmodel.set("y",  y);
                        widgets.add(widgetmodel);
                    });
                });
            return new this({
                'title': jsonobj.title,
                'widgets': widgets});
        }
    });
});
