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
    <v-card-text v-if="qual !== undefined">
      <template v-if="qual">
        <pre
          class="sql"
        ><code v-html="formatSql(qual.where_clause)"></code></pre>
        <v-row>
          <v-col>
            <b>Seen:</b><br />
            {{ qual.occurences }}
          </v-col>
          <v-col>
            <b>Average evaluations by query:</b><br />
            {{ qual.execution_count / qual.occurences }}<br />
            <b>Average number of filtered tuples:</b><br />
            {{ qual.avg_filter }}
          </v-col>
          <v-col>
            <b>Filter ratio:</b><br />
            {{ qual.filter_ratio.toPrecision(4) }} % of tuples are removed by
            the filter.
          </v-col>
        </v-row>
        <div v-for="(q, index) in qual.quals" :key="index">
          <pre class="sql"><code v-html="formatSql(q.label)"></code></pre>
          <v-row>
            <v-col>
              <b>Table:</b><br />
              {{ q.relname }}
            </v-col>
            <v-col>
              <b>Column:</b><br />
              {{ q.attname }}
            </v-col>
            <v-col>
              <b>Accesstype:</b><br />
              {{ q.eval_type == "i" ? "Index" : "After Scan" }}
            </v-col>
          </v-row>
        </div>
      </template>
      <template v-else> No data </template>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { useFetch } from "@/utils/fetch.js";
import { formatSql } from "@/utils/sql.js";

const props = defineProps({
  config: {
    type: Object,
    default() {
      return {};
    },
  },
});

const { loading, data: qual } = useFetch(props.config.name);
</script>
