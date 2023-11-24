import { createApp } from "vue";
import store from "@/store";
import vuetify from "@/plugins/vuetify";
import App from "@/App.vue";
import dynamicComponents from "@/plugins/powa";
import { createWebHistory, createRouter } from "vue-router";

import "@/../styles/main.scss";
import "@/fonts/Roboto/roboto.css";

document
  .querySelectorAll('script[type="text/messages"]')
  .forEach(function (el) {
    const messages = JSON.parse(el.innerText);
    store.addAlertMessages(messages);
  });

const NotFound = { template: "" };
const routerPlugin = createRouter({
  history: createWebHistory(),
  routes: [{ path: "/:pathMatch(.*)", name: "NotFound", component: NotFound }],
});

createApp(App)
  .use(vuetify)
  .use(routerPlugin)
  .use(dynamicComponents)
  .mount("#app");
