import { DateTime } from "luxon";

function toISO(date) {
  if (!(date instanceof DateTime)) {
    date = DateTime.fromJSDate(date);
  }
  return date.startOf("minute").toISO({ suppressSeconds: true });
}

export { toISO };
