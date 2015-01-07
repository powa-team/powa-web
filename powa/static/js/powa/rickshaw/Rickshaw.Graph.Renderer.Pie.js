define(["rickshaw"], function(Rickshaw){
    Rickshaw.namespace('Rickshaw.Graph.Renderer.Pie');

    Rickshaw.Graph.Renderer.Pie = Rickshaw.Class.create( Rickshaw.Graph.Renderer, {

        name: 'pie',

        defaults: function($super) {

            return Rickshaw.extend( $super(), {
                unstack: true,
                fill: false,
                stroke: false,
                label_attribute: ""
            } );
        },

        mergeSeries: function(args){

        },

        render: function(args) {

            args = args || {};

            var graph = this.graph;
            var self = this;
            var series = args.series || graph.series;
            var radius = Math.min(this.graph.height, this.graph.width) * 0.45;

            var vis = args.vis || graph.vis;
            vis.selectAll('*').remove();
            // Merge all series into one
            var newSeries = []
            series.forEach(function(serie){
                if(!serie.disabled){
                    newSeries.push(serie)
                }
            });
            var piegroup = vis.data([newSeries.map(function(d){return d.stack[0]})])
                .attr("width", this.graph.width)
                .attr("height", this.graph.height)
                .append("svg:g")
                    .attr("transform", "translate(" + radius + ", " + radius + ")");

            var arc = d3.svg.arc().outerRadius(radius);
            var pie = d3.layout.pie().value(function(d){return d.y});
            var arcs = piegroup.selectAll("g.slice")
                .data(pie)
                .enter().append("svg:g", 'g')
                .attr("class", "slice")
                .attr("fill", function(d, i){ return newSeries[i].color});
            arcs.append("svg:path").attr("d", arc);
            arcs.append("svg:text")
                .attr("transform", function(d) {
                    d.innerRadius = 0;
                    d.outerRadius = radius;
                    return "translate(" + arc.centroid(d) + ")";
                })
                .attr("text-anchor", "middle")
                .attr("fill", "white")
                .text(function(d, i) {
                    if(d.endAngle - d.startAngle < 4){
                        return ""
                    } else {
                        return d.data[self.label_attribute];
                    }
                });
            series.forEach( function(series) {
                if (series.disabled) return;
                series.path = arcs[0];
            }, this );
        },

    } );
});
