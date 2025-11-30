"""
Functions to generate the queries used in the various graphs components
"""


def wal_to_num(walname):
    """
    Extracts the sequence number from the given WAL file name, similarly to
    pg_split_walfile_name().  It's assuming a 16MB wal_segment_size.
    """
    return """(('x' || substr({walname}, 9, 8))::bit(32)::bigint
 * '4294967296'::bigint / 16777216
 + ('x' || substr({walname}, 17, 8))::bit(32)::bigint)""".format(
        walname=walname
    )


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

        sql = (
            "greatest(lead({var})"
            " OVER (PARTITION BY {partitionby} ORDER BY {orderby})"
            " - {var},"
            " {minval})"
            " AS {alias}".format(
                var=var,
                orderby=", ".join(self.order_by),
                partitionby=", ".join(self.base_columns),
                minval=minval,
                alias=label,
            )
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

        sql = (
            "greatest(lead(sum({var}))"
            " OVER (PARTITION BY {partitionby} ORDER BY {orderby})"
            " - sum({var}),"
            " {minval})"
            " AS {alias}".format(
                var=var,
                orderby=", ".join(self.order_by),
                partitionby=", ".join(self.base_columns),
                minval=minval,
                alias=label,
            )
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

    biggest = Biggest(base_columns, "ts")
    biggestsum = Biggestsum(base_columns, "ts")

    where = " AND ".join(predicates)
    if where != "":
        where = " AND " + where

    cols = base_columns + [
        "ts",
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
        biggestsum("shared_blk_read_time"),
        biggestsum("shared_blk_write_time"),
        biggestsum("local_blk_read_time"),
        biggestsum("local_blk_write_time"),
        biggestsum("temp_blk_read_time"),
        biggestsum("temp_blk_write_time"),
        biggestsum("wal_records"),
        biggestsum("wal_fpi"),
        biggestsum("wal_bytes"),
        biggestsum("jit_functions"),
        biggestsum("jit_generation_time"),
        biggestsum("jit_inlining_count"),
        biggestsum("jit_inlining_time"),
        biggestsum("jit_optimization_count"),
        biggestsum("jit_optimization_time"),
        biggestsum("jit_emission_count"),
        biggestsum("jit_emission_time"),
        biggestsum("jit_deform_count"),
        biggestsum("jit_deform_time"),
    ]

    return """SELECT {cols}
    FROM {base_query}
    WHERE srvid = %(server)s
    {where}
    GROUP BY {base_columns}, ts""".format(
        cols=", ".join(cols),
        base_query=base_query,
        where=where,
        base_columns=", ".join(base_columns),
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
    if mode == "db":
        base_query = BASE_QUERY_KCACHE_SAMPLE_DB
        base_columns = ["d.oid AS dbid", "srvid, datname"]
        groupby_columns = "d.oid, srvid, datname"
    elif mode == "query":
        base_query = BASE_QUERY_KCACHE_SAMPLE
        base_columns = [
            "d.oid AS dbid",
            "d.srvid",
            "datname",
            "queryid",
            "userid",
        ]
        groupby_columns = "d.oid, d.srvid, datname, queryid, userid"

    biggestsum = Biggestsum(groupby_columns, "ts")

    where = " AND ".join(predicates)
    if where != "":
        where = " AND " + where

    base_columns.extend(
        [
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
        ]
    )

    return """SELECT {base_columns}
    FROM {base_query}
    WHERE d.srvid = %(server)s
    {where}
    GROUP BY {groupby_columns}, ts""".format(
        base_columns=", ".join(base_columns),
        groupby_columns=groupby_columns,
        where=where,
        base_query=base_query,
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
    if per_db:
        extra = """JOIN {powa}.powa_databases d
            ON d.oid = pgsa_history.datid and d.srvid = pgsa_history.srvid
        WHERE d.datname = %(database)s"""
    else:
        extra = ""

    # We use dense_rank() as we need ALL the records for a specific ts
    return """
    (
      SELECT *, max(number) OVER () AS total
      FROM (
        SELECT pgsa_history.srvid,
          dense_rank() OVER (ORDER BY pgsa_history.ts) AS number,
          ts,
          clock_ts,
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
          AND backend_type <> 'autovacuum worker'
          UNION ALL
          SELECT srvid, (record).*
          FROM {{powa}}.powa_stat_activity_history_current pgsac
          WHERE (pgsac.record).ts <@ tstzrange(%(from)s, %(to)s, '[]')
          AND pgsac.srvid = %(server)s
          AND (record).backend_type <> 'autovacuum worker'
          ) AS pgsa_history
          {extra}
      ) AS ranking
    ) AS pgsa
    WHERE number %% ( int8larger((total)/(%(samples)s+1),1) ) = 0
""".format(extra=extra)


BASE_QUERY_ARCHIVER_SAMPLE = """
    (SELECT srvid,
      row_number() OVER (ORDER BY arc_history.ts) AS number,
      count(*) OVER () AS total,
      ts,
      current_wal,
      archived_count,
      last_archived_wal,
      last_archived_time,
      failed_count,
      last_failed_wal,
      last_failed_time
      FROM (
        SELECT *
        FROM (
          SELECT srvid, (unnest(records)).*
          FROM {powa}.powa_stat_archiver_history arch
          WHERE coalesce_range && tstzrange(%(from)s, %(to)s, '[]')
          AND arch.srvid = %(server)s
        ) AS unnested
        WHERE ts <@ tstzrange(%(from)s, %(to)s, '[]')
        UNION ALL
        SELECT srvid, (record).*
        FROM {powa}.powa_stat_archiver_history_current arcc
        WHERE (arcc.record).ts <@ tstzrange(%(from)s, %(to)s, '[]')
        AND arcc.srvid = %(server)s
      ) AS arc_history
    ) AS arc
    WHERE number %% ( int8larger((total)/(%(samples)s+1),1) ) = 0
"""


BASE_QUERY_BGWRITER_SAMPLE = """
    (SELECT srvid,
      row_number() OVER (ORDER BY bgw_history.ts) AS number,
      count(*) OVER () AS total,
      ts,
      buffers_clean,
      maxwritten_clean,
      buffers_backend,
      buffers_backend_fsync,
      buffers_alloc
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
    ) AS bgw
    WHERE number %% ( int8larger((total)/(%(samples)s+1),1) ) = 0
"""


BASE_QUERY_CHECKPOINTER_SAMPLE = """
    (SELECT srvid,
      row_number() OVER (ORDER BY cpt_history.ts) AS number,
      count(*) OVER () AS total,
      ts,
      num_timed,
      num_requested,
      write_time,
      sync_time,
      buffers_written
      FROM (
        SELECT *
        FROM (
          SELECT srvid, (unnest(records)).*
          FROM {powa}.powa_stat_checkpointer_history cpth
          WHERE coalesce_range && tstzrange(%(from)s, %(to)s, '[]')
          AND cpth.srvid = %(server)s
        ) AS unnested
        WHERE ts <@ tstzrange(%(from)s, %(to)s, '[]')
        UNION ALL
        SELECT srvid, (record).*
        FROM {powa}.powa_stat_checkpointer_history_current cptc
        WHERE (cptc.record).ts <@ tstzrange(%(from)s, %(to)s, '[]')
        AND cptc.srvid = %(server)s
      ) AS cpt_history
    ) AS cpt
    WHERE number %% ( int8larger((total)/(%(samples)s+1),1) ) = 0
"""


def BASE_QUERY_DATABASE_SAMPLE(per_db=False):
    if per_db:
        extra = """JOIN {powa}.powa_databases d
            ON d.oid = psd_history.datid and d.srvid = psd_history.srvid
        WHERE d.datname = %(database)s"""
    else:
        extra = ""

    return """
    (SELECT psd_history.srvid,
      row_number() OVER (ORDER BY psd_history.ts) AS number,
      count(*) OVER () AS total,
      ts,
      sum(numbackends) AS numbackends,
      sum(xact_commit) AS xact_commit,
      sum(xact_rollback) AS xact_rollback,
      sum(blks_read) AS blks_read,
      sum(blks_hit) AS blks_hit,
      sum(tup_returned) AS tup_returned,
      sum(tup_fetched) AS tup_fetched,
      sum(tup_inserted) AS tup_inserted,
      sum(tup_updated) AS tup_updated,
      sum(tup_deleted) AS tup_deleted,
      sum(conflicts) AS conflicts,
      sum(temp_files) AS temp_files,
      sum(temp_bytes) AS temp_bytes,
      sum(deadlocks) AS deadlocks,
      sum(checksum_failures) AS checksum_failures,
      max(checksum_last_failure) AS checksum_last_failure,
      sum(blk_read_time) AS blk_read_time,
      sum(blk_write_time) AS blk_write_time,
      sum(session_time) AS session_time,
      sum(active_time) AS active_time,
      sum(idle_in_transaction_time) AS idle_in_transaction_time,
      sum(sessions) AS sessions,
      sum(sessions_abandoned) AS sessions_abandoned,
      sum(sessions_fatal) AS sessions_fatal,
      sum(sessions_killed) AS sessions_killed,
      max(stats_reset) AS stats_reset
      FROM (
        SELECT *
        FROM (
          SELECT srvid, datid, (unnest(records)).*
          FROM {{powa}}.powa_stat_database_history psdh
          WHERE coalesce_range && tstzrange(%(from)s, %(to)s, '[]')
          AND psdh.srvid = %(server)s
        ) AS unnested
        WHERE ts <@ tstzrange(%(from)s, %(to)s, '[]')
        UNION ALL
        SELECT srvid, datid, (record).*
        FROM {{powa}}.powa_stat_database_history_current psdc
        WHERE (psdc.record).ts <@ tstzrange(%(from)s, %(to)s, '[]')
        AND psdc.srvid = %(server)s
      ) AS psd_history
      {extra}
      GROUP BY psd_history.srvid, psd_history.ts
    ) AS psd
    WHERE number %% ( int8larger((total)/(%(samples)s+1),1) ) = 0
""".format(extra=extra)


def BASE_QUERY_DATABASE_CONFLICTS_SAMPLE(per_db=False):
    if per_db:
        extra = """JOIN {powa}.powa_databases d
            ON d.oid = psd_history.datid and d.srvid = psd_history.srvid
        WHERE d.datname = %(database)s"""
    else:
        extra = ""

    return """
    (SELECT psdc_history.srvid,
      row_number() OVER (ORDER BY psdc_history.ts) AS number,
      count(*) OVER () AS total,
      ts,
      sum(confl_tablespace) AS confl_tablespace,
      sum(confl_lock) AS confl_lock,
      sum(confl_snapshot) AS confl_snapshot,
      sum(confl_bufferpin) AS confl_bufferpin,
      sum(confl_deadlock) AS confl_deadlock,
      sum(confl_active_logicalslot) AS confl_active_logicalslot
      FROM (
        SELECT *
        FROM (
          SELECT srvid, (unnest(records)).*
          FROM {{powa}}.powa_stat_database_conflicts_history psdch
          WHERE coalesce_range && tstzrange(%(from)s, %(to)s, '[]')
          AND psdch.srvid = %(server)s
        ) AS unnested
        WHERE ts <@ tstzrange(%(from)s, %(to)s, '[]')
        UNION ALL
        SELECT srvid, (record).*
        FROM {{powa}}.powa_stat_database_conflicts_history_current psdcc
        WHERE (psdcc.record).ts <@ tstzrange(%(from)s, %(to)s, '[]')
        AND psdcc.srvid = %(server)s
      ) AS psdc_history
      {extra}
      GROUP BY psdc_history.srvid, psdc_history.ts
    ) AS psdc
    WHERE number %% ( int8larger((total)/(%(samples)s+1),1) ) = 0
""".format(extra=extra)


# We use dense_rank() as we need ALL the records for a specific ts.  Caller
# will group the data per backend_type, object or other as needed
BASE_QUERY_IO_SAMPLE = """
    (SELECT srvid,
      --dense_rank() OVER (ORDER BY ts, backend_type, object, context) AS number,
      dense_rank() OVER (ORDER BY ts) AS number,
      count(*) OVER (PARTITION BY ts) AS num_per_window,
      count(*) OVER () AS total,
      ts,
      backend_type, object, context,
      reads * op_bytes AS reads, read_time,
      writes * op_bytes AS writes, write_time,
      writebacks * op_bytes AS writebacks, writeback_time,
      extends * op_bytes AS extends, extend_time,
      hits * op_bytes AS hits,
      evictions * op_bytes AS evictions,
      reuses * op_bytes AS reuses,
      fsyncs * op_bytes AS fsyncs, fsync_time AS fsync_time
      FROM (
        SELECT *
        FROM (
          SELECT srvid, backend_type, object, context, (unnest(records)).*
          FROM {powa}.powa_stat_io_history ioh
          WHERE coalesce_range && tstzrange(%(from)s, %(to)s, '[]')
          AND ioh.srvid = %(server)s
        ) AS unnested
        WHERE ts <@ tstzrange(%(from)s, %(to)s, '[]')
        UNION ALL
        SELECT srvid, backend_type, object, context, (record).*
        FROM {powa}.powa_stat_io_history_current ioc
        WHERE (ioc.record).ts <@ tstzrange(%(from)s, %(to)s, '[]')
        AND ioc.srvid = %(server)s
      ) AS io_history
    ) AS io
    WHERE number %% ( int8larger((total / num_per_window)/(%(samples)s+1),1) ) = 0
"""


BASE_QUERY_REPLICATION_SAMPLE = """
    (SELECT srvid,
      row_number() OVER (ORDER BY psr_history.ts) AS number,
      count(*) OVER () AS total,
      ts,
      rep_current_lsn,
      count(DISTINCT pid) AS nb_repl,
      min(sent_lsn) AS sent_lsn,
      min(write_lsn) AS write_lsn,
      min(flush_lsn) AS flush_lsn,
      min(replay_lsn) AS replay_lsn,
      max(write_lag) AS write_lag,
      max(flush_lag) AS flush_lag,
      max(replay_lag) AS replay_lag,
      count(DISTINCT pid) FILTER (WHERE sync_state = 'async') AS nb_async,
      count(*) FILTER (WHERE slot_type = 'physical' AND active) AS nb_physical_act,
      count(*) FILTER (WHERE slot_type = 'physical' AND NOT active) AS nb_physical_not_act,
      count(*) FILTER (WHERE slot_type = 'logical' AND active) AS nb_logical_act,
      count(*) FILTER (WHERE slot_type = 'logical' AND NOT active) AS nb_logical_not_act
      FROM (
        SELECT statrep.srvid,
          statrep.ts,
          statrep.current_lsn AS rep_current_lsn, statrep.pid, statrep.usename,
          statrep.application_name, statrep.client_addr, statrep.backend_start,
          statrep.backend_xmin, statrep.state, statrep.sent_lsn,
          statrep.write_lsn, statrep.flush_lsn, statrep.replay_lsn,
          statrep.write_lag, statrep.flush_lag, statrep.replay_lag,
          statrep.sync_priority, statrep.sync_state, statrep.reply_time,

          replslot.cur_txid, replslot.current_lsn AS slot_current_lsn,
          replslot.slot_name, replslot.plugin, replslot.slot_type,
          replslot.datoid, replslot.temporary, replslot.active,
          replslot.active_pid, replslot.slot_xmin, replslot.catalog_xmin,
          replslot.restart_lsn, replslot.confirmed_flush_lsn,
          replslot.wal_status, replslot.safe_wal_size, replslot.two_phase,
          replslot.conflicting
        FROM (
          SELECT srvid, (unnest(records)).*
          FROM {powa}.powa_stat_replication_history psrh
          WHERE coalesce_range && tstzrange(%(from)s, %(to)s, '[]')
          AND psrh.srvid = %(server)s
        ) AS statrep
        FULL OUTER JOIN (
          SELECT srvid, slot_name, plugin, slot_type, datoid, temporary,
            (unnest(records)).*
          FROM {powa}.powa_replication_slots_history prsh
          WHERE coalesce_range && tstzrange(%(from)s, %(to)s, '[]')
          AND prsh.srvid = %(server)s
        ) AS replslot
          ON replslot.srvid = statrep.srvid
          AND replslot.ts = statrep.ts
          AND replslot.active_pid = statrep.pid
        WHERE statrep.ts <@ tstzrange(%(from)s, %(to)s, '[]')
        UNION ALL
        SELECT %(server)s AS srvid,
          (psrc.record).ts,
          (psrc.record).current_lsn AS rep_current_lsn, (psrc.record).pid,
          (psrc.record).usename, (psrc.record).application_name,
          (psrc.record).client_addr, (psrc.record).backend_start,
          (psrc.record).backend_xmin, (psrc.record).state,
          (psrc.record).sent_lsn, (psrc.record).write_lsn,
          (psrc.record).flush_lsn, (psrc.record).replay_lsn,
          (psrc.record).write_lag, (psrc.record).flush_lag,
          (psrc.record).replay_lag, (psrc.record).sync_priority,
          (psrc.record).sync_state, (psrc.record).reply_time,

          (prsc.record).cur_txid,
          (prsc.record).current_lsn AS slot_current_lsn,
          prsc.slot_name, prsc.plugin,
          prsc.slot_type, prsc.datoid,
          prsc.temporary, (prsc.record).active,
          (prsc.record).active_pid, (prsc.record).slot_xmin,
          (prsc.record).catalog_xmin, (prsc.record).restart_lsn,
          (prsc.record).confirmed_flush_lsn, (prsc.record).wal_status,
          (prsc.record).safe_wal_size, (prsc.record).two_phase,
          (prsc.record).conflicting
        FROM {powa}.powa_stat_replication_history_current psrc
        FULL OUTER JOIN {powa}.powa_replication_slots_history_current prsc
          ON psrc.srvid = prsc.srvid AND (psrc.record).ts = (prsc.record).ts
            AND  (psrc.record).pid = (prsc.record).active_pid
        WHERE (psrc.record).ts <@ tstzrange(%(from)s, %(to)s, '[]')
        AND psrc.srvid = %(server)s
      ) AS psr_history
      GROUP BY psr_history.srvid, psr_history.ts, psr_history.rep_current_lsn
    ) AS psr
    WHERE number %% ( int8larger((total)/(%(samples)s+1),1) ) = 0
"""


# We use dense_rank() as we need ALL the records for a specific ts.  Caller
# will group the data as needed
BASE_QUERY_SLRU_SAMPLE = """
    (SELECT srvid,
      dense_rank() OVER (ORDER BY slru_history.ts) AS number,
      count(*) OVER (PARTITION BY ts) AS num_per_window,
      count(*) OVER () AS total,
      ts,
      name,
      blks_zeroed, blks_hit, blks_read, blks_written,
      blks_exists, flushes, truncates
      FROM (
        SELECT *
        FROM (
          SELECT srvid, name, (unnest(records)).*
          FROM {powa}.powa_stat_slru_history slruh
          WHERE coalesce_range && tstzrange(%(from)s, %(to)s, '[]')
          AND slruh.srvid = %(server)s
        ) AS unnested
        WHERE ts <@ tstzrange(%(from)s, %(to)s, '[]')
        UNION ALL
        SELECT srvid, name, (record).*
        FROM {powa}.powa_stat_slru_history_current slruc
        WHERE (slruc.record).ts <@ tstzrange(%(from)s, %(to)s, '[]')
        AND slruc.srvid = %(server)s
      ) AS slru_history
    ) AS slru
    WHERE number %% ( int8larger((total / num_per_window)/(%(samples)s+1),1) ) = 0
"""


def BASE_QUERY_SUBSCRIPTION_SAMPLE(subname=None):
    if subname is not None:
        extra = "AND subname = %(subscription)s"
    else:
        extra = ""

    # We use dense_rank() as we need ALL the records for a specific ts.  Caller
    # will group the data as needed.
    return """
    (SELECT srvid,
      dense_rank() OVER (ORDER BY ts) AS number,
      count(*) OVER (PARTITION BY ts) AS num_per_window,
      count(*) OVER () AS total,
      ts,
      subname,
      extract(epoch FROM ((last_msg_receipt_time - last_msg_send_time) * 1000)) AS last_msg_lag,
      latest_end_lsn,
      extract(epoch FROM ((ts - latest_end_time) * 1000)) AS report_lag,
      apply_error_count,
      sync_error_count
      FROM (
        SELECT *
        FROM (
          SELECT *
          FROM (
            SELECT srvid, sh.subid, sh.subname, (unnest(records)).*
            FROM {{powa}}.powa_stat_subscription_history sh
            WHERE coalesce_range && tstzrange(%(from)s, %(to)s, '[]')
            AND sh.srvid = %(server)s
            {extra}
            ) AS sub1
          LEFT JOIN (
            SELECT srvid, ssh.subid, (unnest(records)).*
            FROM {{powa}}.powa_stat_subscription_stats_history ssh
            WHERE coalesce_range && tstzrange(%(from)s, %(to)s, '[]')
            AND ssh.srvid = %(server)s
            {extra}
          ) AS sub2 USING (srvid, subid, ts)
        ) AS unnested
        WHERE ts <@ tstzrange(%(from)s, %(to)s, '[]')
        UNION ALL
        SELECT *
        FROM (
            SELECT srvid, shc.subid, shc.subname, (record).*
            FROM {{powa}}.powa_stat_subscription_history_current shc
            WHERE (shc.record).ts <@ tstzrange(%(from)s, %(to)s, '[]')
            AND shc.srvid = %(server)s
            {extra}
        ) AS sub1
        LEFT JOIN (
            SELECT srvid, sshc.subid, (record).*
            FROM {{powa}}.powa_stat_subscription_stats_history_current sshc
            WHERE (sshc.record).ts <@ tstzrange(%(from)s, %(to)s, '[]')
            AND sshc.srvid = %(server)s
            {extra}
        ) AS sub2 USING (srvid, subid, ts)
      ) AS subscription_history
    ) AS io
    WHERE number %% ( int8larger((total / num_per_window)/(%(samples)s+1),1) ) = 0
""".format(extra=extra)


BASE_QUERY_WAL_SAMPLE = """
    (SELECT srvid,
      row_number() OVER (ORDER BY wal_history.ts) AS number,
      count(*) OVER () AS total,
      ts,
      wal_records,
      wal_fpi,
      wal_bytes,
      wal_buffers_full,
      wal_write,
      wal_sync,
      wal_write_time,
      wal_sync_time
      FROM (
        SELECT *
        FROM (
          SELECT srvid, (unnest(records)).*
          FROM {powa}.powa_stat_wal_history walh
          WHERE coalesce_range && tstzrange(%(from)s, %(to)s, '[]')
          AND walh.srvid = %(server)s
        ) AS unnested
        WHERE ts <@ tstzrange(%(from)s, %(to)s, '[]')
        UNION ALL
        SELECT srvid, (record).*
        FROM {powa}.powa_stat_wal_history_current walc
        WHERE (walc.record).ts <@ tstzrange(%(from)s, %(to)s, '[]')
        AND walc.srvid = %(server)s
      ) AS wal_history
    ) AS wal
    WHERE number %% ( int8larger((total)/(%(samples)s+1),1) ) = 0
"""


BASE_QUERY_WAL_RECEIVER_SAMPLE = """
    (SELECT srvid,
      row_number() OVER (ORDER BY wr_history.ts) AS number,
      count(*) OVER () AS total,
      ts,
      slot_name,
      sender_host, sender_port,
      pid, status,
      receive_start_lsn, receive_start_tli,
      last_received_lsn,
      written_lsn, flushed_lsn,
      received_tli,
      last_msg_send_time,
      last_msg_receipt_time,
      latest_end_lsn,
      latest_end_time,
      conninfo
      FROM (
        SELECT *
        FROM (
          SELECT srvid, slot_name, sender_host, sender_port, (unnest(records)).*
          FROM {powa}.powa_stat_wal_receiver_history walh
          WHERE coalesce_range && tstzrange(%(from)s, %(to)s, '[]')
          AND walh.srvid = %(server)s
        ) AS unnested
        WHERE ts <@ tstzrange(%(from)s, %(to)s, '[]')
        UNION ALL
        SELECT srvid, slot_name, sender_host, sender_port, (record).*
        FROM {powa}.powa_stat_wal_receiver_history_current walc
        WHERE (walc.record).ts <@ tstzrange(%(from)s, %(to)s, '[]')
        AND walc.srvid = %(server)s
      ) AS wr_history
    ) AS wr
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

    biggest = Biggest(base_columns, "ts")
    biggestsum = Biggestsum(base_columns, "ts")

    where = " AND ".join(predicates)
    if where != "":
        where = " AND " + where

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
        all_cols=", ".join(all_cols),
        base_columns=", ".join(base_columns),
        base_query=base_query,
        where=where,
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
        return """extract(epoch FROM (coalesce(clock_ts, ts) - {f})) * 1000 AS {a}""".format(
            f=field, a=alias
        )

    all_cols = base_columns + [
        "ts",
        "datid",
        txid_age("backend_xid"),  # backend_xid_age
        txid_age("backend_xmin"),  # backend_xmin_age
        ts_get_sec("backend_start"),  # backend_start_age
        ts_get_sec("xact_start"),  # xact_start_age
        ts_get_sec("query_start"),  # query_start_age
        "state",
        "leader_pid",
    ]

    return """SELECT {all_cols}
    FROM {base_query}""".format(
        all_cols=", ".join(all_cols), base_query=base_query
    )


def powa_get_archiver_sample():
    base_query = BASE_QUERY_ARCHIVER_SAMPLE
    base_columns = ["srvid"]

    biggest = Biggest(base_columns, "ts")

    all_cols = base_columns + [
        "ts",
        biggest("ts", "'0 s'", "mesure_interval"),
        "current_wal",
        "last_archived_time",
        biggest(wal_to_num("last_archived_wal"), label="nb_arch"),
        "last_failed_time",
        wal_to_num("current_wal")
        + " - "
        + wal_to_num("last_archived_wal")
        + " - 1 AS nb_to_arch",
    ]

    return """SELECT {all_cols}
    FROM {base_query}""".format(
        all_cols=", ".join(all_cols), base_query=base_query
    )


def powa_get_bgwriter_sample():
    base_query = BASE_QUERY_BGWRITER_SAMPLE
    base_columns = ["srvid"]

    biggest = Biggest(base_columns, "ts")
    biggestsum = Biggestsum(base_columns, "ts")

    all_cols = base_columns + [
        "ts",
        biggest("ts", "'0 s'", "mesure_interval"),
        biggestsum("buffers_clean"),
        biggestsum("maxwritten_clean"),
        biggestsum("buffers_backend"),
        biggestsum("buffers_backend_fsync"),
        biggestsum("buffers_alloc"),
    ]

    return """SELECT {all_cols}
    FROM {base_query}
    GROUP BY {base_columns}, ts""".format(
        all_cols=", ".join(all_cols),
        base_columns=", ".join(base_columns),
        base_query=base_query,
    )


def powa_get_checkpointer_sample():
    base_query = BASE_QUERY_CHECKPOINTER_SAMPLE
    base_columns = ["srvid"]

    biggest = Biggest(base_columns, "ts")
    biggestsum = Biggestsum(base_columns, "ts")

    all_cols = base_columns + [
        "ts",
        biggest("ts", "'0 s'", "mesure_interval"),
        biggestsum("num_timed"),
        biggestsum("num_requested"),
        biggestsum("write_time"),
        biggestsum("sync_time"),
        biggestsum("buffers_written"),
    ]

    return """SELECT {all_cols}
    FROM {base_query}
    GROUP BY {base_columns}, ts""".format(
        all_cols=", ".join(all_cols),
        base_columns=", ".join(base_columns),
        base_query=base_query,
    )


def powa_get_database_sample(per_db=False):
    base_query = BASE_QUERY_DATABASE_SAMPLE(per_db)
    base_columns = ["srvid"]

    biggest = Biggest(base_columns, "ts")

    all_cols = base_columns + [
        "ts",
        biggest("ts", "'0 s'", "mesure_interval"),
        biggest("numbackends"),
        biggest("xact_commit"),
        biggest("xact_rollback"),
        biggest("blks_read"),
        biggest("blks_hit"),
        biggest("tup_returned"),
        biggest("tup_fetched"),
        biggest("tup_inserted"),
        biggest("tup_updated"),
        biggest("tup_deleted"),
        biggest("conflicts"),
        biggest("temp_files"),
        biggest("temp_bytes"),
        biggest("deadlocks"),
        biggest("checksum_failures"),
        "checksum_last_failure",
        biggest("blk_read_time"),
        biggest("blk_write_time"),
        biggest("session_time"),
        biggest("active_time"),
        biggest("idle_in_transaction_time"),
        biggest("sessions"),
        biggest("sessions_abandoned"),
        biggest("sessions_fatal"),
        biggest("sessions_killed"),
        "stats_reset",
    ]

    return """SELECT {all_cols}
    FROM {base_query}""".format(
        all_cols=", ".join(all_cols), base_query=base_query
    )


def powa_get_database_conflicts_sample(per_db=False):
    base_query = BASE_QUERY_DATABASE_CONFLICTS_SAMPLE(per_db)
    base_columns = ["srvid"]

    biggest = Biggest(base_columns, "ts")

    all_cols = base_columns + [
        "ts",
        biggest("ts", "'0 s'", "mesure_interval"),
        biggest("confl_tablespace"),
        biggest("confl_lock"),
        biggest("confl_snapshot"),
        biggest("confl_bufferpin"),
        biggest("confl_deadlock"),
        biggest("confl_active_logicalslot"),
    ]

    return """SELECT {all_cols}
    FROM {base_query}""".format(
        all_cols=", ".join(all_cols), base_query=base_query
    )


def powa_get_replication_sample():
    base_query = BASE_QUERY_REPLICATION_SAMPLE
    base_columns = ["srvid"]

    biggest = Biggest(base_columns, "ts")

    all_cols = base_columns + [
        "ts",
        biggest("ts", "'0 s'", "mesure_interval"),
        "rep_current_lsn",
        "nb_repl",
        "sent_lsn",
        "write_lsn",
        "flush_lsn",
        "replay_lsn",
        "write_lag",
        "flush_lag",
        "replay_lag",
        "nb_async",
        "nb_repl - nb_async AS nb_sync",
        "nb_physical_act",
        "nb_physical_not_act",
        "nb_logical_act",
        "nb_logical_not_act",
    ]

    return """SELECT {all_cols}
    FROM {base_query}""".format(
        all_cols=", ".join(all_cols), base_query=base_query
    )


def powa_get_io_sample(qual=None):
    base_query = BASE_QUERY_IO_SAMPLE
    base_columns = ["srvid", "backend_type", "object", "context"]

    biggest = Biggest(base_columns, "ts")

    if qual is not None:
        qual = " AND %s" % qual
    else:
        qual = ""

    all_cols = base_columns + [
        "ts",
        biggest("ts", "'0 s'", "mesure_interval"),
        biggest("reads"),
        biggest("read_time"),
        biggest("writes"),
        biggest("write_time"),
        biggest("writebacks"),
        biggest("writeback_time"),
        biggest("extends"),
        biggest("extend_time"),
        biggest("hits"),
        biggest("evictions"),
        biggest("reuses"),
        biggest("fsyncs"),
        biggest("fsync_time"),
    ]

    return """SELECT {all_cols}
    FROM {base_query}
    {qual}""".format(
        all_cols=", ".join(all_cols), base_query=base_query, qual=qual
    )


def powa_get_slru_sample(qual=None):
    base_query = BASE_QUERY_SLRU_SAMPLE
    base_columns = ["srvid", "name"]

    biggest = Biggest(base_columns, "ts")

    if qual is not None:
        qual = " AND %s" % qual
    else:
        qual = ""

    all_cols = base_columns + [
        "ts",
        biggest("ts", "'0 s'", "mesure_interval"),
        biggest("blks_zeroed"),
        biggest("blks_hit"),
        biggest("blks_read"),
        biggest("blks_written"),
        biggest("blks_exists"),
        biggest("flushes"),
        biggest("truncates"),
    ]

    return """SELECT {all_cols}
    FROM {base_query}
    {qual}""".format(
        all_cols=", ".join(all_cols),
        base_query=base_query,
        qual=qual,
    )


def powa_get_subscription_sample(subname=None):
    base_query = BASE_QUERY_SUBSCRIPTION_SAMPLE(subname)
    base_columns = ["srvid", "subname"]

    biggest = Biggest(base_columns, "ts")

    all_cols = base_columns + [
        "ts",
        biggest("ts", "'0 s'", "mesure_interval"),
        biggest("last_msg_lag"),
        biggest("report_lag"),
        biggest("apply_error_count"),
        biggest("sync_error_count"),
    ]

    return """SELECT {all_cols}
    FROM {base_query}""".format(
        all_cols=", ".join(all_cols),
        base_query=base_query,
    )


def powa_get_wal_sample():
    base_query = BASE_QUERY_WAL_SAMPLE
    base_columns = ["srvid"]

    biggest = Biggest(base_columns, "ts")
    biggestsum = Biggestsum(base_columns, "ts")

    all_cols = base_columns + [
        "ts",
        biggest("ts", "'0 s'", "mesure_interval"),
        biggestsum("wal_records"),
        biggestsum("wal_fpi"),
        biggestsum("wal_bytes"),
        biggestsum("wal_buffers_full"),
        biggestsum("wal_write"),
        biggestsum("wal_sync"),
        biggestsum("wal_write_time"),
        biggestsum("wal_sync_time"),
    ]

    return """SELECT {all_cols}
    FROM {base_query}
    GROUP BY {base_columns}, ts""".format(
        all_cols=", ".join(all_cols),
        base_columns=", ".join(base_columns),
        base_query=base_query,
    )


def powa_get_wal_receiver_sample():
    base_query = BASE_QUERY_WAL_RECEIVER_SAMPLE
    base_columns = ["srvid", "slot_name", "sender_host", "sender_port"]

    biggest = Biggest(base_columns, "ts")

    all_cols = base_columns + [
        "ts",
        biggest("ts", "'0 s'", "mesure_interval"),
        "slot_name",
        "sender_host",
        "sender_port",
        "pid",
        "status",
        "receive_start_lsn",
        "receive_start_tli",
        "last_received_lsn",
        biggest("last_received_lsn", label="received_bytes"),
        "written_lsn",
        "flushed_lsn",
        "received_tli",
        "last_msg_send_time",
        "last_msg_receipt_time",
        "latest_end_lsn",
        "latest_end_time",
        "conninfo",
    ]

    return """SELECT {all_cols}
    FROM {base_query}""".format(
        all_cols=", ".join(all_cols), base_query=base_query
    )


def powa_get_all_idx_sample(mode):
    if mode == "db":
        base_query = BASE_QUERY_ALL_IDXS_SAMPLE_DB
        base_columns = ["srvid", "dbid", "datname"]
    else:
        base_query = BASE_QUERY_ALL_IDXS_SAMPLE
        base_columns = ["srvid", "dbid", "datname", "relid"]

    biggest = Biggest(base_columns, "ts")
    biggestsum = Biggestsum(base_columns, "ts")

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
        all_cols=", ".join(all_cols),
        base_columns=", ".join(base_columns),
        base_query=base_query,
    )


def powa_get_all_tbl_sample(mode):
    if mode == "db":
        base_query = BASE_QUERY_ALL_TBLS_SAMPLE_DB
        base_columns = ["srvid", "dbid", "datname"]
    else:
        base_query = BASE_QUERY_ALL_TBLS_SAMPLE
        base_columns = ["srvid", "dbid", "datname", "relid"]

    biggest = Biggest(base_columns, "ts")
    biggestsum = Biggestsum(base_columns, "ts")

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
        all_cols=", ".join(all_cols),
        base_columns=", ".join(base_columns),
        base_query=base_query,
    )


def powa_get_user_fct_sample(mode):
    if mode == "db":
        base_query = BASE_QUERY_USER_FCTS_SAMPLE_DB
        base_columns = ["srvid", "dbid", "datname"]
    else:
        base_query = BASE_QUERY_USER_FCTS_SAMPLE
        base_columns = ["srvid", "dbid", "datname", "funcid"]

    biggest = Biggest(base_columns, "ts")
    biggestsum = Biggestsum(base_columns, "ts")

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
        all_cols=", ".join(all_cols),
        base_columns=", ".join(base_columns),
        base_query=base_query,
    )
