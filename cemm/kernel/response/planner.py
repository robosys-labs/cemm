"""ResponsePlanner — sole public-content authority.

Import boundary: model + epistemics submodules only. No engine imports.

Architectural guardrails (AGENTS.md §19, CORE_LOOP.md G1-G2,
AUTHORITY_MATRIX):
- ResponsePlanner is the only response-content authority.
- It consumes selected semantic propositions, epistemic/capability
  assessments, execution outcomes, commit outcomes, goals, and discourse
  state. It produces a language-neutral SemanticMessagePlan.
- Response content begins from propositions, assessments, ledger, and
  commit outcomes — not from raw text or templates.
- Language renderers choose wording, not truth or response content.
- NLG may not decide truth, capability, schema activation, or response
  content selection.
- Templates, renderer, and raw input must not decide response content.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..model.message import (
    SemanticMessagePlan, MessageContentItem, RhetoricalRelation,
)
from ..model.epistemic import EpistemicAssessment
from ..model.execution import OperationOutcome, ExecutionLedger
from ..model.mutation import CommitOutcome


class EpistemicStance(str, Enum):
    """Epistemic stance for qualified language.

    Implements qualified language for:
    - reported theory
    - provisional understanding
    - contested evidence
    - known limitations
    - stale/repaired prior claims
    """
    ASSERTED = "asserted"               # actual-world admitted knowledge
    REPORTED = "reported"               # reported theory / attributed claim
    PROVISIONAL = "provisional"         # provisional understanding
    CONTESTED = "contested"             # contested evidence
    HEDGED = "hedged"                   # known limitations / uncertainty
    STALE = "stale"                     # stale/repaired prior claims
    DENIED = "denied"                   # refuted or blocked


class DiscourseFunction(str, Enum):
    """Discourse function for content items."""
    INFORM = "inform"
    QUERY = "query"
    REQUEST = "request"
    ACKNOWLEDGE = "acknowledge"
    CORRECT = "correct"
    PROMISE = "promise"
    REFUSE = "refuse"
    REPAIR = "repair"


@dataclass(frozen=True, slots=True)
class ContentSelectionInput:
    """Input to response content selection.

    ResponsePlanner consumes selected semantic propositions,
    epistemic/capability assessments, execution outcomes, commit outcomes,
    goals, and discourse state.
    """
    proposition_refs: tuple[str, ...] = ()
    assessments: tuple[EpistemicAssessment, ...] = ()
    commit_outcome: CommitOutcome | None = None
    execution_ledger: ExecutionLedger | None = None
    goal_refs: tuple[str, ...] = ()
    discourse_state_refs: tuple[str, ...] = ()
    repair_obligation_refs: tuple[str, ...] = ()
    addressee_ref: str = ""
    language: str = "und"
    channel: str = "text"


class ResponsePlanner:
    """Sole response-content authority.

    ResponsePlanner is the only response-content authority.
    It produces a language-neutral SemanticMessagePlan from
    propositions, assessments, ledger, and commit outcomes.

    Does NOT:
    - Choose wording (that's the language renderer's job)
    - Decide truth
    - Decide capability
    - Decide schema activation
    - Use templates or raw input for content selection
    """

    def plan_response(
        self,
        selection: ContentSelectionInput,
    ) -> SemanticMessagePlan:
        """Plan a response from selected semantic content.

        Response content begins from propositions, assessments, ledger,
        and commit outcomes — not from raw text or templates.
        """
        content_items: list[MessageContentItem] = []
        rhetorical_relations: list[RhetoricalRelation] = []

        # 1. Select content from propositions with epistemic qualification
        for i, prop_ref in enumerate(selection.proposition_refs):
            assessment = self._find_assessment(
                prop_ref, selection.assessments
            )
            stance = self._derive_stance(assessment)
            discourse_fn = self._derive_discourse_function(assessment)

            item = MessageContentItem(
                semantic_ref=prop_ref,
                discourse_function=discourse_fn.value,
                stance=stance.value,
                focus="",
                required=True,
                provenance_refs=self._collect_provenance(
                    prop_ref, assessment, selection
                ),
            )
            content_items.append(item)

        # 2. Add commit outcome content if present
        if selection.commit_outcome is not None:
            commit_item = self._plan_commit_content(
                selection.commit_outcome, selection
            )
            if commit_item is not None:
                content_items.append(commit_item)

        # 3. Add repair content if needed
        if selection.repair_obligation_refs:
            for repair_ref in selection.repair_obligation_refs:
                repair_item = MessageContentItem(
                    semantic_ref=repair_ref,
                    discourse_function=DiscourseFunction.REPAIR.value,
                    stance=EpistemicStance.STALE.value,
                    focus="prior_claim",
                    required=True,
                    provenance_refs=(repair_ref,),
                )
                content_items.append(repair_item)

        # 4. Build rhetorical relations (simple ordering for now)
        for i in range(1, len(content_items)):
            rhetorical_relations.append(RhetoricalRelation(
                source_item_ref=content_items[i - 1].semantic_ref,
                target_item_ref=content_items[i].semantic_ref,
                relation_kind="elaboration",
            ))

        return SemanticMessagePlan(
            id=f"msg_plan:{id(selection)}",
            communicative_goal_refs=selection.goal_refs,
            content_items=tuple(content_items),
            rhetorical_relations=tuple(rhetorical_relations),
            addressee_refs=(selection.addressee_ref,) if selection.addressee_ref else (),
            language=selection.language,
            channel=selection.channel,
        )

    def _find_assessment(
        self,
        proposition_ref: str,
        assessments: tuple[EpistemicAssessment, ...],
    ) -> EpistemicAssessment | None:
        """Find the assessment for a proposition."""
        for a in assessments:
            if a.proposition_ref == proposition_ref:
                return a
        return None

    def _derive_stance(
        self,
        assessment: EpistemicAssessment | None,
    ) -> EpistemicStance:
        """Derive epistemic stance from an assessment.

        Implements qualified language for:
        - reported theory → REPORTED
        - provisional understanding → PROVISIONAL
        - contested evidence → CONTESTED
        - known limitations → HEDGED
        - stale/repaired prior claims → STALE
        """
        if assessment is None:
            return EpistemicStance.ASSERTED  # Default

        # Check admissibility — blocked is strongest (can't use at all)
        if assessment.admissibility == "blocked":
            return EpistemicStance.DENIED

        # Check support state — refutation overrides admissibility level
        if assessment.support_state == "refuted":
            return EpistemicStance.DENIED
        if assessment.support_state == "both":
            return EpistemicStance.CONTESTED
        if assessment.support_state == "neither":
            return EpistemicStance.HEDGED

        # Check admissibility — contested/attributed after support state
        if assessment.admissibility == "contested":
            return EpistemicStance.CONTESTED
        if assessment.admissibility == "attributed_only":
            return EpistemicStance.REPORTED

        # Check confidence
        if assessment.confidence < 0.5:
            return EpistemicStance.HEDGED

        # Check schema use validity
        if not assessment.schema_use_valid:
            return EpistemicStance.PROVISIONAL

        return EpistemicStance.ASSERTED

    def _derive_discourse_function(
        self,
        assessment: EpistemicAssessment | None,
    ) -> DiscourseFunction:
        """Derive discourse function from assessment."""
        if assessment is None:
            return DiscourseFunction.INFORM

        if assessment.admissibility == "blocked":
            return DiscourseFunction.REFUSE
        if assessment.support_state == "refuted":
            return DiscourseFunction.CORRECT

        return DiscourseFunction.INFORM

    def _collect_provenance(
        self,
        prop_ref: str,
        assessment: EpistemicAssessment | None,
        selection: ContentSelectionInput,
    ) -> tuple[str, ...]:
        """Collect provenance refs for a content item.

        Every generated clause must trace to a selected semantic item
        and evidence/ledger/commit provenance.
        """
        refs: list[str] = [prop_ref]
        if assessment is not None:
            refs.extend(assessment.explanation_refs)
        return tuple(refs)

    def _plan_commit_content(
        self,
        commit_outcome: CommitOutcome,
        selection: ContentSelectionInput,
    ) -> MessageContentItem | None:
        """Plan content from commit outcomes.

        A response may say "I stored it," "I learned it," "I changed it,"
        or "I completed it" only when every required mutation for that
        claim committed.
        """
        if not commit_outcome.required_satisfied:
            # Required commits failed — response must not claim success
            return MessageContentItem(
                semantic_ref=commit_outcome.mutation_set_ref,
                discourse_function=DiscourseFunction.ACKNOWLEDGE.value,
                stance=EpistemicStance.DENIED.value,
                focus="commit_failure",
                required=True,
                provenance_refs=(commit_outcome.mutation_set_ref,),
            )

        # Required commits succeeded
        return MessageContentItem(
            semantic_ref=commit_outcome.mutation_set_ref,
            discourse_function=DiscourseFunction.INFORM.value,
            stance=EpistemicStance.ASSERTED.value,
            focus="commit_success",
            required=True,
            provenance_refs=(commit_outcome.mutation_set_ref,),
        )
