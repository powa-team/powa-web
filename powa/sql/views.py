from sqlalchemy.sql import (select, cast, func, column, text, extract, case,
                            bindparam)
from sqlalchemy.types import Numeric
from sqlalchemy.sql.functions import max, min, sum
from powa.sql.utils import *


def powa_base_statdata_detailed_db():
    base_query = text("""(
        SELECT unnested.md5query,(unnested.records).*
        FROM (
            SELECT psh.md5query, psh.coalesce_range, unnest(records) AS records
            FROM powa_statements_history psh
            WHERE coalesce_range && tstzrange(:from,:to,'[]')
            AND psh.md5query IN (SELECT powa_statements.md5query FROM powa_statements WHERE powa_statements.dbname=:database)
        ) AS unnested
        WHERE tstzrange(:from,:to,'[]') @> (records).ts
        UNION ALL
        SELECT psc.md5query,(psc.record).*
        FROM powa_statements_history_current psc
        WHERE tstzrange(:from,:to,'[]') @> (record).ts
        AND psc.md5query IN (SELECT powa_statements.md5query FROM powa_statements WHERE powa_statements.dbname=:database)
    ) h JOIN powa_statements s USING (md5query)""")
    return base_query

def powa_base_statdata_db():
    base_query = text("""(
          SELECT dbname, min(lower(coalesce_range)) as min_ts, max(upper(coalesce_range)) as max_ts
          FROM powa_statements_history_db dbh
          WHERE coalesce_range && tstzrange(:from,:to,'[]')
          GROUP BY dbname
    ) ranges,
    LATERAL
      (
        SELECT (unnested1.records).*
        FROM (
            SELECT dbh.coalesce_range, unnest(records) AS records
            FROM powa_statements_history_db dbh
            WHERE coalesce_range @> min_ts
            AND dbh.dbname = ranges.dbname
        ) AS unnested1
        WHERE tstzrange(:from,:to,'[]') @> (unnested1.records).ts
        UNION ALL
        SELECT (unnested2.records).*
        FROM (
            SELECT dbh.coalesce_range, unnest(records) AS records
            FROM powa_statements_history_db dbh
            WHERE coalesce_range @> max_ts
            AND dbh.dbname = ranges.dbname
        ) AS unnested2
        WHERE tstzrange(:from,:to,'[]') @> (unnested2.records).ts
        UNION ALL
        SELECT (dbc.record).*
        FROM powa_statements_history_current_db dbc
        WHERE tstzrange(:from,:to,'[]') @> (dbc.record).ts
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


BASE_QUERY_SAMPLE_DB = text("""(SELECT datname, base.* FROM pg_database, LATERAL (SELECT *
        FROM (SELECT
            row_number() over (partition by dbname order by statements_history.ts) as number,
            count(*) OVER (partition by dbname) as total,
            *
            FROM (
                SELECT dbname, (unnested.records).*
                FROM (
                    SELECT psh.dbname, psh.coalesce_range, unnest(records) AS records
                    FROM powa_statements_history_db psh
                    WHERE coalesce_range && tstzrange(:from, :to,'[]')
                    AND psh.dbname = datname
                ) AS unnested
                WHERE tstzrange(:from, :to,'[]') @> (records).ts
                UNION ALL
                SELECT dbname, (record).*
                FROM powa_statements_history_current_db
                WHERE tstzrange(:from, :to,'[]') @> (record).ts
                AND dbname = datname
            ) as statements_history
        ) as sh
        WHERE number % (int8larger((total)/(:samples+1),1) )=0) as base) as by_db
""")

BASE_QUERY_SAMPLE = text("""(
SELECT dbname, md5query, base.* FROM powa_statements, LATERAL (SELECT *
        FROM (SELECT
            row_number() over (partition by md5query order by statements_history.ts) as number,
            count(*) OVER (partition by md5query) as total,
            *
            FROM (
                SELECT (unnested.records).*
                FROM (
                    SELECT psh.md5query, psh.coalesce_range, unnest(records) AS records
                    FROM powa_statements_history psh
                    WHERE coalesce_range && tstzrange(:from, :to,'[]')
                    AND psh.md5query = powa_statements.md5query
                ) AS unnested
                WHERE tstzrange(:from, :to,'[]') @> (records).ts
                UNION ALL
                SELECT (record).*
                FROM powa_statements_history_current phc
                WHERE tstzrange(:from, :to,'[]') @> (record).ts
                AND phc.md5query = powa_statements.md5query
            ) as statements_history
        ) as sh
        WHERE number % (int8larger((total)/(:samples+1),1) )=0) as base) as by_db
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
