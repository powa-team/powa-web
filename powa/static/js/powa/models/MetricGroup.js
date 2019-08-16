define([
        'backbone',
        'powa/models/DataSource',
        'powa/models/Metric',
        'powa/models/MetricCollection',
        'powa/utils/message'],
        function(Backbone, DataSource, Metric, MetricCollection, Message){
    return DataSource.extend({

        initialize: function(){

        },

        update: function(from_date, to_date){
            var grouper = this.get('grouper', null),
                self = this,
                xaxis = this.get("xaxis");
            this.trigger("metricgroup:startload");
            self.get("metrics").each(function(metric){
                metric.trigger("metric:startload");
            });

            $.ajax({
                url: this.getUrl(from_date, to_date),
                type: 'GET'
            }).done(function (response) {
                var series_by_metric = {}

                self.get("metrics").each(function(metric){
                    series_by_metric[metric.get("name")] = {};
                });

                self.trigger("metricgroup:dataload", response.data, from_date, to_date);

                if (response.messages !== undefined) {
                  $.each(response.messages, function(level, arr){
                      $.each(arr, function(i) {
                        msg = Message.add_message(level, arr[i]);
                        $("#messages").append(msg);
                      })
                  })
                }

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
                                name: metric.label_template({group: group}),
                                data: []
                            }
                        }
                        if(row[xaxis] === undefined){
                            throw "Data is lacking for xaxis. Did you include " + xaxis + " column in your query ?";
                        }
                        current_group.data.push($.extend({},
                                    {x: row[xaxis], y: row[metric.get("yaxis")]},
                                    row));
                    });
                });
                self.get("metrics").each(function(metric){
                    var series = series_by_metric[metric.get("name")];
                    if (!$.isEmptyObject(series)) {
                        metric.set("series", series);
                    } else {
                        // ugly hack to make sure data change is detected even
                        // after several empty responses
                        // Forces "change:series" event to be triggered
                        metric.set("series", new Date());
                    }
                });
            }).fail(function(response){
                var value = response.status != 500 ? response.responseText: ""
                self.trigger("metricgroup:dataload-failed", value);
            });
        },

        update_timeline: function(changes) {
          var self = this;
          // FIXME this will update each timeline as many time as there are
          // metric displayed in the owning graph, we should find a way to do
          // it only once.  There shouldn't be many configuration changes, so
          // hopefully this isn't a big problem.
          self.get("metrics").each(function(metric){
              metric.trigger("metric:configchanges", changes);
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
