<template>
  <v-card>
    <v-tabs
      v-model="activeTab"
      align-tabs="title"
      role="tablist"
      show-arrows
      density="compact"
      color="primary"
    >
      <v-tab v-for="(tab, index) in config.tabs" :key="'tab' + index">
        {{ tab.title }}
      </v-tab>
    </v-tabs>
    <v-window v-model="activeTab">
      <v-window-item
        v-for="(tab, index) in config.tabs"
        :key="'tab_content' + index"
        :transition="false"
        :reverse-transition="false"
      >
        <v-card>
          <v-card-text>
            <component
              :is="widgetComponent(tab)"
              v-if="activeTab == index"
              :config="tab"
            />
          </v-card-text>
        </v-card>
      </v-window-item>
    </v-window>
  </v-card>
</template>

<script setup>
import { ref } from "vue";
import { widgetComponent } from "@/utils/widget-component.js";

defineProps({
  config: {
    type: Object,
    default() {
      return {};
    },
  },
});

const activeTab = ref(0);
</script>
