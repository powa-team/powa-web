from sqlalchemy import select, cast, func
from sqlalchemy.types import Numeric
from sqlalchemy.sql import (extract, column, case, table, column, text,
                            ColumnCollection)
from sqlalchemy.sql.functions import sum, min, max
from powa.sql import qual_constants

block_size = select([cast(func.current_setting('block_size'), Numeric)
                     .label('block_size')]).alias('block_size')


round = func.round
greatest = func.greatest
least = func.least

def mulblock(column, label=None):
    return (column * block_size.c.block_size).label(label or column.name)

def total_measure_interval(column):
    return extract(
        "epoch",
        case([(min(column) == '0 second', '1 second')],
             else_= min(column)))


def diff(var):
    return (max(column(var)) - min(column(var))).label(var)

def to_epoch(column):
    return extract("epoch", column).label(column.name)


def total_read(c):
    bs = block_size.c.block_size
    return (sum(c.shared_blks_read + c.local_blks_read
               + c.temp_blks_read) * bs /
            total_measure_interval(c.mesure_interval)).label("total_blks_read")

def total_hit(c):
    bs = block_size.c.block_size
    return ((sum(c.shared_blks_hit + c.local_blks_hit) * bs /
            total_measure_interval(c.mesure_interval))
            .label("total_blks_hit"))

def inner_cc(selectable):
    new_cc = ColumnCollection()
    for c in selectable.inner_columns:
        new_cc.add(c)
    return new_cc

def qualstat_get_figures(conn, database, query, tsfrom, tsto):
    condition = text("""datname = :database AND s.queryid = :query
             AND coalesce_range && tstzrange(:from, :to)""")
    sql = (select(['most_filtering.quals',
                  'most_filtering.query',
                  'to_json(most_filtering) as "most filtering"',
                  'to_json(least_filtering) as "least filtering"',
                  'to_json(most_executed) as "most executed"'])
           .select_from(
               qual_constants("most_filtering", condition)
               .alias("most_filtering")
               .join(
                   qual_constants("least_filtering", condition)
                   .alias("least_filtering"),
                   text("most_filtering.rownumber = "
                        "least_filtering.rownumber"))
               .join(qual_constants("most_executed", condition)
                     .alias("most_executed"),
                     text("most_executed.rownumber = "
                          "least_filtering.rownumber"))))

    params = {"database": database, "query": query,
              "from": tsfrom,
              "to": tsto}
    quals = conn.execute(sql, params=params)

    if quals.rowcount == 0:
        return None

    row = quals.first()

    return row

