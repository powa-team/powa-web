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
    <v-card-text v-if="data !== undefined">
      <v-row>
        <v-col>
          <h4>Perform wizard analysis of this database</h4>
          <a :href="data.url" class="button radius">Launch</a>
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { useFetch } from "@/utils/fetch.js";

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
