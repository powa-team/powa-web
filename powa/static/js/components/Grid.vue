<template>
  <v-card :loading="loading">
    <template #progress>
      <v-progress-linear
        height="2"
        indeterminate
        style="position: absolute; z-index: 1"
      ></v-progress-linear>
    </template>
    <v-app-bar flat height="40px;">
      <v-toolbar-title>
        <v-card-title class="pl-0">{{ config.title }}</v-card-title>
      </v-toolbar-title>
    </v-app-bar>
    <v-card-text class="pb-0">
      <v-row>
        <v-col cols="12" sm="6" md="4" xl="2">
          <v-text-field
            v-model="search"
            label="Search"
            :append-icon="mdiMagnify"
            single-line
            hide-details
            class="pt-0 mt-0"
          ></v-text-field>
        </v-col>
      </v-row>
      <v-data-table
        :headers="headers"
        :items="items"
        :footer-props="{
          'items-per-page-options': [25, 50, -1],
        }"
        :items-per-page="25"
        :search="search"
        :dense="true"
        hide-default-header
        class="superdense"
      >
        <template #header>
          <thead class="v-data-table-header">
            <tr>
              <th
                v-for="header in headers"
                :key="header.value"
                :class="header.class"
              >
                {{ header.text }}
              </th>
            </tr>
          </thead>
        </template>
        <template #item="{ item }">
          <tr class="clickable" @click="onRowClicked(item)">
            <td v-for="field in fields" :key="field.key" :class="field.type">
              <template
                v-if="field.type == 'query' || field.type == 'where_clause'"
              >
                <!-- eslint-disable-next-line vue/no-v-html -->
                <pre v-html="field.formatter(item[field.key])" />
              </template>
              <template v-else>
                {{ field.formatter(item[field.key]) }}
              </template>
            </td>
          </tr>
        </template>
      </v-data-table>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import store from "../store";
import { serialize } from "../store";
import { dateMath } from "@grafana/data";
import * as _ from "lodash";
import $ from "jquery";
import * as moment from "moment";
import size from "../utils/size";
import hljs from "highlight.js";
import "highlight.js/styles/default.css";
import pgsql from "highlight.js/lib/languages/pgsql";
import { mdiMagnify } from "@mdi/js";

hljs.registerLanguage("pgsql", pgsql);

const props = defineProps({
  config: {
    type: Object,
    default() {
      return {};
    },
  },
});

const loading = ref(false);
const search = ref("");
const items = ref([]);

onMounted(() => {
  loadData();
});

const fields = computed(() => {
  const metricGroup = _.uniq(
    _.map(props.config.metrics, (metric) => {
      return metric.split(".")[0];
    })
  );
  const metrics = _.map(props.config.metrics, (metric) => {
    return metric.split(".")[1];
  });
  const sourceConfig = store.dataSources[metricGroup];

  const columns = props.config.columns;
  _.each(metrics, function (metric) {
    columns.push($.extend({}, sourceConfig.metrics[metric]));
  });
  _.each(columns, (c) => {
    $.extend(c, {
      key: c.name,
      label: c.label,
      formatter: getFormatter(c.type),
      class: c.type,
    });
  });
  return columns;
});

const headers = computed(() => {
  return _.uniqBy(
    _.map(fields.value, function headerize(n) {
      return {
        text: n.label,
        value: n.key,
        class: n.type,
      };
    }),
    "value"
  );
});

function loadData() {
  loading.value = true;
  const metricGroup = _.uniq(
    _.map(props.config.metrics, (metric) => {
      return metric.split(".")[0];
    })
  );
  const sourceConfig = store.dataSources[metricGroup];
  const params = {
    from: dateMath.parse(store.from).format("YYYY-MM-DD HH:mm:ssZZ"),
    to: dateMath.parse(store.to, true).format("YYYY-MM-DD HH:mm:ssZZ"),
  };
  $.ajax({
    url: sourceConfig.data_url + "?" + $.param(params),
  }).done((response) => {
    dataLoaded(response.data);
    loading.value = false;
  });
}

function dataLoaded(data) {
  items.value = data;
}

function formatBool(value) {
  return value ? "✓" : "✗";
}

function formatDuration(value) {
  return moment(parseFloat(value, 10)).preciseDiff(moment(0), true);
}

function formatSize(value) {
  return new size.SizeFormatter().fromRaw(value);
}

function formatQuery(value) {
  return hljs.highlightAuto(value, ["pgsql"]).value;
}

function getFormatter(type) {
  switch (type) {
    case "bool":
      return formatBool;
    case "duration":
      return formatDuration;
    case "percent":
      return (value) => value + "%";
    case "query":
      return formatQuery;
    case "size":
      return formatSize;
    default:
      return (value) => value;
  }
}

function onRowClicked(row) {
  if (row.url) {
    window.location.href = [row.url, serialize(store.from, store.to)].join("?");
  }
}

watch(
  () => store.from + store.to,
  () => {
    loadData();
  }
);
</script>

<style lang="scss">
.v-data-table.superdense > .v-data-table__wrapper > table {
  tbody,
  thead,
  tfoot {
    td {
      white-space: nowrap;

      &.query {
        width: 50%;
        overflow: hidden;
        max-width: 0;
        pre,
        code {
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          margin-bottom: 0;
        }
      }
    }
    th,
    td {
      padding: 0 0.3rem;
      &.duration,
      &.integer,
      &.number,
      &.size {
        text-align: right;
      }
      &.bool {
        text-align: center;
      }
    }
    .clickable {
      cursor: pointer;
    }
  }
}
</style>
