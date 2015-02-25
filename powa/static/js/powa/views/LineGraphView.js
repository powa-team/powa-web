define(["rickshaw", "d3", "powa/views/TimeView"],
        function(rickshaw, d3, TimeView){
    return TimeView.extend({

        initGraph: function(series){
            this.graph = new Rickshaw.Graph($.extend(this.getSize(), this.model.attributes, {
                        element: this.graph_elem,
                        xScale: d3.time.scale(),
                        renderer: "line",
                        series: series || [],
                        interpolation: 'linear'
            }));
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

        updatePeriod: function(startDate, endDate){
            if(this.preview){
                this.preview.rendered = false;
            }
            this.from_date = startDate;
            this.to_date = endDate;
            this.showload();
        },

        addPreview: function(xmin, xmax){

        },

    });
});
