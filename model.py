"""Declaring data models"""

import sqlalchemy
import sqlalchemy.ext.declarative
from sqlalchemy.orm import relationship

Base = sqlalchemy.ext.declarative.declarative_base()

# pylint: disable=R0903

class Address(Base):
    """Address representation."""

    __tablename__ = "address"
    address_id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    address = sqlalchemy.Column(sqlalchemy.String, unique=True)
