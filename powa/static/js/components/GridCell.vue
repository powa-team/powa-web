<template>
  <query-tooltip
    v-if="props.column.type == 'query'"
    :value="props.value"
  ></query-tooltip>
  <span v-else v-html="props.column.formatter(props.value)"></span>
</template>
<script setup>
import QueryTooltip from "@/components/QueryTooltip.vue";
const props = defineProps({
  column: {
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
