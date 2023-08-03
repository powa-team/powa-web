<template>
  <v-tooltip
    content-class="sql elevation-2"
    transition="fade"
    open-delay="200"
    bottom
  >
    <template #activator="{ on, attrs }">
      <pre
        class="sql"
        v-bind="attrs"
        v-on="on"
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
