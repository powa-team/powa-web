define(["rickshaw", "d3"], function(rickshaw, d3){
    return Rickshaw.Class.create( Rickshaw.Graph.RangeSlider.Preview, {

        initialize: function($super, args){
            this.range = args.range;
            $super(args);
            args.graph.window.xMin = this.range[0];
            args.graph.window.xMax = this.range[1];
        },


        render: function($super) {
            var self = this;

            this.svg = d3.select(this.element)
                .selectAll("svg.rickshaw_range_slider_preview")
                .data([null]);

            this.previewHeight = this.config.height - (this.config.frameTopThickness * 2);
            this.previewWidth = this.config.width - (this.config.frameHandleThickness * 2);

            this.currentFrame = [0, this.previewWidth];

            var buildGraph = function(parent, index) {

                var graphArgs = Rickshaw.extend({}, parent.config);
                var height = self.previewHeight / self.graphs.length;
                var renderer = parent.renderer.name;

                Rickshaw.extend(graphArgs, {
                    element: this.appendChild(document.createElement("div")),
                    height: height,
                    width: self.previewWidth,
                    series: parent.series,
                    renderer: renderer,
                    xScale: d3.time.scale(),
                });

                var graph = new Rickshaw.Graph(graphArgs);
                new Rickshaw.Graph.Axis.Time({
                    graph: graph,
                    timeFixture: new Rickshaw.Fixtures.Time.Local()
                });
                self.previews.push(graph);

                parent.onUpdate(function() {
                    var graphRange = parent.dataDomain();
                    if((self.range[0] > graphRange[0]) ||
                        (self.range[1] < graphRange[1])){
                        self.rendered = false;
                        self.range = graphRange;
                    }

                    /*
                     * We don't render the graph here, as we want to preserve
                     * the preview as it was before applying a zoom
                     */
                    //if(!self.rendered){
                    //    graph.render();
                    //}

                    // but we render the widget itself, to show the selected
                    // interval
                    self.render();
                });

                parent.onConfigure(function(args) {
                    // don't propagate height
                    delete args.height;
                    args.width = args.width - self.config.frameHandleThickness * 2;
                    graph.configure(args);
                    graph.render();
                });

                graph.render();


            };

            var graphContainer = d3.select(this.element)
                .selectAll("div.rickshaw_range_slider_preview_container")
                .data(this.graphs);

            var translateCommand = "translate(" +
                this.config.frameHandleThickness + "px, " +
                this.config.frameTopThickness + "px)";


            if(!this.rendered){
            graphContainer.enter()
                .append("div")
                .classed("rickshaw_range_slider_preview_container", true)
                .style("-webkit-transform", translateCommand)
                .style("-moz-transform", translateCommand)
                .style("-ms-transform", translateCommand)
                .style("transform", translateCommand)
                .each(buildGraph);

            graphContainer.exit()
                .remove();
            }

            // Use the first graph as the "master" for the frame state
            var masterGraph = this.graphs[0];

            var domainScale = d3.scale.linear()
                .domain([0, this.previewWidth])
                .range(this.range);


            var currentWindow = [masterGraph.window.xMin, masterGraph.window.xMax];

            this.currentFrame[0] = currentWindow[0] === undefined ? 
                0 : Math.round(domainScale.invert(currentWindow[0]));

            if (this.currentFrame[0] < 0) this.currentFrame[0] = 0;

            this.currentFrame[1] = currentWindow[1] === undefined ?
                this.previewWidth : domainScale.invert(currentWindow[1]);

            if (this.currentFrame[1] - this.currentFrame[0] < self.config.minimumFrameWidth) {
                this.currentFrame[1] = (this.currentFrame[0] || 0) + self.config.minimumFrameWidth;
            }

            this.svg.enter()
                .append("svg")
                .classed("rickshaw_range_slider_preview", true)
                .style("height", this.config.height + "px")
                .style("width", this.config.width + "px")
                .style("position", "absolute")
                .style("top", 0);

            this._renderDimming();
            this._renderFrame();
            this._renderGrippers();
            this._renderHandles();
            this._renderMiddle();

            this._registerMouseEvents();
            this.rendered = true;
        },


        update: function($super, args){
            $super(args);
        },

        configure: function($super, args){
            $super(args);
        },

        _updateAll: function(frameAfterDrag){
            var self = this;
                self.render();
                self.graphs.forEach(function(graph) {

                    var domainScale = d3.scale.linear()
                        .interpolate(d3.interpolateNumber)
                        .domain([0, self.previewWidth])
                        .range(self.range);

                    var windowAfterDrag = [
                        domainScale(frameAfterDrag[0]),
                        domainScale(frameAfterDrag[1])
                    ];


                    if (frameAfterDrag[0] === 0) {
                        windowAfterDrag[0] = undefined;
                    }
                    if (frameAfterDrag[1] === self.previewWidth) {
                        windowAfterDrag[1] = undefined;
                    }
                    graph.window.xMin = windowAfterDrag[0];
                    graph.window.xMax = windowAfterDrag[1];
                });
        },

        _registerMouseEvents: function() {

            var element = d3.select(this.element);
            var selection = d3.select(document);

            var drag = {
                target: null,
                start: null,
                stop: null,
                left: false,
                right: false,
                rigid: false
            };

            var self = this;


            function onMousemove(datum, index) {

                drag.stop = self._getClientXFromEvent(d3.event, drag);
                var distanceTraveled = drag.stop - drag.start;
                var frameAfterDrag = self.frameBeforeDrag.slice(0);
                var minimumFrameWidth = self.config.minimumFrameWidth;

                if (drag.rigid) {
                    minimumFrameWidth = self.frameBeforeDrag[1] - self.frameBeforeDrag[0];
                }
                if (drag.left) {
                    frameAfterDrag[0] = Math.max(frameAfterDrag[0] + distanceTraveled, 0);
                }
                if (drag.right) {
                    frameAfterDrag[1] = Math.min(frameAfterDrag[1] + distanceTraveled, self.previewWidth);
                }

                var currentFrameWidth = frameAfterDrag[1] - frameAfterDrag[0];

                if (currentFrameWidth <= minimumFrameWidth) {

                    if (drag.left) {
                        frameAfterDrag[0] = frameAfterDrag[1] - minimumFrameWidth;
                    }
                    if (drag.right) {
                        frameAfterDrag[1] = frameAfterDrag[0] + minimumFrameWidth;
                    }
                    if (frameAfterDrag[0] <= 0) {
                        frameAfterDrag[1] -= frameAfterDrag[0];
                        frameAfterDrag[0] = 0;
                    }
                    if (frameAfterDrag[1] >= self.previewWidth) {
                        frameAfterDrag[0] -= (frameAfterDrag[1] - self.previewWidth);
                        frameAfterDrag[1] = self.previewWidth;
                    }
                }
                self._updateAll(frameAfterDrag);
            }

            function onMousedown() {
                drag.target = d3.event.target;
                drag.start = self._getClientXFromEvent(d3.event, drag);
                self.frameBeforeDrag = self.currentFrame.slice();
                d3.event.preventDefault ? d3.event.preventDefault() : d3.event.returnValue = false;
                selection.on("mousemove.rickshaw_range_slider_preview", onMousemove);
                selection.on("mouseup.rickshaw_range_slider_preview", onMouseup);
                selection.on("touchmove.rickshaw_range_slider_preview", onMousemove);
                selection.on("touchend.rickshaw_range_slider_preview", onMouseup);
                selection.on("touchcancel.rickshaw_range_slider_preview", onMouseup);
            }

            function onMousedownLeftHandle(datum, index) {
                drag.left = true;
                onMousedown();
            }

            function onMousedownRightHandle(datum, index) {
                drag.right = true;
                onMousedown();
            }

            function onMousedownMiddleHandle(datum, index) {
                drag.left = true;
                drag.right = true;
                drag.rigid = true;
                onMousedown();
            }

            function onMouseup(datum, index) {
                selection.on("mousemove.rickshaw_range_slider_preview", null);
                selection.on("mouseup.rickshaw_range_slider_preview", null);
                selection.on("touchmove.rickshaw_range_slider_preview", null);
                selection.on("touchend.rickshaw_range_slider_preview", null);
                selection.on("touchcancel.rickshaw_range_slider_preview", null);
                delete self.frameBeforeDrag;
                drag.left = false;
                drag.right = false;
                drag.rigid = false;
                self.graphs.forEach(function(graph){
                    self.slideCallbacks.forEach(function(callback) {
                        callback(graph, graph.window.xMin || self.range[0], graph.window.xMax || self.range[1]);
                    });
                });
            }

            element.select("rect.left_handle").on("mousedown", onMousedownLeftHandle);
            element.select("rect.right_handle").on("mousedown", onMousedownRightHandle);
            element.select("rect.middle_handle").on("mousedown", onMousedownMiddleHandle);
            element.select("rect.left_handle").on("touchstart", onMousedownLeftHandle);
            element.select("rect.right_handle").on("touchstart", onMousedownRightHandle);
            element.select("rect.middle_handle").on("touchstart", onMousedownMiddleHandle);
        },


    });
});

