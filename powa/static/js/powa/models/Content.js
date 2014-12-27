define(['backbone'], function(Backbone){
    return Backbone.Model.extend({
    }, {
        fromJSON: function(jsonobj){
            return new this(jsonobj);
        }
    });
});
