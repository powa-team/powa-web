define(['backbone',
        'powa/models/Widget',
        'powa/models/DataSourceCollection'],
function(Backbone, Widget, DataSourceCollection){
    return Widget.extend({
        typname: "panel",
        initialize: function(args){
            this.title = args.title;
            this.widget = args.widget:
        }
    }, {
        fromJSON: function(jsonobj){
            return new this({
                title: jsonobj.title,
                widget: Widget.fromJSON(jsonobj.widget);
            });
        }
    });
});


