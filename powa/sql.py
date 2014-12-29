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
