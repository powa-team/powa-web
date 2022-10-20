<template>
  <v-card>
    <v-card-title>
      {{ config.title }}
    </v-card-title>
    <v-card-text>
      <em>Wizard component not implemented.</em>
    </v-card-text>
  </v-card>
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
