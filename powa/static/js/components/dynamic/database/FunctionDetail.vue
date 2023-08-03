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
    <v-card-text v-if="stats !== undefined">
      <template v-if="stats">
        <v-row>
          <v-col cols="12">
            <pre
              class="sql"
            ><code v-html="formatSql(stats.func_name)"></code></pre>
          </v-col>
        </v-row>
        <v-row>
          <v-col cols="4" align="center">
            <b># of execution:</b> {{ stats.calls }}
          </v-col>
          <v-col cols="4" align="center">
            <b>Total time runtime:</b>
            <span class="duration">{{ formatDuration(stats.total_time) }}</span>
          </v-col>
          <v-col cols="4" align="center">
            <b>Self time runtime:</b>
            <span class="duration">{{ formatDuration(stats.self_time) }}</span>
          </v-col>
        </v-row>
        <template v-if="stats.last_refresh">
          Source code (refreshed at <b>{{ stats.last_refresh }}</b
          >):
          <v-row>
            <v-col cols="12">
              <pre class="sql"><code v-html="formatSql(stats.prosrc)"/></pre>
            </v-col>
          </v-row>
        </template>
        <template v-else>
          Source code not available, please refresh the catalog.
        </template>
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
