from sqlalchemy.sql import (select, cast, func, column, text, case, and_,
                            literal_column, join)
from sqlalchemy.types import Numeric
from sqlalchemy.sql.functions import max, min, sum
from powa.sql.utils import diff
from powa.sql.tables import powa_statements


class Biggest(object):

    def __init__(self, base_columns, order_by):
        self.base_columns = base_columns
        self.order_by = order_by

    def __call__(self, var, minval=0, label=None):
        label = label or var
        return func.greatest(
            func.lead(column(var))
            .over(order_by=self.order_by,
                  partition_by=self.base_columns)
            - column(var),
            minval).label(label)


class Biggestsum(object):

    def __init__(self, base_columns, order_by):
        self.base_columns = base_columns
        self.order_by = order_by

    def __call__(self, var, minval=0, label=None):
        label = label or var
        return func.greatest(
            func.lead(sum(column(var)))
            .over(order_by=self.order_by,
                  partition_by=self.base_columns)
            - sum(column(var)),
            minval).label(label)


def powa_base_statdata_detailed_db():
    base_query = text("""
  powa_databases,
  LATERAL
  (
    SELECT unnested.dbid, unnested.userid, unnested.queryid,
      (unnested.records).*
    FROM (
      SELECT psh.dbid, psh.userid, psh.queryid, psh.coalesce_range,
        unnest(records) AS records
      FROM powa_statements_history psh
      WHERE coalesce_range && tstzrange(:from, :to, '[]')
      AND psh.dbid = powa_databases.oid
      AND psh.queryid IN (
        SELECT powa_statements.queryid
        FROM powa_statements
        WHERE powa_statements.dbid = powa_databases.oid
          AND powa_statements.srvid = :server
      )
      AND psh.srvid = :server
    ) AS unnested
    WHERE (records).ts <@ tstzrange(:from, :to, '[]')
    UNION ALL
    SELECT psc.dbid, psc.userid, psc.queryid,(psc.record).*
    FROM powa_statements_history_current psc
    WHERE (record).ts <@ tstzrange(:from,:to,'[]')
    AND psc.dbid = powa_databases.oid
    AND psc.queryid IN (
      SELECT powa_statements.queryid
      FROM powa_statements
      WHERE powa_statements.dbid = powa_databases.oid
        AND powa_statements.srvid = :server
    )
    AND psc.srvid = :server
  ) h""")
    return base_query


def powa_base_statdata_db():
    base_query = text("""(
 SELECT d.srvid, d.oid as dbid, h.*
 FROM
 powa_databases d LEFT JOIN
 (
   SELECT srvid, dbid
   FROM powa_statements_history_db dbh
   WHERE coalesce_range && tstzrange(:from, :to, '[]')
   AND dbh.srvid = :server
   GROUP BY srvid, dbid
 ) ranges ON d.oid = ranges.dbid AND d.srvid = ranges.srvid,
 LATERAL (
   SELECT (unnested1.records).*
   FROM (
     SELECT dbh.coalesce_range, unnest(records) AS records
     FROM powa_statements_history_db dbh
     WHERE coalesce_range && tstzrange(:from, :to, '[]')
     AND dbh.dbid = ranges.dbid
     AND dbh.srvid = :server
   ) AS unnested1
   WHERE (unnested1.records).ts <@ tstzrange(:from, :to, '[]')
   UNION ALL
   SELECT (unnested2.records).*
   FROM (
     SELECT dbh.coalesce_range, unnest(records) AS records
     FROM powa_statements_history_db dbh
     WHERE coalesce_range && tstzrange(:from, :to, '[]')
     AND dbh.dbid = ranges.dbid
     AND dbh.srvid = :server
   ) AS unnested2
   WHERE  (unnested2.records).ts <@ tstzrange(:from, :to, '[]')
   UNION ALL
   SELECT (dbc.record).*
   FROM powa_statements_history_current_db dbc
   WHERE  (dbc.record).ts <@ tstzrange(:from, :to, '[]')
   AND dbc.dbid = d.oid
   AND dbc.srvid = d.srvid
   AND dbc.srvid = :server
    ) AS h
) AS db_history
    """)
    return base_query


def powa_base_bgwriter():
    base_query = text("""(
 SELECT h.*
 FROM
 (
   SELECT srvid
   FROM powa_stat_bgwriter_history bgwh
   WHERE coalesce_range && tstzrange(:from, :to, '[]')
   AND dbh.srvid = :server
   GROUP BY srvid
 ) ranges
 LATERAL (
   SELECT (unnested1.records).*
   FROM (
     SELECT bgwh.coalesce_range, unnest(records) AS records
     FROM powa_stat_bgwriter_history bgwh
     WHERE coalesce_range && tstzrange(:from, :to, '[]')
     AND bgwh.srvid = :server
   ) AS unnested1
   WHERE  (unnested1.records).ts <@ tstzrange(:from, :to, '[]')
   UNION ALL
   SELECT (bgwc.record).*
   FROM powa_stat_bgwriter_history_current bgwc
   WHERE  (dbc.record).ts <@ tstzrange(:from, :to, '[]')
   AND dbc.srvid = d.srvid
   AND dbc.srvid = :server
    ) AS h
) AS bgw_history
    """)
    return base_query


def get_diffs_forstatdata():
    return [
        diff("calls"),
        diff("total_plan_time").label("plantime"),
        diff("total_exec_time").label("runtime"),
        diff("shared_blks_read"),
        diff("shared_blks_hit"),
        diff("shared_blks_dirtied"),
        diff("shared_blks_written"),
        diff("temp_blks_read"),
        diff("temp_blks_written"),
        diff("blk_read_time"),
        diff("blk_write_time"),
        diff("wal_records"),
        diff("wal_fpi"),
        diff("wal_bytes")
    ]


def powa_getstatdata_detailed_db(srvid):
    base_query = powa_base_statdata_detailed_db()
    diffs = get_diffs_forstatdata()
    return (select([
        column("srvid"),
        column("queryid"),
        column("dbid"),
        column("userid"),
        column("datname"),
    ] + diffs)
            .select_from(base_query)
            .where(column("srvid") == srvid)
            .group_by(column("srvid"), column("queryid"), column("dbid"),
                      column("userid"), column("datname"))
            .having(max(column("calls")) - min(column("calls")) > 0))


def powa_getstatdata_db(srvid):
    base_query = powa_base_statdata_db()
    diffs = get_diffs_forstatdata()
    return (select([column("srvid")] + [column("dbid")] + diffs)
            .select_from(base_query)
            .where(column("srvid") == srvid)
            .group_by(column("srvid"), column("dbid"))
            .having(max(column("calls")) - min(column("calls")) > 0))


BASE_QUERY_SAMPLE_DB = text("""(
  SELECT d.srvid, d.datname, base.* FROM powa_databases d,
  LATERAL (
    SELECT *
    FROM (
      SELECT
      row_number() OVER (
        PARTITION BY dbid ORDER BY statements_history.ts
      ) AS number,
      count(*) OVER (PARTITION BY dbid) AS total,
      *
      FROM (
        SELECT dbid, (unnested.records).*
        FROM (
          SELECT psh.dbid, psh.coalesce_range, unnest(records) AS records
          FROM powa_statements_history_db psh
          WHERE coalesce_range && tstzrange(:from, :to,'[]')
          AND psh.dbid = d.oid
          AND psh.srvid = d.srvid
          AND psh.srvid = :server
        ) AS unnested
        WHERE (records).ts <@ tstzrange(:from, :to, '[]')
        UNION ALL
        SELECT dbid, (record).*
        FROM powa_statements_history_current_db
        WHERE  (record).ts <@ tstzrange(:from, :to, '[]')
        AND dbid = d.oid
        AND srvid = d.srvid
        AND srvid = :server
      ) AS statements_history
    ) AS sh
    WHERE number % ( int8larger((total)/(:samples+1),1) ) = 0
  ) AS base
  WHERE srvid = :server
) AS by_db""")


BASE_QUERY_SAMPLE = text("""(
  SELECT powa_statements.srvid, datname, dbid, queryid, userid, base.*
  FROM powa_statements
  JOIN powa_databases ON powa_databases.oid = powa_statements.dbid
   AND powa_databases.srvid = powa_statements.srvid,
  LATERAL (
      SELECT *
      FROM (SELECT
          row_number() OVER (
            PARTITION BY queryid ORDER BY statements_history.ts
          ) AS number,
          count(*) OVER (PARTITION BY queryid) AS total,
          *
          FROM (
              SELECT (unnested.records).*
              FROM (
                  SELECT psh.queryid, psh.coalesce_range,
                    unnest(records) AS records
                  FROM powa_statements_history psh
                  WHERE coalesce_range && tstzrange(:from, :to, '[]')
                  AND psh.queryid = powa_statements.queryid
                  AND psh.userid = powa_statements.userid
                  AND psh.srvid = :server
              ) AS unnested
              WHERE  (records).ts <@ tstzrange(:from, :to, '[]')
              UNION ALL
              SELECT (record).*
              FROM powa_statements_history_current phc
              WHERE (record).ts <@ tstzrange(:from, :to, '[]')
              AND phc.queryid = powa_statements.queryid
              AND phc.userid = powa_statements.userid
              AND phc.srvid = :server
          ) AS statements_history
      ) AS sh
      WHERE number % ( int8larger((total)/(:samples+1),1) ) = 0
  ) AS base
  WHERE powa_statements.srvid = :server
) AS by_query

""")


def powa_getstatdata_sample(mode, srvid):
    if mode == "db":
        base_query = BASE_QUERY_SAMPLE_DB
        base_columns = [column("srvid"), column("dbid")]

    elif mode == "query":
        base_query = BASE_QUERY_SAMPLE
        base_columns = [column("srvid"), column("dbid"), column("queryid"),
                        column("userid")]

    ts = column('ts')
    biggest = Biggest(base_columns, ts)
    biggestsum = Biggestsum(base_columns, ts)

    return (select(base_columns + [
        ts,
        biggest("ts", '0 s', "mesure_interval"),
        biggestsum("calls"),
        biggestsum("total_plan_time").label("plantime"),
        biggestsum("total_exec_time", label="runtime"),
        biggestsum("rows"),
        biggestsum("shared_blks_read"),
        biggestsum("shared_blks_hit"),
        biggestsum("shared_blks_dirtied"),
        biggestsum("shared_blks_written"),
        biggestsum("local_blks_read"),
        biggestsum("local_blks_hit"),
        biggestsum("local_blks_dirtied"),
        biggestsum("local_blks_written"),
        biggestsum("temp_blks_read"),
        biggestsum("temp_blks_written"),
        biggestsum("blk_read_time"),
        biggestsum("blk_write_time"),
        biggestsum("wal_records"),
        biggestsum("wal_fpi"),
        biggestsum("wal_bytes")
        ])
            .select_from(base_query)
            .apply_labels()
            .group_by(*(base_columns + [ts])))


def qualstat_base_statdata():
    base_query = text("""
    (
    SELECT srvid, qualid, queryid, dbid, userid, (unnested.records).*
    FROM (
        SELECT pqnh.srvid, pqnh.qualid, pqnh.queryid, pqnh.dbid, pqnh.userid,
          pqnh.coalesce_range, unnest(records) AS records
        FROM powa_qualstats_quals_history pqnh
        WHERE coalesce_range  && tstzrange(:from, :to, '[]')
        AND pqnh.srvid = :server
    ) AS unnested
    WHERE  (records).ts <@ tstzrange(:from, :to, '[]')
    UNION ALL
    SELECT pqnc.srvid, qualid, queryid, dbid, userid, pqnc.ts, pqnc.occurences,
      pqnc.execution_count, pqnc.nbfiltered,
      pqnc.mean_err_estimate_ratio, pqnc.mean_err_estimate_num
    FROM powa_qualstats_quals_history_current pqnc
    WHERE pqnc.ts <@ tstzrange(:from, :to, '[]')
    AND pqnc.srvid = :server
    ) h
    JOIN powa_qualstats_quals pqnh USING (srvid, queryid, qualid)
    """)
    return base_query


def qualstat_getstatdata(srvid, condition=None):
    base_query = qualstat_base_statdata()
    if condition:
        base_query = base_query.where(condition)
    return (select([
        powa_statements.c.srvid,
        column("qualid"),
        powa_statements.c.queryid,
        column("query"),
        powa_statements.c.dbid,
        func.to_json(column("quals")).label("quals"),
        sum(column("execution_count")).label("execution_count"),
        sum(column("occurences")).label("occurences"),
        (sum(column("nbfiltered")) / sum(column("occurences")))
        .label("avg_filter"),
        case(
            [(sum(column("execution_count")) == 0, 0)],
            else_=sum(column("nbfiltered")) /
            cast(sum(column("execution_count")), Numeric) * 100
        ).label("filter_ratio")])
            .select_from(
                join(base_query, powa_statements,
                     and_(powa_statements.c.queryid ==
                          literal_column("pqnh.queryid"),
                          powa_statements.c.srvid ==
                          literal_column("pqnh.srvid")),
                     powa_statements.c.srvid == column("srvid")))
            .group_by(powa_statements.c.srvid, column("qualid"),
                      powa_statements.c.queryid, powa_statements.c.dbid,
                      powa_statements.c.query, column("quals")))


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

BASE_QUERY_KCACHE_SAMPLE_DB = text("""
        powa_databases d,
        LATERAL (
            SELECT *
            FROM (
                SELECT row_number() OVER (ORDER BY kmbq.ts) AS number,
                    count(*) OVER () as total,
                        *
                FROM (
                    SELECT km.ts,
                    sum(km.plan_reads + km.exec_reads) AS reads,
                    sum(km.plan_writes + km.exec_writes) AS writes,
                    sum(km.plan_user_time + km.exec_user_time) AS user_time,
                    sum(km.plan_system_time + km.exec_system_time) AS system_time,
                    sum(km.plan_minflts + km.exec_minflts) AS minflts,
                    sum(km.plan_majflts + km.exec_majflts) AS majflts,
                    -- not maintained on GNU/Linux, and not available on Windows
                    -- sum(km.plan_nswaps + km.exec_nswaps) AS nswaps,
                    -- sum(km.plan_msgsnds + km.exec_msgsnds) AS msgsnds,
                    -- sum(km.plan_msgrcvs + km.exec_msgrcvs) AS msgrcvs,
                    -- sum(km.plan_nsignals + km.exec_nsignals) AS nsignals,
                    sum(km.plan_nvcsws + km.exec_nvcsws) AS nvcsws,
                    sum(km.plan_nivcsws + km.exec_nivcsws) AS nivcsws
                    FROM (
                        SELECT * FROM (
                            SELECT (unnest(metrics)).*
                            FROM powa_kcache_metrics_db kmd
                            WHERE kmd.srvid = d.srvid
                            AND kmd.dbid = d.oid
                            AND kmd.coalesce_range &&
                                tstzrange(:from, :to, '[]')
                        ) his
                        WHERE his.ts <@ tstzrange(:from, :to, '[]')
                        UNION ALL
                        SELECT (metrics).*
                        FROM powa_kcache_metrics_current_db kmcd
                        WHERE kmcd.srvid = d.srvid
                        AND kmcd.dbid = d.oid
                        AND (metrics).ts <@ tstzrange(:from, :to, '[]')
                    ) km
                    GROUP BY km.ts
                ) kmbq
            ) kmn
        WHERE kmn.number % (int8larger(total/(:samples+1),1) ) = 0
        ) kcache
""")


BASE_QUERY_KCACHE_SAMPLE = text("""
        powa_statements s JOIN powa_databases d
            ON d.oid = s.dbid AND d.srvid = s.srvid
            AND s.srvid = :server,
        LATERAL (
            SELECT *
            FROM (
                SELECT row_number() OVER (ORDER BY kmbq.ts) AS number,
                    count(*) OVER () as total,
                        *
                FROM (
                    SELECT km.ts,
                    sum(km.plan_reads + km.exec_reads) AS reads,
                    sum(km.plan_writes + km.exec_writes) AS writes,
                    sum(km.plan_user_time + km.exec_user_time) AS user_time,
                    sum(km.plan_system_time + km.exec_system_time) AS system_time,
                    sum(km.plan_minflts + km.exec_minflts) AS minflts,
                    sum(km.plan_majflts + km.exec_majflts) AS majflts,
                    -- not maintained on GNU/Linux, and not available on Windows
                    -- sum(km.plan_nswaps + km.exec_nswaps) AS nswaps,
                    -- sum(km.plan_msgsnds + km.exec_msgsnds) AS msgsnds,
                    -- sum(km.plan_msgrcvs + km.exec_msgrcvs) AS msgrcvs,
                    -- sum(km.plan_nsignals + km.exec_nsignals) AS nsignals,
                    sum(km.plan_nvcsws + km.exec_nvcsws) AS nvcsws,
                    sum(km.plan_nivcsws + km.exec_nivcsws) AS nivcsws
                    FROM (
                        SELECT * FROM (
                            SELECT (unnest(metrics)).*
                            FROM powa_kcache_metrics km
                            WHERE km.srvid = s.srvid
                            AND km.queryid = s.queryid
                            AND km.dbid = s.dbid
                            AND km.coalesce_range &&
                                tstzrange(:from, :to, '[]')
                        ) his
                        WHERE his.ts <@ tstzrange(:from, :to, '[]')
                        UNION ALL
                        SELECT (metrics).*
                        FROM powa_kcache_metrics_current kmc
                        WHERE kmc.srvid = s.srvid
                        AND kmc.queryid = s.queryid
                        AND kmc.dbid = s.dbid
                        AND (metrics).ts <@ tstzrange(:from, :to, '[]')
                    ) km
                    GROUP BY km.ts
                ) kmbq
            ) kmn
        WHERE kmn.number % (int8larger(total/(:samples+1),1) ) = 0
        ) kcache
""")


def kcache_getstatdata_sample(mode):
    if (mode == "db"):
        base_query = BASE_QUERY_KCACHE_SAMPLE_DB
        base_columns = [literal_column("d.oid").label("dbid"),
                        column("srvid"), column("datname")]
    elif (mode == "query"):
        base_query = BASE_QUERY_KCACHE_SAMPLE
        base_columns = [literal_column("d.oid").label("dbid"),
                        literal_column("d.srvid").label("srvid"),
                        column("datname"), column("queryid"),
                        column("userid")]

    ts = column('ts')
    biggestsum = Biggestsum(base_columns, ts)

    return (select(base_columns + [
        ts,
        biggestsum("reads"),
        biggestsum("writes"),
        biggestsum("user_time"),
        biggestsum("system_time"),
        biggestsum("minflts"),
        biggestsum("majflts"),
        # not maintained on GNU/Linux, and not available on Windows
        # biggestsum("nswaps"),
        # biggestsum("msgsnds"),
        # biggestsum("msgrcvs"),
        # biggestsum("nsignals"),
        biggestsum("nvcsws"),
        biggestsum("nivcsws")
        ])
            .select_from(base_query)
            .apply_labels()
            .group_by(*(base_columns + [ts])))


BASE_QUERY_WAIT_SAMPLE_DB = text("""(
  SELECT d.oid AS dbid, datname, base.*
  FROM powa_databases d,
  LATERAL (
    SELECT *
    FROM (SELECT
      row_number() OVER (
        PARTITION BY dbid ORDER BY waits_history.ts
      ) AS number,
      count(*) OVER (PARTITION BY dbid) AS total,
      srvid,
      ts,
      -- pg 96 columns (bufferpin and lock are included in pg 10+)
      sum(count) FILTER
        (WHERE event_type = 'LWLockNamed') as count_lwlocknamed,
      sum(count) FILTER
        (WHERE event_type = 'LWLockTranche') as count_lwlocktranche,
      -- pg 10+ columns
      sum(count) FILTER (WHERE event_type = 'LWLock') as count_lwlock,
      sum(count) FILTER (WHERE event_type = 'Lock') as count_lock,
      sum(count) FILTER (WHERE event_type = 'BufferPin') as count_bufferpin,
      sum(count) FILTER (WHERE event_type = 'Activity') as count_activity,
      sum(count) FILTER (WHERE event_type = 'Client') as count_client,
      sum(count) FILTER (WHERE event_type = 'Extension') as count_extension,
      sum(count) FILTER (WHERE event_type = 'IPC') as count_ipc,
      sum(count) FILTER (WHERE event_type = 'Timeout') as count_timeout,
      sum(count) FILTER (WHERE event_type = 'IO') as count_io
      FROM (
        SELECT srvid, dbid, event_type, (unnested.records).ts,
          sum((unnested.records).count) AS count
        FROM (
          SELECT wsh.srvid, wsh.dbid, wsh.coalesce_range, event_type,
              unnest(records) AS records
          FROM powa_wait_sampling_history_db wsh
          WHERE coalesce_range && tstzrange(:from, :to,'[]')
          AND wsh.dbid = d.oid
          AND wsh.srvid = :server
        ) AS unnested
        WHERE (records).ts <@ tstzrange(:from, :to, '[]')
        GROUP BY unnested.srvid, unnested.dbid, unnested.event_type,
          (unnested.records).ts
        UNION ALL
        SELECT wshc.srvid, wshc.dbid, event_type, (wshc.record).ts,
            sum((wshc.record).count) AS count
        FROM powa_wait_sampling_history_current_db wshc
        WHERE (wshc.record).ts <@ tstzrange(:from, :to, '[]')
        AND wshc.dbid = d.oid
        AND wshc.srvid = :server
        GROUP BY wshc.srvid, wshc.dbid, wshc.event_type, (wshc.record).ts
      ) AS waits_history
      GROUP BY ts, srvid, dbid
    ) AS wh
    WHERE number % ( int8larger((total)/(:samples+1),1) ) = 0
    AND wh.srvid = d.srvid
  ) AS base
  WHERE d.srvid = :server
) AS by_db
""")


BASE_QUERY_WAIT_SAMPLE = text("""(
  SELECT d.srvid, datname, dbid, queryid, base.*
  FROM powa_statements s
  JOIN powa_databases d ON d.oid = s.dbid
      AND d.srvid = s.srvid,
  LATERAL (
    SELECT *
    FROM (SELECT
      row_number() OVER (
        PARTITION BY queryid ORDER BY waits_history.ts
      ) AS number,
      count(*) OVER (PARTITION BY queryid) AS total,
      ts,
      -- pg 96 columns (bufferpin and lock are included in pg 10+)
      sum(count) FILTER
        (WHERE event_type = 'LWLockNamed') AS count_lwlocknamed,
      sum(count) FILTER
        (WHERE event_type = 'LWLockTranche') AS count_lwlocktranche,
      -- pg 10+ columns
      sum(count) FILTER (WHERE event_type = 'LWLock') AS count_lwlock,
      sum(count) FILTER (WHERE event_type = 'Lock') AS count_lock,
      sum(count) FILTER (WHERE event_type = 'BufferPin') AS count_bufferpin,
      sum(count) FILTER (WHERE event_type = 'Activity') AS count_activity,
      sum(count) FILTER (WHERE event_type = 'Client') AS count_client,
      sum(count) FILTER (WHERE event_type = 'Extension') AS count_extension,
      sum(count) FILTER (WHERE event_type = 'IPC') AS count_ipc,
      sum(count) FILTER (WHERE event_type = 'Timeout') AS count_timeout,
      sum(count) FILTER (WHERE event_type = 'IO') AS count_io
      FROM (
        SELECT unnested.event_type, (unnested.records).ts,
          sum((unnested.records).count) AS count
        FROM (
          SELECT coalesce_range, event_type,
              unnest(records) AS records
          FROM powa_wait_sampling_history wsh
          WHERE coalesce_range && tstzrange(:from, :to, '[]')
          AND wsh.queryid = s.queryid
          AND wsh.srvid = :server
        ) AS unnested
        WHERE (records).ts <@ tstzrange(:from, :to, '[]')
        GROUP BY unnested.event_type, (unnested.records).ts
        UNION ALL
        SELECT wshc.event_type, (wshc.record).ts,
          sum((wshc.record).count) AS count
        FROM powa_wait_sampling_history_current wshc
        WHERE (wshc.record).ts <@ tstzrange(:from, :to, '[]')
        AND wshc.queryid = s.queryid
        AND wshc.srvid = :server
        GROUP BY wshc.srvid, wshc.event_type, (wshc.record).ts
      ) AS waits_history
      GROUP BY waits_history.ts
    ) AS sh
    WHERE number % ( int8larger((total)/(:samples+1),1) ) = 0
  ) AS base
  WHERE d.srvid = :server
) AS by_query
""")


BASE_QUERY_BGWRITER_SAMPLE = text("""
    (SELECT srvid,
      row_number() OVER (ORDER BY bgw_history.ts) AS number,
      count(*) OVER () AS total,
      ts,
      sum(checkpoints_timed) AS checkpoints_timed,
      sum(checkpoints_req) AS checkpoints_req,
      sum(checkpoint_write_time) AS checkpoint_write_time,
      sum(checkpoint_sync_time) AS checkpoint_sync_time,
      sum(buffers_checkpoint) AS buffers_checkpoint,
      sum(buffers_clean) AS buffers_clean,
      sum(maxwritten_clean) AS maxwritten_clean,
      sum(buffers_backend) AS buffers_backend,
      sum(buffers_backend_fsync) AS buffers_backend_fsync,
      sum(buffers_alloc) AS buffers_alloc
      FROM (
        SELECT *
        FROM (
          SELECT srvid, (unnest(records)).*
          FROM powa_stat_bgwriter_history bgwh
          WHERE coalesce_range && tstzrange(:from, :to, '[]')
          AND bgwh.srvid = :server
        ) AS unnested
        WHERE ts <@ tstzrange(:from, :to, '[]')
        UNION ALL
        SELECT srvid, (record).*
        FROM powa_stat_bgwriter_history_current bgwc
        WHERE (bgwc.record).ts <@ tstzrange(:from, :to, '[]')
        AND bgwc.srvid = :server
      ) AS bgw_history
      GROUP BY bgw_history.srvid, bgw_history.ts
    ) AS bgw
    WHERE number % ( int8larger((total)/(:samples+1),1) ) = 0
""")


def powa_base_waitdata_detailed_db():
    base_query = text("""
  powa_databases,
  LATERAL
  (
    SELECT unnested.dbid, unnested.queryid,
      unnested.event_type, unnested.event, (unnested.records).*
    FROM (
      SELECT wsh.dbid, wsh.queryid, wsh.event_type, wsh.event,
        wsh.coalesce_range, unnest(records) AS records
      FROM powa_wait_sampling_history wsh
      WHERE coalesce_range && tstzrange(:from, :to, '[]')
      AND wsh.dbid = powa_databases.oid
      AND wsh.queryid IN (
        SELECT ps.queryid
        FROM powa_statements ps
        WHERE ps.dbid = powa_databases.oid
          AND ps.srvid = :server
      )
      AND wsh.srvid = :server
    ) AS unnested
    WHERE  (records).ts <@ tstzrange(:from, :to, '[]')
    UNION ALL
    SELECT wsc.dbid, wsc.queryid, wsc.event_type, wsc.event, (wsc.record).*
    FROM powa_wait_sampling_history_current wsc
    WHERE (record).ts <@ tstzrange(:from,:to,'[]')
    AND wsc.dbid = powa_databases.oid
    AND wsc.queryid IN (
      SELECT ps.queryid
      FROM powa_statements ps
      WHERE ps.dbid = powa_databases.oid
        AND ps.srvid = :server
    )
    AND wsc.srvid = :server
  ) h
  WHERE powa_databases.srvid = :server
""")
    return base_query


def powa_base_waitdata_db():
    base_query = text("""(
  SELECT powa_databases.srvid, powa_databases.oid as dbid, h.*
  FROM
  powa_databases LEFT JOIN
  (
    SELECT dbid
    FROM powa_wait_sampling_history_db wsh
    WHERE coalesce_range && tstzrange(:from, :to, '[]')
    AND wsh.srvid = :server
    GROUP BY dbid
  ) ranges ON powa_databases.oid = ranges.dbid,
  LATERAL (
    SELECT event_type, event, (unnested1.records).*
    FROM (
      SELECT wsh.event_type, wsh.event, unnest(records) AS records
      FROM powa_wait_sampling_history_db wsh
      WHERE coalesce_range && tstzrange(:from, :to, '[]')
      AND wsh.dbid = ranges.dbid
      AND wsh.srvid = :server
    ) AS unnested1
    WHERE (unnested1.records).ts <@ tstzrange(:from, :to, '[]')
    UNION ALL
    SELECT event_type, event, (wsc.record).*
    FROM powa_wait_sampling_history_current_db wsc
    WHERE (wsc.record).ts <@ tstzrange(:from, :to, '[]')
    AND wsc.dbid = powa_databases.oid
    AND wsc.srvid = :server
  ) AS h
  WHERE powa_databases.srvid = :server
) AS ws_history
    """)
    return base_query


BASE_QUERY_ALL_RELS_SAMPLE_DB = text("""(
  SELECT d.srvid, d.datname, base.*
  FROM powa_databases d,
  LATERAL (
    SELECT *
    FROM (
      SELECT
      row_number() OVER (PARTITION BY dbid ORDER BY ts) AS number,
      count(*) OVER (PARTITION BY dbid ) AS total,
      ar_history.*
      FROM (
        SELECT dbid, (unnested.records).*
        FROM (
          SELECT arh.dbid, unnest(records) AS records
          FROM powa_all_relations_history_db arh
          WHERE arh.dbid = d.oid
          AND arh.srvid = d.srvid
          AND arh.srvid = :server
        ) AS unnested
        WHERE (records).ts <@ tstzrange(:from, :to, '[]')
        UNION ALL
        SELECT dbid, (record).*
        FROM powa_all_relations_history_current_db arhc
        WHERE (record).ts <@ tstzrange(:from, :to, '[]')
        AND arhc.dbid = d.oid
        AND arhc.srvid = d.srvid
        AND arhc.srvid = :server
      ) AS ar_history
    ) AS arh
    WHERE number % (int8larger(total/(:samples+1),1) ) = 0
  ) AS base
  WHERE srvid = :server
) AS by_db
""")


BASE_QUERY_ALL_RELS_SAMPLE = text("""(
  SELECT d.srvid, d.datname,
  CASE WHEN
    (n_tup_ins + n_tup_upd + n_tup_del + n_tup_hot_upd +
     n_liv_tup + n_dead_tup + n_mod_since_analyze) = 0
  THEN 'i'
  ELSE 'r'
  END AS relkind,
  CASE WHEN
    (n_tup_ins + n_tup_upd + n_tup_del + n_tup_hot_upd +
     n_liv_tup + n_dead_tup + n_mod_since_analyze) = 0
  THEN numscan
  ELSE 0
  END AS idx_scan,
  CASE WHEN
    (n_tup_ins + n_tup_upd + n_tup_del + n_tup_hot_upd +
     n_liv_tup + n_dead_tup + n_mod_since_analyze) = 0
  THEN 0
  ELSE numscan
  END AS seq_scan,
  base.*
  FROM
  powa_databases d,
  LATERAL (
    SELECT *
    FROM (
      SELECT
      row_number() OVER (PARTITION BY dbid, relid ORDER BY ts) AS number,
      count(*) OVER (PARTITION BY dbid, relid ) AS total,
      ar_history.*
      FROM (
        SELECT dbid, relid, (unnested.records).*
        FROM (
          SELECT arh.dbid, relid, unnest(records) AS records
          FROM powa_all_relations_history_db arh
          WHERE arh.dbid = d.oid
          AND arh.srvid = d.srvid
          AND arh.srvid = :server
        ) AS unnested
        WHERE (records).ts <@ tstzrange(:from, :to, '[]')
        UNION ALL
        SELECT dbid, relid, (record).*
        FROM powa_all_relations_history_current_db arhc
        WHERE (record).ts <@ tstzrange(:from, :to, '[]')
        AND arhc.dbid = d.oid
        AND arhc.srvid = d.srvid
        AND arhc.srvid = :server
      ) AS ar_history
    ) AS arh
    WHERE number % (int8larger(total/(:samples+1),1) ) = 0
  ) AS base
  WHERE srvid = :server
) AS by_db
    """)


def powa_getwaitdata_detailed_db(srvid):
    base_query = powa_base_waitdata_detailed_db()
    return (select([
        column("srvid"),
        column("queryid"),
        column("dbid"),
        column("datname"),
        column("event_type"),
        column("event"),
        diff("count")
    ])
        .select_from(base_query)
        .group_by(column("srvid"), column("queryid"), column("dbid"),
                  column("datname"), column("event_type"), column("event"))
        .having(max(column("count")) - min(column("count")) > 0))


def powa_getwaitdata_db(srvid):
    base_query = powa_base_waitdata_db()

    return (select([
        column("srvid"),
        column("dbid"),
        column("event_type"),
        column("event"),
        diff("count")
    ])
        .select_from(base_query)
        .group_by(column("srvid"), column("dbid"), column("event_type"),
                  column("event"))
        .having(max(column("count")) - min(column("count")) > 0))


def powa_getwaitdata_sample(srvid, mode):
    if mode == "db":
        base_query = BASE_QUERY_WAIT_SAMPLE_DB
        base_columns = [column("srvid"), column("dbid")]

    elif mode == "query":
        base_query = BASE_QUERY_WAIT_SAMPLE
        base_columns = [column("srvid"), column("dbid"), column("queryid")]

    ts = column('ts')
    biggest = Biggest(base_columns, ts)
    biggestsum = Biggestsum(base_columns, ts)

    return (select(base_columns + [
        ts,
        biggest("ts", '0 s', "mesure_interval"),
        # pg 96 only columns
        biggestsum("count_lwlocknamed"),
        biggestsum("count_lwlocktranche"),
        # pg 10+ columns
        biggestsum("count_lwlock"),
        biggestsum("count_lock"),
        biggestsum("count_bufferpin"),
        biggestsum("count_activity"),
        biggestsum("count_client"),
        biggestsum("count_extension"),
        biggestsum("count_ipc"),
        biggestsum("count_timeout"),
        biggestsum("count_io")])
        .select_from(base_query)
        .apply_labels()
        .group_by(*(base_columns + [ts])))


def powa_get_bgwriter_sample(srvid):
    base_query = BASE_QUERY_BGWRITER_SAMPLE
    base_columns = [column("srvid")]

    ts = column('ts')
    biggest = Biggest(base_columns, ts)
    biggestsum = Biggestsum(base_columns, ts)

    return (select(base_columns + [
            ts,
            biggest("ts", '0 s', "mesure_interval"),
            biggestsum("checkpoints_timed"),
            biggestsum("checkpoints_req"),
            biggestsum("checkpoint_write_time"),
            biggestsum("checkpoint_sync_time"),
            biggestsum("buffers_checkpoint"),
            biggestsum("buffers_clean"),
            biggestsum("maxwritten_clean"),
            biggestsum("buffers_backend"),
            biggestsum("buffers_backend_fsync"),
            biggestsum("buffers_alloc")])
            .select_from(base_query)
            .apply_labels()
            .group_by(*(base_columns + [ts])))


def powa_get_all_tbl_sample(mode, srvid):

    if mode == "db":
        base_query = BASE_QUERY_ALL_RELS_SAMPLE_DB
        base_columns = [column("srvid"), column("dbid"), column("datname")]
    else:
        base_query = BASE_QUERY_ALL_RELS_SAMPLE
        base_columns = [column("srvid"), column("dbid"), column("datname"),
                        column("relid")]

    ts = column('ts')
    biggest = Biggest(base_columns, ts)
    biggestsum = Biggestsum(base_columns, ts)

    return (select(base_columns + [
            ts,
            biggest("ts", '0 s', "mesure_interval"),
            biggestsum("seq_scan"),
            biggestsum("idx_scan"),
            biggestsum("tup_returned"),
            biggestsum("tup_fetched"),
            biggestsum("n_tup_ins"),
            biggestsum("n_tup_upd"),
            biggestsum("n_tup_del"),
            biggestsum("n_tup_hot_upd"),
            biggestsum("vacuum_count"),
            biggestsum("autovacuum_count"),
            biggestsum("analyze_count"),
            biggestsum("autoanalyze_count")])
            .select_from(base_query)
            .apply_labels()
            .group_by(*(base_columns + [ts])))


def get_config_changes(restrict_database=False):
    restrict_db = ""
    if (restrict_database):
        restrict_db = "AND (d.datname = :database OR h.setdatabase = 0)"

    return text("""SELECT * FROM
(
  WITH src AS (
    select ts, name,
    lag(setting_pretty) OVER (PARTITION BY name ORDER BY ts) AS prev_val,
    setting_pretty AS new_val,
    lag(is_dropped) OVER (PARTITION BY name ORDER BY ts) AS prev_is_dropped,
    is_dropped as is_dropped
    FROM public.pg_track_settings_history h
    WHERE srvid = :server
    AND ts <= :to
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
  WHERE ts >= :from AND ts <= :to
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
    FROM public.pg_track_db_role_settings_history h
    LEFT JOIN public.powa_databases d
      ON d.srvid = h.srvid
      AND d.oid = h.setdatabase
    WHERE h.srvid = :server
    %(restrict_db)s
    AND ts <= :to
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
  WHERE ts >= :from AND ts <= :to
) AS rds

UNION ALL

SELECT extract("epoch" FROM ts) AS ts, 'reboot' AS kind,
NULL AS data
FROM public.pg_reboot AS r
WHERE r.srvid = :server
AND r.ts>= :from
AND r.ts <= :to
ORDER BY ts""" % {'restrict_db': restrict_db})
