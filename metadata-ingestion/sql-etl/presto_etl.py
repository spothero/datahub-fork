from common import run

# See https://github.com/dropbox/PyHive for more details
URL = '' # e.g. presto://user:password@host:port
OPTIONS = {"echo": True, "connect_args": {"protocol": "https"}}
PLATFORM = 'presto'
SCHEMA_BLACKLIST = ['brazetest_local', 'granttest_segment_data_lake', 'information_schema', 'presto_performance_testing', 'segment_local', 'segment_processed_local', 'spark_pipegen_local', 'yield_management_local', 'zack_test']

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