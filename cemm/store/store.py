from __future__ import annotations
import sqlite3
import uuid
import json
from pathlib import Path
from .schema import create_schema, create_indexes
from .signal_store import SignalStore
from .entity_store import EntityStore
from .claim_store import ClaimStore
from .model_store import ModelStore
from .action_store import ActionStore
from .self_store import SelfStore
from .source_trust_store import SourceTrustStore


class Store:
    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        create_schema(self.conn)
        create_indexes(self.conn)
        self.signals = SignalStore(self.conn)
        self.entities = EntityStore(self.conn)
        self.claims = ClaimStore(self.conn, store=self)
        self.models = ModelStore(self.conn)
        self.actions = ActionStore(self.conn)
        self.self_store = SelfStore(self.conn)
        self.source_trust = SourceTrustStore(self.conn)

    def close(self) -> None:
        self.conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        self.conn.close()

    def vacuum(self) -> None:
        self.conn.execute("VACUUM")

    def transaction(self) -> sqlite3.Connection:
        return self.conn
