from common import run

# See https://docs.sqlalchemy.org/en/13/dialects/postgresql.html#module-sqlalchemy.dialects.postgresql.psycopg2 for more details
URL = '' # e.g. postgresql+psycopg2://user:password@host:port
OPTIONS = {"echo": True} # e.g. {"client_encoding": "utf8"}
PLATFORM = 'redshift'
SCHEMA_BLACKLIST = ["_fivetran_staging", "admin", "attribution_testing", "bdrupieski_dev", "information_schema", "inventory_local", "maggiehays", "money_squad_test", "pipegen_local", "segment_local", "test_grant", "user_deliverability_local", "weather_local"]

# Modify to use your cert files from aiven (no java keystores!)
EXTRA_KAFKA_CONF = {
  'bootstrap.servers': '',
  'schema.registry.url': '',
  'security.protocol': 'SSL',
  'ssl.ca.location': '/Users/grant.nicholas/.kafka/data_stg/ca.pem',
  'ssl.key.location': '/Users/grant.nicholas/.kafka/data_stg/service.key',
  'ssl.certificate.location': '/Users/grant.nicholas/.kafka/data_stg/service.cert'
}

run(URL, OPTIONS, PLATFORM, EXTRA_KAFKA_CONF, SCHEMA_BLACKLIST)