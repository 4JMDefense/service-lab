from sqlalchemy import Column, Integer, String, DateTime
from base import Base  # Import your declarative base

class Stats(Base):
    __tablename__ = 'stats'  # Table name in the MySQL database

    id = Column(Integer, primary_key=True)  # Assuming there's an 'id' column
    trace_id = Column(String(50))  # Adjust length as per your database schema
    task_name = Column(String(100))
    due_date = Column(DateTime)
    task_description = Column(String(255))
    task_difficulty = Column(String(50))
    uuid = Column(String(36))  # Adjust based on your UUID format
