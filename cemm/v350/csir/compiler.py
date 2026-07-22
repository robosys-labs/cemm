"""Mandatory Stage-5 exact CSIR compiler barrier.

This compiler accepts only explicit CSIR graph/fragments.  Legacy UOL/schema labels may
reach this boundary only through a separately reviewed Phase-8 one-way compiler that
produces exact CSIR fragments.  Opaque legacy objects never enter the solver and there
is no fallback path.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .authority import CURRENT_KERNEL_ABI
from .canonical import exact_fingerprint, normalize, semantic_fingerprint
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

    External/language services may propose exact fragments, but they never choose the
    final semantic fingerprint.  The kernel validates, normalizes and recomputes it.
    """

    RUNTIME_ABI = "v351"
    SERVICE_KIND = "csir_compiler"

    @staticmethod
    def _fragment(value: Any) -> CSIRCandidateFragment | None:
        if isinstance(value, CSIRCandidateFragment):
            return value
        if isinstance(value, CSIRGraph):
            return CSIRCandidateFragment(fragment_ref="inline-csir-graph", graph=value)
        converter = getattr(value, "to_csir_fragment", None)
        if callable(converter):
            converted = converter()
            if not isinstance(converted, CSIRCandidateFragment):
                raise CSIRCompilationError("to_csir_fragment() must return CSIRCandidateFragment")
            return converted
        return None

    def compile_fragments(
        self,
        values: Iterable[Any],
        *,
        authority_generation: int,
        authority_fingerprint: str,
        canonicalization_budget: int = 100_000,
    ) -> ExactCompilationResult:
        if authority_generation < 1 or not authority_fingerprint:
            raise CSIRCompilationError("Stage 5 requires exact pinned AuthorityGeneration")
        fragments = []
        opaque = []
        for value in values:
            fragment = self._fragment(value)
            if fragment is None:
                opaque.append(type(value).__name__)
            else:
                fragments.append(fragment)

        frontiers = []
        if opaque:
            frontiers.append(
                CompilationFrontier(
                    frontier_ref="frontier:csir:opaque-candidate-input",
                    missing_contract="explicit_csir_fragment_or_phase8_one_way_compiler",
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
            return ExactCompilationResult((), (), (), tuple(x.frontier_ref for x in frontiers), tuple(frontiers))

        # Semantic-equivalent derivations collapse into one exact candidate class, while
        # proof/evidence lineage is unioned rather than discarded.
        classes: dict[str, dict[str, Any]] = {}
        for fragment in fragments:
            if fragment.graph.applications and not fragment.closure_proof_refs:
                frontiers.append(
                    CompilationFrontier(
                        frontier_ref="frontier:csir:missing-exact-definition-closure-proof:" + fragment.fragment_ref,
                        missing_contract="exact_definition_closure_proof",
                        source_refs=(fragment.fragment_ref,),
                    )
                )
                continue
            graph = normalize(fragment.graph, budget=canonicalization_budget)
            sem_fp = semantic_fingerprint(graph, budget=canonicalization_budget)
            exact_fp = exact_fingerprint(graph, budget=canonicalization_budget)
            bucket = classes.setdefault(
                sem_fp,
                {
                    "graphs": [],
                    "evidence": set(),
                    "closure": set(),
                    "constraints": set(),
                    "prior": float("-inf"),
                    "fragment_refs": set(),
                },
            )
            bucket["graphs"].append((exact_fp, graph))
            bucket["evidence"].update(fragment.evidence_refs)
            bucket["closure"].update(fragment.closure_proof_refs)
            bucket["constraints"].update(fragment.hard_constraint_trace_refs)
            bucket["prior"] = max(bucket["prior"], fragment.prior_score)
            bucket["fragment_refs"].add(fragment.fragment_ref)

        candidates = []
        for sem_fp in sorted(classes):
            bucket = classes[sem_fp]
            # Prefer lexicographically smallest exact normal form only as a proof-lineage
            # representative; semantic class identity is sem_fp.
            exact_fp, graph = min(bucket["graphs"], key=lambda item: item[0])
            candidate_ref = "csir-candidate:" + sem_fp[:32]
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
                    closure_proof_refs=tuple(sorted(bucket["closure"])),
                    hard_constraint_trace_refs=tuple(sorted(bucket["constraints"])),
                    prior_score=bucket["prior"],
                )
            )
        return ExactCompilationResult(
            candidates=tuple(candidates),
            closure_proof_refs=tuple(sorted({x for c in candidates for x in c.closure_proof_refs})),
            hard_constraint_trace_refs=tuple(sorted({x for c in candidates for x in c.hard_constraint_trace_refs})),
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
    ) -> CSIRCandidate:
        result = self.compile_fragments(
            (
                CSIRCandidateFragment(
                    fragment_ref=candidate.candidate_ref,
                    graph=candidate.graph,
                    evidence_refs=candidate.evidence_refs,
                    closure_proof_refs=candidate.closure_proof_refs,
                    hard_constraint_trace_refs=candidate.hard_constraint_trace_refs,
                    prior_score=candidate.prior_score,
                ),
            ),
            authority_generation=authority_generation,
            authority_fingerprint=authority_fingerprint,
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
