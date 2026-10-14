from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS rooms (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  join_key_hash TEXT NOT NULL,
  admin_token_hash TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS drinks (
  id INTEGER PRIMARY KEY,
  room_id TEXT NOT NULL REFERENCES rooms(id),
  key TEXT NOT NULL,
  name TEXT NOT NULL,
  abv TEXT NOT NULL,
  step_ml INTEGER NOT NULL,
  presets_json TEXT NOT NULL,
  sort_order INTEGER NOT NULL,
  active INTEGER NOT NULL DEFAULT 1,
  UNIQUE(room_id, key)
);

CREATE TABLE IF NOT EXISTS participants (
  id TEXT PRIMARY KEY,
  room_id TEXT NOT NULL REFERENCES rooms(id),
  nickname TEXT NOT NULL,
  token_hash TEXT NOT NULL,
  device_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  last_seen_at TEXT NOT NULL,
  UNIQUE(room_id, nickname)
);

CREATE TABLE IF NOT EXISTS drink_logs (
  id INTEGER PRIMARY KEY,
  room_id TEXT NOT NULL,
  participant_id TEXT NOT NULL,
  drink_id INTEGER NOT NULL,
  delta_ml INTEGER NOT NULL,
  abv_snapshot TEXT NOT NULL,
  drink_name_snapshot TEXT NOT NULL,
  drink_key_snapshot TEXT NOT NULL,
  shanghai_date TEXT NOT NULL,
  editor_participant_id TEXT,
  editor_nickname TEXT NOT NULL,
  subject_nickname TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_logs_room_date ON drink_logs(room_id, shanghai_date);
CREATE INDEX IF NOT EXISTS idx_logs_room_person ON drink_logs(room_id, participant_id);
CREATE INDEX IF NOT EXISTS idx_logs_room_id ON drink_logs(room_id, id);

CREATE TABLE IF NOT EXISTS room_events (
  id INTEGER PRIMARY KEY,
  room_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  detail_json TEXT NOT NULL,
  actor TEXT NOT NULL,
  created_at TEXT NOT NULL
);
"""


class Database:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.conn = sqlite3.connect(str(path), check_same_thread=False, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.execute("PRAGMA busy_timeout=4000")
        self.conn.executescript(SCHEMA)

    def transaction(self):
        return _Transaction(self)

    def close(self) -> None:
        self.conn.close()


class _Transaction:
    def __init__(self, db: Database):
        self.db = db

    def __enter__(self) -> sqlite3.Connection:
        self.db._lock.acquire()
        try:
            self.db.conn.execute("BEGIN IMMEDIATE")
        except Exception:
            self.db._lock.release()
            raise
        return self.db.conn

    def __exit__(self, exc_type, exc, tb) -> bool:
        try:
            if exc_type:
                self.db.conn.execute("ROLLBACK")
            else:
                self.db.conn.execute("COMMIT")
        finally:
            self.db._lock.release()
        return False
