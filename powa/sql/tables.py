from sqlalchemy.sql import table, column

powa_statements = table("powa_statements",
                        column("query"),
                        column("queryid"),
                        column("dbid"),
                        column("userid"))

pg_database = table(
    "pg_database",
    column("oid"),
    column("datname"))

