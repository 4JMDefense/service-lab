import json
import logging
import logging.config
import os
from datetime import datetime

import connexion
import pytz
import requests
import yaml
from apscheduler.schedulers.background import BackgroundScheduler
from flask import jsonify, request
from flask_cors import CORS
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Load logging configuration
with open('log_conf.yml', 'r') as f:
    log_config = yaml.safe_load(f.read())
    logging.config.dictConfig(log_config)

# Create a logger instance
logger = logging.getLogger('basicLogger')

# MySQL info
with open('app_conf.yml', 'r') as f:
    app_config = yaml.safe_load(f.read())

# Constants
TASK_FILE = 'tasks.json'
MAX_EVENTS = 5

db_config = app_config['datastore']
DATABASE_URL = (
    f"mysql+pymysql://{db_config['user']}:{db_config['password']}@{db_config['hostname']}:"
    f"{db_config['port']}/{db_config['db']}"
)
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

STATS_FILE = app_config['datastore']['filename']
PERIODIC_INTERVAL = app_config['scheduler']['period_sec']


def tasks():
    """Fetch and return tasks from an external service based on provided timestamps."""
    try:
        # Get timestamp parameters from the query string
        start_timestamp = request.args.get('start_timestamp')
        end_timestamp = request.args.get('end_timestamp')

        # Prepare the query parameters
        params = {}
        if start_timestamp:
            params['start_timestamp'] = start_timestamp
        if end_timestamp:
            params['end_timestamp'] = end_timestamp

        # Query the external service (Updated API URL)
        response = requests.get(
            "http://ec2-44-229-192-171.us-west-2.compute.amazonaws.com:8090/tasks",
            params=params,
        )

        if response.status_code == 200:
            tasks_data = response.json()
            logger.info("Tasks retrieved: %d tasks", len(tasks_data))
            return jsonify(tasks_data), 200
        else:
            logger.error("Error retrieving tasks: %s", response.text)
            return jsonify({"message": "Tasks not found"}), 400
    except Exception as e:
        logger.error("Exception in tasks: %s", str(e))
        return jsonify({"message": "Tasks not found"}), 400


def completed_tasks():
    """Fetch and return completed tasks from an external service based on provided timestamps."""
    try:
        # Get timestamp parameters from the query string
        start_timestamp = request.args.get('start_timestamp')
        end_timestamp = request.args.get('end_timestamp')

        # Prepare the query parameters
        params = {}
        if start_timestamp:
            params['start_timestamp'] = start_timestamp
        if end_timestamp:
            params['end_timestamp'] = end_timestamp

        # Query the external service (Updated API URL)
        response = requests.get(
            "http://ec2-44-229-192-171.us-west-2.compute.amazonaws.com:8090/completed_tasks",
            params=params,
        )

        if response.status_code == 200:
            completed_tasks_data = response.json()
            logger.info("Completed tasks retrieved: %d tasks", len(completed_tasks_data))
            return jsonify(completed_tasks_data), 200
        else:
            logger.error("Error retrieving completed tasks: %s", response.text)
            return jsonify({"message": "Completed tasks not found"}), 400
    except Exception as e:
        logger.error("Exception in completed_tasks: %s", str(e))
        return jsonify({"message": "Completed tasks not found"}), 400


def populate_stats():
    """Periodically update stats with incremental processing."""
    logger.info("Start Periodic Processing")

    # Set timezone to UTC
    utc_tz = pytz.utc

    # Initialize default stats structure
    stats = {
        "num_tasks": 0,
        "completed_tasks": 0,
        "max_task_difficulty": 0,
        "avg_task_difficulty": 0,
        "last_updated": datetime.now(utc_tz).strftime('%Y-%m-%dT%H:%M:%SZ')
    }

    # Load existing stats
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, 'r') as file:
            stats = json.load(file)

    # Update timestamps
    start_timestamp = stats["last_updated"]
    end_timestamp = datetime.now(utc_tz).strftime('%Y-%m-%dT%H:%M:%SZ')

    logger.debug("Fetching tasks from %s to %s", start_timestamp, end_timestamp)

    # Fetch new events data
    try:
        new_task_events = requests.get(
            f"http://ec2-44-229-192-171.us-west-2.compute.amazonaws.com:8090/tasks?start_timestamp={start_timestamp}&end_timestamp={end_timestamp}"
        )
        new_completed_events = requests.get(
            f"http://ec2-44-229-192-171.us-west-2.compute.amazonaws.com:8090/completed_tasks?start_timestamp={start_timestamp}&end_timestamp={end_timestamp}"
        )

        # Log response statuses
        logger.debug("Task Events Status: %d", new_task_events.status_code)
        logger.debug("Completed Events Status: %d", new_completed_events.status_code)

        # Check for successful responses
        if new_task_events.status_code == 200 and new_completed_events.status_code == 200:
            task_data = new_task_events.json()
            completed_data = new_completed_events.json()

            logger.debug("Task Data: %s", task_data)
            logger.debug("Completed Data: %s", completed_data)

            # Increment counts based on the fetched data
            stats["num_tasks"] += len(task_data)
            stats["completed_tasks"] += len(completed_data)

            if task_data:
                max_difficulty = max(task["task_difficulty"] for task in task_data)
                stats["max_task_difficulty"] = max(stats["max_task_difficulty"], max_difficulty)

                # Update average based on the new tasks
                total_difficulty = (
                    (stats["avg_task_difficulty"] * (stats["num_tasks"] - len(task_data)))
                    + sum(task["task_difficulty"] for task in task_data)
                )
                stats["avg_task_difficulty"] = total_difficulty / (stats["num_tasks"] or 1)  # Avoid division by zero

            # Update last_updated timestamp
            stats["last_updated"] = end_timestamp

            # Ensure the directory exists
            stats_dir = os.path.dirname(STATS_FILE)
            if not os.path.exists(stats_dir):
                os.makedirs(stats_dir)

            # Write updated stats to file
            with open(STATS_FILE, 'w') as file:
                json.dump(stats, file)
            logger.info("Statistics updated successfully")
            logger.debug("Updated statistics: %s", stats)
        else:
            logger.error("Failed to fetch data")
            if new_task_events.status_code != 200:
                logger.error("Task Events Error: %s", new_task_events.text)
            if new_completed_events.status_code != 200:
                logger.error("Completed Events Error: %s", new_completed_events.text)

    except Exception as e:
        logger.error("Exception occurred: %s", str(e))

    logger.info("End Periodic Processing")


def get_stats():
    """Retrieve statistics from the stats JSON file."""
    try:
        # Check if the stats file exists
        if not os.path.exists(STATS_FILE):
            logger.error("Stats file not found")
            return jsonify({"message": "Stats file not found"}), 404

        # Read the stats from the file
        with open(STATS_FILE, 'r') as file:
            stats = json.load(file)

        logger.info("Statistics retrieved successfully")
        return jsonify(stats), 200
    except Exception as e:
        logger.error("Exception in get_stats: %s", str(e))
        return jsonify({"message": "Failed to retrieve stats"}), 500


def init_scheduler():
    """Initialize and start the scheduler for periodic processing."""
    sched = BackgroundScheduler(daemon=True)
    sched.add_job(populate_stats, 'interval', seconds=PERIODIC_INTERVAL, timezone='UTC')
    sched.start()
    logger.info("Scheduler initialized and started")


# Initialize Connexion app
app = connexion.FlaskApp(__name__, specification_dir='')
app.add_api("openapi.yaml", strict_validation=True, validate_responses=True)
CORS(app.app)

if __name__ == "__main__":
    init_scheduler()
    app.run(host="0.0.0.0", port=8100)

