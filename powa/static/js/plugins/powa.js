// inspired from https://zerotomastery.io/blog/how-to-auto-register-components-for-vue-with-vite/
import _ from "lodash";

export default {
  install(app) {
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

      app.component(`${componentName}`, m.default);
    });
  },
};
