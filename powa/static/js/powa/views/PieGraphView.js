define(["powa/views/GraphView", "rickshaw", "powa/rickshaw/Rickshaw.Graph.Renderer.Pie"],
function(GraphView, Rickshaw){
    return GraphView.extend({

        initGraph: function(series){
            this.graph = new Rickshaw.Graph({
                        element: this.graph_elem,
                        height: this.$el.innerHeight(),
                        width: this.$el.innerWidth() - 40,
                        renderer: 'pie',
                        series: series || []
            });
            this.adaptGraph(series);
        },

        initAxes: function(){
            return;
        },

        initGoodies: function(){

        }

    });
});
