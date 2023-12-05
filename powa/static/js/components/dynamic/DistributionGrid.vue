<template>
  <v-card :loading="loading">
    <template #progress>
      <v-progress-linear
        height="2"
        indeterminate
        style="position: absolute; z-index: 1"
      ></v-progress-linear>
    </template>
    <v-card-item class="bg-surface">
      <v-card-title class="pl-0">{{ config.title }}</v-card-title>
    </v-card-item>
    <v-table density="compact" class="superdense">
      <template #default>
        <thead>
          <tr>
            <th>Value</th>
            <th class="text-right">{{ sourceConfig.metrics[metric].label }}</th>
            <th>% {{ sourceConfig.metrics[metric].label }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in items" :key="item.name">
            <td>{{ item.name }}</td>
            <td class="text-right">{{ item.value }}</td>
            <td>
              <div class="d-flex align-center">
                <div
                  class="d-inline-block bg-primary border"
                  style="height: 15px; min-width: 1px"
                  :style="{ width: (item.value / total) * 100 + '%' }"
                ></div>
                <strong class="ml-2">
                  {{ formatPercentage((item.value / total) * 100) }}
                </strong>
              </div>
            </td>
          </tr>
        </tbody>
      </template>
    </v-table>
  </v-card>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import _ from "lodash";
import { formatPercentage } from "@/utils/percentage";
import { useStoreService } from "@/composables/useStoreService";

const props = defineProps({
  config: {
    type: Object,
    default() {
      return {};
    },
  },
});

const loading = ref(false);

const items = ref([]);
const metric = ref([]);
const { dataSources } = useStoreService();
onMounted(() => {
  watch(
    () => dataSources.value,
    () => {
      loadData();
    },
    { immediate: true }
  );
});

const metricGroup = _.uniq(
  _.map(props.config.metrics, (metric) => {
    return metric.split(".")[0];
  })
);
metric.value = props.config.metrics[0].split(".")[1];
const sourceConfig = dataSources.value[metricGroup];

function loadData() {
  loading.value = true;
  sourceConfig.promise.then((response) => {
    dataLoaded(JSON.parse(response).data);
    loading.value = false;
  });
}

function dataLoaded(data) {
  items.value = _.map(data, (datum) => {
    const names = datum[props.config.x_label_attr];
    let name;
    if (_.isArray(names)) {
      name = _.map(names, (n) => String(n)).join(", ");
    } else {
      name = names;
    }

    return {
      name: name,
      value: datum[metric.value],
    };
  });
}
const total = computed(() => _.sumBy(items.value, "value"));
</script>
