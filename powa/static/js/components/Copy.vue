<template>
  <v-btn
    :icon="copied ? mdiCheck : mdiClipboardMultipleOutline"
    @click="copy"
  />
</template>

<script setup>
import { ref } from "vue";
import { mdiCheck, mdiClipboardMultipleOutline } from "@mdi/js";

const props = defineProps({
  content: {
    type: String,
    default: "",
  },
});

const copied = ref(false);

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const copy = async () => {
  await navigator.clipboard.writeText(props.content);

  copied.value = true;

  await wait(2000);

  copied.value = false;
};
</script>
