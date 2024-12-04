"""
This script connects to a MySQL database to create a new user and grant privileges,
and then creates the 'tasks' and 'completed_tasks' tables if they do not already exist.
"""

import mysql.connector

# Connect as root to manage the database and users
try:
    db_conn = mysql.connector.connect(
        host="ec2-35-91-72-209.us-west-2.compute.amazonaws.com",
        user="root",
        password="passpass",
        database="storage"
    )

    db_cursor = db_conn.cursor()

    # Create the new user and grant privileges
    db_cursor.execute("CREATE USER IF NOT EXISTS 'suser'@'%' IDENTIFIED BY 'passpass';")
    db_cursor.execute("GRANT ALL PRIVILEGES ON storage.* TO 'suser'@'%';")
    db_cursor.execute("FLUSH PRIVILEGES;")  # Refresh privileges to ensure they take effect
    print("User 'suser' created with full privileges on 'storage' database.")

    # Commit changes
    db_conn.commit()

except mysql.connector.Error as err:
    print(f"Error creating user: {err}")
finally:
    if 'db_cursor' in locals():
        db_cursor.close()  # Close the cursor if it exists
    if 'db_conn' in locals() and db_conn.is_connected():
        db_conn.close()  # Close the connection if it exists

# Now connect as the new user to create tables
try:
    db_conn = mysql.connector.connect(
        host="ec2-35-91-72-209.us-west-2.compute.amazonaws.com",
        user="suser",
        password="passpass",
        database="storage",
        port=3306
    )

    db_cursor = db_conn.cursor()

    # Create the tasks table
    db_cursor.execute(''' 
        CREATE TABLE IF NOT EXISTS tasks (
            id INT NOT NULL AUTO_INCREMENT, 
            task_name VARCHAR(250) NOT NULL,
            due_date VARCHAR(250) NOT NULL,
            task_description VARCHAR(100) NOT NULL,
            trace_id VARCHAR(36),
            task_difficulty INT, 
            uuid VARCHAR(36), 
            date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id)
        )
    ''')

    # Create the completed_tasks table
    db_cursor.execute(''' 
        CREATE TABLE IF NOT EXISTS completed_tasks (
            id INT NOT NULL AUTO_INCREMENT, 
            task_name VARCHAR(250) NOT NULL,
            task_difficulty INT,
            trace_id VARCHAR(36),
            uuid VARCHAR(36) NOT NULL, 
            completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completion_status BOOLEAN NOT NULL DEFAULT 0, 
            completed_by VARCHAR(250) NOT NULL, 
            date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id)
        )
    ''')

    # Commit changes and close connection
    db_conn.commit()
    print("Tables created successfully.")

except mysql.connector.Error as err:
    print(f"Error creating tables: {err}")
finally:
    if 'db_cursor' in locals():
        db_cursor.close()  # Close the cursor if it exists
    if 'db_conn' in locals() and db_conn.is_connected():
        db_conn.close()  # Close the connection if it exists

