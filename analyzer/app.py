import threading
import connexion
import json
import yaml
import logging.config
from flask import jsonify, request
from pykafka import KafkaClient
from pykafka.common import OffsetType
import time
import atexit

# Load configurations
with open('app_conf.yml', 'r') as f:
    app_config = yaml.safe_load(f.read())

with open('log_conf.yml', 'r') as f:
    log_config = yaml.safe_load(f.read())
    logging.config.dictConfig(log_config)

logger = logging.getLogger('basicLogger')

# Kafka settings
KAFKA_HOST = f"{app_config['events']['hostname']}:{app_config['events']['port']}"
KAFKA_TOPIC = app_config['events']['topic']

# Initialize Kafka client and topic
client = KafkaClient(hosts=KAFKA_HOST)
topic = client.topics[KAFKA_TOPIC.encode('utf-8')]

# Shared event counts and event storage
event_counts = {
    "create_count": 0,
    "complete_count": 0
}

# Store events by type
event_store = {
    "create": [],
    "complete": []
}

# Kafka consumer function
def consume_messages():
    global event_counts, event_store

    consumer = topic.get_simple_consumer(
        consumer_group=b'analyzer_group',
        reset_offset_on_start=True,
        auto_offset_reset=OffsetType.EARLIEST
    )

    logger.info("Starting Kafka consumer...")

    for msg in consumer:
        if msg is not None:
            msg_str = msg.value.decode('utf-8')
            event = json.loads(msg_str)
            logger.info(f"Consumed message: {event}")

            # Store event data by type and increment counts
            if event['type'] == 'create':
                event_store["create"].append(event)
                event_counts["create_count"] += 1
            elif event['type'] == 'complete':
                event_store["complete"].append(event)
                event_counts["complete_count"] += 1

            consumer.commit_offsets()


def start_kafka_consumer():
    kafka_thread = threading.Thread(target=consume_messages, daemon=True)
    kafka_thread.start()


def get_stats():
    """ Return the current event counts as JSON """
    return jsonify(event_counts), 200


def get_event1():
    try:
        index = int(request.args.get('index'))
        logger.info(f"Fetching 'create' event at index {index}")  # Log the fetching process
        if index < 0 or index >= len(event_store["create"]):
            logger.error(f"Could not find 'create' event at index {index}")
            return jsonify({"message": "Not Found"}), 404
        
        return jsonify(event_store["create"][index]), 200
    except (ValueError, TypeError):
        logger.error("Invalid index provided for 'create' event")
        return jsonify({"message": "Invalid index"}), 400


def get_event2():
    try:
        index = int(request.args.get('index'))
        logger.info(f"Fetching 'complete' event at index {index}")  # Log the fetching process
        if index < 0 or index >= len(event_store["complete"]):
            logger.error(f"Could not find 'complete' event at index {index}")
            return jsonify({"message": "Not Found"}), 404
        
        return jsonify(event_store["complete"][index]), 200
    except (ValueError, TypeError):
        logger.error("Invalid index provided for 'complete' event")
        return jsonify({"message": "Invalid index"}), 400

# Initialize the Connexion app
app = connexion.FlaskApp(__name__, specification_dir='')


app.add_api("openapi.yaml", strict_validation=True, validate_responses=True)


start_kafka_consumer()

# Start the Flask app
if __name__ == "__main__":
    app.run(port=8110)  # Disable reloader to prevent restarts
