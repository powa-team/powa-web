"""
Utilities for commonly used SQL constructs.
"""
import re
from sqlalchemy.sql import text
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
    SELECT json_object_agg(oid, oprname) FROM pg_operator WHERE oid in :oid_list
""")

RESOLVE_ATTNAME = text("""
    SELECT json_object_agg(attrelid || '.'|| attnum, ARRAY[relname, attname])
    FROM pg_attribute a
    INNER JOIN pg_class c on c.oid = a.attrelid
    WHERE (attrelid, attnum) IN :att_list
""")


def resolve_quals(conn, quallist, attribute="quals", store="where_clause"):
    operator_to_look = set()
    attname_to_look = set()
    operators = {}
    attnames = {}
    print(quallist)
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
    for row in quallist:
        values = row[attribute]
        if not isinstance(values, list):
            values = [values]
        for v in values:
            attname = attnames["%s.%s" % (v["relid"], v["attnum"])]
            v["relname"] = attname[0]
            v["attname"] = attname[1]
            v["opname"] = operators[v["opno"]]
            v["repr"] = "%s.%s %s ?" % (attname[0], attname[1], operators[v["opno"]])
        row[store] = "WHERE %s" % (" AND ".join(v["repr"] for v in values))
    return quallist


Plan = namedtuple(
    "Plan",
    ("title", "values", "query", "plan", "filter_ratio", "exec_count"))


def aggregate_qual_values(filter_clause):
    filter_clause = filter_clause.compile()
    return text("""
    WITH sample AS (
    SELECT query, quals as quals, t.*
        FROM powa_statements s
        JOIN powa_qualstats_statements qs ON s.md5query = qs.md5query
        JOIN powa_qualstats_nodehash qn ON qs.queryid = qn.queryid
        JOIN powa_qualstats_nodehash_constvalues qnc
            ON qn.nodehash = qnc.nodehash AND qn.queryid = qnc.queryid,
        LATERAL
                unnest(least_filtering, most_filtering, most_executed) as t(
                lf_nodehash,lf_constants,lf_ts,lf_filter_ratio,lf_count,
                mf_nodehash, mf_constants,mf_ts,mf_filter_ratio,mf_count,
                me_nodehash, me_constants,me_ts,me_filter_ratio,me_count)
        WHERE %s
    ),
    mf AS (SELECT query, quals, mf_constants as constants,
                        CASE
                            WHEN sum(mf_count) = 0 THEN 0
                            ELSE sum(mf_count * mf_filter_ratio) / sum(mf_count)
                        END as filter_ratio,
                        sum(mf_count) as count
        FROM sample
    GROUP BY mf_constants, quals, query
    ORDER BY 4 DESC
    LIMIT 1),
    lf AS (SELECT
        quals, lf_constants as constants,
                        CASE
                            WHEN sum(lf_count) = 0 THEN 0
                            ELSE sum(lf_count * lf_filter_ratio) / sum(lf_count)
                        END as filter_ratio,
                        sum(lf_count) as count
        FROM sample
    GROUP BY lf_constants, quals
    ORDER BY 3
    LIMIT 1),
    me AS (SELECT quals, me_constants as constants,
                        CASE
                            WHEN sum(me_count) = 0 THEN 0
                            ELSE sum(me_count * me_filter_ratio) / sum(me_count)
                        END as filter_ratio,
                        sum(me_count) as count
        FROM sample
    GROUP BY me_constants, quals
    ORDER BY 4 DESC
    LIMIT 1)
    SELECT
    mf.query,
    to_json(mf) as "most filtering",
    to_json(lf) as "least filtering",
    to_json(me) as "most executed"
    FROM mf, lf, me
    """ % filter_clause.statement).params(**filter_clause.params)
