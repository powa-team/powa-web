<template>
  <v-card>
    <v-card-title>
      {{ config.title }}
      <span ref="helpEl">
        <v-icon class="pl-2">
          {{ mdiInformation }}
        </v-icon>
      </span>
    </v-card-title>
    <v-card-text>
      <div ref="graphContainer" style="height: 400px" />
    </v-card-text>
  </v-card>
</template>

<script setup>
import { onMounted, ref, watch } from "vue";
import * as _ from "lodash";
import * as echarts from "echarts";
import { mdiInformation } from "@mdi/js";
import { dateMath } from "@grafana/data";
import size from "../utils/size";
import store from "../store";
import moment from "moment";
import "../utils/precisediff";
import tippy from "tippy.js";
import "tippy.js/dist/tippy.css";
import $ from "jquery";

const props = defineProps({
  config: {
    type: Object,
    default() {
      return {};
    },
  },
});

const axisFormats = {
  //"number": Rickshaw.Fixtures.Number.formatKMBT,
  size: new size.SizeFormatter().fromRaw,
  sizerate: function (value) {
    return new size.SizeFormatter({ suffix: "ps" }).fromRaw(value);
  },
  duration: function (data) {
    return moment(parseFloat(data, 10)).preciseDiff(moment(0));
  },
  percent: function (value) {
    return Math.round(value * 100) / 100 + "%";
  },
};

const graphContainer = ref(null);

const helpEl = ref(null);

onMounted(() => {
  loadData();
});

function loadData() {
  const metricGroup = _.uniq(
    _.map(props.config.metrics, (metric) => {
      return metric.split(".")[0];
    })
  );
  const metrics = _.map(props.config.metrics, (metric) => {
    return metric.split(".")[1];
  });
  const params = {
    from: dateMath.parse(store.from).format("YYYY-MM-DD HH:mm:ssZZ"),
    to: dateMath.parse(store.to, true).format("YYYY-MM-DD HH:mm:ssZZ"),
  };
  const sourceConfig = store.dataSources[metricGroup];
  const grouper = props.config.grouper || null;
  const xaxis = sourceConfig.xaxis;
  $.ajax({
    url: sourceConfig.data_url + "?" + $.param(params),
  })
    .done((response) => {
      const seriesByMetric = {};

      _.each(metrics, (metric) => {
        seriesByMetric[metric] = {};
      });

      if (response.messages !== undefined) {
        $.each(response.messages, function (level, arr) {
          $.each(arr, function (i) {
            console.error(`FIXME: error ${level} ${i}`);
            /*msg = Message.add_message(level, arr[i]);*/
            /*$("#messages").append(msg);*/
          });
        });
      }

      _.each(response.data, (row) => {
        const group = grouper || "";
        _.each(metrics, (metric) => {
          const series = seriesByMetric[metric];
          let current_group = series[group];
          if (current_group === undefined) {
            current_group = series[group] = {
              metric: metric,
              id: metric + group,
              // name: metric.label_template({group: group}),
              data: [],
            };
          }
          if (row[xaxis] === undefined) {
            throw (
              "Data is lacking for xaxis. Did you include " +
              xaxis +
              " column in your query ?"
            );
          }
          current_group.data.push(
            $.extend(
              {},
              {
                x: new Date(row[xaxis] * 1000),
                y: row[sourceConfig.metrics[metric].yaxis],
              },
              row
            )
          );
        });
      });

      let newSeries = [];
      _.each(metrics, (metric) => {
        const series = seriesByMetric[metric];
        if (!$.isEmptyObject(series)) {
          $.each(series, function (key, serie) {
            const newSerie = $.extend({}, sourceConfig.metrics[metric], serie);
            newSeries.push(newSerie);
          });
        }
      });
      dataLoaded(newSeries);
    })
    .fail(() => {
      console.log("fail");
    });
}

function getType(metric) {
  const metricGroup = _.uniq(
    _.map(props.config.metrics, (metric) => {
      return metric.split(".")[0];
    })
  );
  const sourceConfig = store.dataSources[metricGroup];
  return sourceConfig.metrics[metric].type || "number";
}

function getLabel(metric) {
  const metricGroup = _.uniq(
    _.map(props.config.metrics, (metric) => {
      return metric.split(".")[0];
    })
  );
  const sourceConfig = store.dataSources[metricGroup];
  return sourceConfig.metrics[metric].label;
}

function getDesc(metric) {
  const metricGroup = _.uniq(
    _.map(props.config.metrics, (metric) => {
      return metric.split(".")[0];
    })
  );
  const sourceConfig = store.dataSources[metricGroup];
  return sourceConfig.metrics[metric].desc;
}

function dataLoaded(data) {
  // Help
  initGraphHelp();

  const chart = echarts.init(graphContainer.value);

  const yAxis = {};
  const metrics = _.map(props.config.metrics, (metric) => {
    return metric.split(".")[1];
  });
  _.each(metrics, (metric) => {
    const type = getType(metric);
    if (yAxis[type] == undefined) {
      const formatter = axisFormats[type];
      yAxis[type] = {
        type: "value",
        alignTicks: true,
        axisLabel: {
          formatter: formatter,
        },
      };
    }
  });

  const series = _.map(data, (serie) => {
    return {
      type: "line",
      name: serie.label,
      data: _.map(serie.data, (d) => [d.x, d.y]),
      yAxisIndex: _.keys(yAxis).indexOf(serie.type),
      symbol: "none",
    };
  });

  const option = {
    tooltip: {
      trigger: "axis",
      position: function (pt) {
        return [pt[0], "10%"];
      },
    },
    legend: {
      data: _.map(series, (serie) => serie.name),
    },
    xAxis: {
      type: "time",
      min: dateMath.parse(store.from).toDate(),
      max: dateMath.parse(store.to).toDate(),
    },
    yAxis: _.map(yAxis, (axis) => axis),
    series: series,
  };
  chart.setOption(option);
}

function initGraphHelp() {
  let labels = "";
  const metrics = _.map(props.config.metrics, (metric) => {
    return metric.split(".")[1];
  });
  _.each(metrics, (metric) => {
    labels =
      "<tr>" +
      "<td><b>" +
      getLabel(metric) +
      "</b></td>" +
      "<td>" +
      getDesc(metric) +
      "</td></td>" +
      labels;
  });
  const help = "<table>" + labels + '</table class="stack">';
  // add the hover info
  tippy(helpEl.value, {
    content: help,
    arrow: true,
    maxWidth: "100%",
    theme: "translucent",
    allowHTML: true,
  });
}

watch(
  () => store.from + store.to,
  () => {
    loadData();
  }
);
</script>
