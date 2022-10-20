<template>
  <div class="card mb-4">
    <div class="card-body">
      <h4>{{ config.title }}</h4>
      <!-- eslint-disable-next-line vue/no-v-html -->
      <div ref="contentEl" v-html="content" />
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
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

const content = ref("");
const contentEl = ref(null);

onMounted(() => {
  loadData();
});

function loadData() {
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
    content.value = response;
    window.setTimeout(loaded, 1);
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
