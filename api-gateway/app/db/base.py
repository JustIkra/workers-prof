"""
SQLAlchemy Base class.

This module provides the declarative base for all ORM models.
Models are automatically registered with Base.metadata when they inherit from Base.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy models.

    All models inherit from this class to be registered in metadata.
    Models are automatically registered when they are imported anywhere in the application.
    """

    pass


# Note: Models should NOT be imported here to avoid circular imports.
# Alembic will find models via the env.py configuration.
