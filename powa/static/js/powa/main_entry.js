import _ from 'lodash';
import Vue from 'vue';
import Dashboard from './components/Dashboard.vue';
import './components';
import store from './store';
import BootstrapVue from 'bootstrap-vue';

Vue.use(BootstrapVue);

import 'bootstrap';

import 'bootstrap/dist/css/bootstrap.css'
import 'bootstrap-vue/dist/bootstrap-vue.css'

var app = new Vue ({
  el: '#dashboard',
  components: {
    Dashboard
  },
  data () {
    return {
      config: {}
    }
  }
});

const colors = ["#c05020", "#30c020", "#6060c0"];
// const ds = DataSourceCollection.get_instance();
// const picker = new timeurls({$el: $('#daterangepicker')});
const dashboards = [];

$('script[type="text/datasources"]').each(function() {
  const dataSources = JSON.parse(this.text);
  _.each(dataSources, function(dataSource) {
    store.dataSources[dataSource.name] = dataSource;
    try {
      if (dataSource.type == "metric_group") {
        dataSource.metrics = _.keyBy(dataSource.metrics, 'name');
      } else if (dataSource.type == "content") {
        // nothing to do
      }
    }
    catch(e) {
      console.error("Could not instantiate metric group. Check the metric group definition");
    }
  });
});

$('script[type="text/dashboard"]').each(function(){
  app.config = JSON.parse(this.text);
  //const widgetsEl = $('.widgets');

  //_.each(config.widgets, (w) => {
    //const widget = w[0];
    //console.log (widget.type);
    //app.widgets.push(widget);
  //});
  //var dashboard = Widget.fromJSON(JSON.parse(this.text));
  //var dashboardview = dashboard.makeView({el: $(self).find('.widgets')});
  //dashboards.push(dashboard);
  //dashboardview.listenTo(picker, "pickerChanged", dashboardview.refreshSources, dashboardview);
  //dashboardview.refreshSources(picker.start_date, picker.end_date);
  //picker.listenTo(dashboardview, "dashboard:updatePeriod", picker.updateUrls, picker);
});
