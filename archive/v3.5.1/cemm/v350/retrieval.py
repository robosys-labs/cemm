"""Stage-10 semantic retrieval and answer binding.

Retrieval operates on UOL structure only.  It never searches generated text or
routes on interrogative words.  Open QUERY bindings are matched against exact
schema revisions in the pinned semantic store; concrete non-query bindings are
structural constraints on candidate applications.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .learning.model import PinnedRecord
from .schema.model import OpenBindingPurpose, PortFillerClass, semantic_fingerprint
from .storage import RecordKind, SemanticStore, StoreSnapshot
from .uol.model import ApplicationBinding, FillerRef, SemanticApplication, UOLGraph


@dataclass(frozen=True, slots=True)
class AnswerBinding:
    binding_ref: str
    query_application_ref: str
    matched_application_pin: PinnedRecord
    variable_fillers: tuple[tuple[str, tuple[FillerRef, ...]], ...]
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    bindings: tuple[AnswerBinding, ...]
    unresolved_query_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]


class SemanticRetriever:
    def __init__(self, store: SemanticStore) -> None:
        self.store = store

    def bind(
        self,
        graph: UOLGraph,
        *,
        context_ref: str,
        snapshot: StoreSnapshot | None = None,
        maximum_matches_per_query: int = 64,
    ) -> RetrievalResult:
        if maximum_matches_per_query < 1:
            raise ValueError("maximum_matches_per_query must be positive")
        if snapshot is None:
            with self.store.snapshot() as pinned:
                return self.bind(
                    graph,
                    context_ref=context_ref,
                    snapshot=pinned,
                    maximum_matches_per_query=maximum_matches_per_query,
                )
        self.store.assert_snapshot(snapshot)

        answers: list[AnswerBinding] = []
        unresolved: list[str] = []
        evidence: set[str] = set(graph.evidence_refs)
        candidates = self.store.records(
            RecordKind.SEMANTIC_APPLICATION,
            all_revisions=False,
            snapshot=snapshot,
        )

        for query in sorted(graph.applications.values(), key=lambda item: item.application_ref):
            open_bindings = tuple(
                binding
                for binding in query.bindings
                if binding.open_binding_purpose == OpenBindingPurpose.QUERY
            )
            if not open_bindings:
                continue
            concrete = tuple(
                binding
                for binding in query.bindings
                if binding.open_binding_purpose is None
            )
            matches = []
            for stored in candidates:
                candidate = stored.payload
                if not isinstance(candidate, SemanticApplication):
                    continue
                if (candidate.schema_ref, candidate.schema_revision) != (
                    query.schema_ref,
                    query.schema_revision,
                ):
                    continue
                if candidate.context_ref not in {"global", context_ref}:
                    continue
                if not _concrete_bindings_match(concrete, candidate):
                    continue
                variable_fillers = _answer_fillers(open_bindings, candidate)
                if variable_fillers is None:
                    continue
                pin = PinnedRecord(
                    stored.record_kind,
                    stored.record_ref,
                    stored.revision,
                    stored.record_fingerprint,
                )
                matches.append(
                    AnswerBinding(
                        binding_ref="answer-binding:"
                        + semantic_fingerprint(
                            "answer-binding-ref",
                            (
                                query.application_ref,
                                pin.key,
                                pin.record_fingerprint,
                                variable_fillers,
                            ),
                            24,
                        ),
                        query_application_ref=query.application_ref,
                        matched_application_pin=pin,
                        variable_fillers=variable_fillers,
                        evidence_refs=tuple(
                            sorted(
                                set(query.evidence_refs)
                                | set(candidate.evidence_refs)
                                | {stored.record_fingerprint}
                            )
                        ),
                    )
                )
                if len(matches) >= maximum_matches_per_query:
                    break
            if not matches:
                unresolved.append(query.application_ref)
            answers.extend(matches)
            for item in matches:
                evidence.update(item.evidence_refs)

        return RetrievalResult(
            bindings=tuple(sorted(answers, key=lambda item: item.binding_ref)),
            unresolved_query_refs=tuple(sorted(set(unresolved))),
            evidence_refs=tuple(sorted(evidence)),
        )


def _concrete_bindings_match(
    query_bindings: Iterable[ApplicationBinding], candidate: SemanticApplication
) -> bool:
    for query_binding in query_bindings:
        candidate_binding = candidate.binding(query_binding.port_ref)
        if candidate_binding is None:
            return False
        expected = tuple(sorted(_filler_key(item) for item in query_binding.fillers))
        actual = tuple(sorted(_filler_key(item) for item in candidate_binding.fillers))
        if expected != actual:
            return False
    return True


def _answer_fillers(
    open_bindings: Iterable[ApplicationBinding], candidate: SemanticApplication
) -> tuple[tuple[str, tuple[FillerRef, ...]], ...] | None:
    result = []
    for query_binding in open_bindings:
        candidate_binding = candidate.binding(query_binding.port_ref)
        if candidate_binding is None or candidate_binding.open_binding_purpose is not None:
            return None
        concrete = tuple(
            item
            for item in candidate_binding.fillers
            if isinstance(item, FillerRef)
            and item.filler_class != PortFillerClass.SEMANTIC_VARIABLE
        )
        if not concrete:
            return None
        variables = tuple(
            item.ref
            for item in query_binding.fillers
            if isinstance(item, FillerRef)
            and item.filler_class == PortFillerClass.SEMANTIC_VARIABLE
        )
        if not variables:
            # QUERY authority belongs to the explicit open-binding marker; a query
            # without a variable is still a retrieval frontier, never an implicit
            # request to stringify the candidate application.
            return None
        for variable_ref in variables:
            result.append((variable_ref, concrete))
    return tuple(sorted(result, key=lambda item: item[0]))


def _filler_key(value: object) -> tuple[str, str]:
    filler_class = getattr(value, "filler_class", None)
    ref = getattr(value, "ref", None)
    if filler_class is not None and ref is not None:
        return str(getattr(filler_class, "value", filler_class)), str(ref)
    literal_ref = getattr(value, "literal_ref", None)
    return "quoted_literal", str(literal_ref)
