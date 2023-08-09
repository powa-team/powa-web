<template>
  <div>
    <v-breadcrumbs :items="items">
      <template #item="{ item }">
        <v-breadcrumbs-item v-if="item.children">
          <v-select
            :items="item.children"
            :label="item.text"
            item-text="title"
            item-value="url"
            hide-details
            hide-selected
            @change="onSelect"
          ></v-select>
        </v-breadcrumbs-item>
        <v-breadcrumbs-item v-else :to="item.href" exact-path>
          {{ item.text }}
        </v-breadcrumbs-item>
      </template>
    </v-breadcrumbs>
  </div>
</template>

<script setup>
import { getCurrentInstance } from "vue";
import { toRef, watch } from "vue";
import store from "@/store";
import _ from "lodash";
const props = defineProps({
  breadCrumbItems: {
    type: Array,
    default() {
      return [];
    },
  },
});

const instance = getCurrentInstance();
const items = toRef(props, "breadCrumbItems");

watch(
  () => store.rawFrom + store.rawTo,
  () => {
    _.each(items.value, (item) => {
      if (item.text == "Home") {
        return;
      }
      const baseUrl = new URL(window.location.href);
      const url = new URL(item.href, baseUrl.origin);
      url.searchParams.set("to", store.rawTo);
      url.searchParams.set("from", store.rawFrom);
      item.href = url.pathname + url.search;
    });
  }
);

function onSelect(url) {
  instance.proxy.$router.push(url);
}
</script>
