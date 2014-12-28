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


    var axisFormats = {
        "number": Rickshaw.Fixtures.Number.formatKMBT,
        "size": new size.SizeFormatter().fromRaw,
        "sizerate": function(value){ return new size.SizeFormatter({suffix: "ps"}).fromRaw(value)},
        "duration": function(data){ return moment(parseInt(data, 10)).preciseDiff(moment(0))}
    }

    var GraphView = WidgetView.extend({
            template: template,
            tag: "div",
            model: Graph,

            initialize: function(){
                var self = this;
                this.$el.html(this.template(this.model.toJSON()));
                this.graph_elem = this.$el.find(".graph_container");
                this.graph = new Rickshaw.Graph({
                            element: this.graph_elem.get(0),
                            height: this.$el.innerHeight(),
                            width: this.$el.innerWidth(),
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
                // TODO: allow multiple axes
                this.y_axes = {};
                this.model.get("metrics").each(function(metric, index){
                    var type = metric.get("type") || "number";
                    if(this.y_axes[type] == undefined){
                        var formatter = axisFormats[type];
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
                this.legend = new Rickshaw.Graph.Legend( {
                    graph: this.graph,
                    element: this.$el.find('.graph_legend').get(0)
                });

                var hoverDetail = new Rickshaw.Graph.HoverDetail( {
                    graph: this.graph,
                    formatter: function(series, x, y){
                        var type = series.metric.get("type") || "number";
                        var formatter = axisFormats[type];
                        var date = '<span class="date">' + new Date(x * 1000).toUTCString() + '</span>';
                        var swatch = '<span class="detail_swatch" style="background-color: ' + series.color + '"></span>';
                        var content = swatch + series.label + ": " + formatter(y) + '<br/>' + date;
                        return content;

                    }
                } );

                var highlighter = new Rickshaw.Graph.Behavior.Series.Highlight( {
                    graph: this.graph,
                    legend: this.legend
                } );
                this.preview = new Rickshaw.Graph.RangeSlider.Preview({
                	graph: this.graph,
                	element: this.$el.find(".graph_preview").get(0)
                });
                this.listenTo(this.model, "widget:needrefresh", this.update);
                this.render();
            },


            nodata: function(){
                this.$nodata_el.width(this.$el.innerWidth());
                this.$nodata_el.height(this.$el.height());
                this.el.insertBefore(this.nodata_el, this.el.firstChild||null);
            },

            remove_nodata: function(){
                if(this.nodata_el && this.nodata_el.parentNode){
                    this.nodata_el.parentNode.removeChild(this.nodata_el);
                }
            },

            _resize: function(){
               this.graph.setSize({width: this.graph_elem.parent().innerWidth()});
               this.preview.configure({width: this.graph.width});
                _.each(this.y_axes, function(axis){
                    var width = axis.orientation === "left" ? 0 : this.$el.innerWidth();
                    axis.setSize({height: this.graph.height + 4, auto: true});
                }, this);
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
                         this.graph.validateSeries(this.graph.series);
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
                this.legend.render();
                return this;
            }
        });
    return GraphView;

});
