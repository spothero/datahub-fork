#! /usr/bin/python
import time
import os
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

	def get_platform_and_table(self):
		raise NotImplementedError("Subclass of Dependency must override get_platform_and_table")

	def construct_datalineage_urn(self):
		platform, table_name = self.get_platform_and_table()
		return f"urn:li:dataset:(urn:li:dataPlatform:{platform},{table_name},PROD)"


class DataDependency(Dependency):
	def get_platform_and_table(self):
		"""
		Data dependencies use fully qualified table names like:
		Presto -> hive.segment.tracks
		Redshift -> sh_public.rental
		"""
		if self.source == "Presto":
			parts = self.table.split(".")
			catalog = parts[0]

			if catalog == "hive":
				platform = "presto_glue"
			elif catalog == "hive_emr":
				platform = "presto_hive"
			else:
				raise Exception(f"Unknown catalog: {catalog} for data_dependency: {self.table}")

			table_name = ".".join(parts[1::])

			return platform, table_name

		elif self.source == "Redshift":
			platform = "redshift"
			table_name = self.table

			return platform, table_name

		else:
			raise Exception(f"Unknown source: {self.source}")


class SchedulingDependency(Dependency):
	def get_platform_and_table(self):
		"""
		Scheduling dependencies do *not* use fully qualified table names
		This is because scheduling dependencies can only occur on other pipegen jobs
		Since they are pipegen jobs, we know more information about their fully qualified names like:
		Presto -> must be hive_emr.pipegen.{table_name}, so we just use {table_name}
		Redshift -> must be pipegen.{table_name}, so we just use {table_name}
		"""
		if "." in self.table:
			raise Exception(f"{self.table} is a scheduling dependency and should not contain catalog/schema information")
		
		if self.source == "Presto":
			platform = "presto_hive"
			table_name = f"pipegen.{self.table}"

			return platform, table_name

		elif self.source == "Redshift":
			platform = "redshift"
			table_name = f"pipegen.{self.table}"

			return platform, table_name

		else:
			raise Exception(f"Unknown source: {self.source}")


@dataclass
class PipegenSpec:
	file_name: str
	name: str
	description: str 
	target_table_name: str
	data_dependencies:  typing.List[DataDependency]
	scheduling_dependencies: typing.List[SchedulingDependency]
	source: str
	enabled_for_scheduling: bool
	email: str

	def all_data_dependencies(self) -> typing.List[Dependency]:
		return set(self.data_dependencies).union(
			set(self.scheduling_dependencies)
		)


def file_to_pipegen_spec(file_path):
	file_name = os.path.basename(file_path)
	with open(file_path, "r") as f: 
		return file_contents_to_pipegen_spec(file_name, yaml.safe_load(f))

def file_contents_to_pipegen_spec(file_name, file_obj):
	data_dependencies = file_obj.get("DataDependencies", [])
	scheduling_dependencies = file_obj.get("SchedulingDependencies", [])

	mapped_data_dependencies = [ DataDependency(d["Source"], d["Name"]) for d in data_dependencies]
	mapped_scheduling_dependencies = [ SchedulingDependency(d["Source"], d["Name"]) for d in scheduling_dependencies]

	return PipegenSpec(
		file_name = file_name,
		name = file_obj["Name"],
		description = file_obj["Description"],
		target_table_name = file_obj["TargetTableName"],
		data_dependencies = mapped_data_dependencies,
		scheduling_dependencies = mapped_scheduling_dependencies,
		source = file_obj["Source"],
		enabled_for_scheduling = file_obj.get("EnabledForScheduling", True),
		email = file_obj["Email"]
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


def build_dataset_mce(pipegen_spec):
    """
    Creates MetadataChangeEvent for the dataset, creating upstream lineage links
    """
    actor, sys_time = "urn:li:corpuser:etl", int(time.time()) * 1000

    upstreams = [{
    	"auditStamp":{
    		"time": sys_time,
    		"actor": actor
    	},
    	"dataset": dep.construct_datalineage_urn(),
    	"type":"TRANSFORMED"
    } for dep in pipegen_spec.all_data_dependencies()]

    doc_elements = [{
    	"url":f"https://github.com/spothero/data-pipeline-definitions/blob/master/{pipegen_spec.file_name}",
    	"description":"Github pipegen definition",
    	"createStamp":{
    		"time": sys_time,
    		"actor": actor
    	}
    }]

    owners = [{
    	"owner": f"urn:li:corpuser:{pipegen_spec.email}",
    	"type": "DEVELOPER"
    }]

    return {
        "auditHeader": None,
        "proposedSnapshot":("com.linkedin.pegasus2avro.metadata.snapshot.DatasetSnapshot", {
            "urn": construct_data_urn(pipegen_spec),
            "aspects": [
            	("com.linkedin.pegasus2avro.dataset.UpstreamLineage", {"upstreams": upstreams}),
            	("com.linkedin.pegasus2avro.common.InstitutionalMemory", {"elements": doc_elements}),
            	("com.linkedin.pegasus2avro.common.Ownership", {
            		"owners": owners,
            		"lastModified":{
            			"time": sys_time,
            			"actor": actor
            		}
            	}),
            	("com.linkedin.pegasus2avro.dataset.DatasetProperties", {"description": pipegen_spec.description, "customProperties": {}})
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
	files = sorted(f for f in glob.glob(f"{PIPEGEN_DIRECTORY}/*.yaml"))
	for fn in files:
		print(f"Processing filename: {fn}")
		pipegen_spec = file_to_pipegen_spec(fn)
		mce = build_dataset_mce(pipegen_spec)

		print(pipegen_spec)
		print(mce)
		print("---")

		kafka_producer.produce(topic=KAFKA_TOPIC, key=mce['proposedSnapshot'][1]['urn'], value=mce)
		kafka_producer.flush()


if __name__ == "__main__":
	main()

