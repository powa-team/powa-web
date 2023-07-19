"""
Functions to generate the queries used in the various graphs components
"""
class Biggest(object):

    def __init__(self, base_columns, order_by):
        if type(base_columns) is str:
            base_columns = [base_columns]
        if type(order_by) is str:
            order_by = [order_by]

        self.base_columns = base_columns
        self.order_by = order_by

    def __call__(self, var, minval=0, label=None):
        label = label or var

        sql = "greatest(lead({var})" \
              " OVER (PARTITION BY {partitionby} ORDER BY {orderby})" \
              " - {var}," \
              " {minval})" \
              " AS {alias}".format(
                  var=var,
                  orderby=', '.join(self.order_by),
                  partitionby=', '.join(self.base_columns),
                  minval=minval,
                  alias=label
              )
        return sql


class Biggestsum(object):

    def __init__(self, base_columns, order_by):
        if type(base_columns) is str:
            base_columns = [base_columns]
        if type(order_by) is str:
            order_by = [order_by]

        self.base_columns = base_columns
        self.order_by = order_by

    def __call__(self, var, minval=0, label=None):
        label = label or var

        sql = "greatest(lead(sum({var}))"\
              " OVER (PARTITION BY {partitionby} ORDER BY {orderby})" \
              " - sum({var})," \
              " {minval})" \
              " AS {alias}".format(
                  var=var,
                  orderby=', '.join(self.order_by),
                  partitionby=', '.join(self.base_columns),
                  minval=minval,
                  alias=label
              )
        return sql


BASE_QUERY_SAMPLE_DB = """(
  SELECT d.srvid, d.datname, base.* FROM {powa}.powa_databases d,
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
          FROM {powa}.powa_statements_history_db psh
          WHERE coalesce_range && tstzrange(%(from)s, %(to)s,'[]')
          AND psh.dbid = d.oid
          AND psh.srvid = d.srvid
          AND psh.srvid = %(server)s
        ) AS unnested
        WHERE (records).ts <@ tstzrange(%(from)s, %(to)s, '[]')
        UNION ALL
        SELECT dbid, (record).*
        FROM {powa}.powa_statements_history_current_db
        WHERE  (record).ts <@ tstzrange(%(from)s, %(to)s, '[]')
        AND dbid = d.oid
        AND srvid = d.srvid
        AND srvid = %(server)s
      ) AS statements_history
    ) AS sh
    WHERE number %% ( int8larger((total)/(%(samples)s+1),1) ) = 0
  ) AS base
  WHERE srvid = %(server)s
) AS by_db"""


BASE_QUERY_SAMPLE = """(
  SELECT powa_statements.srvid, datname, dbid, queryid, userid, base.*
  FROM {powa}.powa_statements
  JOIN {powa}.powa_databases ON powa_databases.oid = powa_statements.dbid
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
                  FROM {powa}.powa_statements_history psh
                  WHERE coalesce_range && tstzrange(%(from)s, %(to)s, '[]')
                  AND psh.queryid = powa_statements.queryid
                  AND psh.userid = powa_statements.userid
                  AND psh.srvid = %(server)s
              ) AS unnested
              WHERE  (records).ts <@ tstzrange(%(from)s, %(to)s, '[]')
              UNION ALL
              SELECT (record).*
              FROM {powa}.powa_statements_history_current phc
              WHERE (record).ts <@ tstzrange(%(from)s, %(to)s, '[]')
              AND phc.queryid = powa_statements.queryid
              AND phc.userid = powa_statements.userid
              AND phc.srvid = %(server)s
          ) AS statements_history
      ) AS sh
      WHERE number %% ( int8larger((total)/(%(samples)s+1),1) ) = 0
  ) AS base
  WHERE powa_statements.srvid = %(server)s
) AS by_query

"""


def powa_getstatdata_sample(mode, predicates=[]):
    """
    predicates is an optional array of plain-text predicates.
    """
    if mode == "db":
        base_query = BASE_QUERY_SAMPLE_DB
        base_columns = ["srvid", "dbid"]

    elif mode == "query":
        base_query = BASE_QUERY_SAMPLE
        base_columns = ["srvid", "dbid", "queryid", "userid"]

    biggest = Biggest(base_columns, 'ts')
    biggestsum = Biggestsum(base_columns, 'ts')

    where = ' AND '.join(predicates)
    if where != '':
        where = ' AND ' + where

    cols = base_columns + [
        'ts',
        biggest("ts", "'0 s'", "mesure_interval"),
        biggestsum("calls"),
        biggestsum("total_plan_time", label="plantime"),
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
    ]

    return """SELECT {cols}
    FROM {base_query}
    WHERE srvid = %(server)s
    {where}
    GROUP BY {base_columns}, ts""".format(
        cols=', '.join(cols),
        base_query=base_query,
        where=where,
        base_columns=', '.join(base_columns)
    )


BASE_QUERY_KCACHE_SAMPLE_DB = """
        {powa}.powa_databases d,
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
                            FROM {powa}.powa_kcache_metrics_db kmd
                            WHERE kmd.srvid = d.srvid
                            AND kmd.dbid = d.oid
                            AND kmd.coalesce_range &&
                                tstzrange(%(from)s, %(to)s, '[]')
                        ) his
                        WHERE his.ts <@ tstzrange(%(from)s, %(to)s, '[]')
                        UNION ALL
                        SELECT (metrics).*
                        FROM {powa}.powa_kcache_metrics_current_db kmcd
                        WHERE kmcd.srvid = d.srvid
                        AND kmcd.dbid = d.oid
                        AND (metrics).ts <@ tstzrange(%(from)s, %(to)s, '[]')
                    ) km
                    GROUP BY km.ts
                ) kmbq
            ) kmn
        WHERE kmn.number %% (int8larger(total/(%(samples)s+1),1) ) = 0
        ) kcache
"""


BASE_QUERY_KCACHE_SAMPLE = """
        {powa}.powa_statements s JOIN {powa}.powa_databases d
            ON d.oid = s.dbid AND d.srvid = s.srvid
            AND s.srvid = %(server)s,
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
                            FROM {powa}.powa_kcache_metrics km
                            WHERE km.srvid = s.srvid
                            AND km.queryid = s.queryid
                            AND km.dbid = s.dbid
                            AND km.coalesce_range &&
                                tstzrange(%(from)s, %(to)s, '[]')
                        ) his
                        WHERE his.ts <@ tstzrange(%(from)s, %(to)s, '[]')
                        UNION ALL
                        SELECT (metrics).*
                        FROM {powa}.powa_kcache_metrics_current kmc
                        WHERE kmc.srvid = s.srvid
                        AND kmc.queryid = s.queryid
                        AND kmc.dbid = s.dbid
                        AND (metrics).ts <@ tstzrange(%(from)s, %(to)s, '[]')
                    ) km
                    GROUP BY km.ts
                ) kmbq
            ) kmn
        WHERE kmn.number %% (int8larger(total/(%(samples)s+1),1) ) = 0
        ) kcache
"""


def kcache_getstatdata_sample(mode, predicates=[]):
    """
    predicates is an optional array of plain-text predicates.
    """
    if (mode == "db"):
        base_query = BASE_QUERY_KCACHE_SAMPLE_DB
        base_columns = ["d.oid AS dbid", "srvid, datname"]
        groupby_columns = "d.oid, srvid, datname"
    elif (mode == "query"):
        base_query = BASE_QUERY_KCACHE_SAMPLE
        base_columns = ["d.oid AS dbid", "d.srvid", "datname", "queryid",
                        "userid"]
        groupby_columns = "d.oid, d.srvid, datname, queryid, userid"

    biggestsum = Biggestsum(groupby_columns, "ts")

    where = ' AND '.join(predicates)
    if where != '':
        where = ' AND ' + where

    base_columns.extend([
        "ts",
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
        biggestsum("nivcsws"),
    ])

    return """SELECT {base_columns}
    FROM {base_query}
    WHERE d.srvid = %(server)s
    {where}
    GROUP BY {groupby_columns}, ts""".format(
        base_columns=', '.join(base_columns),
        groupby_columns=groupby_columns,
        where=where,
        base_query=base_query
    )


BASE_QUERY_WAIT_SAMPLE_DB = """(
  SELECT d.oid AS dbid, datname, base.*
  FROM {powa}.powa_databases d,
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
          FROM {powa}.powa_wait_sampling_history_db wsh
          WHERE coalesce_range && tstzrange(%(from)s, %(to)s,'[]')
          AND wsh.dbid = d.oid
          AND wsh.srvid = %(server)s
        ) AS unnested
        WHERE (records).ts <@ tstzrange(%(from)s, %(to)s, '[]')
        GROUP BY unnested.srvid, unnested.dbid, unnested.event_type,
          (unnested.records).ts
        UNION ALL
        SELECT wshc.srvid, wshc.dbid, event_type, (wshc.record).ts,
            sum((wshc.record).count) AS count
        FROM {powa}.powa_wait_sampling_history_current_db wshc
        WHERE (wshc.record).ts <@ tstzrange(%(from)s, %(to)s, '[]')
        AND wshc.dbid = d.oid
        AND wshc.srvid = %(server)s
        GROUP BY wshc.srvid, wshc.dbid, wshc.event_type, (wshc.record).ts
      ) AS waits_history
      GROUP BY ts, srvid, dbid
    ) AS wh
    WHERE number %% ( int8larger((total)/(%(samples)s+1),1) ) = 0
    AND wh.srvid = d.srvid
  ) AS base
  WHERE d.srvid = %(server)s
) AS by_db
"""


BASE_QUERY_WAIT_SAMPLE = """(
  SELECT d.srvid, datname, dbid, queryid, base.*
  FROM {powa}.powa_statements s
  JOIN {powa}.powa_databases d ON d.oid = s.dbid
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
          FROM {powa}.powa_wait_sampling_history wsh
          WHERE coalesce_range && tstzrange(%(from)s, %(to)s, '[]')
          AND wsh.queryid = s.queryid
          AND wsh.srvid = %(server)s
        ) AS unnested
        WHERE (records).ts <@ tstzrange(%(from)s, %(to)s, '[]')
        GROUP BY unnested.event_type, (unnested.records).ts
        UNION ALL
        SELECT wshc.event_type, (wshc.record).ts,
          sum((wshc.record).count) AS count
        FROM {powa}.powa_wait_sampling_history_current wshc
        WHERE (wshc.record).ts <@ tstzrange(%(from)s, %(to)s, '[]')
        AND wshc.queryid = s.queryid
        AND wshc.srvid = %(server)s
        GROUP BY wshc.srvid, wshc.event_type, (wshc.record).ts
      ) AS waits_history
      GROUP BY waits_history.ts
    ) AS sh
    WHERE number %% ( int8larger((total)/(%(samples)s+1),1) ) = 0
  ) AS base
  WHERE d.srvid = %(server)s
) AS by_query
"""


# Note about xid calculations: we store 32b xids and those wraparounds, so we
# have to account for that.  At the same time, cur_txid is retrieved before
# executing the query fetching pg_stat_activity information.  On some busy
# system, this could take quite some time and nothing prevents xid from being
# assigned during that time, so to avoid returning negative number we
# arbitrarily choose 100k transactions as a cutoff point to distinguish
# wraparound vs really negative numbers.
# For any number less than -100k, we assume this is because cur_txid
# wraparound and the xid didn't, in which case we compute the actual value,
# knowing that the first 3 xid are reserved and can never be assigned, and that
# the highest transaction id is 2^32.
def BASE_QUERY_PGSA_SAMPLE(per_db=False):
    if (per_db):
        extra = """JOIN {powa}.powa_catalog_databases d
            ON d.oid = pgsa_history.datid
        WHERE d.datname = %(database)s"""
    else:
        extra = ""

    # We use dense_rank() as we need ALL the records for a specific ts
    return """
    (SELECT pgsa_history.srvid,
      dense_rank() OVER (ORDER BY pgsa_history.ts) AS number,
      count(*) OVER () AS total,
      ts,
      datid,
      cur_txid,
      backend_xid,
      backend_xmin,
      backend_start,
      xact_start,
      query_start,
      state,
      leader_pid
      FROM (
        SELECT *
        FROM (
          SELECT srvid, (unnest(records)).*
          FROM {{powa}}.powa_stat_activity_history pgsah
          WHERE coalesce_range && tstzrange(%(from)s, %(to)s, '[]')
          AND pgsah.srvid = %(server)s
        ) AS unnested
        WHERE ts <@ tstzrange(%(from)s, %(to)s, '[]')
        UNION ALL
        SELECT srvid, (record).*
        FROM {{powa}}.powa_stat_activity_history_current pgsac
        WHERE (pgsac.record).ts <@ tstzrange(%(from)s, %(to)s, '[]')
        AND pgsac.srvid = %(server)s
      ) AS pgsa_history
      {extra}
    ) AS pgsa
    WHERE number %% ( int8larger((total)/(%(samples)s+1),1) ) = 0
""".format(extra=extra)


BASE_QUERY_BGWRITER_SAMPLE = """
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
          FROM {powa}.powa_stat_bgwriter_history bgwh
          WHERE coalesce_range && tstzrange(%(from)s, %(to)s, '[]')
          AND bgwh.srvid = %(server)s
        ) AS unnested
        WHERE ts <@ tstzrange(%(from)s, %(to)s, '[]')
        UNION ALL
        SELECT srvid, (record).*
        FROM {powa}.powa_stat_bgwriter_history_current bgwc
        WHERE (bgwc.record).ts <@ tstzrange(%(from)s, %(to)s, '[]')
        AND bgwc.srvid = %(server)s
      ) AS bgw_history
      GROUP BY bgw_history.srvid, bgw_history.ts
    ) AS bgw
    WHERE number %% ( int8larger((total)/(%(samples)s+1),1) ) = 0
"""


BASE_QUERY_ALL_IDXS_SAMPLE_DB = """(
  SELECT d.srvid, d.datname, base.*
  FROM {powa}.powa_databases d,
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
          SELECT ari.dbid, unnest(records) AS records
          FROM {powa}.powa_all_indexes_history_db ari
          WHERE ari.dbid = d.oid
          AND ari.srvid = d.srvid
          AND ari.srvid = %(server)s
        ) AS unnested
        WHERE (records).ts <@ tstzrange(%(from)s, %(to)s, '[]')
        UNION ALL
        SELECT dbid, (record).*
        FROM {powa}.powa_all_indexes_history_current_db aric
        WHERE (record).ts <@ tstzrange(%(from)s, %(to)s, '[]')
        AND aric.dbid = d.oid
        AND aric.srvid = d.srvid
        AND aric.srvid = %(server)s
      ) AS ar_history
    ) AS ari
    WHERE number %% (int8larger(total/(%(samples)s+1),1) ) = 0
  ) AS base
  WHERE srvid = %(server)s
) AS by_db
"""


BASE_QUERY_ALL_IDXS_SAMPLE = """(
  SELECT d.srvid, d.datname,
  base.*
  FROM
  {powa}.powa_databases d,
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
          SELECT ari.dbid, relid, unnest(records) AS records
          FROM {powa}.powa_all_indexes_history_db ari
          WHERE ari.dbid = d.oid
          AND ari.srvid = d.srvid
          AND ari.srvid = %(server)s
        ) AS unnested
        WHERE (records).ts <@ tstzrange(%(from)s, %(to)s, '[]')
        UNION ALL
        SELECT dbid, relid, (record).*
        FROM {powa}.powa_all_indexes_history_current_db aric
        WHERE (record).ts <@ tstzrange(%(from)s, %(to)s, '[]')
        AND aric.dbid = d.oid
        AND aric.srvid = d.srvid
        AND aric.srvid = %(server)s
      ) AS ar_history
    ) AS ari
    WHERE number %% (int8larger(total/(%(samples)s+1),1) ) = 0
  ) AS base
  WHERE srvid = %(server)s
) AS by_db
    """


BASE_QUERY_ALL_TBLS_SAMPLE_DB = """(
  SELECT d.srvid, d.datname, base.*
  FROM {powa}.powa_databases d,
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
          FROM {powa}.powa_all_tables_history_db arh
          WHERE arh.dbid = d.oid
          AND arh.srvid = d.srvid
          AND arh.srvid = %(server)s
        ) AS unnested
        WHERE (records).ts <@ tstzrange(%(from)s, %(to)s, '[]')
        UNION ALL
        SELECT dbid, (record).*
        FROM {powa}.powa_all_tables_history_current_db arhc
        WHERE (record).ts <@ tstzrange(%(from)s, %(to)s, '[]')
        AND arhc.dbid = d.oid
        AND arhc.srvid = d.srvid
        AND arhc.srvid = %(server)s
      ) AS ar_history
    ) AS arh
    WHERE number %% (int8larger(total/(%(samples)s+1),1) ) = 0
  ) AS base
  WHERE srvid = %(server)s
) AS by_db
"""


BASE_QUERY_ALL_TBLS_SAMPLE = """(
  SELECT d.srvid, d.datname,
  base.*
  FROM
  {powa}.powa_databases d,
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
          FROM {powa}.powa_all_tables_history_db arh
          WHERE arh.dbid = d.oid
          AND arh.srvid = d.srvid
          AND arh.srvid = %(server)s
        ) AS unnested
        WHERE (records).ts <@ tstzrange(%(from)s, %(to)s, '[]')
        UNION ALL
        SELECT dbid, relid, (record).*
        FROM {powa}.powa_all_tables_history_current_db arhc
        WHERE (record).ts <@ tstzrange(%(from)s, %(to)s, '[]')
        AND arhc.dbid = d.oid
        AND arhc.srvid = d.srvid
        AND arhc.srvid = %(server)s
      ) AS ar_history
    ) AS arh
    WHERE number %% (int8larger(total/(%(samples)s+1),1) ) = 0
  ) AS base
  WHERE srvid = %(server)s
) AS by_db
    """


BASE_QUERY_USER_FCTS_SAMPLE_DB = """(
  SELECT d.srvid, d.datname, base.*
  FROM {powa}.powa_databases d,
  LATERAL (
    SELECT *
    FROM (
      SELECT
      row_number() OVER (PARTITION BY dbid ORDER BY ts) AS number,
      count(*) OVER (PARTITION BY dbid ) AS total,
      af_history.*
      FROM (
        SELECT dbid, (unnested.records).*
        FROM (
          SELECT afh.dbid, unnest(records) AS records
          FROM {powa}.powa_user_functions_history_db afh
          WHERE afh.dbid = d.oid
          AND afh.srvid = d.srvid
          AND afh.srvid = %(server)s
        ) AS unnested
        WHERE (records).ts <@ tstzrange(%(from)s, %(to)s, '[]')
        UNION ALL
        SELECT dbid, (record).*
        FROM {powa}.powa_user_functions_history_current_db afhc
        WHERE (record).ts <@ tstzrange(%(from)s, %(to)s, '[]')
        AND afhc.dbid = d.oid
        AND afhc.srvid = d.srvid
        AND afhc.srvid = %(server)s
      ) AS af_history
    ) AS afh
    WHERE number %% (int8larger(total/(%(samples)s+1),1) ) = 0
  ) AS base
  WHERE srvid = %(server)s
) AS by_db
"""


BASE_QUERY_USER_FCTS_SAMPLE = """(
  SELECT d.srvid, d.datname,
  base.*
  FROM
  {powa}.powa_databases d,
  LATERAL (
    SELECT *
    FROM (
      SELECT
      row_number() OVER (PARTITION BY dbid, funcid ORDER BY ts) AS number,
      count(*) OVER (PARTITION BY dbid, funcid ) AS total,
      af_history.*
      FROM (
        SELECT dbid, funcid, (unnested.records).*
        FROM (
          SELECT afh.dbid, funcid, unnest(records) AS records
          FROM {powa}.powa_user_functions_history_db afh
          WHERE afh.dbid = d.oid
          AND afh.srvid = d.srvid
          AND afh.srvid = %(server)s
        ) AS unnested
        WHERE (records).ts <@ tstzrange(%(from)s, %(to)s, '[]')
        UNION ALL
        SELECT dbid, funcid, (record).*
        FROM {powa}.powa_user_functions_history_current_db afhc
        WHERE (record).ts <@ tstzrange(%(from)s, %(to)s, '[]')
        AND afhc.dbid = d.oid
        AND afhc.srvid = d.srvid
        AND afhc.srvid = %(server)s
      ) AS af_history
    ) AS afh
    WHERE number %% (int8larger(total/(%(samples)s+1),1) ) = 0
  ) AS base
  WHERE srvid = %(server)s
) AS by_db
    """


def powa_getwaitdata_sample(mode, predicates=[]):
    """
    predicates is an optional array of plain-text predicates.
    """
    if mode == "db":
        base_query = BASE_QUERY_WAIT_SAMPLE_DB
        base_columns = ["srvid", "dbid"]

    elif mode == "query":
        base_query = BASE_QUERY_WAIT_SAMPLE
        base_columns = ["srvid", "dbid", "queryid"]

    biggest = Biggest(base_columns, 'ts')
    biggestsum = Biggestsum(base_columns, 'ts')

    where = ' AND '.join(predicates)
    if where != '':
        where = ' AND ' + where

    all_cols = base_columns + [
        "ts",
        biggest("ts", "'0 s'", "mesure_interval"),
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
        biggestsum("count_io"),
    ]

    return """SELECT {all_cols}
    FROM {base_query}
    WHERE srvid = %(server)s
    {where}
    GROUP BY {base_columns}, ts""".format(
        all_cols=', '.join(all_cols),
        base_columns=', '.join(base_columns),
        base_query=base_query,
        where=where
    )


def powa_get_pgsa_sample(per_db=False):
    base_query = BASE_QUERY_PGSA_SAMPLE(per_db)
    base_columns = ["srvid"]

    def txid_age(field):
        ref = "cur_txid"
        alias = field + "_age"

        return """CASE
        WHEN {ref}::text::bigint - {field}::text::bigint < -100000
          THEN ({ref}::text::bigint - 3) +
            ((4::bigint * 1024 * 1024 * 1024) - {field}::text::bigint)
        WHEN {ref}::text::bigint - {field}::text::bigint <= 0
          THEN 0
        ELSE
          {ref}::text::bigint - {field}::text::bigint
      END AS {alias}""".format(field=field, ref=ref, alias=alias)

    def ts_get_sec(field):
        alias = field + "_age"
        return """extract(epoch FROM (ts - {f})) * 1000 AS {a}""".format(
                f=field,
                a=alias)

    all_cols = base_columns + [
        "ts",
        "datid",
        txid_age("backend_xid"),     # backend_xid_age
        txid_age("backend_xmin"),    # backend_xmin_age
        ts_get_sec("backend_start"), # backend_start_age
        ts_get_sec("xact_start"),    # xact_start_age
        ts_get_sec("query_start"),   # query_start_age
        "state",
        "leader_pid",
    ]

    return """SELECT {all_cols}
    FROM {base_query}""".format(
        all_cols=', '.join(all_cols),
        base_columns=', '.join(base_columns),
        base_query=base_query
    )


def powa_get_bgwriter_sample():
    base_query = BASE_QUERY_BGWRITER_SAMPLE
    base_columns = ["srvid"]

    biggest = Biggest(base_columns, 'ts')
    biggestsum = Biggestsum(base_columns, 'ts')

    all_cols = base_columns + [
        "ts",
        biggest("ts", "'0 s'", "mesure_interval"),
        biggestsum("checkpoints_timed"),
        biggestsum("checkpoints_req"),
        biggestsum("checkpoint_write_time"),
        biggestsum("checkpoint_sync_time"),
        biggestsum("buffers_checkpoint"),
        biggestsum("buffers_clean"),
        biggestsum("maxwritten_clean"),
        biggestsum("buffers_backend"),
        biggestsum("buffers_backend_fsync"),
        biggestsum("buffers_alloc"),
    ]

    return """SELECT {all_cols}
    FROM {base_query}
    GROUP BY {base_columns}, ts""".format(
        all_cols=', '.join(all_cols),
        base_columns=', '.join(base_columns),
        base_query=base_query
    )


def powa_get_all_idx_sample(mode):

    if mode == "db":
        base_query = BASE_QUERY_ALL_IDXS_SAMPLE_DB
        base_columns = ["srvid", "dbid", "datname"]
    else:
        base_query = BASE_QUERY_ALL_IDXS_SAMPLE
        base_columns = ["srvid", "dbid", "datname", "relid"]

    biggest = Biggest(base_columns, 'ts')
    biggestsum = Biggestsum(base_columns, 'ts')

    all_cols = base_columns + [
        "ts",
        biggest("ts", "'0 s'", "mesure_interval"),
        "sum(idx_size) AS idx_size",
        biggestsum("idx_scan"),
        biggestsum("idx_tup_read"),
        biggestsum("idx_tup_fetch"),
        biggestsum("idx_blks_read"),
        biggestsum("idx_blks_hit"),
    ]

    return """SELECT {all_cols}
        FROM {base_query}
        WHERE srvid = %(server)s
        GROUP BY {base_columns}, ts""".format(
            all_cols=', '.join(all_cols),
            base_columns=', '.join(base_columns),
            base_query=base_query
    )


def powa_get_all_tbl_sample(mode):

    if mode == "db":
        base_query = BASE_QUERY_ALL_TBLS_SAMPLE_DB
        base_columns = ["srvid", "dbid", "datname"]
    else:
        base_query = BASE_QUERY_ALL_TBLS_SAMPLE
        base_columns = ["srvid", "dbid", "datname", "relid"]

    biggest = Biggest(base_columns, 'ts')
    biggestsum = Biggestsum(base_columns, 'ts')

    all_cols = base_columns + [
        "ts",
        biggest("ts", "'0 s'", "mesure_interval"),
        "sum(tbl_size) AS tbl_size",
        biggestsum("seq_scan"),
        biggestsum("idx_scan"),
        biggestsum("n_tup_ins"),
        biggestsum("n_tup_upd"),
        biggestsum("n_tup_del"),
        biggestsum("n_tup_hot_upd"),
        biggestsum("vacuum_count"),
        biggestsum("autovacuum_count"),
        biggestsum("analyze_count"),
        biggestsum("autoanalyze_count"),
    ]

    return """SELECT {all_cols}
        FROM {base_query}
        WHERE srvid = %(server)s
        GROUP BY {base_columns}, ts""".format(
            all_cols=', '.join(all_cols),
            base_columns=', '.join(base_columns),
            base_query=base_query
    )


def powa_get_user_fct_sample(mode):

    if mode == "db":
        base_query = BASE_QUERY_USER_FCTS_SAMPLE_DB
        base_columns = ["srvid", "dbid", "datname"]
    else:
        base_query = BASE_QUERY_USER_FCTS_SAMPLE
        base_columns = ["srvid", "dbid", "datname", "funcid"]

    biggest = Biggest(base_columns, 'ts')
    biggestsum = Biggestsum(base_columns, 'ts')

    all_cols = base_columns + [
        "ts",
        biggest("ts", "'0 s'", "mesure_interval"),
        biggestsum("calls"),
        biggestsum("total_time"),
        biggestsum("self_time"),
    ]

    return """SELECT {all_cols}
        FROM {base_query}
        WHERE srvid = %(server)s
        GROUP BY {base_columns}, ts""".format(
            all_cols=', '.join(all_cols),
            base_columns=', '.join(base_columns),
            base_query=base_query
    )
