"""Seed construction lattice.

Construction records are form-meaning operators. This in-memory version uses
group features as a lightweight matching surface and can be updated by
construction observation patches.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from ..types.graph_patch import GraphPatch
from ..types.meaning_percept import MeaningPerceptPacket
from ..types.uol_graph import ConstructionMatch, UOLGraph


@dataclass
class ConstructionRecord:
    key: str
    group_types: set[str] = field(default_factory=set)
    expected_ports: list[str] = field(default_factory=list)
    pragmatic_hints: list[str] = field(default_factory=list)
    confidence: float = 0.5
    support_count: int = 0


class ConstructionLattice:
    def __init__(self, constructions: Iterable[ConstructionRecord] | None = None) -> None:
        self._records: dict[str, ConstructionRecord] = {}
        self._seed()
        for record in constructions or []:
            self.upsert(record)

    def upsert(self, record: ConstructionRecord) -> ConstructionRecord:
        existing = self._records.get(record.key)
        if existing is None:
            self._records[record.key] = record
            return record
        existing.group_types.update(record.group_types)
        existing.expected_ports = sorted({*existing.expected_ports, *record.expected_ports})
        existing.pragmatic_hints = sorted({*existing.pragmatic_hints, *record.pragmatic_hints})
        existing.confidence = max(existing.confidence, record.confidence)
        existing.support_count += record.support_count
        return existing

    def match(self, packet: MeaningPerceptPacket, _graph: UOLGraph) -> list[ConstructionMatch]:
        matches: list[ConstructionMatch] = []
        for group in packet.meaning_groups:
            for record in self._records.values():
                if group.group_type not in record.group_types:
                    continue
                matches.append(ConstructionMatch(
                    id=f"cx_{group.id}_{record.key}",
                    construction_key=record.key,
                    group_id=group.id,
                    matched_span_ids=[self._span_id_for_group(packet, group)],
                    expected_ports=list(record.expected_ports),
                    graph_patch_templates=[{
                        "target": "construction_lattice",
                        "operation": "observe_construction_match",
                        "construction_key": record.key,
                    }],
                    pragmatic_hints=list(record.pragmatic_hints),
                    confidence=max(group.confidence, record.confidence),
                ))
        return matches

    def apply_patch(self, patch: GraphPatch) -> list[str]:
        applied: list[str] = []
        if patch.target != "construction_lattice":
            return applied
        for operation in patch.operations:
            if operation.operation != "observe_construction_match":
                continue
            fields = operation.fields
            key = str(fields.get("construction_key") or operation.target_id.replace("construction:", ""))
            record = ConstructionRecord(
                key=key,
                group_types={str(fields.get("group_type"))} if fields.get("group_type") else set(),
                expected_ports=[str(port) for port in fields.get("expected_ports", [])],
                pragmatic_hints=[str(hint) for hint in fields.get("pragmatic_hints", [])],
                confidence=operation.confidence,
                support_count=1,
            )
            self.upsert(record)
            applied.append(operation.target_id)
        return applied

    def snapshot(self) -> dict[str, Any]:
        return {
            key: {
                "key": record.key,
                "group_types": sorted(record.group_types),
                "expected_ports": list(record.expected_ports),
                "pragmatic_hints": list(record.pragmatic_hints),
                "confidence": record.confidence,
                "support_count": record.support_count,
            }
            for key, record in sorted(self._records.items())
        }

    def _seed(self) -> None:
        for record in [
            ConstructionRecord("definition_or_claim_teaching", {"teaching"}, ["source", "target", "relation"], ["definition_teaching"], 0.62),
            ConstructionRecord("question", {"question"}, ["speaker", "topic", "evidence"], ["question"], 0.58),
            ConstructionRecord("command_request", {"command"}, ["actor", "action", "target"], ["command_request"], 0.58),
            ConstructionRecord("state_report", {"state_report"}, ["holder", "state", "time", "place"], ["state_report"], 0.58),
            ConstructionRecord("repair", {"repair"}, ["speaker", "repair_target"], ["repair"], 0.58),
            ConstructionRecord("social_turn", {"social", "closing", "answer"}, ["speaker", "listener"], ["social_response"], 0.55),
        ]:
            self.upsert(record)

    @staticmethod
    def _span_id_for_group(packet: MeaningPerceptPacket, group: Any) -> str:
        for span in packet.spans:
            if span.span_type == "clause" and span.start_token <= group.start_token and span.end_token >= group.end_token:
                return span.id
        return f"group_span:{group.id}"
