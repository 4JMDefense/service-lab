import connexion
from connexion import NoContent
from flask import jsonify
import json
from datetime import datetime
import os
import requests
import yaml
import logging
import logging.config
import uuid


#LOGGING
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

    headers = {'Content-Type': 'application/json'}
    response = requests.post(eventstore1_url, json=body, headers=headers)

    
    logger.info(f"Returned event 'create' response (Id: {trace_id}) with status {response.status_code}")

    return NoContent, response.status_code


def complete(body):
   
    trace_id = str(uuid.uuid4())
    body['trace_id'] = trace_id

    
    logger.info(f"Stored event 'complete' request with trace id {trace_id}")

    headers = {'Content-Type': 'application/json'}
    response = requests.post(eventstore2_url, json=body, headers=headers)

     
    logger.info(f"Returned event 'complete' response (Id: {trace_id}) with status {response.status_code}")

    return NoContent, response.status_code


# Initialize Connexion app
app = connexion.FlaskApp(__name__, specification_dir='')
app.add_api("openapi.yaml", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    app.run(port=8080)


