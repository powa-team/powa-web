// inspired from https://zerotomastery.io/blog/how-to-auto-register-components-for-vue-with-vite/
import _ from "lodash";
import Vue from "vue";

export default {
  install() {
    const componentFiles = import.meta.globEager(
      "@/components/dynamic/**/*.vue"
    );

    Object.entries(componentFiles).forEach(([path, m]) => {
      const componentName = _.upperFirst(
        _.camelCase(
          path
            .split("/")
            .pop()
            .replace(/\.\w+$/, "")
        )
      );

      Vue.component(`${componentName}`, m.default);
    });
  },
};
