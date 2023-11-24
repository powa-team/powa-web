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
    <v-card-text v-if="stats !== undefined">
      <template v-if="stats">
        <v-row>
          <v-col cols="12">
            <pre class="sql"><code v-html="formatSql(stats.query)"/></pre>
          </v-col>
        </v-row>
        <v-row>
          <v-col cols="4" align="center">
            <b># of execution:</b> {{ stats.calls }}
          </v-col>
          <v-col cols="4" align="center">
            <b>Total runtime:</b>
            <span class="duration">{{ formatDuration(stats.runtime) }}</span>
          </v-col>
          <v-col cols="4" align="center">
            <b>Hit ratio:</b>
            <template v-if="stats.total_blks && stats.total_blks > 0">
              {{
                Math.round(
                  (stats.shared_blks_hit * 100) / stats.total_blks,
                  2
                ) + "%"
              }}
            </template>
            <template v-else> N/A </template>
          </v-col>
        </v-row>
      </template>
      <template v-else> No data </template>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { useFetch } from "@/utils/fetch.js";
import { formatSql } from "@/utils/sql.js";
import { formatDuration } from "@/utils/duration.js";

const props = defineProps({
  config: {
    type: Object,
    default() {
      return {};
    },
  },
});

const { loading, data: stats } = useFetch(props.config.name);
</script>
