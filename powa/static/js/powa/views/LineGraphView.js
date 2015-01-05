define(["rickshaw", "d3", "powa/views/GraphView"], function(rickshaw, d3, GraphView){
    return GraphView.extend({

        initGraph: function(series){
            this.graph = new Rickshaw.Graph({
                        element: this.graph_elem,
                        height: this.$el.innerHeight(),
                        width: this.$el.innerWidth() - 40,
                        xScale: d3.time.scale(),
                        renderer: "line",
                        series: series || []
            });
            var time = new Rickshaw.Fixtures.Time();
            var seconds = time.unit('second');
            this.x_axis = new Rickshaw.Graph.Axis.Time( {
                graph: this.graph,
                tickFormat: this.graph.x.tickFormat(),
            } );
        },

        onResize: function(){
            this.preview.configure({width: this.graph.width});
        },

        initGoodies: function(){
            GraphView.prototype.initGoodies.call(this);
            var self = this;
            var hoverDetail = new Rickshaw.Graph.HoverDetail( {
                graph: this.graph,
                formatter: function(series, x, y){
                    var type = series.metric.get("type") || "number";
                    var formatter = self.axisFormats[type];
                    var date = '<span class="date">' + new Date(x * 1000).toUTCString() + '</span>';
                    var swatch = '<span class="detail_swatch" style="background-color: ' + series.color + '"></span>';
                    var content = swatch + series.label + ": " + formatter(y) + '<br/>' + date;
                    return content;

                }
            });

            this.preview = new Rickshaw.Graph.RangeSlider.Preview({
                graph: this.graph,
                element: this.$el.find(".graph_preview").get(0)
            });
        }

    });
});
