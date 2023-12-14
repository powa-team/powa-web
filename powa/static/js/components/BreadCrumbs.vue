<template>
  <div>
    <v-breadcrumbs :items="items">
      <template #item="{ item }">
        <v-breadcrumbs-item v-if="item.children">
          <v-select
            :items="item.children"
            :label="item.text"
            item-title="title"
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
          :to="getUrl(item.href)"
          :disabled="item.href == route.path"
        >
          {{ item.text }}
        </v-breadcrumbs-item>
      </template>
    </v-breadcrumbs>
  </div>
</template>

<script setup>
import { toRef } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useDateRangeService } from "@/composables/DateRangeService.js";
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
const route = useRoute();
const { getUrl } = useDateRangeService();

function onSelect(url) {
  router.push(getUrl(url));
}
</script>
