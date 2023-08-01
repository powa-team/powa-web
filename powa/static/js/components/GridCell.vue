<template>
  <query-tooltip
    v-if="props.header.type == 'query'"
    :key="props.header.value"
    :value="props.value"
  ></query-tooltip>
  <span
    v-else
    :key="props.header.value"
    v-html="props.header.formatter(props.value)"
  ></span>
</template>
<script setup>
import QueryTooltip from "@/components/QueryTooltip.vue";
const props = defineProps({
  header: {
    type: Object,
    default() {
      return {};
    },
  },
  value: {
    type: [String, Number, Boolean],
    default: "",
  },
});
</script>
