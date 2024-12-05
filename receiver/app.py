"""This module handles the main application logic for the receiver service."""

import json
from datetime import datetime
import logging
import logging.config
import uuid
from time import sleep
import yaml
import os
from flask import jsonify
from pykafka import KafkaClient
import connexion
from connexion import NoContent

# LOGGING CONFIGURATION
# Determine configuration file paths based on environment
if "TARGET_ENV" in os.environ and os.environ["TARGET_ENV"] == "test":
    print("In Test Environment")
    app_conf_file = "/config/app_conf.yml"
    log_conf_file = "/config/log_conf.yml"
else:
    print("In Dev Environment")
    app_conf_file = "app_conf.yml"
    log_conf_file = "log_conf.yml"

# Load YAML configuration from the specified paths
def load_yaml_config(file_path, encoding='utf-8'):
    """Load YAML configuration from a file."""
    try:
        with open(file_path, 'r', encoding=encoding) as file:
            return yaml.safe_load(file.read())
    except FileNotFoundError:
        logger.error("Configuration file '%s' not found.", file_path)
        raise
    except yaml.YAMLError as error:
        logger.error("Error parsing YAML file '%s': %s", file_path, error)
        raise

app_config = load_yaml_config(app_conf_file)
log_config = load_yaml_config(log_conf_file)

logging.config.dictConfig(log_config)
logger = logging.getLogger('basicLogger')
logger.info("App Conf File: %s" % app_conf_file)
logger.info("Log Conf File: %s" % log_conf_file)

# Constants
TASK_FILE = 'tasks.json'
EVENTS_FILE = 'events.json'
MAX_EVENTS = 5

# Kafka configuration
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
        except Exception as error:  # Catching all exceptions temporarily for robustness
            logger.error("Attempt %d to initialize Kafka client failed: %s", attempt + 1, error)
            if attempt < retry_count - 1:
                sleep(2)  # Wait before retrying
            else:
                logger.critical("Failed to initialize Kafka client after multiple attempts.")
                raise

producer = create_kafka_producer()

def tasks():
    """Retrieve and return all tasks from the TASK_FILE."""
    try:
        with open(TASK_FILE, 'r', encoding='utf-8') as file:
            data = json.load(file)
    except FileNotFoundError:
        logger.warning("Task file '%s' not found.", TASK_FILE)
        return jsonify([]), 200
    except json.JSONDecodeError as error:
        logger.error("Error parsing task file '%s': %s", TASK_FILE, error)
        return jsonify({"message": "Error reading task file"}), 500

    return jsonify(data), 200

def produce_event(event_type, body):
    """Produce an event message to Kafka."""
    trace_id = str(uuid.uuid4())
    body['trace_id'] = trace_id

    logger.info("Preparing event '%s' with trace id %s", event_type, trace_id)

    try:
        msg = {
            "type": event_type,
            "datetime": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "payload": body
        }
        producer.produce(json.dumps(msg).encode('utf-8'))
        logger.info("Produced event '%s' with trace id %s", event_type, trace_id)
    except Exception as error:
        logger.error("Failed to produce Kafka message for event '%s': %s", event_type, error)
        return jsonify({"message": "Error producing Kafka message"}), 500

    return NoContent, 201

def create(body):
    """Handle the 'create' event."""
    return produce_event('create', body)

def complete(body):
    """Handle the 'complete' event."""
    return produce_event('complete', body)

app = connexion.FlaskApp(__name__, specification_dir='')
#app.add_api("openapi.yaml", strict_validation=True, validate_responses=True)
app.add_api("openapi.yaml", base_path="/receiver", strict_validation=True, validate_responses=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

