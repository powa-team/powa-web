<template>
  <div class="card mb-4">
    <div class="card-header">
      <ul
        class="nav nav-tabs card-header-tabs"
        role="tablist"
      >
        <li
          v-for="(tab, index) in tabs"
          :key="tab.uuid"
          class="nav-item"
        >
          <a
            :href="'#' + tab.uuid"
            :class="['nav-link', {'active': index === 0}]"
            data-toggle="tab"
            role="tab"
            :aria-controls="tab.uuid"
            :aria-selected="index === 0 ? 'true' : 'false'"
          >
            {{ tab.title }}
          </a>
        </li>
      </ul>
    </div>
    <div class="tab-content">
      <div
        v-for="(tab, index) in tabs"
        :id="tab.uuid"
        :key="tab.uuid"
        :class="['tab-pane card-body', {'show active': index === 0}]"
        role="tabpanel"
        :aria-labelledby="tab.uuid"
      >
        <component
          :is="widgetComponent(tab.type)"
          v-if="activeTab == tab.uuid"
          :config="tab"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import * as _ from 'lodash';
import $ from "jquery";
import { widgetComponent } from "../utils/widget-component.js"

const props = defineProps(["config"])

const activeTab = ref(null)

const tabs = computed(() => {
  // Provide a unique Id to tabs
  return _.map(props.config.tabs,
               (tab) => Object.assign({uuid: _.uniqueId('tab-')}, tab));
  }
)

onMounted(() => {
  activeTab.value = tabs.value[0].uuid;
  $('a[data-toggle="tab"]').on('shown.bs.tab', function (e) {
    activeTab.value = e.target.getAttribute('aria-controls');
  });
})
</script>
