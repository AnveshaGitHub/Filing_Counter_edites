from __future__ import annotations

from logging.config import fileConfig
import os
from pathlib import Path

from sqlalchemy import engine_from_config, pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

try:
    from dotenv import load_dotenv

    project_root = Path(__file__).resolve().parents[2]
    backend_root = project_root / "backend"
    load_dotenv(project_root / ".env")
    load_dotenv(backend_root / ".env")
except Exception:
    project_root = Path(__file__).resolve().parents[2]
    backend_root = project_root / "backend"

database_url = os.getenv("DATABASE_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)
else:
    sqlite_path = backend_root / "filing_counter.db"
    config.set_main_option("sqlalchemy.url", f"sqlite:///{sqlite_path.as_posix()}")

# Import app metadata
from app.db.base import Base  # noqa: E402
from app import models  # noqa: F401,E402  # ensure model tables are registered

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
