<template>
  <div>
    <v-btn>
      <v-icon class="mr-2">
        {{ icons.mdiClockOutline }}
      </v-icon>
      <span>{{ rangeString }}</span>
      <v-menu v-model="menu" activator="parent" :close-on-content-click="false">
        <v-sheet class="d-flex" height="350" width="540" no-gutters>
          <v-sheet
            class="pa-6 flex-grow-1"
            style="border-right: 1px solid #dfdfdf"
          >
            <v-form ref="form" v-model="valid">
              <b>Absolute time range</b>
              <br />
              <br />
              From
              <br />
              <v-row>
                <v-col cols="auto">
                  <v-dialog v-model="fromDialog" activator="parent">
                    <template #activator="{ props }">
                      <v-btn
                        size="small"
                        :icon="icons.mdiCalendar"
                        v-bind="props"
                      >
                      </v-btn>
                    </template>
                    <v-date-picker
                      v-model="pickerFrom"
                      title="Select 'from' date"
                    >
                      <template #actions>
                        <v-btn text color="primary" @click="cancelPicker">
                          Cancel
                        </v-btn>
                        <v-btn
                          text
                          class="bg-primary"
                          :disabled="pickerFrom == null"
                          @click="applyPickerFromDate"
                        >
                          OK
                        </v-btn>
                      </template>
                    </v-date-picker>
                  </v-dialog>
                </v-col>
                <v-col>
                  <v-text-field
                    v-model="inputFrom"
                    :rules="fromRules"
                    hide-details
                    hide-selected
                    density="compact"
                  ></v-text-field>
                </v-col>
              </v-row>
              <br />
              To
              <br />
              <v-row>
                <v-col cols="auto">
                  <v-dialog
                    v-model="toDialog"
                    activator="parent"
                    max-width="400"
                  >
                    <template #activator="{ props }">
                      <v-btn
                        size="small"
                        :icon="icons.mdiCalendar"
                        v-bind="props"
                      >
                      </v-btn>
                    </template>
                    <v-date-picker v-model="pickerTo" title="Select 'to' date">
                      <template #actions>
                        <v-btn text color="primary" @click="cancelPicker">
                          Cancel
                        </v-btn>
                        <v-btn
                          text
                          class="bg-primary"
                          :disabled="pickerTo == null"
                          @click="applyPickerToDate"
                        >
                          OK
                        </v-btn>
                      </template>
                    </v-date-picker>
                  </v-dialog>
                </v-col>
                <v-col>
                  <v-text-field
                    v-model="inputTo"
                    :rules="toRules"
                    hide-details
                    hide-selected
                    density="compact"
                  ></v-text-field>
                </v-col>
              </v-row>
              <v-btn
                class="mt-4"
                :disabled="!valid"
                variant="elevated"
                @click="applyTimeRange"
                >Apply time range</v-btn
              >
            </v-form>
          </v-sheet>
          <v-sheet sm="5" width="180" class="overflow-auto">
            <v-list dense>
              <v-list-item
                v-for="(range, index) in quickOptions"
                :key="index"
                link
                @click.prevent="loadRangeShortcut(range)"
              >
                {{ range.display }}
              </v-list-item>
            </v-list>
          </v-sheet>
        </v-sheet>
      </v-menu>
    </v-btn>
    <v-btn @click="refresh">
      <v-icon>
        {{ icons.mdiReload }}
      </v-icon>
    </v-btn>
    <v-btn class="me-4" @click="zoomOut">
      <v-icon>
        {{ icons.mdiMagnifyMinusOutline }}
      </v-icon>
    </v-btn>
  </div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { quickOptions } from "./options.ts";
import { dateMath, rangeUtil } from "@grafana/data";
import { icons } from "@/plugins/vuetify";
import { toISO } from "@/utils/dates";
import { useStoreService } from "@/composables/useStoreService.js";

const menu = ref(false);
const { from, to, setFromTo } = useStoreService();

// The raw values (examples: 'now-24h', 'Tue Sep 01 2020 10:16:00 GMT+0200')
// Interaction with parent component is done with from/to props which
// are unix timestamps
const rawFrom = ref(from.value);
const rawTo = ref(to.value);
// The values to display in the custom range from and to fields
// we don't use raw values because we may want to pick/change from and
// to in the form before applying changes
const inputFrom = ref(rawFrom.value);
const inputTo = ref(rawTo.value);

const pickerFrom = ref(null);
const pickerTo = ref(null);

const fromDialog = ref(false);
const toDialog = ref(false);

const form = ref(null);
const valid = ref(true);

const emit = defineEmits({
  refresh: () => true,
});

const rangeString = computed(() => {
  if (!from.value || !to.value) {
    return;
  }
  return rangeUtil.describeTimeRange({ from: from.value, to: to.value });
});

const requiredMsg = `Please enter a past date or "now"`;

const commonRules = [
  (value) => !!value || requiredMsg,
  (value) => !!dateMath.parse(value) || requiredMsg,
];
const fromRules = ref(
  commonRules.concat([
    () => {
      return (
        !dateMath.parse(inputFrom.value) ||
        !dateMath.parse(inputTo.value) ||
        dateMath.parse(inputFrom.value) < dateMath.parse(inputTo.value, true) ||
        `"From" can't be after "To"`
      );
    },
  ])
);
const toRules = ref(commonRules);

function loadRangeShortcut(shortcut) {
  menu.value = false;
  setFromTo(shortcut.from, shortcut.to);
}

watch(
  () => from.value,
  () => {
    inputFrom.value = from.value;
    synchronizeFromPicker();
  }
);
watch(
  () => to.value,
  () => {
    inputTo.value = to.value;
    synchronizeToPicker();
  }
);

function refresh() {
  emit("refresh");
}

function applyTimeRange() {
  rawFrom.value = inputFrom.value;
  rawTo.value = inputTo.value;
  setFromTo(rawFrom.value, rawTo.value);
  menu.value = false;
}

function cancelPicker() {
  synchronizeFromPicker();
  synchronizeToPicker();
  fromDialog.value = false;
  toDialog.value = false;
}

function applyPickerFromDate() {
  inputFrom.value = toISO(pickerFrom.value);
  fromDialog.value = false;
}

function applyPickerToDate() {
  inputTo.value = toISO(pickerTo.value);
  toDialog.value = false;
}

function synchronizeFromPicker() {
  pickerFrom.value = dateMath.parse(from.value).toDate();
}

function synchronizeToPicker() {
  pickerTo.value = dateMath.parse(to.value, true).toDate();
}

function zoomOut() {
  const from_ = dateMath.parse(from.value);
  const to_ = dateMath.parse(to.value);
  const diff = to_ - from_;
  const newFrom = toISO(new Date(from_.toDate().getTime() - diff / 2));
  const newTo = toISO(new Date(to_.toDate().getTime() + diff / 2));
  setFromTo(newFrom, newTo);
}
</script>
