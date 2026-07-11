"""GraphPatch extraction boundary.

The graph builder emits StructuralObservation objects that carry structural
propositions with full provenance. This extractor converts those observations
to GraphPatch objects that can be authorized and committed by downstream
contract compilation.

The insult/object-surface sanitization code has been removed per CEMM 3.3
substrate law 3.1 — surface evidence may not repair semantic content after
interpretation is complete.
"""

from __future__ import annotations

from typing import Any

from ..types.graph_patch import GraphPatch, PatchOperation
from ..types.uol_graph import UOLGraph
from .learning_types import StructuralObservation


class GraphPatchExtractor:
    def extract(
        self,
        graph: UOLGraph,
        meaning_frames: list[Any] | None = None,
        obligation_contract: Any | None = None,
    ) -> list[GraphPatch]:
        patches = self._observations_to_patches(graph)
        if obligation_contract is not None:
            patches = self._authorized_patches(patches, obligation_contract)
        graph.patch_candidates = list(patches)
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
    def _observations_to_patches(graph: UOLGraph) -> list[GraphPatch]:
        """Convert StructuralObservation list to grouped GraphPatch list.

        Observations with the same target + source_refs + permission_refs +
        reason are grouped into a single GraphPatch.
        """
        from collections import defaultdict

        groups: dict[tuple, list[StructuralObservation]] = defaultdict(list)
        for obs in getattr(graph, "structural_observations", []) or []:
            key = (
                obs.target,
                tuple(obs.source_refs),
                tuple(obs.permission_refs),
                obs.reason,
            )
            groups[key].append(obs)

        patches: list[GraphPatch] = []
        for (target, source_refs, permission_refs, reason), obs_list in groups.items():
            operations = [
                PatchOperation(
                    operation=obs.operation,
                    target_id=obs.target_id,
                    fields=dict(obs.fields),
                    confidence=obs.confidence,
                    reason=obs.reason,
                )
                for obs in obs_list
            ]
            all_evidence: list[str] = []
            all_group_ids: list[str] = []
            for obs in obs_list:
                all_evidence.extend(obs.evidence_refs)
                if obs.source_group_id:
                    all_group_ids.append(obs.source_group_id)
            deduped_evidence = list(dict.fromkeys(all_evidence))
            patches.append(GraphPatch(
                source_graph_id=graph.id,
                target=target,
                operations=operations,
                source_refs=list(source_refs),
                permission_refs=list(permission_refs),
                evidence_refs=deduped_evidence,
                confidence=max(obs.confidence for obs in obs_list),
                reason=reason,
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
    def _should_retain_exemplar(graph: UOLGraph) -> bool:
        return bool(graph.candidate_sets or graph.affordance_predictions or graph.construction_matches)
