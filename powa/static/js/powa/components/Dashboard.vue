<template>
  <div>
    <div
      v-for="(row, rIndex) in config.widgets"
      :key="rIndex"
      class="row"
    >
      <div
        v-for="(widget, wIndex) in row"
        :key="rIndex + wIndex"
        :class="['col-lg-' + 12 / Object.keys(row).length]"
      >
        <div class="">
          <component
            :is="widgetComponent(widget.type)"
            :config="widget"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import Widget from './Widget.vue';
export default {
  extends: Widget
}
</script>
