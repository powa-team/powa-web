"""
Utilities for commonly used SQL constructs.
"""

import re
import sys
from collections import defaultdict, namedtuple
from powa.json import JSONizable

TOTAL_MEASURE_INTERVAL = """
extract( epoch from
    CASE WHEN min(total_mesure_interval) = '0 second'
        THEN '1 second'::interval
    ELSE min(total_mesure_interval) END)
"""


def unprepare(sql):
    if sql.startswith("PREPARE"):
        sql = re.sub("PREPARE.*AS", "", sql)
    sql = re.sub("\$\d+", "?", sql)
    return sql


def format_jumbled_query(sql, params):
    sql = unprepare(sql)
    it = iter(params)
    try:
        sql = re.sub("\?", lambda val: next(it), sql)
    except StopIteration:
        pass
    return sql


RESOLVE_OPNAME = """
SELECT json_object_agg(oid, value)
    FROM (

    SELECT oproid as oid, json_build_object(
        'name', oprname,
        'amop',
        coalesce(
            json_object_agg(am, opclass_oids::jsonb
            ORDER BY am)
                      FILTER (WHERE am is NOT NULL)),
        'amop_names',
         coalesce(
            json_object_agg(
                      amname,
                      opclass_names ORDER BY am)
                      FILTER (WHERE am is NOT NULL))) as value
    FROM
    (
        SELECT oprname, pg_operator.oid as oproid,
            pg_am.oid as am, to_json(array_agg(distinct c.oid)) as opclass_oids,
            amname,
        to_json(array_agg(distinct CASE
                      WHEN opcdefault IS TRUE THEN ''
                      WHEN opcdefault IS FALSE THEN opcname
                      ELSE NULL END)) as opclass_names
        FROM
        pg_operator
        LEFT JOIN pg_amop amop ON amop.amopopr = pg_operator.oid
        LEFT JOIN pg_am ON amop.amopmethod = pg_am.oid AND pg_am.amname != 'hash'
        LEFT JOIN pg_opfamily f ON f.opfmethod = pg_am.oid AND amop.amopfamily = f.oid
        LEFT JOIN pg_opclass c ON c.opcfamily = f.oid
        WHERE pg_operator.oid in %(oid_list)s
        GROUP BY pg_operator.oid, oprname, pg_am.oid, amname
    ) by_am
    GROUP BY oproid, oprname
    ) detail
"""

RESOLVE_ATTNAME = """
    SELECT json_object_agg(attrelid || '.'|| attnum, value)
    FROM (
    SELECT attrelid, attnum, json_build_object(
        'relname', quote_ident(relname),
        'attname', quote_ident(attname),
        'nspname', quote_ident(nspname),
        'n_distinct', COALESCE(stadistinct, 0),
        'null_frac', stanullfrac,
        'most_common_values', CASE
            WHEN s.stakind1 = 1 THEN s.stavalues1
            WHEN s.stakind2 = 1 THEN s.stavalues2
            WHEN s.stakind3 = 1 THEN s.stavalues3
            WHEN s.stakind4 = 1 THEN s.stavalues4
            WHEN s.stakind5 = 1 THEN s.stavalues5
            ELSE NULL::anyarray
        END,
        'table_liverows', pg_stat_get_live_tuples(c.oid)
    ) as value
    FROM pg_attribute a
    INNER JOIN pg_class c on c.oid = a.attrelid
    INNER JOIN pg_namespace n ON n.oid = c.relnamespace
    LEFT JOIN pg_statistic s ON s.starelid = c.oid
                       AND s.staattnum = a.attnum
    WHERE (attrelid, attnum) IN %(att_list)s
    ) detail
"""


class ResolvedQual(JSONizable):
    def __init__(
        self,
        nspname,
        relname,
        attname,
        opname,
        amops,
        n_distinct=0,
        most_common_values=None,
        null_frac=None,
        example_values=None,
        eval_type=None,
        relid=None,
        attnum=None,
    ):
        self.nspname = nspname
        self.relname = relname
        self.attname = attname
        self.opname = opname
        self.amops = amops or {}
        self.n_distinct = n_distinct
        self.most_common_values = most_common_values
        self.null_frac = null_frac
        self.example_values = example_values or []
        self.eval_type = eval_type
        self.relid = relid
        self.attnum = attnum

    def __str__(self):
        return "{}.{} {} ?".format(self.relname, self.attname, self.opname)

    @property
    def distinct_values(self):
        if self.n_distinct == 0:
            return None
        elif self.n_distinct > 0:
            return "{}".format(self.n_distinct)
        else:
            return "{} %".format(abs(self.n_distinct) * 100)

    def to_json(self):
        base = super(ResolvedQual, self).to_json()
        base["label"] = str(self)
        base["distinct_values"] = self.distinct_values
        return base


class ComposedQual(JSONizable):
    def __init__(
        self,
        nspname=None,
        relname=None,
        avg_filter=None,
        filter_ratio=None,
        occurences=None,
        execution_count=None,
        table_liverows=None,
        qualid=None,
        relid=None,
        queries=None,
        queryids=None,
    ):
        super(ComposedQual, self).__init__()
        self.qualid = qualid
        self.relname = relname
        self.nspname = nspname
        self.avg_filter = avg_filter
        self.filter_ratio = filter_ratio
        self.execution_count = execution_count
        self.occurences = occurences
        self.table_liverows = table_liverows
        self.relid = relid
        self.queries = queries or []
        self.queryids = queryids or []
        self._quals = []

    def append(self, element):
        if not isinstance(element, ResolvedQual):
            raise ValueError(
                ("ComposedQual elements must be instances of ", "ResolvedQual")
            )
        self._quals.append(element)

    def __iter__(self):
        return self._quals.__iter__()

    def __str__(self):
        return " AND ".join(str(v) for v in self._quals)

    @property
    def where_clause(self):
        return "WHERE {}".format(self)

    def to_json(self):
        base = super(ComposedQual, self).to_json()
        base["quals"] = self._quals
        base["where_clause"] = self.where_clause
        return base


def resolve_quals(conn, quallist, attribute="quals"):
    """
    Resolve quals definition (as dictionary coming from a to_json(quals)
    sql query.

    Arguments:
        conn: a connection to the database against which the qual was executed
        quallist: an iterable of rows, each storing quals in the attributes
        attribute: the attribute containing the qual list itself in each row
    Returns:
        a list of ComposedQual objects
    """
    operator_to_look = set()
    attname_to_look = set()
    operators = {}
    attnames = {}
    for row in quallist:
        values = row[attribute]
        if not isinstance(values, list):
            values = [values]
        for v in values:
            operator_to_look.add(v["opno"])
            attname_to_look.add((v["relid"], v["attnum"]))
    if operator_to_look:
        cur = conn.cursor()
        cur.execute(RESOLVE_OPNAME, {"oid_list": tuple(operator_to_look)})
        operators = cur.fetchone()[0]
        cur.close()
    if attname_to_look:
        cur = conn.cursor()
        cur.execute(RESOLVE_ATTNAME, {"att_list": tuple(attname_to_look)})
        attnames = cur.fetchone()[0]
    new_qual_list = []
    for row in quallist:
        row = dict(row)
        newqual = ComposedQual(
            occurences=row["occurences"],
            execution_count=row["execution_count"],
            avg_filter=row["avg_filter"],
            filter_ratio=row["filter_ratio"],
            qualid=row["qualid"],
            queries=row.get("queries"),
            queryids=row.get("queryids"),
        )
        new_qual_list.append(newqual)
        values = [v for v in row[attribute] if v["relid"] != "0"]
        if not isinstance(values, list):
            values = [values]
        for v in values:
            attname = attnames["{}.{}".format(v["relid"], v["attnum"])]
            if newqual.relname is not None:
                if newqual.relname != attname["relname"]:
                    raise ValueError(
                        "All individual qual parts should be on the "
                        "same relation"
                    )
            else:
                newqual.relname = attname["relname"]
                newqual.nspname = attname["nspname"]
                newqual.relid = v["relid"]
                newqual.table_liverows = attname["table_liverows"]
            newqual.append(
                ResolvedQual(
                    nspname=attname["nspname"],
                    relname=attname["relname"],
                    attname=attname["attname"],
                    opname=operators[v["opno"]]["name"],
                    amops=operators[v["opno"]]["amop_names"],
                    n_distinct=attname["n_distinct"],
                    most_common_values=attname["most_common_values"],
                    null_frac=attname["null_frac"],
                    eval_type=v["eval_type"],
                    relid=v["relid"],
                    attnum=v["attnum"],
                )
            )
    return new_qual_list


Plan = namedtuple(
    "Plan",
    (
        "title",
        "values",
        "query",
        "plan",
        "filter_ratio",
        "exec_count",
        "occurences",
    ),
)


def qual_constants(
    srvid, type, filter_clause, queries=None, quals=None, top=1
):
    """
    filter_clause is a plain string corresponding to the list of predicates to
    apply in the main query.

    queries and quals are optional list of respectively queryid and qualid to
    filter on.
    """
    orders = {
        "most_executed": "8 DESC",
        "least_filtering": "9",
        "most_filtering": "9 DESC",
        "most_used": "6 DESC",
    }
    if type not in (
        "most_executed",
        "most_filtering",
        "least_filtering",
        "most_used",
    ):
        return

    query_subfilter = ""
    query_filter = ""
    qual_subfilter = ""
    qual_filter = ""

    if queries is not None:
        query_subfilter = "AND queryid IN ({})".format(queries)
        query_filter = "AND s.queryid IN ({})".format(queries)

    if quals is not None:
        qual_subfilter = "AND qualid IN ({})".format(quals)
        qual_filter = "AND qnc.qualid IN ({})".format(quals)

    base = """
    (
    WITH sample AS (
    SELECT s.srvid, query, s.queryid, qn.qualid, quals as quals,
                constants,
                sum(occurences) as occurences,
                sum(execution_count) as execution_count,
                sum(nbfiltered) as nbfiltered,
                CASE WHEN sum(execution_count) = 0 THEN 0 ELSE sum(nbfiltered) / sum(execution_count) END AS filter_ratio
        FROM {{powa}}.powa_statements s
        JOIN {{powa}}.powa_databases d ON d.oid = s.dbid AND d.srvid = s.srvid
        JOIN {{powa}}.powa_qualstats_quals qn ON s.queryid = qn.queryid AND s.srvid = qn.srvid
        JOIN (
            SELECT *
            FROM {{powa}}.powa_qualstats_constvalues_history qnc
            WHERE srvid = {srvid}
            {query_subfilter}
            {qual_subfilter}
              AND coalesce_range && tstzrange(%(from)s, %(to)s)
            UNION ALL
            SELECT *
            FROM {{powa}}.powa_qualstats_aggregate_constvalues_current(%(server)s, %(from)s, %(to)s)
            WHERE srvid = {srvid}
            {query_subfilter}
            {qual_subfilter}
        ) qnc ON qnc.srvid = s.srvid AND qn.qualid = qnc.qualid AND qn.queryid = qnc.queryid,
        LATERAL
                unnest({qual_type}) as t(constants,occurences, execution_count, nbfiltered)
        WHERE {filter}
        {query_filter}
        {qual_filter}
        AND s.srvid = {srvid}
        GROUP BY s.srvid, qn.qualid, quals, constants, s.queryid, query
        ORDER BY {order}
        LIMIT {top_value}
    )
    SELECT srvid, query, queryid, qualid, quals, constants as constants,
                occurences as occurences,
                nbfiltered as nbfiltered,
                execution_count as execution_count,
                filter_ratio as filter_ratio,
                row_number() OVER (ORDER BY execution_count desc NULLS LAST) AS rownumber
        FROM sample
    ORDER BY rownumber
    LIMIT {top_value}
    ) {qual_type}
    """.format(
        qual_type=type,
        filter=filter_clause,
        query_subfilter=query_subfilter,
        query_filter=query_filter,
        qual_subfilter=qual_subfilter,
        qual_filter=qual_filter,
        order=orders[type],
        top_value=top,
        srvid=srvid,
    )

    query = "SELECT * FROM " + base

    return query


def quote_ident(name):
    return '"' + name + '"'


def get_plans(cls, server, database, query, all_vals):
    plans = []
    for key in (
        "most filtering",
        "least filtering",
        "most executed",
        "most used",
    ):
        vals = all_vals[key]
        query = format_jumbled_query(query, vals["constants"])
        plan = "N/A"
        try:
            sqlQuery = "EXPLAIN {}".format(query)
            result = cls.execute(
                sqlQuery, srvid=server, database=database, remote_access=True
            )
            plan = "\n".join(v["QUERY PLAN"] for v in result)
        except Exception as e:
            plan = "ERROR: %r" % e
            pass
        plans.append(
            Plan(
                key,
                vals["constants"],
                query,
                plan,
                vals["filter_ratio"],
                vals["execution_count"],
                vals["occurences"],
            )
        )
    return plans


def get_unjumbled_query(
    ctrl, srvid, database, queryid, _from, _to, kind="most executed"
):
    """
    From a queryid, build a query string ready to be executed.

    Gather a jumbled query from powa_statements, then try to denormalized it
    using stored const values, by its kind (least/most filtering, most common).

    This function can return None if the query has not been gathered by powa,
    or a partially or fully normalized query, depending on const values has
    been found and/or the SELECT clause has been normalized
    """

    rs = list(
        ctrl.execute(
            """
        SELECT query
        FROM {powa}.powa_statements
        WHERE srvid= %(srvid)s
        AND queryid = %(queryid)s LIMIT 1
    """,
            params={"srvid": srvid, "queryid": queryid},
        )
    )[0]
    normalized_query = rs["query"]
    values = qualstat_get_figures(
        ctrl, srvid, database, _from, _to, queries=[queryid]
    )

    if values is None:
        unprepared = unprepare(normalized_query)
        if unprepared != normalized_query:
            return None

    # Try to inject values
    sql = format_jumbled_query(
        normalized_query, values[kind].get("constants", [])
    )
    return sql


def get_any_sample_query(ctrl, srvid, database, queryid, _from, _to):
    """
    From a queryid, get a non normalized query.

    If pg_qualstats is available and recent enough, try to retrieve a randomly
    chosen non normalized query, which is fast, trying to avoid EXPLAIN
    queries.

    If this fail, fallback get_unjumbled_query, with "most executed" const
    values.
    """
    has_pgqs = ctrl.has_extension_version(srvid, "pg_qualstats", "0.0.7")
    example_query = None
    if has_pgqs:
        rows = ctrl.execute(
            """
            WITH s(max, v) AS (
                SELECT
                (SELECT setting::int
                    FROM pg_catalog.pg_settings
                    WHERE name = 'track_activity_query_size'
                ), {pg_qualstats}.pg_qualstats_example_query(%(queryid)s)
            )
            SELECT max, v, octet_length(v) AS len
            FROM s
            WHERE v NOT ILIKE '%%EXPLAIN%%'
            LIMIT 1
        """,
            params={"queryid": queryid},
            srvid=srvid,
            remote_access=True,
        )
        if rows is not None and len(rows) > 0:
            # Ignore the query if it looks like it was truncated
            if rows[0]["len"] < (rows[0]["max"] - 1):
                example_query = rows[0]["v"]
        if example_query is not None:
            unprepared = unprepare(example_query)
            if example_query == unprepared:
                return example_query
    return get_unjumbled_query(
        ctrl, srvid, database, queryid, _from, _to, "most executed"
    )


def qualstat_get_figures(
    cls, srvid, database, tsfrom, tsto, queries=None, quals=None
):
    condition = """datname = %(database)s
            AND coalesce_range && tstzrange(%(from)s, %(to)s)"""

    if queries is not None:
        queries_str = ",".join(str(q) for q in queries)

    cols = [
        "most_filtering.quals",
        "most_filtering.query",
        'to_json(most_filtering) as "most filtering"',
        'to_json(least_filtering) as "least filtering"',
        'to_json(most_executed) as "most executed"',
        'to_json(most_used) as "most used"',
    ]

    sql = """SELECT {cols}
    FROM ({most_filtering}) AS most_filtering
    JOIN ({least_filtering}) AS least_filtering USING (rownumber)
    JOIN ({most_executed}) AS most_executed USING (rownumber)
    JOIN ({most_used}) AS most_used USING (rownumber)""".format(
        cols=", ".join(cols),
        most_filtering=qual_constants(
            srvid, "least_filtering", condition, queries_str, quals
        ),
        least_filtering=qual_constants(
            srvid, "least_filtering", condition, queries_str, quals
        ),
        most_executed=qual_constants(
            srvid, "most_executed", condition, queries_str, quals
        ),
        most_used=qual_constants(
            srvid, "most_used", condition, queries_str, quals
        ),
    )

    params = {
        "server": srvid,
        "database": database,
        "from": tsfrom,
        "to": tsto,
        "queryids": queries,
    }
    quals = cls.execute(sql, params=params)

    if len(quals) == 0:
        return None

    row = quals[0]

    return row


class HypoPlan(JSONizable):
    def __init__(
        self, baseplan, basecost, hypoplan, hypocost, query, indexes=None
    ):
        self.baseplan = baseplan
        self.basecost = basecost
        self.hypoplan = hypoplan
        self.hypocost = hypocost
        self.query = query
        self.indexes = indexes or []

    @property
    def gain_percent(self):
        return round(
            100 - float(self.hypocost) * 100 / float(self.basecost), 2
        )

    def to_json(self):
        base = super(HypoPlan, self).to_json()
        base["gain_percent"] = self.gain_percent
        return base


class HypoIndex(JSONizable):
    def __init__(self, nspname, relname, amname, composed_qual=None):
        self.nspname = nspname
        self.relname = relname
        self.qual = composed_qual
        self.amname = amname
        self.name = None
        self._ddl = None
        self.__setattr__ = self.__setattr
        self._update_ddl()

    def _update_ddl(self):
        if "btree" == self.amname:
            attrs = []
            for qual in self.qual:
                if qual.attname not in attrs:
                    attrs.append(qual.attname)
            # Qual resolution is responsible for quoting all identifiers
            super(HypoIndex, self).__setattr__(
                "_ddl",
                """CREATE INDEX ON {nsp}.{rel}({attrs})""".format(
                    nsp=self.nspname, rel=self.relname, attrs=",".join(attrs)
                ),
            )

    def __setattr(self, name, value):
        super(HypoIndex, self).__setattr__(name, value)
        # Only btree is supported right now
        if name in ("amname", "nspname", "relname", "composed_qual"):
            self._update_ddl()

    @property
    def ddl(self):
        return self._ddl

    @property
    def hypo_ddl(self):
        ddl = self.ddl
        if ddl is not None:
            return (
                "SELECT indexname"
                + " FROM {hypopg}.hypopg_create_index(%(sql)s)",
                {"sql": ddl},
            )
        return (None, None)

    def to_json(self):
        base = super(HypoIndex, self).to_json()
        base["ddl"] = self.ddl
        return base


def possible_indexes(composed_qual, order=()):
    by_am = defaultdict(list)

    def sorter(qual):
        attnum = qual.attnum
        if attnum in order:
            return order.index(attnum)
        else:
            # - attnum to guarantee stable sort
            return sys.maxsize - attnum

    for qual in sorted(composed_qual, key=sorter):
        for am in qual.amops.keys():
            by_am[am].append(qual)
    indexes = []
    for am, quals in by_am.items():
        base = quals[0]
        indexes.append(HypoIndex(base.nspname, base.relname, am, quals))
    return indexes


def get_hypoplans(cur, query, indexes=None):
    """
    With a connection to a database where hypothetical indexes
    have already been created, request two plans for each query:
        - one with hypothetical indexes
        - one without hypothetical indexes

    Arguments:
        conn: a connection to the target database
        queries: a list of sql queries, already formatted with values
        indexes: a list of hypothetical index names to look for in the plan
    """
    # Early exit if no query was provided
    if query is None:
        return None

    indexes = indexes or []
    # Escape literal '%'
    query = query.replace("%", "%%")
    cur.execute("SET hypopg.enabled = off")
    try:
        cur.execute("SAVEPOINT hypo")
        cur.execute("EXPLAIN {}".format(query))
        baseplan = "\n".join(v[0] for v in cur.fetchall())
        cur.execute("RELEASE hypo")
    except Exception as e:
        cur.execute("ROLLBACK TO hypo")
        raise e

    cur.execute("SET hypopg.enabled = on")
    try:
        cur.execute("SAVEPOINT hypo")
        cur.execute("EXPLAIN {}".format(query))
        hypoplan = "\n".join(v[0] for v in cur.fetchall())
        cur.execute("RELEASE hypo")
    except Exception as e:
        cur.execute("ROLLBACK TO hypo")
        raise e

    COST_RE = "(?<=\.\.)\d+\.\d+"
    m = re.search(COST_RE, baseplan)
    if m:
        basecost = float(m.group(0))
    else:
        basecost = None
    m = re.search(COST_RE, hypoplan)
    if m:
        hypocost = float(m.group(0))
    else:
        hypocost = None
    used_indexes = []
    for ind in indexes:
        if ind.name is not None and ind.name in hypoplan:
            used_indexes.append(ind)
    return HypoPlan(
        baseplan, basecost, hypoplan, hypocost, query, used_indexes
    )
