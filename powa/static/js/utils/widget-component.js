export function widgetComponent(widget) {
  if (widget.type === "content") {
    // we cannot use <content> reserved HTML tag
    return "content-cmp";
  }
  if (widget.type == "grid" && widget.renderer == "distribution") {
    return "distribution-grid";
  }
  return widget.type;
}
