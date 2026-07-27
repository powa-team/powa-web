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
        codeSplitting: {
          groups: [
            { name: "d3", test: /node_modules\/d3/ },
            { name: "lodash", test: /node_modules\/lodash/ },
            { name: "vue", test: /node_modules\/(vue|vue-router)/ },
            { name: "vuetify", test: /node_modules\/(vuetify|@mdi\/js)/ },
            { name: "luxon", test: /node_modules\/luxon/ },
            { name: "highlight", test: /node_modules\/highlight\.js/ },
            { name: "moment", test: /node_modules\/moment/ },
            { name: "sqltools-formatter", test: /node_modules\/@sqltools\/formatter/ },
          ],
        },
      },
    },
  },
});
