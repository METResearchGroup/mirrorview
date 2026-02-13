"""SQLAlchemy declarative base shared by all ORM models.

This module provides the Base class that every table model in app.db.models
inherits from. It is used to register mappings and support Alembic migrations.
"""
from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all ORM models."""

