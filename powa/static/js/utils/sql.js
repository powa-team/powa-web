import hljs from "highlight.js/lib/core";
import pgsql from "highlight.js/lib/languages/pgsql";
import "highlight.js/styles/default.css";
import * as sqlFormatter from "sql-formatter";

hljs.registerLanguage("sql", pgsql);

export function formatSql(value) {
  value = sqlFormatter.format(value, { language: "postgresql" });
  return hljs.highlightAuto(value, ["sql"]).value;
}
