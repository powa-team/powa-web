define(['backbone'], function(Backbone){
    return Backbone.Model.extend({

        initialize: function(){
            this.label_template = _.template(this.get("label"));
        }
    }, {
        fromJSON: function(jsonobj){
            return new this(jsonobj);
        }
    });
});
