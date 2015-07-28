define(['backbone'], function(Backbone, Metric, MetricCollection){
    return Backbone.Model.extend({
        initialize: function(){
        },

        getUrl: function(from_date, to_date){
            var url = this.get("data_url"),
                params = {from: from_date.format("YYYY-MM-DD HH:mm:ssZZ"),
                          to: to_date.format("YYYY-MM-DD HH:mm:ssZZ")};
            return url + "?" + jQuery.param(params);
        }

    }, {
        fromJSON: function(jsonobj){
            return new this(jsonobj);
        }
    });
});
