/*
 * This file is released by Prometeheus under the Apache License
 */
define([
    'rickshaw'
], function(Rickshaw){

Rickshaw.namespace('Rickshaw.Graph.DragZoom');

Rickshaw.Graph.DragZoom = Rickshaw.Class.create({

  initialize: function(args) {
    if (!args.graph) {
      throw "Rickshaw.Graph.DragZoom needs a reference to a graph";
    }
    var defaults = {
      opacity: 0.5,
      fill: 'steelblue',
      minimumTimeSelection: 0.02,
      callback: function() {}
    };

    this.graph = args.graph;
    this.svg = d3.select(this.graph.element).select("svg");
    this.svgWidth = parseInt(this.svg.attr("width"), 10);
    this.opacity = args.opacity || defaults.opacity;
    this.fill = args.fill || defaults.fill;
    this.minimumTimeSelection = args.minimumTimeSelection || defaults.minimumTimeSelection;
    this.callback = args.callback || defaults.callback;
    this.stack = [];
    this.registerMouseEvents();
  },

  registerMouseEvents: function() {
    var self = this;
    var ESCAPE_KEYCODE = 27;
    var rectangle;

    var drag = {
      startDt: null,
      stopDt: null,
      startPX: null,
      stopPX: null
    };

    this.svg.on("mousedown", onMousedown);
    this.svg.on("touchstart", onMousedown);
    this.svg.on("dblclick", onDblClick);

    function onDblClick(datum, index){
        if(self.stack.length){
            var range = self.stack.pop();
            self.callback(range[0], range[1]);
        }

    }

    function onMouseup(datum, index) {
      drag.stopDt = pointAsDate(d3.event);
      var beforeDrag = [
        self.graph.window.xMin,
        self.graph.window.xMax
      ];
      var windowAfterDrag = [
        drag.startDt,
        drag.stopDt
      ].sort(compareNumbers);

      reset(this);

      var range = windowAfterDrag[1] - windowAfterDrag[0],
          wholerange = beforeDrag[1] - beforeDrag[0];

      /* Can't zoom by less than 2% */
      if(range < self.minimumTimeSelection * wholerange){
        return;
      }
      self.graph.window.xMin = windowAfterDrag[0];
      self.graph.window.xMax = windowAfterDrag[1];

      var endTime = self.graph.window.xMax;

      if (isNaN(range)) {
        return;
      }
      self.stack.push(beforeDrag);
      self.callback(self.graph.window.xMin, self.graph.window.xMax);
    }

    function onMousemove() {
      var offset = drag.stopPX = (d3.event.offsetX || d3.event.layerX);
      if (offset > (self.svgWidth - 1) || offset < 1) {
        return;
      }

      var limits = [drag.startPX, offset].sort(compareNumbers);
      var selectionWidth = limits[1]-limits[0];
      if (isNaN(selectionWidth)) {
        return reset(this);
      }
      rectangle.attr("fill", self.fill)
               .attr("x", limits[0])
               .attr("width", selectionWidth);
    }

    function onMousedown() {
      var el = d3.select(this);
      rectangle = el.append("rect")
                    .style("opacity", self.opacity)
                    .attr("y", 0)
                    .attr("height", "100%");

      if(d3.event.preventDefault) {
        d3.event.preventDefault();
      } else {
        d3.event.returnValue = false;
      }
      drag.target = d3.event.target;
      drag.startDt = pointAsDate(d3.event);
      drag.startPX = d3.event.offsetX || d3.event.layerX;
      el.on("mousemove", onMousemove);
      d3.select(document).on("mouseup", onMouseup);
      d3.select(document).on("keyup", function() {
        if (d3.event.keyCode === ESCAPE_KEYCODE) {
          reset(this);
        }
      });
      el.on("touchmove", onMousemove);
      d3.select(document).on("touchend", onMouseup);
      d3.select(document).on("touchcancel", onMouseup);
    }

    function reset(el) {
      var s = d3.select(el);
      s.on("mousemove", null);
      d3.select(document).on("mouseup", null);
      s.on("touchmove", null);
      d3.select(document).on("touchend", null);
      d3.select(document).on("touchcancel", null);
      drag = {};
      rectangle.remove();
    }

    function compareNumbers(a, b) {
      return a - b;
    }

    function pointAsDate(e) {
      return Math.floor(self.graph.x.invert(e.offsetX || e.layerX));
    }
  }
});
return Rickshaw.Graph.DragZoom;
});
