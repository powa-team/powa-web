<template>
  <div>
    <v-row v-for="(row, rIndex) in config.widgets" :key="rIndex">
      <v-col
        v-for="(widget, wIndex) in row"
        :key="rIndex + wIndex"
        :cols="12"
        :md="12 / Object.keys(row).length"
      >
        <div class="">
          <component :is="widgetComponent(widget.type)" :config="widget" />
        </div>
      </v-col>
    </v-row>
  </div>
</template>

<script setup>
import { widgetComponent } from "../utils/widget-component.js";
// eslint-disable-next-line no-unused-vars
const props = defineProps({
  config: {
    type: Object,
    default() {
      return {};
    },
  },
});
</script>
