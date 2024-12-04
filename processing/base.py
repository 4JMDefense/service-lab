"""
This module defines the SQLAlchemy base class for the application's database models.

It imports the `declarative_base` function from SQLAlchemy and creates a `Base` class
that can be used as a foundation for all ORM models in the application.
"""

from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

