import hljs from "highlight.js/lib/core";
import pgsql from "highlight.js/lib/languages/pgsql";
import "highlight.js/styles/default.css";

hljs.registerLanguage("sql", pgsql);

export function formatSql(value) {
  return hljs.highlightAuto(value, ["sql"]).value;
}
