<template>
  <div class="card mb-4">
    <div class="card-body">
      <h4>{{ config.title }}</h4>
      <div ref="content" v-html="content" />
    </div>
  </div>
</template>

<script>
import Widget from './Widget.vue';
import store from '../store';
import moment from 'moment';
import hljs from 'highlight.js';
import 'highlight.js/styles/default.css';
import $ from "jquery";

export default {
  extends: Widget,

  data: () => {
    return {
      content: ''
    }
  },

  mounted() {
    this.loadData();
  },

  methods: {
    loadData() {
      const sourceConfig = store.dataSources[this.config.name];
      const toDate = moment();
      const fromDate = toDate.clone().subtract(1, 'hour');
      const params = {
        from: fromDate.format("YYYY-MM-DD HH:mm:ssZZ"),
        to: toDate.format("YYYY-MM-DD HH:mm:ssZZ")
      };
      $.ajax({
        url: sourceConfig.data_url + '?' + $.param(params)
      }).done((response) => {
        this.content = response;
        window.setTimeout(this.loaded, 1);
      });
    },

    loaded() {
      const el = $(this.$refs.content);
      el.find("pre.sql code").each(function(i, block){
        hljs.highlightBlock(block);
      });
      el.find("span.duration").each(function(i, block){
        const date = moment(parseInt($(block).html()));
        $(block).html(date.preciseDiff(moment.unix(0)));
      });
    }
  }
}
</script>
