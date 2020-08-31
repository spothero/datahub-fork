from common import run

# See https://docs.sqlalchemy.org/en/13/dialects/postgresql.html#module-sqlalchemy.dialects.postgresql.psycopg2 for more details
URL = '' # e.g. postgresql+psycopg2://user:password@host:port
OPTIONS = {"echo": True} # e.g. {"client_encoding": "utf8"}
PLATFORM = 'redshift'
SCHEMA_BLACKLIST = ["_fivetran_staging", "admin", "attribution_testing", "bdrupieski_dev", "information_schema", "inventory_local", "maggiehays", "money_squad_test", "pipegen_local", "segment_local", "test_grant", "user_deliverability_local", "weather_local"]

run(URL, OPTIONS, PLATFORM, SCHEMA_BLACKLIST)