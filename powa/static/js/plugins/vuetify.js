import Vue from "vue";
import {
  mdiAlert,
  mdiCalendar,
  mdiCancel,
  mdiClockOutline,
  mdiCog,
  mdiHome,
  mdiMagnifyMinusOutline,
  mdiReload,
  mdiPower,
  mdiClose,
} from "@mdi/js";

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
  VChip,
  VCol,
  VCombobox,
  VContainer,
  VFlex,
  VFooter,
  VForm,
  VIcon,
  VLayout,
  VMain,
  VProgressLinear,
  VRow,
  VSimpleTable,
  VSnackbar,
  VSpacer,
  VTextField,
  VToolbar,
  VToolbarTitle,
} from "vuetify/lib";

import VSnackbars from "v-snackbars";

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
  VChip,
  VCol,
  VCombobox,
  VContainer,
  VFlex,
  VFooter,
  VForm,
  VIcon,
  VLayout,
  VMain,
  VProgressLinear,
  VRow,
  VSimpleTable,
  VSnackbar,
  VSnackbars,
  VSpacer,
  VTextField,
  VToolbar,
  VToolbarTitle,
};
Object.keys(components).forEach((component) => {
  Vue.component(component, components[component]);
});

const icons = {
  mdiAlert,
  mdiCalendar,
  mdiCancel,
  mdiClockOutline,
  mdiCog,
  mdiHome,
  mdiMagnifyMinusOutline,
  mdiPower,
  mdiReload,
  mdiClose,
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

export { createVuetify, icons };
