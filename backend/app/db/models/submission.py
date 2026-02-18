"""Submission model: one user submission (input text) and its metadata.

A Submission represents a single user request to "flip" text—e.g. from formal
to casual or vice versa. It stores the original input_text, client-side
timestamp (client_created_at), server receipt time, and optional client_metadata
(JSON). All generations and feedback events (thumbs, edits) are linked to a
submission via submission_id. Stored for analytics, debugging, and linking
feedback back to the original request.
"""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import DateTime, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    client_created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    input_text: Mapped[str] = mapped_column(Text, nullable=False)
    selected_model_id: Mapped[str] = mapped_column(Text, nullable=False)
    server_received_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    client_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

