define([
        'backbone',
        'rickshaw',
        'powa/views/WidgetView',
        'powa/models/Graph',
        'tpl!powa/templates/graph.html'],
        function(Backbone, Rickshaw, WidgetView, Graph, template){
    var GraphView = WidgetView.extend({
            template: template,
            tag: "div",
            model: Graph,

            initialize: function(){
                var self = this;
                this.$el.html(this.template(this.model.toJSON()));
                this.graph = new Rickshaw.Graph({
                            element: this.$el.find(".graph_container").get(0),
                            innerWidth: this.$el.innerWidth(),
                            height: this.$el.height(),
                            xScale: d3.time.scale(),
                            renderer: "line",
                            series: []
                });
                this.$nodata_el = $("<div>").html("No data").css({
                    position: "absolute",
                    left: "50%",
                    top: "50%",
                    width: "100%",
                    height: "100%"
                }).addClass("nodata");
                this.nodata_el = this.$nodata_el.get(0);
                var time = new Rickshaw.Fixtures.Time();
                var seconds = time.unit('second');
                this.x_axis = new Rickshaw.Graph.Axis.Time( {
                    graph: this.graph,
                    tickFormat: this.graph.x.tickFormat(),
                } );

                this.y_axis = new Rickshaw.Graph.Axis.Y( {
                    graph: this.graph,
                    min: 0,
                    tickFormat: Rickshaw.Fixtures.Number.formatKMBT
                } );
                this.legend = new Rickshaw.Graph.Legend( {
                    graph: this.graph,
                    element: this.$el.find('.graph_legend').get(0)
                });

                var hoverDetail = new Rickshaw.Graph.HoverDetail( {
                    graph: this.graph
                } );

                var highlighter = new Rickshaw.Graph.Behavior.Series.Highlight( {
                    graph: this.graph,
                    legend: this.legend
                } );
                this.listenTo(this.model, "graph:needrefresh", this.update);
            },


            nodata: function(){
                this.$nodata_el.width(this.$el.width());
                this.$nodata_el.height(this.$el.height());
                this.el.insertBefore(this.nodata_el, this.el.firstChild||null);
            },

            remove_nodata: function(){
                if(this.nodata_el && this.nodata_el.parentNode){
                    this.nodata_el.parentNode.removeChild(this.nodata_el);
                }
            },

            update: function(newseries){
                if(newseries.length == 0){
                    this.hideload();
                    this.nodata();
                    return;
                }
                this.remove_nodata();
                var palette = new Rickshaw.Color.Palette({scheme: this.model.get("color_scheme"), interpolatedStopCount: 1});
                $.each(newseries, function(){
                    this.color = palette.color();
                });
                this.graph.series.splice(0, this.graph.series.length + 1);
                this.graph.series.push.apply(this.graph.series, newseries);
                this.graph.setSize(this.$el.innerWidth(), this.$el.height());
                this.graph.validateSeries(this.graph.series);
                this.graph.update();
                this.legend.render();
                var shelving = new Rickshaw.Graph.Behavior.Series.Toggle( {
                    graph: this.graph,
                    legend: this.legend
                } );
                this.hideload();

            },

            render: function(){
                this.graph.setSize(this.$el.innerWidth(), this.$el.height());
                this.graph.render();
                return this;
            }
        });
    return GraphView;

});
