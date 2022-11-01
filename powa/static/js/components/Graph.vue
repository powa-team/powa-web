<template>
  <v-card :loading="loading" outlined>
    <template #progress>
      <v-progress-linear
        height="2"
        indeterminate
        style="position: absolute"
      ></v-progress-linear>
    </template>
    <v-app-bar flat height="40px;">
      <v-toolbar-title class="mx-auto">
        {{ config.title }}
        <v-tooltip bottom>
          <template #activator="{ on, attrs }">
            <v-icon class="pl-2" v-bind="attrs" v-on="on">
              {{ mdiInformation }}
            </v-icon>
          </template>
          <div>
            <dl>
              <div v-for="metric in metrics" :key="metric">
                <dt>
                  <b>{{ getLabel(metric) }}</b>
                </dt>
                <dd class="ml-4">{{ getDesc(metric) }}</dd>
              </div>
            </dl>
          </div>
        </v-tooltip>
      </v-toolbar-title>
    </v-app-bar>
    <v-card-text>
      <div ref="graphContainer" style="height: 400px" />
    </v-card-text>
  </v-card>
</template>

<script setup>
import { onMounted, ref, watch } from "vue";
import * as _ from "lodash";
import * as echarts from "echarts/lib/echarts";
import "echarts/lib/chart/line";
import "echarts/lib/component/tooltip";
import "echarts/lib/component/legend";
import "echarts/lib/component/grid";
import { mdiInformation } from "@mdi/js";
import { dateMath } from "@grafana/data";
import size from "../utils/size";
import store from "../store";
import moment from "moment";
import "../utils/precisediff";
import $ from "jquery";

const props = defineProps({
  config: {
    type: Object,
    default() {
      return {};
    },
  },
});

const loading = ref(false);

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

const chart = ref();

const metrics = ref();

onMounted(() => {
  chart.value = echarts.init(graphContainer.value);
  loadData();
});

function loadData() {
  chart.value.showLoading();
  loading.value = true;
  const metricGroup = _.uniq(
    _.map(props.config.metrics, (metric) => {
      return metric.split(".")[0];
    })
  );
  metrics.value = _.map(props.config.metrics, (metric) => {
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

      _.each(metrics.value, (metric) => {
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
        _.each(metrics.value, (metric) => {
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
      _.each(metrics.value, (metric) => {
        const series = seriesByMetric[metric];
        if (!$.isEmptyObject(series)) {
          $.each(series, function (key, serie) {
            const newSerie = $.extend({}, sourceConfig.metrics[metric], serie);
            newSeries.push(newSerie);
          });
        }
      });
      dataLoaded(newSeries);
      loading.value = false;
    })
    .fail(() => {
      console.log("fail");
      loading.value = false;
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
    animation: false,
  };
  chart.value.setOption(option);
  chart.value.hideLoading();
  window.addEventListener("resize", function () {
    chart.value.resize();
  });
}

watch(
  () => store.from + store.to,
  () => {
    loadData();
  }
);
</script>
