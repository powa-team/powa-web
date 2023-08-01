import _ from "lodash";
import Vue from "vue";
import store from "@/store";
import vuetify from "@/plugins/vuetify";
import App from "@/App.vue";
import dynamicComponents from "@/plugins/powa";

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

dynamicComponents.install();

new Vue({
  render: (h) => h(App),
  vuetify,
}).$mount("#app");
