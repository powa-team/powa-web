define([
        'backbone',
        'd3',
        'rickshaw',
        'powa/views/WidgetView',
        'powa/models/Graph',
        'tpl!powa/templates/graph.html',
        'powa/utils/duration',
        'powa/utils/size'
],
        function(Backbone, d3, Rickshaw, WidgetView, Graph, template, duration, size){

    var GraphView = WidgetView.extend({
            template: template,
            tag: "div",
            model: Graph,
            axisFormats: {
                "number": Rickshaw.Fixtures.Number.formatKMBT,
                "size": new size.SizeFormatter().fromRaw,
                "sizerate": function(value){ return new size.SizeFormatter({suffix: "ps"}).fromRaw(value)},
                "duration": function(data){ return moment(parseInt(data, 10)).preciseDiff(moment(0))}
            },


            initialize: function(){
                var self = this;
                this.listenTo(this.model, "widget:needrefresh", this.update);
                this.listenTo(this.model, "widget:dataload-failed", this.fail);
                this.listenTo(this, "graph:resize", this.onResize);
                this.render();
                this.$nodata_el = $("<div>").html("No data").css({
                    position: "absolute",
                    left: "50%",
                    top: "50%",
                    width: "100%",
                    height: "100%"
                }).addClass("nodata");
                this.nodata_el = this.$nodata_el.get(0);
                this.$el.addClass("graph");
            },

            getGraph: function(series){
                var palette = new Rickshaw.Color.Palette({scheme: this.model.get("color_scheme"), interpolatedStopCount: 1});
                $.each(series, function(){
                    this.color = palette.color();
                });
                if(this.graph === undefined){
                    this.makeGraph(series);
                } else {
                    // update series
                    this.graph.series.splice(0, this.graph.series.length + 1);
                    this.graph.series.push.apply(this.graph.series, series);
                                this.graph.validateSeries(this.graph.series);
                    this.adaptGraph(series);
                }
                return this.graph;
            },

            adaptGraph: function(series){},

            makeGraph: function(series){
                // TODO: split this in subclasses for each type
                // of graph
                var renderer = this.model.get("renderer") || "line";
                this.$el.html(this.template(this.model.toJSON()));
                this.$graph_elem = this.$el.find(".graph_container");
                this.graph_elem = this.$graph_elem.get(0);
                this.y_axes = {};
                this.initGraph(series);
                this.initAxes();
                this.initGoodies();
            },

            initAxes: function(){
                var self = this;
                this.model.get("metrics").each(function(metric, index){
                    var type = metric.get("type") || "number";
                    if(this.y_axes[type] == undefined){
                        var formatter = self.axisFormats[type];
                        var orientation = index % 2 == 0 ? "left" : "right";
                        this.y_axes[type] = new Rickshaw.Graph.Axis.Y({
                            element: this.$el.find(".graph_" + orientation + "_axis").get(0),
                            graph: this.graph,
                            min: 0,
                            orientation: orientation,
                            tickFormat: formatter
                        });
                    }
                }, this);
            },

            initGoodies: function(){
                this.legend = new Rickshaw.Graph.Legend( {
                    graph: this.graph,
                    element: this.$el.find('.graph_legend').get(0)
                });


                var highlighter = new Rickshaw.Graph.Behavior.Series.Highlight( {
                    graph: this.graph,
                    legend: this.legend
                });
            },


            nodata: function(){
                this.$nodata_el.width(this.$el.innerWidth());
                this.$nodata_el.height(this.$el.innerHeight());
                this.el.insertBefore(this.nodata_el, this.el.firstChild||null);
            },

            remove_nodata: function(){
                if(this.nodata_el && this.nodata_el.parentNode){
                    this.nodata_el.parentNode.removeChild(this.nodata_el);
                }
            },

            _resize: function(){
               this.graph.setSize({width: this.$graph_elem.parent().innerWidth()});
               _.each(this.y_axes, function(axis){
                   var width = axis.orientation === "left" ? 0 : this.$el.innerWidth();
                   axis.setSize({height: this.graph.height + 4, auto: true});
               }, this);
               this.trigger("graph:resize");
            },

            onResize: function(){},

            update: function(newseries){
                if(newseries.length == 0){
                    this.hideload();
                    this.nodata();
                    return;
                }
                this.getGraph(newseries);
                this.remove_nodata();
                this._resize();
                this.graph.update();
                this.legend.render();
                var shelving = new Rickshaw.Graph.Behavior.Series.Toggle( {
                    graph: this.graph,
                    legend: this.legend
                } );
                this.hideload();
                this.trigger("widget:update");
            },

            render: function(){
                return this;
            }
        });
    return GraphView;

});
