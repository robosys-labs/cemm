"""Seed construction lattice.

Construction records are form-meaning operators. This in-memory version uses
group features as a lightweight matching surface and can be updated by
construction observation patches.
"""

from __future__ import annotations

from typing import Any, Iterable

from ..types.construction_atom import (
    ConstructionAtom,
    FormSignature,
    PortConstraint,
    PragmaticPattern,
)
from ..types.graph_patch import GraphPatch
from ..types.meaning_percept import MeaningPerceptPacket
from ..types.uol_graph import ConstructionMatch, UOLGraph


class ConstructionLattice:
    def __init__(self, constructions: Iterable[ConstructionAtom] | None = None) -> None:
        self._records: dict[str, ConstructionAtom] = {}
        self._seed()
        for record in constructions or []:
            self.upsert(record)

    def upsert(self, record: ConstructionAtom) -> ConstructionAtom:
        existing = self._records.get(record.construction_id)
        if existing is None:
            self._records[record.construction_id] = record
            return record
        if record.form_signature.surface_pattern:
            existing.form_signature = record.form_signature
        if record.graph_signature is not None:
            existing.graph_signature = record.graph_signature
        if record.pragmatic_signature is not None:
            existing.pragmatic_signature = record.pragmatic_signature
        existing_ports = {pc.port_key for pc in existing.port_constraints}
        for pc in record.port_constraints:
            if pc.port_key not in existing_ports:
                existing.port_constraints.append(pc)
        existing.support_count += record.support_count
        existing.confidence = max(existing.confidence, record.confidence)
        return existing

    def match(self, packet: MeaningPerceptPacket, _graph: UOLGraph) -> list[ConstructionMatch]:
        matches: list[ConstructionMatch] = []
        for group in packet.meaning_groups:
            for record in self._records.values():
                surface = record.form_signature.surface_pattern
                if surface and group.group_type not in surface.split(",") and group.group_type != surface:
                    continue
                expected_ports = [pc.port_key for pc in record.port_constraints]
                pragmatic_hints = list(record.pragmatic_signature.expected_acts) if record.pragmatic_signature else []
                matches.append(ConstructionMatch(
                    id=f"cx_{group.id}_{record.construction_id}",
                    construction_key=record.construction_id,
                    group_id=group.id,
                    matched_span_ids=[self._span_id_for_group(packet, group)],
                    expected_ports=expected_ports,
                    graph_patch_templates=[{
                        "target": "construction_lattice",
                        "operation": "observe_construction_match",
                        "construction_key": record.construction_id,
                    }],
                    pragmatic_hints=pragmatic_hints,
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
            record = ConstructionAtom(
                construction_id=key,
                form_signature=FormSignature(
                    surface_pattern=str(fields.get("group_type", "")),
                ),
                port_constraints=[
                    PortConstraint(port_key=str(p))
                    for p in fields.get("expected_ports", [])
                ],
                pragmatic_signature=PragmaticPattern(
                    expected_acts=[str(h) for h in fields.get("pragmatic_hints", [])],
                ),
                confidence=operation.confidence,
                support_count=1,
            )
            self.upsert(record)
            applied.append(operation.target_id)
        return applied

    def snapshot(self) -> dict[str, Any]:
        return {
            key: {
                "construction_id": record.construction_id,
                "form_signature": {
                    "surface_pattern": record.form_signature.surface_pattern,
                },
                "port_constraints": [
                    {"port_key": pc.port_key} for pc in record.port_constraints
                ],
                "pragmatic_acts": list(record.pragmatic_signature.expected_acts) if record.pragmatic_signature else [],
                "confidence": record.confidence,
                "support_count": record.support_count,
            }
            for key, record in sorted(self._records.items())
        }

    def _seed(self) -> None:
        for item in [
            ("definition_or_claim_teaching", "teaching",
             ["source", "target", "relation"], ["definition_teaching"], 0.62),
            ("question", "question",
             ["speaker", "topic", "evidence"], ["question"], 0.58),
            ("command_request", "command",
             ["actor", "action", "target"], ["command_request"], 0.58),
            ("state_report", "state_report",
             ["holder", "state", "time", "place"], ["state_report"], 0.58),
            ("repair", "repair",
             ["speaker", "repair_target"], ["repair"], 0.58),
            ("social_turn", "social,closing,answer",
             ["speaker", "listener"], ["social_response"], 0.55),
        ]:
            cid, surface, ports, acts, conf = item
            self.upsert(ConstructionAtom(
                construction_id=cid,
                form_signature=FormSignature(surface_pattern=surface),
                port_constraints=[PortConstraint(port_key=p) for p in ports],
                pragmatic_signature=PragmaticPattern(expected_acts=acts),
                confidence=conf,
            ))

    @staticmethod
    def _span_id_for_group(packet: MeaningPerceptPacket, group: Any) -> str:
        for span in packet.spans:
            if span.span_type == "clause" and span.start_token <= group.start_token and span.end_token >= group.end_token:
                return span.id
        return f"group_span:{group.id}"
