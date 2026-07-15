"""GapDetector — structural gaps for selected interpretations only."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from ..model.gap import GapRecord, ProbePlan
from .grounding import GraphGrounding


BLOCKER_KINDS: tuple[str, ...] = (
    "missing_semantic_family", "missing_definition_field",
    "missing_required_role", "missing_value_type",
    "missing_constitutive_pattern", "missing_differentiator",
    "ungrounded_dependency", "unsupported_recursive_cycle",
    "missing_independent_competence", "actual_context_not_admitted",
    "expressiveness_blocker", "sense_individuation_pending",
    "stale_assessment",
)


@dataclass(frozen=True, slots=True)
class GapDetectionResult:
    gaps: tuple[GapRecord, ...] = ()
    blocking_gaps: tuple[GapRecord, ...] = ()
    has_blocking: bool = False

    @property
    def gap_count(self) -> int:
        return len(self.gaps)


class GapDetector:
    def detect(
        self,
        candidate_graph: Any | None = None,
        grounding_assessments: list[Any] | None = None,
        epistemic_assessments: list[Any] | None = None,
        capability_assessment: Any | None = None,
        selected_interpretations: list[Any] | None = None,
        suppress_fresh_lexical_gaps: bool = False,
    ) -> GapDetectionResult:
        gaps: list[GapRecord] = []
        graph_grounding = self._graph_grounding(grounding_assessments)
        selected = tuple(selected_interpretations or ())
        selected_predication_refs = {
            getattr(item, "predication_ref", "") for item in selected
            if getattr(item, "predication_ref", "")
        }
        # A selected outer proposition may embed the proposition whose exact
        # open role or opaque filler is blocking the query. Include that
        # compositional dependency without selecting it as an assertion.
        if candidate_graph is not None:
            selected_prop_refs = {
                getattr(item, "proposition_ref", "") for item in selected
                if getattr(item, "proposition_ref", "")
            }
            embedded_prop_refs: set[str] = set()
            for candidate in getattr(candidate_graph, "candidate_propositions", ()):
                if candidate.proposition.id in selected_prop_refs:
                    embedded_prop_refs.update(candidate.embedded_proposition_refs)
            for candidate in getattr(candidate_graph, "candidate_propositions", ()):
                if candidate.proposition.id in embedded_prop_refs:
                    selected_predication_refs.add(candidate.proposition.predication_ref)

        if graph_grounding is not None:
            for predication in graph_grounding.predications:
                if selected_predication_refs and predication.predication_ref not in selected_predication_refs:
                    continue

                for binding in predication.role_bindings:
                    grounding = binding.grounding
                    if grounding is None or not grounding.is_unknown:
                        continue
                    if suppress_fresh_lexical_gaps:
                        continue
                    target = grounding.discourse_identity or grounding.referent_ref
                    gaps.append(
                        self._gap(
                            "missing_semantic_family",
                            target,
                            "ground",
                            expected="semantic_family",
                            missing=("semantic_family",),
                        )
                    )

                query_open_roles = set(getattr(predication, "query_role_refs", ()) or ())
                for role_ref in predication.unresolved_role_refs:
                    if role_ref in query_open_roles:
                        continue
                    gaps.append(
                        self._gap(
                            "missing_required_role",
                            role_ref,
                            "compose",
                            expected="role_filler",
                            missing=(role_ref,),
                        )
                    )

                if (
                    predication.definition is not None
                    and predication.definition.blockers
                    and predication.predicate_schema_ref
                ):
                    # Do not duplicate the lexical gap when the only blocker is
                    # an opaque role filler; preserve exact definition blockers.
                    for blocker in predication.definition.blockers:
                        if blocker == "predicate schema unresolved":
                            gaps.append(
                                self._gap(
                                    "ungrounded_dependency",
                                    predication.predicate_schema_ref,
                                    "ground",
                                    expected="predicate_schema",
                                )
                            )

        # Detect opaque lexical refs that were never resolved into any
        # predication.  A bare unknown word without a construction match
        # produces no role bindings, but the system still needs to learn it.
        if candidate_graph is not None and not suppress_fresh_lexical_gaps:
            opaque_refs = tuple(getattr(candidate_graph, "opaque_lexeme_refs", ()) or ())
            if opaque_refs and not selected_predication_refs:
                for opaque_ref in opaque_refs:
                    target = opaque_ref
                    gaps.append(
                        self._gap(
                            "missing_semantic_family",
                            target,
                            "ground",
                            expected="semantic_family",
                            missing=("semantic_family",),
                        )
                    )

        if epistemic_assessments:
            for assessment in epistemic_assessments:
                if getattr(assessment, "admissibility", "") == "blocked":
                    gaps.append(
                        GapRecord(
                            id=f"gap:{uuid4().hex[:12]}",
                            gap_kind="actual_context_not_admitted",
                            target_artifact_ref=getattr(assessment, "proposition_ref", ""),
                            blocked_stage="know",
                            learnable=False,
                        )
                    )

        if capability_assessment is not None and not getattr(
            capability_assessment, "is_capable", True
        ):
            for limitation in getattr(capability_assessment, "limitations", ()):
                gaps.append(
                    self._gap(
                        "missing_independent_competence",
                        str(limitation),
                        "know",
                        expected="competence_evidence",
                    )
                )

        gaps = self._dedupe(gaps)
        blocking = tuple(
            gap for gap in gaps
            if gap.blocked_stage in {"compose", "ground", "know"}
        )
        return GapDetectionResult(
            gaps=tuple(gaps),
            blocking_gaps=blocking,
            has_blocking=bool(blocking),
        )

    @staticmethod
    def _gap(
        kind: str,
        target: str,
        stage: str,
        *,
        expected: str,
        missing: tuple[str, ...] = (),
    ) -> GapRecord:
        gap_id = f"gap:{uuid4().hex[:12]}"
        probe_key = f"probe:{kind}:{target}"
        return GapRecord(
            id=gap_id,
            gap_kind=kind,
            target_artifact_ref=target,
            missing_fields=missing,
            blocked_stage=stage,
            learnable=True,
            probe_options=(
                ProbePlan(
                    probe_kind="ask_user",
                    target_ref=target,
                    expected_evidence_kind=expected,
                    idempotency_key=probe_key,
                ),
            ),
            expected_evidence_schema_ref=expected,
        )

    @staticmethod
    def _graph_grounding(values: list[Any] | None) -> GraphGrounding | None:
        if not values:
            return None
        return next((item for item in values if isinstance(item, GraphGrounding)), None)

    @staticmethod
    def _dedupe(gaps: list[GapRecord]) -> list[GapRecord]:
        result: list[GapRecord] = []
        seen: set[tuple[str, str, tuple[str, ...]]] = set()
        for gap in gaps:
            key = (gap.gap_kind, gap.target_artifact_ref, gap.missing_fields)
            if key not in seen:
                seen.add(key)
                result.append(gap)
        return result

    def classify_blocking(
        self, gaps: tuple[GapRecord, ...], selected_refs: set[str],
    ) -> tuple[GapRecord, ...]:
        return tuple(
            gap for gap in gaps
            if gap.target_artifact_ref in selected_refs
            or gap.blocked_stage in {"compose", "ground", "know"}
        )
