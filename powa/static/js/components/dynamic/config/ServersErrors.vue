<template>
  <v-card :loading="loading">
    <template #progress>
      <v-progress-linear
        height="2"
        indeterminate
        style="position: absolute; z-index: 1"
      ></v-progress-linear>
    </template>
    <v-card-item flat height="40px;">
      <v-card-title class="pl-0">{{ config.title }}</v-card-title>
    </v-card-item>
    <v-card-text v-if="errors !== undefined">
      <v-row>
        <v-col cols="12">
          <ul v-if="errors.length">
            <li v-for="(e, index) in errors" :key="index">
              <b>{{ e.server_alias }}:</b>
              <ul>
                <li v-for="msg in e.errors" :key="msg">{{ msg }}</li>
              </ul>
            </li>
          </ul>
          <template v-else> No error! </template>
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { useFetch } from "@/utils/fetch.js";

const props = defineProps({
  config: {
    type: Object,
    default() {
      return {};
    },
  },
});

const { loading, data: errors } = useFetch(props.config.name);
</script>
