import Vue from "vue";
import store from "@/store";
import vuetify from "@/plugins/vuetify";
import App from "@/App.vue";
import dynamicComponents from "@/plugins/powa";
import VueRouter from "vue-router";

import "@/../styles/main.scss";

document
  .querySelectorAll('script[type="text/messages"]')
  .forEach(function (el) {
    const messages = JSON.parse(el.innerText);
    store.addAlertMessages(messages);
  });

dynamicComponents.install();

Vue.use(VueRouter);

const router = new VueRouter({
  mode: "history",
});

new Vue({
  render: (h) => h(App),
  vuetify,
  router,
}).$mount("#app");
