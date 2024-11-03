from sqlalchemy import Column, Integer, String, DateTime, Boolean  
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from base import Base
from create import Create  
from datetime import datetime 
import uuid 

DATABASE_URL = 'mysql+pymysql://root:Sandwich$2021@localhost:3306/events'  
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

class Complete(Base):
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
        self.task_name = task_name
        self.uuid = uuid
        self.completed_by = completed_by
        self.completed_at = datetime.now() 
        self.completion_status = True  
        self.date_created = datetime.now()  
        self.task_difficulty = task_difficulty 
        self.trace_id = trace_id

    def to_dict(self):
        dict = {}
        dict['id'] = self.id
        dict['uuid'] = self.uuid
        dict['task_name'] = self.task_name
        dict['task_difficulty'] = self.task_difficulty  
        dict['completed_at'] = self.completed_at
        dict['completed_by'] = self.completed_by
        dict['completion_status'] = self.completion_status
        dict['date_created'] = self.date_created
        dict['trace_id'] = self.trace_id

        return dict
