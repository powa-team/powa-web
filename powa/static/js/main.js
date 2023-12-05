import { createApp } from "vue";
import vuetify from "@/plugins/vuetify";
import App from "@/App.vue";
import dynamicComponents from "@/plugins/powa";
import { createWebHistory, createRouter } from "vue-router";
import { useMessageService } from "@/composables/MessageService";

import "@/../styles/main.scss";
import "@/fonts/Roboto/roboto.css";

const { addAlertMessages } = useMessageService();

document
  .querySelectorAll('script[type="text/messages"]')
  .forEach(function (el) {
    const messages = JSON.parse(el.innerText);
    addAlertMessages(messages);
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
