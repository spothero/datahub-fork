#! /usr/bin/python
import time

from confluent_kafka import avro
from confluent_kafka.avro import AvroProducer
from dataclasses import dataclass
from sqlalchemy import create_engine
from sqlalchemy import types
from sqlalchemy.engine import reflection

@dataclass
class KafkaConfig:
    avsc_path = '../../metadata-events/mxe-schemas/src/renamed/avro/com/linkedin/mxe/MetadataChangeEvent.avsc'
    kafka_topic = 'MetadataChangeEvent_v4'
    bootstrap_server = 'localhost:9092'
    schema_registry = 'http://localhost:8081'


def get_column_type(column_type):
    """
    Maps SQLAlchemy types (https://docs.sqlalchemy.org/en/13/core/type_basics.html) to corresponding schema types
    """
    if isinstance(column_type, (types.Integer, types.Numeric)):
        return ("com.linkedin.pegasus2avro.schema.NumberType", {})

    if isinstance(column_type, (types.Boolean)):
        return ("com.linkedin.pegasus2avro.schema.BooleanType", {})

    if isinstance(column_type, (types.Enum)):
        return ("com.linkedin.pegasus2avro.schema.EnumType", {})

    if isinstance(column_type, (types._Binary, types.PickleType)):
        return ("com.linkedin.pegasus2avro.schema.BytesType", {})

    if isinstance(column_type, (types.ARRAY)):
        return ("com.linkedin.pegasus2avro.schema.ArrayType", {})

    if isinstance(column_type, (types.String)):
        return ("com.linkedin.pegasus2avro.schema.StringType", {})

    return ("com.linkedin.pegasus2avro.schema.NullType", {})


def build_dataset_mce(platform, dataset_name, columns):
    """
    Creates MetadataChangeEvent for the dataset.
    """
    actor, sys_time = "urn:li:corpuser:etl", int(time.time())

    fields = []
    for column in columns:
        fields.append({
            "fieldPath": column["name"],
            "nativeDataType": repr(column["type"]),
            "type": { "type":get_column_type(column["type"]) },
            "description": column.get("comment", None)
        })

    schema_metadata = {
        "schemaName": dataset_name,
        "platform": f"urn:li:dataPlatform:{platform}",
        "version": 0,
        "created": { "time": sys_time, "actor": actor },
        "lastModified": { "time":sys_time, "actor": actor },
        "hash": "",
        "platformSchema": { "tableSchema": "Table DDL goes here" },
        "fields": fields
    }

    return {
        "auditHeader": None,
        "proposedSnapshot":("com.linkedin.pegasus2avro.metadata.snapshot.DatasetSnapshot", {
            "urn": f"urn:li:dataset:(urn:li:dataPlatform:{platform},{dataset_name},PROD)",
            "aspects": [("com.linkedin.pegasus2avro.schema.SchemaMetadata", schema_metadata)]
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


def produce_dataset_mce(mce, kafka_config, producer):
    """
    Produces a MetadataChangeEvent to Kafka
    """
    producer.produce(topic=kafka_config.kafka_topic, key=mce['proposedSnapshot'][1]['urn'], value=mce)


def run(url, options, platform, schema_blacklist = None, kafka_config = KafkaConfig()):
    schema_blacklist = schema_blacklist or []

    engine = create_engine(url, **options)

    # avro producer
    conf = {'bootstrap.servers': kafka_config.bootstrap_server,
            'on_delivery': delivery_report,
            'schema.registry.url': kafka_config.schema_registry}
    key_schema = avro.loads('{"type": "string"}')
    record_schema = avro.load(kafka_config.avsc_path)
    producer = AvroProducer(conf, default_key_schema=key_schema, default_value_schema=record_schema)

    inspector = reflection.Inspector.from_engine(engine)
    for schema in inspector.get_schema_names():
        if schema in schema_blacklist:
            continue

        for table in inspector.get_table_names(schema):
            print(f"Producing data for table: {schema}.{table}")
            columns = inspector.get_columns(table, schema)
            mce = build_dataset_mce(platform, f'{schema}.{table}', columns)
            produce_dataset_mce(mce, kafka_config, producer)

        producer.flush()
