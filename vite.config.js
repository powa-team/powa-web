import { resolve } from 'path'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    vue(),
  ],
  resolve: {
    alias: {
      'vue': 'vue/dist/vue.esm-bundler.js'
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
