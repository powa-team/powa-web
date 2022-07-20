import * as d3 from "d3";

function formatPercentage(value) {
  return d3.format(".2%")(value / 100);
}

export { formatPercentage };
