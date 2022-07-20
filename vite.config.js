import { resolve } from 'path'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue2'
import inject from '@rollup/plugin-inject'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    inject({
      $: "jquery"
    })
  ],
  resolve: {
    alias: {
      'vue': 'vue/dist/vue.esm.js'
    }
  },
  build: {
    manifest: true,
    rollupOptions: {
      input: "/powa/static/js/powa/main_entry.js",
      output: {
        dir: resolve(__dirname, "powa/static/dist")
      }
    }
  }
})
