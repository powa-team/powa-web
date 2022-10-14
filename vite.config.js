import { resolve } from 'path'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue2'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    vue(),
  ],
  resolve: {
    alias: {
      'vue': 'vue/dist/vue.esm.js'
    }
  },
  build: {
    manifest: true,
    rollupOptions: {
      input: "/powa/static/js/main.js",
      output: {
        dir: resolve(__dirname, "powa/static/dist")
      }
    }
  }
})
