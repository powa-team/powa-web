from datetime import datetime
from sqlalchemy.types import String, Integer, DateTime, Numeric
from sqlalchemy.sql import table, func, case, literal, text, bindparam
from sqlalchemy.dialects.postgresql import INTERVAL

def date_parser(value):
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S%z")


DBLIST = (
    table("public.powa_statements").select("dbname").distinct()
    .order_by("dbname"))


