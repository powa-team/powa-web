import { onMounted, ref, watch } from "vue";
import store from "@/store";
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

  watch(
    () => store.rawFrom + store.rawTo,
    () => {
      loadData();
    }
  );

  return { loading, data };
}
