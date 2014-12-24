"""
Utilities for commonly used SQL constructs.
"""
from sqlalchemy.types import String, Integer, DateTime, Numeric
from sqlalchemy.sql import table, func, case, literal, text, bindparam
from sqlalchemy.dialects.postgresql import INTERVAL

TOTAL_MEASURE_INTERVAL = """
extract( epoch from
    CASE WHEN min(total_mesure_interval) = '0 second'
        THEN '1 second'::interval
    ELSE min(total_mesure_interval) END)
"""
