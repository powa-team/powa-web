<template>
  <v-card :loading="loading">
    <template #progress>
      <v-progress-linear
        height="2"
        indeterminate
        style="position: absolute; z-index: 1"
      ></v-progress-linear>
    </template>
    <v-card-item flat height="40px;">
      <v-card-title class="pl-0">{{ config.title }}</v-card-title>
    </v-card-item>
    <v-card-text v-if="plans !== undefined">
      <template v-if="plans">
        <v-row>
          <v-col v-for="(plan, i) in plans" :key="i" cols="6">
            <h5>{{ _.startCase(plan.title) }} values</h5>
            <b>Executed:</b> {{ plan.exec_count }} times
            <br />
            <b>Average filter ratio:</b>
            {{ Math.round(plan.filter_ratio * 100, 2) }}%
            <h6 class="subheader">Example plan:</h6>
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
import { useFetch } from "@/utils/fetch.js";
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

const { loading, data: plans } = useFetch(props.config.name);
</script>
