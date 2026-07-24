"""Append-only claim history and source-local correction/retraction projection."""
from __future__ import annotations

from ..storage import ClaimHistoryAction, ClaimHistoryRecord, ClaimRecord


class ClaimHistoryProjector:
    def effective_claims(
        self,
        claims: tuple[ClaimRecord, ...],
        history: tuple[ClaimHistoryRecord, ...],
    ) -> tuple[ClaimRecord, ...]:
        by_ref = {item.claim_record_ref: item for item in claims}
        latest_history: dict[str, ClaimHistoryRecord] = {}
        for item in history:
            current = latest_history.get(item.history_ref)
            if current is None or item.revision > current.revision:
                latest_history[item.history_ref] = item
        inactive: set[str] = set()
        for item in sorted(
            latest_history.values(),
            key=lambda value: (value.occurred_at or "", value.history_ref, value.revision),
        ):
            if item.action in {ClaimHistoryAction.CORRECT, ClaimHistoryAction.RETRACT, ClaimHistoryAction.SUPERSEDE} and item.target_claim_record_ref:
                target = by_ref.get(item.target_claim_record_ref)
                if target is not None and target.source_ref == item.source_ref:
                    inactive.add(target.claim_record_ref)
        return tuple(sorted((item for item in claims if item.claim_record_ref not in inactive), key=lambda value: value.claim_record_ref))

    def timeline(
        self,
        claim_record_ref: str,
        history: tuple[ClaimHistoryRecord, ...],
    ) -> tuple[ClaimHistoryRecord, ...]:
        return tuple(sorted(
            (item for item in history if item.claim_record_ref == claim_record_ref or item.target_claim_record_ref == claim_record_ref),
            key=lambda value: (value.occurred_at or "", value.history_ref, value.revision),
        ))
