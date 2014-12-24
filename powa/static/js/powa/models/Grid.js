define(['backbone',  'powa/models/MetricGroupCollection', 'powa/models/MetricCollection',
        'backbone-pageable'
],
        function(Backbone, MetricGroupCollection, MetricCollection){
    return Backbone.Model.extend({

        initialize: function(){
            var self = this;
            this.set("collection", new Backbone.PageableCollection());
            this.listenTo(this.get("common_group"), "metricgroup:dataload", this.update);
        },

        update: function(data){
            this.get("collection").reset(data);
            this.trigger("grid:needrefresh");
        }


    }, {
        fromJSON: function(jsonobj){
            var group = MetricGroupCollection.get_instance(),
                metrics = jsonobj.metrics.map(function(metric){
                var splittedname = metric.split(".");
                var common_group = group.findWhere({name: splittedname[0]});
                jsonobj.common_group = common_group;
                return common_group.get("metrics")
                        .findWhere({name: splittedname[1]});
            });
            jsonobj.metrics = new MetricCollection(metrics);
            return new this(jsonobj);
        }
    });
});
