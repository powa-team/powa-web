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

import Vuetify from "vuetify/lib";
import { ClickOutside } from "vuetify/lib";

const directives = {
  ClickOutside,
};

export const icons = {
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

Vue.use(Vuetify, { directives });

const opts = {
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
};

export default new Vuetify(opts);
