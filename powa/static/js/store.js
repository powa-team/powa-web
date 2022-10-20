import { reactive } from "vue";

const initialQuery = parseQuery(window.location.search);

const store = reactive({
  dataSources: {},
  from: initialQuery.from || "now-1h",
  to: initialQuery.to || "now",
  setFromTo(from, to, silent) {
    silent = !!silent;
    this.from = from;
    this.to = to;
    if (!silent) {
      history.pushState({}, "", window.location.pathname + "?" + serialize());
    }
  },
});

addEventListener("popstate", () => {
  const query = parseQuery(window.location.search);
  if (query.from && query.to) {
    store.setFromTo(query.from, query.to, true);
  }
});

export function serialize() {
  var str = [
    "from=" + encodeURIComponent(store.from),
    "to=" + encodeURIComponent(store.to),
  ];
  return str.join("&");
}

function parseQuery(queryString) {
  var query = {};
  var pairs = (
    queryString[0] === "?" ? queryString.substr(1) : queryString
  ).split("&");
  for (var i = 0; i < pairs.length; i++) {
    var pair = pairs[i].split("=");
    query[decodeURIComponent(pair[0])] = decodeURIComponent(pair[1] || "");
  }
  return query;
}

export default store;
