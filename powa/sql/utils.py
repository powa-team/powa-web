from sqlalchemy import select, cast, func
from sqlalchemy.types import Numeric
from sqlalchemy.sql import extract, column, case, table, column
from sqlalchemy.sql.functions import sum, min, max

block_size = select([cast(func.current_setting('block_size'), Numeric)
                     .label('block_size')]).alias('block_size')

powa_statements = table("powa_statements",
                   column("query"),
                   column("md5query"),
                   column("dbname"))

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
               + c.temp_blks_read) * bs).label("total_blks_read")

def total_hit(c):
    bs = block_size.c.block_size
    return ((sum(c.shared_blks_hit + c.local_blks_hit) * bs)
            .label("total_blks_hit"))
