<template>
  <v-tooltip
    content-class="sql elevation-2"
    transition="fade"
    open-delay="200"
    location="bottom"
  >
    <template #activator="{ props: activatorProps }">
      <pre
        class="sql"
        v-bind="activatorProps"
      ><code v-html="formatSql(props.value)"/></pre>
    </template>
    <pre class="sql"><code v-html="formatSql(props.value)" /></pre>
  </v-tooltip>
</template>

<script setup>
import { formatSql } from "@/utils/sql.js";

const props = defineProps({
  value: {
    type: String,
    default() {
      return {};
    },
  },
});
</script>
