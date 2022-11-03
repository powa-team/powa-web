import Vue from "vue";
import { mdiCog, mdiHome, mdiReload, mdiPower } from "@mdi/js";

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

const directives = {
  ClickOutside,
};
const components = {
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
};

const icons = {
  mdiCog,
  mdiHome,
  mdiPower,
  mdiReload,
};

/** Create Vuetify Instance */
function createVuetify() {
  Vue.use(Vuetify, {
    directives,
  });
  return new Vuetify({
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
  });
}

export { components, createVuetify, icons };
