define([
        'backbone',
        'd3',
        'rickshaw',
        'powa/views/WidgetView',
        'powa/models/Graph',
        'tpl!powa/templates/graph.html',
        'powa/utils/duration',
        'powa/utils/size',
        'powa/rickshaw/Rickshaw.Graph.DragZoom',
        'powa/utils/message',
        'tippy'
],
        function(Backbone, d3, Rickshaw, WidgetView, Graph, template, duration, size, DragZoom, Message, tippy){
    var registry = {};
    var makeInstance = function(options){
        return new registry[options.model.get("renderer") || "line"](options);
    };

    var GraphView = WidgetView.extend({
            template: template,
            tag: "div",
            model: Graph,
            typname: "graph",
            axisFormats: {
                "number": Rickshaw.Fixtures.Number.formatKMBT,
                "size": new size.SizeFormatter().fromRaw,
                "sizerate": function(value){ return new size.SizeFormatter({suffix: "ps"}).fromRaw(value)},
                "duration": function(data){
                    return moment(parseFloat(data, 10)).preciseDiff(moment(0))
                },
                "percent": function(value){ return Math.round(value * 100) / 100 + '%'}
            },

            initialize: function(){
                var self = this;
                this.listenTo(this.model, "widget:needrefresh", this.update);
                this.listenTo(this.model, "widget:configchanges", this.configchanges);
                this.listenTo(this.model, "widget:dataload-failed", this.fail);
                this.listenTo(this, "graph:resize", this.onResize);
                this.render();
                this.$nodata_el = $("<div>").html("No data").css({
                    position: "absolute",
                    "text-align": "center",
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
                    this.updateScales();
                    this.graph.series.splice(0, this.graph.series.length + 1);
                    this.graph.series.push.apply(this.graph.series, series);
                    this.adaptGraph(series);
                    this.graph.validateSeries(this.graph.series);
                }
                return this.graph;
            },

            getSize: function(){
                return {
                      width: this.$graph_elem.parent().innerWidth()
                };
            },

            updateScales: function(series){
                var self = this;
                $.each(this.y_axes, function(key, axis){
                    return;
                    var unit = key;
                    var ymin = +Infinity,
                        ymax = -Infinity;
                    axis.scale = d3.scale.linear();
                    var all_series = [];
                    _.each(this.graph.series, function(serie){
                        var metric = serie.metric;
                        if(metric.get("type") === key){
                            _.each(serie.data, function(datum){
                                ymin = Math.min(datum.y, ymin);
                                ymax = Math.max(datum.y, ymax);
                                serie.scale = axis.scale;
                                all_series.push(serie);
                            });
                        };
                    });
                    ymin = 0.8 * ymin;
                    ymax = 1.2 * ymax;
                    axis.scale = axis.scale.domain([ymin, ymax]).range([0, 1]);
                    _.each(all_series, function(serie){
                        serie.scale = axis.scale;
                    });
                });
            },

            adaptGraph: function(series){},

            makeGraph: function(series){
                // TODO: split this in subclasses for each type
                // of graph
                var renderer = this.model.get("renderer") || "line";
                data = this.model.toJSON()
                data["cid"] = this.cid
                this.$el.html(this.template(data));
                var url = this.model.get("url");
                if (url != undefined) {
                  var title = this.model.get("title");
                  this.title = title
                  this.$el.find(".title").append(' <a href="' + url + '"'
                    + 'target="_blank">'
                    + '<i class="fi-link" title="See the documentation"></i>'
                    + '</a>');
                }
                this.$graph_elem = this.$el.find(".graph_container");
                this.graph_elem = this.$graph_elem.get(0);
                this.y_axes = {};
                this.initGraph(series);
                this.initAxes(series);
                this.updateScales();
                this.initGoodies();
            },

            initAxes: function(series){
                var self = this;
                var i = 0;
                this.model.get("metrics").each(function(metric, index){
                    var type = metric.get("type") || "number";
                    if(this.y_axes[type] == undefined){
                        var formatter = self.axisFormats[type];
                        var orientation = i % 2 == 0 ? "left" : "right";
                        this.y_axes[type] = new Rickshaw.Graph.Axis.Y.Scaled({
                            element: this.$el.find(".graph_" + orientation + "_axis").get(0),
                            graph: this.graph,
                            min: 0,
                            scale: d3.scale.linear(),
                            orientation: orientation,
                            tickFormat: formatter
                        });
                        i++;
                    }
                }, this);
            },

            initAnnotator: function() {
                this.annotator = new Rickshaw.Graph.Annotate( {
                    graph: this.graph,
                    element: this.$el.find('.graph_timeline').get(0)
                });
            },

            initGraphHelp: function() {
              labels = '';
              // retrieve the description of each metrics
              this.model.get("metrics").each(function(metric, index) {
                labels ='<tr>'
                  + '<td><b>' + metric.get("label") + '</b></td>'
                  + '<td>'
                  + metric.get("desc")
                  + '</td></td>'
                  + labels;
              });
              help = '<table>'
                + labels
                + '</table class="stack">'
              // add the hover info
              tippy('#' + this.cid, {
                content: help,
                arrow: true,
                arrowType: 'round',
                maxWidth: '100%',
                theme: 'translucent',
              });
            },

            initGoodies: function(){
                this.initAnnotator();
                this.legend = new Rickshaw.Graph.Legend( {
                    graph: this.graph,
                    element: this.$el.find('.graph_legend').get(0)
                });
                this.initGraphHelp();
            },

            nodata: function(){
                this.$nodata_el.width(this.$el.innerWidth());
                this.$nodata_el.height(this.$el.innerHeight());
                this.el.insertBefore(this.nodata_el, this.el.firstChild||null);
                if (this.legend) {
                    $(this.legend.element).hide();
                }
                if (this.graph) {
                    $(this.graph.element).hide();
                }
                $('.graph_timeline').hide();
                _.each(this.y_axes, function(axis){
                    $(axis.element).empty();
                });
            },

            remove_nodata: function(){
                if(this.nodata_el && this.nodata_el.parentNode){
                    this.nodata_el.parentNode.removeChild(this.nodata_el);
                }
            },

            _resize: function(){
               if(this.graph){
                this.graph.configure({width: this.$graph_elem.parent().innerWidth()});
                _.each(this.y_axes, function(axis){
                    var width = axis.orientation === "left" ? 0 : this.$el.innerWidth();
                    axis.setSize({height: this.graph.height + 4, auto: true});
                }, this);
                this.graph.render();
                this.trigger("graph:resize");
               }
            },

            onResize: function(){},

            update: function(newseries){
                this.hideload();
                this.remove_nodata();
                if(newseries.length == 0){
                    this.nodata();
                }
                else{
                   this.getGraph(newseries);
                   $(this.graph.element).show();
                   $(this.legend.element).show();
                   this.graph.update();
                   if(this.legend){
                       this.legend.render();
                       var shelving = new Rickshaw.Graph.Behavior.Series.Toggle( {
                           graph: this.graph,
                           legend: this.legend
                       } );
                       var highlighter = new Rickshaw.Graph.Behavior.Series.Highlight( {
                           graph: this.graph,
                           legend: this.legend
                       });
                   }
                }
                this.trigger("widget:update");
            },

            configchanges: function(changes) {
              if (this.annotator) {
                var self = this;

                // bail out if nothing was received
                if (changes === undefined || changes.length == 0)
                  return;

                // show the timeline as soon as we received events
                $('.graph_timeline').show();

                // clean previously received events
                self.initAnnotator()

                // display each new event
                $.each(changes, function(i) {
                  change = changes[i];
                  txt = Message.format_config_change(change);
                  self.annotator.add(change["ts"], txt);
                })
                this.annotator.update();
              }
            },

            show: function(){
                this._resize();
            },

            render: function(){
                return this;
            },
        }, {
            extend: function(instanceattrs, clsattrs){
                var newcls = WidgetView.extend.apply(this, [instanceattrs, clsattrs]);
                registry[newcls.prototype.rendername] = newcls;
                if(!newcls.makeInstance){
                    newcls.makeInstance = makeInstance;
                }
                return newcls;
            },
            makeInstance: makeInstance

        });
    return GraphView;

});
