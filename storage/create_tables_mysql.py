import mysql.connector


db_conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Sandwich$2021",  
    database="storage"           
)

db_cursor = db_conn.cursor()


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
