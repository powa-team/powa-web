<template>
  <v-card
    :loading="loading"
    variant="flat"
    border
    style="overflow: initial; z-index: initial"
  >
    <v-card-item class="bg-surface">
      <v-card-title>
        {{ config.title }}
        <v-tooltip location="bottom" content-class="elevation-2">
          <template #activator="{ props: tooltipProps }">
            <v-icon
              class="pl-2"
              v-bind="tooltipProps"
              :icon="mdiInformationOutline"
            ></v-icon>
          </template>
          <div>
            <v-alert v-if="config.desc" class="ma-2 pa-3 ps-6">
              {{ config.desc }}
            </v-alert>
            <dl>
              <div v-for="metric in chosenMetrics" :key="metric">
                <dt>
                  <b>{{ getLabel(metric) }}</b>
                </dt>
                <dd class="ml-4">{{ getDesc(metric) }}</dd>
              </div>
            </dl>
          </div>
        </v-tooltip>
        <a
          v-if="config.url"
          :href="config.url"
          target="_blank"
          title="See the documentation"
        >
          <v-icon class="pl-2">
            {{ mdiLinkVariant }}
          </v-icon>
        </a>
      </v-card-title>
    </v-card-item>
    <v-card-text>
      <div
        ref="container"
        style="height: 180px; position: relative"
        :hidden="noData"
      >
        <div
          v-if="tooltip.content"
          class="chart-tooltip"
          :style="`transform: translate(${tooltip.x}px, ${
            tooltip.y
          }px) translateX(${tooltipTranslateX(tooltip)}) translateY(-50%)`"
        >
          <div>
            <div>
              <b>
                {{ tooltip.content["time"] }}
              </b>
            </div>
            <div
              v-for="metric in [...chosenMetrics].reverse()"
              :key="metric"
              class="d-flex justify-space-between"
            >
              <div class="d-flex align-center">
                <div
                  style="width: 12px; height: 3px; border-radius: 1px"
                  :style="`background: ${getColor(metric)}`"
                  class="mr-2"
                ></div>
                <div style="font-weight: 400; margin-left: 2px" class="mr-4">
                  {{ getLabel(metric) }}
                </div>
              </div>
              <div style="float: right; margin-left: 20px; font-weight: 900">
                {{ tooltip.content[metric] }}
              </div>
            </div>
          </div>
        </div>
        <div
          v-if="changesTooltip.event"
          class="chart-tooltip events"
          :style="`transform: translate(${changesTooltip.x}px, ${
            changesTooltip.y
          }px) translateX(${tooltipTranslateX(
            changesTooltip
          )}) translateY(${tooltipTranslateY(changesTooltip)})`"
        >
          <b>{{ timeFormat(changesTooltip.event.date) }}</b>
          <br />
          <template
            v-if="
              changesTooltip.event.kind == 'global' ||
              changesTooltip.event.kind == 'rds'
            "
          >
            <ul>
              <template v-for="(eventData, index) in changesTooltip.event.data">
                <li v-if="index <= 5" :key="eventData.name">
                  <b>{{ eventData.name }}</b>
                  changed:<br />
                  <v-chip label class="ma-2 pa-2" size="small">
                    <v-icon v-if="eventData.prev_is_dropped" size="small">{{
                      mdiCancel
                    }}</v-icon>
                    <span v-else>{{ eventData.prev_val }}</span>
                  </v-chip>
                  →
                  <v-chip label class="ma-2 pa-2" size="small">
                    <v-icon v-if="eventData.is_dropped" size="small">{{
                      mdiCancel
                    }}</v-icon>
                    <span v-else>{{ eventData.new_val || "&emsp;" }}</span>
                  </v-chip>
                  <template v-if="eventData.datname">
                    <br />on database <b>{{ eventData.datname }}</b>
                  </template>
                  <template v-if="eventData.setrole && eventData.setrole != 0">
                    <br />for role <b>{{ eventData.setrole }}</b>
                  </template>
                </li>
              </template>
            </ul>
            <div
              v-if="changesTooltip.event.data.length > 5"
              class="font-weight-light font-italic"
            >
              + {{ changesTooltip.event.data.length - 5 }} other settings
              changed
            </div>
          </template>
          <template v-else-if="changesTooltip.event.kind == 'reboot'">
            <v-icon size="small">{{ mdiAlert }}</v-icon>
            <b>Instance restarted!</b>
          </template>
          <template v-else>
            <v-icon size="small">{{ mdiAlert }}</v-icon>
            Unknown configChanges
            {{ changesTooltip.event.kind }}:<br />
            {{ changesTooltip.event.data }}
          </template>
        </div>
      </div>
      <div v-if="!noData" class="d-flex justify-space-between">
        <div
          v-for="(axis, type, index) in yAxisByType"
          :key="type"
          class="d-flex flex-wrap align-content-start"
        >
          <div
            v-for="metric in metricsByAxis(axis).reverse()"
            :key="metric"
            class="d-flex align-center pointer"
            :class="{
              'text-disabled': !chosenMetrics.includes(metric),
              'ml-auto': index == 1,
            }"
            @click="selectSerie(metric, $event)"
          >
            <div
              style="width: 12px; height: 3px; border-radius: 1px"
              :style="`background: ${getColor(metric)}; ${
                !chosenMetrics.includes(metric) ? 'opacity: 0.3' : ''
              }`"
              class="mr-2"
            ></div>
            <div style="font-weight: 400; margin-left: 2px" class="mr-4">
              {{ getLabel(metric) }}
            </div>
          </div>
        </div>
      </div>
      <div v-if="noData" class="text-center text-disabled">
        No data available
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import _ from "lodash";
import { storeToRefs } from "pinia";
import {
  mdiAlert,
  mdiCancel,
  mdiInformationOutline,
  mdiLinkVariant,
} from "@mdi/js";
/*import store from "@/store";*/
import { useRoute, useRouter } from "vue-router";
import * as d3 from "d3";
import size from "@/utils/size";
import { toISO } from "@/utils/dates";
import { formatDuration } from "@/utils/duration";
import { formatPercentage } from "@/utils/percentage";
import { useDateRangeStore } from "@/stores/dateRange.js";
import { useDashboardStore } from "@/stores/dashboard.js";
import { useDataLoader } from "@/composables/DataLoaderService.js";

const { changes, cursorPosition } = storeToRefs(useDashboardStore());

const props = defineProps({
  config: {
    type: Object,
    default() {
      return {};
    },
  },
});

const route = useRoute();
const router = useRouter();
const { from, to } = storeToRefs(useDateRangeStore());

const loading = ref(false);
const noData = ref(false);

const container = ref(null); // Container DOM Element

// List of metrics to show in the chart
// For example: 'avg_runtime', 'load', 'calls', 'planload'
const metrics = ref([]);

const chosenMetrics = ref([]);

// SVG Element
let svg;

const margin = { top: 20, right: 60, bottom: 20, left: 60 };
let width;
let height;

// The scaleTime for the X axis
let xScale;

// y axes by type
// Each item of this object has a scale and metrics property
let yAxisByType = {};

// line series
let series = [];

// The SVG <g> in which we display the dots appearing on hover
let markers;
// The SVG <g> containing the config changes markers
let changesEl;
// The SVG <g> in which we display the line showing cursor position
let cursorLine;

// The D3 brushX used for drag zoom
let brush;
// The SVG <g> used to show the brush
let gb;

// The metrics data
let data = {};
// The config changes data
let changesData = {};

const metricGroup = _.uniq(
  _.map(props.config.metrics, (metric) => {
    return metric.split(".")[0];
  })
);
if (metricGroup.length > 1) {
  console.error(
    "metrics from different datasources on a single widget are not supported"
  );
}
// The data source for the given chart
const { source, data: data_ } = useDataLoader(metricGroup);
// Whether or not to use stack
let stacked = false;
// The stack generator if required
let stack;

const defaultScheme = [
  "rgb(203, 81, 58)",
  "rgb(115, 192, 58)",
  "rgb(101, 185, 172)",
  "rgb(70, 130, 180)",
  "rgb(150, 85, 126)",
  "rgb(120, 95, 67)",
  "rgb(133, 135, 114)",
  "rgb(181, 182, 169)",
  "rgb(199, 180, 57)",
];

const colors = props.config.color_scheme || defaultScheme;

// The tooltip
const tooltip = ref({
  x: 0,
  y: 0,
  content: "",
});

// The tooltip for the config changes
const changesTooltip = ref({
  x: 0,
  y: 0,
  event: null,
});

const transitionDuration = 400;

const formatMillisecond = d3.timeFormat(".%L"),
  formatSecond = d3.timeFormat(":%S"),
  formatMinute = d3.timeFormat("%H:%M"),
  formatHour = d3.timeFormat("%H:00"),
  formatDay = d3.timeFormat("%a %d"),
  formatWeek = d3.timeFormat("%b %d"),
  formatMonth = d3.timeFormat("%B"),
  formatYear = d3.timeFormat("%Y");

function multiFormat(date) {
  return (
    d3.timeSecond(date) < date
      ? formatMillisecond
      : d3.timeMinute(date) < date
      ? formatSecond
      : d3.timeHour(date) < date
      ? formatMinute
      : d3.timeDay(date) < date
      ? formatHour
      : d3.timeMonth(date) < date
      ? d3.timeWeek(date) < date
        ? formatDay
        : formatWeek
      : d3.timeYear(date) < date
      ? formatMonth
      : formatYear
  )(date);
}

// Unit to show on the Y axes
const unit = {
  size: "Bytes",
  sizerate: "Bytes per sec",
  duration: "duration in ms",
  percent: "%",
};

// Value formatters
const valueFormats = {
  size: new size.SizeFormatter().fromRaw,
  sizerate: new size.SizeFormatter({ suffix: "ps" }).fromRaw,
  duration: (value) => formatDuration(value, true),
  percent: (value) => formatPercentage(value),
  number: (value) => (!_.isNil(value) ? d3.format(".2s")(value) : "-"),
  integer: d3.format(".2s"),
};

// Time formatter
const timeFormat = d3.timeFormat("%Y-%m-%d %H:%M:%S");

let unwatch;
let unwatchCursorPosition;
onMounted(async () => {
  // Await for next tick in case we're in a tab item
  await nextTick();

  metrics.value = _.map(props.config.metrics, (metric) => {
    return metric.split(".")[1];
  });
  chosenMetrics.value = metrics.value;

  initChart();
  unwatch = watch(
    () => [data_.value, changes.value],
    () => {
      loading.value = true;
      // make sure both data and changes are loaded before drawing the chart
      if (data_.value && changes.value) {
        loadData();
      }
    },
    { immediate: true }
  );
  unwatchCursorPosition = watch(cursorPosition, (date) => {
    cursorLine
      .selectAll("line")
      .attr("display", _.isNil(date) ? "none" : "")
      .attr("x1", xScale(date))
      .attr("x2", xScale(date));
  });
  window.addEventListener("resize", resize);
});

onUnmounted(() => {
  window.removeEventListener("resize", resize);
  unwatch && unwatch();
  unwatchCursorPosition && unwatchCursorPosition();
});

function resize() {
  initChart();
  drawOrUpdateChart();
  changesLoaded();
}

function initChart() {
  width = container.value.offsetWidth - margin.left - margin.right;
  height = container.value.offsetHeight - margin.top - margin.bottom;

  // remove any previously existing chart (useful for resize)
  svg = d3.select(container.value).selectAll("svg").remove();

  svg = d3
    .select(container.value)
    .append("svg")
    .attr("class", "chart")
    .attr("width", width)
    .attr("height", height)
    .attr("viewBox", [0, 0, width, height])
    .attr("style", "max-width: 100%; height: auto; height: intrinsic;")
    .style("-webkit-tap-highlight-color", "transparent")
    .style("overflow", "visible")
    .attr("transform", `translate(0, ${margin.top})`);

  stacked = props.config.stack;

  // Create the group for the changes
  changesEl = svg
    .append("g")
    .attr("class", "changes")
    .attr("transform", `translate(0, ${height})`)
    .on("pointerenter pointermove", eventspointermoved)
    .on("pointerleave", eventspointerleft);

  // prepare the grids
  const grids = svg.append("g").attr("class", "grids");
  grids
    .append("g")
    .attr("class", "x axis-grid")
    .attr("transform", `translate(0, ${height})`);

  grids.append("g").attr("class", "y axis-grid");

  // Create the group to display the series
  const lines = svg
    .append("g")
    .attr("class", "lines")
    .on("pointerenter pointermove", pointermoved)
    .on("pointerleave", pointerleft);

  // Create the group in which to show the circles on hover
  markers = svg.append("g").style("pointer-events", "none");

  // Create the group in which to show the vertical line showing cursor position
  cursorLine = svg.append("g").attr("class", "cursor-line");

  cursorLine
    .append("line")
    .attr("display", "none")
    .attr("y1", 0)
    .attr("y2", height);

  // For each metric prepare the container for the line path
  let index = 0;
  _.each(metrics.value, (metric) => {
    const type = source.value.config.metrics[metric].type || "number";
    if (!_.has(yAxisByType, type)) {
      yAxisByType[type] = {
        metrics: [],
        scale: d3.scaleLinear().range([height, 0]),
      };
    }
    yAxisByType[type].metrics.push(metric);
    if (_.keys(yAxisByType).length > 2) {
      throw "More than two yAxis is not supported";
    }

    if (!stacked) {
      series.push(
        d3
          .line()
          .defined((d) => !_.isNil(d[metric]))
          .x((d) => xScale(d.date))
          .y((d) => yAxisByType[type].scale(d[metric]))
      );
      lines.append("path").attr("class", "line line" + index);
    } else {
      series.push(
        d3
          .area()
          .x((d) => xScale(d.data.date))
          .y0(([y1]) => yAxisByType[type].scale(y1))
          .y1(([, y2]) => yAxisByType[type].scale(y2))
      );
      lines.append("path").attr("class", "area area" + index);
    }
    markers
      .append("circle")
      .attr("display", "none")
      .attr("fill", colors[index])
      .attr("stroke", "#555")
      .attr("stroke-width", "0.5px")
      .attr("r", 3);
    index++;
  });

  // Create the brush for the drag zoom
  brush = d3
    .brushX()
    .extent([
      [0, 0],
      [width, height],
    ])
    .on("end", brushended);
  gb = lines.append("g").call(brush);

  // prepare the x axis
  svg
    .append("g")
    .attr("class", "x axis")
    .attr("transform", `translate(0,${height})`);

  // Prepare the 2 y axes
  svg.append("g").attr("class", "y axis0");
  svg
    .append("g")
    .attr("class", "y axis1")
    .attr("transform", `translate(${width}, 0)`);
}

function loadData() {
  dataLoaded();
  drawOrUpdateChart();

  // make sure we group changes by ts in order to have one tooltip for each
  // change date
  const grouped = _.groupBy(_.cloneDeep(changes.value.data), "ts");
  _.forEach(grouped, (a, key) => {
    if (_.uniq(_.map(a, "kind")).length > 1) {
      console.error("Multiple 'kind' values for the same 'ts'");
    }
    grouped[key] = Object.assign(a[0], {
      data: _.reduce(
        a,
        (result, n) => {
          result.push(n.data);
          return result;
        },
        []
      ),
    });
  });

  changesData = _.values(grouped);
  changesLoaded();
  loading.value = false;
}

function dataLoaded() {
  data = data_.value.data;
  if (_.isEmpty(data)) {
    noData.value = true;
    return;
  } else {
    noData.value = false;
  }
  // Parse time and convert it to JS Date
  data.forEach(function (d) {
    d.date = new Date(d.ts * 1000);
  });
}

function drawOrUpdateChart() {
  // Draw X Axis
  xScale = d3.scaleTime().range([0, width]).domain([from.value, to.value]);

  const ticksCount = 5;
  const xAxis = d3
    .axisBottom(xScale)
    .ticks(ticksCount)
    .tickSizeOuter(0)
    .tickFormat(multiFormat);

  d3.select(container.value)
    .select(".x.axis")
    .transition(transitionDuration)
    .call(xAxis);

  // Draw X Axis grid lines
  const xAxisGrid = d3
    .axisBottom(xScale)
    .tickSizeOuter(0)
    .tickSizeInner(-height)
    .ticks(ticksCount)
    .tickFormat("");
  d3.select(container.value).select(".x.axis-grid").call(xAxisGrid);

  // Stack generator to be used when
  stack = d3
    .stack()
    .keys(chosenMetrics.value)
    .order(d3.stackOrderNone)
    .offset(d3.stackOffsetNone);

  // Compute the extent for the y axis
  _.each(yAxisByType, (axis) => {
    let max = 0;
    if (!stacked) {
      _.each(axis.metrics, (metric) => {
        if (chosenMetrics.value.includes(metric)) {
          max = Math.max(
            max,
            d3.max(data, (d) => d[metric] || 0)
          );
        }
      });
    } else {
      const stackedData = stack(data);
      const extent = d3.extent(stackedData.flat(2));
      // We use toPrecision here to prevent max being 100.0000000001 in some cases
      max = extent[1];
      if (max) {
        max = max.toPrecision(5);
      }
    }
    max = max || 1; // Prevent empty domain
    axis.scale.domain([0, max]).nice();
  });

  // Then draw the Y axes
  let axisIndex = 0;
  let yAxisGrid;
  _.each(yAxisByType, (axis, type) => {
    const show = _.some(axis.metrics, (metric) =>
      chosenMetrics.value.includes(metric)
    );
    let axisGenerator = axisIndex == 0 ? d3.axisLeft : d3.axisRight;
    d3.select(container.value)
      .select(`.y.axis${axisIndex}`)
      .attr("display", show ? null : "none")
      .transition(transitionDuration)
      .call(axisGenerator(axis.scale).ticks(ticksCount, "s"));

    // Draw axis grid lines but only for one axis
    if (!yAxisGrid && show) {
      yAxisGrid = d3
        .axisLeft(axis.scale)
        .tickSizeOuter(0)
        .tickSizeInner(-width)
        .ticks(ticksCount)
        .tickFormat("");
      d3.select(container.value)
        .select(".y.axis-grid")
        .transition(transitionDuration)
        .call(yAxisGrid);
    }

    d3.select(container.value)
      .select(`.y.axis${axisIndex}`)
      .append("g")
      .attr("opacity", 1)
      .attr("class", "tick")
      .append("text")
      .attr("fill", "currentColor")
      .attr("transform", "rotate(-90)")
      .attr("y", axisIndex == 0 ? 6 : 0)
      .attr("dy", axisIndex == 0 ? "0.71em" : "-0.71em")
      .style("text-anchor", "end")
      .text(unit[type])
      .clone(true)
      .lower()
      .attr("aria-hidden", "true")
      .attr("class", "clone");

    axisIndex++;
  });

  // Then draw the lines or areas
  let index = 0;
  _.each(series, (serie) => {
    const chosenIndex = chosenMetrics.value.indexOf(metrics.value[index]);
    const isChosen = chosenIndex != -1;
    if (!stacked) {
      svg
        .transition(transitionDuration)
        .select(".line.line" + index)
        .attr("stroke", colors[index])
        .attr("class", "line line" + index)
        .attr("d", serie(isChosen ? data : []));
    } else {
      const stackedData = isChosen ? stack(data)[chosenIndex] : [];
      svg
        .transition(transitionDuration)
        .select(".area.area" + index)
        .attr("fill", colors[index])
        .attr("d", serie(stackedData));
    }
    index++;
  });
}

function getLabel(metric) {
  return source.value.config && source.value.config.metrics[metric].label;
}

function getDesc(metric) {
  return source.value.config && source.value.config.metrics[metric].desc;
}

function pointermoved(event) {
  if (!data || _.isEmpty(data)) {
    return;
  }
  const X = d3.map(data, (d) => d.date);
  const [pointerX, pointerY] = d3.pointer(event);

  const i = d3.bisectCenter(X, xScale.invert(pointerX));

  const content = {
    time: timeFormat(X[i]),
  };
  const markersData = [];
  _.each(chosenMetrics.value, (metric, index) => {
    const Y = d3.map(data, (d) => {
      return d[metric];
    });
    const Y2 = stack(data)[index];
    const type = source.value.config.metrics[metric].type || "number";
    content[metric] = valueFormats[type](Y[i]);
    markersData.push([
      metric,
      yAxisByType[type].scale(stacked ? Y2[i][1] : Y[i]),
    ]);
  });
  markers
    .selectAll("circle")
    .data(markersData)
    .attr("fill", (d) => getColor(d[0]))
    .attr("display", (d) => _.isNil(d[1] ? "none" : null))
    .attr("transform", (d) =>
      !_.isNil(d[1]) ? `translate(${xScale(X[i])}, ${d[1]})` : null
    );
  tooltip.value = {
    x: pointerX + margin.left,
    y: pointerY + margin.top,
    clientX: event.clientX,
    clientY: event.clientY,
    content: content,
  };

  cursorPosition.value = X[i];
}

function pointerleft() {
  tooltip.value.content = null;
  markers.selectAll("circle").attr("display", "none");
  cursorPosition.value = null;
}

function eventspointermoved(evt) {
  if (!changesData || _.isEmpty(changesData)) {
    return;
  }
  const X = d3.map(changesData, (d) => d.date);
  const [pointerX] = d3.pointer(evt);
  const i = d3.bisectCenter(X, xScale.invert(pointerX));
  changesTooltip.value = {
    x: xScale(X[i]) + margin.left,
    y: 40,
    clientX: evt.clientX,
    clientY: evt.clientY,
    event: changesData[i],
  };
}

function eventspointerleft() {
  changesTooltip.value.event = null;
}

function brushended({ selection }) {
  if (selection) {
    const from = toISO(xScale.invert(selection[0]));
    const to = toISO(xScale.invert(selection[1]));
    router.push({
      path: route.path,
      query: { from, to },
    });

    gb.call(brush);
    gb.call(brush.move, null);
  }
}

function changesLoaded() {
  changesData.forEach(function (d) {
    d.date = new Date(d.ts * 1000);
  });

  const events = changesEl.selectAll(".event").data(changesData);

  // Create markers for new changes
  const g = events
    .enter()
    .append("g")
    .attr("class", "event")
    .attr("transform", (d) => `translate(${xScale(d.date)}, ${-height - 10})`);

  g.append("line")
    .attr("class", "event-line")
    .attr("stroke", "#555")
    .attr("x1", 0)
    .attr("y1", 10)
    .attr("x2", 0)
    .attr("y2", height + 10);

  g.append("polygon")
    .attr("class", "marker")
    .attr("fill", "#999")
    .attr("points", "0,5 -4,0 0,-5 4,0")
    .attr("transform", () => "scale(0.7)");

  g.append("circle")
    .attr("fill", "transparent")
    .attr("class", "pointer")
    .attr("r", 5);

  // Move already existing elements
  events
    .merge(events)
    .attr("transform", (d) => `translate(${xScale(d.date)}, ${-height - 10})`);

  // Remove changes that don't exist anymore
  events.exit().remove();
}

function tooltipTranslateX(tooltip) {
  return tooltip.clientX > window.innerWidth / 2 ? "-120%" : "20%";
}

function tooltipTranslateY(tooltip) {
  return tooltip.clientY > window.innerHeight / 2 ? "-100%" : "0";
}

function metricsByAxis(axis) {
  return _.filter(
    metrics.value,
    (metric) => axis.metrics.indexOf(metric) != -1
  );
}

function getColor(metric) {
  return colors[metrics.value.indexOf(metric)];
}

function selectSerie(metric, event) {
  if (event.ctrlKey || event.metaKey) {
    if (chosenMetrics.value.includes(metric)) {
      _.remove(chosenMetrics.value, (m) => m == metric);
    } else {
      chosenMetrics.value = chosenMetrics.value.concat([metric]);
    }
  } else {
    if (_.isEqual(chosenMetrics.value, [metric])) {
      chosenMetrics.value = metrics.value;
    } else {
      chosenMetrics.value = [metric];
    }
  }
  // Ensure that order from original metrics list is kept and metrics are unique
  chosenMetrics.value = _.intersection(metrics.value, chosenMetrics.value);

  drawOrUpdateChart();
}
</script>
<style lang="scss" scope>
svg.chart {
  display: block;
  margin: auto;
}
.line {
  fill: none;
  stroke-width: 1.5px;
}

.pointer {
  cursor: pointer;
}

.axis-grid .domain {
  display: none;
}
.axis-grid line {
  fill: none;
  shape-rendering: crispEdges;
  stroke: rgb(var(--v-theme-axisgridlinestroke));
  stroke-width: 1px;
}

.cursor-line line {
  stroke: currentColor;
  stroke-width: 1px;
  stroke-dasharray: 4;
  pointer-events: none;
}

.tick text.clone {
  fill: none;
  stroke: rgb(var(--v-theme-tickstroke));
  stroke-width: 2px;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.chart-tooltip {
  position: absolute;
  top: -10px;
  background-color: rgb(var(--v-theme-background));
  padding: 0.3rem 0.5rem;
  border-radius: 3px;
  box-shadow: rgba(0, 0, 0, 0.3) 0px 0px 3px 0px;
  pointer-events: none;
  z-index: 100;
}

.event {
  line {
    display: none;
  }

  &:hover {
    .marker {
      fill: black;
    }
    line {
      display: block;
    }
  }
}
</style>
