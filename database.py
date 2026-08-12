"""Shared SQLite configuration and schema management."""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


DATABASE_FILE = Path(os.getenv("DATABASE_FILE", "data/whale_tracker.db"))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_FILE, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 10000")
    return connection


@contextmanager
def db_session():
    connection = connect()
    try:
        yield connection
    finally:
        connection.close()


def initialize_database() -> None:
    DATABASE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with db_session() as connection:
        connection.execute("PRAGMA journal_mode = WAL")
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS addresses (
                address TEXT PRIMARY KEY,
                first_seen TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                notes TEXT
            );

            CREATE TABLE IF NOT EXISTS leaderboard_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scrape_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                rank INTEGER NOT NULL,
                asset TEXT NOT NULL,
                whale_address TEXT NOT NULL,
                FOREIGN KEY (whale_address) REFERENCES addresses (address)
            );

            CREATE INDEX IF NOT EXISTS idx_leaderboard_address_asset_time
                ON leaderboard_snapshots (whale_address, asset, scrape_time DESC);

            CREATE TABLE IF NOT EXISTS position_details (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                whale_address TEXT NOT NULL,
                asset TEXT NOT NULL,
                position_size_usd REAL NOT NULL,
                unrealized_pnl REAL NOT NULL,
                leverage REAL NOT NULL,
                entry_price REAL NOT NULL,
                last_updated TIMESTAMP NOT NULL,
                FOREIGN KEY (whale_address) REFERENCES addresses (address),
                UNIQUE (whale_address, asset)
            );

            CREATE INDEX IF NOT EXISTS idx_positions_updated
                ON position_details (last_updated DESC);

            CREATE TABLE IF NOT EXISTS sync_status (
                component TEXT PRIMARY KEY,
                last_attempt TIMESTAMP NOT NULL,
                last_success TIMESTAMP,
                last_error TEXT
            );
            """
        )
        connection.commit()


def record_sync_status(component: str, success: bool, error: str | None = None) -> None:
    attempted_at = utc_now()
    with db_session() as connection:
        connection.execute(
            """
            INSERT INTO sync_status (component, last_attempt, last_success, last_error)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(component) DO UPDATE SET
                last_attempt = excluded.last_attempt,
                last_success = CASE
                    WHEN excluded.last_error IS NULL THEN excluded.last_attempt
                    ELSE sync_status.last_success
                END,
                last_error = excluded.last_error
            """,
            (component, attempted_at, attempted_at if success else None, None if success else (error or "unknown error")[:500]),
        )
        connection.commit()
