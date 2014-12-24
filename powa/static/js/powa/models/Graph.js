define(['backbone', 'powa/models/MetricGroupCollection', 'powa/models/MetricCollection'],
        function(Backbone, MetricGroupCollection, MetricCollection){
    return Backbone.Model.extend({

        initialize: function(){
            var self = this;
            this.listenTo(this.get("metrics"), "change:series", self.update);
        },

        update: function(){
            var new_series = [];
            var self = this;
            console.log("UPDATE?");
            self.get("metrics").each(function(metric){
                var series = metric.get("series");
                if(series != undefined){
                    $.each(series, function(key, serie){
                        var new_serie = $.extend({}, serie, metric.attributes);
                        new_series.push(new_serie);
                    });
                }
            });
            this.trigger("graph:needrefresh", new_series);
        }
    }, {
        fromJSON: function(jsonobj){
            var group = MetricGroupCollection.get_instance(),
                metrics = jsonobj.metrics.map(function(metric){
                var splittedname = metric.split(".");
                return group.findWhere({name: splittedname[0]})
                        .get("metrics")
                        .findWhere({name: splittedname[1]});
            });
            jsonobj.metrics = new MetricCollection(metrics);
            return new this(jsonobj);
        }
    });
});
