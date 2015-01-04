"""
Utilities for commonly used SQL constructs.
"""
import re
from sqlalchemy.sql import text, select
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
            v["relname"] = attname[0]
            v["attname"] = attname[1]
            v["opname"] = operators[v["opno"]]
            v["repr"] = "%s.%s %s ?" % (attname[0], attname[1], operators[v["opno"]])

        row["where_clause"] = "WHERE %s" % (" AND ".join(v["repr"] for v in values))
        row["eval_type"] = ", ".join("by index" if v["eval_type"] == 'i' else 'post-scan'
                                     for v in values)
    return new_qual_list


Plan = namedtuple(
    "Plan",
    ("title", "values", "query", "plan", "filter_ratio", "exec_count"))


def aggregate_qual_values(filter_clause, top=1):
    filter_clause = filter_clause.compile()
    base = text("""
    (
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
                        sum(mf_count) as count,
                        row_number() over (ORDER BY  CASE
                            WHEN sum(mf_count) = 0 THEN 0
                            ELSE sum(mf_count * mf_filter_ratio) / sum(mf_count)
                        END DESC NULLS LAST) as rownumber
        FROM sample
    GROUP BY mf_constants, quals, query
    ORDER BY 4 DESC NULLS LAST
    LIMIT :top_value),
    lf AS (SELECT
        quals, lf_constants as constants,
                        CASE
                            WHEN sum(lf_count) = 0 THEN 0
                            ELSE sum(lf_count * lf_filter_ratio) / sum(lf_count)
                        END as filter_ratio,
                        sum(lf_count) as count,
                        row_number() over (ORDER BY                          CASE
                            WHEN sum(lf_count) = 0 THEN 0
                            ELSE sum(lf_count * lf_filter_ratio) / sum(lf_count)
                        END NULLS LAST) as rownumber
        FROM sample
    GROUP BY lf_constants, quals
    ORDER BY 3 NULLS LAST
    LIMIT :top_value),
    me AS (SELECT quals, me_constants as constants,
            CASE
                WHEN sum(me_count) = 0 THEN 0
                ELSE sum(me_count * me_filter_ratio) / sum(me_count)
            END as filter_ratio,
            sum(me_count) as count,
            row_number() over (ORDER BY sum(me_count) DESC NULLS LAST) as rownumber
        FROM sample
    GROUP BY me_constants, quals
    ORDER BY 4 DESC NULLS LAST
    LIMIT :top_value)
    SELECT
    rownumber,
    mf.query,
    mf.quals,
    mf,
    lf,
    me
    FROM mf inner join lf using(quals, rownumber)
        inner join me using(quals, rownumber)
    ORDER BY mf.rownumber
    ) agg_constvalues
    """ % filter_clause.statement).params(top_value=top, **filter_clause.params)
    return select(["*"]).select_from(base)

def suggest_indexes(handler, database, query):
    # Find suitable indexes for a given query
    # TODO :
    # - handle all fields and ops, not only the first row
    # - exclude already existing indexes
    # - add intelligence, like indexes on multiple columns, functional indexes...

    # first, find the fields and operators used, on powa database
    sql = text("""
        SELECT * FROM
        (
            SELECT dbname, relid, attnum, opno,
            avg(filter_ratio) as filter_ratio,
            avg(count) as count
            FROM (
                SELECT s.md5query,dbname,(unnest(qn.quals)).*
                -- work on most executed quals
                ,(unnest(most_executed)).*
                FROM powa_statements s
                JOIN powa_qualstats_statements qs ON qs.md5query = s.md5query
                JOIN powa_qualstats_nodehash qn ON qn.queryid = qs.queryid
                JOIN (SELECT * FROM powa_qualstats_nodehash_constvalues c1
                    UNION ALL
                    SELECT * FROM powa_qualstats_view_current c2
                ) qnc ON qnc.nodehash = qn.nodehash AND qnc.queryid = qn.queryid

                WHERE s.dbname = :database AND s.md5query = :query
                -- compute all available data or filter ?
                --AND tstzrange(now() - interval '20 hours',now(),'[)') && coalesce_range
            ) quals
            -- Only quals accessed by a full scan
            WHERE eval_type = 'f'
            GROUP by dbname, relid, attnum, opno
        ) class
        -- only quals filtering half the rows
        WHERE filter_ratio > 0.5
    """)
    params = {"database": database, "query": query}
    qual_fields = handler.execute(sql, params=params)

    if qual_fields.rowcount == 0:
        return []

    row = qual_fields.first()

    # then find indexes for this fields and ops
    sql = text("""
        SELECT 'CREATE INDEX ON ' || quote_ident(nspname) || '.' || quote_ident(relname) || ' USING ' || amname || '(' || string_agg(attname,',') || ')' as query
        FROM (
            SELECT DISTINCT am.amname,nsp.nspname,c.relname,a.attname
            FROM pg_class c
            JOIN pg_attribute a ON a.attrelid = c.oid
            JOIN pg_namespace nsp on nsp.oid = c.relnamespace
            JOIN pg_amop amop ON amop.amoplefttype = a.atttypid
            JOIN pg_am am ON am.oid = amop.amopmethod
            --JOIN pg_opfamily of ON of.oid = amop.amopfamily
            JOIN pg_operator o ON o.oid = amop.amopopr
            --JOIN powa_qualstats_nodehash_constvalues nc ON nc.nodehash = nh.nodehash AND nc.md5query = nh.md5query
            WHERE c.oid in ( :relid )
            AND amop.amopopr = :opno
            AND a.attnum IN ( :attnum )
            AND am.amname != 'hash'
        ) idx
        GROUP by amname,nspname,relname
    """)
    params = {"database": row['dbname'], "relid": row['relid'], "opno": row['opno'], "attnum": row['attnum']}
    result = handler.execute(sql, database=row['dbname'], params=params)
    indexes = result.fetchall()
    return indexes
