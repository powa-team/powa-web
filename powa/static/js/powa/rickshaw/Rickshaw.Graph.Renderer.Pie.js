define(["rickshaw"], function(Rickshaw){
    Rickshaw.namespace('Rickshaw.Graph.Renderer.Pie');

    Rickshaw.Graph.Renderer.Pie = Rickshaw.Class.create( Rickshaw.Graph.Renderer, {

        name: 'pie',

        defaults: function($super) {

            return Rickshaw.extend( $super(), {
                unstack: false,
                fill: false,
                stroke: false
            } );
        },

        seriesPathFactory: function() {

            var graph = this.graph;

            var factory = d3.svg.area()
                .x( function(d) { return graph.x(d.x) } )
                .y0( function(d) { return graph.y(d.y0) } )
                .y1( function(d) { return graph.y(d.y + d.y0) } )
                .interpolate(graph.interpolation).tension(this.tension);

            factory.defined && factory.defined( function(d) { return d.y !== null } );
            return factory;
        },

        seriesStrokeFactory: function() {

            var graph = this.graph;

            var factory = d3.svg.line()
                .x( function(d) { return graph.x(d.x) } )
                .y( function(d) { return graph.y(d.y + d.y0) } )
                .interpolate(graph.interpolation).tension(this.tension);

            factory.defined && factory.defined( function(d) { return d.y !== null } );
            return factory;
        },

        render: function(args) {

            args = args || {};

            var graph = this.graph;
            var series = args.series || graph.series;
            var radius = Math.min(this.graph.height, this.graph.width) * 0.45;

            var vis = args.vis || graph.vis;
            vis.selectAll('*').remove();
            var piegroup = vis.data(series.map(function(serie){return serie.stack}))
                .attr("width", this.graph.width)
                .attr("height", this.graph.height)
                .append("svg:g")
                    .attr("transform", "translate(" + radius + ", " + radius + ")");

            var arc = d3.svg.arc().outerRadius(radius);
            var pie = d3.layout.pie().value(function(d){return d.y});
            var palette = new Rickshaw.Color.Palette({scheme: graph.scheme});
            var arcs = piegroup.selectAll("g.slice")
                .data(pie)
                .enter().append("svg:g", 'g')
                .attr("class", "slice")
                .attr("fill", function(){ return palette.color()});
            arcs.append("svg:path").attr("d", arc);

            series.forEach( function(series) {
                if (series.disabled) return;
                series.path = arcs[0];
            }, this );
        },

    } );
});
