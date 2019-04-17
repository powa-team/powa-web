define(['backbone', 'powa/models/DataSourceCollection', 'powa/models/MetricCollection',
        'powa/models/Widget'],
        function(Backbone, DataSourceCollection, MetricCollection, Widget){
    return Widget.extend({
        typname: "graph",
        initialize: function(){
            var self = this;
            this.hasloading = 0;
            this.listenTo(this.get("metrics"), "change:series", self.update);
            this.listenTo(this.get("metrics"), "metric:configchanges", self.configchanges);
            this.listenTo(this.get("metrics"), "metric:startload", function(){self.hasloading +=1});
        },

        update: function(){
            var new_series = [];
            var self = this;
            self.hasloading -= 1;
            if(self.hasloading != 0){
                return;
            }
            self.get("metrics").each(function(metric){
                var series = metric.get("series");
                if(series != undefined){
                    $.each(series, function(key, serie){
                        var new_serie = $.extend({}, metric.attributes, serie);
                        new_series.push(new_serie);
                    });
                }
            });
            this.trigger("widget:needrefresh", new_series);
        },

        configchanges: function(changes) {
          this.trigger("widget:configchanges", changes);
        }
    }, {
        fromJSON: function(jsonobj){
            var ds = DataSourceCollection.get_instance(),
                metrics = jsonobj.metrics.map(function(metric){
                    var metric,
                        splittedname = metric.split("."),
                        group = ds.findWhere({name: splittedname[0]});
                    if(group === undefined){
                        throw ("The metric group " + splittedname[0] + " could not be found.");
                    }
                    metric = group.get("metrics").findWhere({name: splittedname[1]});
                    if (metric === undefined){
                        throw("The metric " + splittedname[1] + " could not be found in group " + splittedname[1]);
                    }
                    return metric
                });
            jsonobj.metrics = new MetricCollection(metrics);
            return new this(jsonobj);
        }
    });
});
