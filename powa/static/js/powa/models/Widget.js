define(['backbone'], function(Backbone){
    var registry = {};
    return Backbone.Model.extend({
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
        extend: function(instanceattrs, clsattrs){
            var newcls = Backbone.Model.extend.apply(this, [instanceattrs, clsattrs]);
            registry[newcls.prototype.typname] = newcls;
            return newcls;
        },
        fromJSON: function(jsonobj){
            var cls = registry[jsonobj.type];
            if(cls == undefined){
                throw "Unknown widget type: " + jsonobj.type;
            }
            return cls.fromJSON(jsonobj);
        }
    });
});
