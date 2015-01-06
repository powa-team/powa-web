define(['backbone'], function(Backbone){
    return Backbone.Model.extend({

        initialize: function(){
            this.label_template = _.template(this.get("label"));
            var type = this.get("type");
            if(type === undefined){
                this.set("type", "number");
            }
        }
    }, {
        fromJSON: function(jsonobj){
            return new this(jsonobj);
        }
    });
});
