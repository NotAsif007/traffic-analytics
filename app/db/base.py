"""
SQLAlchemy declarative base.

All ORM models inherit from Base.
Import this module (not the models themselves) in alembic/env.py
so that Alembic can discover all mapped tables for autogeneration.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Root declarative base for all SQLAlchemy models.

    Using the new 2.x mapped_column / Mapped API throughout.
    """

    pass
