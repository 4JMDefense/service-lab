import os
import json
import uuid
import yaml
import logging
import requests
import pytz
import logging.config
from datetime import datetime
from flask import jsonify, request
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from apscheduler.schedulers.background import BackgroundScheduler
from connexion import NoContent
from flask_cors import CORS
import connexion
from create import Create
from complete import Complete

# Load logging configuration
with open('log_conf.yml', 'r', encoding='utf-8') as f:
    log_config = yaml.safe_load(f)
    logging.config.dictConfig(log_config)

# Create a logger instance
logger = logging.getLogger('basicLogger')

# MySQL info
with open('app_conf.yml', 'r', encoding='utf-8') as f:
    app_config = yaml.safe_load(f)

# Constants
TASK_FILE = 'tasks.json'
MAX_EVENTS = 5

db_config = app_config['datastore']
DATABASE_URL = f"mysql+pymysql://{db_config['user']}:{db_config['password']}@{db_config['hostname']}:{db_config['port']}/{db_config['db']}"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

STATS_FILE = app_config['datastore']['filename']
PERIODIC_INTERVAL = app_config['scheduler']['period_sec']


def tasks():
    """Retrieve tasks from the external service based on optional timestamp filters."""
    try:
        start_timestamp = request.args.get('start_timestamp')
        end_timestamp = request.args.get('end_timestamp')

        params = {}
        if start_timestamp:
            params['start_timestamp'] = start_timestamp
        if end_timestamp:
            params['end_timestamp'] = end_timestamp

        response = requests.get("http://external_service_url/tasks", params=params)

        if response.status_code == 200:
            tasks_data = response.json()
            logger.info("Retrieved %d tasks", len(tasks_data))
            return jsonify(tasks_data), 200
        else:
            logger.error("Error retrieving tasks: %s", response.text)
            return jsonify({"message": "Tasks not found"}), 400
    except Exception as e:
        logger.error("Exception in tasks: %s", str(e))
        return jsonify({"message": "Tasks not found"}), 400


def populate_stats():
    """Periodically update stats with incremental processing."""
    logger.info("Start periodic processing")

    utc_tz = pytz.utc
    stats = {
        "num_tasks": 0,
        "completed_tasks": 0,
        "max_task_difficulty": 0,
        "avg_task_difficulty": 0,
        "last_updated": datetime.now(utc_tz).strftime('%Y-%m-%dT%H:%M:%SZ')
    }

    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, 'r', encoding='utf-8') as file:
            stats = json.load(file)

    start_timestamp = stats["last_updated"]
    end_timestamp = datetime.now(utc_tz).strftime('%Y-%m-%dT%H:%M:%SZ')

    try:
        task_events_resp = requests.get(f"http://external_service_url/tasks?start_timestamp={start_timestamp}&end_timestamp={end_timestamp}")
        completed_events_resp = requests.get(f"http://external_service_url/completed_tasks?start_timestamp={start_timestamp}&end_timestamp={end_timestamp}")

        if task_events_resp.status_code == 200 and completed_events_resp.status_code == 200:
            task_data = task_events_resp.json()
            completed_data = completed_events_resp.json()

            stats["num_tasks"] += len(task_data)
            stats["completed_tasks"] += len(completed_data)

            if task_data:
                max_difficulty = max(task["task_difficulty"] for task in task_data)
                stats["max_task_difficulty"] = max(stats["max_task_difficulty"], max_difficulty)

                total_difficulty = (stats["avg_task_difficulty"] * (stats["num_tasks"] - len(task_data))) + sum(task["task_difficulty"] for task in task_data)
                stats["avg_task_difficulty"] = total_difficulty / max(stats["num_tasks"], 1)

            stats["last_updated"] = end_timestamp

            with open(STATS_FILE, 'w', encoding='utf-8') as file:
                json.dump(stats, file)

            logger.info("Statistics updated successfully")
        else:
            logger.error("Failed to fetch data")
            if task_events_resp.status_code != 200:
                logger.error("Task events error: %s", task_events_resp.text)
            if completed_events_resp.status_code != 200:
                logger.error("Completed events error: %s", completed_events_resp.text)

    except Exception as e:
        logger.error("Exception occurred: %s", str(e))

    logger.info("End periodic processing")


def get_stats():
    """Retrieve statistics from the stats JSON file."""
    try:
        if not os.path.exists(STATS_FILE):
            logger.error("Stats file not found")
            return jsonify({"message": "Stats file not found"}), 404

        with open(STATS_FILE, 'r', encoding='utf-8') as file:
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

