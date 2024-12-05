import connexion
from connexion import NoContent
from flask import jsonify, request
import json
from datetime import datetime
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from create import Create
from complete import Complete
import uuid
import yaml
import logging
import logging.config
import threading
from pykafka import KafkaClient
from pykafka.common import OffsetType

# Determine configuration file paths based on environment
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

# Constants
TASK_FILE = 'tasks.json'
MAX_EVENTS = 5

# Database configuration
db_config = app_config['datastore']
logger.info(f"Connecting to MySQL database on host '{db_config['hostname']}' and port '{db_config['port']}'.")
DATABASE_URL = f"mysql+pymysql://{db_config['user']}:{db_config['password']}@{db_config['hostname']}:{db_config['port']}/{db_config['db']}"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

# Kafka configuration
KAFKA_HOST = f"{app_config['events']['hostname']}:{app_config['events']['port']}"
KAFKA_TOPIC = app_config['events']['topic']

# API tasks
def tasks():
    """
    Retrieve tasks from the database with optional timestamp filtering.
    """
    logger.info("assignment 3.")
    session = Session()
    try:
        start_timestamp = request.args.get('start_timestamp')
        end_timestamp = request.args.get('end_timestamp')

        query = session.query(Create)

        # Handle timestamp filtering with 'Z' handling
        if start_timestamp:
            if 'Z' in start_timestamp:
                start_timestamp = start_timestamp.replace('Z', '+00:00')
            start_dt = datetime.strptime(start_timestamp, "%Y-%m-%dT%H:%M:%S%z")
            query = query.filter(Create.date_created >= start_dt)

        if end_timestamp:
            if 'Z' in end_timestamp:
                end_timestamp = end_timestamp.replace('Z', '+00:00')
            end_dt = datetime.strptime(end_timestamp, "%Y-%m-%dT%H:%M:%S%z")
            query = query.filter(Create.date_created < end_dt)

        tasks_list = query.all()
        tasks_data = [
            {
                'trace_id': task.trace_id,
                'task_name': task.task_name,
                'due_date': task.due_date,
                'task_description': task.task_description,
                'task_difficulty': task.task_difficulty,
                'uuid': task.uuid,
                'date_created': task.date_created.isoformat()
            }
            for task in tasks_list
        ]

        logger.info("Tasks retrieved: %d tasks", len(tasks_data))
        return jsonify(tasks_data), 200
    except Exception as e:
        logger.error(f"Error retrieving tasks: {str(e)}")
        return "Error retrieving tasks", 500
    finally:
        session.close()

def create(body):
    """
    Create a new task in the database.
    """
    trace_id = body.get('trace_id')
    session = Session()

    task_name = body.get('task_name')
    due_date = body.get('due_date')
    task_description = body.get('task_description')
    task_difficulty = body.get('task_difficulty')
    provided_uuid = body.get('uuid')

    # Check if we have the required values
    if not task_name or not due_date or not task_description:
        return "Error: 'task_name', 'due_date', and 'task_description' are required.", 400

    if not provided_uuid:
        return "Error: 'uuid' is required in the body.", 400

    new_task = Create(
        trace_id=trace_id,
        task_name=task_name,
        due_date=due_date,
        task_description=task_description,
        task_difficulty=task_difficulty,
        uuid=provided_uuid
    )

    session.add(new_task)
    session.commit()

    # Log the trace ID
    logger.info(f"Task created with trace ID: {trace_id}")

    session.close()
    return "Task created", 201

def complete(body):
    """
    Complete a task and move it to the completed tasks table.
    """
    trace_id = body.get('trace_id')
    task_name_to_complete = body.get('task_name')

    if not task_name_to_complete:
        return "Error: 'task_name' is required in the body.", 400

    provided_uuid = body.get('uuid')
    if not provided_uuid:
        return "Error: 'uuid' is required in the body.", 400

    # Get the name of the user completing the task
    completed_by = body.get('completed_by', "Unknown")

    session = Session()
    # Find the task name in the task table
    task_found = session.query(Create).filter(Create.task_name == task_name_to_complete).first()

    if task_found:
        completed_task = Complete(
            trace_id=trace_id,
            task_name=task_name_to_complete,
            task_difficulty=task_found.task_difficulty,
            uuid=provided_uuid,
            completed_by=completed_by
        )

        session.add(completed_task)
        session.delete(task_found)
        response_message = f"Task '{task_name_to_complete}' updated and completed"
    else:
        # If it doesn't find an existing task name, create a new task in the completed table
        completed_task = Complete(
            trace_id=trace_id,
            task_name=task_name_to_complete,
            uuid=provided_uuid,
            task_difficulty=None,
            completed_by=completed_by
        )
        session.add(completed_task)
        response_message = f"Task '{task_name_to_complete}' created and completed"

    session.commit()

    # Log the trace ID
    logger.info(f"Task completed with trace ID: {trace_id}")

    session.close()

    return response_message, 200 if task_found else 201

def completed_tasks():
    """
    Retrieve completed tasks from the database with optional timestamp filtering.
    """
    session = Session()
    try:
        start_timestamp = request.args.get('start_timestamp')
        end_timestamp = request.args.get('end_timestamp')

        query = session.query(Complete)

        # Handle timestamp filtering with 'Z' handling
        if start_timestamp:
            if 'Z' in start_timestamp:
                start_timestamp = start_timestamp.replace('Z', '+00:00')
            start_dt = datetime.strptime(start_timestamp, "%Y-%m-%dT%H:%M:%S%z")
            query = query.filter(Complete.date_created >= start_dt)

        if end_timestamp:
            if 'Z' in end_timestamp:
                end_timestamp = end_timestamp.replace('Z', '+00:00')
            end_dt = datetime.strptime(end_timestamp, "%Y-%m-%dT%H:%M:%S%z")
            query = query.filter(Complete.date_created < end_dt)

        completed_tasks_list = query.all()
        completed_tasks_data = [
            {
                'trace_id': task.trace_id,
                'task_name': task.task_name,
                'task_difficulty': task.task_difficulty,
                'uuid': task.uuid,
                'completed_by': task.completed_by,
                'date_created': task.date_created.strftime("%Y-%m-%d %H:%M:%S")
            }
            for task in completed_tasks_list
        ]

        logger.info("Completed tasks retrieved: %d tasks", len(completed_tasks_data))
        return jsonify(completed_tasks_data), 200
    except Exception as e:
        logger.error(f"Error retrieving completed tasks: {str(e)}")
        return "Error retrieving completed tasks", 500
    finally:
        session.close()

def process_messages():
    """
    Process incoming messages from Kafka and store them in the database.
    """
    logger.info("Initializing Kafka consumer...")
    try:
        client = KafkaClient(hosts=KAFKA_HOST)
        topic = client.topics[KAFKA_TOPIC.encode('utf-8')]
        consumer = topic.get_simple_consumer(
            consumer_group=b'event_group',
            reset_offset_on_start=False,
            auto_offset_reset=OffsetType.LATEST
        )

        logger.info("Starting Kafka consumer...")
        for msg in consumer:
            if msg is not None:
                msg_str = msg.value.decode('utf-8')
                event_msg = json.loads(msg_str)
                logger.info(f"Message received: {event_msg}")

                # Process events based on their type
                if event_msg["type"] == "create":
                    store_event1(event_msg["payload"])
                elif event_msg["type"] == "complete":
                    store_event2(event_msg["payload"])

                # Commit message offsets
                consumer.commit_offsets()
    except Exception as e:
        logger.error(f"Error in Kafka consumer: {str(e)}")

def store_event1(payload):
    """
    Store an event of type 'create' in the database.
    """
    session = Session()
    try:
        new_event = Create(
            trace_id=payload['trace_id'],
            task_name=payload['task_name'],
            due_date=payload['due_date'],
            task_description=payload['task_description'],
            task_difficulty=payload['task_difficulty'],
            uuid=payload['uuid']
        )
        session.add(new_event)
        session.commit()
        logger.info(f"Stored event1 with trace ID: {payload['trace_id']}")
    except Exception as e:
        logger.error(f"Error storing event1: {str(e)}")
        session.rollback()
    finally:
        session.close()

def store_event2(payload):
    """
    Store an event of type 'complete' in the database.
    """
    session = Session()
    try:
        new_event = Complete(
            trace_id=payload['trace_id'],
            task_name=payload['task_name'],
            task_difficulty=payload.get('task_difficulty'),
            uuid=payload['uuid'],
            completed_by=payload.get('completed_by')
        )
        session.add(new_event)
        session.commit()
        logger.info(f"Stored event2 with trace ID: {payload['trace_id']}")
    except Exception as e:
        logger.error(f"Error storing event2: {str(e)}")
        session.rollback()
    finally:
        session.close()

# Initialize Connexion app
app = connexion.FlaskApp(__name__, specification_dir='')
#app.add_api("openapi.yaml", strict_validation=True, validate_responses=True)
app.add_api("openapi.yaml", base_path="/storage", strict_validation=True, validate_responses=True)


if __name__ == "__main__":
    # Start the Kafka consumer in a separate thread
    t1 = threading.Thread(target=process_messages)
    t1.setDaemon(True)
    t1.start()

    # Start the Flask application
    app.run(host="0.0.0.0", port=8090)

