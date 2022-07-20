export function widgetComponent(type) {
  if (type === "content") {
    // we cannot use <content> reserved HTML tag
    return "content-cmp";
  }
  return type;
}
