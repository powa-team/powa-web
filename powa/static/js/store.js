import { nextTick, reactive } from "vue";
import _ from "lodash";

let messageId = 1;

const store = reactive({
  alertMessages: [],
  addAlertMessage(level, message) {
    const colors = {
      alert: "error",
      error: "error",
      warning: "warning",
      info: "info",
      success: "success",
    };
    this.alertMessages.push({
      id: ++messageId,
      color: colors[level],
      message: message,
      shown: false,
    });
    nextTick(() => (_.last(this.alertMessages).shown = true));
  },
  addAlertMessages(messages) {
    _.forEach(messages, function (value, key) {
      for (let message of value) {
        store.addAlertMessage(key, message);
      }
    });
  },
  removeAlertMessage(id) {
    // Remove message from list with delay to make sure transition is finished
    window.setTimeout(() => {
      _.remove(this.alertMessages, (n) => n.id == id);
      // workaround to force an update of components
      this.alertMessages = [].concat(this.alertMessages);
    }, 500);
  },
});

export default store;
