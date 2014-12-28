define(['backbone', 'powa/models/DataSourceCollection'], function(Backbone, DataSourceCollection){
    return Backbone.Model.extend({
        initialize: function(){
            this.listenTo(this.get("contentsource"), "contentsource:dataload", this.update);
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
