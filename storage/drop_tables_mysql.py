import mysql.connector

db_conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Sandwich$2021",
    database="storage"
)

db_cursor = db_conn.cursor()

db_cursor.execute('''
    DROP TABLE IF EXISTS tasks, completed_tasks
''')

db_conn.commit()
db_conn.close()
