"""Graph-patch extraction boundary with proposition-integrity enforcement."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from ..kernel.semantic_integrity import SemanticIntegrityValidator
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
        integrity = SemanticIntegrityValidator().validate_graph(graph)
        if not integrity.valid:
            graph.patch_candidates = []
            graph.trace["patch_extraction_blocked"] = True
            graph.trace["patch_extraction_block_reasons"] = list(integrity.errors)
            return []
        patches = self._observations_to_patches(graph)
        graph.patch_candidates = list(patches)
        if obligation_contract is not None:
            patches = self._authorized_patches(patches, obligation_contract)
        if not patches and obligation_contract is None and self._should_retain_exemplar(graph):
            patches.append(GraphPatch(
                source_graph_id=graph.id,
                target="episodic_trace",
                operations=[PatchOperation(
                    operation="retain_exemplar",
                    target_id=f"trace:{graph.id}",
                    fields={"raw_text": graph.raw_text},
                    confidence=0.5,
                    reason="interesting_graph_without_patch",
                )],
                confidence=0.5,
                reason="retain_sparse_exemplar",
            ))
        return patches

    @staticmethod
    def _observations_to_patches(graph: UOLGraph) -> list[GraphPatch]:
        groups: dict[tuple[Any, ...], list[StructuralObservation]] = defaultdict(list)
        for observation in getattr(graph, "structural_observations", []) or []:
            groups[(
                observation.target,
                tuple(observation.source_refs),
                tuple(observation.permission_refs),
                observation.reason,
            )].append(observation)
        patches: list[GraphPatch] = []
        for (target, source_refs, permission_refs, reason), observations in groups.items():
            operations: list[PatchOperation] = []
            evidence: list[str] = []
            for observation in observations:
                fields = dict(observation.fields)
                operation = PatchOperation(
                    operation=observation.operation,
                    target_id=observation.target_id,
                    fields=fields,
                    confidence=observation.confidence,
                    reason=observation.reason,
                )
                operations.append(operation)
                evidence.extend(observation.evidence_refs)
            patches.append(GraphPatch(
                source_graph_id=graph.id,
                target=target,
                operations=operations,
                source_refs=list(source_refs),
                permission_refs=list(permission_refs),
                evidence_refs=list(dict.fromkeys(evidence)),
                confidence=max(item.confidence for item in observations),
                reason=reason,
            ))
        return patches

    @staticmethod
    def _authorized_patches(patches: list[GraphPatch], obligation_contract: Any) -> list[GraphPatch]:
        write_contract = getattr(obligation_contract, "write_contract", None)
        if write_contract is None or not getattr(write_contract, "is_writable", False):
            return []
        allowed_targets = set(getattr(write_contract, "allowed_patch_targets", []) or [])
        if not allowed_targets or getattr(write_contract, "commit_policy", "validate_only") in {"no_commit", "require_confirmation"}:
            return []
        contract_features = dict(getattr(write_contract, "features", {}) or {})
        authorized: list[GraphPatch] = []
        required_target_ids: list[str] = []
        for patch in patches:
            if getattr(patch, "target", "") not in allowed_targets:
                continue
            kept_operations: list[PatchOperation] = []
            for operation in getattr(patch, "operations", []) or []:
                fields = operation.fields or {}
                proposition_mode = str(
                    fields.get("proposition_mode", "")
                    or (fields.get("features", {}) or {}).get("proposition_mode", "asserted")
                    or "asserted"
                )
                if proposition_mode == "queried" or fields.get("open_roles") or (fields.get("features", {}) or {}).get("open_roles"):
                    continue
                if fields.get("relation_key") == "has_property":
                    features = dict(fields.get("features", {}) or {})
                    for key in ("dimension", "property_dimension", "relation_scope", "cardinality", "update_policy"):
                        if contract_features.get(key) and not features.get(key):
                            features[key] = contract_features[key]
                    fields["features"] = features
                    if contract_features.get("dimension") and not fields.get("dimension"):
                        fields["dimension"] = contract_features["dimension"]
                    if contract_features.get("cardinality") and not fields.get("cardinality"):
                        fields["cardinality"] = contract_features["cardinality"]
                if operation.operation == "upsert_relation_candidate":
                    fields["required_by_write_contract"] = True
                    required_target_ids.append(operation.target_id)
                kept_operations.append(operation)
            if kept_operations:
                patch.operations = kept_operations
                setattr(patch, "required_operation_target_ids", list(dict.fromkeys(required_target_ids)))
                authorized.append(patch)
        setattr(obligation_contract, "required_write_target_ids", list(dict.fromkeys(required_target_ids)))
        return authorized

    @staticmethod
    def _should_retain_exemplar(graph: UOLGraph) -> bool:
        return bool(graph.candidate_sets or graph.affordance_predictions or graph.construction_matches)
