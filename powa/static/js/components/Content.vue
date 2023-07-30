<template>
  <v-card :loading="loading">
    <template #progress>
      <v-progress-linear
        height="2"
        indeterminate
        style="position: absolute; z-index: 1"
      ></v-progress-linear>
    </template>
    <v-app-bar flat height="40px;">
      <v-toolbar-title>
        <v-card-title class="pl-0">{{ config.title }}</v-card-title>
      </v-toolbar-title>
    </v-app-bar>
    <v-card-text ref="contentEl"><div v-html="content"></div></v-card-text>
  </v-card>
</template>

<script setup>
import Vue, { onMounted, ref, watch } from "vue";
import vuetify, { icons } from "../plugins/vuetify.js";
import store from "../store";
import hljs from "highlight.js/lib/core";
import pgsql from "highlight.js/lib/languages/pgsql";
import "highlight.js/styles/default.css";
import { formatDuration } from "../utils/duration";

hljs.registerLanguage("sql", pgsql);

const props = defineProps({
  config: {
    type: Object,
    default() {
      return {};
    },
  },
});

const loading = ref(false);
const content = ref("");
const contentEl = ref(null);

onMounted(() => {
  watch(
    () => store.dataSources,
    () => {
      loadData();
    },
    { immediate: true }
  );
});

function loadData() {
  loading.value = true;
  const sourceConfig = store.dataSources[props.config.name];
  sourceConfig.promise.then((response) => {
    const el = new Vue({
      data: () => ({
        icons,
      }),
      template: response,
      vuetify,
    });
    const html = el.$mount().$el.outerHTML;
    content.value = html;
    window.setTimeout(loaded, 1);
    loading.value = false;
  });
}

function loaded() {
  const el = contentEl.value;
  el.querySelectorAll("pre.sql code").forEach((block) => {
    hljs.highlightBlock(block);
  });
  el.querySelectorAll("span.duration").forEach((block) => {
    const duration = parseInt(block.innerHTML);
    block.innerHTML = formatDuration(duration, true);
  });
}

watch(
  () => store.rawFrom + store.rawTo,
  () => {
    loadData();
  }
);
</script>
