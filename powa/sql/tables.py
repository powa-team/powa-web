from sqlalchemy.sql import table, column

powa_statements = table("powa_statements",
                        column("query"),
                        column("queryid"),
                        column("dbid"),
                        column("userid"))

powa_databases = table(
    "powa_databases",
    column("oid"),
    column("datname"))

