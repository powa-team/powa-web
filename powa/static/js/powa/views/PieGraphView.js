define(["powa/views/GraphView", "rickshaw", "powa/rickshaw/Rickshaw.Graph.Renderer.Pie"],
function(GraphView, Rickshaw){
    return GraphView.extend({
        rendername: "pie",
        initGraph: function(series){
            this.graph = new Rickshaw.Graph($.extend({}, this.model.attributes, {
                        element: this.graph_elem,
                        height: this.$el.innerHeight(),
                        width: this.$el.innerWidth() - 40,
                        renderer: 'pie',
                        series: series || [],
                        label_attribute: this.model.get("x_label_attr")
            }));
            this.adaptGraph(series);
        },

        initAxes: function(){
            return;
        }


    });
});
