import mysql.connector

# Connect as root to manage the database and users
db_conn = mysql.connector.connect(
    host="ec2-54-71-130-207.us-west-2.compute.amazonaws.com",
    user="root",
    password="Sandwich$2021",  
    database="storage"           
)

db_cursor = db_conn.cursor()

# Create the new user and grant privileges
try:
    db_cursor.execute("CREATE USER IF NOT EXISTS 'suser'@'%' IDENTIFIED BY 'passpass';")
    db_cursor.execute("GRANT ALL PRIVILEGES ON storage.* TO 'suser'@'%';")
    db_cursor.execute("FLUSH PRIVILEGES;")  # Refresh privileges to ensure they take effect
    print("User 'suser' created with full privileges on 'storage' database.")
except mysql.connector.Error as err:
    print(f"Error creating user: {err}")


db_conn = mysql.connector.connect(
    host="localhost",
    user="suser",
    password="passpass",  
    database="storage",           
    port=3306
)

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
db_conn.close()
