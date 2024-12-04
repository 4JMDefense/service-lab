"""
This script connects to an SQLite database and creates two tables: 'tasks' and 'completed_tasks'.
The tables include columns for task details and timestamps.
"""

import sqlite3

conn = sqlite3.connect('storage.db')  
c = conn.cursor()

# Create new tasks table with uuid
c.execute(''' 
          CREATE TABLE IF NOT EXISTS tasks (
           id INTEGER PRIMARY KEY, 
           task_name VARCHAR(250) NOT NULL,
           due_date VARCHAR(250) NOT NULL,
           task_description VARCHAR(100) NOT NULL,
           uuid VARCHAR(36), 
           date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
          ''')

# Create new completed_tasks table with uuid
c.execute(''' 
          CREATE TABLE IF NOT EXISTS completed_tasks (
           id INTEGER PRIMARY KEY, 
           task_name VARCHAR(250) NOT NULL,
           uuid VARCHAR(36) NOT NULL, 
           completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
           completion_status BOOLEAN NOT NULL DEFAULT 0, 
           completed_by VARCHAR(250) NOT NULL, 
           date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
          ''')

