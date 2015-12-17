define(['backbone',
        'powa/models/Widget',
        'powa/models/DataSourceCollection',
        'powa/views/TabView'],
function(Backbone, Widget, DataSourceCollection, TabView){
    return Widget.extend({
        typname: "tabcontainer",
        initialize: function(args){
            this.tabs = args.tabs;
            this.title = args.title;
        },

        makeView: function(options){
            options.model = this;
            return new TabView(options);
        }

    }, {
        fromJSON: function(jsonobj){
                var tabs = new Backbone.Collection();
                var self = this;
                _.each(jsonobj.tabs, function(widget, idx){
                    tabs.add(Widget.fromJSON(widget));
                });
            return new this({
                'title': jsonobj.title,
                'tabs': tabs});
        }

    });
});
