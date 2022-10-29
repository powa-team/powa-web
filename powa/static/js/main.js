import _ from "lodash";
import Vue from "vue";
import Vuetify, {
  ClickOutside,
  VApp,
  VAppBar,
  VBreadcrumbs,
  VBreadcrumbsItem,
  VBtn,
  VCol,
  VContainer,
  VFlex,
  VFooter,
  VIcon,
  VMain,
  VRow,
  VSpacer,
  VToolbarTitle,
} from "vuetify/lib";
import { mdiCog, mdiHome, mdiReload, mdiPower } from "@mdi/js";
import store from "./store";
import Dashboard from "./components/Dashboard.vue";
import DateRangePicker from "./components/DateRangePicker/DateRangePicker.vue";
import Graph from "./components/Graph.vue";
import Grid from "./components/Grid.vue";
import Tabcontainer from "./components/Tabcontainer.vue";
import Wizard from "./components/Wizard.vue";
import Content from "./components/Content.vue";
import $ from "jquery";
import { addMessage } from "./utils/message.js";

import "bootstrap";

//import "vuetify/src/styles/styles";
//import "bootstrap/dist/css/bootstrap.css";
//import "vuetify/dist/vuetify.min.css";

Vue.use(Vuetify, {
  directives: {
    ClickOutside,
  },
});

const app = new Vue({
  el: "#app",
  vuetify: new Vuetify({
    icons: {
      iconfont: "mdiSvg",
    },
    theme: {
      themes: {
        light: {
          primary: "#859145",
          secondary: "#b0bec5",
          accent: "#8c9eff",
          error: "#b71c1c",
        },
      },
    },
  }),
  components: {
    Dashboard,
    DateRangePicker,
    VApp,
    VAppBar,
    VBreadcrumbs,
    VBreadcrumbsItem,
    VBtn,
    VCol,
    VContainer,
    VFlex,
    VFooter,
    VIcon,
    VMain,
    VRow,
    VSpacer,
    VToolbarTitle,
  },
  data: () => ({
    breadCrumbItems: [],
    config: {},
    icons: {
      mdiCog,
      mdiHome,
      mdiPower,
      mdiReload,
    },
  }),
});

Vue.component("Dashboard", Dashboard);
Vue.component("DateRangePicker", DateRangePicker);
Vue.component("Graph", Graph);
Vue.component("Grid", Grid);
Vue.component("Tabcontainer", Tabcontainer);
Vue.component("Wizard", Wizard);
Vue.component("ContentCmp", Content);

$('script[type="text/datasources"]').each(function () {
  const dataSources = JSON.parse(this.text);
  _.each(dataSources, function (dataSource) {
    store.dataSources[dataSource.name] = dataSource;
    try {
      if (dataSource.type == "metric_group") {
        dataSource.metrics = _.keyBy(dataSource.metrics, "name");
      } else if (dataSource.type == "content") {
        // nothing to do
      }
    } catch (e) {
      console.error(
        "Could not instantiate metric group. Check the metric group definition"
      );
    }
  });
});

$('script[type="text/dashboard"]').each(function () {
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

$('script[type="text/breadcrumb"]').each(function () {
  app.breadCrumbItems = JSON.parse(this.text);
});

$("#reload_collector").click(function () {
  $.ajax({
    url: "/reload_collector/",
    type: "GET",
  })
    .done(function (response) {
      if (response) {
        addMessage("success", "Collector successfully reloaded!");
      } else {
        addMessage("danger", "Could not reload collector");
      }
    })
    .fail(function () {
      addMessage("danger", "Error while trying to reload the collector.");
    });
});
