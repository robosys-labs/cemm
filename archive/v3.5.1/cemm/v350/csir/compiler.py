"""Mandatory Stage-5 exact CSIR compiler barrier for v3.5.1.

Only explicit CSIR fragments cross this boundary. Legacy UOL/schema objects must first
pass the reviewed one-way migration compiler. Higher-order applications require typed,
verifiable ``ClosureProof`` objects; a string that merely looks like a proof reference is
not authority.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .authority import CURRENT_KERNEL_ABI
from .authority_v351 import (
    AuthoritySnapshotV351,
    ClosureProof,
    ExecutableAuthorityEnvelope,
    ClosureProofError,
    HardConstraintTrace,
    SemanticAuthorityError,
)
from .canonical_v351 import exact_fingerprint, normalize, semantic_fingerprint
from .model import CSIRCandidate, CSIRCandidateFragment, CSIRGraph


class CSIRCompilationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class CompilationFrontier:
    frontier_ref: str
    missing_contract: str
    source_refs: tuple[str, ...] = ()
    effects: tuple[str, ...] = ("learning", "blocks_query_answer")


@dataclass(frozen=True, slots=True)
class ExactCompilationResult:
    candidates: tuple[CSIRCandidate, ...]
    closure_proof_refs: tuple[str, ...]
    hard_constraint_trace_refs: tuple[str, ...]
    unresolved_refs: tuple[str, ...]
    frontiers: tuple[CompilationFrontier, ...]


class ExactCSIRCompiler:
    """Kernel-owned canonicalization/validation barrier.

    External/language services may propose exact fragments, but never choose final
    semantic identity. The kernel validates typed closure proofs, normalizes and
    recomputes fingerprints.
    """

    RUNTIME_ABI = "v351"
    SERVICE_KIND = "csir_compiler"

    @staticmethod
    def _fragment(value: Any) -> CSIRCandidateFragment | None:
        if isinstance(value, CSIRCandidateFragment):
            return value
        if isinstance(value, CSIRGraph):
            return CSIRCandidateFragment(fragment_ref="inline-csir-graph", graph=value)
        # Deliberately no duck-typed to_csir_fragment(). A wrapper around legacy authority
        # is still legacy authority and must stay in cemm.migration.
        return None

    @staticmethod
    def _verify_closure_proofs(
        fragment: CSIRCandidateFragment,
        graph: CSIRGraph,
        *,
        authority_generation: int,
        authority_fingerprint: str,
        semantic_authority_snapshot: AuthoritySnapshotV351 | None,
    ) -> tuple[
        tuple[str, ...],
        tuple[Any, ...],
        tuple[CompilationFrontier, ...],
    ]:
        if not graph.applications:
            return (), (), ()
        raw = tuple(fragment.closure_proofs)
        if not raw:
            return (), (), (
                CompilationFrontier(
                    frontier_ref=(
                        "frontier:csir:missing-exact-definition-closure-proof:"
                        + fragment.fragment_ref
                    ),
                    missing_contract="typed_exact_definition_closure_proof",
                    source_refs=(fragment.fragment_ref,),
                ),
            )
        if semantic_authority_snapshot is None:
            return (), (), (
                CompilationFrontier(
                    frontier_ref=(
                        "frontier:csir:missing-semantic-authority-snapshot:"
                        + fragment.fragment_ref
                    ),
                    missing_contract="AuthoritySnapshotV351 required to verify definition closure",
                    source_refs=(fragment.fragment_ref,),
                ),
            )

        verified: list[str] = []
        closure_keys: set[tuple[str, str, str, int, str, str]] = set()
        required_constraints: dict[tuple[str, str, str, int, str, str], Any] = {}
        frontiers: list[CompilationFrontier] = []
        for value in raw:
            if not isinstance(value, ClosureProof):
                frontiers.append(
                    CompilationFrontier(
                        frontier_ref=(
                            "frontier:csir:unverified-definition-closure-proof:"
                            + fragment.fragment_ref
                        ),
                        missing_contract="ClosureProof payload, not opaque proof-ref string",
                        source_refs=(fragment.fragment_ref, str(value)),
                    )
                )
                continue
            try:
                value.verify_authority(semantic_authority_snapshot)
            except ClosureProofError as exc:
                frontiers.append(
                    CompilationFrontier(
                        frontier_ref=(
                            "frontier:csir:invalid-definition-closure-proof:"
                            + fragment.fragment_ref
                            + ":"
                            + value.proof_ref[-16:]
                        ),
                        missing_contract="valid_exact_definition_closure_proof",
                        source_refs=(fragment.fragment_ref, value.proof_ref, str(exc)),
                    )
                )
                continue
            verified.append(value.proof_ref)
            closure_keys.update(pin.key for pin in value.closure_pins)
            for constraint_pin in value.constraint_pins:
                required_constraints[constraint_pin.key] = constraint_pin

        if frontiers:
            return (), (), tuple(frontiers)
        uncovered = sorted(
            application.predicate_pin.key
            for application in graph.applications
            if application.predicate_pin.key not in closure_keys
        )
        if uncovered:
            return (), (), (
                CompilationFrontier(
                    frontier_ref="frontier:csir:predicate-outside-proven-definition-closure:" + fragment.fragment_ref,
                    missing_contract="every executable predicate covered by exact typed closure proof",
                    source_refs=(fragment.fragment_ref, *tuple(map(str, uncovered))),
                ),
            )
        try:
            semantic_authority_snapshot.validate_executable_graph(graph)
        except SemanticAuthorityError as exc:
            return (), (), (
                CompilationFrontier(
                    frontier_ref="frontier:csir:definition-structure-violation:" + fragment.fragment_ref,
                    missing_contract="concrete CSIR applications conform to exact definition ports/profiles",
                    source_refs=(fragment.fragment_ref, str(exc)),
                ),
            )
        return (
            tuple(sorted(set(verified))),
            tuple(required_constraints[key] for key in sorted(required_constraints)),
            (),
        )

    @staticmethod
    def _verify_hard_constraints(
        fragment: CSIRCandidateFragment,
        graph: CSIRGraph,
        *,
        required_constraint_pins: tuple[Any, ...],
        semantic_authority_snapshot: AuthoritySnapshotV351 | None,
    ) -> tuple[tuple[str, ...], tuple[CompilationFrontier, ...]]:
        raw = tuple(fragment.hard_constraint_traces)
        if not required_constraint_pins:
            if raw:
                return (), (
                    CompilationFrontier(
                        frontier_ref=(
                            "frontier:csir:unexpected-hard-constraint-trace:"
                            + fragment.fragment_ref
                        ),
                        missing_contract="constraint trace must correspond to proven exact constraints",
                        source_refs=(fragment.fragment_ref,),
                    ),
                )
            return (), ()
        if semantic_authority_snapshot is None:
            return (), (
                CompilationFrontier(
                    frontier_ref=(
                        "frontier:csir:missing-semantic-authority-for-constraints:"
                        + fragment.fragment_ref
                    ),
                    missing_contract="AuthoritySnapshotV351 required for hard constraints",
                    source_refs=(fragment.fragment_ref,),
                ),
            )
        if not raw:
            return (), (
                CompilationFrontier(
                    frontier_ref=(
                        "frontier:csir:missing-hard-constraint-trace:" + fragment.fragment_ref
                    ),
                    missing_contract="typed HardConstraintTrace covering exact constraint closure",
                    source_refs=(fragment.fragment_ref,),
                ),
            )
        verified: list[str] = []
        frontiers: list[CompilationFrontier] = []
        for trace in raw:
            if not isinstance(trace, HardConstraintTrace):
                frontiers.append(
                    CompilationFrontier(
                        frontier_ref=(
                            "frontier:csir:unverified-hard-constraint-trace:"
                            + fragment.fragment_ref
                        ),
                        missing_contract="HardConstraintTrace payload, not opaque ref",
                        source_refs=(fragment.fragment_ref, str(trace)),
                    )
                )
                continue
            try:
                trace.verify(
                    graph,
                    authority_snapshot=semantic_authority_snapshot,
                    required_constraint_pins=required_constraint_pins,
                )
            except SemanticAuthorityError as exc:
                frontiers.append(
                    CompilationFrontier(
                        frontier_ref=(
                            "frontier:csir:invalid-hard-constraint-trace:"
                            + fragment.fragment_ref
                            + ":"
                            + trace.trace_ref[-16:]
                        ),
                        missing_contract="valid exact hard constraint trace",
                        source_refs=(fragment.fragment_ref, trace.trace_ref, str(exc)),
                    )
                )
                continue
            verified.append(trace.trace_ref)
        return tuple(sorted(set(verified))), tuple(frontiers)

    def compile_fragments(
        self,
        values: Iterable[Any],
        *,
        authority_generation: int,
        authority_fingerprint: str,
        semantic_authority_snapshot: AuthoritySnapshotV351 | None = None,
        operation: str = "compose",
        context_ref: str = "global",
        permission_ref: str = "public",
        require_execution_authority: bool = True,
        require_projection_authority: bool = False,
        canonicalization_budget: int = 100_000,
    ) -> ExactCompilationResult:
        if authority_generation < 1 or not authority_fingerprint:
            raise CSIRCompilationError("Stage 5 requires exact pinned AuthorityGeneration")
        if semantic_authority_snapshot is not None and (
            semantic_authority_snapshot.generation, semantic_authority_snapshot.authority_fingerprint
        ) != (authority_generation, authority_fingerprint):
            raise CSIRCompilationError("Stage 5 semantic authority snapshot differs from pinned AuthorityGeneration")
        fragments = []
        opaque = []
        for value in values:
            fragment = self._fragment(value)
            if fragment is None:
                opaque.append(type(value).__name__)
            else:
                fragments.append(fragment)

        frontiers: list[CompilationFrontier] = []
        if opaque:
            frontiers.append(
                CompilationFrontier(
                    frontier_ref="frontier:csir:opaque-candidate-input",
                    missing_contract="explicit_csir_fragment_or_reviewed_phase8_one_way_compiler",
                    source_refs=tuple(sorted(set(opaque))),
                )
            )
        if not fragments:
            frontiers.append(
                CompilationFrontier(
                    frontier_ref="frontier:csir:no-exact-candidate-fragments",
                    missing_contract="exact_csir_candidate_fragments",
                )
            )
            return ExactCompilationResult(
                (), (), (), tuple(x.frontier_ref for x in frontiers), tuple(frontiers)
            )

        classes: dict[str, dict[str, Any]] = {}
        for fragment in fragments:
            graph = normalize(fragment.graph, budget=canonicalization_budget)
            verified_closure, required_constraints, closure_frontiers = self._verify_closure_proofs(
                fragment,
                graph,
                authority_generation=authority_generation,
                authority_fingerprint=authority_fingerprint,
                semantic_authority_snapshot=semantic_authority_snapshot,
            )
            if closure_frontiers:
                frontiers.extend(closure_frontiers)
                continue

            execution_authority: ExecutableAuthorityEnvelope | None = None
            if require_execution_authority and graph.applications:
                if semantic_authority_snapshot is None:
                    frontiers.append(
                        CompilationFrontier(
                            frontier_ref="frontier:csir:missing-execution-authority:" + fragment.fragment_ref,
                            missing_contract="split exact executable authority envelope",
                            source_refs=(fragment.fragment_ref,),
                        )
                    )
                    continue
                try:
                    graph, execution_authority = semantic_authority_snapshot.bind_execution_authority(
                        graph,
                        operation=operation,
                        context_ref=context_ref,
                        permission_ref=permission_ref,
                        projection_authority_pins=tuple(fragment.projection_authority_pins),
                        causal_mechanism_pins=tuple(fragment.causal_mechanism_pins),
                        policy_adapter_pins=tuple(fragment.policy_adapter_pins),
                        require_projection_authority=(
                            require_projection_authority or bool(fragment.requires_projection_authority)
                        ),
                    )
                    graph = normalize(graph, budget=canonicalization_budget)
                    execution_authority.verify(graph, semantic_authority_snapshot)
                except SemanticAuthorityError as exc:
                    frontiers.append(
                        CompilationFrontier(
                            frontier_ref="frontier:csir:invalid-execution-authority:" + fragment.fragment_ref,
                            missing_contract="exact operational/profile/dynamics/use/projection authority",
                            source_refs=(fragment.fragment_ref, str(exc)),
                        )
                    )
                    continue

            verified_constraints, constraint_frontiers = self._verify_hard_constraints(
                fragment,
                graph,
                required_constraint_pins=required_constraints,
                semantic_authority_snapshot=semantic_authority_snapshot,
            )
            if constraint_frontiers:
                frontiers.extend(constraint_frontiers)
                continue
            sem_fp = semantic_fingerprint(graph, budget=canonicalization_budget)
            exact_fp = exact_fingerprint(graph, budget=canonicalization_budget)
            bucket = classes.setdefault(
                sem_fp,
                {
                    "derivations": [],
                    "evidence": set(),
                    "prior": float("-inf"),
                },
            )
            # Keep closure proof lineage attached to the derivation it actually proves.
            # Do not union unrelated closure refs and later attach them to an arbitrary
            # lexicographically-selected representative.
            bucket["derivations"].append(
                (
                    exact_fp,
                    "" if execution_authority is None else execution_authority.envelope_ref,
                    tuple(verified_closure),
                    tuple(verified_constraints),
                    graph,
                    execution_authority,
                )
            )
            bucket["evidence"].update(fragment.evidence_refs)
            bucket["prior"] = max(bucket["prior"], fragment.prior_score)

        candidates = []
        for sem_fp in sorted(classes):
            bucket = classes[sem_fp]
            (
                exact_fp,
                _execution_authority_ref,
                closure_refs,
                constraint_refs,
                graph,
                execution_authority,
            ) = min(
                bucket["derivations"],
                key=lambda item: (item[0], item[1], item[2], item[3]),
            )
            candidate_ref = "csir-candidate:" + sem_fp[:32]
            # Semantic-class evidence can be unioned. Exact closure lineage must remain
            # the lineage of the selected exact representative.
            candidates.append(
                CSIRCandidate(
                    candidate_ref=candidate_ref,
                    graph=graph,
                    semantic_fingerprint=sem_fp,
                    exact_fingerprint=exact_fp,
                    authority_generation=authority_generation,
                    authority_fingerprint=authority_fingerprint,
                    kernel_abi_fingerprint=CURRENT_KERNEL_ABI.fingerprint,
                    evidence_refs=tuple(sorted(bucket["evidence"])),
                    closure_proof_refs=closure_refs,
                    hard_constraint_trace_refs=constraint_refs,
                    execution_authority_ref=(
                        "" if execution_authority is None else execution_authority.envelope_ref
                    ),
                    semantic_authority_snapshot_fingerprint=(
                        "" if execution_authority is None
                        else execution_authority.semantic_authority_snapshot_fingerprint
                    ),
                    dynamics_parameter_pins=(
                        () if execution_authority is None else execution_authority.dynamics_parameter_pins
                    ),
                    use_authorization_pins=(
                        () if execution_authority is None else execution_authority.use_authorization_pins
                    ),
                    projection_authority_pins=(
                        () if execution_authority is None else execution_authority.projection_authority_pins
                    ),
                    causal_mechanism_pins=(
                        () if execution_authority is None else execution_authority.causal_mechanism_pins
                    ),
                    policy_adapter_pins=(
                        () if execution_authority is None else execution_authority.policy_adapter_pins
                    ),
                    projection_authority_required=(
                        False if execution_authority is None
                        else execution_authority.projection_authority_required
                    ),
                    prior_score=bucket["prior"],
                )
            )
        return ExactCompilationResult(
            candidates=tuple(candidates),
            closure_proof_refs=tuple(
                sorted({x for c in candidates for x in c.closure_proof_refs})
            ),
            hard_constraint_trace_refs=tuple(
                sorted({x for c in candidates for x in c.hard_constraint_trace_refs})
            ),
            unresolved_refs=tuple(x.frontier_ref for x in frontiers),
            frontiers=tuple(frontiers),
        )

    def validate_candidate(
        self,
        candidate: CSIRCandidate,
        *,
        authority_generation: int,
        authority_fingerprint: str,
        canonicalization_budget: int = 100_000,
        closure_proofs: Iterable[ClosureProof] = (),
        hard_constraint_traces: Iterable[HardConstraintTrace] = (),
        semantic_authority_snapshot: AuthoritySnapshotV351 | None = None,
    ) -> CSIRCandidate:
        proofs_by_ref = {item.proof_ref: item for item in closure_proofs}
        proof_payloads = tuple(
            proofs_by_ref[ref]
            for ref in candidate.closure_proof_refs
            if ref in proofs_by_ref
        )
        traces_by_ref = {item.trace_ref: item for item in hard_constraint_traces}
        trace_payloads = tuple(
            traces_by_ref[ref]
            for ref in candidate.hard_constraint_trace_refs
            if ref in traces_by_ref
        )
        result = self.compile_fragments(
            (
                CSIRCandidateFragment(
                    fragment_ref=candidate.candidate_ref,
                    graph=candidate.graph,
                    evidence_refs=candidate.evidence_refs,
                    closure_proofs=proof_payloads,
                    hard_constraint_trace_refs=candidate.hard_constraint_trace_refs,
                    hard_constraint_traces=trace_payloads,
                    projection_authority_pins=candidate.projection_authority_pins,
                    causal_mechanism_pins=candidate.causal_mechanism_pins,
                    policy_adapter_pins=candidate.policy_adapter_pins,
                    requires_projection_authority=candidate.projection_authority_required,
                    prior_score=candidate.prior_score,
                ),
            ),
            authority_generation=authority_generation,
            authority_fingerprint=authority_fingerprint,
            semantic_authority_snapshot=semantic_authority_snapshot,
            canonicalization_budget=canonicalization_budget,
        )
        if len(result.candidates) != 1:
            raise CSIRCompilationError("candidate did not validate to one exact semantic class")
        return result.candidates[0]


__all__ = [
    "CSIRCompilationError",
    "CompilationFrontier",
    "ExactCSIRCompiler",
    "ExactCompilationResult",
]
