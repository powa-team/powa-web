import { nextTick, reactive } from "vue";
let messageId = 1;

let alertMessages = reactive([]);

function addAlertMessage(level, message) {
  const colors = {
    alert: "error",
    error: "error",
    warning: "warning",
    info: "info",
    success: "success",
  };
  let newId = ++messageId;
  alertMessages.push({
    id: newId,
    color: colors[level],
    message: message,
    shown: false,
  });
  nextTick(
    () =>
      (alertMessages[
        alertMessages.findIndex((n) => n.id == newId)
      ].shown = true)
  );
}

function addAlertMessages(messages) {
  for (let message in messages) {
    addAlertMessage(message.level, message.message);
  }
}
function removeAlertMessage(id) {
  // Remove message from list with delay to make sure transition is finished
  window.setTimeout(() => {
    alertMessages.splice(
      alertMessages.findIndex((n) => n.id == id),
      1
    );
  }, 500);
}

export function useMessageService() {
  return {
    alertMessages,
    addAlertMessage,
    addAlertMessages,
    removeAlertMessage,
  };
}
