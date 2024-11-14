import hljs from "highlight.js/lib/core";
import pgsql from "highlight.js/lib/languages/pgsql";
import "highlight.js/styles/default.css";
import sqlFormatter from "@sqltools/formatter";

hljs.registerLanguage("sql", pgsql);

export function formatSql(value) {
  try {
    value = sqlFormatter.format(value, { language: "postgresql" });
  } catch (error) {
    console.error("Could not format SQL:", "\n", value, "\n", error);
  }
  value = hljs.highlightAuto(value, ["sql"]).value;
  return value;
}
