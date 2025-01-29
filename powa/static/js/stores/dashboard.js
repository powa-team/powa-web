import * as _ from "lodash";
import { reactive, ref, watch } from "vue";
import { defineStore, storeToRefs } from "pinia";
import { useRoute } from "vue-router";
import { useDateRangeStore } from "@/stores/dateRange.js";
import { useMessageService } from "@/composables/MessageService.js";
const { addAlertMessages } = useMessageService();

export const useDashboardStore = defineStore("dashboard", () => {
  const route = useRoute();
  const dateRangeStore = useDateRangeStore();
  const { urlSearchParams } = storeToRefs(dateRangeStore);
  const isFetching = ref(false);
  const dashboardConfig = ref(null);
  const handlerConfig = ref({ homeUrl: "" });
  const breadcrumbs = ref([]);
  const dataSources = ref({});
  const changesUrl = ref(null);
  const changes = ref(null);
  const changesFetching = ref(false);
  let dashboardController;
  let changesController;

  function cleanUpDashboard() {
    // Force a clean up of all components for the page
    dashboardConfig.value = null;
    dashboardController && dashboardController.abort();
  }

  function cleanUpDataSources() {
    _.each(dataSources.value, (source) => {
      source.controller && source.controller.abort();
    });
  }

  function cleanUpChanges() {
    changesController && changesController.abort();
    changes.value = null;
  }

  function fetchDashboardConfig() {
    cleanUpDashboard();
    cleanUpDataSources();
    cleanUpChanges();
    isFetching.value = true;
    dashboardController = new AbortController();
    fetch(route.path, {
      signal: dashboardController.signal,
      headers: {
        "Content-type": "application/json",
      },
    })
      .then((res) => res.json())
      .then(dashboardConfigFetched)
      .catch(() => {});
  }

  function dashboardConfigFetched(config) {
    isFetching.value = false;
    dataSources.value = {};
    handlerConfig.value = config.handler;
    breadcrumbs.value = config.breadcrumbs;
    changesUrl.value = config.timeline;

    config.datasources.forEach((config) => {
      try {
        if (config.type == "metric_group") {
          config.metrics = _.keyBy(config.metrics, "name");
        }
      } catch (e) {
        console.error(
          "Could not instantiate metric group. Check the metric group definition"
        );
      }

      const source = reactive({
        config,
        isFetching: true,
        data: null,
        error: null,
        controller: null,
      });
      dataSources.value[config.name] = source;
    });

    // Make sure from/to are up-to-date
    dateRangeStore.refresh();
    dashboardConfig.value = config.dashboard;
  }

  function fetchDataSources() {
    cleanUpDataSources();
    _.each(dataSources.value, (source) => {
      source.isFetching = true;
      source.controller = new AbortController();
      fetch(`${source.config.data_url}?${urlSearchParams.value}`, {
        signal: source.controller.signal,
      })
        .then((res) => res.json())
        .then((json) => {
          source.data = json;
          addAlertMessages(json.messages);
        })
        .catch((err) => (source.error = err))
        .finally(() => {
          source.isFetching = false;
        });
    });
  }

  function fetchChanges() {
    cleanUpChanges();
    if (!changesUrl.value) {
      return;
    }
    changesController = new AbortController();
    changesFetching.value = true;
    fetch(`${changesUrl.value}?${urlSearchParams.value}`, {
      signal: changesController.signal,
    })
      .then((res) => res.json())
      .then((json) => {
        changesFetching.value = false;
        changes.value = json;
      })
      .catch(() => {})
      .finally(() => {
        changesFetching.value = false;
      });
  }

  watch(() => route.path, fetchDashboardConfig);
  watch(() => [dataSources.value, urlSearchParams.value], fetchDataSources);
  watch(() => [changesUrl.value, urlSearchParams.value], fetchChanges);

  return {
    breadcrumbs,
    changes,
    changesFetching,
    dashboardConfig,
    dataSources,
    handlerConfig,
    isFetching,
  };
});
