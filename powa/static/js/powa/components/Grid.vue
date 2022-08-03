<template>
  <div class="card mb-4">
    <div class="card-body">
      <h4>{{ config.title }}</h4>
      <div class="row">
        <div class="col-sm-4">
        </div>
      </div>
      <table class="table table-sm table-hover">
        <thead>
          <tr>
            <th v-for="field in fields" :class="field.type">
              {{ field.label }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="entry in items" @click="onRowClicked(entry)">
            <td v-for="field in fields" :class="field.type">
              <template v-if="field.type == 'query' || field.type == 'where_clause'">
                <pre v-html="field.formatter(entry[field.key])" />
              </template>
              <template v-else>
                {{ field.formatter(entry[field.key]) }}
              </template>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script>

import Widget from './Widget.vue';
import store from '../store';
import * as _ from 'lodash';
import $ from "jquery";
import * as moment from 'moment';
import size from '../utils2/size';
import hljs from 'highlight.js';
import 'highlight.js/styles/default.css';
import pgsql from 'highlight.js/lib/languages/pgsql';
hljs.registerLanguage('pgsql', pgsql);

export default {
  extends: Widget,
  data: () => {
    return {
      items: null,
      totalRows: 1,
      currentPage: 1,
      perPage: 20,
      filter: null
    }
  },

  mounted() {
    this.loadData();
  },

  computed: {
    fields() {
      const metricGroup = _.uniq(_.map(this.config.metrics, (metric) => {
        return metric.split('.')[0];
      }));
      const metrics = _.map(this.config.metrics, (metric) => {
        return metric.split('.')[1];
      });
      const sourceConfig = store.dataSources[metricGroup];

      const columns = this.config.columns;
      _.each(metrics, function(metric) {
        columns.push($.extend({}, sourceConfig.metrics[metric]));
      });
      _.each(columns, (c) => {
        $.extend(c, {
          key: c.name,
          label: c.label,
          formatter: this.getFormatter(c.type),
          class: c.type
        })
      });
      return columns;
    }
  },

  methods: {
    loadData() {
      const metricGroup = _.uniq(_.map(this.config.metrics, (metric) => {
        return metric.split('.')[0];
      }));
      const sourceConfig = store.dataSources[metricGroup];
      const toDate = moment();
      const fromDate = toDate.clone().subtract(1, 'hour');
      const params = {
        from: fromDate.format("YYYY-MM-DD HH:mm:ssZZ"),
        to: toDate.format("YYYY-MM-DD HH:mm:ssZZ")
      };
      $.ajax({
        url: sourceConfig.data_url + '?' + $.param(params)
      }).done((response) => {
        this.dataLoaded(response.data);
      });
    },

    dataLoaded(data) {
      this.items = data;
      this.totalRows = this.items.length;
    },

    formatBool(value) {
      return value ? '✓' : '✗';
    },

    formatDuration(value) {
      return moment(parseFloat(value, 10)).preciseDiff(moment(0), true);
    },

    formatSize(value) {
      return new size.SizeFormatter().fromRaw(value);
    },

    formatQuery(value) {
      return hljs.highlightAuto(value, ['pgsql']).value;
    },

    getFormatter(type) {
      switch (type) {
        case 'bool':
          return this.formatBool;
        case 'duration':
          return this.formatDuration;
        case 'percent':
          return (value) => value + '%';
        case 'query':
          return this.formatQuery;
        case 'size':
          return this.formatSize;
        default:
          return (value) => value;
      }
    },

    onFiltered(filteredItems) {
      this.totalRows = filteredItems.length;
      this.currentPage = 1;
    },

    onRowClicked(row) {
      if (row.url) {
        window.location.href = row.url;
      }
    }
  }
}
</script>

<style lang="scss">
  td {
    white-space: nowrap;

    &.query {
      width: 50%;
      overflow: hidden;
      max-width: 0;
      pre, code {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        margin-bottom: 0;
      }
    }
  }
  th, td {
    &.duration,
    &.number,
    &.size {
      text-align: right;
    }
  }
</style>
