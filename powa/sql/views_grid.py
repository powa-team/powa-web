"""
Functions to generate the queries used in the various grid components
"""

from powa.sql.utils import block_size, diff, diffblk


def powa_base_statdata_detailed_db():
    """
    Base for query used in the grids displaying info about pgss.

    This is based on the "detailed" version of the table, with queryid
    information.

    As the data is stored in 2 sets of tables (the coalesced records and the
    "current" records), we have to retrieve the query in multiple steps.

    To improve performance, the retrieval of the coalesced records is divided
    in 3 parts, which can greatly limit the number of rows that will need to be
    sorted.

    Those 3 parts are split in 3 subqueries.  For the left and right bounds
    (the smallest and largest timestamp in the given interval), we get the 2
    underlying records in the coalesced records (if any) and unnest them
    fully, filtering any records outside of the interval bound.  For any record
    in the coalesced records that are entirely inside the given interval,
    we rely on the pre-computed metadata (mins_in_range and maxs_in_range) and
    simply return that, which can greatly reduces the amount of rows to sort.

    For the "current" records, we simply return all the rows in the given
    interval.
    """
    base_query = """
  {powa}.powa_databases,
  LATERAL
  (
    -- Left bound: the search interval is a single timestamp, the smallest one
    -- of the search interval, and has to be inside the coalesce_range. We
    -- still need to unnest this one as we may have to remove some of the
    -- underlying records
    SELECT unnested.dbid, unnested.toplevel, unnested.userid, unnested.queryid,
      (unnested.records).*
    FROM (
      SELECT psh.dbid, psh.toplevel, psh.userid, psh.queryid,
        psh.coalesce_range, unnest(records) AS records
      FROM {powa}.powa_statements_history psh
      WHERE coalesce_range && tstzrange(%(from)s, %(from)s, '[]')
      AND psh.dbid = powa_databases.oid
      AND psh.srvid = %(server)s
    ) AS unnested
    WHERE (records).ts <@ tstzrange(%(from)s, %(to)s, '[]')

    UNION ALL

    -- Right bound: the search interval is a single timestamp, the largest one
    -- of the search interval, and has to be inside the coalesce_range. We
    -- still need to unnest this one as we may have to remove some of the
    -- underlying records
    SELECT unnested.dbid, unnested.toplevel, unnested.userid, unnested.queryid,
      (unnested.records).*
    FROM (
      SELECT psh.dbid, psh.toplevel, psh.userid, psh.queryid,
        psh.coalesce_range, unnest(records) AS records
      FROM {powa}.powa_statements_history psh
      WHERE coalesce_range && tstzrange(%(to)s, %(to)s, '[]')
      AND psh.dbid = powa_databases.oid
      AND psh.srvid = %(server)s
    ) AS unnested
    WHERE (records).ts <@ tstzrange(%(from)s, %(to)s, '[]')

    UNION ALL

    -- These entries have their coalesce_range ENTIRELY inside the search range
    -- so we don't need to unnest them.  We just retrieve the mins_in_range,
    -- maxs_in_range from the record, build an array of this and return it as
    -- if it was the full record
    SELECT unnested.dbid, unnested.toplevel, unnested.userid, unnested.queryid,
      (unnested.records).*
    FROM (
      SELECT psh.dbid, psh.toplevel, psh.userid, psh.queryid,
        psh.coalesce_range,
        unnest(ARRAY[mins_in_range,maxs_in_range]) AS records
      FROM {powa}.powa_statements_history psh
      WHERE coalesce_range && tstzrange(%(from)s, %(to)s, '[]')
      AND psh.dbid = powa_databases.oid
      AND psh.srvid = %(server)s
    ) AS unnested
    WHERE (records).ts <@ tstzrange(%(from)s, %(to)s, '[]')

    UNION ALL

    -- The "current" records are simply returned after filtering
    SELECT psc.dbid, psc.toplevel, psc.userid, psc.queryid,(psc.record).*
    FROM {powa}.powa_statements_history_current psc
    WHERE (record).ts <@ tstzrange(%(from)s,%(to)s,'[]')
    AND psc.dbid = powa_databases.oid
    AND psc.srvid = %(server)s
  ) h"""
    return base_query


def powa_base_statdata_db():
    """
    Query used in the grids displaying info about pgss.

    This is based on the db-aggregated version of the tables, without queryid
    information.

    This uses the same optimization as powa_base_statdata_detailed_db.
    """
    base_query = """(
 SELECT d.srvid, d.oid as dbid, h.*
 FROM
 {powa}.powa_databases d LEFT JOIN
 (
   SELECT srvid, dbid
   FROM {powa}.powa_statements_history_db dbh
   WHERE coalesce_range && tstzrange(%(from)s, %(to)s, '[]')
   AND dbh.srvid = %(server)s
   GROUP BY srvid, dbid
 ) ranges ON d.oid = ranges.dbid AND d.srvid = ranges.srvid,
 LATERAL (
   -- Left bound: the search interval is a single timestamp, the smallest one
   -- of the search interval, and has to be inside the coalesce_range. We
   -- still need to unnest this one as we may have to remove some of the
   -- underlying records
   SELECT (unnested1.records).*
   FROM (
     SELECT dbh.coalesce_range, unnest(records) AS records
     FROM {powa}.powa_statements_history_db dbh
     WHERE coalesce_range && tstzrange(%(from)s, %(from)s, '[]')
     AND dbh.dbid = ranges.dbid
     AND dbh.srvid = %(server)s
   ) AS unnested1
   WHERE (unnested1.records).ts <@ tstzrange(%(from)s, %(to)s, '[]')

   -- Right bound: the search interval is a single timestamp, the largest one
   -- of the search interval, and has to be inside the coalesce_range. We
   -- still need to unnest this one as we may have to remove some of the
   -- underlying records
   UNION ALL
   SELECT (unnested2.records).*
   FROM (
     SELECT dbh.coalesce_range, unnest(records) AS records
     FROM {powa}.powa_statements_history_db dbh
     WHERE coalesce_range && tstzrange(%(to)s, %(to)s, '[]')
     AND dbh.dbid = ranges.dbid
     AND dbh.srvid = %(server)s
   ) AS unnested2
   WHERE  (unnested2.records).ts <@ tstzrange(%(from)s, %(to)s, '[]')

   UNION ALL

   -- These entries have their coalesce_range ENTIRELY inside the search range
   -- so we don't need to unnest them.  We just retrieve the mins_in_range,
   -- maxs_in_range from the record, build an array of this and return it as
   -- if it was the full record
   SELECT (unnested1.records).*
   FROM (
     SELECT dbh.coalesce_range,
       unnest(ARRAY[mins_in_range,maxs_in_range]) AS records
     FROM {powa}.powa_statements_history_db dbh
     WHERE coalesce_range && tstzrange(%(from)s, %(to)s, '[]')
     AND dbh.dbid = ranges.dbid
     AND dbh.srvid = %(server)s
   ) AS unnested1
   WHERE (unnested1.records).ts <@ tstzrange(%(from)s, %(to)s, '[]')

   UNION ALL

   -- The "current" records are simply returned after filtering
   SELECT (dbc.record).*
   FROM {powa}.powa_statements_history_current_db dbc
   WHERE  (dbc.record).ts <@ tstzrange(%(from)s, %(to)s, '[]')
   AND dbc.dbid = d.oid
   AND dbc.srvid = d.srvid
   AND dbc.srvid = %(server)s
    ) AS h
) AS db_history
    """
    return base_query


def powa_base_bgwriter():
    base_query = """(
 SELECT h.*
 FROM
 (
   SELECT srvid
   FROM {powa}.powa_stat_bgwriter_history bgwh
   WHERE coalesce_range && tstzrange(%(from)s, %(to)s, '[]')
   AND dbh.srvid = %(server)s
   GROUP BY srvid
 ) ranges
 LATERAL (
   SELECT (unnested1.records).*
   FROM (
     SELECT bgwh.coalesce_range, unnest(records) AS records
     FROM {powa}.powa_stat_bgwriter_history bgwh
     WHERE coalesce_range && tstzrange(%(from)s, %(to)s, '[]')
     AND bgwh.srvid = %(server)s
   ) AS unnested1
   WHERE  (unnested1.records).ts <@ tstzrange(%(from)s, %(to)s, '[]')
   UNION ALL
   SELECT (bgwc.record).*
   FROM {powa}.powa_stat_bgwriter_history_current bgwc
   WHERE  (dbc.record).ts <@ tstzrange(%(from)s, %(to)s, '[]')
   AND dbc.srvid = d.srvid
   AND dbc.srvid = %(server)s
    ) AS h
) AS bgw_history
    """
    return base_query


def powa_base_io():
    """
    Query used in the grids displaying info about pg_stat_io.

    This uses the same optimization as powa_base_statdata_detailed_db.
    """
    base_query = """(
 SELECT *
 FROM
 (
   SELECT srvid
   FROM {powa}.powa_stat_io_history ioh
   WHERE coalesce_range && tstzrange(%(from)s, %(to)s, '[]')
   AND ioh.srvid = %(server)s
   GROUP BY srvid
 ) ranges,
 LATERAL (
   -- Left bound: the search interval is a single timestamp, the smallest one
   -- of the search interval, and has to be inside the coalesce_range. We
   -- still need to unnest this one as we may have to remove some of the
   -- underlying records
   SELECT backend_type, object, context, (unnested.records).*
   FROM (
     SELECT ioh.backend_type, ioh.object, ioh.context,
       ioh.coalesce_range, unnest(records) AS records
     FROM {powa}.powa_stat_io_history ioh
     WHERE coalesce_range && tstzrange(%(from)s, %(from)s, '[]')
     AND ioh.srvid = %(server)s
   ) AS unnested
   WHERE (records).ts <@ tstzrange(%(from)s, %(to)s, '[]')

   UNION ALL

   -- Right bound: the search interval is a single timestamp, the largest one
   -- of the search interval, and has to be inside the coalesce_range. We
   -- still need to unnest this one as we may have to remove some of the
   -- underlying records
   SELECT backend_type, object, context, (unnested.records).*
   FROM (
     SELECT ioh.backend_type, ioh.object, ioh.context,
       ioh.coalesce_range, unnest(records) AS records
     FROM {powa}.powa_stat_io_history ioh
     WHERE coalesce_range && tstzrange(%(to)s, %(to)s, '[]')
     AND ioh.srvid = %(server)s
   ) AS unnested
   WHERE (records).ts <@ tstzrange(%(from)s, %(to)s, '[]')

   UNION ALL

   -- These entries have their coalesce_range ENTIRELY inside the search range
   -- so we don't need to unnest them.  We just retrieve the mins_in_range,
   -- maxs_in_range from the record, build an array of this and return it as
   -- if it was the full record
   SELECT backend_type, object, context, (unnested.records).*
   FROM (
     SELECT ioh.backend_type, ioh.object, ioh.context,
       ioh.coalesce_range,
       unnest(ARRAY[mins_in_range,maxs_in_range]) AS records
     FROM {powa}.powa_stat_io_history ioh
     WHERE coalesce_range && tstzrange(%(from)s, %(to)s, '[]')
     AND ioh.srvid = %(server)s
   ) AS unnested
   WHERE (records).ts <@ tstzrange(%(from)s, %(to)s, '[]')
 ) AS h
 UNION ALL
 SELECT srvid, backend_type, object, context, (ioc.record).*
 FROM {powa}.powa_stat_io_history_current ioc
 WHERE (ioc.record).ts <@ tstzrange(%(from)s, %(to)s, '[]')
 AND ioc.srvid = %(server)s
) AS io_history
    """
    return base_query


def powa_getiodata(qual=None):
    """
    Query used in the grid displaying info about pg_stat_io.
    """
    base_query = powa_base_io()

    if qual is not None:
        qual = " WHERE %s" % qual
    else:
        qual = ""

    base_cols = [
        "srvid",
        "backend_type",
        "object",
        "context",
    ]

    cols = [
        diffblk("reads", "op_bytes"),
        diff("read_time"),
        diffblk("writes", "op_bytes"),
        diff("write_time"),
        diffblk("writebacks", "op_bytes"),
        diff("writeback_time"),
        diffblk("extends", "op_bytes"),
        diff("extend_time"),
        diffblk("hits", "op_bytes"),
        diffblk("evictions", "op_bytes"),
        diffblk("reuses", "op_bytes"),
        diffblk("fsyncs", "op_bytes"),
        diff("fsync_time"),
    ]

    return """SELECT {base_cols}, {cols}
    FROM {base_query}
    {qual}
    GROUP BY srvid, {base_cols}, op_bytes""".format(
        cols=", ".join(cols),
        base_cols=", ".join(base_cols),
        base_query=base_query,
        qual=qual,
    )


def powa_base_slru():
    """
    Query used in the grids displaying info about pg_stat_slru.

    This uses the same optimization as powa_base_statdata_detailed_db.
    """
    base_query = """(
 SELECT *
 FROM
 (
   SELECT srvid
   FROM {powa}.powa_stat_slru_history slru
   WHERE coalesce_range && tstzrange(%(from)s, %(to)s, '[]')
   AND slru.srvid = %(server)s
   GROUP BY srvid
 ) ranges,
 LATERAL (
   -- Left bound: the search interval is a single timestamp, the smallest one
   -- of the search interval, and has to be inside the coalesce_range. We
   -- still need to unnest this one as we may have to remove some of the
   -- underlying records
   SELECT name, (unnested.records).*
   FROM (
     SELECT slru.name, slru.coalesce_range, unnest(records) AS records
     FROM {powa}.powa_stat_slru_history slru
     WHERE coalesce_range && tstzrange(%(from)s, %(from)s, '[]')
     AND slru.srvid = %(server)s
   ) AS unnested
   WHERE (records).ts <@ tstzrange(%(from)s, %(to)s, '[]')

   UNION ALL

   -- Right bound: the search interval is a single timestamp, the largest one
   -- of the search interval, and has to be inside the coalesce_range. We
   -- still need to unnest this one as we may have to remove some of the
   -- underlying records
   SELECT name, (unnested.records).*
   FROM (
     SELECT slru.name, slru.coalesce_range, unnest(records) AS records
     FROM {powa}.powa_stat_slru_history slru
     WHERE coalesce_range && tstzrange(%(to)s, %(to)s, '[]')
     AND slru.srvid = %(server)s
   ) AS unnested
   WHERE (records).ts <@ tstzrange(%(from)s, %(to)s, '[]')

   UNION ALL

   -- These entries have their coalesce_range ENTIRELY inside the search range
   -- so we don't need to unnest them.  We just retrieve the mins_in_range,
   -- maxs_in_range from the record, build an array of this and return it as
   -- if it was the full record
   SELECT name, (unnested.records).*
   FROM (
     SELECT slru.name, slru.coalesce_range,
       unnest(ARRAY[mins_in_range,maxs_in_range]) AS records
     FROM {powa}.powa_stat_slru_history slru
     WHERE coalesce_range && tstzrange(%(from)s, %(to)s, '[]')
     AND slru.srvid = %(server)s
   ) AS unnested
   WHERE (records).ts <@ tstzrange(%(from)s, %(to)s, '[]')
 ) AS h
 UNION ALL
 SELECT srvid, name, (ioc.record).*
 FROM {powa}.powa_stat_slru_history_current ioc
 WHERE  (ioc.record).ts <@ tstzrange(%(from)s, %(to)s, '[]')
 AND ioc.srvid = %(server)s
) AS io_history
    """
    return base_query


def powa_getslrudata(qual=None):
    """
    Query used in the grid displaying info about pg_stat_slru.
    """
    base_query = powa_base_slru()

    if qual is not None:
        qual = " WHERE %s" % qual
    else:
        qual = ""

    base_cols = [
        "srvid",
        "name",
    ]

    cols = [
        diffblk("blks_zeroed", "block_size"),
        diffblk("blks_hit", "block_size"),
        diffblk("blks_read", "block_size"),
        diffblk("blks_written", "block_size"),
        diffblk("blks_exists", "block_size"),
        diff("flushes"),
        diff("truncates"),
    ]

    return """SELECT {base_cols}, {cols}
    FROM {base_query}
    CROSS JOIN {block_size}
    {qual}
    GROUP BY {base_cols}, block_size""".format(
        cols=", ".join(cols),
        base_cols=", ".join(base_cols),
        base_query=base_query,
        block_size=block_size,
        qual=qual,
    )


def get_diffs_forstatdata():
    return [
        diff("calls"),
        diff("total_plan_time", "plantime"),
        diff("total_exec_time", "runtime"),
        diff("shared_blks_read"),
        diff("shared_blks_hit"),
        diff("shared_blks_dirtied"),
        diff("shared_blks_written"),
        diff("temp_blks_read"),
        diff("temp_blks_written"),
        diff("shared_blk_read_time"),
        diff("shared_blk_write_time"),
        diff("local_blk_read_time"),
        diff("local_blk_write_time"),
        diff("temp_blk_read_time"),
        diff("temp_blk_write_time"),
        diff("wal_records"),
        diff("wal_fpi"),
        diff("wal_bytes"),
        diff("jit_functions"),
        diff("jit_generation_time"),
        diff("jit_inlining_count"),
        diff("jit_inlining_time"),
        diff("jit_optimization_count"),
        diff("jit_optimization_time"),
        diff("jit_emission_count"),
        diff("jit_emission_time"),
        diff("jit_deform_count"),
        diff("jit_deform_time"),
    ]


def powa_getstatdata_detailed_db(srvid="%(server)s", predicates=[]):
    """
    Query used in the grids displaying info about pgss.

    This is based on the "detailed" version of the tables, with queryid
    information.

    predicates is an optional array of plain-text predicates.
    """
    base_query = powa_base_statdata_detailed_db()
    diffs = get_diffs_forstatdata()

    where = " AND ".join(predicates)
    if where != "":
        where = " AND " + where

    cols = [
        "srvid",
        "queryid",
        "dbid",
        "toplevel",
        "userid",
        "datname",
    ] + diffs

    return """SELECT {cols}
    FROM {base_query}
    WHERE srvid = {srvid}
    {where}
    GROUP BY srvid, queryid, dbid, toplevel, userid, datname
    HAVING max(calls) - min(calls) > 0""".format(
        cols=", ".join(cols), base_query=base_query, srvid=srvid, where=where
    )


def powa_getstatdata_db(srvid):
    """
    Query used in the grids displaying info about pgss.

    This is based on the db-aggregated version of the tables, without queryid
    information.
    """
    base_query = powa_base_statdata_db()
    diffs = get_diffs_forstatdata()

    cols = ["srvid", "dbid"] + diffs

    return """SELECT {cols}
    FROM {base_query}
    WHERE srvid = {srvid}
    GROUP BY srvid, dbid
    HAVING max(calls) - min(calls) > 0""".format(
        cols=", ".join(cols), base_query=base_query, srvid=srvid
    )


def powa_base_waitdata_detailed_db():
    """
    Query used in the grids displaying info about pg_wait_sampling.

    This is based on the "detailed" version of the tables, with queryid
    information.

    This uses the same optimization as powa_base_statdata_detailed_db.
    """
    base_query = """
  {powa}.powa_databases,
  LATERAL
  (
    -- Left bound: the search interval is a single timestamp, the smallest one
    -- of the search interval, and has to be inside the coalesce_range. We
    -- still need to unnest this one as we may have to remove some of the
    -- underlying records
    SELECT unnested.dbid, unnested.queryid,
      unnested.event_type, unnested.event, (unnested.records).*
    FROM (
      SELECT wsh.dbid, wsh.queryid, wsh.event_type, wsh.event,
        wsh.coalesce_range, unnest(records) AS records
      FROM {powa}.powa_wait_sampling_history wsh
      WHERE coalesce_range && tstzrange(%(from)s, %(from)s, '[]')
      AND wsh.dbid = powa_databases.oid
      -- we can't simply join powa_statements as there's no userid in
      -- powa_wait_sampling_* tables
      AND wsh.srvid = %(server)s
    ) AS unnested
    WHERE  (records).ts <@ tstzrange(%(from)s, %(to)s, '[]')

    UNION ALL

    -- Right bound: the search interval is a single timestamp, the largest one
    -- of the search interval, and has to be inside the coalesce_range. We
    -- still need to unnest this one as we may have to remove some of the
    -- underlying records
    SELECT unnested.dbid, unnested.queryid,
      unnested.event_type, unnested.event, (unnested.records).*
    FROM (
      SELECT wsh.dbid, wsh.queryid, wsh.event_type, wsh.event,
        wsh.coalesce_range, unnest(records) AS records
      FROM {powa}.powa_wait_sampling_history wsh
      WHERE coalesce_range && tstzrange(%(to)s, %(to)s, '[]')
      AND wsh.dbid = powa_databases.oid
      -- we can't simply join powa_statements as there's no userid in
      -- powa_wait_sampling_* tables
      AND wsh.srvid = %(server)s
    ) AS unnested
    WHERE  (records).ts <@ tstzrange(%(from)s, %(to)s, '[]')

    UNION ALL

    -- These entries have their coalesce_range ENTIRELY inside the search range
    -- so we don't need to unnest them.  We just retrieve the mins_in_range,
    -- maxs_in_range from the record, build an array of this and return it as
    -- if it was the full record
    SELECT unnested.dbid, unnested.queryid,
      unnested.event_type, unnested.event, (unnested.records).*
    FROM (
      SELECT wsh.dbid, wsh.queryid, wsh.event_type, wsh.event,
        wsh.coalesce_range,
        unnest(ARRAY[mins_in_range,maxs_in_range]) AS records
      FROM {powa}.powa_wait_sampling_history wsh
      WHERE coalesce_range && tstzrange(%(from)s, %(to)s, '[]')
      AND wsh.dbid = powa_databases.oid
      -- we can't simply join powa_statements as there's no userid in
      -- powa_wait_sampling_* tables
      AND wsh.srvid = %(server)s
    ) AS unnested
    WHERE  (records).ts <@ tstzrange(%(from)s, %(to)s, '[]')

    UNION ALL

    -- The "current" records are simply returned after filtering
    SELECT wsc.dbid, wsc.queryid, wsc.event_type, wsc.event, (wsc.record).*
    FROM {powa}.powa_wait_sampling_history_current wsc
    WHERE (record).ts <@ tstzrange(%(from)s,%(to)s,'[]')
    AND wsc.dbid = powa_databases.oid
    -- we can't simply join powa_statements as there's no userid in
    -- powa_wait_sampling_* tables
    AND wsc.srvid = %(server)s
  ) h
  WHERE powa_databases.srvid = %(server)s
"""
    return base_query


def powa_base_waitdata_db():
    """
    Query used in the grids displaying info about pg_wait_sampling.

    This is based on the db-aggregated version of the tables, without queryid
    information.

    This uses the same optimization as powa_base_statdata_detailed_db.
    """
    base_query = """(
  SELECT powa_databases.srvid, powa_databases.oid as dbid,
    powa_databases.datname, h.*
  FROM
  {powa}.powa_databases LEFT JOIN
  (
    SELECT dbid
    FROM {powa}.powa_wait_sampling_history_db wsh
    WHERE coalesce_range && tstzrange(%(from)s, %(to)s, '[]')
    AND wsh.srvid = %(server)s
    GROUP BY dbid
  ) ranges ON powa_databases.oid = ranges.dbid,
  LATERAL (
    -- Left bound: the search interval is a single timestamp, the smallest one
    -- of the search interval, and has to be inside the coalesce_range. We
    -- still need to unnest this one as we may have to remove some of the
    -- underlying records
    SELECT event_type, event, (unnested1.records).*
    FROM (
      SELECT wsh.event_type, wsh.event, unnest(records) AS records
      FROM {powa}.powa_wait_sampling_history_db wsh
      WHERE coalesce_range && tstzrange(%(from)s, %(from)s, '[]')
      AND wsh.dbid = ranges.dbid
      AND wsh.srvid = %(server)s
    ) AS unnested1
    WHERE (unnested1.records).ts <@ tstzrange(%(from)s, %(to)s, '[]')

    UNION ALL

    -- Right bound: the search interval is a single timestamp, the largest one
    -- of the search interval, and has to be inside the coalesce_range. We
    -- still need to unnest this one as we may have to remove some of the
    -- underlying records
    SELECT event_type, event, (unnested1.records).*
    FROM (
      SELECT wsh.event_type, wsh.event, unnest(records) AS records
      FROM {powa}.powa_wait_sampling_history_db wsh
      WHERE coalesce_range && tstzrange(%(to)s, %(to)s, '[]')
      AND wsh.dbid = ranges.dbid
      AND wsh.srvid = %(server)s
    ) AS unnested1
    WHERE (unnested1.records).ts <@ tstzrange(%(from)s, %(to)s, '[]')

    UNION ALL

    -- These entries have their coalesce_range ENTIRELY inside the search range
    -- so we don't need to unnest them.  We just retrieve the mins_in_range,
    -- maxs_in_range from the record, build an array of this and return it as
    -- if it was the full record
    SELECT event_type, event, (unnested1.records).*
    FROM (
      SELECT wsh.event_type, wsh.event,
        unnest(ARRAY[mins_in_range,maxs_in_range]) AS records
      FROM {powa}.powa_wait_sampling_history_db wsh
      WHERE coalesce_range && tstzrange(%(from)s, %(to)s, '[]')
      AND wsh.dbid = ranges.dbid
      AND wsh.srvid = %(server)s
    ) AS unnested1
    WHERE (unnested1.records).ts <@ tstzrange(%(from)s, %(to)s, '[]')

    UNION ALL

    -- The "current" records are simply returned after filtering
    SELECT event_type, event, (wsc.record).*
    FROM {powa}.powa_wait_sampling_history_current_db wsc
    WHERE (wsc.record).ts <@ tstzrange(%(from)s, %(to)s, '[]')
    AND wsc.dbid = powa_databases.oid
    AND wsc.srvid = %(server)s
  ) AS h
  WHERE powa_databases.srvid = %(server)s
) AS ws_history
    """
    return base_query


def powa_getwaitdata_detailed_db():
    """
    Query used in the grids displaying info about pg_wait_sampling.

    This is based on the "detailed" version of the tables, with queryid
    information.
    """
    base_query = powa_base_waitdata_detailed_db()
    return """SELECT srvid, queryid, dbid, datname, event_type, event,
    {count}
    FROM {base_query}
    GROUP BY srvid, queryid, dbid, datname, event_type, event
    HAVING max(count) - min(count) > 0""".format(
        count=diff("count"), base_query=base_query
    )


def powa_getwaitdata_db():
    """
    Query used in the grids displaying info about pg_wait_sampling.

    This is based on the db-aggregated version of the tables, without queryid
    information.
    """
    base_query = powa_base_waitdata_db()

    return """SELECT srvid, dbid, event_type, event, {count}
    FROM {base_query}
    GROUP BY srvid, dbid, event_type, event
    HAVING max(count) - min(count) > 0""".format(
        count=diff("count"), base_query=base_query
    )


def powa_base_userfuncdata_detailed_db():
    """
    Base for query used in the grids displaying info about
    pg_stat_user_functions.

    This is based on the "detailed" version of the tables, with per-function
    information.

    This uses the same optimization as powa_base_statdata_detailed_db.
    """
    base_query = """
  {powa}.powa_databases d
  JOIN LATERAL
  (
    -- Left bound: the search interval is a single timestamp, the smallest one
    -- of the search interval, and has to be inside the coalesce_range. We
    -- still need to unnest this one as we may have to remove some of the
    -- underlying records
    SELECT unnested.dbid, unnested.funcid,
      (unnested.records).*
    FROM (
      SELECT ufh.dbid, ufh.funcid,
        ufh.coalesce_range, unnest(records) AS records
      FROM {powa}.powa_user_functions_history ufh
      WHERE coalesce_range && tstzrange(%(from)s, %(from)s, '[]')
      AND ufh.dbid = d.oid
      AND ufh.srvid = %(server)s
    ) AS unnested
    WHERE (records).ts <@ tstzrange(%(from)s, %(to)s, '[]')

    UNION ALL

    -- Right bound: the search interval is a single timestamp, the largest one
    -- of the search interval, and has to be inside the coalesce_range. We
    -- still need to unnest this one as we may have to remove some of the
    -- underlying records
    SELECT unnested.dbid, unnested.funcid,
      (unnested.records).*
    FROM (
      SELECT ufh.dbid, ufh.funcid,
        ufh.coalesce_range, unnest(records) AS records
      FROM {powa}.powa_user_functions_history ufh
      WHERE coalesce_range && tstzrange(%(to)s, %(to)s, '[]')
      AND ufh.dbid = d.oid
      AND ufh.srvid = %(server)s
    ) AS unnested
    WHERE (records).ts <@ tstzrange(%(from)s, %(to)s, '[]')

    UNION ALL

    -- These entries have their coalesce_range ENTIRELY inside the search range
    -- so we don't need to unnest them.  We just retrieve the mins_in_range,
    -- maxs_in_range from the record, build an array of this and return it as
    -- if it was the full record
    SELECT unnested.dbid, unnested.funcid,
      (unnested.records).*
    FROM (
      SELECT ufh.dbid, ufh.funcid,
        ufh.coalesce_range,
        unnest(ARRAY[mins_in_range,maxs_in_range]) AS records
      FROM {powa}.powa_user_functions_history ufh
      WHERE coalesce_range && tstzrange(%(from)s, %(to)s, '[]')
      AND ufh.dbid = d.oid
      AND ufh.srvid = %(server)s
    ) AS unnested
    WHERE (records).ts <@ tstzrange(%(from)s, %(to)s, '[]')

    UNION ALL

    -- The "current" records are simply returned after filtering
    SELECT ufc.dbid, ufc.funcid, (ufc.record).*
    FROM {powa}.powa_user_functions_history_current ufc
    WHERE (record).ts <@ tstzrange(%(from)s,%(to)s,'[]')
    AND ufc.dbid = d.oid
    AND ufc.srvid = %(server)s
  ) h ON d.srvid = %(server)s
  LEFT JOIN {powa}.powa_catalog_proc pcp
    ON pcp.dbid = h.dbid AND pcp.oid = h.funcid AND pcp.srvid = d.srvid
        AND pcp.srvid = %(server)s
  LEFT JOIN {powa}.powa_catalog_language pcl
    ON pcl.srvid = pcp.srvid AND pcl.dbid = pcp.dbid AND pcl.oid = pcp.prolang"""
    return base_query


def powa_base_userfuncdata_db():
    """
    Base for query used in the grids displaying info about
    pg_stat_user_functions.

    This is based on the db-aggregated version of the tables, without
    per-function information.

    This uses the same optimization as powa_base_statdata_detailed_db.
    """
    base_query = """
  {powa}.powa_databases d,
  LATERAL
  (
    -- Left bound: the search interval is a single timestamp, the smallest one
    -- of the search interval, and has to be inside the coalesce_range. We
    -- still need to unnest this one as we may have to remove some of the
    -- underlying records
    SELECT unnested.dbid,
      (unnested.records).*
    FROM (
      SELECT ufhd.dbid,
        ufhd.coalesce_range, unnest(records) AS records
      FROM {powa}.powa_user_functions_history_db ufhd
      WHERE coalesce_range && tstzrange(%(from)s, %(from)s, '[]')
      AND ufhd.dbid = d.oid
      AND ufhd.srvid = %(server)s
    ) AS unnested
    WHERE (records).ts <@ tstzrange(%(from)s, %(to)s, '[]')

    UNION ALL

    -- Right bound: the search interval is a single timestamp, the largest one
    -- of the search interval, and has to be inside the coalesce_range. We
    -- still need to unnest this one as we may have to remove some of the
    -- underlying records
    SELECT unnested.dbid,
      (unnested.records).*
    FROM (
      SELECT ufhd.dbid,
        ufhd.coalesce_range, unnest(records) AS records
      FROM {powa}.powa_user_functions_history_db ufhd
      WHERE coalesce_range && tstzrange(%(to)s, %(to)s, '[]')
      AND ufhd.dbid = d.oid
      AND ufhd.srvid = %(server)s
    ) AS unnested
    WHERE (records).ts <@ tstzrange(%(from)s, %(to)s, '[]')

    UNION ALL

    -- These entries have their coalesce_range ENTIRELY inside the search range
    -- so we don't need to unnest them.  We just retrieve the mins_in_range,
    -- maxs_in_range from the record, build an array of this and return it as
    -- if it was the full record
    SELECT unnested.dbid,
      (unnested.records).*
    FROM (
      SELECT ufhd.dbid,
        ufhd.coalesce_range,
        unnest(ARRAY[mins_in_range,maxs_in_range]) AS records
      FROM {powa}.powa_user_functions_history_db ufhd
      WHERE coalesce_range && tstzrange(%(from)s, %(to)s, '[]')
      AND ufhd.dbid = d.oid
      AND ufhd.srvid = %(server)s
    ) AS unnested
    WHERE (records).ts <@ tstzrange(%(from)s, %(to)s, '[]')

    UNION ALL

    -- The "current" records are simply returned after filtering
    SELECT ufcd.dbid, (ufcd.record).*
    FROM {powa}.powa_user_functions_history_current_db ufcd
    WHERE (record).ts <@ tstzrange(%(from)s,%(to)s,'[]')
    AND ufcd.dbid = d.oid
    AND ufcd.srvid = %(server)s
  ) h
  LEFT JOIN {powa}.powa_catalog_proc pcp
    ON pcp.dbid = h.dbid AND pcp.srvid = %(server)s
  WHERE d.srvid = pcp.srvid"""
    return base_query


def powa_getuserfuncdata_detailed_db(funcid=None):
    """
    Query used in the grids displaying info about pg_stat_user_functions.

    This is based on the "detailed" version of the tables, with per-function
    information.
    """
    base_query = powa_base_userfuncdata_detailed_db()

    cols = [
        "d.srvid",
        "h.dbid",
        "d.datname",
        "funcid",
        "coalesce(regprocedure, '<' || funcid || '>') AS func_name",
        "lanname",
        diff("calls"),
        diff("total_time"),
        diff("self_time"),
    ]
    if funcid:
        cols.extend(["prosrc", "last_refresh"])

    groupby = [
        "d.srvid",
        "h.dbid",
        "d.datname",
        "funcid",
        "regprocedure",
        "lanname",
    ]
    if funcid:
        groupby.extend(["prosrc", "last_refresh"])

    if funcid:
        join_db = """INNER JOIN {powa}.powa_databases pd
            ON pd.srvid = d.srvid AND pd.oid = h.dbid"""
        and_funcid = "AND funcid = {funcid}".format(funcid=funcid)
    else:
        join_db = ""
        and_funcid = ""

    return """SELECT {cols}
    FROM {base_query}
    {join_db}
    WHERE d.datname = %(database)s
    {and_funcid}
    GROUP BY {groupby}
    HAVING max(calls) - min(calls) > 0""".format(
        cols=", ".join(cols),
        base_query=base_query,
        join_db=join_db,
        and_funcid=and_funcid,
        groupby=", ".join(groupby),
    )


def powa_getuserfuncdata_db():
    """
    Query used in the grids displaying info about pg_stat_user_functions.

    This is based on the db-aggregated version of the tables, without
    per-function information.
    """
    base_query = powa_base_userfuncdata_db()

    cols = [
        "d.srvid",
        "d.datname",
        "h.dbid",
        diff("calls"),
        diff("total_time"),
        diff("self_time"),
    ]

    return """SELECT {cols}
    FROM {base_query}
    GROUP BY d.srvid, d.datname, h.dbid, d.oid
    HAVING max(calls) - min(calls) > 0""".format(
        cols=", ".join(cols), base_query=base_query
    )
