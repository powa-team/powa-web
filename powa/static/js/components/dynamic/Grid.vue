<template>
  <v-card :loading="loading">
    <v-card-item class="bg-surface">
      <v-card-title>
        {{ config.title }}
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
    <v-card-text v-if="data" class="pb-0">
      <v-row class="mb-4" justify="space-between">
        <v-col sm="6" md="4" xl="2">
          <v-text-field
            v-model="search"
            label="Search"
            :append-inner-icon="mdiMagnify"
            density="compact"
            hide-details
            class="pt-0 mt-0"
          ></v-text-field>
        </v-col>
        <v-col class="text-right">
          <v-btn size="small" @click="exportAsCsv">Export CSV</v-btn>
        </v-col>
      </v-row>
      <v-data-table
        :headers="headers"
        :items="data.data"
        :footer-props="{
          'items-per-page-options': [25, 50, -1],
        }"
        :items-per-page="25"
        :search="search"
        density="compact"
        :cell-props="getCellProps"
        class="superdense"
        hover
      >
        <!-- This template looks for columns with formatters and executes them -->
        <template
          v-for="column in columns.filter((column) =>
            column.hasOwnProperty('formatter')
          )"
          #[`item.${column.key}`]="{ item }"
        >
          <router-link
            v-if="column.urlAttr"
            :key="column.key"
            :to="getUrl(item[column.urlAttr])"
            exact-match
          >
            <grid-cell :value="item[column.key]" :column="column"></grid-cell>
          </router-link>
          <grid-cell
            v-else
            :key="column.key"
            :value="item[column.key]"
            :column="column"
          >
          </grid-cell>
        </template>
      </v-data-table>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { computed, ref } from "vue";
import _ from "lodash";
import size from "@/utils/size";
import "highlight.js/styles/default.css";
import { mdiMagnify, mdiLinkVariant } from "@mdi/js";
import { formatDuration } from "@/utils/duration";
import { formatPercentage } from "@/utils/percentage";
import GridCell from "@/components/GridCell.vue";
import { useDateRangeStore } from "@/stores/dateRange.js";
import { useDataLoader } from "@/composables/DataLoaderService.js";

const props = defineProps({
  config: {
    type: Object,
    default() {
      return {};
    },
  },
});

const metricGroup = _.uniq(
  _.map(props.config.metrics, (metric) => {
    return metric.split(".")[0];
  })
);

// The data source for the given chart
const { getUrl } = useDateRangeStore();
const { loading, source, data } = useDataLoader(metricGroup);
const search = ref("");

const fields = computed(() => {
  const metrics = _.map(props.config.metrics, (metric) => {
    return metric.split(".")[1];
  });

  const columns = props.config.columns;
  _.each(metrics, function (metric) {
    columns.push(Object.assign({}, source.value.config.metrics[metric]));
  });
  _.each(columns, (c) => {
    Object.assign(c, {
      key: c.name,
      label: c.label,
    });
  });
  return columns;
});

const columns = computed(() => {
  return _.uniqBy(
    _.map(fields.value, function headerize(n) {
      return {
        title: n.label,
        key: n.key,
        class: n.type,
        cellClass: n.type || "",
        formatter: getFormatter(n.type),
        type: n.type,
        align: getAlign(n.type),
        urlAttr: n.url_attr,
      };
    }),
    "key"
  );
});

const headers = computed(() => {
  if (!props.config.toprow) {
    return columns.value;
  }
  const h = [];
  let index = 0;
  _.each(props.config.toprow, (group) => {
    if (group.name) {
      h.push({
        title: group.name,
        align: "center",
        children: columns.value.slice(index, index + (group.colspan || 1)),
      });
      index += group.colspan || 1;
    } else {
      h.push(columns.value[index]);
      index++;
    }
  });
  return h;
});

function getCellProps(data) {
  return { class: data.column.cellClass };
}

function formatBool(value) {
  switch (value) {
    case true:
      return '<span class="text-success">✓</span>';
    case false:
      return '<span class="text-error">✗</span>';
    default:
      return '<span class="text-disabled">∅</span>';
  }
}

function formatSize(value) {
  return new size.SizeFormatter().fromRaw(value);
}

function getFormatter(type) {
  switch (type) {
    case "bool":
      return formatBool;
    case "duration":
      return (value) => formatDuration(value, true);
    case "percent":
      return (value) => formatPercentage(value);
    case "size":
      return formatSize;
    case "integer":
      return (value) => value.toLocaleString();
    default:
      return (value) => _.escape(value);
  }
}

function getAlign(type) {
  switch (type) {
    case "bool":
      return "center";
    case "duration":
    case "percent":
    case "size":
    case "integer":
      return "end";
  }
}

function exportAsCsv() {
  const labels = _.map(fields.value, "label");
  const keys = _.map(fields.value, "name");
  let csv = labels.join(",") + "\n";
  csv += _.map(data.value.data, (item) => {
    return _.map(keys, (key) => {
      let value = item[key];
      if (_.includes(value, ",") || _.includes(value, "\n")) {
        value = value.replace(/"/g, '""');
        value = '"' + value + '"';
      }
      return value;
    }).join(",");
  }).join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  downloadFile(blob, "export_powa.csv", "text/csv;charset=utf-8");
}

function downloadFile(content, fileName, mimeType) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const downloadLink = document.createElement("a");
  downloadLink.href = url;
  downloadLink.download = fileName;
  document.body.appendChild(downloadLink);
  downloadLink.click();
  document.body.removeChild(downloadLink);
  URL.revokeObjectURL(url);
}
</script>

<style lang="scss">
td a {
  text-decoration: none;
}
td.query a {
  color: inherit;
}
</style>
