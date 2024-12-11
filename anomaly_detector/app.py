import json
import logging
import logging.config
import os
import yaml
from datetime import datetime
from pykafka import KafkaClient
from threading import Thread
from time import sleep
from connexion import FlaskApp

# Environment-based configuration
if "TARGET_ENV" in os.environ and os.environ["TARGET_ENV"] == "test":
    print("In Test Environment")
    app_conf_file = "/config/app_conf.yml"
    log_conf_file = "/config/log_conf.yml"
else:
    print("In Dev Environment")
    app_conf_file = "app_conf.yml"
    log_conf_file = "log_conf.yml"

# Configure logging
with open(log_conf_file, 'r') as f:
    log_config = yaml.safe_load(f.read())
    logging.config.dictConfig(log_config)

logger = logging.getLogger('basicLogger')
logger.info("Log Conf File: %s" % log_conf_file)

# Load application configuration
with open(app_conf_file, 'r') as f:
    app_config = yaml.safe_load(f.read())

logger.info("App Conf File: %s" % app_conf_file)

# Kafka Configuration
kafka_config = app_config['events']
kafka_hostname = kafka_config['hostname']
kafka_port = kafka_config['port']
kafka_topic = kafka_config['topic']

JSON_FILE_PATH = app_config['data_store']['filepath']
THRESHOLDS = app_config['thresholds']

# Create Flask app
app = FlaskApp(__name__, specification_dir='')
app.add_api("openapi.yml", strict_validation=True, validate_responses=True)

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

# Kafka producer instance
producer = create_kafka_producer()

# Load existing anomalies from JSON store
def load_anomalies():
    if os.path.exists(JSON_FILE_PATH):
        with open(JSON_FILE_PATH, 'r') as file:
            return json.load(file)
    return []

# Save anomalies to JSON store
def save_anomalies(anomalies):
    with open(JSON_FILE_PATH, 'w') as file:
        json.dump(anomalies, file, indent=4)

# Function to detect anomalies
def detect_anomaly(event):
    event_id = event.get('event_id')
    trace_id = event.get('trace_id')
    event_type = event.get('event_type')
    value = event.get('value')

    if event_type in THRESHOLDS:
        threshold = THRESHOLDS[event_type]
        anomaly_type = None
        description = ""

        if value > threshold:
            anomaly_type = "Too High"
            description = f"The value is too high ({event_type} of {value} is greater than threshold of {threshold})"
        elif value < threshold:
            anomaly_type = "Too Low"
            description = f"The value is too low ({event_type} of {value} is less than the threshold of {threshold})"

        if anomaly_type:
            anomaly = {
                "event_id": event_id,
                "trace_id": trace_id,
                "event_type": event_type,
                "anomaly_type": anomaly_type,
                "description": description,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            logger.info(f"Anomaly detected: {anomaly}")
            anomalies = load_anomalies()
            anomalies.append(anomaly)
            save_anomalies(anomalies)

# Start processing events
def process_kafka_events():
    client = KafkaClient(hosts=f"{kafka_hostname}:{kafka_port}")
    topic = client.topics[str.encode(kafka_topic)]
    consumer = topic.get_simple_consumer()
    for message in consumer:
        if message is not None:
            event = json.loads(message.value.decode('utf-8'))
            logger.info(f"Event consumed: {event}")
            detect_anomaly(event)

# Start the Kafka consumer in a separate thread
Thread(target=process_kafka_events, daemon=True).start()

# New function to get anomalies
def get_anomalies(anomaly_type=None):
    anomalies = load_anomalies()
    if not anomalies:
        logger.info("No anomalies found.")
        return []

    if anomaly_type:
        filtered_anomalies = [a for a in anomalies if a['anomaly_type'].lower() == anomaly_type.lower()]
        if not filtered_anomalies:
            logger.info(f"No anomalies found for type: {anomaly_type}")
            return []
        return filtered_anomalies
    
    return anomalies

# Register the function with Connexion
app.add_url_rule('/anomalies', 'get_anomalies', get_anomalies, methods=['GET'])

# Run the Connexion app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8120)

