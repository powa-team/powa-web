import { resolve } from "path";
import { defineConfig } from "vite";
import vue2 from "@vitejs/plugin-vue2";
import Components from "unplugin-vue-components/vite";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    vue2(),
    Components({
      resolvers: [
        {
          type: "component",
          resolve: (name) => {
            if (name.match(/^V[A-Z]/) && name !== "VSnackbars") {
              return { name, from: "vuetify/lib" };
            }
          },
        },
      ],
    }),
  ],
  resolve: {
    alias: {
      vue: "vue/dist/vue.esm.js",
    },
  },
  build: {
    manifest: true,
    outDir: resolve(__dirname, "powa/static/dist"),
    rollupOptions: {
      input: "/powa/static/js/main.js",
      output: {
        manualChunks: {
          // Split external library from transpiled code.
          d3: ["d3"],
          grafana: ["@grafana/data"],
          lodash: ["lodash"],
          vue: ["vue"],
          vuetify: ["vuetify"],
          luxon: ["luxon"],
          highlight: ["highlight.js"],
        },
      },
    },
  },
  css: {
    preprocessorOptions: {
      sass: {
        additionalData: [
          '@import "./powa/static/styles/variables"',
          '@import "./powa/static/styles/main"',
          "", // end with new line
        ].join("\n"),
      },
    },
  },
});
