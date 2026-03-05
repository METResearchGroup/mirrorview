from __future__ import annotations

import logging
import os
from pathlib import Path

from alembic import command
from alembic.config import Config

logger = logging.getLogger(__name__)


def run_migrations_to_head(database_url: str) -> None:
    """Apply Alembic migrations to `head` using DATABASE_URL.

    This is intended to run during service startup when persistence is enabled.
    """
    backend_root = Path(__file__).resolve().parents[2]
    alembic_ini = backend_root / "alembic.ini"
    if not alembic_ini.exists():
        raise FileNotFoundError(f"Missing alembic.ini at expected path: {alembic_ini}")

    cfg = Config(str(alembic_ini))

    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = database_url
    try:
        logger.info("db_migrate_start target=head")
        command.upgrade(cfg, "head")
        logger.info("db_migrate_complete target=head")
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous

