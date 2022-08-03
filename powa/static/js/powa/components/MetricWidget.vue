<script>
import Widget from './Widget.vue';
import store from '../store';
import * as _ from 'lodash';
import $ from "jquery";
import * as moment from 'moment';
//import Rickshaw from 'rickshaw';

export default {
  extends: Widget,
  mounted() {
    this.loadData();
  },

  methods: {
    loadData() {
      const metricGroup = _.uniq(_.map(this.config.metrics, (metric) => {
        return metric.split('.')[0];
      }));
      const metrics = _.map(this.config.metrics, (metric) => {
        return metric.split('.')[1];
      });
      const toDate = moment();
      const fromDate = toDate.clone().subtract(1, 'hour');
      const params = {
        from: fromDate.format("YYYY-MM-DD HH:mm:ssZZ"),
        to: toDate.format("YYYY-MM-DD HH:mm:ssZZ")
      };
      const sourceConfig = store.dataSources[metricGroup];
      const grouper = this.config.grouper || null;
      const xaxis = sourceConfig.xaxis;
      const yaxis = sourceConfig.yaxis;
      $.ajax({
        url: sourceConfig.data_url + '?' + $.param(params)
      }).done((response) => {
        const seriesByMetric = {}

        _.each(metrics, (metric) => {
          seriesByMetric[metric] = {};
        });

        if (response.messages !== undefined) {
          $.each(response.messages, function(level, arr) {
            $.each(arr, function(i) {
              msg = Message.add_message(level, arr[i]);
              $("#messages").append(msg);
            });
          });
        }

        _.each(response.data, (row) => {
          const group = grouper || "";
          _.each(metrics, (metric) => {
            const series = seriesByMetric[metric];
            let current_group = series[group];
            if (current_group === undefined) {
              current_group = series[group] = {
                metric: metric,
                id: metric + group,
                // name: metric.label_template({group: group}),
                data: []
              }
            }
            if (row[xaxis] === undefined) {
              throw "Data is lacking for xaxis. Did you include " + xaxis + " column in your query ?";
            }
            current_group.data.push($.extend({}, {x: new Date(row[xaxis] * 1000), y: row[sourceConfig.metrics[metric].yaxis]}, row));
          });
        });

        let newSeries = [];
        _.each(metrics, (metric) => {
          const series = seriesByMetric[metric];
          if (!$.isEmptyObject(series)) {
            $.each(series, function(key, serie){
              const newSerie = $.extend({}, sourceConfig.metrics[metric], serie);
              newSeries.push(newSerie);
            });
          }
        });
        this.dataLoaded(newSeries);
      }).fail((response) => {
        console.log ('fail');
      });
    },

    dataLoaded() {
      console.log ('Should be implemented in child classes');
    },

    getType(metric) {
      const metricGroup = _.uniq(_.map(this.config.metrics, (metric) => {
        return metric.split('.')[0];
      }));
      const sourceConfig = store.dataSources[metricGroup];
      return sourceConfig.metrics[metric].type || 'number';
    },

    getLabel(metric) {
      const metricGroup = _.uniq(_.map(this.config.metrics, (metric) => {
        return metric.split('.')[0];
      }));
      const sourceConfig = store.dataSources[metricGroup];
      return sourceConfig.metrics[metric].label;
    },

    getDesc(metric) {
      const metricGroup = _.uniq(_.map(this.config.metrics, (metric) => {
        return metric.split('.')[0];
      }));
      const sourceConfig = store.dataSources[metricGroup];
      return sourceConfig.metrics[metric].desc;
    }
  }
}
</script>
