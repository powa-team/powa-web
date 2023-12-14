import { onMounted, ref, watchEffect } from "vue";
import { useDateRangeService } from "@/composables/DateRangeService.js";

export function useDataLoader(metric) {
  const loading = ref(false);
  const data = ref(undefined);
  const { dataSources } = useDateRangeService();

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
