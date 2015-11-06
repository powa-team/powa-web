define(['backbone',
        'powa/models/Widget',
        'powa/models/DataSourceCollection'],
function(Backbone, Widget, DataSourceCollection){
    return Widget.extend({
        typname: "content",
        initialize: function(){
            this.listenTo(this.get("contentsource"), "contentsource:dataload", this.update);
            this.listenTo(this.get("contentsource"), "contentsource:dataload-failed", function(message){
              this.trigger("widget:dataload-failed", message);
            });
        },
        update: function(content){
            this.trigger("widget:needrefresh", content);
        }

    }, {
        fromJSON: function(jsonobj){
            var group = DataSourceCollection.get_instance();
            jsonobj.contentsource = group.findWhere({name: jsonobj.content});
            if(jsonobj.contentsource === undefined){
                throw ("The content source could not be found.");
            }
            return new this(jsonobj);
        }
    });
});
