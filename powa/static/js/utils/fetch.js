import { onMounted, ref, watch } from "vue";
import { useStoreService } from "@/composables/useStoreService";

export function useFetch(name) {
  const loading = ref(false);
  const data = ref(undefined);
  const { dataSources } = useStoreService();

  onMounted(() => {
    watch(
      () => dataSources.value,
      () => {
        loadData();
      },
      { immediate: true }
    );
  });

  function loadData() {
    loading.value = true;
    const sourceConfig = dataSources.value[name];
    sourceConfig.promise.then((response) => {
      data.value = JSON.parse(response);
      loading.value = false;
    });
  }

  return { loading, data };
}
