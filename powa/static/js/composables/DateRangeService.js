import { ref } from "vue";
import { dateMath } from "@grafana/data";

const defaultFrom = "now-1h";
const rawFrom = ref(defaultFrom);
const defaultTo = "now";
const rawTo = ref(defaultTo);

const from = ref(dateMath.parse(defaultFrom));
const to = ref(dateMath.parse(defaultTo), true);

function getUrl(url) {
  const query = {};
  if (rawFrom.value != defaultFrom || rawTo.value != defaultTo) {
    query.from = rawFrom.value;
    query.to = rawTo.value;
  }
  return { path: url, query };
}

export function useDateRangeService() {
  function setFromTo(newFrom = defaultFrom, newTo = defaultTo) {
    rawFrom.value = newFrom;
    rawTo.value = newTo;
    from.value = dateMath.parse(newFrom);
    to.value = dateMath.parse(newTo);
  }

  return {
    rawFrom,
    rawTo,
    from,
    to,
    setFromTo,
    getUrl,
  };
}
