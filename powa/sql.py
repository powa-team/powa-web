"""
Utilities for commonly used SQL constructs.
"""
from sqlalchemy.types import String, Integer, DateTime, Numeric
from sqlalchemy.sql import table, func, case, literal, text, bindparam
from sqlalchemy.dialects.postgresql import INTERVAL
import re
from collections import namedtuple

TOTAL_MEASURE_INTERVAL = """
extract( epoch from
    CASE WHEN min(total_mesure_interval) = '0 second'
        THEN '1 second'::interval
    ELSE min(total_mesure_interval) END)
"""

def format_jumbled_query(sql, params):
    it = iter(params)
    sql = re.sub("\?", lambda val: next(it), sql)
    return sql

Plan = namedtuple("Plan", ("title", "values", "query", "plan", "filter_ratio", "exec_count"))
