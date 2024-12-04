"""
This module defines a SQLAlchemy ORM model for a 'completed_tasks' table.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, create_engine
from sqlalchemy.orm import sessionmaker
from base import Base

# Ensure that the DATABASE_URL is correct for your environment
DATABASE_URL = 'mysql+pymysql://suser:passpass@localhost:3306/events'  
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

class Complete(Base):
    """
    Represents a completed task in the database.
    """
    __tablename__ = 'completed_tasks'

    id = Column(Integer, primary_key=True, unique=True)
    task_name = Column(String(250), nullable=False)
    task_difficulty = Column(Integer, nullable=True)
    trace_id = Column(String(36), nullable=True)
    uuid = Column(String(36), unique=True)
    completed_at = Column(DateTime, default=datetime.now)
    completion_status = Column(Boolean, nullable=False, default=False)
    completed_by = Column(String(250), nullable=False)
    date_created = Column(DateTime, default=datetime.now)

    def __init__(self, task_name, uuid, completed_by, task_difficulty=None, trace_id=None):
        """
        Initializes a new Complete instance.
        """
        self.task_name = task_name
        self.uuid = uuid
        self.completed_by = completed_by
        self.completed_at = datetime.now()
        self.completion_status = True
        self.date_created = datetime.now()
        self.task_difficulty = task_difficulty
        self.trace_id = trace_id

    def to_dict(self):
        """
        Converts the Complete instance to a dictionary.
        """
        return {
            'id': self.id,
            'uuid': self.uuid,
            'task_name': self.task_name,
            'task_difficulty': self.task_difficulty,
            'completed_at': self.completed_at,
            'completed_by': self.completed_by,
            'completion_status': self.completion_status,
            'date_created': self.date_created,
            'trace_id': self.trace_id
        }

