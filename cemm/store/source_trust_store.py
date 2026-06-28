from __future__ import annotations
import sqlite3
from dataclasses import dataclass


@dataclass
class SourceTrustEntry:
    source_id: str
    domain: str
    trust: float = 0.5
    evidence_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    last_observed_at: float = 0.0


class SourceTrustStore:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def get(self, source_id: str, domain: str) -> SourceTrustEntry | None:
        row = self.conn.execute(
            "SELECT * FROM source_trust WHERE source_id = ? AND domain = ?",
            (source_id, domain),
        ).fetchone()
        if row is None:
            return None
        return SourceTrustEntry(
            source_id=row["source_id"],
            domain=row["domain"],
            trust=row["trust"],
            evidence_count=row["evidence_count"],
            success_count=row["success_count"],
            failure_count=row["failure_count"],
            last_observed_at=row["last_observed_at"],
        )

    def update(self, entry: SourceTrustEntry) -> None:
        self.conn.execute(
            """INSERT OR REPLACE INTO source_trust
               (source_id, domain, trust, evidence_count, success_count, failure_count, last_observed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (entry.source_id, entry.domain, entry.trust,
             entry.evidence_count, entry.success_count,
             entry.failure_count, entry.last_observed_at),
        )
        self.conn.commit()

    def record_outcome(self, source_id: str, domain: str, success: bool) -> SourceTrustEntry:
        existing = self.get(source_id, domain)
        if existing is None:
            existing = SourceTrustEntry(source_id=source_id, domain=domain)
        existing.evidence_count += 1
        if success:
            existing.success_count += 1
        else:
            existing.failure_count += 1
        ratio = existing.success_count / max(existing.evidence_count, 1)
        existing.trust = 0.3 + 0.7 * ratio
        existing.last_observed_at = __import__("time").time()
        self.update(existing)
        return existing

    def list_by_source(self, source_id: str) -> list[SourceTrustEntry]:
        rows = self.conn.execute(
            "SELECT * FROM source_trust WHERE source_id = ? ORDER BY domain", (source_id,)
        ).fetchall()
        return [
            SourceTrustEntry(
                source_id=r["source_id"], domain=r["domain"],
                trust=r["trust"], evidence_count=r["evidence_count"],
                success_count=r["success_count"], failure_count=r["failure_count"],
                last_observed_at=r["last_observed_at"],
            ) for r in rows
        ]

    def list_by_domain(self, domain: str) -> list[SourceTrustEntry]:
        rows = self.conn.execute(
            "SELECT * FROM source_trust WHERE domain = ? ORDER BY trust DESC", (domain,)
        ).fetchall()
        return [
            SourceTrustEntry(
                source_id=r["source_id"], domain=r["domain"],
                trust=r["trust"], evidence_count=r["evidence_count"],
                success_count=r["success_count"], failure_count=r["failure_count"],
                last_observed_at=r["last_observed_at"],
            ) for r in rows
        ]
