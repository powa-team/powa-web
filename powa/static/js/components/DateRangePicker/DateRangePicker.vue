<template>
  <div v-click-outside="clickOutside" style="position: relative">
    <v-btn @click="isShown = true">
      <i class="fa fa-clock-o mr-2"></i>
      <span>{{ rangeString }}</span>
    </v-btn>
    <div
      v-show="isShown"
      style="
        position: absolute;
        width: 500px;
        height: 350px;
        right: 0;
        top: 116%;
      "
    >
      <v-card style="height: 100%">
        <v-card-text style="height: 100%" class="pa-0">
          <v-row style="height: 100%; overflow: hidden" no-gutters>
            <v-col
              cols="12"
              sm="7"
              class="pa-6"
              style="border-right: 1px solid #dfdfdf"
            >
              <v-form ref="form" v-model="valid">
                <b>Absolute time range</b>
                <br />
                <br />
                From
                <br />
                <v-btn
                  small
                  elevation="0"
                  class="d-inline-block mr-2"
                  style="min-width: 0"
                  @click.stop="dialog = true"
                >
                  <i class="fa fa-calendar"></i>
                </v-btn>
                <v-text-field
                  v-model="inputFrom"
                  :rules="fromRules"
                  class="pt-0 d-inline-block"
                ></v-text-field>
                <br />
                To
                <br />
                <v-btn
                  small
                  elevation="0"
                  class="d-inline-block mr-2"
                  style="min-width: 0"
                  @click.stop="dialog = true"
                >
                  <i class="fa fa-calendar"></i>
                </v-btn>
                <v-text-field
                  v-model="inputTo"
                  :rules="toRules"
                  class="pt-0 d-inline-block"
                ></v-text-field>
                <v-btn
                  color="primary"
                  class="mb-4"
                  :disabled="!valid"
                  @click="applyTimeRange"
                  >Apply time range</v-btn
                >
              </v-form>
            </v-col>
            <v-col
              cols="12"
              sm="5"
              class="d-flex flex-column"
              style="height: 100%"
            >
              <v-list dense class="flex-grow-1" style="overflow: auto">
                <v-list-item
                  v-for="(range, index) in quickOptions"
                  :key="index"
                  link
                  @click.prevent="loadRangeShortcut(range)"
                >
                  <v-list-item-content>
                    {{ range.display }}
                  </v-list-item-content>
                </v-list-item>
              </v-list>
            </v-col>
          </v-row>
        </v-card-text>
      </v-card>
      <v-dialog v-model="dialog" width="290px" persistent>
        <v-date-picker
          v-model="pickerDates"
          range
          elevation="2"
          show-adjacent-months
        >
          <v-spacer></v-spacer>
          <v-btn text color="primary" @click="cancelPicker"> Cancel </v-btn>
          <v-btn
            text
            color="primary"
            :disabled="pickerDates[1] == null"
            @click="applyDatesFromPicker"
          >
            OK
          </v-btn>
        </v-date-picker>
      </v-dialog>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { quickOptions } from "./options.ts";
import { dateMath, rangeUtil } from "@grafana/data";
import { DateTime } from "luxon";
import store from "../../store";

// The raw values (examples: 'now-24h', 'Tue Sep 01 2020 10:16:00 GMT+0200')
// Interaction with parent component is done with from/to props which
// are unix timestamps
const rawFrom = ref(store.from);
const rawTo = ref(store.to);
// The values to display in the custom range from and to fields
// we don't use raw values because we may want to pick/change from and
// to in the form before applying changes
const inputFrom = ref(rawFrom.value);
const inputTo = ref(rawTo.value);

const dialog = ref(false);
const pickerDates = ref([]);

// whether or not the menu dropdown is shown
const isShown = ref(false);

const form = ref(null);
const valid = ref(true);

const rangeString = computed(() => {
  if (!rawFrom.value || !rawTo.value) {
    return;
  }
  return rangeUtil.describeTimeRange({ from: rawFrom.value, to: rawTo.value });
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
  rawFrom.value = shortcut.from;
  rawTo.value = shortcut.to;
  isShown.value = false;
}

watch(
  () => rawFrom.value + rawTo.value,
  () => {
    inputFrom.value = rawFrom.value;
    inputTo.value = rawTo.value;
    synchronizePicker();
    store.setFromTo(rawFrom.value, rawTo.value);
  }
);

watch(
  () => inputFrom.value + inputTo.value,
  () => {
    form.value.validate();
  }
);

function applyTimeRange() {
  isShown.value = false;
  rawFrom.value = inputFrom.value;
  rawTo.value = inputTo.value;
}

function cancelPicker() {
  synchronizePicker();
  // Close the dialog after update cycle to let the click outside happen first
  setTimeout(() => {
    dialog.value = false;
  }, 1);
}

function applyDatesFromPicker() {
  inputFrom.value = DateTime.fromFormat(
    pickerDates.value[0],
    "yyyy-LL-dd"
  ).toFormat("yyyy-LL-dd 00:00:00");
  inputTo.value = DateTime.fromFormat(
    pickerDates.value[1],
    "yyyy-LL-dd"
  ).toFormat("yyyy-LL-dd 23:59:00");
  // Close the dialog after update cycle to let the click outside happen first
  setTimeout(() => {
    dialog.value = false;
  }, 1);
}

function synchronizePicker() {
  pickerDates.value = [
    dateMath.parse(rawFrom.value).format("YYYY-MM-DD"),
    dateMath.parse(rawTo.value, true).format("YYYY-MM-DD"),
  ];
}

function clickOutside() {
  if (dialog.value) {
    return;
  }
  isShown.value = false;
}
</script>
