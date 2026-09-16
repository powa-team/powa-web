<template>
  <v-sheet
    class="mx-auto pa-4 my-5 text-center"
    max-width="400"
    rounded="lg"
    elevation="4"
  >
    <h3 class="mt-0 mb-6">
      <v-icon :icon="mdiAutoFix" size="30"></v-icon>
      Index Suggestion
    </h3>

    <p class="mb-4 text-medium-emphasis text-body-medium">
      PoWA can analyze executed quals to suggest indexes and verify what the
      gain would be.
    </p>
    <div>
      <v-btn
        color="primary"
        class="mr-4"
        variant="flat"
        block
        :to="optimizeUrl"
      >
        Optimize this database
      </v-btn>
    </div>
  </v-sheet>
</template>

<script setup>
import { computed } from "vue";
import { useRoute } from "vue-router";
import { mdiAutoFix } from "@mdi/js";

defineProps({
  config: {
    type: Object,
    default() {
      return {};
    },
  },
});

const route = useRoute();
const optimizeUrl = computed(() =>
  route.path.replace(/\/overview\/?$/, "/optimize/")
);
</script>
