import os

# Specify the path to the database file
db_file = 'storage.db'

# Check if the file exists and delete it
if os.path.exists(db_file):
    try:
        os.remove(db_file)
        print(f"{db_file} has been deleted.")
    except PermissionError as e:
        print(f"Permission error: {e}")
else:
    print(f"{db_file} does not exist.")
