#! /usr/bin/python
import time
import glob
import typing 
import yaml


from dataclasses import dataclass

from confluent_kafka import avro
from confluent_kafka.avro import AvroProducer

# Configuration
AVSC_PATH = "../../metadata-events/mxe-schemas/src/renamed/avro/com/linkedin/mxe/MetadataChangeEvent.avsc"
KAFKA_TOPIC = 'MetadataChangeEvent_v4'

PIPEGEN_DIRECTORY = "./test_pipegen"

EXTRA_KAFKA_CONF = {
  'bootstrap.servers': 'localhost:9092',
  'schema.registry.url': 'http://localhost:8081'
  # 'security.protocol': 'SSL',
  # 'ssl.ca.location': '/Users/grant.nicholas/.kafka/data_stg/ca.pem',
  # 'ssl.key.location': '/Users/grant.nicholas/.kafka/data_stg/service.key',
  # 'ssl.certificate.location': '/Users/grant.nicholas/.kafka/data_stg/service.cert'
}


@dataclass(frozen=True)
class Dependency:
	source: str 
	table: str

@dataclass
class PipegenSpec:
	name: str
	description: str 
	target_table_name: str
	data_dependencies:  typing.List[Dependency]
	scheduling_dependencies: typing.List[Dependency]
	source: str
	enabled_for_scheduling: bool

	def all_data_dependencies(self):
		return set(self.data_dependencies).union(
			set(self.scheduling_dependencies)
		)


def file_to_pipegen_spec(file_name):
	with open(file_name, "r") as f: 
		return file_contents_to_pipegen_spec(yaml.safe_load(f))

def file_contents_to_pipegen_spec(file_obj):
	data_dependencies = file_obj.get("DataDependencies", [])
	scheduling_dependencies = file_obj.get("SchedulingDependencies", [])

	mapped_data_dependencies = [ Dependency(d["Source"], d["Name"]) for d in data_dependencies]
	mapped_scheduling_dependencies = [ Dependency(d["Source"], f"pipegen.{d['Name']}") for d in scheduling_dependencies]

	return PipegenSpec(
		name = file_obj["Name"],
		description = file_obj["Description"],
		target_table_name = file_obj["TargetTableName"],
		data_dependencies = mapped_data_dependencies,
		scheduling_dependencies = mapped_scheduling_dependencies,
		source = file_obj["Source"],
		enabled_for_scheduling = file_obj.get("EnabledForScheduling", True)
	)


def construct_data_urn(pipegen_spec):
	if pipegen_spec.source == "Presto":
		# pipegen stores metadata in hive_emr not glue
		platform = "presto_hive"
		table_name = f"pipegen.{pipegen_spec.target_table_name}"

	elif pipegen_spec.source in ("Redshift", "PrestoToRedshift"):
		platform = "redshift"
		table_name = f"pipegen.{pipegen_spec.target_table_name}"		

	else:
		raise Exception(f"Unknown source: {pipegen_spec.source}")		


	return f"urn:li:dataset:(urn:li:dataPlatform:{platform},{table_name},PROD)"


def construct_datalineage_urn(data_dependency):
	if data_dependency.source == "Presto":
		parts = data_dependency.table.split(".")
		catalog = parts[0]

		if catalog == "hive":
			platform = "presto_glue"
		elif catalog == "hive_emr":
			platform = "presto_hive"
		else:
			raise Exception(f"Unknown catalog: {catalog} for data_dependency: {data_dependency.table}")

		table_name = ".".join(parts[1::])

	elif data_dependency.source == "Redshift":
		platform = "redshift"
		table_name = data_dependency.table

	else:
		raise Exception(f"Unknown source: {data_dependency.source}")
		
	return f"urn:li:dataset:(urn:li:dataPlatform:{platform},{table_name},PROD)"

def build_dataset_mce(pipegen_spec):
    """
    Creates MetadataChangeEvent for the dataset, creating upstream lineage links
    """
    actor, sys_time = "urn:li:corpuser:etl", int(time.time())

    upstreams = [{
    	"auditStamp":{
    		"time": sys_time,
    		"actor":actor
    	},
    	"dataset": construct_datalineage_urn(dep),
    	"type":"TRANSFORMED"
    } for dep in pipegen_spec.all_data_dependencies()]

    return {
        "auditHeader": None,
        "proposedSnapshot":("com.linkedin.pegasus2avro.metadata.snapshot.DatasetSnapshot", {
            "urn": construct_data_urn(pipegen_spec),
            "aspects": [
            	("com.linkedin.pegasus2avro.dataset.UpstreamLineage", {"upstreams": upstreams})
            ]
        }),
        "proposedDelta": None
    }


def delivery_report(err, msg):
    """ Called once for each message produced to indicate delivery result.
        Triggered by poll() or flush(). """
    if err is not None:
        print('Message delivery failed: {}'.format(err))
    else:
        print('Message delivered to {} [{}]'.format(msg.topic(), msg.partition()))


def make_kafka_producer(extra_kafka_conf):
	conf = {
		"on_delivery": delivery_report,
		**extra_kafka_conf
	}

	key_schema = avro.loads('{"type": "string"}')
	record_schema = avro.load(AVSC_PATH)
	producer = AvroProducer(conf, default_key_schema=key_schema, default_value_schema=record_schema)
	return producer


def main():
	kafka_producer = make_kafka_producer(EXTRA_KAFKA_CONF)
	files = [f for f in glob.glob(f"{PIPEGEN_DIRECTORY}/*.yaml")]
	for fn in files:
		pipegen_spec = file_to_pipegen_spec(fn)
		mce = build_dataset_mce(pipegen_spec)

		print(pipegen_spec)
		print(mce)
		print("---")

		kafka_producer.produce(topic=KAFKA_TOPIC, key=mce['proposedSnapshot'][1]['urn'], value=mce)
		kafka_producer.flush()


if __name__ == "__main__":
	main()

