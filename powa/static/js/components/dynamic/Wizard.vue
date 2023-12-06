<template>
  <v-card>
    <v-progress-linear
      :value="progress"
      height="2"
      style="position: absolute; z-index: 1"
    ></v-progress-linear>
    <v-app-bar flat height="40px;">
      <v-toolbar-title>
        <v-card-title class="pl-0">{{ config.title }}</v-card-title>
      </v-toolbar-title>
    </v-app-bar>
    <v-card-text>
      <v-row>
        <v-col>
          <div v-if="!config.has_remote_conn">
            Impossible to suggest indexes: impossible to connect to the remote
            database.
            <br />
            <b>{{ config.conn_error }}</b>
          </div>

          <div v-else-if="!config.has_qualstats">
            Impossible to suggest indexes: please enable support for
            pg_qualstats in powa or update pg_qualstats extension to a newer
            version. See
            <a href="http://powa.readthedocs.io">
              the documentation for more information
            </a>
          </div>
          <div v-else>
            <v-btn color="primary" class="mr-4" @click="optimize">
              Optimize this database !
            </v-btn>
            <span>{{ progressLabel }}</span>
          </div>
        </v-col>
      </v-row>

      <template v-if="optimized">
        <v-row>
          <v-col>
            <v-data-table
              v-if="unoptimizableItems"
              :headers="unoptimizableHeaders"
              :items="unoptimizableItems"
              :dense="true"
              class="superdense elevation-1"
              no-data-text="All quals could be optimized."
              hide-default-footer
              disable-pagination
            >
              <template #item.quals="{ item }">
                <div v-html="qualRepr(item)" />
              </template>
            </v-data-table>
          </v-col>
        </v-row>
        <v-row>
          <v-col>
            <v-data-table
              v-if="indexItems"
              :headers="indexHeaders"
              :items="indexItems"
              :dense="true"
              class="superdense elevation-1"
              no-data-text="No qual to optimize !"
              hide-default-footer
              disable-pagination
            >
              <template #item.ddl="{ item }">
                <query-tooltip :value="indexDdl(item)"></query-tooltip>
              </template>
              <template #item.quals="{ item }">
                <div v-html="qualRepr(item.node)" />
              </template>
              <template #item.nbqueries="{ item }">
                {{ item.queryids.length }}
              </template>
            </v-data-table>
          </v-col>
        </v-row>
        <v-row>
          <v-col>
            <v-data-table
              v-if="indexCheckErrorItems"
              :headers="indexCheckErrorHeaders"
              :items="indexCheckErrorItems"
              :dense="true"
              class="superdense elevation-1"
              no-data-text="No hypothetical index creation error."
              hide-default-footer
              disable-pagination
            >
              <template #item.ddl="{ item }">
                <query-tooltip :value="item.ddl"></query-tooltip>
              </template>
            </v-data-table>
          </v-col>
        </v-row>
        <v-row>
          <v-col>
            <v-data-table
              v-if="indexCheckItems"
              :headers="indexCheckHeaders"
              :items="indexCheckItems"
              :dense="true"
              class="superdense elevation-1"
              no-data-text="No index validation done."
              hide-default-footer
              disable-pagination
            >
              <template #item.query="{ item }">
                <query-tooltip :value="item.query"></query-tooltip>
              </template>
              <template #item.used="{ item }">
                <b v-if="item.gain > 0" class="green--text">✓</b>
              </template>
              <template #item.gain="{ item }"> {{ item.gain }}% </template>
            </v-data-table>
          </v-col>
        </v-row>
      </template>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { nextTick, ref } from "vue";
import store from "@/store";
import * as d3 from "d3";
import { encodeQueryData } from "@/utils/query";
import _ from "lodash";
import QueryTooltip from "@/components/QueryTooltip.vue";
import { formatSql } from "@/utils/sql";

// eslint-disable-next-line no-unused-vars
const props = defineProps({
  config: {
    type: Object,
    default() {
      return {};
    },
  },
});
const sourceConfig = store.dataSources[props.config.type];

const optimized = ref(false);
const progressLabel = ref("");
const progress = ref(0);

const indexHeaders = ref([
  {
    value: "ddl",
    text: "Index",
    cellClass: "query",
  },
  {
    value: "quals",
    text: "Used by",
    cellClass: "query",
  },
  {
    value: "nbqueries",
    text: "# Queries boosted",
    align: "right",
  },
]);
const indexItems = ref([]);

const indexCheckErrorHeaders = ref([
  {
    value: "ddl",
    text: "Hypothetical index creation error",
    cellClass: "query",
  },
  {
    value: "error",
    text: "Reason",
  },
]);
const indexCheckErrorItems = ref([]);

const indexCheckHeaders = ref([
  {
    value: "query",
    text: "Query",
    cellClass: "query",
  },
  {
    value: "used",
    text: "Index used",
    align: "center",
  },
  {
    value: "gain",
    text: "Gain",
    align: "right",
  },
]);
const indexCheckItems = ref([]);

const unoptimizableHeaders = ref([
  {
    value: "quals",
    text: "Unoptimized quals",
  },
]);
const unoptimizableItems = ref([]);

async function optimize() {
  indexItems.value = [];
  indexCheckItems.value = [];
  indexCheckErrorItems.value = [];
  unoptimizableItems.value = [];
  await updateProgress("Fetching most executed quals…", 0);
  const params = {
    from: store.from.format("YYYY-MM-DD HH:mm:ssZZ"),
    to: store.to.format("YYYY-MM-DD HH:mm:ssZZ"),
  };
  d3.json(sourceConfig.data_url + "?" + encodeQueryData(params)).then(
    async (response) => {
      dataLoaded(response.data, params.from, params.to);
    }
  );
}

async function dataLoaded(quals, from_date, to_date) {
  const total_quals = _.size(quals);
  if (total_quals == 0) {
    await updateProgress("No quals require optimization!", 100);
    optimized.value = true;
    return;
  } else {
    await updateProgress(`Building nodes for ${total_quals} quals…`, 0);
  }
  const nodes = [];
  let index = 1;
  for (const qual of quals) {
    const node = {
      label: qual.where_clause,
      type: "qual",
      quals: qual.quals,
      from_date: from_date,
      to_date: to_date,
      queries: qual.queries,
      queryids: qual.queryids,
      relid: qual.relid,
      relname: qual.relname,
      nspname: qual.nspname,
      links: {},
      id: qual.qualid,
      contained: [],
      trashedQuals: [],
    };

    qualUpdate(node);

    // If we already found a node with the same qualid, we simply need to
    // merge it with the new nodes, otherwise add it to the list.
    const existing = _.find(nodes, (n) => n.id == node.id);
    if (existing) {
      mergeNodes(existing, node);
    } else {
      nodes.push(node);
    }

    await updateProgress(
      `Building nodes for qual ${index} out of ${total_quals} quals…`,
      (10 + (10 * index) / total_quals).toFixed(2)
    );
    index++;
  }
  const result = await computeLinks(nodes);
  unoptimizableItems.value = result[1];
  await solve(result[0]);
  await checkSolution();
  optimized.value = true;
}

/* Compute the links between quals.
 *
 * Two types of links are considered:
 *  - Almost-free links, where two predicates can be grouped together
 *  using a single index
 *  - Expensive links, where a new index has to be created.
 *
 */
async function computeLinks(nodes) {
  let nodesToTrash = [];
  let firstNode;
  for (let i = 0, nbNodes = nodes.length; i < nbNodes; i++) {
    firstNode = nodes[i];
    await updateProgress(
      `Building links for node ${i + 1} out of ${nbNodes}`,
      (20 + ((i + 1) / nbNodes) * 10).toFixed(2)
    );
    if (!firstNode.quals.some((qual) => _.keys(qual.amops).length > 0)) {
      nodesToTrash.push(firstNode);
      continue;
    }
    for (let j = 0; j < i; j++) {
      let secondNode = nodes[j];
      if (!secondNode.quals.some((qual) => _.keys(qual.amops).length > 0)) {
        nodesToTrash.push(secondNode);
        continue;
      }

      nodesToTrash = _.uniq(
        nodesToTrash.concat(makeLinks(firstNode, secondNode))
      );
    }
  }
  _.each(nodes, function (nodeSource) {
    nodeSource.contained = _.difference(nodeSource.contained, nodesToTrash);
  });
  return [_.difference(nodes, nodesToTrash), nodesToTrash];
}

function makeLinks(node1, node2) {
  // according to the (relid,attnum,opno) tuple.
  // This is basically a merge-join.
  let idx1 = 0;
  let idx2 = 0;
  const attrs1 = {};
  const attrs2 = {};
  const missing1 = [];
  const missing2 = [];
  const l1 = _.uniqBy(node1.quals, (q) => [q.attnum, q.relid].join("."));
  const l2 = _.uniqBy(node2.quals, (q) => [q.attnum, q.relid].join("."));
  if (node1.relid != node2.relid) {
    return [];
  }
  /* eslint no-constant-condition: ["error", { "checkLoops": false  }] */
  while (true) {
    if (idx1 >= l1.length || idx2 >= l2.length) {
      for (let i = idx1; i < l1.length; i++) {
        missing1.push(l1[i]);
      }

      for (let j = idx2; j < l2.length; j++) {
        missing2.push(l2[j]);
      }
      break;
    }
    const q1 = l1[idx1];
    const q2 = l2[idx2];
    const attrid1 = makeAttrid(q1);
    const attrid2 = makeAttrid(q2);
    if (attrs1[attrid1] === undefined) {
      attrs1[attrid1] = false;
    }
    if (attrs2[attrid2] === undefined) {
      attrs2[attrid2] = false;
    }
    let isOverlap = false;
    if (q1.relid == q2.relid && q1.attnum == q2.attnum) {
      const commonAms = _.filter(
        _.keys(q1.amops),
        (indexam) => q2.amops[indexam] != undefined
      );
      if (commonAms.length > 0) {
        isOverlap = true;
        attrs1[attrid1] = true;
        attrs2[attrid2] = true;
        idx1++;
        idx2++;
        continue;
      }
    }
    if (!isOverlap) {
      if (compareQuals(q1, q2) > 0) {
        missing2.push(q2);
        idx2++;
      } else {
        missing1.push(q1);
        idx1++;
      }
    }
  }

  if (missing1.length == 0 && missing2.length == 0) {
    mergeNodes(node1, node2);
    return [node2];
  }
  if (missing2.length == 0) {
    node1.contained.push(node2);
  }
  if (missing1.length == 0) {
    node2.contained.push(node1);
  }
  return [];
}

function makeAttrid(qual) {
  return `${qual.relid}/${qual.attnum}`;
}

function compareQuals(qual1, qual2) {
  if (qual1.relid != qual2.relid) {
    return qual1.relid - qual2.relid;
  }
  if (qual1.attnum != qual2.attnum) {
    return qual1.attnum - qual2.attnum;
  }
  if (qual1.opno != qual2.opno) {
    return qual1.opno - qual2.opno;
  }
  return 0;
}

async function solve(nodes) {
  let remainingNodes = nodes;
  const pathes = {};
  const makePathId = (nodes) => {
    return nodes.map((node) => node.id).join(",");
  };
  function getPathes(node) {
    const mypath = {
      id: node.id,
      score: node.score,
      nodes: [node],
    };
    const pathes = [];
    _.each(node.contained, (contained) => {
      _.each(getPathes(contained), (path) => {
        const currentPath = _.clone(path.nodes);
        currentPath.push(node);
        pathes.push({
          nodes: currentPath,
          id: makePathId(currentPath),
          score: scorePath(nodes),
        });
      });
    });
    pathes.push(mypath);
    return pathes;
  }

  // Compute score for each node.
  _.each(remainingNodes, function (node) {
    node.score = scoreNode(node);
  });

  const nbNodes = nodes.length;
  let idx = 1;
  // use for (x of xs) here to make sure await works
  for (const node of remainingNodes) {
    await updateProgress(
      `Building pathes for node ${idx} out of ${nbNodes} nodes…`,
      30 + 10 * (idx / nbNodes).toFixed(2)
    );

    _.each(getPathes(node), function (path) {
      pathes[path.id] = path;
    });
    idx++;
  }
  let safeguard = 0;
  let nbOptimized = 0;
  const nbPathes = _.keys(pathes).length;
  while (_.values(pathes).length > 0 && safeguard < 10000) {
    safeguard++;
    /* Work with the remainging highest-scoring path */
    const firstPath = _.maxBy(_.toPairs(pathes), (pair) => pair[1].score)[1];
    /* Find attnum order */
    let attnums = [];
    let queryids = [];
    await updateProgress(
      `Optimizing ${nbOptimized} out of ${nbPathes} pathes…`,
      40 + 20 * (nbOptimized / nbPathes).toFixed(2)
    );

    // use for (x of xs) here to make sure await works
    for (const node of firstPath.nodes) {
      const nodeAttnum = node.quals.map((qual) => qual.attnum);
      const newAttnums = _.difference(nodeAttnum, attnums);
      attnums = attnums.concat(newAttnums);
      for (const pair of _.toPairs(pathes)) {
        const pathid = pair[0];
        const path = pair[1];
        if (_.some(path.nodes, (n) => n == node)) {
          const pathToDel = pathes[pathid];
          nbOptimized++;
          if (pathToDel) {
            await updateProgress(
              `Optimizing ${nbOptimized} out of ${nbPathes} pathes…`,
              40 + 20 * (nbOptimized / nbPathes).toFixed(2)
            );
          }
          delete pathes[pathid];
        }
      }
      queryids = _.uniq(queryids.concat(node.queryids));
    }
    const ams = _.uniq(
      _.flatten(
        firstPath.nodes.slice(-1)[0].quals.map((qual) => _.keys(qual.amops))
      )
    );
    indexItems.value.push({
      node: firstPath.nodes.slice(-1)[0],
      path: firstPath.nodes,
      attnums: attnums,
      queryids: queryids,
      ams: ams,
      stub: true,
    });
  }
}
function scoreNode(node) {
  return _.uniq(node.quals.map((qual) => qual.attnum)).length;
}

function scorePath(nodes) {
  return _.reduce(nodes, (memo, node) => memo + node.score, 0);
}

function indexDdl(index) {
  let am = index.ams[0];
  if (index.ams.indexOf("btree") > 0) {
    // Propose btree when possible
    am = "";
  } else {
    am = "USING " + am;
  }
  const myattnums = index.attnums;
  const attnames = _.uniq(
    _.map(
      _.sortBy(
        index.node.quals.map((qual) => {
          const attnum = qual.attnum;
          const attname = qual.attname;
          return [myattnums.indexOf(attnum), attname];
        }),
        (pair) => pair[0]
      ),
      (pair) => pair[1]
    )
  );
  return `CREATE INDEX ON ${relfqn(index.node)} ${am} (${attnames.join(",")})`;
}

function qualRepr(node) {
  let base = "WHERE ";
  const hasquals = node.quals.length > 0;
  if (hasquals) {
    base += _.uniq(node.quals.map((qual) => qual.label)).join(" AND ");
  }
  base = formatSql(base);
  const unmanaged = node.trashedQuals
    .map(function (qual, idx) {
      let part = "<strike>";
      let value = qual.label;
      if (idx == 0 && hasquals) {
        value = " AND " + value;
      }
      if (idx < node.trashedQuals.length - 1) {
        value += " AND ";
      }
      value = formatSql("WHERE " + value);
      value = value.substring(value.indexOf("</span> ") + 8);
      part += value + "</strike>";
      return part;
    }, node)
    .join(" AND ");
  base = "<pre class='sql'><code>• " + base + unmanaged + "</code></pre>";
  base = base + node.contained.map((node) => qualRepr(node)).join("");
  return base;
}

function relfqn(node) {
  return [node.nspname, node.relname].join(".");
}

function qualUpdate(node) {
  const relids = _.uniq(node.quals.map((node) => node.relid));
  if (relids.length > 1) {
    throw "A qual should not span more than one table";
  }
  node.relid = relids[0];
  node.relname = node.quals[0].relname;
  trashQuals(node);
}

function trashQuals(node) {
  // Delete quals which do not support the most common access
  // method.
  const quals = node.quals;
  const accessMethods = {};
  _.each(quals, (qual) => {
    _.each(_.keys(qual.amops), (am) => {
      accessMethods[am] = (accessMethods[am] || 0) + 1;
    });
  });
  const maxCommonAm = _.maxBy(_.toPairs(accessMethods), (pair) => pair[1]);
  // In some cases, a predicate contains an operator that is not optimizable by
  // any access method
  const mostCommonAm = maxCommonAm ? maxCommonAm[0] : "";
  const grouped = _.groupBy(quals, (qual) =>
    qual.amops[mostCommonAm] ? "keep" : "trash"
  );
  node.trashedQuals = grouped.trash || [];
  node.quals = grouped.keep || [];
}

function mergeNodes(node1, node2) {
  node1.queries = _.uniq(node1.queries.concat(node2.queries));
  node1.queryids = _.uniq(node1.queryids.concat(node2.queryids));
  const quals = _.union(node1.quals, node2.quals);
  node1.quals = quals;
  qualUpdate(node1);
}

async function checkSolution() {
  if (!props.config.has_hypopg) {
    await updateProgress("Install hypopg for solution validation", 100);
    return;
  }

  if (indexItems.value.length == 0) {
    await updateProgress("No indexes to suggest!", 100);
    return;
  }
  await updateProgress("Checking solution with hypopg...", 60);
  const indexes = [];
  let queryids = [];
  _.each(indexItems.value, (index) => {
    const node = _.clone(index.node);
    node.ams = index.ams;
    node.ddl = indexDdl(index);
    if (node.ams.length > 0) {
      indexes.push(node);
    }
    queryids = _.uniq(queryids.concat(index.queryids));
  });
  const params = {
    from: store.from.format("YYYY-MM-DD HH:mm:ssZZ"),
    to: store.to.format("YYYY-MM-DD HH:mm:ssZZ"),
  };
  d3.json(
    `/server/${props.config.server}/database/${props.config.database}/suggest/`,
    {
      method: "POST",
      body: JSON.stringify({
        queryids: queryids,
        indexes: indexes,
        from_date: params.from,
        to_date: params.to,
      }),
      headers: {
        "Content-type": "application/json; charset=UTF-8",
      },
    }
  ).then(async (data) => {
    indexCheckErrorItems.value = _.map(data.inderrors, (err, ddl) => {
      return {
        ddl: ddl,
        error: err,
      };
    });
    indexCheckItems.value = _.map(data.plans, (stat) => {
      return {
        query: stat.query,
        gain: stat.gain_percent,
      };
    });
    await updateProgress("Done!", 100);
  });
}

async function updateProgress(text, value) {
  progressLabel.value = text;
  progress.value = value;
  await nextTick();
}
</script>
