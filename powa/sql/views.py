from sqlalchemy.sql import (select, cast, func, column, text, extract, case,
                            bindparam, literal_column)
from sqlalchemy.types import Numeric
from sqlalchemy.sql.functions import max, min, sum
from powa.sql.utils import *


def powa_base_statdata_detailed_db():
    base_query = text("""(
        SELECT unnested.md5query,(unnested.records).*
        FROM (
            SELECT psh.md5query, psh.coalesce_range, unnest(records) AS records
            FROM powa_statements_history psh
            WHERE coalesce_range && tstzrange(:from, :to, '[]')
            AND psh.md5query IN ( SELECT powa_statements.md5query FROM powa_statements WHERE powa_statements.dbname=:database )
        ) AS unnested
        WHERE tstzrange(:from, :to, '[]') @> (records).ts
        UNION ALL
        SELECT psc.md5query,(psc.record).*
        FROM powa_statements_history_current psc
        WHERE tstzrange(:from,:to,'[]') @> (record).ts
        AND psc.md5query IN (SELECT powa_statements.md5query FROM powa_statements WHERE powa_statements.dbname = :database)
    ) h JOIN powa_statements s USING (md5query)
    """)
    return base_query

def powa_base_statdata_db():
    base_query = text("""(
          SELECT dbname, min(lower(coalesce_range)) AS min_ts, max(upper(coalesce_range)) AS max_ts
          FROM powa_statements_history_db dbh
          WHERE coalesce_range && tstzrange(:from, :to, '[]')
          GROUP BY dbname
    ) ranges,
    LATERAL (
        SELECT (unnested1.records).*
        FROM (
            SELECT dbh.coalesce_range, unnest(records) AS records
            FROM powa_statements_history_db dbh
            WHERE coalesce_range @> min_ts
            AND dbh.dbname = ranges.dbname
        ) AS unnested1
        WHERE tstzrange(:from, :to, '[]') @> (unnested1.records).ts
        UNION ALL
        SELECT (unnested2.records).*
        FROM (
            SELECT dbh.coalesce_range, unnest(records) AS records
            FROM powa_statements_history_db dbh
            WHERE coalesce_range @> max_ts
            AND dbh.dbname = ranges.dbname
        ) AS unnested2
        WHERE tstzrange(:from, :to, '[]') @> (unnested2.records).ts
        UNION ALL
        SELECT (dbc.record).*
        FROM powa_statements_history_current_db dbc
        WHERE tstzrange(:from, :to, '[]') @> (dbc.record).ts
        AND dbc.dbname = ranges.dbname
    ) AS db_history
    """)
    return base_query

def get_diffs_forstatdata():
    return [
        diff("calls"),
        diff("total_time").label("runtime"),
        diff("shared_blks_read"),
        diff("shared_blks_hit"),
        diff("shared_blks_dirtied"),
        diff("shared_blks_written"),
        diff("temp_blks_read"),
        diff("temp_blks_written"),
        diff("blk_read_time"),
        diff("blk_write_time")
    ]

def powa_getstatdata_detailed_db():
    base_query = powa_base_statdata_detailed_db()
    diffs = get_diffs_forstatdata()
    return (select([
        column("md5query"),
        column("query"),
        column("dbname"),
] + diffs)
        .select_from(base_query)
        .where(column("dbname") == bindparam("database"))
        .group_by(column("md5query"), column("query"), column("dbname"))
        .having(max(column("calls")) - min(column("calls")) > 0))

def powa_getstatdata_db():
    base_query = powa_base_statdata_db()
    diffs = get_diffs_forstatdata()
    return (select([column("dbname")] + diffs)
            .select_from(base_query)
            .group_by(column("dbname"))
            .having(max(column("calls")) - min(column("calls")) > 0))


BASE_QUERY_SAMPLE_DB = text("""(
    SELECT datname, base.* FROM pg_database,
    LATERAL (
        SELECT *
        FROM (
            SELECT
            row_number() OVER (PARTITION BY dbname ORDER BY statements_history.ts) AS number,
            count(*) OVER (PARTITION BY dbname) AS total,
            *
            FROM (
                SELECT dbname, (unnested.records).*
                FROM (
                    SELECT psh.dbname, psh.coalesce_range, unnest(records) AS records
                    FROM powa_statements_history_db psh
                    WHERE coalesce_range && tstzrange(:from, :to,'[]')
                    AND psh.dbname = datname
                ) AS unnested
                WHERE tstzrange(:from, :to, '[]') @> (records).ts
                UNION ALL
                SELECT dbname, (record).*
                FROM powa_statements_history_current_db
                WHERE tstzrange(:from, :to, '[]') @> (record).ts
                AND dbname = datname
            ) AS statements_history
        ) AS sh
        WHERE number % ( int8larger((total)/(:samples+1),1) ) = 0
    ) AS base
) AS by_db
""")

BASE_QUERY_SAMPLE = text("""(
    SELECT dbname, md5query, base.*
    FROM powa_statements,
    LATERAL (
        SELECT *
        FROM (SELECT
            row_number() OVER (PARTITION BY md5query ORDER BY statements_history.ts) AS number,
            count(*) OVER (PARTITION BY md5query) AS total,
            *
            FROM (
                SELECT (unnested.records).*
                FROM (
                    SELECT psh.md5query, psh.coalesce_range, unnest(records) AS records
                    FROM powa_statements_history psh
                    WHERE coalesce_range && tstzrange(:from, :to, '[]')
                    AND psh.md5query = powa_statements.md5query
                ) AS unnested
                WHERE tstzrange(:from, :to, '[]') @> (records).ts
                UNION ALL
                SELECT (record).*
                FROM powa_statements_history_current phc
                WHERE tstzrange(:from, :to, '[]') @> (record).ts
                AND phc.md5query = powa_statements.md5query
            ) AS statements_history
        ) AS sh
        WHERE number % ( int8larger((total)/(:samples+1),1) ) = 0
    ) AS base
) AS by_query
""")


def powa_getstatdata_sample(mode):
    if mode == "db":
        base_query = BASE_QUERY_SAMPLE_DB
        base_columns = ["dbname"]

    elif mode == "query":
        base_query = BASE_QUERY_SAMPLE
        base_columns = ["dbname", "md5query"]


    def biggest(var, minval=0, label=None):
        label = label or var
        return func.greatest(
            func.lead(column(var)).over(order_by="ts", partition_by=base_columns) - column(var),
            minval).label(label)

    return select(base_columns + [
        "ts",
        biggest("ts", '0 s', "mesure_interval"),
        biggest("calls"),
        biggest("total_time", label="runtime"),
        biggest("rows"),
        biggest("shared_blks_read"),
        biggest("shared_blks_hit"),
        biggest("shared_blks_dirtied"),
        biggest("shared_blks_written"),
        biggest("local_blks_read"),
        biggest("local_blks_hit"),
        biggest("local_blks_dirtied"),
        biggest("local_blks_written"),
        biggest("temp_blks_read"),
        biggest("temp_blks_written"),
        biggest("blk_read_time"),
        biggest("blk_write_time")]).select_from(base_query)



BASE_QUERY_QUALSTATS_SAMPLE = text("""
powa_statements ps
JOIN powa_qualstats_statements pqs USING(md5query)
JOIN powa_qualstats_nodehash nh USING(queryid)
, LATERAL (
    SELECT  sh.ts,
         sh.nodehash,
         sh.quals,
         int8larger(lead(sh.count) over (querygroup) - sh.count,0) count,
         CASE WHEN sum(sh.count) over querygroup > 0 THEN sum(sh.count * sh.filter_ratio) over (querygroup) / sum(sh.count) over (querygroup) ELSE 0 END as filter_ratio
         FROM (
      SELECT * FROM
      (
         SELECT row_number() over (order by quals_history.ts) as number, *,
          count(*) OVER () as total
         FROM (
          SELECT unnested.queryid, unnested.nodehash, (unnested.records).*
          FROM (
              SELECT nh.queryid, nh.nodehash, nh.coalesce_range, unnest(records) AS records
              FROM powa_qualstats_nodehash_history nh
              WHERE coalesce_range && tstzrange(:from, :to)
              AND queryid = nh.queryid AND nodehash = nh.nodehash
          ) AS unnested
          WHERE tstzrange(:from, :to) @> (records).ts and queryid = nh.queryid
          UNION ALL
          SELECT powa_qualstats_nodehash_current.queryid, powa_qualstats_nodehash_current.nodehash, powa_qualstats_nodehash_current.ts, powa_qualstats_nodehash_current.quals, powa_qualstats_nodehash_current.avg_filter_ratio, powa_qualstats_nodehash_current.count
          FROM powa_qualstats_nodehash_current
          WHERE tstzrange(:from, :to)@> powa_qualstats_nodehash_current.ts
          AND queryid = nh.queryid AND nodehash = nh.nodehash
        ) quals_history
     ) numbered_history WHERE number % (int8larger(total/(:samples+1),1) )=0
    ) sh
     WINDOW querygroup AS (PARTITION BY sh.nodehash  ORDER BY sh.ts)
) samples
""")

def qualstat_getstatdata_sample():
    base_query = BASE_QUERY_QUALSTATS_SAMPLE
    base_columns = [
        literal_column("nh.queryid").label("queryid"),
        func.to_json(literal_column("nh.quals")).label("quals"),
        literal_column("nh.nodehash").label("nodehash"),
        "count",
        "filter_ratio",
        "md5query"]
    return (select(base_columns)
            .select_from(base_query)
            .where(column("count") != None))


def qualstat_base_statdata():
    base_query = text("""
    (
    SELECT unnested.nodehash, unnested.queryid,  (unnested.records).*
    FROM (
        SELECT pqnh.nodehash, pqnh.queryid, pqnh.coalesce_range, unnest(records) as records
        FROM powa_qualstats_nodehash_history pqnh
        WHERE coalesce_range && tstzrange(:from, :to, '[]')
        AND pqnh.queryid IN ( SELECT pqs.queryid FROM powa_qualstats_statements pqs WHERE pqs.md5query = :query)
    ) AS unnested
    WHERE tstzrange(:from, :to, '[]') @> (records).ts
    UNION ALL
        SELECT pqnc.nodehash, pqnc.queryid, pqnc.ts, pqnc.quals, pqnc.avg_filter_ratio, pqnc.count
        FROM powa_qualstats_nodehash_current pqnc
        WHERE tstzrange(:from, :to, '[]') @> pqnc.ts
        AND pqnc.queryid IN ( SELECT pqs.queryid FROM powa_qualstats_statements pqs WHERE pqs.md5query = :query)
    ) h JOIN powa_qualstats_statements USING (queryid)
    """)
    return base_query


def qualstat_getstatdata():
    base_query = qualstat_base_statdata()
    return (select([
        column("nodehash"),
        column("queryid"),
        column("md5query"),
        func.to_json(column("quals")).label("quals"),
        diff("count"),
        (sum(column("count") * column("filter_ratio")) /
         sum(column("count"))).label("filter_ratio")])
        .select_from(base_query)
        .group_by(column("nodehash"), column("queryid"), column("quals"), column("md5query"))
        .having(max(column("count")) - min(column("count")) > 0))
