"""Additive SQLite migration tests."""

from __future__ import annotations

from sqlalchemy import create_engine

from app.db import _apply_sqlite_additive_migrations


def test_additive_migration_adds_phase4_clip_columns(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE jobs (id VARCHAR(36) PRIMARY KEY)"
        )
        connection.exec_driver_sql(
            "CREATE TABLE clips (id VARCHAR(36) PRIMARY KEY)"
        )

    _apply_sqlite_additive_migrations(engine)

    with engine.connect() as connection:
        job_columns = {
            row[1]
            for row in connection.exec_driver_sql("PRAGMA table_info(jobs)")
        }
        clip_columns = {
            row[1]
            for row in connection.exec_driver_sql("PRAGMA table_info(clips)")
        }

    assert "clip_selection_model" in job_columns
    assert "has_speech" in job_columns
    assert {"crop_plan", "tracking_details"} <= clip_columns

    # Re-running the migration must be harmless.
    _apply_sqlite_additive_migrations(engine)
