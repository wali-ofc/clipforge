"""Database engine and session helpers."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import Settings


class Base(DeclarativeBase):
    pass


def ensure_sqlite_directory(database_url: str) -> None:
    """Create the parent directory for a file-backed SQLite database."""
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        return

    raw_path = database_url[len(prefix) :]
    if raw_path in {":memory:", ""} or raw_path.startswith("file:"):
        return

    Path(raw_path).parent.mkdir(parents=True, exist_ok=True)


def create_engine_from_settings(settings: Settings) -> Engine:
    ensure_sqlite_directory(settings.database_url)

    connect_args: dict[str, object] = {}
    if settings.database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    engine = create_engine(
        settings.database_url,
        connect_args=connect_args,
        pool_pre_ping=True,
    )

    if settings.database_url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragmas(dbapi_connection, _connection_record) -> None:
            cursor = dbapi_connection.cursor()
            try:
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.execute("PRAGMA busy_timeout=5000")
            finally:
                cursor.close()

    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )


def init_db(engine: Engine) -> None:
    # Importing the models registers them on Base.metadata.
    from app.models import clip, job  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _apply_sqlite_additive_migrations(engine)


def _apply_sqlite_additive_migrations(engine: Engine) -> None:
    """Add columns introduced after a database was first created.

    ``create_all`` never alters existing tables. This project intentionally
    avoids a migration framework, so additive SQLite columns are applied
    here. Only constant column definitions are interpolated.
    """
    if engine.dialect.name != "sqlite":
        return

    additions: dict[str, dict[str, str]] = {
        "jobs": {
            "transcript_path": "VARCHAR(1024)",
            "transcript_language": "VARCHAR(16)",
            "transcript_segment_count": "INTEGER",
            "has_speech": "BOOLEAN",
            "clip_count": "INTEGER NOT NULL DEFAULT 0",
            "clip_selection_model": "VARCHAR(128)",
        },
        "clips": {
            "crop_plan": "JSON NOT NULL DEFAULT '{}'",
            "tracking_details": "JSON NOT NULL DEFAULT '{}'",
        },
    }

    with engine.begin() as connection:
        for table, columns in additions.items():
            existing = {
                row[1]
                for row in connection.exec_driver_sql(
                    f"PRAGMA table_info({table})"
                )
            }
            for column, definition in columns.items():
                if column not in existing:
                    connection.exec_driver_sql(
                        f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
                    )
