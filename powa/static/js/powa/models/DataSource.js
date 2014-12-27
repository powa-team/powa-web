define(['backbone'], function(Backbone, Metric, MetricCollection){
    return Backbone.Model.extend({
        initialize: function(){
        }
    }, {
        fromJSON: function(jsonobj){
            return new this(jsonobj);
        }
    });
});
