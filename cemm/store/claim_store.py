from __future__ import annotations
import sqlite3
import json
import time
from ..types.claim import Claim, ClaimStatus
from ..types.permission import Permission, PermissionScope, RetentionPolicy


def _serialize_object_value(ov: object) -> str | None:
    if ov is None:
        return None
    if isinstance(ov, bool):
        return "true" if ov else "false"
    if isinstance(ov, (int, float)):
        return str(ov)
    return str(ov)


def _deserialize_object_value(ov_str: str | None) -> object:
    if ov_str is None:
        return None
    if ov_str == "true":
        return True
    if ov_str == "false":
        return False
    try:
        return int(ov_str)
    except (ValueError, TypeError):
        pass
    try:
        return float(ov_str)
    except (ValueError, TypeError):
        pass
    return ov_str


def _row_to_claim(row: sqlite3.Row) -> Claim:
    return Claim(
        id=row["id"],
        subject_entity_id=row["subject_entity_id"],
        predicate=row["predicate"],
        predicate_model_id=row["predicate_model_id"],
        object_entity_id=row["object_entity_id"],
        object_value=_deserialize_object_value(row["object_value"]),
        evidence_signal_ids=[],
        source_id=row["source_id"],
        domain=row["domain"],
        confidence=row["confidence"],
        confidence_log_odds=row["confidence_log_odds"],
        trust=row["trust"],
        salience=row["salience"],
        status=ClaimStatus(row["status"]),
        supersedes_claim_id=row["supersedes_claim_id"],
        frame_id=row["frame_id"],
        valid_from=row["valid_from"],
        valid_until=row["valid_until"],
        observed_at=row["observed_at"],
        updated_at=row["updated_at"],
        permission=Permission(
            scope=PermissionScope(row["permission_scope"]),
            retention=RetentionPolicy(row["permission_retention"]),
            may_store=bool(row["permission_may_store"]),
            may_retrieve=bool(row["permission_may_retrieve"]),
            may_use=bool(row["permission_may_use"]),
        ),
        version=row["version"],
    )


class ClaimStore:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self._cache: dict[str, Claim] = {}

    def put(self, claim: Claim) -> None:
        perm = claim.permission or Permission.public()
        self.conn.execute(
            """INSERT OR REPLACE INTO claims
               (id, subject_entity_id, predicate, predicate_model_id,
                object_entity_id, object_value, source_id, domain,
                confidence, confidence_log_odds, trust, salience,
                status, supersedes_claim_id, frame_id, valid_from, valid_until,
                observed_at, updated_at,
                permission_scope, permission_retention, permission_may_store,
                permission_may_retrieve, permission_may_use, version)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                claim.id, claim.subject_entity_id, claim.predicate, claim.predicate_model_id,
                claim.object_entity_id, _serialize_object_value(claim.object_value),
                claim.source_id, claim.domain,
                claim.confidence, claim.confidence_log_odds, claim.trust, claim.salience,
                claim.status.value, claim.supersedes_claim_id, claim.frame_id,
                claim.valid_from, claim.valid_until,
                claim.observed_at, claim.updated_at,
                perm.scope.value, perm.retention.value,
                int(perm.may_store), int(perm.may_retrieve), int(perm.may_use),
                claim.version,
            ),
        )
        self.conn.execute("DELETE FROM claim_evidence WHERE claim_id = ?", (claim.id,))
        for sig_id in claim.evidence_signal_ids:
            self.conn.execute(
                "INSERT INTO claim_evidence (claim_id, signal_id) VALUES (?, ?)",
                (claim.id, sig_id),
            )
        self.conn.execute("DELETE FROM claim_qualifiers WHERE claim_id = ?", (claim.id,))
        for k, v in claim.qualifiers.items():
            self.conn.execute(
                "INSERT INTO claim_qualifiers (claim_id, key, value) VALUES (?, ?, ?)",
                (claim.id, k, str(v) if v is not None else None),
            )
        self.conn.commit()
        self._cache[claim.id] = claim

        from ..causal.temporal import derive_temporal_relations
        temporal_relations = derive_temporal_relations(claim, self)
        for tr in temporal_relations:
            tc = Claim(
                id=f"temp_{claim.id}_{tr.object_claim_id}",
                subject_entity_id=claim.subject_entity_id,
                predicate=tr.relation.value,
                object_entity_id="",
                object_value=tr.object_claim_id,
                evidence_signal_ids=claim.evidence_signal_ids,
                source_id=claim.source_id,
                domain="temporal",
                confidence=tr.confidence,
                status=ClaimStatus.ACTIVE,
                observed_at=time.time(),
                updated_at=time.time(),
            )
            self.put(tc)

    def get(self, claim_id: str) -> Claim | None:
        if claim_id in self._cache:
            return self._cache[claim_id]
        row = self.conn.execute("SELECT * FROM claims WHERE id = ?", (claim_id,)).fetchone()
        if row is None:
            return None
        claim = _row_to_claim(row)
        ev_rows = self.conn.execute(
            "SELECT signal_id FROM claim_evidence WHERE claim_id = ?", (claim_id,)
        ).fetchall()
        claim.evidence_signal_ids = [r["signal_id"] for r in ev_rows]
        q_rows = self.conn.execute(
            "SELECT key, value FROM claim_qualifiers WHERE claim_id = ?", (claim_id,)
        ).fetchall()
        claim.qualifiers = {r["key"]: r["value"] for r in q_rows}
        self._cache[claim_id] = claim
        return claim

    def _enrich(self, claim: Claim) -> Claim:
        ev_rows = self.conn.execute(
            "SELECT signal_id FROM claim_evidence WHERE claim_id = ?", (claim.id,)
        ).fetchall()
        claim.evidence_signal_ids = [r["signal_id"] for r in ev_rows]
        q_rows = self.conn.execute(
            "SELECT key, value FROM claim_qualifiers WHERE claim_id = ?", (claim.id,)
        ).fetchall()
        claim.qualifiers = {r["key"]: r["value"] for r in q_rows}
        return claim

    def find_by_subject(self, subject_entity_id: str, predicate: str | None = None, limit: int = 100) -> list[Claim]:
        if predicate:
            rows = self.conn.execute(
                "SELECT * FROM claims WHERE subject_entity_id = ? AND predicate = ? ORDER BY observed_at DESC LIMIT ?",
                (subject_entity_id, predicate, limit),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM claims WHERE subject_entity_id = ? ORDER BY observed_at DESC LIMIT ?",
                (subject_entity_id, limit),
            ).fetchall()
        return [self._enrich(_row_to_claim(r)) for r in rows]

    def find_by_predicate_model(self, predicate_model_id: str, limit: int = 100) -> list[Claim]:
        rows = self.conn.execute(
            "SELECT * FROM claims WHERE predicate_model_id = ? ORDER BY observed_at DESC LIMIT ?",
            (predicate_model_id, limit),
        ).fetchall()
        return [self._enrich(_row_to_claim(r)) for r in rows]

    def find_by_object(self, object_entity_id: str, limit: int = 100) -> list[Claim]:
        rows = self.conn.execute(
            "SELECT * FROM claims WHERE object_entity_id = ? ORDER BY observed_at DESC LIMIT ?",
            (object_entity_id, limit),
        ).fetchall()
        return [self._enrich(_row_to_claim(r)) for r in rows]

    def find_by_domain(self, domain: str, source_id: str | None = None, limit: int = 100) -> list[Claim]:
        if source_id:
            rows = self.conn.execute(
                "SELECT * FROM claims WHERE domain = ? AND source_id = ? ORDER BY observed_at DESC LIMIT ?",
                (domain, source_id, limit),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM claims WHERE domain = ? ORDER BY observed_at DESC LIMIT ?",
                (domain, limit),
            ).fetchall()
        return [self._enrich(_row_to_claim(r)) for r in rows]

    def find_by_frame(self, frame_id: str, status: str | None = None, limit: int = 100) -> list[Claim]:
        if status:
            rows = self.conn.execute(
                "SELECT * FROM claims WHERE frame_id = ? AND status = ? ORDER BY valid_from DESC LIMIT ?",
                (frame_id, status, limit),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM claims WHERE frame_id = ? ORDER BY valid_from DESC LIMIT ?",
                (frame_id, limit),
            ).fetchall()
        return [self._enrich(_row_to_claim(r)) for r in rows]

    def find_active(self, limit: int = 100) -> list[Claim]:
        rows = self.conn.execute(
            "SELECT * FROM claims WHERE status = 'active' ORDER BY observed_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [self._enrich(_row_to_claim(r)) for r in rows]

    def find_contradictions(self, subject_id: str, predicate: str) -> list[Claim]:
        rows = self.conn.execute(
            "SELECT * FROM claims WHERE subject_entity_id = ? AND predicate = ? AND status = 'active' ORDER BY observed_at DESC",
            (subject_id, predicate),
        ).fetchall()
        return [self._enrich(_row_to_claim(r)) for r in rows]
