"""
This script connects to a MySQL database and drops the 'tasks' and 'completed_tasks' tables if they exist.
"""

import mysql.connector

# Establish connection to the MySQL database
db_conn = mysql.connector.connect(
    host="localhost",
    user="suser",
    password="passpass",
    database="storage"
)

# Create a cursor object to execute SQL queries
db_cursor = db_conn.cursor()

# Execute SQL command to drop the tables if they exist
db_cursor.execute('''DROP TABLE IF EXISTS tasks, completed_tasks''')

# Commit the changes to the database
db_conn.commit()

# Close the database connection
db_conn.close()

