<template>
  <div class="card mb-4">
    <div class="card-body">
      <h4>{{ config.title }}</h4>
      <em>Wizard component not implemented.</em>
    </div>
  </div>
</template>

<script setup>
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
