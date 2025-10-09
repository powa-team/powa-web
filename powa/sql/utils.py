block_size = (
    "(SELECT cast(current_setting('block_size') AS numeric)"
    " AS block_size) AS bs"
)


def mulblock(col, alias=None, fn=None):
    alias = alias or col

    if fn is None:
        sql = "{col}"
    else:
        sql = "{fn}({col})"

    sql += " * block_size AS {alias}"

    return sql.format(col=col, alias=alias, fn=fn)


def total_measure_interval(col):
    sql = (
        "extract(epoch FROM "
        + " CASE WHEN min({col}) = '0 second' THEN '1 second'"
        + " ELSE min({col})"
        + "END)"
    )

    return sql.format(col=col)


def diff(var, alias=None):
    alias = alias or var
    return "max({var}) - min({var}) AS {alias}".format(var=var, alias=alias)


def diffblk(var, blksize=8192, alias=None):
    alias = alias or var
    return "(max({var}) - min({var})) * {blksize} AS {alias}".format(
        var=var, blksize=blksize, alias=alias
    )


def get_ts():
    return "extract(epoch FROM greatest(mesure_interval, '1 second'))"


def sum_per_sec(col, prefix=None, alias=None):
    alias = alias or col
    if prefix is not None:
        prefix = prefix + "."
    else:
        prefix = ""

    return "sum({prefix}{col}) / {ts} AS {alias}".format(
        prefix=prefix, col=col, ts=get_ts(), alias=alias
    )


def byte_per_sec(col, prefix=None, alias=None):
    alias = alias or col
    if prefix is not None:
        prefix = prefix + "."
    else:
        prefix = ""

    return "sum({prefix}{col}) * block_size / {ts} AS {alias}".format(
        prefix=prefix, col=col, ts=get_ts(), alias=alias
    )


def wps(col, do_sum=True):
    field = "sub." + col
    if do_sum:
        field = "sum(" + field + ")"

    return "({field} / {ts}) AS {col}".format(
        field=field, col=col, ts=get_ts()
    )


def to_epoch(col, prefix=None):
    if prefix is not None:
        qn = "{prefix}.{col}".format(prefix=prefix, col=col)
    else:
        qn = col

    return "extract(epoch FROM {qn}) AS {col}".format(qn=qn, col=col)


def total_read(prefix, noalias=False):
    if noalias:
        alias = ""
    else:
        alias = " AS total_blks_read"

    sql = (
        "sum({prefix}.shared_blks_read"
        + "+ {prefix}.local_blks_read"
        + "+ {prefix}.temp_blks_read"
        ") * block_size / {total_measure_interval}{alias}"
    )

    return sql.format(
        prefix=prefix,
        total_measure_interval=total_measure_interval("mesure_interval"),
        alias=alias,
    )


def total_hit(c):
    return (
        "sum(shared_blks_hit + local_blks_hit) * block_size /"
        + total_measure_interval("mesure_interval")
        + " AS total_blks_hit"
    )
