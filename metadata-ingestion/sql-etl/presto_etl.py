from common import run

# See https://github.com/dropbox/PyHive for more details
URL = '' # e.g. presto://user:password@host:port
OPTIONS = {"echo": True, "connect_args": {"protocol": "https"}}
PLATFORM = 'presto'
SCHEMA_BLACKLIST = ['brazetest_local', 'granttest_segment_data_lake', 'information_schema', 'presto_performance_testing', 'segment_local', 'segment_processed_local', 'spark_pipegen_local', 'yield_management_local', 'zack_test']

run(URL, OPTIONS, PLATFORM, SCHEMA_BLACKLIST)