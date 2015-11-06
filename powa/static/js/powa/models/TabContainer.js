define(['backbone',
        'powa/models/Widget',
        'powa/models/DataSourceCollection'],
function(Backbone, Widget, DataSourceCollection){
    return Widget.extend({
        typname: "tabcontainer",
        initialize: function(args){
            this.tabs = args.tabs;
            this.title = args.title;
        }

    }, {
        fromJSON: function(jsonobj){
                var tabs = new Backbone.Collection();
                var self = this;
                _.each(jsonobj.tabs, function(row, y){
                    _.each(row, function(widget, x){
                        widget.x = x;
                        widget.y = y;
                        widgets.add(Widget.fromJSON(widget));
                    });
                });
            return new this({
                'title': jsonobj.title,
                'tabs': tabs});
        }

    });
});
