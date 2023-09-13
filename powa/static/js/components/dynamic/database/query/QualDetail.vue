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
    <v-card-text v-if="qual !== undefined">
      <template v-if="qual">
        <h4>
          <pre
            class="sql"
          ><code v-html="formatSql(qual.where_clause)"></code></pre>
        </h4>
        <div>
          <dl>
            <dt>Seen:</dt>
            <dd>{{ qual.occurences }}</dd>
            <dt>Average evaluations by query</dt>
            <dd>{{ qual.execution_count / qual.occurences }}</dd>
            <dt>Average number of filtered tuples:</dt>
            <dd>{{ qual.avg_filter }}</dd>
            <dt>Filter ratio</dt>
            <dd>
              {{ qual.filter_ratio.toPrecision(4) }} % of tuples are removed by
              the filter.
            </dd>
          </dl>
        </div>
        <ul>
          <li v-for="(q, index) in qual.quals" :key="index">
            <h5>
              <pre class="sql"><code v-html="formatSql(q.label)"></code></pre>
            </h5>
            <dl>
              <dt>Table</dt>
              <dd>{{ q.relname }}</dd>
              <dt>Column</dt>
              <dd>{{ q.attname }}</dd>
              <dt>Accesstype</dt>
              <dd :class="'access-type-' + q.eval_type">
                {{ q.eval_type == "i" ? "Index" : "After Scan" }}
              </dd>
            </dl>
          </li>
        </ul>
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
