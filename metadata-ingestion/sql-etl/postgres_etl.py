from common import run

# See https://docs.sqlalchemy.org/en/13/dialects/postgresql.html#module-sqlalchemy.dialects.postgresql.psycopg2 for more details
URL = '' # e.g. postgresql+psycopg2://user:password@host:port
OPTIONS = {"echo": True} # e.g. {"client_encoding": "utf8"}
PLATFORM = 'postgresql'
SCHEMA_BLACKLIST = ["_fivetran_staging", "admin", "attribution_testing", "bdrupieski_dev", "brazetest_local", "granttest_segment_data_lake", "information_schema"]

run(URL, OPTIONS, PLATFORM, SCHEMA_BLACKLIST)