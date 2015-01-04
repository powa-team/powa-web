define(["rickshaw", "d3", "powa/views/GraphView"], function(rickshaw, d3, GraphView){
    return GraphView.extend({

        initGraph: function(series){
            this.graph = new Rickshaw.Graph({
                        element: this.graph_elem,
                        height: this.$el.innerHeight(),
                        width: this.$el.innerWidth() - 40,
                        renderer: 'bar',
                        series: series || []
            });
            var time = new Rickshaw.Fixtures.Time();
            var seconds = time.unit('second');
            var self = this;
            this.x_axis = new Rickshaw.Graph.Axis.X({
                graph: this.graph,
                tickFormat: function(x, index){
                    console.log(arguments);
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
