from sqlalchemy import Column, Integer, String, DateTime
from base import Base
from datetime import datetime
import uuid

class Create(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, unique=True)
    task_name = Column(String(250), nullable=False)
    due_date = Column(String(250), nullable=False)
    task_description = Column(String(100), nullable=False)
    task_difficulty = Column(Integer, nullable=True)
    trace_id = Column(String(36), nullable=True)
    date_created = Column(DateTime, default=datetime.now)  
    uuid = Column(String(36), unique=False, nullable=False)

    def __init__(self, task_name, due_date, task_description, uuid, task_difficulty=None, trace_id=None):
        self.task_name = task_name
        self.due_date = due_date
        self.task_description = task_description
        self.task_difficulty = task_difficulty  
        self.date_created = datetime.now()  
        self.uuid = uuid
        self.trace_id = trace_id


    def to_dict(self):
        dict = {}
        dict['id'] = self.id
        dict['uuid'] = self.uuid
        dict['task_name'] = self.task_name
        dict['due_date'] = self.due_date
        dict['task_description'] = self.task_description
        dict['task_difficulty'] = self.task_difficulty  
        dict['date_created'] = self.date_created
        dict['trace_id'] = self.trace_id

        return dict
