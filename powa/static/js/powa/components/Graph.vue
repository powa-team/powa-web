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
        <div class="col">
          <div ref="graphContainer" style="height: 400px"/>
        </div>
      </div>
    </div>
  </div>
</template>

<script>

import * as _ from "lodash";
import MetricWidget from './MetricWidget.vue';
import * as echarts from "echarts";
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
        //"number": Rickshaw.Fixtures.Number.formatKMBT,
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

    dataLoaded(data) {
      // Help
      this.initGraphHelp();

      const chart = echarts.init(this.$refs.graphContainer);

      const yAxis = {}
      const metrics = _.map(this.config.metrics, (metric) => {
        return metric.split('.')[1];
      });
      _.each(metrics, (metric, index) => {
        const type = this.getType(metric);
        if (yAxis[type] == undefined) {
          const formatter = this.axisFormats[type];
          yAxis[type] = {
            type: "value",
            alignTicks: true,
            axisLabel: {
              formatter: formatter,
            }
          }
        }
      });

      const series = _.map(data, (serie) => {
        return {
          type: "line",
          name: serie.label,
          data: _.map(serie.data, (d) => [d.x, d.y]),
          yAxisIndex: _.keys(yAxis).indexOf(serie.type)
        };
      });

      const option = {
        tooltip: {
          trigger: "axis",
          position: function (pt) {
            return [pt[0], '10%'];
          }
        },
        legend: {
          data: _.map(series, (serie) => serie.name),
        },
        xAxis: {
          type: "time",
        },
        yAxis: _.map(yAxis, (axis) => axis),
        series: series
      }
      chart.setOption(option);
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
