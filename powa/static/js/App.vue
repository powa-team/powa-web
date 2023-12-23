<template>
  <v-app>
    <v-app-bar elevation="2" height="40" style="overflow: initial; z-index: 2">
      <v-btn
        :to="{ path: handlerConfig.homeUrl }"
        class="mr-2"
        title="Home page"
        exact
      >
        <img :src="handlerConfig.logoUrl" />&nbsp;<b>PoWA</b>
      </v-btn>
      <template v-if="handlerConfig.currentUser">
        <v-toolbar-title text class="mr-2 text-body-1">
          Server <b>{{ handlerConfig.currentServer }}</b> ({{
            handlerConfig.currentConnection
          }})
        </v-toolbar-title>
        <v-btn
          variant="text"
          :to="handlerConfig.configUrl"
          title="Configuration"
        >
          <v-icon start :icon="mdiCog" class="me-2" />
          Configuration
        </v-btn>
        <v-menu v-if="handlerConfig.notifyAllowed">
          <template #activator="{ props }">
            <v-btn variant="text" color="primary" v-bind="props">
              <v-icon start :icon="mdiReload" class="me-2"></v-icon>
              Actions
            </v-btn>
          </template>
          <v-list>
            <v-list-item link @click="reloadCollector">
              <v-list-item-title> Reload collector </v-list-item-title>
            </v-list-item>
            <v-list-item
              v-if="handlerConfig.server && handlerConfig.server != 0"
              link
              @click="forceSnapshot(handlerConfig.server)"
            >
              <v-list-item-title> Force a snapshot </v-list-item-title>
            </v-list-item>
            <v-list-item
              v-if="handlerConfig.server && handlerConfig.server != 0"
              link
              :data-dbname="handlerConfig.database"
              @click="refreshDbCat(handlerConfig.server, $event)"
            >
              <v-list-item-title>
                Refresh catalogs
                <span v-if="handlerConfig.database">
                  on db {{ handlerConfig.database }}</span
                >
                <span v-else> on all db</span>
              </v-list-item-title>
            </v-list-item>
          </v-list>
        </v-menu>

        <v-spacer></v-spacer>
        <v-switch
          v-model="theme.global.name.value"
          hide-details
          :false-icon="mdiWhiteBalanceSunny"
          :true-icon="mdiWeatherNight"
          true-value="dark"
          false-value="light"
          class="flex-grow-0"
          @update:model-value="toggleTheme"
        >
        </v-switch>
        <v-btn variant="text" color="primary" :href="handlerConfig.logoutUrl">
          <v-icon start :icon="mdiPower" class="me-2"></v-icon>
          Logout
        </v-btn>
      </template>
      <template v-if="handlerConfig.currentUser" #extension>
        <bread-crumbs :bread-crumb-items="breadcrumbs"></bread-crumbs>
        <v-spacer></v-spacer>
        <date-range-picker ml-auto @refresh="loadData"></date-range-picker>
      </template>
    </v-app-bar>
    <v-main>
      <v-container fluid>
        <dashboard v-if="dashboardConfig" :config="dashboardConfig"></dashboard>
        <login-view v-else-if="servers" :servers="servers"></login-view>
      </v-container>
    </v-main>
    <v-footer app absolute elevation="2" style="z-index: initial">
      <v-container fluid>
        <v-sheet class="d-flex">
          <v-sheet>
            <ul style="margin-bottom: 0; padding-left: 0">
              <li style="display: inline-block">
                Version {{ handlerConfig.version }}
              </li>
              <li style="display: inline-block" class="ml-5">
                &copy; 2014-2017 Dalibo
              </li>
              <li style="display: inline-block" class="ml-5">
                &copy; 2018-{{ handlerConfig.year }} The PoWA-team
              </li>
              <li style="display: inline-block" class="ml-5">
                <a href="https://powa.readthedocs.io"
                  >https://powa.readthedocs.io</a
                >
              </li>
            </ul>
          </v-sheet>
          <v-sheet class="text-right ms-auto">
            <a href="https://github.com/powa-team/powa-web/issues"
              >Report a bug</a
            >
          </v-sheet>
        </v-sheet>
      </v-container>
    </v-footer>
    <div
      class="d-flex flex-column-reverse powa-snackbars align-center"
      style="position: fixed; bottom: 0; width: 100%"
    >
      <div class="d-flex flex-column flex-column-reverse align-center">
        <v-snackbar
          v-for="message in alertMessages"
          :key="message.id"
          v-model="message.shown"
          :color="message.color"
          timeout="5000"
          :attach="true"
          @update:model-value="onSnackbarChanged(message.id, $event)"
        >
          <span v-html="message.message"></span>
          <template #actions>
            <v-icon
              text
              :icon="mdiClose"
              @click="closeSnackBar(message)"
            ></v-icon>
          </template>
        </v-snackbar>
      </div>
    </div>
  </v-app>
</template>

<script setup>
import { onMounted, provide, readonly, ref, watch } from "vue";
import { useTheme } from "vuetify";
import {
  mdiClose,
  mdiCog,
  mdiPower,
  mdiReload,
  mdiWeatherNight,
  mdiWhiteBalanceSunny,
} from "@mdi/js";
import { useDateRangeService } from "@/composables/DateRangeService.js";
import { useRoute } from "vue-router";
import _ from "lodash";
import * as d3 from "d3";
import BreadCrumbs from "@/components/BreadCrumbs.vue";
import DateRangePicker from "@/components/DateRangePicker/DateRangePicker.vue";
import LoginView from "@/components/LoginView.vue";
import { encodeQueryData } from "@/utils/query";
import { useMessageService } from "@/composables/MessageService.js";

const { alertMessages, addAlertMessage, removeAlertMessage } =
  useMessageService();

const theme = useTheme();
const { from, to, setFromTo } = useDateRangeService();
const route = useRoute();
const breadcrumbs = ref([]);
provide("breadcrumbs", readonly(breadcrumbs));
const dataSources = ref({});
provide("dataSources", readonly(dataSources));
const dashboardConfig = ref({});
provide("dashboardConfig", readonly(dashboardConfig));
const handlerConfig = ref({ homeUrl: "" });
const changesUrl = ref(null);
const changes = ref([]);
provide("changes", readonly(changes));

let servers;
document.querySelectorAll('script[type="text/servers"]').forEach(function (el) {
  servers = JSON.parse(el.innerText);
});

onMounted(() => {
  checkTheme();
});

function reloadCollector() {
  d3.json("/reload_collector/").then(
    (response) => {
      if (response) {
        addAlertMessage("success", "Collector successfully reloaded!");
      } else {
        addAlertMessage("error", "Could not reload collector");
      }
    },
    () => {
      addAlertMessage("error", "Error while trying to reload the collector.");
    }
  );
}

function forceSnapshot(srvid) {
  d3.json("/force_snapshot/" + srvid).then(
    (response) =>
      handleResponse(response, {
        success: "Forced snapshot requested. Status:",
        warning: "Problem with forcing an immediate snapshot:",
        alert: "Could not force an immediate snapshot:",
        error: "Could not force an immediate snapshot.",
      }),
    () => {
      addAlertMessage(
        "alert",
        "Error while trying to force an immediate snapshot."
      );
    }
  );
}

function refreshDbCat(srvid, event) {
  const dbnames = [];
  const dbname = event.target.parentElement.getAttribute("data-dbname");
  if (dbname) {
    dbnames.push(dbname);
  }

  d3.json("/refresh_db_cat/", {
    body: JSON.stringify({ srvid: srvid, dbnames: dbnames }),
    headers: {
      "Content-type": "application/json; charset=UTF-8",
    },
    method: "POST",
  }).then(
    (response) =>
      handleResponse(response, {
        success: "Catalog refresh successfully registered:",
        warning: "Problem with registering the catalog refresh:",
        alert: "Could not register the catalog refresh:",
        error: "Could not refresh the catalogs",
      }),
    () => {
      addAlertMessage("alert", "Error while trying to refresh the catalogs.");
    }
  );
}

function handleResponse(response, messages) {
  if (response) {
    response.forEach((i) => {
      const k = Object.keys(i)[0];
      const v = i[k];
      let level;
      let msg;

      switch (k) {
        case "OK":
          level = "success";
          msg = messages.success;
          break;
        case "WARNING":
        case "UNKNOWN":
          level = "warning";
          msg = messages.warning;
          break;
        default:
          level = "alert";
          msg = messages.alert;
          break;
      }

      msg += "<br/>" + v;

      addAlertMessage(level, msg);
    });
  } else {
    addAlertMessage("alert", messages.error);
  }
}

function onSnackbarChanged(id, isShown) {
  !isShown && removeAlertMessage(id);
}

function closeSnackBar(message) {
  message.shown = false;
  removeAlertMessage(message.id);
}

function toggleTheme() {
  localStorage.setItem("theme", theme.global.name.value);
}

function checkTheme() {
  const savedTheme = localStorage.getItem("theme");
  if (!_.isNull(savedTheme)) {
    theme.global.name.value = savedTheme;
  } else if (
    window.matchMedia &&
    window.matchMedia("(prefers-color-scheme: dark)").matches
  ) {
    theme.global.name.value = "dark";
    localStorage.setItem("theme", "dark");
  }
}

function initDashboard() {
  dashboardConfig.value = null;
  // Load dahsboard config from same url but asking for JSON instead of HTML
  d3.json(window.location.href, {
    headers: {
      "Content-type": "application/json",
    },
  }).then(configure);
}

function configure(config) {
  document.title = config.dashboard.title;
  dataSources.value = {};
  dashboardConfig.value = config.dashboard;
  handlerConfig.value = config.handler;
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
    dataSources.value[dataSource.name] = dataSource;
  });
  changesUrl.value = config.timeline;
  breadcrumbs.value = config.breadcrumbs;
  loadData();
}

function loadData() {
  const params = {
    from: from.value.format("YYYY-MM-DD HH:mm:ssZZ"),
    to: to.value.format("YYYY-MM-DD HH:mm:ssZZ"),
  };

  const copy = Object.assign({}, dataSources.value);
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
  dataSources.value = copy;
  if (changesUrl.value) {
    changes.value = d3.json(changesUrl.value + "?" + encodeQueryData(params));
  }
}

watch(
  () => route.params,
  function (newVal, oldVal) {
    setFromTo(route.query.from, route.query.to);
    if (newVal.pathMatch != oldVal.pathMatch) {
      initDashboard();
    } else {
      loadData();
    }
  }
);
</script>
