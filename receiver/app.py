"""This module handles the main application logic for the receiver service."""

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

# LOGGING CONFIGURATION
def load_yaml_config(file_path, encoding='utf-8'):
    """Load YAML configuration from a file with the specified encoding."""
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            return yaml.safe_load(f.read())
    except FileNotFoundError:
        logger.error(f"Configuration file '{file_path}' not found.")
        raise
    except yaml.YAMLError as e:
        logger.error(f"Error parsing configuration file '{file_path}': {e}")
        raise

app_config = load_yaml_config('app_conf.yml')
log_config = load_yaml_config('log_conf.yml')

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

def create_kafka_producer():
    """Initialize and return a Kafka producer with retry logic."""
    retry_count = 5
    for attempt in range(retry_count):
        try:
            logger.info("Initializing Kafka client...")
            client = KafkaClient(hosts=f"{kafka_hostname}:{kafka_port}")
            topic = client.topics[str.encode(kafka_topic)]
            producer = topic.get_sync_producer()
            logger.info("Kafka client and producer initialized successfully.")
            return producer
        except (ConnectionError, Exception) as e:
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
    """Retrieve and return all tasks from the TASK_FILE."""
    try:
        with open(TASK_FILE, 'r', encoding='utf-8') as file:
            data = json.load(file)
    except FileNotFoundError:
        logger.warning(f"Task file '{TASK_FILE}' not found.")
        return jsonify([]), 200
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing task file '{TASK_FILE}': {e}")
        return jsonify({"message": "Error reading task file"}), 500

    return jsonify(data), 200

def produce_event(event_type, body):
    """Produce an event message to Kafka."""
    trace_id = str(uuid.uuid4())
    body['trace_id'] = trace_id

    logger.info(f"Preparing event '{event_type}' with trace id {trace_id}")

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
    """Handle the 'create' event."""
    return produce_event('create', body)

def complete(body):
    """Handle the 'complete' event."""
    return produce_event('complete', body)

# Initialize Connexion app
app = connexion.FlaskApp(__name__, specification_dir='')
app.add_api("openapi.yaml", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

