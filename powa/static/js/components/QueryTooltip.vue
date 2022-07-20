<template>
  <v-tooltip
    content-class="sql elevation-2"
    transition="fade"
    open-delay="200"
    bottom
  >
    <template #activator="{ on, attrs }">
      <pre v-bind="attrs" v-on="on" v-html="sqlFormat(props.value)" />
    </template>
    <pre v-html="sqlFormat(props.value)" />
  </v-tooltip>
</template>

<script setup>
import hljs from "highlight.js/lib/core";
import pgsql from "highlight.js/lib/languages/pgsql";

hljs.registerLanguage("sql", pgsql);

const props = defineProps({
  value: {
    type: String,
    default() {
      return {};
    },
  },
});

function sqlFormat(value) {
  return hljs.highlightAuto(value, ["pgsql"]).value;
}
</script>
