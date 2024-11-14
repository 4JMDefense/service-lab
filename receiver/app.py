import connexion
from connexion import NoContent
from flask import jsonify
import json
from datetime import datetime
import os
import yaml
import logging
import logging.config
import uuid
from pykafka import KafkaClient


# LOGGING
with open('app_conf.yml', 'r') as f:
    app_config = yaml.safe_load(f.read())

eventstore1_url = app_config['eventstore1']['url']
eventstore2_url = app_config['eventstore2']['url']

with open('log_conf.yml', 'r') as f:
    log_config = yaml.safe_load(f.read())
    logging.config.dictConfig(log_config)

logger = logging.getLogger('basicLogger')

# Constants
TASK_FILE = 'tasks.json'
EVENTS_FILE = 'events.json'
MAX_EVENTS = 5

# Kafka configuration from app_conf.yml
kafka_config = app_config['events']
kafka_hostname = kafka_config['hostname']
kafka_port = kafka_config['port']
kafka_topic = kafka_config['topic']


# Initialize Kafka client
client = KafkaClient(hosts=f"{kafka_hostname}:{kafka_port}")
topic = client.topics[str.encode(kafka_topic)]
producer = topic.get_sync_producer()

## API TASKS
def tasks():
    try:
        with open(TASK_FILE, 'r') as file:
            data = json.load(file)
    except FileNotFoundError:
        return jsonify([]), 200

    return jsonify(data), 200


def create(body):
    trace_id = str(uuid.uuid4())
    body['trace_id'] = trace_id

    logger.info(f"Stored event 'create' request with trace id {trace_id}")

    # Prepare Kafka message
    msg = {
        "type": "create",
        "datetime": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "payload": body
    }
    msg_str = json.dumps(msg)

    # Produce message to Kafka
    producer.produce(msg_str.encode('utf-8'))

    logger.info(f"Produced event 'create' with trace id {trace_id}")

    return NoContent, 201


def complete(body):
    trace_id = str(uuid.uuid4())
    body['trace_id'] = trace_id

    logger.info(f"Stored event 'complete' request with trace id {trace_id}")

    # Prepare Kafka message
    msg = {
        "type": "complete",
        "datetime": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "payload": body
    }
    msg_str = json.dumps(msg)

    # Produce message to Kafka
    producer.produce(msg_str.encode('utf-8'))

    logger.info(f"Produced event 'complete' with trace id {trace_id}")

    return NoContent, 201


# Initialize Connexion app
app = connexion.FlaskApp(__name__, specification_dir='')
app.add_api("openapi.yaml", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    app.run(port=8080)
