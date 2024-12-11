import os
import json
import logging
import logging.config
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

# Check for the environment and set config file paths accordingly
if "TARGET_ENV" in os.environ and os.environ["TARGET_ENV"] == "test":
    print("In Test Environment")
    app_conf_file = "/config/app_conf.yml"
    log_conf_file = "/config/log_conf.yml"
else:
    print("In Dev Environment")
    app_conf_file = "app_conf.yml"
    log_conf_file = "log_conf.yml"

# Load application and logging configurations
with open(app_conf_file, 'r') as f:
    app_config = yaml.safe_load(f.read())

with open(log_conf_file, 'r') as f:
    log_config = yaml.safe_load(f.read())
    logging.config.dictConfig(log_config)


# Create a logger instance
logger = logging.getLogger('basicLogger')
logger.info("App Conf File: %s", app_conf_file)
logger.info("Log Conf File: %s", log_conf_file)

# Constants
TASK_FILE = 'tasks.json'
MAX_EVENTS = 5

# Database configuration
db_config = app_config['datastore']
DATABASE_URL = (
    f"mysql+pymysql://{db_config['user']}:{db_config['password']}@"
    f"{db_config['hostname']}:{db_config['port']}/{db_config['db']}"
)
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

# Stats file and scheduler interval
STATS_FILE = app_config['datastore']['filename']
PERIODIC_INTERVAL = app_config['scheduler']['period_sec']

def tasks():
    """Fetch and return tasks from an external service based on provided timestamps."""
    try:
        start_timestamp = request.args.get('start_timestamp')
        end_timestamp = request.args.get('end_timestamp')

        params = {}
        if start_timestamp:
            params['start_timestamp'] = start_timestamp
        if end_timestamp:
            params['end_timestamp'] = end_timestamp

        response = requests.get(
            "http://ec2-44-229-192-171.us-west-2.compute.amazonaws.com/storage/tasks",
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
        start_timestamp = request.args.get('start_timestamp')
        end_timestamp = request.args.get('end_timestamp')

        params = {}
        if start_timestamp:
            params['start_timestamp'] = start_timestamp
        if end_timestamp:
            params['end_timestamp'] = end_timestamp

        response = requests.get(
            "http://ec2-44-229-192-171.us-west-2.compute.amazonaws.com/storage/completed_tasks",
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
    logger.info("ASSIGNMENT 3!")

    utc_tz = pytz.utc
    stats = {
        "num_tasks": 0,
        "completed_tasks": 0,
        "max_task_difficulty": 0,
        "avg_task_difficulty": 0,
        "last_updated": datetime.now(utc_tz).strftime('%Y-%m-%dT%H:%M:%SZ')
    }

    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, 'r') as file:
            stats = json.load(file)

    start_timestamp = stats["last_updated"]
    end_timestamp = datetime.now(utc_tz).strftime('%Y-%m-%dT%H:%M:%SZ')

    logger.debug("Fetching tasks from %s to %s", start_timestamp, end_timestamp)

    try:
        new_task_events = requests.get(
            f"http://ec2-44-229-192-171.us-west-2.compute.amazonaws.com/storage/tasks"
            f"?start_timestamp={start_timestamp}&end_timestamp={end_timestamp}"
        )
        new_completed_events = requests.get(
            f"http://ec2-44-229-192-171.us-west-2.compute.amazonaws.com/storage/completed_tasks"
            f"?start_timestamp={start_timestamp}&end_timestamp={end_timestamp}"
        )

        logger.debug("Task Events Status: %d", new_task_events.status_code)
        logger.debug("Completed Events Status: %d", new_completed_events.status_code)

        if new_task_events.status_code == 200 and new_completed_events.status_code == 200:
            task_data = new_task_events.json()
            completed_data = new_completed_events.json()

            logger.debug("Task Data: %s", task_data)
            logger.debug("Completed Data: %s", completed_data)

            stats["num_tasks"] += len(task_data)
            stats["completed_tasks"] += len(completed_data)

            if task_data:
                max_difficulty = max(task["task_difficulty"] for task in task_data)
                stats["max_task_difficulty"] = max(stats["max_task_difficulty"], max_difficulty)

                total_difficulty = (
                    (stats["avg_task_difficulty"] * (stats["num_tasks"] - len(task_data)))
                    + sum(task["task_difficulty"] for task in task_data)
                )
                stats["avg_task_difficulty"] = total_difficulty / (stats["num_tasks"] or 1)

            stats["last_updated"] = end_timestamp

            stats_dir = os.path.dirname(STATS_FILE)
            if not os.path.exists(stats_dir):
                os.makedirs(stats_dir)

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
        if not os.path.exists(STATS_FILE):
            logger.error("Stats file not found")
            return jsonify({"message": "Stats file not found"}), 404

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
#app.add_api("openapi.yaml", strict_validation=True, validate_responses=True)
app.add_api("openapi.yaml", base_path="/processing", strict_validation=True, validate_responses=True)
CORS(app.app)

if "TARGET_ENV" not in os.environ or os.environ["TARGET_ENV"] != "test":
    CORS(app.app)
app.app.config['CORS_HEADERS'] = 'Content-Type'


if __name__ == "__main__":
    init_scheduler()
    app.run(host="0.0.0.0", port=8100)

