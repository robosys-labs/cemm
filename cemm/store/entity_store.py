from __future__ import annotations
import sqlite3
from ..types.entity import Entity, EntityType


def _row_to_entity(row: sqlite3.Row, aliases: list[str] | None = None) -> Entity:
    return Entity(
        id=row["id"],
        type=EntityType(row["type"]),
        name=row["name"],
        aliases=aliases or [],
        confidence=row["confidence"],
        created_from_signal_id=row["created_from_signal_id"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        version=row["version"],
    )


class EntityStore:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def put(self, entity: Entity) -> None:
        self.conn.execute(
            """INSERT OR REPLACE INTO entities
               (id, type, name, confidence, created_from_signal_id, created_at, updated_at, version)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                entity.id, entity.type.value, entity.name, entity.confidence,
                entity.created_from_signal_id, entity.created_at,
                entity.updated_at, entity.version,
            ),
        )
        self.conn.execute("DELETE FROM entity_aliases WHERE entity_id = ?", (entity.id,))
        for alias in entity.aliases:
            self.conn.execute(
                "INSERT INTO entity_aliases (entity_id, alias) VALUES (?, ?)",
                (entity.id, alias),
            )
        self.conn.commit()

    def get(self, entity_id: str) -> Entity | None:
        row = self.conn.execute("SELECT * FROM entities WHERE id = ?", (entity_id,)).fetchone()
        if row is None:
            return None
        entity = _row_to_entity(row)
        alias_rows = self.conn.execute(
            "SELECT alias FROM entity_aliases WHERE entity_id = ?", (entity_id,)
        ).fetchall()
        entity.aliases = [r["alias"] for r in alias_rows]
        return entity

    def _load_aliases(self, entity_id: str) -> list[str]:
        return [
            r["alias"] for r in self.conn.execute(
                "SELECT alias FROM entity_aliases WHERE entity_id = ?", (entity_id,)
            )
        ]

    def find_by_name(self, name: str, type_filter: str | None = None) -> list[Entity]:
        if type_filter:
            rows = self.conn.execute(
                "SELECT * FROM entities WHERE name = ? AND type = ? ORDER BY confidence DESC",
                (name, type_filter),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM entities WHERE name = ? ORDER BY confidence DESC", (name,)
            ).fetchall()
        return [_row_to_entity(r, self._load_aliases(r["id"])) for r in rows]

    def find_by_alias(self, alias: str) -> list[Entity]:
        rows = self.conn.execute(
            """SELECT e.* FROM entities e
               JOIN entity_aliases ea ON e.id = ea.entity_id
               WHERE ea.alias = ?
               ORDER BY e.confidence DESC""",
            (alias,),
        ).fetchall()
        return [_row_to_entity(r, self._load_aliases(r["id"])) for r in rows]

    def find_by_type(self, type_val: str, limit: int = 100) -> list[Entity]:
        rows = self.conn.execute(
            "SELECT * FROM entities WHERE type = ? ORDER BY name LIMIT ?",
            (type_val, limit),
        ).fetchall()
        return [_row_to_entity(r, self._load_aliases(r["id"])) for r in rows]

    def list_active(self, limit: int = 100) -> list[Entity]:
        rows = self.conn.execute(
            "SELECT * FROM entities ORDER BY updated_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [_row_to_entity(r, self._load_aliases(r["id"])) for r in rows]

    def delete(self, entity_id: str) -> None:
        self.conn.execute("DELETE FROM entity_aliases WHERE entity_id = ?", (entity_id,))
        self.conn.execute("DELETE FROM entities WHERE id = ?", (entity_id,))
        self.conn.commit()
