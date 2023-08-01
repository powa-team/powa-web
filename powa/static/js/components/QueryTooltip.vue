<template>
  <v-tooltip
    content-class="sql elevation-2"
    transition="fade"
    open-delay="200"
    bottom
  >
    <template #activator="{ on, attrs }">
      <pre v-bind="attrs" v-on="on" v-html="formatSql(props.value)" />
    </template>
    <pre v-html="formatSql(props.value)" />
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
