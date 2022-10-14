import { resolve } from 'path'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue2'
import { VuetifyResolver  } from 'unplugin-vue-components/resolvers'
import Components from 'unplugin-vue-components/vite'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    Components({
      resolvers: [
        VuetifyResolver(),
      ],
    }),
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
