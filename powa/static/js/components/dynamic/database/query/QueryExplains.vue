<template>
  <v-card :loading="loading" class="border">
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
    <v-card-text v-if="plans !== undefined">
      <template v-if="plans">
        <v-row>
          <v-col v-for="(plan, i) in plans" :key="i" cols="6">
            <v-chip label variant="outlined" density="compact" class="px-2"
              >{{ _.startCase(plan.title) }} values</v-chip
            >
            <br />
            <b>Executed:</b>
            {{ plan.exec_count }} times
            <br />
            <b>Average filter ratio:</b>
            {{ Math.round(plan.filter_ratio * 100, 2) }}%
            <br />
            Example plan:
            <pre class="sql mb-4"><code v-html="formatSql(plan.query)"/></pre>
            <pre class="sql"><code>{{plan.plan}}</code></pre>
          </v-col>
        </v-row>
      </template>
      <template v-else> No quals found for this query </template>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { useDataLoader } from "@/composables/DataLoaderService.js";
import { formatSql } from "@/utils/sql.js";
import _ from "lodash";

const props = defineProps({
  config: {
    type: Object,
    default() {
      return {};
    },
  },
});

const { loading, data: plans } = useDataLoader(props.config.name);
</script>
