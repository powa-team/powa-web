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
  mdiWhiteBalanceSunny,
  mdiWeatherNight,
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
  mdiWhiteBalanceSunny,
  mdiWeatherNight,
};

Vue.use(Vuetify, { directives });

const opts = {
  icons: {
    iconfont: "mdiSvg",
  },
  theme: {
    options: {
      customProperties: true,
    },
    themes: {
      light: {
        primary: "#859145",
        secondary: "#b0bec5",
        accent: "#8c9eff",
        error: "#b71c1c",
        mainbg: "#eeeeee",
        tooltipbg: "#ffffff",
        tickstroke: "#ffffff",
        axisgridlinestroke: "#d3d3d3",
        eventmarkerfill: "#000000",
      },
      dark: {
        primary: "#859145",
        mainbg: "#333333",
        tooltipbg: "#313131",
        tickstroke: "#333333",
        axisgridlinestroke: "#4f4f4f",
        eventmarkerfill: "#ffffff",
      },
    },
  },
};

export default new Vuetify(opts);
