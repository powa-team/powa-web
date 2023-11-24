<template>
  <div>
    <v-breadcrumbs :items="items">
      <template #item="{ item, index }">
        <v-breadcrumbs-item v-if="item.children">
          <v-select
            :items="item.children"
            :label="item.text"
            item-text="title"
            item-value="url"
            hide-details
            hide-selected
            density="compact"
            style="min-width: 200px"
            @update:model-value="onSelect"
          ></v-select>
        </v-breadcrumbs-item>
        <v-breadcrumbs-item
          v-else
          :to="item.href"
          exact-path
          :disabled="index == items.length - 1"
        >
          {{ item.text }}
        </v-breadcrumbs-item>
      </template>
    </v-breadcrumbs>
  </div>
</template>

<script setup>
import { toRef, watch } from "vue";
import store from "@/store";
import _ from "lodash";
import { useRouter } from "vue-router";
const props = defineProps({
  breadCrumbItems: {
    type: Array,
    default() {
      return [];
    },
  },
});

const items = toRef(props, "breadCrumbItems");
const router = useRouter();

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
  router.push(url);
}
</script>
