"""A deliberately restricted, verified reference English output constructor.

This is NOT a production R5 generator. It constructs a single reviewed
subject–predicate–object English clause from *grounded semantic role data*
and the authoritative reverse designation index. It cannot invent words,
roles, tense, modality, attribution or world claims. Every candidate must
re-enter ORIENT/PROPOSE/VERIFY read-only and reproduce the bound answer graph
at the exact same world/session/effect revision. Otherwise no surface escapes.

No phrase-specific case handling, internal-ref lexicalization, or neural
token generation occurs here; grammar scope is ONE reviewed binary relation.
"""
from __future__ import annotations

from dataclasses import dataclass
import re

from .expressions import GroundedReference
from .r3_response import ResponseMeaning
from .runtime import HybridRuntime
from .surface_equivalence import SemanticSurfaceOracle, SurfaceAssessment


@dataclass(frozen=True, slots=True)
class ReferenceGeneration:
    status: str
    reason: str
    surface: str | None
    response_meaning_ref: str
    proof_refs: tuple[str, ...]
    assessment: SurfaceAssessment | None

    def __post_init__(self) -> None:
        if self.status not in {"verified", "unadmitted"}:
            raise ValueError("unsupported reference generation status")
        if type(self.reason) is not str or not self.reason:
            raise ValueError("reference generation requires a typed reason")
        if self.status == "verified":
            if (
                not self.surface or self.assessment is None
                or not self.assessment.equivalent
                or self.reason != "canonical_expression_equal"
                or self.assessment.response_meaning_ref != self.response_meaning_ref
                or not self.proof_refs
            ):
                raise ValueError("verified generation lacks exact equivalence and proof")
        elif self.surface is not None:
            raise ValueError("unadmitted output must not contain a user-visible surface")


class ReferenceRelationGenerator:
    """Stateless bounded reference generator; has NO world/effect write port."""

    def __init__(self, runtime: HybridRuntime) -> None:
        if type(runtime) is not HybridRuntime:
            raise TypeError("reference generator requires canonical HybridRuntime")
        self._runtime = runtime
        self._designations = runtime.authority.designations
        self._atoms = runtime.authority.atoms
        self._oracle = SemanticSurfaceOracle(runtime)

    def _safe_reviewed_surfaces(self, ref: str) -> tuple[str, ...]:
        facts = self._designations.facts_for_target(ref, "en")
        approved: set[str] = set()
        for fact in facts:
            word = fact.surface
            # One word only, explicitly reviewed for the target. Capitalized
            # proper nouns are admissible only if reviewed AS capitalized.
            if re.fullmatch(r"[A-Za-z]+", word) is None:
                continue
            exact = self._designations.facts_for_surface(word, "en")
            if len(exact) != 1 or exact[0].target_ref != ref:
                continue
            approved.add(word)
        return tuple(sorted(approved, key=lambda w: (len(w), w.casefold(), w)))

    def _entity(self, ref: str, *, first: bool) -> str | None:
        atom = self._atoms.get(ref)
        if atom is None or atom.kind != "entity" or atom.reviewed is not True:
            return None
        options = self._safe_reviewed_surfaces(ref)
        proper = tuple(
            word for word in options
            if word[:1].isupper() and word[1:].islower()
        )
        if proper:
            return proper[0]
        common = tuple(word for word in options if word.islower())
        if common:
            return ("The " if first else "the ") + common[0]
        return None

    def _relation(self, ref: str) -> str | None:
        atom = self._atoms.get(ref)
        if atom is None or atom.kind != "relation_type" or atom.reviewed is not True:
            return None
        # This baseline admits only reviewed English third-person present
        # relational predicates already spelled in inflected finite form.
        # Other verb inflections and multiword predicates are R5 work.
        candidates = tuple(
            word for word in self._safe_reviewed_surfaces(ref)
            if re.fullmatch(r"[a-z]+s", word) is not None
        )
        return candidates[0] if candidates else None

    def generate(self, response: ResponseMeaning, session_ref: str) -> ReferenceGeneration:
        if type(response) is not ResponseMeaning:
            raise TypeError("reference output requires canonical ResponseMeaning")
        if ResponseMeaning.from_dict(response.as_dict()) != response:
            raise ValueError("noncanonical ResponseMeaning")

        def denied(reason: str, assessment=None) -> ReferenceGeneration:
            return ReferenceGeneration(
                "unadmitted", reason, None,
                response.response_meaning_ref, response.proof_refs, assessment,
            )

        expression = response.response_expression
        if not (
            response.mode.value == "QUERY"
            and response.discourse_action == "answer"
            and response.epistemic_status_ref == "epistemic_status:supported"
            and response.polarity_ref == "polarity:positive"
            and response.modality_ref == "modality:actual"
            and bool(response.proof_refs)
            and not response.blocker_refs
            and len(expression.applications) == 1
            and len(expression.root_refs) == 1
            and not expression.scope_operators
            and not expression.expression_links
            and not expression.binders
            and not expression.unresolved_fillers
        ):
            return denied("reference_fragment_not_admitted")
        app = expression.applications[0]
        if (
            app.operator != "op:relation"
            or expression.root_refs != (app.application_ref,)
            or app.qualifiers
            or len(app.roles) != 2
        ):
            return denied("reference_relation_not_admitted")
        roles = {row.role_ref: row.filler for row in app.roles}
        if set(roles) != {"role:subject", "role:object"} or any(
            type(filler) is not GroundedReference for filler in roles.values()
        ):
            return denied("reference_grounding_not_admitted")

        subject = self._entity(roles["role:subject"].target_ref, first=True)
        object_text = self._entity(roles["role:object"].target_ref, first=False)
        verb = self._relation(app.predicate_ref)
        if subject is None or object_text is None or verb is None:
            return denied("reviewed_language_forms_missing")

        candidate = f"{subject} {verb} {object_text}."
        checked = self._oracle.assess(
            response=response, session_ref=session_ref, candidate=candidate,
        )
        if not checked.equivalent:
            return denied("generated_surface_not_semantically_equivalent", checked)
        return ReferenceGeneration(
            "verified", "canonical_expression_equal", candidate,
            response.response_meaning_ref, response.proof_refs, checked,
        )
