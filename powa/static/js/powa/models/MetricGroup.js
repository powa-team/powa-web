define(['backbone', 'powa/models/DataSource', 'powa/models/Metric', 'powa/models/MetricCollection'], function(Backbone, DataSource Metric, MetricCollection){
    return DataSource.extend({

        initialize: function(){

        },

        getUrl: function(from_date, to_date){
            var url = this.get("data_url"),
                params = {from: from_date.format("YYYY-MM-DD HH:mm:ssZZ"),
                          to: to_date.format("YYYY-MM-DD HH:mm:ssZZ")};
            return url + "?" + jQuery.param(params);
        },


        update: function(from_date, to_date){
            var grouper = this.get('grouper', null),
                self = this,
                xaxis = this.get("xaxis");

            $.ajax({
                url: this.getUrl(from_date, to_date),
                type: 'GET'
            }).done(function (response) {
                var series_by_metric = {}
                self.get("metrics").each(function(metric){
                    series_by_metric[metric.get("name")] = {};
                });
                self.trigger("metricgroup:dataload", response.data);
                $.each(response.data, function(){
                    var row = this,
                        group = this[grouper] || "";
                    self.get("metrics").each(function(metric){
                        var series = series_by_metric[metric.get("name")],
                            current_group = series[group];
                        if(current_group === undefined){
                            current_group = series[group] = {
                                metric: metric,
                                id: metric.get("name") + group,
                                name: metric.get("label") + group,
                                label: metric.label_template(),
                                data: []
                            }
                        }
                        current_group.data.push({x: row[xaxis], y: row[metric.get("yaxis")]});
                    });
                });
                self.get("metrics").each(function(metric){
                    var series = series_by_metric[metric.get("name")];
                    metric.set("series", series);
                });
            });
        }

    }, {
        fromJSON: function(jsonobj){
            var metrics = jsonobj.metrics.map(function(metricobj){
                return Metric.fromJSON(metricobj);
            });
            jsonobj.metrics = new MetricCollection(metrics);
            return new this(jsonobj);
        }
    });
});
