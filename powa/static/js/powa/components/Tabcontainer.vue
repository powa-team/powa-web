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

<script>
import * as _ from 'lodash';
import Widget from './Widget.vue';

export default {
  extends: Widget,
  data: () => {
    return {
      activeTab: null
    }
  },

  computed: {
    tabs () {
      // Provide a unique Id to tabs
      return _.map(this.config.tabs,
                   (tab) => Object.assign({uuid: _.uniqueId('tab-')}, tab));
    }
  },

  mounted() {
    this.activeTab = this.tabs[0].uuid;
    $('a[data-toggle="tab"]').on('shown.bs.tab', function (e) {
      this.activeTab = e.target.getAttribute('aria-controls');
    }.bind(this));
  }
}
</script>
