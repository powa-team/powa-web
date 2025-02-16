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
    <v-card-text>
      <template v-if="data">
        <v-row data-equalizer>
          <v-col cols="4" class="pt-8">
            <template v-if="data.indexes">
              <template v-for="(inds, clause) in data.indexes" :key="clause">
                Possible indexes for attributes present in
                <pre
                  class="bg-surface sql"
                ><code v-html="formatSql(clause)"></code></pre>
                <div v-for="(index, i) in inds" :key="i">
                  <v-list>
                    <v-list-item
                      v-for="(qual, j) in index.qual"
                      :key="j"
                      density="compact"
                    >
                      <v-list-item-title>
                        • With access method <em>{{ index.amname }}</em> :
                      </v-list-item-title>
                      <pre
                        class="sql"
                      ><code>{{ qual.relname }}.{{ qual.attname }}</code></pre>
                      <template v-if="!qual.distinct_values">Unknown</template>
                      <template v-else>
                        approximately
                        <b>{{ qual.distinct_values }}</b> distinct values
                      </template>
                    </v-list-item>
                  </v-list>
                </div>
              </template>
            </template>
            <template v-else> No suitable index to suggest. </template>
          </v-col>
          <v-col cols="8" class="pt-8">
            <template v-if="data.hypoplan">
              <v-row>
                <v-col cols="12">
                  <template v-if="data.hypoplan.indexes">
                    The following indexes would be
                    <v-chip
                      size="small"
                      variant="flat"
                      color="#4CAF50"
                      label
                      density="compact"
                      >used</v-chip
                    >
                    :
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
import { useDataLoader } from "@/composables/DataLoaderService.js";
import { formatSql } from "@/utils/sql.js";

const props = defineProps({
  config: {
    type: Object,
    default() {
      return {};
    },
  },
});

const { loading, data } = useDataLoader(props.config.name);
</script>
