import { resolve } from "path";
import { defineConfig } from "vite";
import { fileURLToPath, URL } from "node:url";
import vue from "@vitejs/plugin-vue";
import vuetify from "vite-plugin-vuetify";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vuetify({
      autoImport: true,
      styles: { configFile: "./powa/static/styles/variables.scss" },
    }),
  ],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./powa/static/js", import.meta.url)),
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
          lodash: ["lodash"],
          vue: ["vue", "vue-router"],
          vuetify: ["vuetify", "@mdi/js"],
          luxon: ["luxon"],
          highlight: ["highlight.js"],
          moment: ["moment"],
          "sql-formatter": ["sql-formatter"],
        },
      },
    },
  },
});
