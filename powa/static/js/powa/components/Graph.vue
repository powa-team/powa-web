<template>
  <div class="card shadow border-0 mb-4">
    <div class="card-body">
      <h4 class="card-title">
        {{ config.title }}
        <i
          ref="help"
          class="fa fa-info"
        />
      </h4>
      <div class="row no-gutters">
        <div
          ref="leftAxis"
          class="col-sm-1"
        />
        <div class="col-sm-10">
          <div ref="graphContainer" />
          <div ref="graphTimeline" />
          <div class="graph_preview" />
        </div>
        <div
          ref="rightAxis"
          class="col-sm-1"
        />
      </div>
      <div class="row">
        <div ref="graphLegend" />
      </div>
    </div>
  </div>
</template>

<script>

import MetricWidget from './MetricWidget.vue';
//import Rickshaw from 'rickshaw';
//import 'rickshaw/rickshaw.css'
import size from '../utils2/size';
import store from '../store';
import moment from 'moment';
import '../utils2/precisediff';
import tippy from 'tippy.js';
import 'tippy.js/dist/tippy.css';

export default {
  extends: MetricWidget,

  data: () => {
    return {
      axisFormats: {
        "number": Rickshaw.Fixtures.Number.formatKMBT,
        "size": new size.SizeFormatter().fromRaw,
        "sizerate": function(value){ return new size.SizeFormatter({suffix: "ps"}).fromRaw(value)},
        "duration": function(data){
          return moment(parseFloat(data, 10)).preciseDiff(moment(0))
        },
        "percent": function(value){ return Math.round(value * 100) / 100 + '%'}
      }
    }
  },

  methods: {

    dataLoaded(series) {
      // Help
      this.initGraphHelp();

      const size = $(this.$refs.graphContainer).parent().innerWidth();
      const attributes = this.config;
      const options = $.extend(
        size,
        attributes,
        {
          element: this.$refs.graphContainer,
          xScale: d3.time.scale(),
          renderer: "line",
          series: series || [],
          interpolation: 'linear'
        }
      );
      this.graph = new Rickshaw.Graph(options);
      this.graph.render();

      // Axis
      this.xAxis = new Rickshaw.Graph.Axis.Time({
        graph: this.graph,
        timeFixture: new Rickshaw.Fixtures.Time.Local()
      });
      this.yAxes = {};
      this.initAxes(series);

      // Hover
      new Rickshaw.Graph.HoverDetail({
        graph: this.graph,
        xFormatter: function(x) {
          return new moment.unix(x).format("LLLL");
        },
        formatter: function(series, x, y) {
          const type = this.getType(series.metric);
          const formatter = this.axisFormats[type];
          const date = '<span class="date">' + new moment.unix(x).format("lll") + '</span>';
          const swatch = '<span class="detail_swatch" style="background-color: ' + series.color + '"></span>';
          const content = swatch + series.label + ": " + formatter(y) + '<br/>' + date;
          return content;
        }.bind(this)
      });

      // Time line
      this.annotator = new Rickshaw.Graph.Annotate( {
        graph: this.graph,
        element: this.$refs.graphTimeline
      });

      // Legend
      this.legend = new Rickshaw.Graph.Legend( {
          graph: this.graph,
          element: this.$refs.graphLegend
      });
      this.legend.render();
      new Rickshaw.Graph.Behavior.Series.Toggle( {
        graph: this.graph,
        legend: this.legend
      });
      new Rickshaw.Graph.Behavior.Series.Highlight( {
        graph: this.graph,
        legend: this.legend
      });
    },

    initAxes(series) {
      let i = 0;
      const metrics = _.map(this.config.metrics, (metric) => {
        return metric.split('.')[1];
      });
      _.each(metrics, (metric, index) => {
        const type = this.getType(metric);
        if (this.yAxes[type] == undefined) {
          const formatter = this.axisFormats[type];
          const orientation = i % 2 == 0 ? "left" : "right";
          this.yAxes[type] = new Rickshaw.Graph.Axis.Y.Scaled({
              element: this.$refs[orientation + "Axis"],
              graph: this.graph,
              min: 0,
              scale: d3.scale.linear(),
              orientation: orientation,
              tickFormat: formatter
          });
          i++;
          this.yAxes[type].render();
        }
      });
    },

    initGraphHelp() {
      let labels = '';
      const metrics = _.map(this.config.metrics, (metric) => {
        return metric.split('.')[1];
      });
      _.each(metrics, (metric, index) => {
        labels = '<tr>'
          + '<td><b>' + this.getLabel(metric) + '</b></td>'
          + '<td>'
          + this.getDesc(metric)
          + '</td></td>'
          + labels;
      });
      const help = '<table>' + labels + '</table class="stack">';
      // add the hover info
      tippy(this.$refs.help, {
        content: help,
        arrow: true,
        maxWidth: '100%',
        theme: 'translucent',
        allowHTML: true
      });
    }
  }
}
</script>

<style lang="scss">
.y_axis {
  overflow: visible;
}
.rickshaw_legend {
  color: black;
  background: transparent;
  padding: 0;
  .swatch {
    display: inline-block;
    width: 10px;
    height: 10px;
    margin: 0 8px 0 0;
  }
  .label {
    display: inline-block;
  }
  .line {
    display: inline-block;
    margin: 0 0 0 30px;
  }
}

</style>
