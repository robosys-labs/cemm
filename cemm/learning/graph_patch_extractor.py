"""GraphPatch extraction boundary.

The graph builder may emit seed patch candidates, but learning code should use
this boundary so future extractors can replace builder-side heuristics without
changing planner or consolidator contracts.
"""

from __future__ import annotations

import re
from typing import Any

from ..types.graph_patch import GraphPatch, PatchOperation
from ..types.uol_graph import UOLGraph


class GraphPatchExtractor:
    def extract(
        self,
        graph: UOLGraph,
        meaning_frames: list[Any] | None = None,
        obligation_contract: Any | None = None,
    ) -> list[GraphPatch]:
        patches = list(graph.patch_candidates)
        if obligation_contract is not None:
            patches = self._authorized_patches(patches, obligation_contract)
        if not patches and self._should_retain_exemplar(graph):
            if obligation_contract is not None:
                return []
            patches.append(GraphPatch(
                source_graph_id=graph.id,
                target="episodic_trace",
                operations=[
                    PatchOperation(
                        operation="retain_exemplar",
                        target_id=f"trace:{graph.id}",
                        fields={"raw_text": graph.raw_text},
                        confidence=0.5,
                        reason="interesting_graph_without_patch",
                    )
                ],
                confidence=0.5,
                reason="retain_sparse_exemplar",
            ))
        return patches

    @staticmethod
    def _authorized_patches(
        patches: list[GraphPatch],
        obligation_contract: Any,
    ) -> list[GraphPatch]:
        write_contract = getattr(obligation_contract, "write_contract", None)
        if write_contract is None or not getattr(write_contract, "is_writable", False):
            return []
        allowed_targets = set(getattr(write_contract, "allowed_patch_targets", []) or [])
        if not allowed_targets:
            return []
        commit_policy = getattr(write_contract, "commit_policy", "validate_only")
        if commit_policy in {"no_commit", "require_confirmation"}:
            return []
        authorized = [
            patch for patch in patches
            if getattr(patch, "target", "") in allowed_targets
        ]
        contract_features = dict(getattr(write_contract, "features", {}) or {})
        for patch in authorized:
            for op in getattr(patch, "operations", []) or []:
                fields = getattr(op, "fields", {}) or {}
                GraphPatchExtractor._sanitize_taught_object(fields, op)
                if fields.get("relation_key") != "has_property":
                    continue
                features = dict(fields.get("features", {}) or {})
                for key in ("dimension", "property_dimension", "relation_scope"):
                    if contract_features.get(key) and not features.get(key):
                        features[key] = contract_features[key]
                if features:
                    fields["features"] = features
                if contract_features.get("dimension") and not fields.get("dimension"):
                    fields["dimension"] = contract_features["dimension"]
                if contract_features.get("relation_scope") and not fields.get("relation_scope"):
                    fields["relation_scope"] = contract_features["relation_scope"]
        return authorized

    @staticmethod
    def _sanitize_taught_object(fields: dict[str, Any], op: Any) -> None:
        surface = str(fields.get("object_surface", "") or "")
        cleaned = GraphPatchExtractor._strip_addressed_insult_tail(surface)
        if not cleaned or cleaned == surface:
            return

        fields["object_surface"] = cleaned
        concept_id = str(fields.get("object_concept_id", "") or "")
        if concept_id:
            fields["object_concept_id"] = "concept:" + re.sub(
                r"[^a-z0-9]+", "_", cleaned.lower()
            ).strip("_")

        target_id = str(getattr(op, "target_id", "") or "")
        if target_id and surface.lower().replace(" ", "_") in target_id:
            setattr(op, "target_id", target_id.replace(
                surface.lower().replace(" ", "_"),
                cleaned.lower().replace(" ", "_"),
            ))

    @staticmethod
    def _strip_addressed_insult_tail(surface: str) -> str:
        text = surface.strip()
        if not text:
            return ""
        cleaned = re.sub(
            r"\s+you\s+(buffoon|idiot|moron|fool|dummy|stupid|clown)\s*$",
            "",
            text,
            flags=re.IGNORECASE,
        ).strip()
        return cleaned

    @staticmethod
    def _should_retain_exemplar(graph: UOLGraph) -> bool:
        return bool(graph.candidate_sets or graph.affordance_predictions or graph.construction_matches)
