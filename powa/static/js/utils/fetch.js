import { onMounted, ref, watch } from "vue";
import store from "@/store";

export function useFetch(name) {
  const loading = ref(false);
  const data = ref(undefined);

  onMounted(() => {
    watch(
      () => store.dataSources,
      () => {
        loadData();
      },
      { immediate: true }
    );
  });

  function loadData() {
    loading.value = true;
    const sourceConfig = store.dataSources[name];
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
