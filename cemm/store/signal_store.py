from __future__ import annotations
import sqlite3
from ..types.signal import Signal, SignalKind, SourceType
from ..types.permission import Permission, PermissionScope, RetentionPolicy


def _row_to_signal(row: sqlite3.Row) -> Signal:
    return Signal(
        id=row["id"],
        kind=SignalKind(row["kind"]),
        source_id=row["source_id"],
        source_type=SourceType(row["source_type"]),
        content=row["content"],
        observed_at=row["observed_at"],
        context_id=row["context_id"],
        salience=row["salience"],
        trust=row["trust"],
        permission=Permission(
            scope=PermissionScope(row["permission_scope"]),
            may_store=bool(row["permission_may_store"]),
            may_retrieve=bool(row["permission_may_retrieve"]),
            may_use=bool(row["permission_may_use"]),
            may_share=bool(row["permission_may_share"]),
            may_execute=bool(row["permission_may_execute"]),
            retention=RetentionPolicy(row["permission_retention"]),
        ),
        parent_signal_id=row["parent_signal_id"],
        version=row["version"],
    )


class SignalStore:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def put(self, signal: Signal) -> None:
        self.conn.execute(
            """INSERT OR REPLACE INTO signals
               (id, kind, source_id, source_type, content, observed_at, context_id,
                salience, trust, permission_scope, permission_may_store,
                permission_may_retrieve, permission_may_use, permission_may_share,
                permission_may_execute, permission_retention, parent_signal_id, version)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                signal.id, signal.kind.value, signal.source_id, signal.source_type.value,
                signal.content, signal.observed_at, signal.context_id,
                signal.salience, signal.trust,
                signal.permission.scope.value,
                int(signal.permission.may_store), int(signal.permission.may_retrieve),
                int(signal.permission.may_use), int(signal.permission.may_share),
                int(signal.permission.may_execute), signal.permission.retention.value,
                signal.parent_signal_id, signal.version,
            ),
        )
        self.conn.commit()

    def get(self, signal_id: str) -> Signal | None:
        row = self.conn.execute("SELECT * FROM signals WHERE id = ?", (signal_id,)).fetchone()
        if row is None:
            return None
        return _row_to_signal(row)

    def list_by_source(self, source_id: str, limit: int = 100) -> list[Signal]:
        rows = self.conn.execute(
            "SELECT * FROM signals WHERE source_id = ? ORDER BY observed_at DESC LIMIT ?",
            (source_id, limit),
        ).fetchall()
        return [_row_to_signal(r) for r in rows]

    def list_by_context(self, context_id: str, kind: str | None = None, limit: int = 100) -> list[Signal]:
        if kind:
            rows = self.conn.execute(
                "SELECT * FROM signals WHERE context_id = ? AND kind = ? ORDER BY observed_at DESC LIMIT ?",
                (context_id, kind, limit),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM signals WHERE context_id = ? ORDER BY observed_at DESC LIMIT ?",
                (context_id, limit),
            ).fetchall()
        return [_row_to_signal(r) for r in rows]

    def recent(self, limit: int = 50) -> list[Signal]:
        rows = self.conn.execute(
            "SELECT * FROM signals ORDER BY observed_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [_row_to_signal(r) for r in rows]

    def count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0]
