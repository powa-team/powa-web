<template>
  <v-row v-for="(row, rIndex) in config.widgets" :key="rIndex">
    <v-col
      v-for="(widget, wIndex) in row"
      :key="rIndex + wIndex"
      cols="12"
      :md="12 / Object.keys(row).length"
    >
      <component :is="widgetComponent(widget)" :config="widget" />
    </v-col>
  </v-row>
</template>

<script setup>
import { widgetComponent } from "@/utils/widget-component.js";
defineProps({
  config: {
    type: Object,
    default() {
      return {};
    },
  },
});
</script>
