<template>
  <v-card :loading="loading">
    <template #progress>
      <v-progress-linear
        height="2"
        indeterminate
        style="position: absolute"
      ></v-progress-linear>
    </template>
    <v-app-bar flat height="40px;">
      <v-toolbar-title>
        <v-card-title class="pl-0">{{ config.title }}</v-card-title>
      </v-toolbar-title>
    </v-app-bar>
    <!-- eslint-disable-next-line vue/no-v-html -->
    <v-card-text ref="contentEl"><div v-html="content"></div></v-card-text>
  </v-card>
</template>

<script setup>
import Vue, { onMounted, ref } from "vue";
import { components, createVuetify } from "../plugins/vuetify.js";
import store from "../store";
import moment from "moment";
import hljs from "highlight.js";
import "highlight.js/styles/default.css";
import $ from "jquery";

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
  loadData();
});

function loadData() {
  loading.value = true;
  const sourceConfig = store.dataSources[props.config.name];
  const toDate = moment();
  const fromDate = toDate.clone().subtract(1, "hour");
  const params = {
    from: fromDate.format("YYYY-MM-DD HH:mm:ssZZ"),
    to: toDate.format("YYYY-MM-DD HH:mm:ssZZ"),
  };
  $.ajax({
    url: sourceConfig.data_url + "?" + $.param(params),
  }).done((response) => {
    const el = new Vue({
      components,
      template: response,
      vuetify: createVuetify(),
    });
    const html = el.$mount().$el.outerHTML;
    content.value = html;
    window.setTimeout(loaded, 1);
    loading.value = false;
  });
}

function loaded() {
  const el = $(contentEl.value);
  el.find("pre.sql code").each(function (i, block) {
    hljs.highlightBlock(block);
  });
  el.find("span.duration").each(function (i, block) {
    const date = moment(parseInt($(block).html()));
    $(block).html(date.preciseDiff(moment.unix(0)));
  });
}
</script>
