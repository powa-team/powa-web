import "vuetify/styles";
import { createVuetify } from "vuetify";
import { aliases, mdi } from "vuetify/lib/iconsets/mdi-svg";

const opts = {
  icons: {
    defaultSet: "mdi",
    aliases,
    sets: {
      mdi,
    },
  },
  theme: {
    options: {
      customProperties: true,
    },
    defaultTheme: "light",
    themes: {
      light: {
        dark: false,
        colors: {
          primary: "#859145",
          secondary: "#b0bec5",
          accent: "#8c9eff",
          error: "#b71c1c",
          surface: "#efefef",
          tickstroke: "#ffffff",
          axisgridlinestroke: "#d3d3d3",
          eventmarkerfill: "#000000",
        },
      },
      dark: {
        dark: true,
        colors: {
          "on-surface": "#ddd",
          primary: "#859145",
          mainbg: "#333333",
          tooltipbg: "#313131",
          tickstroke: "#333333",
          axisgridlinestroke: "#4f4f4f",
          eventmarkerfill: "#ffffff",
        },
      },
    },
  },
};

export default new createVuetify(opts);
