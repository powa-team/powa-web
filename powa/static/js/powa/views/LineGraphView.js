define(["rickshaw", "d3", "powa/views/GraphView",
        "powa/views/GraphPreview", "moment"], function(rickshaw, d3, GraphView, GraphPreview, moment){
    return GraphView.extend({

        initGraph: function(series){
            this.graph = new Rickshaw.Graph($.extend({}, this.model.attributes, {
                        element: this.graph_elem,
                        width: this.$graph_elem.parent().innerWidth(),
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

        update: function(newseries){
            GraphView.prototype.update.call(this, newseries);
            if(this.preview){
                var domain = this.graph.dataDomain();
                console.log(domain);
                this.graph.window.xMin = domain[0];
                this.graph.window.xMax = domain[1];
                if(!this.preview.rendered){
                    this.preview.range = domain;
                }
                this.preview.render();
            }
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

            this.preview = new GraphPreview({
                graph: this.graph,
                element: this.$el.find(".graph_preview").get(0),
                range: this.graph.dataDomain()
            });
            this.preview.onSlide(function(graph, xmin, xmax){
                self.trigger("widget:zoomin", moment.unix(xmin), moment.unix(xmax));
            });
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
