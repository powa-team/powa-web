import Vue from "vue";
import { mdiCog, mdiHome, mdiReload, mdiPower } from "@mdi/js";

import Vuetify, {
  ClickOutside,
  VAlert,
  VApp,
  VAppBar,
  VBreadcrumbs,
  VBreadcrumbsItem,
  VBtn,
  VCard,
  VCardActions,
  VCardText,
  VCol,
  VCombobox,
  VContainer,
  VFlex,
  VFooter,
  VForm,
  VIcon,
  VLayout,
  VMain,
  VRow,
  VSpacer,
  VTextField,
  VToolbar,
  VToolbarTitle,
} from "vuetify/lib";

const directives = {
  ClickOutside,
};
const components = {
  VAlert,
  VApp,
  VAppBar,
  VBreadcrumbs,
  VBreadcrumbsItem,
  VBtn,
  VCard,
  VCardActions,
  VCardText,
  VCol,
  VCombobox,
  VContainer,
  VFlex,
  VFooter,
  VForm,
  VIcon,
  VLayout,
  VMain,
  VRow,
  VSpacer,
  VTextField,
  VToolbar,
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
