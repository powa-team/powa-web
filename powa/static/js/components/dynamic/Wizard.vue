<template>
  <h3 class="mb-3">
    <v-icon :icon="mdiAutoFix" size="24" />{{ config.title }}
  </h3>
  <v-row>
    <v-col>
      <div v-if="!config.has_remote_conn">
        Impossible to suggest indexes: impossible to connect to the remote
        database.
        <br />
        <b>{{ config.conn_error }}</b>
      </div>

      <div v-else-if="!config.has_qualstats">
        Impossible to suggest indexes: please enable support for pg_qualstats in
        powa or update pg_qualstats extension to a newer version. See
        <a href="http://powa.readthedocs.io">
          the documentation for more information
        </a>
      </div>
      <v-row v-if="optimized || optimizing">
        <v-col>
          <div class="d-inline-block">
            <div v-for="step in progressSteps" :key="step">
              <v-icon
                v-if="step.working"
                :icon="mdiLoading"
                class="text-warning spin"
              />
              <v-icon
                v-else-if="step.error"
                :icon="mdiAlertCircle"
                class="text-warning"
              />
              <v-icon v-else :icon="mdiCheck" class="text-success" />
              {{ step.title }}
              <span
                v-if="step.message"
                :class="step.error ? 'text-warning' : 'text-disabled'"
                >{{ step.message }}</span
              >
            </div>
          </div>
        </v-col>
        <v-col v-if="optimized">
          <v-row v-if="!unoptimizableItems && !indexItems"
            ><v-col
              ><v-alert
                color="success"
                :icon="mdiPartyPopper"
                variant="tonal"
                density="compact"
                title="Yay!"
              >
                No qual require optimization!
              </v-alert>
            </v-col>
          </v-row>
          <v-row v-if="unoptimizableItems && unoptimizableItems.length == 0"
            ><v-col
              ><v-alert
                color="success"
                icon="$success"
                variant="tonal"
                density="compact"
              >
                All quals are optimizable
              </v-alert>
            </v-col>
          </v-row>
          <v-row
            v-if="indexItems && indexItems.length && !props.config.has_hypopg"
            ><v-col
              ><v-alert
                color="warning"
                icon="$warning"
                variant="tonal"
                density="compact"
              >
                No index suggestion validation can be performed because
                <b>HypoPG is not installed</b>.
              </v-alert>
            </v-col>
          </v-row>
        </v-col>
      </v-row>
    </v-col>
  </v-row>

  <template v-if="optimized">
    <v-row v-if="indexItems">
      <v-col>
        <v-badge
          location="right center"
          :offset-x="-20"
          :content="indexItems.length"
          color="success"
        >
          <h3>Suggested Indexes</h3>
        </v-badge>
        <v-card
          v-for="item in indexItems"
          :key="item"
          border
          rounded
          elevation="3"
          class="mb-6"
        >
          <v-card-item class="bg-surface-light mb-4">
            <v-card-title class="d-flex">
              <pre class="sql"><code v-html="formatSql(indexDdl(item))" /></pre>
              <v-tooltip
                content-class="sql elevation-2"
                transition="fade"
                open-delay="200"
                location="bottom"
              >
                <template #activator="{ props: activatorProps }">
                  <copy
                    :content="indexDdl(item)"
                    class="text-medium-emphasis ml-6"
                    variant="text"
                    size="x-small"
                    density="compact"
                    v-bind="activatorProps"
                  />
                </template>
                Copy
              </v-tooltip>
            </v-card-title>
          </v-card-item>
          <v-card-text>
            <div class="text-medium-emphasis">
              <v-icon :icon="mdiCheck" class="text-success mr-2"></v-icon>
              <b>{{ 1 + item.node.contained.length }}</b> predicates that would
              use this index
            </div>
            <div class="text-body-2 ml-6 mt-2" v-html="qualRepr(item.node)" />
            <v-divider class="my-6" thickness="2"></v-divider>
            <div class="text-medium-emphasis">
              <v-icon :icon="mdiCheck" class="text-success mr-2"></v-icon
              ><b>{{ Object.keys(item.queries).length }}</b> queries would
              benefit from this index
            </div>
            <v-list class="ml-6">
              <template
                v-for="([key, query], index) in Object.entries(item.queries)"
                :key="query"
              >
                <v-list-item class="pl-0">
                  <v-row>
                    <v-col cols="5">
                      <span class="text-medium-emphasis">Normalized:</span>
                      <div
                        class="nowrap text-body-2 overflow-auto pa-2 mb-2 rounded border"
                        style="max-height: 100px; max-width: 100%"
                      >
                        <pre
                          class="sql"
                        ><code v-html="formatSql(query.query)" /></pre>
                      </div>
                    </v-col>
                    <v-col
                      v-if="checking"
                      class="d-flex justify-center align-center"
                    >
                      <v-icon
                        :icon="mdiLoading"
                        class="text-warning spin mr-3"
                      />
                      Checking solution wih HypoPG
                    </v-col>
                    <v-col
                      v-else-if="!props.config.has_hypopg"
                      class="text-medium-emphasis text-warning text-center align-self-center"
                    >
                      Could not check solution.
                      <br />
                      <b>HypoPG is not installed</b>.
                    </v-col>
                    <template
                      v-else-if="indexCheckItems && indexCheckItems[key]"
                    >
                      <v-col cols="5">
                        <span class="text-medium-emphasis">With values:</span>
                        <div
                          class="nowrap text-body-2 overflow-auto border pa-2 rounded"
                          style="max-height: 100px; max-width: 100%"
                        >
                          <pre
                            class="sql"
                          ><code v-html="formatSql(indexCheckItems[key].query)" /></pre>
                        </div>
                      </v-col>
                      <v-col class="align-self-center">
                        <template
                          v-if="indexCheckItems && indexCheckItems[key]"
                        >
                          <span class="text-medium-emphasis"
                            >Estimated gain for this query:
                          </span>
                          <b>{{ indexCheckItems[key].gain_percent }}%</b>
                        </template>
                      </v-col>
                    </template>
                    <v-col
                      v-else-if="
                        indexCheckErrors && indexCheckErrors[indexDdl(item)]
                      "
                      class="d-flex justify-center align-center"
                    >
                      <span class="text-error"
                        >An error happened while checking solution with HypoPG:
                        <br />
                        <b>{{ indexCheckErrors[indexDdl(item)] }}</b>
                      </span>
                    </v-col>
                  </v-row>
                  <router-link
                    :key="query"
                    :to="getUrl(query.url)"
                    exact-match
                    class="text-decoration-none text-primary"
                  >
                    More details about this query
                    <v-icon :icon="mdiArrowRight" size="1em"></v-icon>
                  </router-link>
                </v-list-item>
                <v-divider
                  v-if="index < Object.keys(item.queries).length - 1"
                  class="my-3"
                />
              </template>
            </v-list>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
    <v-row v-if="unoptimizableItems && unoptimizableItems.length > 0">
      <v-col>
        <v-badge
          location="right center"
          :offset-x="-20"
          :content="unoptimizableItems.length"
          color="warning"
        >
          <h3>Unoptimized Quals</h3>
        </v-badge>
        <div class="mb-4 text-medium-emphasis">
          <span class="text-decoration-line-through">xxxxx</span>: does not
          support common access method
        </div>
        <v-card
          v-for="item in unoptimizableItems"
          :key="item"
          border
          rounded
          elevation="3"
          class="mb-6"
        >
          <v-card-item class="bg-surface-light mb-4">
            <v-card-title>
              <div v-html="qualRepr(item)" />
            </v-card-title>
          </v-card-item>
          <v-card-text>
            <div class="text-medium-emphasis">
              Used in <b>{{ Object.keys(item.queries).length }}</b> queries
            </div>
            <v-list class="ml-6">
              <template
                v-for="([, query], index) in Object.entries(item.queries)"
                :key="query"
              >
                <v-list-item class="pl-0">
                  <v-row>
                    <v-col>
                      <div
                        class="nowrap text-body-2 overflow-auto pa-2 mb-2 rounded border"
                        style="max-height: 100px; max-width: 100%"
                      >
                        <pre
                          class="sql"
                        ><code v-html="formatSql(query.query)" /></pre>
                      </div>
                    </v-col>
                  </v-row>
                  <router-link
                    :key="query"
                    :to="getUrl(query.url)"
                    exact-match
                    class="text-decoration-none text-primary"
                  >
                    More details about this query
                    <v-icon :icon="mdiArrowRight" size="1em"></v-icon>
                  </router-link>
                </v-list-item>
                <v-divider
                  v-if="index < Object.keys(item.queries).length - 1"
                  class="my-3"
                />
              </template>
            </v-list>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </template>
</template>

<script setup>
import { onMounted, ref, watch } from "vue";
import { storeToRefs } from "pinia";
import * as d3 from "d3";
import _ from "lodash";
import Copy from "@/components/Copy.vue";
import { formatSql } from "@/utils/sql";
import { useDateRangeStore } from "@/stores/dateRange.js";
import { useDataLoader } from "@/composables/DataLoaderService.js";
import {
  mdiAlertCircle,
  mdiArrowRight,
  mdiAutoFix,
  mdiCheck,
  mdiLoading,
  mdiPartyPopper,
} from "@mdi/js";

// eslint-disable-next-line no-unused-vars
const props = defineProps({
  config: {
    type: Object,
    default() {
      return {};
    },
  },
});
// The data source for the given chart
const { source } = useDataLoader(props.config.type);
const { from, to, urlSearchParams } = storeToRefs(useDateRangeStore());
const { getUrl } = useDateRangeStore();

const optimized = ref(false);
const optimizing = ref(false);
const checking = ref(false);
const progressSteps = ref([]);
const progress = ref(0);

const indexItems = ref(null);

// Suggestions validated by HypoPG
const indexCheckItems = ref(null);
const indexCheckErrors = ref(null);

const unoptimizableItems = ref(null);

watch(() => [from.value, to.value], optimize);

function optimize() {
  progressSteps.value = [];
  optimizing.value = true;
  checking.value = true;
  indexItems.value = [];
  indexCheckItems.value = null;
  indexCheckErrors.value = null;
  unoptimizableItems.value = null;
  indexItems.value = null;
  addProgressStep("Fetching most executed quals");
  d3.json(`${source.value.config.data_url}?${urlSearchParams.value}`).then(
    async (response) => {
      dataLoaded(
        response.data,
        urlSearchParams.value.from,
        urlSearchParams.value.to
      );
    }
  );
}

onMounted(optimize);

async function dataLoaded(quals, from_date, to_date) {
  const total_quals = _.size(quals);
  if (total_quals == 0) {
    await endProgressStep("No qual require optimization!");
    progress.value = 100;
    optimized.value = true;
    return;
  } else {
    await endProgressStep(`(${total_quals})`);
    addProgressStep(`Building nodes`);
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

    (progress.value = (10 + (10 * index) / total_quals).toFixed(2)), index++;
  }
  await endProgressStep(`(${nodes.length})`);
  addProgressStep(`Building links`);
  const result = await computeLinks(nodes);
  await endProgressStep(`(${result[0].length})`);
  unoptimizableItems.value = result[1];
  await solve(result[0]);
  optimized.value = true;
  await checkSolution();
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
    progress.value = (20 + ((i + 1) / nbNodes) * 10).toFixed(2);
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

      nodesToTrash = nodesToTrash.concat(makeLinks(firstNode, secondNode));
    }
  }
  nodesToTrash = _.uniqWith(nodesToTrash, _.isEqual);
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
  const paths = {};
  const makePathId = (nodes) => {
    return nodes.map((node) => node.id).join(",");
  };
  function getPaths(node) {
    const mypath = {
      id: node.id,
      score: node.score,
      nodes: [node],
    };
    const paths = [];
    _.each(node.contained, (contained) => {
      _.each(getPaths(contained), (path) => {
        const currentPath = _.clone(path.nodes);
        currentPath.push(node);
        paths.push({
          nodes: currentPath,
          id: makePathId(currentPath),
          score: scorePath(nodes),
        });
      });
    });
    paths.push(mypath);
    return paths;
  }

  // Compute score for each node.
  _.each(remainingNodes, function (node) {
    node.score = scoreNode(node);
  });

  const nbNodes = nodes.length;
  let idx = 1;
  addProgressStep(`Building paths`);
  // use for (x of xs) here to make sure await works
  for (const node of remainingNodes) {
    progress.value = 30 + 10 * (idx / nbNodes).toFixed(2);

    _.each(getPaths(node), function (path) {
      paths[path.id] = path;
    });
    idx++;
  }
  let safeguard = 0;
  const nbPaths = _.keys(paths).length;
  await endProgressStep(`(${nbPaths})`);
  idx = 1;
  addProgressStep(`Optimizing paths`);
  indexItems.value = [];
  while (_.values(paths).length > 0 && safeguard < 10000) {
    safeguard++;
    /* Work with the remainging highest-scoring path */
    const firstPath = _.maxBy(_.toPairs(paths), (pair) => pair[1].score)[1];
    /* Find attnum order */
    let attnums = [];
    let queries = {};

    // use for (x of xs) here to make sure await works
    for (const node of firstPath.nodes) {
      const nodeAttnum = node.quals.map((qual) => qual.attnum);
      const newAttnums = _.difference(nodeAttnum, attnums);
      attnums = attnums.concat(newAttnums);
      for (const pair of _.toPairs(paths)) {
        const pathid = pair[0];
        const path = pair[1];
        if (_.some(path.nodes, (n) => n == node)) {
          progress.value = 40 + 20 * (idx / nbPaths).toFixed(2);
          idx++;
          delete paths[pathid];
        }
      }
      queries = Object.assign(queries, node.queries);
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
      queries: queries,
      ams: ams,
      stub: true,
    });
  }
  await endProgressStep();
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
  return `CREATE INDEX ON ${relfqn(index.node)} ${am} (${attnames.join(",")});`;
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
      let part = "<span class='text-decoration-line-through'>";
      let value = qual.label;
      if (idx == 0 && hasquals) {
        value = " AND " + value;
      }
      value = formatSql(value);
      part += value + "</span>";
      return part;
    }, node)
    .join("<span class='hljs-keyword'> AND </span>");
  base = "<pre class='sql'><code>• " + base + " " + unmanaged + "</code></pre>";
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
  node1.queries = Object.assign(node1.queries, node2.queries);
  const quals = _.unionWith(node1.quals, node2.quals, _.isEqual);
  node1.quals = quals;
  qualUpdate(node1);
}

async function checkSolution() {
  addProgressStep("Checking solution with hypopg");
  checking.value = true;
  if (!props.config.has_hypopg) {
    await endProgressStep("Hypopg is not installed", true);
    checking.value = false;
    progress.value = 100;
    return;
  }

  if (indexItems.value.length == 0) {
    await endProgressStep({
      message: "No index to suggest!",
    });
    progress.value = 100;
    return;
  }
  const indexes = [];
  let queryids = [];
  _.each(indexItems.value, (index) => {
    const node = _.clone(index.node);
    node.ams = index.ams;
    node.ddl = indexDdl(index);
    if (node.ams.length > 0) {
      indexes.push(node);
    }
    queryids = _.uniq(queryids.concat(Object.keys(index.queries)));
  });
  const params = {
    from: from.value.format("YYYY-MM-DD HH:mm:ssZZ"),
    to: to.value.format("YYYY-MM-DD HH:mm:ssZZ"),
  };
  d3.json(
    `${props.config.url_prefix}server/${props.config.server}/database/${props.config.database}/suggest/`,
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
    checking.value = false;
    indexCheckItems.value = data.plans;
    indexCheckErrors.value = data.inderrors;
    await endProgressStep();
    progress.value = 100;
  });
}

async function addProgressStep(text) {
  progressSteps.value.push({
    title: text,
    working: true,
  });
}

async function endProgressStep(message, error = false) {
  const currentStep = progressSteps.value.at(-1);
  await new Promise((r) => setTimeout(r, 100));
  currentStep.message = message;
  currentStep.error = error;
  currentStep.working = false;
}

function getCellProps(data) {
  return { class: data.column.cellClass };
}
</script>

<style scoped>
.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
