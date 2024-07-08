import hljs from "highlight.js/lib/core";
import pgsql from "highlight.js/lib/languages/pgsql";
import "highlight.js/styles/default.css";
import { formatDialect, postgresql } from "sql-formatter";

hljs.registerLanguage("sql", pgsql);

export function formatSql(value) {
  value = formatDialect(value, { dialect: postgresql });
  return hljs.highlightAuto(value, ["sql"]).value;
}
