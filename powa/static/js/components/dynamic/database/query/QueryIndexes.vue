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
    <v-card-text v-if="data !== undefined">
      <template v-if="data">
        <v-row data-equalizer>
          <v-col cols="4">
            <ul v-if="data.indexes">
              <li v-for="(inds, clause) in data.indexes" :key="clause">
                <h5>
                  Possible indexes for attributes present in
                  <br />
                  <b><code v-html="formatSql(clause)"></code></b>:
                </h5>
                <ul v-for="(index, i) in inds" :key="i">
                  <h6>
                    With access method <em>{{ index.amname }}</em>
                  </h6>
                  <li>
                    <ul>
                      <li v-for="(qual, j) in index.qual" :key="j">
                        <dl>
                          <dt>Attribute</dt>
                          <dd>{{ qual.relname }}.{{ qual.attname }}</dd>
                          <dt>Data distribution</dt>
                          <dd v-if="!qual.distinct_values">Unknown</dd>
                          <dd v-else>
                            approximately
                            <b>{{ qual.distinct_values }}</b> distinct values
                          </dd>
                        </dl>
                      </li>
                    </ul>
                  </li>
                </ul>
              </li>
            </ul>
            <template v-else> No suitable index to suggest. </template>
          </v-col>
          <v-col cols="8">
            <template v-if="data.hypoplan">
              <v-row>
                <v-col cols="12">
                  <template v-if="data.hypoplan.indexes">
                    The following indexes would be
                    <v-chip class="my-4" small color="#12cd21" label
                      >used</v-chip
                    >:
                    <pre
                      class="sql"
                    ><code v-for="(ind, i) in data.hypoplan.indexes" :key="i" v-html="formatSql(ind.ddl)"></code></pre>
                  </template>
                  <template v-else>
                    None of the indexes would be used !
                  </template>
                </v-col>
              </v-row>
              <v-row>
                <v-col :cols="data.hypoplan.indexes ? 6 : 12">
                  EXPLAIN plan <b>without</b> suggested indexes:
                  <pre
                    class="sql"
                  ><code>{{ data.hypoplan.baseplan }}</code></pre>
                </v-col>
                <v-col v-if="data.hypoplan.indexes" cols="6">
                  EXPLAIN plan <b>with</b> suggested index
                  <pre
                    class="sql"
                  ><code>{{ data.hypoplan.hypoplan }}</code></pre>
                </v-col>
                <v-col cols="12">
                  Query cost gain factor with hypothetical index:
                  <b>{{ data.hypoplan.gain_percent }} %</b>
                </v-col>
              </v-row>
            </template>
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

const props = defineProps({
  config: {
    type: Object,
    default() {
      return {};
    },
  },
});

const { loading, data } = useFetch(props.config.name);
</script>
