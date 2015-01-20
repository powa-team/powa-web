"""
Utilities for commonly used SQL constructs.
"""
import re
from sqlalchemy.sql import text, select, func, case, column, extract, cast, bindparam
from sqlalchemy.types import Numeric
from collections import namedtuple

TOTAL_MEASURE_INTERVAL = """
extract( epoch from
    CASE WHEN min(total_mesure_interval) = '0 second'
        THEN '1 second'::interval
    ELSE min(total_mesure_interval) END)
"""


def format_jumbled_query(sql, params):
    it = iter(params)
    try:
        sql = re.sub("\?", lambda val: next(it), sql)
    except StopIteration:
        pass
    return sql


RESOLVE_OPNAME = text("""
    SELECT json_object_agg(oid, value)
    FROM (
    SELECT pg_operator.oid, json_build_object(
        'name', oprname,
        'indexams', array_agg(distinct pg_am.oid),
        'indexam_names', array_agg(distinct pg_am.amname)) as value
    FROM pg_operator
    JOIN pg_amop amop ON amop.amopopr = pg_operator.oid
    JOIN pg_am ON amop.amopmethod = pg_am.oid
    WHERE pg_operator.oid in :oid_list AND pg_am.amname != 'hash'
    GROUP BY pg_operator.oid, oprname
    ) detail
""")

RESOLVE_ATTNAME = text("""
    SELECT json_object_agg(attrelid || '.'|| attnum, value)
    FROM (
    SELECT attrelid, attnum, json_build_object(
        'relname', relname,
        'attname', attname,
        'n_distinct', stadistinct,
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
    LEFT JOIN pg_statistic s ON s.starelid = c.oid
                       AND s.staattnum = a.attnum
    WHERE (attrelid, attnum) IN :att_list
    ) detail
""")


def resolve_quals(conn, quallist, attribute="quals"):
    """
    Resolve quals definition (as dictionary coming from a to_json(quals)
    sql query.

    Arguments:
        conn: a connection to the database against which the qual was executed
        quallist: an iterable of rows, each storing quals in the attributes
        attribute: the attribute containing the qual list itself in each row
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
            operator_to_look.add(v['opno'])
            attname_to_look.add((v["relid"], v["attnum"]))
    if operator_to_look:
        operators = conn.execute(
            RESOLVE_OPNAME,
            {"oid_list": tuple(operator_to_look)}).scalar()
    if attname_to_look:
        attnames = conn.execute(
            RESOLVE_ATTNAME,
            {"att_list": tuple(attname_to_look)}).scalar()
    new_qual_list = []
    for row in quallist:
        row = dict(row)
        new_qual_list.append(row)
        values = row[attribute]
        if not isinstance(values, list):
            values = [values]
        for v in values:
            attname = attnames["%s.%s" % (v["relid"], v["attnum"])]
            v["relname"] = attname['relname']
            v["attname"] = attname['attname']
            v["n_distinct"] = attname['n_distinct']
            v["most_common_values"] = attname['most_common_values']
            v["null_frac"] = attname['null_frac']
            v["opname"] = operators[v["opno"]]['name']
            v["indexams"] = operators[v["opno"]]['indexams']
            v["indexam_names"] = operators[v["opno"]]['indexam_names']
            v["table_liverows"] = attname["table_liverows"]
            v["repr"] = "%s.%s %s ?" % (attname["relname"], attname["attname"],
                                        v["opname"])
        row["where_clause"] = "WHERE %s" % (" AND ".join(v["repr"] for v in values))
        row["eval_type"] = ", ".join("by index" if v["eval_type"] == 'i' else 'post-scan'
                                     for v in values)
    return new_qual_list


Plan = namedtuple(
    "Plan",
    ("title", "values", "query", "plan", "filter_ratio", "exec_count"))


def qual_constants(type, filter_clause, top=1):
    orders = {
        'most_executed': "4 DESC",
        'least_filtering': "6",
        'most_filtering': "6 DESC"
    }
    if type not in ('most_executed', 'most_filtering',
                    'least_filtering'):
        return
    filter_clause = filter_clause.compile()
    base = text("""
    (
    WITH sample AS (
    SELECT query, quals as quals,
                constants,
                sum(count) as count,
                sum(nbfiltered) as nbfiltered,
                CASE WHEN sum(count) = 0 THEN 0 ELSE sum(nbfiltered) / sum(count) END AS filter_ratio
        FROM powa_statements s
        JOIN pg_database ON pg_database.oid = s.dbid
        JOIN powa_qualstats_quals qn ON s.queryid = qn.queryid
        JOIN (
            SELECT *
            FROM powa_qualstats_constvalues_history qnc
            UNION ALL
            SELECT *
            FROM powa_qualstats_aggregate_constvalues_current
        ) qnc ON qn.qualid = qnc.qualid AND qn.queryid = qnc.queryid,
        LATERAL
                unnest(%s) as t(constants,nbfiltered,count)
        WHERE %s
        GROUP BY quals, constants, query
        ORDER BY %s
        LIMIT :top_value
    )
    SELECT query, quals, constants as constants, nbfiltered as nbfiltered,
                count as count,
                filter_ratio as filter_ratio,
                row_number() OVER (ORDER BY count desc NULLS LAST) as rownumber
        FROM sample
    ORDER BY 7
    LIMIT :top_value
    ) %s
    """ % (type, filter_clause.statement, orders[type], type)
                ).params(top_value=top, **filter_clause.params)
    return select(["*"]).select_from(base)
