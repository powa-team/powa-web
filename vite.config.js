import { resolve } from "path";
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue2";
import { VuetifyResolver } from "unplugin-vue-components/resolvers";
import Components from "unplugin-vue-components/vite";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    // unplugin-vue-components
    // https://github.com/antfu/unplugin-vue-components
    Components({
      dirs: ["/powa/static/js/components"],
      // auto import for directives
      directives: true,
      // resolvers for custom components
      resolvers: [
        // Vuetify
        VuetifyResolver(),
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
    emptyOutDir: true,
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
