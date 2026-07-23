#!/usr/bin/env python3
"""Apply the CEMM v3.5.1 Phase 17-18 patch to the exact reviewed Phase 15-16 baseline.

Fail-closed properties:
- exact baseline commit guard;
- dirty target-file refusal by default;
- all transformations computed/preflighted before writes;
- rollback on write failure;
- new-file collision protection;
- --check performs a no-write applicability check.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

BASELINE_COMMIT = "aefe8b2530d960804417acbbf47e9c0ca3723389"
BUNDLE_ROOT = Path(r"C:\Users\Son\Downloads\CEMM_v351_Phases17_18_Final")
FILES_ROOT = BUNDLE_ROOT / "files"

TARGET_PATCH_FILES = (
    "cemm/v350/runtime_abi.py",
    "cemm/v350/runtime_v351.py",
    "cemm/v350/orchestration.py",
    "cemm/v350/composition/phase12_v351.py",
    "cemm/v350/learning/engine_v351.py",
    "cemm/v350/grounding/candidates.py",
    "cemm/v350/dynamics/compiler_v351.py",
    "cemm/v350/cutover.py",
    "cemm/v350/service_loader.py",
    "cemm/data/v350/runtime_authority_manifest.json",
    "ARCHITECTURE.md", "CEMM_CORE_MATHS.md", "CORE_LOOP.md", "RUNTIME_PLAN.md",
    "CORE_ISSUES.md", "ISSUES_TO_AVOID.md",
)


def run(root: Path, *args: str) -> str:
    return subprocess.check_output(args, cwd=root, text=True, stderr=subprocess.STDOUT).strip()


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one anchor, found {count}")
    return text.replace(old, new, 1)


def regex_once(text: str, pattern: str, replacement: str, label: str) -> str:
    result, count = re.subn(pattern, replacement, text, count=1, flags=re.S | re.M)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one regex anchor, found {count}")
    return result


def patch_runtime_abi(text: str) -> str:
    text = replace_once(
        text,
        "    response_requested: bool = True\n\n    def __post_init__(self) -> None:\n",
        "    response_requested: bool = True\n    observations: tuple[Any, ...] = ()\n\n    def __post_init__(self) -> None:\n",
        "RuntimeInput observations field",
    )
    text = replace_once(
        text,
        "        if len(self.participant_evidence_refs) != len(set(self.participant_evidence_refs)):\n            raise ValueError(\"participant evidence refs must be unique\")\n",
        "        if len(self.participant_evidence_refs) != len(set(self.participant_evidence_refs)):\n            raise ValueError(\"participant evidence refs must be unique\")\n"
        "        observation_refs = tuple(str(getattr(item, \"observation_ref\", \"\") or \"\") for item in self.observations)\n"
        "        if any(not ref for ref in observation_refs) or len(observation_refs) != len(set(observation_refs)):\n"
        "            raise ValueError(\"typed observations require unique stable observation_ref values\")\n",
        "RuntimeInput observations validation",
    )
    return text


RUNTIME_IMPORTS = '''from .observation import CanonicalOperationOutcomeAssimilatorV351, canonical_observation_adapters_v351
from .observation.runtime_bridge_v351 import (
    stage_01_observe_multimodal_evidence_v351,
    stage_02_encode_form_and_sensor_evidence_v351,
    stage_03_activate_and_ground_referents_v351,
)
from .finalization.runtime_v351 import CanonicalCycleFinalizerV351
from .runtime_support_v351 import SystemUTCClockV351
'''

STAGE17_DELEGATES = '''    def stage_01_observe_multimodal_evidence(self, cycle, capability):
        return stage_01_observe_multimodal_evidence_v351(self, cycle, capability)

    def stage_02_encode_form_and_sensor_evidence(self, cycle, capability):
        return stage_02_encode_form_and_sensor_evidence_v351(self, cycle, capability)

    def stage_03_activate_and_ground_referents(self, cycle, capability):
        return stage_03_activate_and_ground_referents_v351(self, cycle, capability)

'''


def patch_runtime(text: str) -> str:
    text = replace_once(text, "from .csir.model import CSIRCandidate, CSIRCandidateFragment, CSIRGraph\n", "from .csir.model import CSIRCandidate, CSIRCandidateFragment, CSIRGraph\n" + RUNTIME_IMPORTS, "runtime observation/finalization imports")
    text = replace_once(
        text,
        "        self._reviewed_phase13_dynamics = compile_reviewed_phase13_parameter_artifacts()\n",
        "        self._reviewed_phase13_dynamics = compile_reviewed_phase13_parameter_artifacts()\n"
        "        if self.services.clock is None:\n"
        "            self.services.clock = SystemUTCClockV351()\n"
        "        self._canonical_observation_adapters = canonical_observation_adapters_v351()\n",
        "canonical observation adapters init",
    )
    text = replace_once(
        text,
        '            "response_csir_builder": Phase16ResponseCSIRBuilderV351(\n',
        '            "operation_outcome_assimilator": CanonicalOperationOutcomeAssimilatorV351(),\n'
        '            "response_csir_builder": Phase16ResponseCSIRBuilderV351(\n',
        "canonical operation outcome service",
    )
    text = replace_once(
        text,
        '            "output_discourse_engine": OutputDiscourseCommitterV351(self.session_memory),\n',
        '            "output_discourse_engine": OutputDiscourseCommitterV351(self.session_memory),\n'
        '            "consolidation_engine": CanonicalCycleFinalizerV351(),\n',
        "canonical finalizer service",
    )
    text = replace_once(
        text,
        "    def stage_01_observe_multimodal_evidence(self, cycle, capability):\n",
        "    def _inactive_pre_phase17_stage_01_observe_multimodal_evidence(self, cycle, capability):\n",
        "quarantine pre-Phase17 Stage1",
    )
    text = replace_once(
        text,
        "    def stage_02_encode_form_and_sensor_evidence(self, cycle, capability):\n",
        "    def _inactive_pre_phase17_stage_02_encode_form_and_sensor_evidence(self, cycle, capability):\n",
        "quarantine pre-Phase17 Stage2",
    )
    text = replace_once(
        text,
        "    def stage_03_activate_and_ground_referents(self, cycle, capability):\n",
        "    def _inactive_pre_phase17_stage_03_activate_and_ground_referents(self, cycle, capability):\n",
        "quarantine pre-Phase17 Stage3",
    )
    text = replace_once(
        text,
        "    def stage_04_project_entitled_state_spaces(self, cycle, capability):\n",
        STAGE17_DELEGATES + "    def stage_04_project_entitled_state_spaces(self, cycle, capability):\n",
        "install Phase17 Stage1-3 delegates",
    )
    text = replace_once(
        text,
        "        combined_frontiers = tuple((*proposal_frontiers, *compiled.frontiers))\n",
        "        # Exact observation-model projections may contribute already-typed CSIR fragments.\n"
        "        # They join the same Stage-5 compiler barrier; they never bypass closure/authority validation.\n"
        "        for analysis in tuple(cycle.artifacts.get(\"_structured_observation_analyses\", ()) or ()):\n"
        "            fragments = tuple(getattr(analysis, \"semantic_fragments\", ()) or ())\n"
        "            if fragments and not tuple(getattr(analysis, \"semantic_projection_pins\", ()) or ()):\n"
        "                raise ValueError(\"semantic observation fragments require exact ObservationModel projection pins\")\n"
        "            proposed.extend(fragments)\n"
        "        if proposed and tuple(cycle.artifacts.get(\"_structured_observation_analyses\", ()) or ()):\n"
        "            compiled = self.exact_csir_compiler.compile_fragments(\n"
        "                proposed, authority_generation=capability.authority_generation,\n"
        "                authority_fingerprint=capability.authority_fingerprint,\n"
        "                semantic_authority_snapshot=cycle.artifacts[\"semantic_authority_snapshot_v351\"],\n"
        "                context_ref=cycle.context_ref, permission_ref=cycle.permission_ref,\n"
        "                require_projection_authority=True,\n"
        "            )\n"
        "        combined_frontiers = tuple((*proposal_frontiers, *compiled.frontiers))\n",
        "Stage5 observation fragments",
    )
    text = replace_once(text, "        service = self.services.operation_engine\n", "        service = self._resolved_service(\"operation_engine\")\n", "Stage16 canonical service resolver")
    text = regex_once(
        text,
        r"    def stage_22_consolidate_invalidate_replay_and_finalize\(self, c, cap\):.*?(?=\n\nclass Runtime:)",
        '''    def stage_22_consolidate_invalidate_replay_and_finalize(self, c, cap):\n        service = self._resolved_service("consolidation_engine")\n        if service is None:\n            return self._gap(cap.stage, "consolidation_engine")\n        return self._service(c, cap, "consolidation_engine", "finalize")\n''',
        "Stage22 canonical finalizer",
    )
    text = replace_once(
        text,
        "                 response_requested: bool = True) -> RuntimeResult:\n",
        "                 response_requested: bool = True, observations: tuple[Any, ...] = ()) -> RuntimeResult:\n",
        "run_text observations signature",
    )
    text = replace_once(
        text,
        "            response_requested=bool(response_requested),\n        )\n",
        "            response_requested=bool(response_requested), observations=tuple(observations),\n        )\n",
        "run_text observations envelope",
    )
    return text


def patch_orchestration(text: str) -> str:
    anchor = '''                request = outcome.reentry_request\n                cycle.reentry_count += 1\n                if cycle.reentry_count > int(request.max_reentries):\n'''
    replacement = '''                request = outcome.reentry_request\n                from .observation.operation_outcome_v351 import SemanticReentryRequestV351\n                if not isinstance(request, SemanticReentryRequestV351):\n                    raise CanonicalOrchestrationError("Stage 17 re-entry requires SemanticReentryRequestV351")\n                if (request.authority_generation, request.authority_fingerprint) != (\n                    capability.authority_generation, capability.authority_fingerprint\n                ):\n                    raise CanonicalOrchestrationError("semantic re-entry cannot cross AuthorityGeneration")\n                guard = cycle.artifacts.get("_operation_reentry_guard")\n                if guard != request.guard:\n                    raise CanonicalOrchestrationError("semantic re-entry request guard differs from Stage-17 artifact")\n                cycle.reentry_count += 1\n                if cycle.reentry_count > int(request.max_reentries):\n'''
    return replace_once(text, anchor, replacement, "typed operation reentry validation")


def patch_grounding_candidates(text: str) -> str:
    text = replace_once(text, "from typing import Iterable\n", "from typing import Any, Iterable\n", "grounding Any import")
    text = replace_once(text, "from ..uol.model import Referent\n", "", "remove active UOL Referent import")
    text = text.replace("referent: Referent", "referent: Any")
    text = text.replace("by_ref: dict[str, Referent]", "by_ref: dict[str, Any]")
    text = replace_once(
        text,
        "        if track.context_ref not in {\"global\", mention.context_ref}:\n            return None\n",
        "        if track.context_ref not in {\"global\", mention.context_ref}:\n            return None\n"
        "        source_track_ref = str(mention.metadata.get(\"source_track_ref\", \"\") or \"\")\n"
        "        if source_track_ref and source_track_ref != track.track_ref:\n"
        "            return None\n",
        "originating multimodal track guard",
    )
    return text


NEW_MULTIMODAL_METHOD = '''    @staticmethod\n    def _add_multimodal_edges(candidate, class_node, nodes, add_node, add_edge, evidence_lattice):\n        if evidence_lattice is None:\n            return\n        predicate_keys = {app.predicate_pin.key for app in candidate.graph.applications}\n        identities = {term.identity_ref for term in candidate.graph.terms if term.identity_ref}\n        for item in tuple(getattr(evidence_lattice, "structured_observations", ()) or ()):\n            source_ref = str(getattr(item, "analysis_ref", None) or getattr(item, "track_ref", None) or getattr(item, "observation_ref", None) or repr(item))\n            node_ref = "activation-node:multimodal:" + semantic_fingerprint("activation-multimodal-v351", source_ref, 24)\n            evidence = tuple(getattr(item, "evidence_refs", ()) or ())\n            lineage = tuple(getattr(item, "lineage_refs", ()) or evidence or (source_ref,))\n            if node_ref not in nodes:\n                add_node(SemanticActivationNode(\n                    node_ref=node_ref, node_kind=ActivationNodeKind.MULTIMODAL_TRACK,\n                    semantic_class_ref="multimodal-evidence:not-semantic-identity",\n                    source_ref=source_ref, initial_activation=1.0, current_activation=1.0,\n                    evidence_refs=evidence, lineage_refs=lineage,\n                ))\n            target_refs = set(tuple(getattr(item, "target_refs", ()) or ()))\n            direct_match = tuple(sorted(target_refs.intersection(identities)))\n            projection_pins = tuple(getattr(item, "semantic_projection_pins", ()) or ())\n            semantic_pins = tuple(pin for pin in projection_pins if pin.key in predicate_keys)\n            if not direct_match and not semantic_pins:\n                continue\n            features = tuple(getattr(item, "features", ()) or ())\n            clusters = {}\n            for feature in features:\n                key = str(getattr(feature, "dependence_ref", "") or getattr(feature, "feature_ref", "") or source_ref)\n                clusters.setdefault(key, []).append(feature)\n            if not clusters:\n                clusters = {"lineage:" + "|".join(sorted(lineage)): ()}\n            for dependence_ref in sorted(clusters):\n                values = tuple(clusters[dependence_ref])\n                confidences = tuple(float(getattr(feature, "confidence", 1.0)) for feature in values)\n                # One contribution per dependence class. Correlated transforms cannot multiply support.\n                strength = min(confidences) if confidences else 1.0\n                cluster_evidence = tuple(sorted(set((*evidence, *(ref for feature in values for ref in tuple(getattr(feature, "evidence_refs", ()) or ()))))))\n                add_edge(\n                    MessageFamily.MULTIMODAL, node_ref, class_node, strength=strength,\n                    evidence_refs=cluster_evidence, authority_pins=semantic_pins,\n                    feature_refs=tuple(sorted(set((dependence_ref, *direct_match, *(pin.ref for pin in semantic_pins))))),\n                )\n'''


def patch_dynamics_compiler(text: str) -> str:
    return regex_once(
        text,
        r"    @staticmethod\n    def _add_multimodal_edges\(candidate, class_node, nodes, add_node, add_edge, evidence_lattice\):.*?(?=\n\n__all__ =)",
        NEW_MULTIMODAL_METHOD,
        "dependence-aware multimodal recurrent bridge",
    )


def patch_cutover(text: str) -> str:
    text = replace_once(
        text,
        '        "cemm.v350.runtime_hardening", "cemm.v350.runtime_services",\n        "cemm.v350.composition",\n',
        '        "cemm.v350.runtime_hardening", "cemm.v350.runtime_services",\n        "cemm.v350.activation_services", "cemm.v350.uol",\n',
        "cutover forbidden canonical composition correction",
    )
    text = text.replace(', "cemm.v350.composition",\n', ',\n')
    text = replace_once(
        text,
        "    runtime_service_bindings: tuple[Mapping[str, Any], ...] = ()\n",
        "    runtime_service_bindings: tuple[Mapping[str, Any], ...] = ()\n"
        "    canonical_service_authorities: tuple[Mapping[str, Any], ...] = ()\n"
        "    runtime_source_root_sha256: str = \"\"\n"
        "    closure_ledger_sha256: str = \"\"\n"
        "    detached_signature: Mapping[str, Any] = field(default_factory=dict)\n",
        "manifest v5 authority fields",
    )
    text = replace_once(
        text,
        "            runtime_service_bindings=tuple(\n                dict(item) for item in doc.get(\"runtime_service_bindings\", ())\n                if isinstance(item, Mapping)\n            ),\n",
        "            runtime_service_bindings=tuple(\n                dict(item) for item in doc.get(\"runtime_service_bindings\", ())\n                if isinstance(item, Mapping)\n            ),\n"
        "            canonical_service_authorities=tuple(\n                dict(item) for item in doc.get(\"canonical_service_authorities\", ())\n                if isinstance(item, Mapping)\n            ),\n"
        "            runtime_source_root_sha256=str(doc.get(\"runtime_source_root_sha256\", \"\")),\n"
        "            closure_ledger_sha256=str(doc.get(\"closure_ledger_sha256\", \"\")),\n"
        "            detached_signature=dict(doc.get(\"detached_signature\", {}) or {}),\n",
        "manifest v5 loader fields",
    )
    text = replace_once(text, "        if m.manifest_version < 3:\n            raise RuntimeAuthorityError(\"runtime authority manifest v3 is required for v3.5.1\")\n", "        if m.manifest_version < 5:\n            raise RuntimeAuthorityError(\"runtime authority manifest v5 is required for final v3.5.1 cutover\")\n", "manifest v5 cutover requirement")
    text = replace_once(
        text,
        "        if set(m.allowed_record_kinds) != {item.value for item in RecordKind}:\n            errors.append(\"manifest record-kind authority differs from v3.5.1 storage contract\")\n",
        "        runtime_safe_record_kinds = {item.value for item in RecordKind if not item.value.startswith(\"migration_\")} - {\"response_uol\"}\n"
        "        if set(m.allowed_record_kinds) != runtime_safe_record_kinds:\n"
        "            errors.append(\"manifest runtime record-kind authority is not the exact legacy-free v3.5.1 set\")\n",
        "runtime-safe record families",
    )
    text = replace_once(
        text,
        "        service_kinds = {\n            str(item.get(\"service_kind\", \"\"))\n            for item in m.runtime_service_bindings\n        }\n",
        "        service_kinds = {str(item.get(\"service_kind\", \"\")) for item in m.runtime_service_bindings}\n"
        "        canonical_service_kinds = {str(item.get(\"service_kind\", \"\")) for item in m.canonical_service_authorities}\n"
        "        service_kinds.update(canonical_service_kinds)\n",
        "canonical plus injected service slots",
    )
    insertion = '''        if m.activation_ready:\n            if not m.closure_ledger_sha256 or not re.fullmatch(r"[0-9a-f]{64}", m.closure_ledger_sha256):\n                errors.append("activation-ready manifest lacks exact Phase-18 closure ledger")\n            signature_sha = str(m.detached_signature.get("sha256", ""))\n            if not re.fullmatch(r"[0-9a-f]{64}", signature_sha) or not m.detached_signature.get("signer_identity"):\n                errors.append("activation-ready manifest lacks exact detached signature authority")\n        for item in m.canonical_service_authorities:\n            class_path = str(item.get("class_path", ""))\n            module_name, sep, symbol = class_path.partition(":")\n            if not sep or not module_name or not symbol:\n                errors.append(f"invalid canonical service class path:{class_path}")\n                continue\n            if any(module_name == prefix or module_name.startswith(prefix + ".") for prefix in self.REQUIRED_FORBIDDEN_PREFIXES):\n                errors.append(f"canonical service points into forbidden namespace:{class_path}")\n                continue\n            try:\n                module = importlib.import_module(module_name)\n                cls = getattr(module, symbol)\n                for method in tuple(item.get("required_methods", ()) or ()):\n                    if not callable(getattr(cls, str(method), None)):\n                        errors.append(f"canonical service lacks required method:{class_path}:{method}")\n                runtime_abi = str(getattr(cls, "RUNTIME_ABI", "v351"))\n                if runtime_abi != "v351" or str(item.get("runtime_abi", "")) != "v351":\n                    errors.append(f"canonical service lacks final v351 ABI:{class_path}")\n                declared_kind = str(getattr(cls, "SERVICE_KIND", item.get("service_kind", "")))\n                if declared_kind != str(item.get("implementation_service_kind", declared_kind)):\n                    errors.append(f"canonical service implementation kind mismatch:{class_path}")\n                source_path = inspect.getsourcefile(cls)\n                if not source_path or not Path(source_path).is_file() or _sha256(Path(source_path)) != str(item.get("source_sha256", "")):\n                    errors.append(f"canonical service source fingerprint mismatch:{class_path}")\n            except Exception as exc:\n                errors.append(f"canonical service authority cannot resolve:{class_path}:{exc}")\n'''
    text = replace_once(text, "        forbidden_service_prefixes = (\n", insertion + "        forbidden_service_prefixes = (\n", "canonical service authority validation")
    text = replace_once(
        text,
        "            if not denylist.is_file() or _sha256(denylist) != m.legacy_denylist_sha256:\n                errors.append(\"legacy denylist fingerprint mismatch\")\n",
        "            if not denylist.is_file() or _sha256(denylist) != m.legacy_denylist_sha256:\n                errors.append(\"legacy denylist fingerprint mismatch\")\n"
        "            try:\n"
        "                from .finalization.source_attestation_v351 import runtime_source_root_v351\n"
        "                observed_root, _inventory = runtime_source_root_v351(self.repo_root)\n"
        "                if not m.runtime_source_root_sha256 or observed_root != m.runtime_source_root_sha256:\n"
        "                    errors.append(\"runtime source-tree root fingerprint mismatch\")\n"
        "            except Exception as exc:\n"
        "                errors.append(f\"cannot attest runtime source-tree root:{exc}\")\n",
        "runtime source-tree root validation",
    )
    return text


def patch_service_loader(text: str) -> str:
    return replace_once(text, '    "cemm.v350.uol",\n    "cemm.v350.composition",\n', '    "cemm.v350.uol",\n', "allow canonical composition in service loader")


def patch_manifest(text: str) -> str:
    doc = json.loads(text)
    doc["activation_ready"] = False
    doc["allowed_record_kinds"] = [
        item for item in doc.get("allowed_record_kinds", ())
        if not str(item).startswith("migration_") and str(item) != "response_uol"
    ]
    doc["forbidden_runtime_import_prefixes"] = [
        item for item in doc.get("forbidden_runtime_import_prefixes", ())
        if str(item) != "cemm.v350.composition"
    ]
    metadata = dict(doc.get("metadata", {}) or {})
    metadata.update({
        "phase17_18_status": "preactivation",
        "reason": "final Phase-18 closure/signature artifacts must be regenerated from exact patched checkout",
    })
    doc["metadata"] = metadata
    return json.dumps(doc, indent=2, sort_keys=True) + "\n"


DOC_APPEND = {
    "ARCHITECTURE.md": """\n\n## Phase 17–18 final activation clarification\n\nMultimodal observation models are exact authority artifacts. Provider labels are evidence, not ontology. All modalities enter the same grounding → CSIR → recurrent semantic dynamics path; there is no second multimodal brain. Final activation additionally requires a content-addressed runtime source-tree root, exact canonical service-method inventory, legacy-free runtime record families, complete Phase-18 closure evidence, and detached release signature.\n""",
    "CEMM_CORE_MATHS.md": """\n\n## Final v3.5.1 mathematical clarifications\n\nThis document is the canonical mathematical contract for v3.5.1. Inactive hard-masked semantic states are bottom/ineligible states, not ordinary zero-evidence states. Posterior/support aggregation is over evidence-dependence quotient classes rather than derivation count. Without an exact joint model, correlated transforms cannot multiply support. Multimodal fusion is conditioned on candidate identity hypotheses. Interventions use do-semantics rather than conditioning; feedback requires explicit equilibrium authority or time-unrolling. Operation results re-enter as observations under the same AuthorityGeneration with a bounded two-hop recurrence budget. Oscillation or budget exhaustion is typed partial cognition, never convergence.\n""",
    "CORE_LOOP.md": """\n\n## Phase 17–18 final loop clarification\n\nStage 1 accepts typed observations as well as text. Stage 2 applies only reviewed, exact ObservationModel/calibration authority. Stage 3 supports nonlexical multimodal-only grounding without fabricating a text lattice. Stage 17 may request only typed, same-authority, bounded operation-result semantic re-entry while preserving participant/session identity. Stage 22 owns explicit invalidation/replay/consolidation/final status.\n""",
    "RUNTIME_PLAN.md": """\n\n## Phase 17–18 final runtime closure\n\nFinal runtime authority uses manifest v5 with exact Stage 0–22 adapters, canonical service slot + implementation method/source attestations, runtime source-tree Merkle-style root, boot-derived exact pins, legacy-free runtime record families, closure-ledger hash and detached signature metadata. Checked-in manifests remain preactivation until every closure gate passes against the same commit, boot hash, source root and authority payload hash.\n""",
    "CORE_ISSUES.md": """\n\n## Phase 17–18 closure defects\n\n- FIXED BY PHASE17_18 PATCH: multimodal-only Stage-3 hidden text dependency.\n- FIXED: canonical composition namespace incorrectly forbidden by cutover/service-loader policy.\n- FIXED: Stage-16 direct injected-only operation service lookup.\n- FIXED: missing canonical Stage-17 operation-result assimilation and bounded recurrence.\n- FIXED: recurrence participant/session identity loss.\n- FIXED: observation provider labels/direct referent bindings could bypass exact model/binding authority.\n- FIXED: correlated multimodal transforms could overcount support.\n- FIXED: final authority conflated runtime slot identity with implementation SERVICE_KIND.\n- FIXED: activation evidence could be mixed across different release roots.\n- OPEN UNTIL EXECUTED: full corpus, learning→promotion→restart, causal replay, multimodal, cross-language, active acquisition, concurrency/performance, deterministic rebuild and detached-signature gates.\n""",
    "ISSUES_TO_AVOID.md": """\n\n## Phase 17–18 anti-regressions\n\nDo not infer ontology from detector labels, ASR tokens, telemetry keys or sensor field names. Do not count correlated transforms as independent evidence. Do not create a separate multimodal grounding/semantic brain. Do not let operation recurrence cross AuthorityGeneration, exceed its bounded budget, replay anonymous participant identity, or mutate world state outside normal commit stages. Do not call a release active because a manifest boolean says so: closure evidence, source roots, boot roots and signature authority must all bind to the same payload.\n""",
}


def append_doc(text: str, addition: str) -> str:
    marker = addition.strip().splitlines()[0]
    if marker in text:
        raise RuntimeError(f"documentation patch marker already present:{marker}")
    return text.rstrip() + addition + "\n"


def transform(rel: str, text: str) -> str:
    if rel == "cemm/v350/runtime_abi.py": return patch_runtime_abi(text)
    if rel == "cemm/v350/runtime_v351.py": return patch_runtime(text)
    if rel == "cemm/v350/orchestration.py": return patch_orchestration(text)
    if rel == "cemm/v350/composition/phase12_v351.py":
        text = replace_once(text, 'RUNTIME_ABI = "v351-phase12"', 'RUNTIME_ABI = "v351"', "composer final ABI")
        return replace_once(text, 'SERVICE_KIND = "projection_aware_deterministic_csir_composer"', 'SERVICE_KIND = "csir_compiler"', "composer service slot")
    if rel == "cemm/v350/learning/engine_v351.py":
        text = replace_once(text, 'RUNTIME_ABI = "v351-phase14"', 'RUNTIME_ABI = "v351"', "learning final ABI")
        return replace_once(text, 'SERVICE_KIND = "prediction_error_learning_engine_v351"', 'SERVICE_KIND = "learning_engine"', "learning service slot")
    if rel == "cemm/v350/grounding/candidates.py": return patch_grounding_candidates(text)
    if rel == "cemm/v350/dynamics/compiler_v351.py": return patch_dynamics_compiler(text)
    if rel == "cemm/v350/cutover.py": return patch_cutover(text)
    if rel == "cemm/v350/service_loader.py": return patch_service_loader(text)
    if rel == "cemm/data/v350/runtime_authority_manifest.json": return patch_manifest(text)
    if rel == "CEMM_CORE_MATHS.md":
        text = replace_once(
            text,
            "**Status:** proposed canonical mathematical contract",
            "**Status:** canonical mathematical contract",
            "core maths canonical status",
        )
        return append_doc(text, DOC_APPEND[rel])
    if rel in DOC_APPEND: return append_doc(text, DOC_APPEND[rel])
    raise KeyError(rel)


def collect_new_files():
    return tuple(path for path in FILES_ROOT.rglob("*") if path.is_file())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", type=Path)
    parser.add_argument("--check", action="store_true", help="validate applicability without writing")
    parser.add_argument("--allow-dirty", action="store_true", help="allow dirty target files (not recommended)")
    args = parser.parse_args()
    root = args.repo.resolve()
    if not (root / ".git").exists():
        raise SystemExit(f"not a git checkout:{root}")
    head = run(root, "git", "rev-parse", "HEAD")
    if head != BASELINE_COMMIT:
        raise SystemExit(f"baseline mismatch: expected {BASELINE_COMMIT}, observed {head}")
    if not args.allow_dirty:
        dirty = run(root, "git", "status", "--porcelain", "--", *TARGET_PATCH_FILES)
        if dirty:
            raise SystemExit("target files are dirty; refusing non-reviewable patch:\n" + dirty)

    planned: dict[Path, bytes] = {}
    originals: dict[Path, bytes | None] = {}
    for rel in TARGET_PATCH_FILES:
        path = root / rel
        if not path.is_file():
            raise SystemExit(f"required baseline file missing:{rel}")
        original = path.read_text(encoding="utf-8")
        transformed = transform(rel, original)
        if transformed == original:
            raise SystemExit(f"transformation produced no change:{rel}")
        planned[path] = transformed.encode("utf-8")
        originals[path] = path.read_bytes()

    for source in collect_new_files():
        rel = source.relative_to(FILES_ROOT)
        target = root / rel
        payload = source.read_bytes()
        if target.exists():
            if target.read_bytes() != payload:
                raise SystemExit(f"new-file collision with different content:{rel}")
            continue
        planned[target] = payload
        originals[target] = None

    if args.check:
        print(json.dumps({
            "status": "applicable", "baseline_commit": head,
            "changed_or_added_files": len(planned),
        }, indent=2))
        return 0

    temp_root = Path(tempfile.mkdtemp(prefix="cemm-phase17-18-", dir=str(root)))
    committed = []
    try:
        for target, payload in planned.items():
            rel = target.relative_to(root)
            staged = temp_root / rel
            staged.parent.mkdir(parents=True, exist_ok=True)
            staged.write_bytes(payload)
        for target in sorted(planned, key=lambda path: path.relative_to(root).as_posix()):
            rel = target.relative_to(root)
            staged = temp_root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            os.replace(staged, target)
            committed.append(target)
    except Exception:
        for target in reversed(committed):
            original = originals[target]
            if original is None:
                target.unlink(missing_ok=True)
            else:
                target.write_bytes(original)
        raise
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)

    print(json.dumps({
        "status": "applied", "baseline_commit": head,
        "changed_or_added_files": len(planned),
        "next": [
            "python -m compileall -q cemm tools tests",
            "python tools/verify_v351_phases17_18.py --run-tests --report cemm/data/v350/release/phase17_18_structural_verification.json",
            "pytest -q",
        ],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
