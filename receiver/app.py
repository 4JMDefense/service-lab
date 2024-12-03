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
from time import sleep

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

# Initialize Kafka client and producer with retry logic
def create_kafka_producer():
    retry_count = 5
    for attempt in range(retry_count):
        try:
            logger.info("Initializing Kafka client...")
            client = KafkaClient(hosts=f"{kafka_hostname}:{kafka_port}")
            topic = client.topics[str.encode(kafka_topic)]
            producer = topic.get_sync_producer()
            logger.info("Kafka client and producer initialized successfully.")
            return producer
        except Exception as e:
            logger.error(f"Attempt {attempt + 1} to initialize Kafka client failed: {str(e)}")
            if attempt < retry_count - 1:
                sleep(2)  # Wait before retrying
            else:
                logger.critical("Failed to initialize Kafka client after multiple attempts.")
                raise

# Create the producer at startup
producer = create_kafka_producer()

# API TASKS
def tasks():
    try:
        with open(TASK_FILE, 'r') as file:
            data = json.load(file)
    except FileNotFoundError:
        return jsonify([]), 200

    return jsonify(data), 200

def produce_event(event_type, body):
    trace_id = str(uuid.uuid4())
    body['trace_id'] = trace_id

    logger.info(f"Stored event '{event_type}' request with trace id {trace_id}")

    try:
        # Prepare Kafka message
        msg = {
            "type": event_type,
            "datetime": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "payload": body
        }
        msg_str = json.dumps(msg)

        # Produce message to Kafka
        producer.produce(msg_str.encode('utf-8'))
        logger.info(f"Produced event '{event_type}' with trace id {trace_id}")

    except Exception as e:
        logger.error(f"Failed to produce Kafka message for event '{event_type}': {str(e)}")
        return jsonify({"message": "Error producing Kafka message"}), 500

    return NoContent, 201

def create(body):
    return produce_event('create', body)

def complete(body):
    return produce_event('complete', body)

# Initialize Connexion app
app = connexion.FlaskApp(__name__, specification_dir='')
app.add_api("openapi.yaml", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

