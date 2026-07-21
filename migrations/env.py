"""Alembic migration configuration."""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import settings

config = context.config

# Override sqlalchemy.url with value from settings
config.set_main_option("sqlalchemy.url", settings.sync_database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

from sqlalchemy import engine_from_config, pool, event
from sqlalchemy.orm import configure_mappers
from geoalchemy2.alembic import GistIndex  # enables spatial index rendering

# Import all models so Alembic can detect them
from app.database import Base
from app.models import *  # noqa: F401,F403

target_metadata = Base.metadata

# Ensure all mappers are configured before Alembic inspects metadata
configure_mappers()


def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
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
            include_object=_include_object,
            render_item=_render_item,
        )
        with context.begin_transaction():
            context.run_migrations()


def _include_object(object, name, type_, reflected, compare_to):
    """Skip internal GeoAlchemy2 helper tables."""
    if type_ == "table" and name == "spatial_ref_sys":
        return False
    return True


def _render_item(type_, obj, autogen_context):
    """Custom render for GeoAlchemy2 Geography type."""
    if type_ == "type" and isinstance(obj, Geography):
        autogen_context.imports.add("from geoalchemy2 import Geography")
        return repr(obj)
    return False


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
