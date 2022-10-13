import _ from 'lodash';
import Vue from 'vue';
import store from './store';
import Dashboard from './components/Dashboard.vue';
import Graph from './components/Graph.vue';
import Grid from './components/Grid.vue';
import Tabcontainer from './components/Tabcontainer.vue';
import Wizard from './components/Wizard.vue';
import Content from './components/Content.vue';
import $ from "jquery";
import { addMessage } from './utils/message.js';

import 'bootstrap';

import 'bootstrap/dist/css/bootstrap.css'

const app = new Vue({
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


Vue.component('dashboard', Dashboard);
Vue.component('graph', Graph);
Vue.component('grid', Grid);
Vue.component('tabcontainer', Tabcontainer);
Vue.component('wizard', Wizard);
Vue.component('content-cmp', Content);

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

$("#reload_collector").click(function() {
  $.ajax({
    url: '/reload_collector/',
    type: 'GET',
  }).done(function(response) {
    if (response) {
      addMessage("success", "Collector successfully reloaded!")
    } else {
      addMessage("danger", "Could not reload collector")
    }
  }).fail(function(response) {
    addMessage("danger", "Error while trying to reload the collector.")
  });
});
