from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.cemm_trainer import deploy_models


def test_deploy_handles_frame_classification() -> None:
    """deploy_models must process frame_classification outputs
    and produce frame engine model records."""
    import sqlite3
    import time
    import tempfile
    train_db = tempfile.mktemp(suffix=".db")
    conn = sqlite3.connect(train_db)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS training_examples (
            id TEXT PRIMARY KEY, task_type TEXT NOT NULL,
            payload_json TEXT NOT NULL DEFAULT '{}',
            permission_scope TEXT NOT NULL DEFAULT 'public',
            created_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS training_jobs (
            id TEXT PRIMARY KEY, example_id TEXT NOT NULL,
            task_type TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'queued',
            priority INTEGER NOT NULL DEFAULT 100,
            attempts INTEGER NOT NULL DEFAULT 0,
            created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS agent_outputs (
            id TEXT PRIMARY KEY, job_id TEXT NOT NULL,
            output_json TEXT, confidence REAL,
            created_at INTEGER NOT NULL
        );
    """)
    ts = int(time.time())
    conn.execute("INSERT INTO training_examples (id, task_type, payload_json, created_at) VALUES ('ex1', 'frame_classification', '{}', ?)", (ts,))
    conn.execute("INSERT INTO training_jobs (id, example_id, task_type, status, priority, created_at, updated_at) VALUES ('job1', 'ex1', 'frame_classification', 'done', 100, ?, ?)", (ts, ts))
    conn.execute("INSERT INTO agent_outputs (id, job_id, output_json, confidence, created_at) VALUES ('out1', 'job1', '{\"frame_key\": \"schedule\"}', 0.85, ?)", (ts,))
    conn.commit()
    conn.close()

    count = deploy_models(train_db)
    assert count > 0, "deploy_models should produce at least one model record for frame_classification"


def test_deploy_handles_predicate_mapping() -> None:
    """deploy_models must process predicate_mapping outputs."""
    import sqlite3
    import time
    import tempfile
    train_db = tempfile.mktemp(suffix=".db")
    conn = sqlite3.connect(train_db)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS training_examples (
            id TEXT PRIMARY KEY, task_type TEXT NOT NULL,
            payload_json TEXT NOT NULL DEFAULT '{}',
            permission_scope TEXT NOT NULL DEFAULT 'public',
            created_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS training_jobs (
            id TEXT PRIMARY KEY, example_id TEXT NOT NULL,
            task_type TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'queued',
            priority INTEGER NOT NULL DEFAULT 100,
            attempts INTEGER NOT NULL DEFAULT 0,
            created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS agent_outputs (
            id TEXT PRIMARY KEY, job_id TEXT NOT NULL,
            output_json TEXT, confidence REAL,
            created_at INTEGER NOT NULL
        );
    """)
    ts = int(time.time())
    conn.execute("INSERT INTO training_examples (id, task_type, payload_json, created_at) VALUES ('ex1', 'predicate_mapping', '{}', ?)", (ts,))
    conn.execute("INSERT INTO training_jobs (id, example_id, task_type, status, priority, created_at, updated_at) VALUES ('job1', 'ex1', 'predicate_mapping', 'done', 100, ?, ?)", (ts, ts))
    conn.execute("INSERT INTO agent_outputs (id, job_id, output_json, confidence, created_at) VALUES ('out1', 'job1', '{\"predicate_map\": {\"input\": \"output\"}}', 0.8, ?)", (ts,))
    conn.commit()
    conn.close()

    count = deploy_models(train_db)
    assert count > 0, "deploy_models should produce a model record for predicate_mapping"
