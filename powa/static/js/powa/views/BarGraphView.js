define(["rickshaw", "d3", "powa/views/TimeView"],
    function(rickshaw, d3, TimeView){
    return TimeView.extend({

        initGraph: function(series){
            this.graph = new Rickshaw.Graph($.extend(this.getSize(), this.model.attributes, {
                        element: this.graph_elem,
                        renderer: 'bar',
                        series: series || []
            }));
            var time = new Rickshaw.Fixtures.Time();
            var seconds = time.unit('second');
            var self = this;
            this.x_axis = new Rickshaw.Graph.Axis.Time({
                graph: this.graph,
                tickFormat: function(x, index){
                    var value = self.graph.series[0].data[x - 1.5];
                    if(value){
                        return value[self.model.get("x_label_attr")];
                    }
                    return "";
                }
            });
            this.adaptGraph(series);
        },

        adaptGraph: function(series){
            var max_x = _.max(_.map(series, function(serie){
                var max_value = _.max(serie.data, function(value){return value.x});
                return max_value.x;
            }));
            this.graph.x = d3.scale.linear().range([0, max_x]).domain([0, max_x]);
            this.graph.xScale =this.graph.x;
        },

    });
});
