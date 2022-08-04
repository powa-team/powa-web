import $ from "jquery";

export function addMessage(level, message) {
  const content = `
    <div class="alert alert-${level} alert-dismissible fade show" role="alert">
      ${message}
      <button type="button" class="close" data-dismiss="alert" aria-label="Close">
        <span aria-hidden="true">&times;</span>
      </button>
    </div>`
  $("#messages").append(content);
}
