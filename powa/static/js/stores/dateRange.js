import { computed, ref } from "vue";
import { defineStore } from "pinia";
import { useRoute } from "vue-router";
import dateMath from "@/utils/datemath";

export const useDateRangeStore = defineStore("daterange", () => {
  const route = useRoute();
  const defaultFrom = "now-1h";
  const defaultTo = "now";
  const rawFrom = computed(() => route.query.from || defaultFrom);
  const rawTo = computed(() => route.query.to || defaultTo);
  const refreshCount = ref(0);

  const from = computed(() => {
    refreshCount.value;
    return dateMath.parse(rawFrom.value);
  });
  const to = computed(() => {
    refreshCount.value;
    return dateMath.parse(rawTo.value);
  });

  const urlSearchParams = computed(() =>
    new URLSearchParams({
      from: from.value.format("YYYY-MM-DD HH:mm:ssZZ"),
      to: to.value.format("YYYY-MM-DD HH:mm:ssZZ"),
    }).toString()
  );

  function refresh() {
    // force refresh of computed properties
    refreshCount.value++;
  }

  function getUrl(url) {
    // Utility function to build links url
    const query = {};
    if (rawFrom.value != defaultFrom || rawTo.value != defaultTo) {
      query.from = rawFrom.value;
      query.to = rawTo.value;
    }
    return { path: url, query };
  }

  return { rawFrom, rawTo, from, to, refresh, getUrl, urlSearchParams };
});
