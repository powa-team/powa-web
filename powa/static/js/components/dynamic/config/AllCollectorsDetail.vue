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
    <v-card-text v-if="collector">
      <v-row>
        <v-col>
          <template v-if="!collector">
            <v-alert type="error" role="alert">
              Not enough permission to check for collectors!
            </v-alert>
            <v-row>
              <v-col cols="12"
                ><b>Background worker status:</b>
                <span class="text-disabled">∅</span></v-col
              >
            </v-row>
            <v-row>
              <v-col cols="12"
                ><b>Remote Collector status:</b>
                <span class="text-disabled">∅</span></v-col
              >
            </v-row>
          </template>
          <template v-else-if="collector.length == 0">
            <v-alert type="error" role="alert">
              No PoWA collector daemon is running!
            </v-alert>
            <v-row>
              <v-col cols="12"
                ><b>Background worker status:</b>
                <span class="text-error">✗</span></v-col
              >
            </v-row>
            <v-row>
              <v-col cols="12"
                ><b>Remote Collector status:</b>
                <span class="text-error">✗</span></v-col
              >
            </v-row>
          </template>
          <template v-else>
            <v-row v-for="(c, index) in collector" :key="index" dense>
              <template v-if="c.start">
                <v-col cols="3"
                  ><b>{{ c.powa_kind }}:</b>
                  <span class="text-success">✓</span></v-col
                >
                <v-col cols="3"><b>Connected as:</b> {{ c.usename }}</v-col>
                <v-col cols="3"
                  ><b>Connected from:</b> {{ c.client_addr }}</v-col
                >
                <v-col cols="3"><b>Connected since:</b> {{ c.start }}</v-col>
              </template>
              <template v-else>
                <v-col cols="12"
                  ><b>{{ c.powa_kind }}:</b>
                  <span class="text-error">✗</span></v-col
                >
              </template>
            </v-row>
          </template>
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { useDataLoader } from "@/composables/DataLoaderService.js";

const props = defineProps({
  config: {
    type: Object,
    default() {
      return {};
    },
  },
});

const { loading, data: collector } = useDataLoader(props.config.name);
</script>
