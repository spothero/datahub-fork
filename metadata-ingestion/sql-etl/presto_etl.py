from common import run

# See https://github.com/dropbox/PyHive for more details
URL = '' # e.g. presto://user:password@host:port
OPTIONS = {"echo": True, "connect_args": {"protocol": "https"}}
PLATFORM = 'presto'
SCHEMA_BLACKLIST = []

run(URL, OPTIONS, PLATFORM, SCHEMA_BLACKLIST)