#!/usr/bin/env python3
"""Apply CEMM v3.5.1 Phases 13-14 against the exact post-Phase-12 baseline.

The script is intentionally fail-closed: every source edit is anchored to the reviewed
baseline text and aborts on drift unless --allow-drift is explicitly supplied.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

BASELINE = "0dc1d64b78d0f1b620b224bdb74265e8b85763c6"
PAYLOAD_ROOT = Path(__file__).resolve().parent

COPY_DIRS = ("cemm", "tests", "docs", "tools")
COPY_FILES = ("PHASES13_14_IMPLEMENTATION_REPORT.md",)


def git_head(repo: Path) -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    except Exception as exc:
        raise SystemExit(f"cannot resolve repository HEAD: {exc}")


def replace_once(path: Path, old: str, new: str, *, allow_drift: bool) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        if allow_drift and new in text:
            return
        raise SystemExit(f"patch anchor mismatch in {path}: expected exactly 1 occurrence, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def replace_span(path: Path, start_marker: str, end_marker: str, new: str, *, allow_drift: bool) -> None:
    text = path.read_text(encoding="utf-8")
    start = text.find(start_marker)
    end = text.find(end_marker, start + len(start_marker)) if start >= 0 else -1
    if start < 0 or end < 0:
        if allow_drift and new.strip() in text:
            return
        raise SystemExit(f"patch span anchor mismatch in {path}")
    end += len(end_marker)
    path.write_text(text[:start] + new + text[end:], encoding="utf-8")


def append_once(path: Path, marker: str, text: str) -> None:
    current = path.read_text(encoding="utf-8")
    if marker in current:
        return
    path.write_text(current.rstrip() + "\n\n" + text.rstrip() + "\n", encoding="utf-8")


def copy_payload(repo: Path) -> None:
    for dirname in COPY_DIRS:
        source = PAYLOAD_ROOT / dirname
        if not source.exists():
            continue
        for item in source.rglob("*"):
            if not item.is_file() or "__pycache__" in item.parts or item.suffix == ".pyc":
                continue
            target = repo / item.relative_to(PAYLOAD_ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)
    for filename in COPY_FILES:
        source = PAYLOAD_ROOT / filename
        if source.exists():
            shutil.copy2(source, repo / filename)


def patch_runtime(repo: Path, *, allow_drift: bool) -> None:
    path = repo / "cemm/v350/runtime_v351.py"
    replace_once(path,
        "from dataclasses import dataclass, field",
        "from dataclasses import dataclass, field, replace",
        allow_drift=allow_drift,
    )
    replace_once(path,
'''from .composition import (
    DeterministicAttractorStabilizer, DeterministicMeaningDynamics,
    ProjectionAwareDeterministicCSIRComposer,
)''',
'''from .composition import ProjectionAwareDeterministicCSIRComposer
from .dynamics import (
    RecurrentAttractorStabilizerV351, RecurrentSemanticDynamicsV351,
    compile_reviewed_phase13_parameter_artifacts,
)''', allow_drift=allow_drift)
    replace_once(path,
        "from .learning.model import PinnedRecord",
'''from .learning.model import PinnedRecord
from .learning.engine_v351 import Phase14LearningEngineV351
from .learning.commit_v351 import Stage13LearningCommitterV351
from .learning.maintenance_v351 import Phase14LearningMaintenanceV351''',
        allow_drift=allow_drift,
    )
    replace_once(path,
'''    learning_maintenance: Any | None = None
    system_ref: str = "referent:self"''',
'''    learning_maintenance: Any | None = None
    learning_competence_executors: Mapping[str, Any] = field(default_factory=dict)
    system_ref: str = "referent:self"''', allow_drift=allow_drift)
    replace_once(path,
'''        self._minimum_response_authority = compile_minimum_response_authority()
        self._minimum_english_realization = compile_minimum_english_realization_package()''',
'''        self._minimum_response_authority = compile_minimum_response_authority()
        self._minimum_english_realization = compile_minimum_english_realization_package()
        self._reviewed_phase13_dynamics = compile_reviewed_phase13_parameter_artifacts()
        if self.services.learning_maintenance is None:
            self.services.learning_maintenance = Phase14LearningMaintenanceV351(
                store,
                competence_executors=self.services.learning_competence_executors,
            )''', allow_drift=allow_drift)
    replace_once(path,
'''            "recurrent_semantic_solver": DeterministicMeaningDynamics(),
            "semantic_attractor_stabilizer": DeterministicAttractorStabilizer(),''',
'''            "recurrent_semantic_solver": RecurrentSemanticDynamicsV351(),
            "semantic_attractor_stabilizer": RecurrentAttractorStabilizerV351(),''', allow_drift=allow_drift)
    replace_once(path,
'''            "query_engine": GroundedQueryEngineV351(self.session_memory),
            "commit_coordinator": SessionMemoryCommitCoordinatorV351(self.session_memory),''',
'''            "query_engine": GroundedQueryEngineV351(self.session_memory),
            "learning_engine": Phase14LearningEngineV351(),
            "commit_coordinator": Stage13LearningCommitterV351(self.session_memory),''', allow_drift=allow_drift)
    replace_once(path,
'''        semantic_authority = self.services.semantic_authority_snapshot or AuthoritySnapshotV351(
            generation=authority.generation,
            authority_fingerprint=authority.authority_fingerprint,
        )
        if (semantic_authority.generation, semantic_authority.authority_fingerprint) != (''',
'''        semantic_authority = self.services.semantic_authority_snapshot or AuthoritySnapshotV351(
            generation=authority.generation,
            authority_fingerprint=authority.authority_fingerprint,
        )
        # Phase 13 requires an explicit immutable Θ inventory.  The reviewed canonical
        # baseline is pinned only when the supplied semantic snapshot has no dynamics
        # artifacts at all; a partial/custom inventory is never silently completed.
        if not semantic_authority.dynamics_parameters:
            semantic_authority = replace(
                semantic_authority,
                dynamics_parameters=tuple(self._reviewed_phase13_dynamics),
            )
        if (semantic_authority.generation, semantic_authority.authority_fingerprint) != (''', allow_drift=allow_drift)
    replace_once(path,
'''            dynamics_parameters=cycle.artifacts["semantic_authority_snapshot_v351"].dynamics_parameters,
            read_generation=cycle.artifacts["read_generation"],
            budgets=cycle.artifacts["runtime_budgets"],
        )''',
'''            dynamics_parameters=cycle.artifacts["semantic_authority_snapshot_v351"].dynamics_parameters,
            read_generation=cycle.artifacts["read_generation"],
            budgets=cycle.artifacts["runtime_budgets"],
            evidence_lattice=cycle.artifacts.get("evidence_lattice"),
            evidence_envelopes=cycle.artifacts.get("evidence_envelopes", ()),
            grounding_candidates=cycle.artifacts.get("grounding_candidates"),
            referent_projections=cycle.artifacts.get("referent_projections"),
            state_space_projections=cycle.artifacts.get("state_space_projections"),
        )''', allow_drift=allow_drift)
    replace_once(path,
'''        if cycle.artifacts.get("_maintenance_events"):
            self.maintenance_scheduler.drain()
        emission = cycle.artifacts.get("emission_observation")''',
'''        maintenance_results = ()
        if cycle.artifacts.get("_maintenance_events"):
            maintenance_results = self.maintenance_scheduler.drain()
        emission = cycle.artifacts.get("emission_observation")''', allow_drift=allow_drift)
    replace_once(path,
'''            frontier_refs=tuple(sorted(set(cycle.frontiers))), errors=tuple(cycle.errors),
            artifacts=dict(cycle.artifacts),
        )''',
'''            frontier_refs=tuple(sorted(set(cycle.frontiers))), errors=tuple(cycle.errors),
            artifacts={
                **dict(cycle.artifacts),
                "_post_cycle_maintenance_results": tuple(maintenance_results),
                "_runtime_restart_required": any(
                    bool(getattr(getattr(item, "details", {}).get("result"), "restart_required", False))
                    for item in maintenance_results
                ),
            },
        )''', allow_drift=allow_drift)


def patch_learning_exports(repo: Path) -> None:
    path = repo / "cemm/v350/learning/__init__.py"
    append_once(path, "Phase14LearningEngineV351", '''# Phase-14 runtime pieces are explicit opt-in exports; durable model imports remain above.
from .phase14_model_v351 import *
from .frontier_classifier_v351 import *
from .inducers_v351 import *
from .teaching_v351 import *
from .engine_v351 import Phase14LearningEngineV351
from .commit_v351 import Stage13LearningCommitterV351
from .maintenance_v351 import Phase14LearningMaintenanceV351''')


def patch_legacy_learning_safety(repo: Path, *, allow_drift: bool) -> None:
    """Harden the superseded Phase-13 advancer so no stale caller reintroduces old bugs."""
    path = repo / "cemm/v350/learning/runtime_advance.py"
    replace_once(path,
'''        if frontier_refs:
            frontiers = tuple(''',
'''        if frontier_refs is None:
            raise ValueError("runtime learning advancement requires explicit event-targeted frontier_refs")
        if frontier_refs:
            frontiers = tuple(''', allow_drift=allow_drift)
    replace_once(path,
'''        else:
            frontiers = tuple(
                item.payload
                for item in self.store.repositories.learning_frontiers.all()
                if item.payload.context_ref in {context_ref, "global"}
                and item.payload.permission_ref in {permission_ref, "public"}
                and item.payload.resolution_status.value in {"open", "partial"}
            )''',
'''        else:
            frontiers = ()''', allow_drift=allow_drift)
    replace_once(path,
'''            if not proposals:
                with self.store.snapshot() as snapshot:''',
'''            if not proposals and not self.inducers:
                deferred.append(f"learning:explicit-inducer-required:{frontier.frontier_ref}")
                continue
            if not proposals:
                with self.store.snapshot() as snapshot:''', allow_drift=allow_drift)
    # The old reconstruction path intentionally cannot recover exact dependency edges from
    # a bare `candidate_ref@revision`. Refuse to erase them: Phase 14 uses persisted package
    # pins directly and the canonical runtime no longer calls this reconstruction path.
    replace_once(path,
'''                dependency_pins=(),
                confidence=float(getattr(stored.payload, "confidence", 1.0)),''',
'''                dependency_pins=tuple(
                    pin for pin in getattr(stored.payload, "dependency_pins", ())
                    if isinstance(pin, PinnedRecord)
                ),
                confidence=float(getattr(stored.payload, "confidence", 1.0)),''', allow_drift=allow_drift)

    # Fix the old competence->PROMOTABLE revision mismatch. The superseded advancer
    # must never synthesize a fresh package revision after competence because competence
    # and evidence are exact to the tested revision. Canonical Phase-14 maintenance promotes
    # that exact package revision after review/authorization.
    replacement_method = """    def _mark_promotable_if_ready(self, package, results):
        requested = tuple(
            item.operation
            for item in package.requested_use_authorizations
            if item.decision in {UseDecision.ALLOW, UseDecision.PROVISIONAL}
        )
        if not requested:
            return None
        passed = {
            item.use_operation
            for item in results
            if item.outcome == CompetenceOutcome.PASSED
        }
        if not set(requested).issubset(passed):
            return None
        if not package.review_refs or not package.metadata.get("authorization_refs"):
            return None
        current = self.store.get_record(RecordKind.LEARNING_PACKAGE, package.package_ref)
        if current is None:
            return None
        # Never sever exact competence/evidence lineage with a synthetic PROMOTABLE
        # revision. Event-driven Phase-14 maintenance evaluates and promotes this exact
        # competence-tested package revision.
        return current.payload
"""
    replace_span(
        path,
        "    def _mark_promotable_if_ready(self, package, results):\n",
        "        return next_package if committed.committed else None",
        replacement_method.rstrip("\n"),
        allow_drift=allow_drift,
    )



def patch_phase14_promotion_graph(repo: Path, *, allow_drift: bool) -> None:
    """Make multi-record candidate promotion an exact dependency-closed graph transition."""
    path = repo / "cemm/v350/learning/promotion.py"
    replace_once(
        path,
        "from .package import LearningDependencyResolver",
        '''from .package import LearningDependencyResolver
from .promotion_rewire_v351 import (
    plan_promoted_revisions, promoted_internal_dependencies, rewire_promoted_record,
)''',
        allow_drift=allow_drift,
    )
    replacement = '''            revision_map = plan_promoted_revisions(self.store, package.candidate_pins, decision)
            planned_promotions = {}
            for pin in package.candidate_pins:
                grants = decision.grants_for(pin)
                if not grants:
                    continue
                source = self.store.get_record(pin.record_kind, pin.record_ref, pin.revision)
                if source is None or source.record_fingerprint != pin.record_fingerprint:
                    raise ValueError("candidate changed after promotion decision")
                promoted = self._promoted_revision(pin, source.payload, grants, package.permission_ref)
                if promoted is None:
                    continue
                expected_revision = revision_map.get(pin.key)
                if expected_revision is None or int(getattr(promoted, "revision", 0)) != expected_revision:
                    raise ValueError("planned promotion revision differs from canonical promoted revision")
                promoted = rewire_promoted_record(
                    promoted,
                    candidate_pins=package.candidate_pins,
                    revision_map=revision_map,
                )
                planned_promotions[pin.key] = (pin, grants, promoted)

            if set(planned_promotions) != set(revision_map):
                missing = sorted(set(revision_map).difference(planned_promotions), key=str)
                raise ValueError(
                    "positive promotion plan contains records that cannot materialize:" + repr(missing)
                )
            promoted_payloads = {key: item[2] for key, item in planned_promotions.items()}
            promoted_count = 0
            for key in sorted(planned_promotions):
                pin, grants, promoted = planned_promotions[key]
                promoted_count += 1
                deps = [
                    RecordDependency(RecordKind.PROMOTION_DECISION, decision.decision_ref, decision.revision, decision_fingerprint, "promotion_decision"),
                    RecordDependency(pin.record_kind, pin.record_ref, pin.revision, pin.record_fingerprint, "promotion_source_candidate"),
                ]
                for result_ref in sorted({ref for grant in grants for ref in grant.competence_result_refs}):
                    stored_result = self.store.get_record(RecordKind.COMPETENCE_RESULT, result_ref)
                    if stored_result is None:
                        raise ValueError(f"missing competence result during promotion: {result_ref}")
                    deps.append(RecordDependency(
                        RecordKind.COMPETENCE_RESULT, result_ref, stored_result.revision,
                        stored_result.record_fingerprint, "promotion_competence",
                    ))
                deps.extend(
                    RecordDependency(dep.record_kind, dep.record_ref, dep.revision, dep.record_fingerprint, "promotion_dependency")
                    for dep in package.dependency_pins
                )
                deps.extend(promoted_internal_dependencies(
                    record=promoted,
                    candidate_pins=package.candidate_pins,
                    revision_map=revision_map,
                    promoted_payloads=promoted_payloads,
                ))
                deduped = {}
                for dep in deps:
                    dep_key = (
                        dep.record_kind.value if dep.record_kind is not None else "",
                        dep.record_ref, dep.revision, dep.fingerprint, dep.dependency_kind,
                    )
                    deduped.setdefault(dep_key, dep)
                operations.append(self._upsert_operation(
                    pin.record_kind,
                    promoted,
                    dependencies=tuple(deduped[item] for item in sorted(deduped, key=str)),
                    expected_record_revision=self._latest_revision(pin.record_kind, pin.record_ref),
                    expected_record_fingerprint=self._latest_fingerprint(pin.record_kind, pin.record_ref),
                    reason="activate exact dependency-closed candidate graph only for competence-authorized uses",
                ))
'''
    replace_span(
        path,
        "            promoted_count = 0\n",
        '''                operations.append(self._upsert_operation(
                    pin.record_kind,
                    promoted,
                    dependencies=tuple(deps),
                    expected_record_revision=self._latest_revision(pin.record_kind, pin.record_ref),
                    expected_record_fingerprint=self._latest_fingerprint(pin.record_kind, pin.record_ref),
                    reason="activate exact candidate only for competence-authorized uses",
                ))''',
        replacement.rstrip("\n"),
        allow_drift=allow_drift,
    )


def patch_reviewed_learning_source(repo: Path, *, allow_drift: bool) -> None:
    # Publish reviewed source contract as English source revision 4 only; do not edit signed boot artifacts.
    path = repo / "cemm/v350/language/minimum_english_v351.py"
    replace_once(
        path,
        "from .model import ConstructionProgramOperation",
        "from .model import ConstructionProgramOperation\nfrom .phase14_learning_authority_v351 import DefinitionLearningContractSeedV351",
        allow_drift=allow_drift,
    )
    replace_once(
        path,
        "class ConstructionSeed:\n    construction_ref: str\n    family: CompositionFamily\n    trigger_categories: tuple[str, ...]\n    required_features: tuple[tuple[str, str], ...]\n    program: tuple[ProgramStep, ...]\n    competence_cases: tuple[str, ...]\n",
        "class ConstructionSeed:\n    construction_ref: str\n    family: CompositionFamily\n    trigger_categories: tuple[str, ...]\n    required_features: tuple[tuple[str, str], ...]\n    program: tuple[ProgramStep, ...]\n    competence_cases: tuple[str, ...]\n    learning_contract: DefinitionLearningContractSeedV351 | None = None\n",
        allow_drift=allow_drift,
    )
    replace_once(
        path,
        '        (ProgramStep(ConstructionProgramOperation.WRAP_DISCOURSE_ACT, "discourse:definition"),),\n        ("case:en:definition:means", "case:en:teaching:is"),\n    ),',
        '        (ProgramStep(ConstructionProgramOperation.WRAP_DISCOURSE_ACT, "discourse:definition"),),\n        ("case:en:definition:means", "case:en:teaching:is"),\n        DefinitionLearningContractSeedV351(\n            form_category="term",\n            parent_category="definition_content",\n            definition_relation="subtype",\n        ),\n    ),',
        allow_drift=allow_drift,
    )
    replace_once(path, "_ENGLISH_REVISION = 3", "_ENGLISH_REVISION = 4", allow_drift=allow_drift)

def verify_patch_anchors(repo: Path, *, allow_drift: bool) -> None:
    """Exercise every source-edit anchor in a disposable minimal checkout view."""
    with tempfile.TemporaryDirectory(prefix="cemm-phases13-14-check-") as tmp:
        shadow = Path(tmp)
        required = (
            "cemm/v350/runtime_v351.py",
            "cemm/v350/learning/__init__.py",
            "cemm/v350/learning/runtime_advance.py",
            "cemm/v350/learning/promotion.py",
            "cemm/v350/language/minimum_english_v351.py",
        )
        for rel in required:
            source = repo / rel
            target = shadow / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        patch_runtime(shadow, allow_drift=allow_drift)
        patch_learning_exports(shadow)
        patch_legacy_learning_safety(shadow, allow_drift=allow_drift)
        patch_phase14_promotion_graph(shadow, allow_drift=allow_drift)
        patch_reviewed_learning_source(shadow, allow_drift=allow_drift)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("repo", type=Path)
    ap.add_argument("--allow-drift", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    repo = args.repo.resolve()
    head = git_head(repo)
    if head != BASELINE and not args.allow_drift:
        raise SystemExit(f"baseline mismatch: expected {BASELINE}, got {head}")
    if args.dry_run:
        verify_patch_anchors(repo, allow_drift=args.allow_drift)
        print(f"baseline-and-anchors-ok:{head}")
        return
    copy_payload(repo)
    patch_runtime(repo, allow_drift=args.allow_drift)
    patch_learning_exports(repo)
    patch_legacy_learning_safety(repo, allow_drift=args.allow_drift)
    patch_phase14_promotion_graph(repo, allow_drift=args.allow_drift)
    patch_reviewed_learning_source(repo, allow_drift=args.allow_drift)
    print("CEMM v3.5.1 Phases 13-14 patch applied")
    print(f"baseline:{BASELINE}")


if __name__ == "__main__":
    main()
