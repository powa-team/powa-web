<template>
  <div>
    <div v-for="(row, rIndex) in config.widgets" :key="rIndex" class="row">
      <div
        v-for="(widget, wIndex) in row"
        :key="rIndex + wIndex"
        :class="['col-lg-' + 12 / Object.keys(row).length]"
      >
        <div class="">
          <component :is="widgetComponent(widget.type)" :config="widget" />
        </div>
      </div>
    </div>
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
