"""Histórico mínimo: armazena hash, nunca o texto original do chamado."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def connect(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA journal_mode=WAL")
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def initialize(path: Path):
    with connect(path) as connection:
        connection.executescript("""
        CREATE TABLE IF NOT EXISTS predictions (
            id TEXT PRIMARY KEY, created_at TEXT NOT NULL, input_sha256 TEXT NOT NULL,
            predicted_label TEXT NOT NULL, score REAL NOT NULL, model_version TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS feedback (
            prediction_id TEXT PRIMARY KEY REFERENCES predictions(id),
            correct_label TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        """)

