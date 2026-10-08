"""Read-only, graph-exact reference check for candidate English surfaces.

This module does NOT generate text. It verifies that a candidate surface
has the same canonical expression as a previously evaluated, proof-bearing
ResponseMeaning, by independently running CEMM's SAME ORIENT/PROPOSE/VERIFY
owners without EFFECT. Only a narrow asserted, actual, positively supported
answer subset is eligible. Nothing here admits the old keyword/template
realization checker or R5 neural activation.
"""
from __future__ import annotations

from dataclasses import dataclass

from .canonical import stable_ref
from .r3_response import ResponseMeaning
from .runtime import HybridRuntime


@dataclass(frozen=True, slots=True)
class SurfaceAssessment:
    equivalent: bool
    reason: str
    response_meaning_ref: str
    candidate_ref: str
    parsed_expression_ref: str | None
    world_revision: int

    def __post_init__(self) -> None:
        if type(self.equivalent) is not bool:
            raise TypeError("equivalent must be an exact bool")
        if type(self.reason) is not str or not self.reason:
            raise TypeError("reason must be nonempty")
        if self.equivalent != (self.reason == "canonical_expression_equal"):
            raise ValueError("assessment status and reason disagree")
        if type(self.world_revision) is not int or self.world_revision < 0:
            raise ValueError("invalid world revision")


class SemanticSurfaceOracle:
    """Exact semantic comparison, NOT a language generative model."""

    def __init__(self, runtime: HybridRuntime):
        if type(runtime) is not HybridRuntime:
            raise TypeError("surface oracle requires canonical HybridRuntime")
        self._runtime = runtime

    def assess(
        self, *, response: ResponseMeaning,
        session_ref: str, candidate: str,
    ) -> SurfaceAssessment:
        if type(response) is not ResponseMeaning:
            raise TypeError("surface oracle requires exact ResponseMeaning")
        if ResponseMeaning.from_dict(response.as_dict()) != response:
            raise ValueError("noncanonical response meaning")
        if type(candidate) is not str:
            raise TypeError("candidate surface must be text")
        if type(session_ref) is not str or not session_ref:
            raise TypeError("session_ref must be nonempty")
        pin = self._runtime.stores.revision_pin()
        candidate_ref = stable_ref(
            "candidate_surface", {"response": response.response_meaning_ref, "text": candidate},
        )

        def rejected(reason: str, parsed: str | None = None) -> SurfaceAssessment:
            return SurfaceAssessment(
                False, reason, response.response_meaning_ref,
                candidate_ref, parsed, pin.world_revision,
            )

        if pin.authority_generation != response.revision_pin.authority_generation:
            return rejected("authority_generation_changed")
        if pin.model_identity != response.revision_pin.model_identity:
            return rejected("proposal_model_changed")
        if pin.world_revision != response.revision_pin.world_revision:
            return rejected("world_evidence_stale")
        if not (
            response.mode.value == "QUERY"
            and response.discourse_action == "answer"
            and response.epistemic_status_ref == "epistemic_status:supported"
            and response.polarity_ref == "polarity:positive"
            and response.modality_ref == "modality:actual"
            and bool(response.proof_refs)
            and not response.blocker_refs
            and not response.response_expression.scope_operators
            and not response.response_expression.expression_links
            and not response.response_expression.binders
            and not response.response_expression.unresolved_fillers
        ):
            return rejected("response_not_admitted_for_reference_surface")
        if (
            not candidate or len(candidate) > 512
            or "\n" in candidate or "\r" in candidate
            or candidate != candidate.strip()
        ):
            return rejected("invalid_candidate_geometry")

        # Verification by the SAME canonical source interpreter, not lexical
        # keywords or template family membership. Distinct sentence content,
        # relation direction, referents, modality and scopes never collapse.
        try:
            verification = self._runtime.verify_surface_read_only(
                session_ref, candidate,
            )
        except (TypeError, ValueError):
            return rejected("surface_unresolved")
        if verification.status != "selected" or verification.selected_meaning is None:
            return rejected("surface_unresolved")
        parsed = verification.selected_meaning.expression.expression_ref
        if parsed != response.response_expression.expression_ref:
            return rejected("canonical_expression_mismatch", parsed)
        if self._runtime.stores.revision_pin() != pin:
            raise RuntimeError("semantic surface oracle changed persistent state")
        return SurfaceAssessment(
            True, "canonical_expression_equal", response.response_meaning_ref,
            candidate_ref, parsed, pin.world_revision,
        )
