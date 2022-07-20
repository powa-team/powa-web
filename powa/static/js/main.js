import _ from "lodash";
import Vue from "vue";
import store from "./store";
import { createVuetify, icons } from "./plugins/vuetify.js";
import Dashboard from "./components/Dashboard.vue";
import DateRangePicker from "./components/DateRangePicker/DateRangePicker.vue";
import Graph from "./components/Graph.vue";
import Grid from "./components/Grid.vue";
import Tabcontainer from "./components/Tabcontainer.vue";
import Wizard from "./components/Wizard.vue";
import Content from "./components/Content.vue";
import BreadCrumbs from "./components/BreadCrumbs.vue";
import QueryTooltip from "./components/QueryTooltip.vue";
import GridCell from "./components/GridCell.vue";
import * as d3 from "d3";

let breadCrumbItems;
document
  .querySelectorAll('script[type="text/breadcrumb"]')
  .forEach(function (el) {
    breadCrumbItems = JSON.parse(el.innerText);
  });

const app = new Vue({
  el: "#app",
  vuetify: createVuetify(),
  components: {
    Dashboard,
    DateRangePicker,
    BreadCrumbs,
  },
  data: () => ({
    breadCrumbItems: breadCrumbItems,
    config: {},
    icons,
    store,
  }),
  methods: {
    reloadCollector() {
      d3.json("/reload_collector/").then(
        (response) => {
          if (response) {
            store.addAlertMessage(
              "success",
              "Collector successfully reloaded!"
            );
          } else {
            store.addAlertMessage("error", "Could not reload collector");
          }
        },
        () => {
          store.addAlertMessage(
            "error",
            "Error while trying to reload the collector."
          );
        }
      );
    },
    forceSnapshot: function (srvid) {
      d3.json("/force_snapshot/" + srvid).then(
        (response) =>
          handleResponse(response, {
            success: "Forced snapshot requested. Status:",
            warning: "Problem with forcing an immediate snapshot:",
            alert: "Could not force an immediate snapshot:",
            error: "Could not force an immediate snapshot.",
          }),
        () => {
          store.addAlertMessage(
            "alert",
            "Error while trying to force an immediate snapshot."
          );
        }
      );
    },
    refreshDbCat(srvid, event) {
      const dbnames = [];
      const dbname = event.target.parentElement.getAttribute("data-dbname");
      if (dbname) {
        dbnames.push(dbname);
      }

      d3.json("/refresh_db_cat/", {
        body: JSON.stringify({ srvid: srvid, dbnames: dbnames }),
        headers: {
          "Content-type": "application/json; charset=UTF-8",
        },
        method: "POST",
      }).then(
        (response) =>
          handleResponse(response, {
            success: "Catalog refresh successfully registered:",
            warning: "Problem with registering the catalog refresh:",
            alert: "Could not register the catalog refresh:",
            error: "Could not refresh the catalogs",
          }),
        () => {
          store.addAlertMessage(
            "alert",
            "Error while trying to refresh the catalogs."
          );
        }
      );
    },
  },
});

function handleResponse(response, messages) {
  if (response) {
    response.forEach((i) => {
      const k = Object.keys(i)[0];
      const v = i[k];
      let level;
      let msg;

      switch (k) {
        case "OK":
          level = "success";
          msg = messages.success;
          break;
        case "WARNING":
        case "UNKNOWN":
          level = "warning";
          msg = messages.warning;
          break;
        default:
          level = "alert";
          msg = messages.alert;
          break;
      }

      msg += "<br/>" + v;

      store.addAlertMessage(level, msg);
    });
  } else {
    store.addAlertMessage("alert", messages.error);
  }
}

Vue.component("Dashboard", Dashboard);
Vue.component("DateRangePicker", DateRangePicker);
Vue.component("Graph", Graph);
Vue.component("Grid", Grid);
Vue.component("Tabcontainer", Tabcontainer);
Vue.component("Wizard", Wizard);
Vue.component("ContentCmp", Content);
Vue.component("BreadCrumbs", BreadCrumbs);
Vue.component("QueryTooltip", QueryTooltip);
Vue.component("GridCell", GridCell);

document
  .querySelectorAll('script[type="text/datasources"]')
  .forEach(function (el) {
    const dataSources = JSON.parse(el.innerText);
    _.each(dataSources, function (dataSource) {
      try {
        if (dataSource.type == "metric_group") {
          dataSource.metrics = _.keyBy(dataSource.metrics, "name");
        }
      } catch (e) {
        console.error(
          "Could not instantiate metric group. Check the metric group definition"
        );
      }
      store.dataSources[dataSource.name] = dataSource;
    });
  });

document
  .querySelectorAll('script[type="text/dashboard"]')
  .forEach(function (el) {
    app.config = JSON.parse(el.innerText);
  });

document
  .querySelectorAll('script[type="text/messages"]')
  .forEach(function (el) {
    const messages = JSON.parse(el.innerText);
    store.addAlertMessages(messages);
  });

document
  .querySelectorAll('script[type="text/datasource_timeline"]')
  .forEach(function (el) {
    store.changesUrl = JSON.parse(el.innerText);
  });
store.loadData();
