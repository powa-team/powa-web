import { computed } from "vue";
import { storeToRefs } from "pinia";
import { useDashboardStore } from "@/stores/dashboard.js";

export function useDataLoader(metric) {
  const { dataSources } = storeToRefs(useDashboardStore());
  const source = computed(() => dataSources.value[metric]);
  const loading = computed(() => source.value.isFetching);
  const data = computed(() => {
    if (!source.value.executed) {
      source.value.execute();
    }
    return source.value.data;
  });

  return { data, loading, source };
}
