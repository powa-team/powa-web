import { useRoute, useRouter } from "vue-router";
import { ref } from "vue";

const dataSources = ref({});
const dashboardConfig = ref(null);
const handlerConfig = ref({
  homeUrl: "",
});
const changesUrl = ref("");
const changes = ref([]);
const breadcrumbs = ref([]);
const defaultFrom = "now-1h";
const from = ref(defaultFrom);
const defaultTo = "now";
const to = ref(defaultTo);

function getUrl(url) {
  const query = {};
  if (from.value != defaultFrom || to.value != defaultTo) {
    query.from = from.value;
    query.to = to.value;
  }
  return { path: url, query };
}

export function useStoreService() {
  const route = useRoute();
  const router = useRouter();

  function setFromTo(from, to) {
    router.push({
      path: route.path,
      query: { from: from, to: to },
    });
  }

  return {
    defaultFrom,
    defaultTo,
    dataSources,
    dashboardConfig,
    handlerConfig,
    changesUrl,
    changes,
    breadcrumbs,
    from,
    to,
    setFromTo,
    getUrl,
  };
}
