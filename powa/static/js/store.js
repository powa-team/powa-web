import { nextTick, reactive } from "vue";
import _ from "lodash";
import * as d3 from "d3";
import { encodeQueryData } from "./utils/query";
import { dateMath } from "@grafana/data";

const initialQuery = parseQuery(window.location.search);
let messageId = 1;

const store = reactive({
  dashboardConfig: null,
  dataSources: {},
  changesUrl: "",
  changes: [],
  breadcrumbs: [],
  rawFrom: initialQuery.from || "now-1h",
  rawTo: initialQuery.to || "now",
  from: null,
  to: null,
  setFromTo(from, to, silent) {
    silent = !!silent;
    this.rawFrom = from;
    this.rawTo = to;
    if (!silent) {
      history.pushState(
        {},
        "",
        window.location.pathname + "?" + this.serialize()
      );
    }
    this.loadData();
  },
  configure(config) {
    store.dataSources = {};
    store.dashboardConfig = config.dashboard;
    _.each(config.datasources, function (dataSource) {
      try {
        if (dataSource.type == "metric_group") {
          dataSource.metrics = _.keyBy(dataSource.metrics, "name");
        }
      } catch (e) {
        console.error(
          "Could not instantiate metric group. Check the metric group definition"
        );
      }
      store.dataSources[dataSource.name] = dataSource;
    });
    store.changesUrl = config.timeline;
    store.breadcrumbs = config.breadcrumbs;
    store.loadData();
  },
  loadData() {
    this.from = dateMath.parse(this.rawFrom);
    this.to = dateMath.parse(this.rawTo, true);
    const params = {
      from: this.from.format("YYYY-MM-DD HH:mm:ssZZ"),
      to: this.to.format("YYYY-MM-DD HH:mm:ssZZ"),
    };

    const copy = Object.assign({}, this.dataSources);
    _.forEach(copy, (source) => {
      source.promise = d3.text(source.data_url + "?" + encodeQueryData(params));
      source.promise.then((response) => {
        try {
          const data = JSON.parse(response);
          if (data) {
            this.addAlertMessages(data.messages);
          }
        } catch (error) {
          // pass
          // this may correspond to content widgets for example
        }
      });
    });
    this.dataSources = copy;
    if (this.changesUrl) {
      this.changes = d3.json(this.changesUrl + "?" + encodeQueryData(params));
    }
  },
  alertMessages: [],
  addAlertMessage(level, message) {
    const colors = {
      alert: "red",
      error: "red",
      warning: "orange",
      info: "blue",
      success: "green",
    };
    this.alertMessages.push({
      id: ++messageId,
      color: colors[level],
      message: message,
      shown: false,
    });
    nextTick(() => (_.last(this.alertMessages).shown = true));
  },
  addAlertMessages(messages) {
    _.forEach(messages, function (value, key) {
      for (let message of value) {
        store.addAlertMessage(key, message);
      }
    });
  },
  removeAlertMessage(id) {
    // Remove message from list with delay to make sure transition is finished
    window.setTimeout(() => {
      _.remove(this.alertMessages, (n) => n.id == id);
      // workaround to force an update of components
      this.alertMessages = [].concat(this.alertMessages);
    }, 500);
  },
  serialize() {
    return [
      "from=" + encodeURIComponent(store.rawFrom),
      "to=" + encodeURIComponent(store.rawTo),
    ].join("&");
  },
});

addEventListener("popstate", () => {
  const query = parseQuery(window.location.search);
  if (query.from && query.to) {
    store.setFromTo(query.from, query.to, true);
  }
});

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
