<template>
  <v-app>
    <v-app-bar elevation="2" height="40" style="overflow: initial; z-index: 2">
      <v-btn
        :to="{ path: store.handlerConfig.homeUrl }"
        class="mr-2"
        title="Home page"
        exact
      >
        <img :src="store.handlerConfig.logoUrl" />&nbsp;<b>PoWA</b>
      </v-btn>
      <template v-if="store.handlerConfig.currentUser">
        <v-toolbar-title text class="mr-2 text-body-1">
          Server <b>{{ store.handlerConfig.currentServer }}</b> ({{
            store.handlerConfig.currentConnection
          }})
        </v-toolbar-title>
        <v-btn
          variant="text"
          :to="store.handlerConfig.configUrl"
          title="Configuration"
        >
          <v-icon start :icon="icons.mdiCog" class="me-2" />
          Configuration
        </v-btn>
        <v-menu v-if="store.handlerConfig.notifyAllowed">
          <template #activator="{ props }">
            <v-btn variant="text" color="primary" v-bind="props">
              <v-icon start :icon="icons.mdiReload" class="me-2"></v-icon>
              Actions
            </v-btn>
          </template>
          <v-list>
            <v-list-item link @click="reloadCollector">
              <v-list-item-title> Reload collector </v-list-item-title>
            </v-list-item>
            <v-list-item
              v-if="
                store.handlerConfig.server && store.handlerConfig.server != 0
              "
              link
              @click="forceSnapshot(store.handlerConfig.server)"
            >
              <v-list-item-title> Force a snapshot </v-list-item-title>
            </v-list-item>
            <v-list-item
              v-if="
                store.handlerConfig.server && store.handlerConfig.server != 0
              "
              link
              :data-dbname="store.handlerConfig.database"
              @click="refreshDbCat(store.handlerConfig.server, $event)"
            >
              <v-list-item-title>
                Refresh catalogs
                <span v-if="store.handlerConfig.database">
                  on db {{ store.handlerConfig.database }}</span
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
          :false-icon="icons.mdiWhiteBalanceSunny"
          :true-icon="icons.mdiWeatherNight"
          true-value="dark"
          false-value="light"
          class="flex-grow-0"
          @update:model-value="toggleTheme"
        >
        </v-switch>
        <v-btn
          variant="text"
          color="primary"
          :href="store.handlerConfig.logoutUrl"
        >
          <v-icon start :icon="icons.mdiPower" class="me-2"></v-icon>
          Logout
        </v-btn>
      </template>
      <template v-if="store.handlerConfig.currentUser" #extension>
        <bread-crumbs :bread-crumb-items="store.breadcrumbs"></bread-crumbs>
        <v-spacer></v-spacer>
        <date-range-picker ml-auto></date-range-picker>
      </template>
    </v-app-bar>
    <v-main>
      <v-container fluid>
        <dashboard
          v-if="store.dashboardConfig"
          :config="store.dashboardConfig"
        ></dashboard>
        <login-view v-else-if="servers" :servers="servers"></login-view>
      </v-container>
    </v-main>
    <v-footer app absolute elevation="2">
      <v-container fluid>
        <v-sheet class="d-flex">
          <v-sheet>
            <ul style="margin-bottom: 0; padding-left: 0">
              <li style="display: inline-block">
                Version {{ store.handlerConfig.version }}
              </li>
              <li style="display: inline-block" class="ml-5">
                &copy; 2014-2017 Dalibo
              </li>
              <li style="display: inline-block" class="ml-5">
                &copy; 2018-{{ store.handlerConfig.year }} The PoWA-team
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
          v-for="message in store.alertMessages"
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
              :icon="icons.mdiClose"
              @click="closeSnackBar(message)"
            ></v-icon>
          </template>
        </v-snackbar>
      </div>
    </div>
  </v-app>
</template>

<script setup>
import { watch } from "vue";
import { onMounted } from "vue";
import { useTheme } from "vuetify";
import { icons } from "@/plugins/vuetify.js";
import store from "@/store";
import _ from "lodash";
import * as d3 from "d3";
import BreadCrumbs from "@/components/BreadCrumbs.vue";
import DateRangePicker from "@/components/DateRangePicker/DateRangePicker.vue";
import LoginView from "@/components/LoginView.vue";
import { useRoute } from "vue-router";

const theme = useTheme();
const route = useRoute();

let servers;
document.querySelectorAll('script[type="text/servers"]').forEach(function (el) {
  servers = JSON.parse(el.innerText);
});

onMounted(() => {
  checkTheme();
  initDashboard();
});

function initDashboard() {
  store.dashboardConfig = null;
  // Load dahsboard config from same url but asking for JSON instead of HTML
  d3.json(window.location.href, {
    headers: {
      "Content-type": "application/json",
    },
  }).then(store.configure);
}

function reloadCollector() {
  d3.json("/reload_collector/").then(
    (response) => {
      if (response) {
        store.addAlertMessage("success", "Collector successfully reloaded!");
      } else {
        store.addAlertMessage("error", "Could not reload collector");
      }
    },
    () => {
      store.addAlertMessage(
        "error",
        "Error while trying to reload the collector."
      );
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
      store.addAlertMessage(
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
      store.addAlertMessage(
        "alert",
        "Error while trying to refresh the catalogs."
      );
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

      store.addAlertMessage(level, msg);
    });
  } else {
    store.addAlertMessage("alert", messages.error);
  }
}

function onSnackbarChanged(id, isShown) {
  !isShown && store.removeAlertMessage(id);
}

function closeSnackBar(message) {
  message.shown = false;
  store.removeAlertMessage(message.id);
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

watch(() => route.params, initDashboard);
</script>
