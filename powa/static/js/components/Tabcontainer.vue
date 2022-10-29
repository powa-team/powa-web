<template>
  <v-card>
    <v-tabs v-model="activeTab" align-with-title role="tablist" show-arrows>
      <v-tab v-for="(tab, index) in props.config.tabs" :key="'tab' + index">
        {{ tab.title }}
      </v-tab>
    </v-tabs>
    <v-tabs-items v-model="activeTab">
      <v-tab-item
        v-for="(tab, index) in props.config.tabs"
        :key="'tab_content' + index"
        :transition="false"
      >
        <v-card>
          <v-card-text>
            <component :is="widgetComponent(tab.type)" :config="tab" />
          </v-card-text>
        </v-card>
      </v-tab-item>
    </v-tabs-items>
  </v-card>
</template>

<script setup>
import { ref } from "vue";
import { widgetComponent } from "../utils/widget-component.js";

const props = defineProps({
  config: {
    type: Object,
    default() {
      return {};
    },
  },
});

const activeTab = ref(0);
</script>
