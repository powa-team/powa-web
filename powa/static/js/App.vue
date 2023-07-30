<template>
  <v-app>
    <v-app-bar app elevation="2" height="40px;">
      <v-btn
        :href="handler.homeUrl"
        class="mr-2"
        text
        color="primary"
        elevation="0"
      >
        <img :src="handler.logoUrl" />&nbsp;<b>PoWA</b>
      </v-btn>
      <template v-if="handler.currentUser">
        <v-toolbar-title text class="mr-2 text-body-1">
          Server <b>{{ handler.currentServer }}</b> ({{
            handler.currentConnection
          }})
        </v-toolbar-title>
        <v-btn
          text
          color="primary"
          :href="handler.configUrl"
          title="Configuration"
        >
          <v-icon left>
            {{ icons.mdiCog }}
          </v-icon>
          Configuration
        </v-btn>
        <v-menu v-if="handler.notifyAllowed" offset-y>
          <template #activator="{ on, attrs }">
            <v-btn text color="primary" v-bind="attrs" v-on="on">
              <v-icon left>
                {{ icons.mdiReload }}
              </v-icon>
              Actions
            </v-btn>
          </template>
          <v-list>
            <v-list-item link @click="reloadCollector">
              <v-list-item-title> Reload collector </v-list-item-title>
            </v-list-item>
            <v-list-item
              v-if="handler.server"
              link
              @click="forceSnapshot(handler.server)"
            >
              <v-list-item-title> Force a snapshot </v-list-item-title>
            </v-list-item>
            <v-list-item
              v-if="handler.server"
              link
              :data-dbname="handler.database"
              @click="refreshDbCat(handler.server, $event)"
            >
              <v-list-item-title>
                Refresh catalogs
                <span v-if="handler.database">
                  on db {{ handler.database }}</span
                >
                <span v-else> on all db</span>
              </v-list-item-title>
            </v-list-item>
          </v-list>
        </v-menu>

        <v-spacer></v-spacer>
        <v-btn text color="primary" :href="handler.logoutUrl">
          <v-icon left>
            {{ icons.mdiPower }}
          </v-icon>
          Logout
        </v-btn>
      </template>
      <template v-if="handler.currentUser" #extension>
        <bread-crumbs :bread-crumb-items="breadCrumbItems"></bread-crumbs>
        <v-spacer></v-spacer>
        <date-range-picker ml-auto></date-range-picker>
      </template>
    </v-app-bar>
    <v-main class="grey lighten-3">
      <v-container fluid>
        <v-row>
          <v-col>
            <dashboard
              v-if="dashboardConfig"
              :config="dashboardConfig"
            ></dashboard>
            <login-view v-else :servers="servers"></login-view>
          </v-col>
        </v-row>
      </v-container>
    </v-main>
    <v-footer>
      <v-container fluid>
        <v-row>
          <v-flex>
            <ul style="margin-bottom: 0; padding-left: 0">
              <li style="display: inline-block">
                Version {{ handler.version }}
              </li>
              <li style="display: inline-block" class="ml-5">
                &copy; 2014-2017 Dalibo
              </li>
              <li style="display: inline-block" class="ml-5">
                &copy; 2018-{{ handler.year }} The PoWA-team
              </li>
              <li style="display: inline-block" class="ml-5">
                <a href="https://powa.readthedocs.io"
                  >https://powa.readthedocs.io</a
                >
              </li>
            </ul>
          </v-flex>
          <v-flex ml-auto class="text-right">
            <a href="https://github.com/powa-team/powa-web/issues"
              >Report a bug</a
            >
          </v-flex>
        </v-row>
      </v-container>
    </v-footer>
    <v-snackbars :objects.sync="store.alertMessages">
      <template #default="{ message }">
        <span v-html="message"></span>
      </template>
      <template #action="{ close }">
        <v-icon text @click="close()">{{ icons.mdiClose }}</v-icon>
      </template>
    </v-snackbars>
  </v-app>
</template>

<script setup>
import { icons } from "./plugins/vuetify.js";
import store from "./store";
import * as d3 from "d3";
let handler;
document.querySelectorAll('script[type="text/handler"]').forEach(function (el) {
  handler = JSON.parse(el.innerText);
});

let breadCrumbItems;
document
  .querySelectorAll('script[type="text/breadcrumb"]')
  .forEach(function (el) {
    breadCrumbItems = JSON.parse(el.innerText);
  });

let dashboardConfig;
document
  .querySelectorAll('script[type="text/dashboard"]')
  .forEach(function (el) {
    dashboardConfig = JSON.parse(el.innerText);
  });

let servers;
document.querySelectorAll('script[type="text/servers"]').forEach(function (el) {
  servers = JSON.parse(el.innerText);
});

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
</script>
