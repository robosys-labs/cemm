"""ActResolutionPlanner - turn multi-act and meaning-group packets into tasks.

ConversationActPacket preserves pragmatic acts, while MeaningPerceptPacket
preserves semantic groups and predicate outcomes. This planner joins both
views into operational obligations:

* reply obligations
* memory update plans
* answer tasks
* safety tasks
* ignored/deferred acts

The planner is deterministic first and traceable enough to become a supervised
target for a later small decision model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

try:
    from ...registry.act_type_policy import get_response_mode
except ModuleNotFoundError:  # pragma: no cover - partial scratch checkouts.
    def get_response_mode(_act_type: str) -> str:
        return ""
from ...types.conversation_act import ConversationAct, ConversationActPacket
from ...types.meaning_percept import MeaningAtomOutcome, MeaningGroup, MeaningPerceptPacket, RetrievalPlan, SafetyFrame, SituationFrame
from .entity_fact_extractor import EntityFactCandidate


@dataclass
class ReplyObligation:
    """A user-facing response obligation created by an act or meaning group."""

    act_type: str
    response_mode: str
    priority: int
    intent: str
    reason: str = ""
    requires_evidence: bool = False
    allowed_creativity: bool = False
    confidence: float = 0.5
    obligation_kind: str = "reply"
    evidence_policy: str = "none"
    group_id: str = ""
    predicate_id: str = ""
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryUpdatePlan:
    """A proposed memory write, not an executed mutation."""

    write_kind: str
    candidates: list[EntityFactCandidate] = field(default_factory=list)
    act_type: str = ""
    permission_scope: str = "public"
    confidence: float = 0.5
    reason: str = ""
    group_id: str = ""
    predicate_id: str = ""
    freshness: str = "speaker_asserted"
    should_confirm: bool = False
    uol_atom_ids: list[str] = field(default_factory=list)
    uol_edge_ids: list[str] = field(default_factory=list)
    graph_patch_ids: list[str] = field(default_factory=list)


@dataclass
class AnswerTask:
    """Internal answer task produced by act resolution."""

    response_mode: str
    intent: str
    selected_act_type: str
    retrieval_mode: str = "none"
    params: dict[str, Any] = field(default_factory=dict)
    priority: int = 50
    confidence: float = 0.5
    evidence_policy: str = "none"
    group_id: str = ""
    predicate_id: str = ""


@dataclass
class SafetyTask:
    """Safety task that can override normal answer behavior."""

    category: str
    response_mode: str
    severity: str
    must_not_do: list[str] = field(default_factory=list)
    confidence: float = 0.5


@dataclass
class IgnoredAct:
    """An act intentionally ignored or deferred with a trace reason."""

    act_type: str
    reason: str


@dataclass
class RejectedPath:
    """A rejected candidate path retained for learning feedback."""

    candidate_set_id: str
    atom_id: str
    atom_kind: str
    atom_key: str
    surface: str
    confidence: float
    reason: str
    evidence_refs: list[str] = field(default_factory=list)


@dataclass
class SelectedPath:
    """The selected interpretation path for a candidate set."""

    candidate_set_id: str
    atom_id: str
    atom_kind: str
    atom_key: str
    surface: str
    confidence: float
    reason: str
    group_id: str = ""


@dataclass
class ActResolutionPlan:
    """Operational plan for all acts and meaning groups in one turn."""

    obligations: list[ReplyObligation] = field(default_factory=list)
    memory_updates: list[MemoryUpdatePlan] = field(default_factory=list)
    graph_patch_candidates: list[Any] = field(default_factory=list)
    answer_tasks: list[AnswerTask] = field(default_factory=list)
    safety_tasks: list[SafetyTask] = field(default_factory=list)
    ignored_acts: list[IgnoredAct] = field(default_factory=list)
    group_plans: list[dict[str, Any]] = field(default_factory=list)
    unresolved_groups: list[str] = field(default_factory=list)
    selected_response_mode: str = "general_conversation"
    selected_intent: str = "general_conversation"
    requires_retrieval: bool = False
    retrieval_mode: str = "none"
    should_abstain: bool = False
    abstention_reason: str = ""
    response_contract: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.5
    selected_paths: list[SelectedPath] = field(default_factory=list)
    rejected_paths: list[RejectedPath] = field(default_factory=list)


class ActResolutionPlanner:
    """Resolve ConversationActPacket and MeaningPerceptPacket into tasks."""

    _PRIORITY = {
        "self_harm": 100,
        "safety": 95,
        "session_exit": 92,
        "frustration_signal": 90,
        "confusion_repair": 88,
        "retrospective_repair": 88,
        "playful_repair": 82,
        "fresh_world_query": 78,
        "self_capability_query": 75,
        "capability_query": 75,
        "self_identity_query": 72,
        "self_category_query": 72,
        "self_knowledge_query": 72,
        "user_identity_query": 72,
        "user_name_query": 72,
        "open_domain_entity_query": 70,
        "evidence_query": 68,
        "memory_query": 68,
        "teaching_offer": 66,
        "definition_teaching": 64,
        "command_alias_teaching": 64,
        "story_request": 62,
        "creative_request": 62,
        "state_report": 58,
        "reciprocal_phatic_checkin": 58,
        "assistant_evaluation": 57,
        "playful_acknowledgment": 56,
        "phatic_checkin": 55,
        "greeting": 50,
        "command_request": 45,
        "question": 45,
        "semantic_disambiguation": 46,
        "acknowledgment": 35,
        "claim_assertion": 30,
        "preference_assertion": 30,
    }

    _MEMORY_ACTS = {
        "claim_assertion",
        "preference_assertion",
        "definition_teaching",
        "command_alias_teaching",
        "explicit_remember",
    }

    _NO_EVIDENCE_ACTS = {
        "greeting",
        "acknowledgment",
        "playful_acknowledgment",
        "phatic_checkin",
        "reciprocal_phatic_checkin",
        "user_state_report",
        "assistant_evaluation",
        "general_conversation",
        "chat_mode_statement",
        "frustration_signal",
        "confusion_repair",
        "retrospective_repair",
        "playful_repair",
        "session_exit",
        "self_capability_query",
        "capability_query",
    }

    def plan(
        self,
        conversation_act: ConversationActPacket | None = None,
        situation: SituationFrame | None = None,
        safety_frame: SafetyFrame | None = None,
        fact_candidates: list[EntityFactCandidate] | None = None,
        meaning_percept: MeaningPerceptPacket | None = None,
        retrieval_plan: RetrievalPlan | None = None,
    ) -> ActResolutionPlan:
        result = ActResolutionPlan()
        facts = list(fact_candidates or [])

        if safety_frame and safety_frame.category != "none":
            self._add_safety_override(result, safety_frame)

        acts = conversation_act.all_acts if conversation_act else [ConversationAct()]
        for act in acts:
            self._resolve_act(act, result, retrieval_plan, facts)

        if meaning_percept is not None:
            result.graph_patch_candidates.extend(
                getattr(meaning_percept, "graph_patch_candidates", []) or []
            )
            self._resolve_meaning_groups(meaning_percept, result, facts)

        act_types = set(conversation_act.act_types) if conversation_act else set()
        teachable_facts = self._teachable_facts(facts, act_types)
        if teachable_facts and not self._has_fact_memory_update(result):
            result.memory_updates.append(MemoryUpdatePlan(
                write_kind="claim",
                candidates=teachable_facts,
                act_type="claim_assertion",
                confidence=self._avg_fact_confidence(teachable_facts),
                reason="speaker_asserted_fact_candidate",
                should_confirm=False,
            ))
            self._add_obligation(result, ReplyObligation(
                act_type="claim_assertion",
                response_mode="social_response",
                priority=89,
                intent="remember",
                reason="acknowledge_speaker_asserted_fact",
                confidence=self._avg_fact_confidence(teachable_facts),
                evidence_policy="none",
            ))        

        if not result.obligations and not result.memory_updates and facts:
            result.memory_updates.append(MemoryUpdatePlan(
                write_kind="claim",
                candidates=facts,
                act_type="inferred_claim_assertion",
                confidence=self._avg_fact_confidence(facts),
                reason="fact_candidates_without_explicit_act",
            ))
            self._add_obligation(result, ReplyObligation(
                act_type="memory_write",
                response_mode="social_response",
                priority=25,
                intent="remember",
                reason="acknowledge_fact_learning",
                confidence=0.6,
                evidence_policy="none",
            ))

        self._dedupe_plan(result)
        self._merge_hypotheses(result)
        self._resolve_competing_obligations(result)
        self._select_answer_task(result, retrieval_plan, meaning_percept)
        return result

    def _add_safety_override(
        self, result: ActResolutionPlan, safety_frame: SafetyFrame
    ) -> None:
        safety_task = SafetyTask(
            category=safety_frame.category,
            response_mode=safety_frame.allowed_response_mode or "safe_info",
            severity=safety_frame.severity,
            must_not_do=list(safety_frame.must_not_do),
            confidence=safety_frame.confidence,
        )
        result.safety_tasks.append(safety_task)
        self._add_obligation(result, ReplyObligation(
            act_type="safety",
            response_mode=safety_task.response_mode,
            priority=self._PRIORITY["safety"],
            intent=safety_frame.category,
            reason="safety_frame_override",
            confidence=safety_frame.confidence,
            evidence_policy="none",
        ))

    def _resolve_act(
        self,
        act: ConversationAct,
        result: ActResolutionPlan,
        retrieval_plan: RetrievalPlan | None,
        fact_candidates: list[EntityFactCandidate],
    ) -> None:
        act_type = act.act_type
        if act_type == "unknown":
            result.ignored_acts.append(
                IgnoredAct(act_type=act_type, reason="unknown_act_waiting_for_meaning_groups")
            )
            return

        if act_type in self._MEMORY_ACTS:
            if fact_candidates:
                result.memory_updates.append(MemoryUpdatePlan(
                    write_kind=self._write_kind_for_act(act_type),
                    candidates=fact_candidates,
                    act_type=act_type,
                    confidence=max(act.confidence, self._avg_fact_confidence(fact_candidates)),
                    reason=f"act_type={act_type}",
                ))
                self._add_obligation(result, ReplyObligation(
                    act_type=act_type,
                    response_mode="social_response",
                    priority=self._PRIORITY.get(act_type, 40),
                    intent="remember",
                    reason="acknowledge_memory_candidate",
                    confidence=max(act.confidence, self._avg_fact_confidence(fact_candidates)),
                    evidence_policy="none",
                ))
            else:
                result.ignored_acts.append(IgnoredAct(
                    act_type=act_type,
                    reason="memory_act_without_fact_candidates",
                ))
            return

        response_mode = get_response_mode(act_type) or act.response_mode
        priority = self._PRIORITY.get(act_type, 40)
        allowed_creativity = act.is_creative
        evidence_policy = self._evidence_policy_for_act(act_type, act.requires_evidence)
        requires_evidence = evidence_policy not in {"none", "optional"}
        intent = self._intent_for_act(act_type, response_mode)
        retrieval_mode = self._retrieval_mode_for_policy(evidence_policy, retrieval_plan)

        self._add_obligation(result, ReplyObligation(
            act_type=act_type,
            response_mode=response_mode,
            priority=priority,
            intent=intent,
            reason=f"act_type={act_type}",
            requires_evidence=requires_evidence,
            allowed_creativity=allowed_creativity,
            confidence=act.confidence,
            evidence_policy=evidence_policy,
        ))

        result.answer_tasks.append(AnswerTask(
            response_mode=response_mode,
            intent=intent,
            selected_act_type=act_type,
            retrieval_mode=retrieval_mode,
            priority=priority,
            confidence=act.confidence,
            evidence_policy=evidence_policy,
        ))

    def _resolve_meaning_groups(
        self,
        percept: MeaningPerceptPacket,
        result: ActResolutionPlan,
        fact_candidates: list[EntityFactCandidate],
    ) -> None:
        facts_by_group = self._facts_by_group(fact_candidates)
        graph = getattr(percept, "uol_graph", None)
        outcomes_by_group = self._outcomes_by_group(percept)
        for group in percept.meaning_groups:
            intent_key = self._graph_intent_for_group(graph, group) or (
                group.intents[0].intent_key if group.intents else group.group_type
            )
            group_facts = facts_by_group.get(group.id, [])
            summary = {
                "group_id": group.id,
                "surface": group.surface,
                "intent": intent_key,
                "parent_group_id": group.parent_group_id,
                "relation_to_parent": group.relation_to_parent,
                "predicate_ids": list(group.predicate_ids),
                "outcome_ids": list(group.outcome_ids),
                "uol_atom_ids": (
                    [atom.id for atom in graph.group_atoms(group.id)] if graph else []
                ),
                "uol_edge_ids": (
                    [edge.id for edge in graph.group_edges(group.id)] if graph else []
                ),
                "port_binding_count": len([
                    binding for binding in getattr(graph, "port_bindings", [])
                    if getattr(graph.atoms.get(binding.owner_atom_id), "group_id", "") == group.id
                ]) if graph else 0,
                "affordance_prediction_count": len([
                    prediction for prediction in getattr(graph, "affordance_predictions", [])
                    if any(
                        getattr(graph.atoms.get(atom_id), "group_id", "") == group.id
                        for atom_id in prediction.trigger_atom_ids
                    )
                ]) if graph else 0,
                "graph_patch_candidate_ids": [
                    patch.id for patch in self._patches_for_group(graph, group.id)
                ] if graph else [],
                "candidate_set_ids": [
                    cs.id for cs in self._candidate_sets_for_group(graph, group.id)
                ] if graph else [],
                "ambiguous_candidate_set_count": len([
                    cs for cs in self._candidate_sets_for_group(graph, group.id)
                    if len(getattr(cs, "candidate_atom_ids", [])) > 1
                ]) if graph else 0,
            }
            result.group_plans.append(summary)

            self._resolve_candidate_sets(
                result, group, self._candidate_sets_for_group(graph, group.id), graph
            )
            self._resolve_group_outcomes(
                result, group, outcomes_by_group.get(group.id, [])
            )
            self._select_and_track_paths(
                result, group, self._candidate_sets_for_group(graph, group.id), graph
            )

            if intent_key == "session_exit":
                self._add_group_obligation(
                    result, group, "session_exit", "social_response", "session_exit", 92, "none"
                )
            elif intent_key == "repair":
                self._add_group_obligation(
                    result, group, "retrospective_repair", "repair_response", "retrospective_repair", 88, "none"
                )
            elif intent_key == "fresh_world_query":
                self._add_group_obligation(
                    result, group, "evidence_query", "live_info_boundary", "fresh_world_query", 78, "tool_required"
                )
            elif intent_key == "capability_query":
                self._add_group_obligation(
                    result, group, "self_capability_query", "capability_summary", "capability_summary", 75, "none"
                )
            elif intent_key == "self_identity_query":
                self._add_group_obligation(
                    result, group, "self_identity_query", "self_identity", "self_identity", 72, "required"
                )
            elif intent_key == "self_knowledge_query":
                self._add_group_obligation(
                    result, group, "self_knowledge_query", "evidence_answer", "self_knowledge_query", 72, "required"
                )
            elif intent_key == "user_profile_query":
                self._add_group_obligation(
                    result, group, "user_profile_query", "evidence_answer", "user_profile_query", 72, "required"
                )
            elif intent_key == "teaching":
                self._resolve_teaching_group(
                    result, group, group_facts or fact_candidates, graph
                )
            elif intent_key == "user_state_report":
                self._add_group_obligation(
                    result, group, "state_report", "social_response", "chat_mode_statement", 34, "none"
                )
            elif intent_key == "greeting":
                self._add_group_obligation(
                    result, group, "greeting", "social_response", "greeting", 50, "none"
                )
            elif intent_key == "acknowledgment":
                self._add_group_obligation(
                    result, group, "acknowledgment", "social_response", "acknowledgment", 35, "none"
                )
            elif intent_key == "question":
                self._add_group_obligation(
                    result, group, "question", "general_conversation", "general_conversation", 45, "optional"
                )
            elif intent_key == "command":
                self._add_group_obligation(
                    result, group, "command_request", "general_conversation", "command_resolution", 45, "optional"
                )
            else:
                result.unresolved_groups.append(group.id)

    def _graph_intent_for_group(
        self, graph: Any, group: MeaningGroup
    ) -> str:
        if graph is None:
            return ""
        intent_atoms = graph.atoms_by_kind("intent", group.id)
        intent_keys = {atom.key for atom in intent_atoms}
        if graph.has_edge("asks_about", source_kind="intent", target_kind="evidence", group_id=group.id):
            return "fresh_world_query"
        if graph.has_edge("teaches", source_kind="source", group_id=group.id):
            return "teaching"
        if "repair" in intent_keys:
            return "repair"
        if "session_exit" in intent_keys:
            return "session_exit"
        if "capability_query" in intent_keys:
            return "capability_query"
        if "self_identity_query" in intent_keys or "self_category_query" in intent_keys:
            return "self_identity_query"
        if "self_knowledge_query" in intent_keys:
            return "self_knowledge_query"
        if "user_profile_query" in intent_keys or "user_name_query" in intent_keys:
            return "user_profile_query"
        if "fresh_world_query" in intent_keys:
            return "fresh_world_query"
        if "user_state_report" in intent_keys:
            return "user_state_report"
        if "greeting" in intent_keys:
            return "greeting"
        if "acknowledgment" in intent_keys:
            return "acknowledgment"
        if "command" in intent_keys:
            return "command"
        if "question" in intent_keys or graph.has_edge("asks_about", source_kind="intent", group_id=group.id):
            return "question"
        return ""

    def _resolve_teaching_group(
        self,
        result: ActResolutionPlan,
        group: MeaningGroup,
        facts: list[EntityFactCandidate],
        graph: Any = None,
    ) -> None:
        if facts:
            result.memory_updates.append(MemoryUpdatePlan(
                write_kind="claim",
                candidates=facts,
                act_type="definition_teaching",
                confidence=max(group.confidence, self._avg_fact_confidence(facts)),
                reason="meaning_group_teaching",
                group_id=group.id,
                predicate_id=group.predicate_ids[0] if group.predicate_ids else "",
                should_confirm=False,
                uol_atom_ids=(
                    [atom.id for atom in graph.group_atoms(group.id)] if graph else []
                ),
                uol_edge_ids=(
                    [edge.id for edge in graph.group_edges(group.id)] if graph else []
                ),
                graph_patch_ids=(
                    [patch.id for patch in self._patches_for_group(graph, group.id)] if graph else []
                ),
            ))
            self._add_group_obligation(
                result, group, "definition_teaching", "social_response", "remember", 64, "none"
            )
        elif (
            graph is not None
            and graph.has_edge("teaches", source_kind="source", target_kind="relation", group_id=group.id)
        ):
            result.memory_updates.append(MemoryUpdatePlan(
                write_kind="graph_patch_candidate",
                candidates=[],
                act_type="definition_teaching",
                confidence=max(group.confidence, 0.68),
                reason="graph_patch_teaching_relation",
                group_id=group.id,
                predicate_id=group.predicate_ids[0] if group.predicate_ids else "",
                should_confirm=False,
                uol_atom_ids=[atom.id for atom in graph.group_atoms(group.id)],
                uol_edge_ids=[edge.id for edge in graph.group_edges(group.id)],
                graph_patch_ids=[patch.id for patch in self._patches_for_group(graph, group.id)],
            ))
            self._add_group_obligation(
                result, group, "definition_teaching", "social_response", "remember", 64, "none"
            )
        else:
            self._add_group_obligation(
                result, group, "teaching_offer", "teaching_prompt", "teaching_clarification", 64, "none"
            )

    def _resolve_group_outcomes(
        self,
        result: ActResolutionPlan,
        group: MeaningGroup,
        outcomes: list[MeaningAtomOutcome],
    ) -> None:
        for outcome in outcomes:
            if outcome.expected_change == "fresh_evidence_required":
                self._add_group_obligation(
                    result, group, "evidence_query", "live_info_boundary", "fresh_world_query", 78,
                    "tool_required", predicate_id=outcome.predicate_id,
                )
            elif outcome.expected_change == "candidate_memory_update":
                result.memory_updates.append(MemoryUpdatePlan(
                    write_kind="graph_patch_candidate",
                    candidates=[],
                    act_type="definition_teaching",
                    confidence=max(group.confidence, outcome.confidence),
                    reason="meaning_outcome_candidate_memory_update",
                    group_id=group.id,
                    predicate_id=outcome.predicate_id,
                    should_confirm=False,
                ))
            elif outcome.expected_change == "clarity_required":
                self._add_group_obligation(
                    result, group, "retrospective_repair", "repair_response", "retrospective_repair", 88,
                    "none", predicate_id=outcome.predicate_id,
                )
            elif outcome.expected_change == "reply_obligation":
                self._add_group_obligation(
                    result, group,
                    "question" if outcome.atom_kind == "intent" else "claim_assertion",
                    "general_conversation",
                    "general_conversation" if outcome.atom_kind == "intent" else "chat_mode_statement",
                    45, "optional", predicate_id=outcome.predicate_id,
                )

    def _resolve_candidate_sets(
        self,
        result: ActResolutionPlan,
        group: MeaningGroup,
        candidate_sets: list[Any],
        graph: Any,
    ) -> None:
        for candidate_set in candidate_sets:
            candidate_atom_ids = list(getattr(candidate_set, "candidate_atom_ids", []) or [])
            if len(candidate_atom_ids) <= 1:
                continue
            candidate_atoms = [
                graph.atoms[atom_id] for atom_id in candidate_atom_ids
                if graph is not None and atom_id in getattr(graph, "atoms", {})
            ]
            kinds = {atom.features.get("interpretation_kind") for atom in candidate_atoms}
            if "act" in kinds:
                for atom in candidate_atoms:
                    act_type = atom.features.get("candidate_act_type") or atom.key
                    if not act_type:
                        continue
                    response_mode = get_response_mode(str(act_type)) or "general_conversation"
                    intent = self._intent_for_act(str(act_type), response_mode)
                    self._add_obligation(result, ReplyObligation(
                        act_type=str(act_type),
                        response_mode=response_mode,
                        priority=max(20, self._PRIORITY.get(str(act_type), 40) - 25),
                        intent=intent,
                        reason=f"candidate_set:{candidate_set.id}",
                        confidence=min(0.65, atom.confidence),
                        evidence_policy="optional",
                        group_id=group.id,
                        params={
                            "candidate_set_id": candidate_set.id,
                            "candidate_surface": candidate_set.target_surface,
                            "candidate_atom_id": atom.id,
                            "selected": atom.features.get("selected", False),
                        },
                    ))
                continue

            if group.group_type in {"question", "command"} or any(
                act in {"command_request", "question"} for act in group.candidate_act_types
            ):
                self._add_obligation(result, ReplyObligation(
                    act_type="semantic_disambiguation",
                    response_mode="clarifying_question",
                    priority=self._PRIORITY["semantic_disambiguation"],
                    intent="disambiguate_meaning",
                    reason=f"ambiguous_candidate_set:{candidate_set.id}",
                    confidence=min(0.7, getattr(candidate_set, "confidence", 0.5)),
                    evidence_policy="none",
                    group_id=group.id,
                    params={
                        "candidate_set_id": candidate_set.id,
                        "surface": candidate_set.target_surface,
                        "candidate_count": len(candidate_atom_ids),
                    },
                ))

    def _select_and_track_paths(
        self,
        result: ActResolutionPlan,
        group: MeaningGroup,
        candidate_sets: list[Any],
        graph: Any,
    ) -> None:
        if graph is None:
            return
        for candidate_set in candidate_sets:
            candidate_atom_ids = list(getattr(candidate_set, "candidate_atom_ids", []) or [])
            if len(candidate_atom_ids) <= 1:
                continue
            selected_atom_id = getattr(candidate_set, "selected_atom_id", "") or ""
            for atom_id in candidate_atom_ids:
                atom = graph.atoms.get(atom_id)
                if atom is None:
                    continue
                is_selected = atom_id == selected_atom_id or atom.features.get("selected_candidate")
                path = SelectedPath(
                    candidate_set_id=candidate_set.id,
                    atom_id=atom.id,
                    atom_kind=atom.kind,
                    atom_key=atom.key,
                    surface=atom.surface or candidate_set.target_surface,
                    confidence=atom.confidence,
                    reason="selected_path" if is_selected else "rejected_path",
                    group_id=group.id,
                )
                if is_selected:
                    result.selected_paths.append(path)
                else:
                    result.rejected_paths.append(RejectedPath(
                        candidate_set_id=candidate_set.id,
                        atom_id=atom.id,
                        atom_kind=atom.kind,
                        atom_key=atom.key,
                        surface=atom.surface or candidate_set.target_surface,
                        confidence=atom.confidence,
                        reason="alternative_rejected",
                        evidence_refs=self._evidence_refs(atom.evidence),
                    ))

    _EVIDENCE_POLICY_RANK = {
        "none": 0,
        "optional": 1,
        "stored_required": 2,
        "fresh_required": 3,
        "tool_required": 4,
    }

    def _merge_hypotheses(self, result: ActResolutionPlan) -> None:
        if not result.obligations:
            return
        merged: dict[str, ReplyObligation] = {}
        merge_trace: dict[str, list[str]] = {}
        for obligation in result.obligations:
            key = f"{obligation.act_type}:{obligation.group_id}:{obligation.predicate_id}"
            if key in merged:
                existing = merged[key]
                existing.confidence = max(existing.confidence, obligation.confidence)
                existing.priority = max(existing.priority, obligation.priority)
                if obligation.requires_evidence:
                    existing.requires_evidence = True
                # Merge evidence_policy: take the most restrictive
                existing_rank = self._EVIDENCE_POLICY_RANK.get(existing.evidence_policy, 0)
                new_rank = self._EVIDENCE_POLICY_RANK.get(obligation.evidence_policy, 0)
                if new_rank > existing_rank:
                    existing.evidence_policy = obligation.evidence_policy
                    existing.requires_evidence = obligation.evidence_policy not in {"none", "optional"}
                existing.params["merged_from"] = existing.params.get("merged_from", [])
                if isinstance(existing.params["merged_from"], list):
                    existing.params["merged_from"].append(obligation.reason)
                merge_trace.setdefault(key, []).append(obligation.reason)
            else:
                merged[key] = obligation
                merge_trace.setdefault(key, [])
        result.obligations = sorted(merged.values(), key=lambda o: o.priority, reverse=True)

        seen_task_keys: set[str] = set()
        deduped: list[AnswerTask] = []
        for task in result.answer_tasks:
            key = f"{task.selected_act_type}:{task.group_id}:{task.predicate_id}:{task.intent}"
            if key in seen_task_keys:
                continue
            seen_task_keys.add(key)
            for existing in deduped:
                if existing.selected_act_type == task.selected_act_type and existing.group_id == task.group_id:
                    existing.confidence = max(existing.confidence, task.confidence)
                    existing.priority = max(existing.priority, task.priority)
                    existing.params["merged"] = True
                    break
            else:
                deduped.append(task)
        result.answer_tasks = sorted(deduped, key=lambda t: (t.priority, t.confidence), reverse=True)

    def _order_by_discourse(
        self,
        result: ActResolutionPlan,
        percept: MeaningPerceptPacket | None,
    ) -> None:
        if not result.obligations:
            return
        child_group_ids: set[str] = set()
        if percept is not None:
            for group in percept.meaning_groups:
                if group.parent_group_id:
                    child_group_ids.add(group.id)

        def discourse_key(obligation: ReplyObligation) -> tuple[int, int, str]:
            is_child = 0 if obligation.group_id in child_group_ids else 1
            return (is_child, -obligation.priority, obligation.group_id)

        result.obligations.sort(key=discourse_key, reverse=False)

    def _resolve_competing_obligations(self, result: ActResolutionPlan) -> None:
        has_capability = any(
            o.intent == "capability_summary" or o.act_type in {"self_capability_query", "capability_query"}
            for o in result.obligations
        )
        if has_capability:
            for obligation in result.obligations:
                if (
                    obligation.act_type == "retrospective_repair"
                    and obligation.reason.startswith("meaning_group:")
                    and obligation.priority > 63
                ):
                    obligation.priority = 63
                    obligation.params["demoted_by"] = "explicit_capability_obligation"
            for task in result.answer_tasks:
                if (
                    task.selected_act_type == "retrospective_repair"
                    and task.group_id
                    and task.priority > 63
                ):
                    task.priority = 63
                    task.params["demoted_by"] = "explicit_capability_obligation"

    def _add_group_obligation(
        self,
        result: ActResolutionPlan,
        group: MeaningGroup,
        act_type: str,
        response_mode: str,
        intent: str,
        priority: int,
        evidence_policy: str,
        predicate_id: str = "",
    ) -> None:
        resolved_predicate_id = (
            predicate_id or (group.predicate_ids[0] if group.predicate_ids else "")
        )
        self._add_obligation(result, ReplyObligation(
            act_type=act_type,
            response_mode=response_mode,
            priority=priority,
            intent=intent,
            reason=f"meaning_group:{group.id}",
            requires_evidence=evidence_policy not in {"none", "optional"},
            confidence=group.confidence,
            evidence_policy=evidence_policy,
            group_id=group.id,
            predicate_id=resolved_predicate_id,
            params={"surface": group.surface, "candidate_act_types": list(group.candidate_act_types)},
        ))
        self._add_answer_task_from_group(
            result, group, act_type, response_mode, intent, priority, evidence_policy, resolved_predicate_id
        )

    def _add_answer_task_from_group(
        self,
        result: ActResolutionPlan,
        group: MeaningGroup,
        act_type: str,
        response_mode: str,
        intent: str,
        priority: int,
        evidence_policy: str,
        predicate_id: str = "",
    ) -> None:
        result.answer_tasks.append(AnswerTask(
            response_mode=response_mode,
            intent=intent,
            selected_act_type=act_type,
            retrieval_mode=self._retrieval_mode_for_policy(evidence_policy, None),
            params={"surface": group.surface},
            priority=priority,
            confidence=group.confidence,
            evidence_policy=evidence_policy,
            group_id=group.id,
            predicate_id=predicate_id or (group.predicate_ids[0] if group.predicate_ids else ""),
        ))

    def _add_obligation(
        self, result: ActResolutionPlan, obligation: ReplyObligation
    ) -> None:
        result.obligations.append(obligation)

    def _select_answer_task(
        self,
        result: ActResolutionPlan,
        retrieval_plan: RetrievalPlan | None,
        meaning_percept: MeaningPerceptPacket | None = None,
    ) -> None:
        if retrieval_plan:
            result.retrieval_mode = retrieval_plan.mode
            result.requires_retrieval = retrieval_plan.mode not in ("", "none")

        if not result.obligations:
            result.selected_response_mode = "general_conversation"
            result.selected_intent = "general_conversation"
            result.confidence = 0.5
            result.response_contract = {"mode": "general_conversation", "evidence_policy": "none"}
            return

        child_group_ids: set[str] = set()
        if meaning_percept is not None:
            for group in meaning_percept.meaning_groups:
                if group.parent_group_id:
                    child_group_ids.add(group.id)

        def _obligation_sort_key(o: ReplyObligation) -> tuple:
            is_child = 1 if o.group_id in child_group_ids else 0
            return (o.priority, is_child, o.confidence, o.group_id)

        result.obligations.sort(key=_obligation_sort_key, reverse=True)
        selected = result.obligations[0]
        result.selected_response_mode = selected.response_mode
        result.selected_intent = selected.intent
        result.confidence = selected.confidence

        if selected.evidence_policy in {"tool_required", "fresh_required"}:
            result.requires_retrieval = True
            result.retrieval_mode = "live_tool_required"
            result.should_abstain = True
            result.abstention_reason = "fresh_external_evidence_required"
        elif selected.evidence_policy == "stored_required":
            result.requires_retrieval = True
            result.retrieval_mode = (
                result.retrieval_mode if result.retrieval_mode != "none" else "world_memory"
            )

        result.answer_tasks.sort(key=lambda t: (t.priority, t.confidence), reverse=True)

        selected_paths = [
            {"candidate_set_id": p.candidate_set_id, "atom_key": p.atom_key, "confidence": p.confidence}
            for p in result.selected_paths
        ]
        rejected_paths_for_learning = [
            {"candidate_set_id": p.candidate_set_id, "atom_key": p.atom_key, "confidence": p.confidence, "reason": p.reason}
            for p in result.rejected_paths
        ]

        result.response_contract = {
            "mode": selected.response_mode,
            "intent": selected.intent,
            "evidence_policy": selected.evidence_policy,
            "group_id": selected.group_id,
            "predicate_id": selected.predicate_id,
            "graph_patch_candidate_count": len(result.graph_patch_candidates),
            "ambiguous_candidate_set_count": sum(
                int(plan.get("ambiguous_candidate_set_count", 0))
                for plan in result.group_plans
            ),
            "must_not_fabricate_fresh_facts": selected.evidence_policy in {"tool_required", "fresh_required"},
            "selected_path_count": len(result.selected_paths),
            "rejected_path_count": len(result.rejected_paths),
            "selected_paths": selected_paths,
            "rejected_paths_for_learning": rejected_paths_for_learning,
        }

    def _dedupe_plan(self, result: ActResolutionPlan) -> None:
        obligations: list[ReplyObligation] = []
        seen_obligations: set[tuple[str, str, str, str, str]] = set()
        for obligation in sorted(
            result.obligations, key=lambda o: (o.priority, o.confidence), reverse=True
        ):
            key = (
                obligation.act_type, obligation.intent,
                obligation.group_id, obligation.predicate_id, obligation.evidence_policy,
            )
            if key in seen_obligations:
                continue
            obligations.append(obligation)
            seen_obligations.add(key)
        result.obligations = obligations

        tasks: list[AnswerTask] = []
        seen_tasks: set[tuple[str, str, str, str]] = set()
        for task in result.answer_tasks:
            key = (task.selected_act_type, task.group_id, task.predicate_id, task.intent)
            if key in seen_tasks:
                continue
            tasks.append(task)
            seen_tasks.add(key)
        result.answer_tasks = tasks

    def _facts_by_group(
        self, facts: list[EntityFactCandidate]
    ) -> dict[str, list[EntityFactCandidate]]:
        grouped: dict[str, list[EntityFactCandidate]] = {}
        for fact in facts:
            group_id = str(
                fact.qualifiers.get("group_id", "") if hasattr(fact, "qualifiers") else ""
            )
            if not group_id:
                continue
            grouped.setdefault(group_id, []).append(fact)
        return grouped

    def _outcomes_by_group(
        self, percept: MeaningPerceptPacket
    ) -> dict[str, list[MeaningAtomOutcome]]:
        grouped: dict[str, list[MeaningAtomOutcome]] = {}
        for outcome in percept.atom_outcomes:
            if not outcome.group_id:
                continue
            grouped.setdefault(outcome.group_id, []).append(outcome)
        return grouped

    def _candidate_sets_for_group(
        self, graph: Any, group_id: str
    ) -> list[Any]:
        if graph is None or not group_id:
            return []
        return [
            cs for cs in getattr(graph, "candidate_sets", []) or []
            if getattr(cs, "group_id", "") == group_id
        ]

    def _patches_for_group(
        self, graph: Any, group_id: str
    ) -> list[Any]:
        if graph is None or not group_id:
            return []
        patches = []
        for patch in getattr(graph, "patch_candidates", []) or []:
            for operation in getattr(patch, "operations", []) or []:
                fields = getattr(operation, "fields", {}) or {}
                if fields.get("group_id") == group_id:
                    patches.append(patch)
                    break
        return patches

    def _evidence_policy_for_act(
        self, act_type: str, requires_evidence: bool
    ) -> str:
        if act_type in self._NO_EVIDENCE_ACTS:
            return "none"
        if act_type in {"open_domain_entity_query", "evidence_query"}:
            return "stored_required" if requires_evidence else "optional"
        if act_type in {
            "memory_query", "self_knowledge_query",
            "user_identity_query", "user_name_query",
        }:
            return "stored_required"
        return "stored_required" if requires_evidence else "optional"

    def _retrieval_mode_for_policy(
        self,
        evidence_policy: str,
        retrieval_plan: RetrievalPlan | None,
    ) -> str:
        if evidence_policy in {"tool_required", "fresh_required"}:
            return "live_tool_required"
        if evidence_policy == "stored_required":
            return retrieval_plan.mode if retrieval_plan else "world_memory"
        return (
            retrieval_plan.mode
            if retrieval_plan and retrieval_plan.mode not in {"", "none"}
            else "none"
        )

    def _write_kind_for_act(self, act_type: str) -> str:
        if act_type == "preference_assertion":
            return "preference"
        if act_type in {"definition_teaching", "command_alias_teaching"}:
            return "lexeme_or_model"
        return "claim"

    def _has_fact_memory_update(self, result: ActResolutionPlan) -> bool:
        return any(update.candidates for update in result.memory_updates)

    def _teachable_facts(
        self, facts: list[EntityFactCandidate], act_types: set[str]
    ) -> list[EntityFactCandidate]:
        if act_types and act_types <= {
            "greeting",
            "acknowledgment",
            "playful_acknowledgment",
            "phatic_checkin",
            "reciprocal_phatic_checkin",
            "user_state_report",
            "assistant_evaluation",
            "frustration_signal",
            "confusion_repair",
            "playful_repair",
            "retrospective_repair",
            "evidence_query",
            "user_name_query",
            "user_identity_query",
            "self_identity_query",
            "self_knowledge_query",
            "self_capability_query",
            "capability_query",
            "open_domain_entity_query",
            "fresh_world_query",
            "memory_query",
            "story_request",
            "creative_request",
            "concept_query",
            "ask_question",
            "question",
            "command_request",
        }:
            return []
        return [
            fact for fact in facts
            if fact.reason != "affordance_atom"
            and fact.subject_entity_id not in {"fresh_source_requirement", "clarity_need"}
            and fact.subject_entity_id not in {"what", "who", "where", "when", "why", "how", "which"}
        ]

    def _intent_for_act(self, act_type: str, response_mode: str) -> str:
        if response_mode == "capability_summary":
            return "capability_summary"
        if response_mode == "unknown_entity_response":
            return "unknown_entity_response"
        if response_mode == "teaching_prompt":
            return "teaching_offer"
        if act_type == "frustration_signal":
            return "frustration_response"
        if act_type == "assistant_evaluation":
            return "frustration_response"
        if act_type == "user_state_report":
            return "chat_mode_statement"
        if act_type == "reciprocal_phatic_checkin":
            return "reciprocal_phatic_checkin"
        if act_type in {"confusion_repair", "retrospective_repair", "playful_repair"}:
            return act_type
        if act_type == "session_exit":
            return "session_exit"
        return act_type

    def _avg_fact_confidence(self, facts: list[EntityFactCandidate]) -> float:
        if not facts:
            return 0.5
        return sum(f.confidence for f in facts) / len(facts)

    @staticmethod
    def _evidence_refs(evidence: list[dict[str, Any]]) -> list[str]:
        refs: list[str] = []
        for item in evidence:
            span_id = str(item.get("span_id", "") or "")
            group_id = str(item.get("group_id", "") or "")
            source = str(item.get("source", "") or "")
            ref = ":".join(part for part in (source, group_id, span_id) if part)
            if ref and ref not in refs:
                refs.append(ref)
        return refs
