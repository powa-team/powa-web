"""
Functions to generate the queries used in components that are neither graphs or
grid.
"""

QUALSTAT_FILTER_RATIO = """CASE
            WHEN sum(execution_count) = 0 THEN 0
            ELSE sum(nbfiltered) / sum(execution_count)::numeric * 100
        END"""


def qualstat_base_statdata(eval_type=None):
    if eval_type is not None:
        base_cols = ["srvid", "qualid", "queryid", "dbid", "userid"]

        pqnh = """(
        SELECT {outer_cols}
            FROM (
                SELECT {inner_cols}
                FROM {{powa}}.powa_qualstats_quals
            ) expanded
            WHERE (qual).eval_type = '{eval_type}'
            GROUP BY {base_cols}
        )""".format(
            outer_cols=", ".join(base_cols + ["array_agg(qual) AS quals"]),
            inner_cols=", ".join(base_cols + ["unnest(quals) AS qual"]),
            base_cols=", ".join(base_cols),
            eval_type=eval_type,
        )
    else:
        pqnh = "{powa}.powa_qualstats_quals"

    base_query = """
    (
    SELECT srvid, qualid, queryid, dbid, userid, (unnested.records).*
    FROM (
        SELECT pqnh.srvid, pqnh.qualid, pqnh.queryid, pqnh.dbid, pqnh.userid,
          pqnh.coalesce_range, unnest(records) AS records
        FROM {{powa}}.powa_qualstats_quals_history pqnh
        WHERE coalesce_range  && tstzrange(%(from)s, %(to)s, '[]')
        AND pqnh.srvid = %(server)s
    ) AS unnested
    WHERE  (records).ts <@ tstzrange(%(from)s, %(to)s, '[]')
    UNION ALL
    SELECT pqnc.srvid, qualid, queryid, dbid, userid, pqnc.ts, pqnc.occurences,
      pqnc.execution_count, pqnc.nbfiltered,
      pqnc.mean_err_estimate_ratio, pqnc.mean_err_estimate_num
    FROM {{powa}}.powa_qualstats_quals_history_current pqnc
    WHERE pqnc.ts <@ tstzrange(%(from)s, %(to)s, '[]')
    AND pqnc.srvid = %(server)s
    ) h
    JOIN {pqnh} AS pqnh USING (srvid, queryid, qualid)""".format(pqnh=pqnh)

    return base_query


def qualstat_getstatdata(
    eval_type=None,
    extra_from="",
    extra_join="",
    extra_select=[],
    extra_where=[],
    extra_groupby=[],
    extra_having=[],
):
    base_query = qualstat_base_statdata(eval_type)

    # Reformat extra_select, extra_where, extra_groupby and extra_having to be
    # plain additional SQL clauses.
    if len(extra_select) > 0:
        extra_select = ", " + ", ".join(extra_select)
    else:
        extra_select = ""

    if len(extra_where) > 0:
        extra_where = " AND " + " AND ".join(extra_where)
    else:
        extra_where = ""

    if len(extra_groupby) > 0:
        extra_groupby = ", " + ", ".join(extra_groupby)
    else:
        extra_groupby = ""

    if len(extra_having) > 0:
        extra_having = " HAVING " + " AND ".join(extra_having)
    else:
        extra_having = ""

    return """SELECT
        ps.srvid, qualid, ps.queryid, query, ps.dbid,
        to_json(quals) AS quals,
        sum(execution_count) AS execution_count,
        sum(occurences) AS occurences,
        (sum(nbfiltered) / sum(occurences)) AS avg_filter,
        {filter_ratio} AS filter_ratio
        {extra_select}
        FROM
        {base_query}
        JOIN {{powa}}.powa_statements ps USING(queryid, srvid)
        {extra_join}
        WHERE h.srvid = %(server)s
        {extra_where}
        GROUP BY ps.srvid, qualid, ps.queryid, ps.dbid, ps.query, quals
        {extra_groupby}
        {extra_having}""".format(
        filter_ratio=QUALSTAT_FILTER_RATIO,
        extra_select=extra_select,
        base_query=base_query,
        extra_join=extra_join,
        extra_where=extra_where,
        extra_groupby=extra_groupby,
        extra_having=extra_having,
    )


TEXTUAL_INDEX_QUERY = """
SELECT 'CREATE INDEX idx_' || q.relid || '_' || array_to_string(attnames, '_')
    || ' ON ' || nspname || '.' || q.relid
    || ' USING ' || idxtype || ' (' || array_to_string(attnames, ', ') || ')'
    AS index_ddl
FROM (SELECT t.nspname,
    t.relid,
    t.attnames,
    unnest(t.possible_types) AS idxtype
    FROM (
        SELECT nl.nspname AS nspname,
            qs.relid::regclass AS relid,
            array_agg(DISTINCT attnames.attnames) AS attnames,
            array_agg(DISTINCT pg_am.amname) AS possible_types,
            array_agg(DISTINCT attnum.attnum) AS attnums
        FROM (
            VALUES (:relid, (:attnums)::smallint[], (:indexam))
        ) as qs(relid, attnums, indexam)
        LEFT JOIN (
            pg_class cl
            JOIN pg_namespace nl ON nl.oid = cl.relnamespace
        ) ON cl.oid = qs.relid
        JOIN pg_am  ON pg_am.amname = qs.indexam
            AND pg_am.amname <> 'hash',
        LATERAL (
            SELECT pg_attribute.attname AS attnames
            FROM pg_attribute
            JOIN unnest(qs.attnums) a(a) ON a.a = pg_attribute.attnum
                AND pg_attribute.attrelid = qs.relid
            ORDER BY pg_attribute.attnum
        ) attnames,
        LATERAL unnest(qs.attnums) attnum(attnum)
       WHERE NOT (EXISTS (
           SELECT 1
           FROM pg_index i
           WHERE i.indrelid = qs.relid AND (
             (i.indkey::smallint[])[0:array_length(qs.attnums, 1) - 1]
                 @> qs.attnums
             OR qs.attnums
                 @> (i.indkey::smallint[])[0:array_length(i.indkey, 1) + 1]
             AND i.indisunique))
       )
       GROUP BY nl.nspname, qs.relid
    ) t
    GROUP BY t.nspname, t.relid, t.attnames, t.possible_types
) q
"""


def get_config_changes(restrict_database=False):
    restrict_db = ""
    if restrict_database:
        restrict_db = "AND (d.datname = %(database)s OR h.setdatabase = 0)"

    sql = """SELECT * FROM
(
  WITH src AS (
    select ts, name,
    lag(setting_pretty) OVER (PARTITION BY name ORDER BY ts) AS prev_val,
    setting_pretty AS new_val,
    lag(is_dropped) OVER (PARTITION BY name ORDER BY ts) AS prev_is_dropped,
    is_dropped as is_dropped
    FROM {{pg_track_settings}}.pg_track_settings_history h
    WHERE srvid = %(server)s
    AND ts <= %(to)s
  )
  SELECT extract("epoch" FROM ts) AS ts, 'global' AS kind,
  json_build_object(
    'name', name,
    'prev_val', prev_val,
    'new_val', new_val,
    'prev_is_dropped', coalesce(prev_is_dropped, true),
    'is_dropped', is_dropped
  ) AS data
  FROM src
  WHERE ts >= %(from)s AND ts <= %(to)s
) AS global

UNION ALL

SELECT * FROM
(
  WITH src AS (
    select ts, name,
    lag(setting) OVER (PARTITION BY name, setdatabase, setrole ORDER BY ts) AS prev_val,
    setting AS new_val,
    lag(is_dropped) OVER (PARTITION BY name, setdatabase, setrole ORDER BY ts) AS prev_is_dropped,
    is_dropped as is_dropped,
    d.datname,
    h.setrole
    FROM {{pg_track_settings}}.pg_track_db_role_settings_history h
    LEFT JOIN {{powa}}.powa_databases d
      ON d.srvid = h.srvid
      AND d.oid = h.setdatabase
    WHERE h.srvid = %(server)s
    {restrict_db}
    AND ts <= %(to)s
  )
  SELECT extract("epoch" FROM ts) AS ts, 'rds' AS kind,
  json_build_object(
    'name', name,
    'prev_val', prev_val,
    'new_val', new_val,
    'prev_is_dropped', coalesce(prev_is_dropped, true),
    'is_dropped', is_dropped,
    'datname', datname,
    'setrole', setrole
  ) AS data
  FROM src
  WHERE ts >= %(from)s AND ts <= %(to)s
) AS rds

UNION ALL

SELECT extract("epoch" FROM ts) AS ts, 'reboot' AS kind,
NULL AS data
FROM {{pg_track_settings}}.pg_reboot AS r
WHERE r.srvid = %(server)s
AND r.ts>= %(from)s
AND r.ts <= %(to)s
ORDER BY ts""".format(restrict_db=restrict_db)

    return sql
