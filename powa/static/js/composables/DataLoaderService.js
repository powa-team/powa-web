import { inject, onMounted, ref, watchEffect } from "vue";

export function useDataLoader(metric) {
  const loading = ref(false);
  const data = ref(undefined);
  const dataSources = inject("dataSources");

  onMounted(() => {
    watchEffect(() => {
      loading.value = true;
      const sourceConfig = dataSources.value[metric];
      sourceConfig.promise.then((response) => {
        data.value = JSON.parse(response);
        loading.value = false;
      });
    });
  });

  return { loading, data };
}
