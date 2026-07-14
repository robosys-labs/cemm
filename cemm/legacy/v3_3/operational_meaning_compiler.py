"""DEPRECATED: Replaced by cemm.kernel.execution.planner.Planner + cemm.kernel.cycle.kernel.CognitiveKernel.

This module is retained for legacy compatibility only. The v3.4 canonical
execution path uses Planner with OperationSchema for operation binding,
OperationAuthorizer for gating, and CommitCoordinator for persistent mutation.
Do not use for new code — redirect to the v3.4 execution pipeline.

OperationalMeaningCompiler — compile UOL graph into OperationalMeaningFrames.

Consumes UOLGraph, SemanticProgram, ConstructionMatches, ConceptResolutions,
PortBindings, and AffordancePredictions to produce OperationalMeaningFrame[].

Each frame is the planner-facing authority unit that determines downstream
query/write/reaction/safety contracts. This replaces broad instruction-kind
routing (assertion -> store_patch) with explicit per-meaning contracts.

Frame type classification heuristics:
- profile_assertion: has_property edge with entity:user subject + dimension feature
- concept_definition_teaching: is_a/same_as edge with teaches source
- concept_definition_query: asks_about edge targeting a concept atom
- style_feedback: frustration/complaint intent + previous-response targeting
- session_exit: session_exit/farewell intent
- user_state_report: user_state_report intent + affective state atom
- social_act: greeting/phatic/acknowledgment intent
- command: command intent without dismissal markers
- memory_command: "remember" command with embedded relation
- self_identity_query: self_identity_query intent
- self_capability_query: capability_query intent
- self_knowledge_query: self_knowledge_query intent
- user_profile_query: user_profile_query intent
- world_fact_claim: assertion with world-scoped subject
- correction: correction intent
- safety_candidate: safety/harm intent or permission deny
"""

from __future__ import annotations

import uuid
from typing import Any

from ...types.operational_meaning import (
    OperationalMeaningFrame,
    OperationalEffect,
    MeaningArbitrationResult,
    is_writable_frame,
)
from ...types.semantic_program import SemanticProgram
from ...types.uol_graph import UOLGraph
from .semantic_schema_kernel import get_kernel as _get_schema_kernel


_STYLE_FEEDBACK_INTENTS = frozenset({
    "response_feedback", "style_feedback",
})

_RESPONSE_FEEDBACK_INTENTS = frozenset({
    "frustration_signal", "user_complaint", "assistant_evaluation",
    "response_feedback",
})

_USER_PROFILE_INTENT_KEYS = frozenset({
    "user_profile_query", "user_name_query", "user_age_query",
})

_SELF_QUERY_INTENT_KEYS = frozenset({
    "self_identity_query",
    "self_knowledge_query",
    "capability_query",
    "self_capability_query",
})

_PROFILE_DIMENSION_BY_INTENT = {
    "user_name_query": "name",
    "user_age_query": "age",
    "user_profile_query": "",
}

_SELF_DIMENSION_BY_INTENT = {
    "self_identity_query": "name",
}


class OperationalMeaningCompiler:
    """Compile OperationalMeaningFrames from UOL graph and semantic program."""

    def compile(
        self,
        graph: UOLGraph,
        program: SemanticProgram,
        affordance_predictions: list[Any] | None = None,
    ) -> list[OperationalMeaningFrame]:
        frames: list[OperationalMeaningFrame] = []

        for instruction in program.instructions:
            frame = self._compile_instruction(graph, instruction, program, affordance_predictions)
            if frame is not None:
                frames.append(frame)

        if not frames and program.instructions:
            entry = program.entry_instruction
            if entry is not None:
                frames.append(self._default_frame(graph, entry))

        return frames

    def arbitrate(
        self,
        frames: list[OperationalMeaningFrame],
        safety_frame: Any | None = None,
    ) -> MeaningArbitrationResult:
        """Select primary frame and suppress lower-priority frames."""
        if not frames:
            return MeaningArbitrationResult(arbitration_reason="no_frames")

        if safety_frame is not None:
            safety_frames = [f for f in frames if f.frame_type == "safety_candidate"]
            if safety_frames:
                primary = safety_frames[0]
                return MeaningArbitrationResult(
                    selected_frame_ids=[primary.frame_id],
                    suppressed_frame_ids=[f.frame_id for f in frames if f.frame_id != primary.frame_id],
                    arbitration_reason="safety_preemption",
                    confidence=primary.confidence,
                )

        writable = [f for f in frames if f.is_writable]
        queries = [f for f in frames if f.is_query]
        social = [f for f in frames if f.frame_type in ("social_act", "phatic_act")]

        if writable and queries:
            best_writable = max(writable, key=lambda f: f.confidence)
            # Only let substantive query types override writable frames.
            # concept_definition_query is often a fallback for commands
            # like "can you remember that?" and shouldn't suppress writes.
            substantive_queries = [
                f for f in queries
                if f.frame_type not in ("concept_definition_query", "clarification_request")
            ]
            if substantive_queries:
                best_query = max(substantive_queries, key=lambda f: (self._query_priority(f.frame_type), f.confidence))
                if best_query.confidence > best_writable.confidence:
                    primary = best_query
                else:
                    primary = best_writable
            else:
                primary = best_writable
        elif writable:
            primary = max(writable, key=lambda f: f.confidence)
        elif queries:
            primary = max(queries, key=lambda f: (self._query_priority(f.frame_type), f.confidence))
        elif social:
            primary = max(social, key=lambda f: f.confidence)
        else:
            primary = max(frames, key=lambda f: f.confidence)

        suppressed = [f.frame_id for f in frames if f.frame_id != primary.frame_id]

        return MeaningArbitrationResult(
            selected_frame_ids=[primary.frame_id],
            suppressed_frame_ids=suppressed,
            arbitration_reason="priority_selection",
            confidence=primary.confidence,
        )

    def _compile_instruction(
        self,
        graph: UOLGraph,
        instruction: Any,
        program: SemanticProgram,
        affordance_predictions: list[Any] | None,
    ) -> OperationalMeaningFrame | None:
        kind = instruction.instruction_kind
        group_id = instruction.group_id
        group = self._find_group(graph, group_id)
        if group is None:
            return None

        frame_type, target_scope = self._classify_frame(graph, instruction, group)
        if frame_type is None:
            return None

        persistence = self._persistence_for_frame(frame_type)
        query_policy = self._query_policy_for_frame(frame_type)

        subject_id, predicate_id, object_id = self._extract_core_atoms(graph, instruction)
        relation_key, relation_family, dimension = self._extract_relation_info(graph, instruction)
        features = self._extract_features(graph, instruction)
        if not dimension:
            dimension = features.get("dimension", "") or features.get("property_dimension", "")
        if frame_type == "style_feedback" and not dimension:
            dimension = features.get("style_dimension", "") or "response_style"
            features.setdefault("dimension", dimension)
        if frame_type == "session_exit":
            dimension = "status"
            features["dimension"] = "status"
        if frame_type == "user_state_report" and not dimension:
            dimension = features.get("dimension", "") or "mood"
            features.setdefault("dimension", dimension)
        if frame_type == "concept_definition_query":
            topic_concept_id, topic_surface = self._query_topic_concept(graph, instruction)
            if topic_concept_id:
                features["object_concept_id"] = topic_concept_id
            if topic_surface:
                features["object_surface"] = topic_surface

        source_refs = self._source_refs(graph, group_id)
        evidence_refs = self._evidence_refs(graph, instruction)
        confidence = instruction.confidence

        return OperationalMeaningFrame(
            frame_id=f"omf_{uuid.uuid4().hex[:12]}",
            graph_id=graph.id,
            group_id=group_id,
            frame_type=frame_type,
            target_scope=target_scope,
            subject_atom_id=subject_id,
            predicate_atom_id=predicate_id,
            object_atom_id=object_id,
            relation_key=relation_key,
            relation_family=relation_family,
            dimension=dimension,
            persistence_policy=persistence,
            query_policy=query_policy,
            source_refs=source_refs,
            evidence_refs=evidence_refs,
            source_atom_ids=list(instruction.atom_ids),
            source_edge_ids=list(instruction.edge_ids),
            confidence=confidence,
            features=features,
        )

    def _classify_frame(self, graph: UOLGraph, instruction: Any, group: Any) -> tuple[str | None, str | None]:
        kind = instruction.instruction_kind
        intent_keys = self._intent_keys(graph, instruction)

        if self._has_safety(graph, instruction):
            return "safety_candidate", "safety"

        if "session_exit" in intent_keys or kind == "exit":
            return "session_exit", "conversation_state"

        if intent_keys & _STYLE_FEEDBACK_INTENTS:
            return "style_feedback", "previous_response"

        if intent_keys & _RESPONSE_FEEDBACK_INTENTS:
            if self._targets_previous_response(graph, instruction):
                return "response_feedback", "previous_response"
            if self._targets_self(graph, instruction) or self._targets_assistant_role(graph, instruction):
                return "response_feedback", "previous_response"
            return "social_act", "ephemeral_social"

        if "self_identity_query" in intent_keys:
            return "self_identity_query", "self_model"

        if "self_knowledge_query" in intent_keys:
            return "self_knowledge_query", "self_model"

        decode = self._decode_quality(graph, instruction, group)

        if intent_keys & _USER_PROFILE_INTENT_KEYS:
            if not self._has_sufficient_decode_for_profile_query(decode):
                return "clarification_request", "conversation_state"
            return "user_profile_query", "user_profile"

        if (kind == "question" or self._is_question_like_group(graph, instruction, group)):
            # When a has_property relation is present, use its source_role to
            # disambiguate self vs user profile queries early.
            prop_source_role = self._property_source_role(graph, instruction)
            if prop_source_role == "self" and not decode.get("decode_unknown_content_tokens"):
                return "self_identity_query", "self_model"
            if prop_source_role == "user":
                return "user_profile_query", "user_profile"

        if (kind == "question" or self._is_question_like_group(graph, instruction, group)) and self._targets_concept(graph, instruction):
            return "concept_definition_query", "concept_lattice"

        if (kind == "question" or self._is_question_like_group(graph, instruction, group)) and self._needs_clarification_before_routing(decode):
            return "clarification_request", "conversation_state"

        if "capability_query" in intent_keys or "self_capability_query" in intent_keys:
            return "self_capability_query", "self_model"

        if kind == "question":
            if self._targets_self(graph, instruction) and not decode.get("decode_unknown_content_tokens"):
                return "self_identity_query", "self_model"
            if self._targets_concept(graph, instruction):
                return "concept_definition_query", "concept_lattice"
            return "concept_definition_query", "concept_lattice"

        if kind == "teaching":
            if self._has_teaching_edge(graph, instruction):
                return "concept_definition_teaching", "concept_lattice"
            return "concept_definition_teaching", "concept_lattice"

        if kind == "assertion":
            if self._is_emotional_evaluation(graph, instruction):
                return "user_state_report", "conversation_state"
            if self._is_profile_assertion(graph, instruction):
                return "profile_assertion", "user_profile"
            if "user_state_report" in intent_keys or self._is_user_state_report(graph, instruction):
                return "user_state_report", "conversation_state"
            return "world_fact_claim", "external_world"

        if kind == "command":
            if self._has_action_key(graph, instruction, "memory_write"):
                return "memory_command", "concept_lattice"
            return "command", "conversation_state"

        if kind == "correction":
            return "correction", "previous_response"

        if kind == "exit":
            return "session_exit", "conversation_state"

        if kind == "social":
            if "session_exit" in intent_keys:
                return "session_exit", "conversation_state"
            if self._has_teaching_edge(graph, instruction):
                return "world_fact_claim", "external_world"
            return "social_act", "ephemeral_social"

        if kind == "repair":
            return "correction", "previous_response"

        return None, None

    def _persistence_for_frame(self, frame_type: str) -> str:
        writable_types = {
            "profile_assertion": "patch_candidate",
            "concept_definition_teaching": "patch_candidate",
            "world_fact_claim": "patch_candidate",
            "correction": "patch_candidate",
            "memory_command": "patch_candidate",
        }
        session_types = {
            "style_feedback": "session_state",
            "response_feedback": "session_state",
            "session_exit": "session_state",
            "user_state_report": "session_state",
            "command": "session_state",
            "social_act": "ephemeral_trace",
            "phatic_act": "ephemeral_trace",
        }
        query_types = {
            "concept_definition_query": "never_store",
            "self_identity_query": "never_store",
            "self_capability_query": "never_store",
            "self_knowledge_query": "never_store",
            "user_profile_query": "never_store",
        }
        if frame_type in writable_types:
            return writable_types[frame_type]
        if frame_type in session_types:
            return session_types[frame_type]
        if frame_type in query_types:
            return query_types[frame_type]
        return "never_store"

    def _query_policy_for_frame(self, frame_type: str) -> str:
        query_map = {
            "concept_definition_query": "concept_definition_lookup",
            "self_identity_query": "relation_lookup",
            "self_capability_query": "relation_lookup",
            "self_knowledge_query": "relation_lookup",
            "user_profile_query": "profile_dimension_lookup",
        }
        return query_map.get(frame_type, "none")

    @staticmethod
    def _query_priority(frame_type: str) -> int:
        return {
            "self_identity_query": 40,
            "self_capability_query": 40,
            "self_knowledge_query": 40,
            "user_profile_query": 35,
            "concept_definition_query": 10,
        }.get(frame_type, 0)

    def _intent_keys(self, graph: UOLGraph, instruction: Any) -> set[str]:
        keys: set[str] = set()
        for aid in instruction.atom_ids:
            atom = graph.atoms.get(aid)
            if atom is not None and atom.kind == "intent":
                keys.add(atom.key)
                if hasattr(atom, "features"):
                    for k in ("intent_key", "act_type", "response_act"):
                        v = atom.features.get(k, "")
                        if v:
                            keys.add(str(v))
        for match in graph.construction_matches:
            if match.group_id != instruction.group_id:
                continue
            if match.construction_key:
                keys.add(match.construction_key)
            keys.update(str(hint) for hint in match.pragmatic_hints if hint)
        return keys

    def _has_safety(self, graph: UOLGraph, instruction: Any) -> bool:
        """Classification hint: check for safety-relevant state delta atoms.

        This is a *hint* for frame classification â€” it causes the frame to be
        typed as safety_candidate so that the downstream pipeline produces
        StateTransmutationFrames from its state deltas. The authoritative
        safety detection happens later in SafetyFrameDetector.detect() which
        consumes StateTransmutationFrames with prior state and severity
        assessment.
        """
        schema_kernel = _get_schema_kernel()
        state_dims = schema_kernel.state_dimensions
        action_ops = schema_kernel.action_operators
        instruction_atom_ids = set(instruction.atom_ids)

        for atom in graph.atoms.values():
            if atom.group_id != instruction.group_id:
                continue
            # Check state delta atoms for harmful vital directions
            if atom.kind == "state" and atom.source == "schema_state_delta":
                dimension = atom.features.get("dimension", "")
                direction = atom.features.get("direction", "")
                parts = dimension.split(".", 1)
                if len(parts) != 2:
                    continue
                state_family, dim_name = parts
                if state_dims.is_safety_relevant(state_family, dim_name) and state_dims.is_harmful_direction(state_family, dim_name, direction):
                    return True
            # Check action atoms for restricted permission_policy
            if atom.kind == "action":
                action_key = atom.key
                if action_ops.permission_policy_for(action_key) == "restricted":
                    return True
        return False

    def _targets_self(self, graph: UOLGraph, instruction: Any) -> bool:
        for aid in instruction.atom_ids:
            atom = graph.atoms.get(aid)
            if atom is not None and atom.kind in ("self", "entity") and atom.key == "self":
                return True
        for edge in graph.edges:
            if edge.group_id == instruction.group_id and edge.edge_type == "asks_about":
                target = graph.atoms.get(edge.target_id)
                if target is not None and target.kind == "self":
                    return True
        return False

    def _property_source_role(self, graph: UOLGraph, instruction: Any) -> str:
        """Return 'self' or 'user' if a has_property relation in this group has
        an explicit source_role, otherwise empty string."""
        for atom in graph.atoms.values():
            if atom.group_id != instruction.group_id:
                continue
            if atom.kind == "relation" and atom.key == "has_property":
                role = atom.features.get("source_role", "")
                if role in ("self", "user"):
                    return role
        return ""

    def _targets_user_profile(self, graph: UOLGraph, instruction: Any) -> bool:
        for edge in graph.edges:
            if edge.group_id == instruction.group_id and edge.edge_type == "asks_about":
                target = graph.atoms.get(edge.target_id)
                if target is not None and target.kind == "entity" and target.key == "user":
                    return True
        return False

    def _targets_concept(self, graph: UOLGraph, instruction: Any) -> bool:
        for edge in graph.edges:
            if edge.group_id != instruction.group_id or edge.edge_type != "asks_about":
                continue
            target = graph.atoms.get(edge.target_id)
            if target is None:
                continue
            if target.kind in {"concept", "referent"}:
                return True
            if target.kind == "entity" and (
                target.source == "unknown_lexeme"
                or target.features.get("candidate_role") in {"topic", "unknown"}
                or target.features.get("role") == "topic"
            ):
                return True
            if target.kind == "relation" and str(target.features.get("proposition_mode", "")) == "queried":
                # Profile queries are classified earlier by intent. Other queried
                # relations represent a concept/relation lookup, not an assertion.
                return True
        return False

    def _targets_previous_response(self, graph: UOLGraph, instruction: Any) -> bool:
        for aid in instruction.atom_ids:
            atom = graph.atoms.get(aid)
            if atom is not None and atom.kind == "entity" and atom.key == "previous_response":
                return True
        return False

    def _targets_assistant_role(self, graph: UOLGraph, instruction: Any) -> bool:
        for edge in graph.edges:
            if edge.group_id != instruction.group_id or edge.edge_type != "has_role":
                continue
            target = graph.atoms.get(edge.target_id)
            if target is not None and target.kind == "self":
                return True
            if edge.features.get("role_value") == "self":
                return True
        return False

    @staticmethod
    def _has_action_key(graph: UOLGraph, instruction: Any, action_key: str) -> bool:
        for aid in instruction.atom_ids:
            atom = graph.atoms.get(aid)
            if atom is not None and atom.kind == "action" and atom.key == action_key:
                return True
        return False

    def _is_profile_assertion(self, graph: UOLGraph, instruction: Any) -> bool:
        for edge in graph.edges:
            if edge.group_id == instruction.group_id and edge.edge_type == "has_property":
                if edge.features.get("schema_source") == "state_delta":
                    continue
                source = graph.atoms.get(edge.source_id)
                if source is not None and source.kind == "entity" and source.key == "user":
                    return True
        return False

    def _is_emotional_evaluation(self, graph: UOLGraph, instruction: Any) -> bool:
        for edge in graph.edges:
            if edge.group_id != instruction.group_id:
                continue
            if edge.edge_type == "evaluates":
                return True
            if edge.features.get("emotional_verb") or edge.features.get("valence"):
                return True
            if edge.features.get("schema_source") == "state_delta":
                dimension = edge.features.get("dimension", "")
                if dimension.startswith("affective.") or dimension.startswith("volition."):
                    return True
        return False

    def _has_teaching_edge(self, graph: UOLGraph, instruction: Any) -> bool:
        teaching_types = {"is_a", "same_as", "has_property", "used_for", "part_of"}
        for edge in graph.edges:
            if edge.group_id == instruction.group_id and edge.edge_type in teaching_types:
                return True
        return False

    def _find_group(self, graph: UOLGraph, group_id: str) -> Any | None:
        for group in graph.groups:
            if group.id == group_id:
                return group
        return None

    def _extract_core_atoms(self, graph: UOLGraph, instruction: Any) -> tuple[str, str, str]:
        subject_id = ""
        predicate_id = ""
        object_id = ""
        for edge in graph.edges:
            if edge.group_id != instruction.group_id:
                continue
            if edge.edge_type in ("has_property", "is_a", "same_as", "used_for", "part_of"):
                subject_id = edge.source_id
                object_id = edge.target_id
                break
            if edge.edge_type == "asks_about":
                subject_id = edge.source_id
                object_id = edge.target_id
                break
        return subject_id, predicate_id, object_id

    def _extract_relation_info(self, graph: UOLGraph, instruction: Any) -> tuple[str, str, str]:
        relation_key = ""
        relation_family = ""
        dimension = ""
        for edge in graph.edges:
            if edge.group_id != instruction.group_id:
                continue
            if edge.edge_type in ("has_property", "is_a", "same_as", "used_for", "part_of"):
                relation_key = edge.edge_type
                dimension = edge.features.get("dimension", "") or edge.features.get("property_dimension", "")
                break
            if edge.edge_type == "asks_about":
                relation_key = edge.edge_type
                break
        if relation_key:
            if "is_a" in relation_key or "type_of" in relation_key:
                relation_family = "taxonomy"
            elif "has_property" in relation_key:
                relation_family = "property"
            elif "same_as" in relation_key:
                relation_family = "identity"
            elif "part_of" in relation_key:
                relation_family = "membership"
            elif "used_for" in relation_key:
                relation_family = "affordance"
            else:
                relation_family = "definition"
        return relation_key, relation_family, dimension

    def _extract_features(self, graph: UOLGraph, instruction: Any) -> dict[str, Any]:
        features: dict[str, Any] = {}
        for atom_id in instruction.atom_ids:
            atom = graph.atoms.get(atom_id)
            if atom is not None and atom.kind == "relation" and atom.group_id == instruction.group_id:
                features.update(dict(atom.features or {}))
        for atom in graph.atoms.values():
            if atom.group_id == instruction.group_id and atom.kind == "relation":
                features.update(dict(atom.features or {}))
        for edge in graph.edges:
            if edge.group_id != instruction.group_id:
                continue
            if edge.features:
                features.update(edge.features)
            if edge.edge_type in {"has_property", "is_a", "same_as", "used_for", "part_of", "asks_about"}:
                source = graph.atoms.get(edge.source_id)
                target = graph.atoms.get(edge.target_id)
                if source is not None:
                    features.setdefault("subject_concept_id", self._concept_id_for_atom(graph, source))
                    features.setdefault("subject_entity_id", self._entity_id_for_atom(source))
                    features.setdefault("subject_surface", source.surface)
                if target is not None and target.kind != "relation":
                    features.setdefault("object_concept_id", self._concept_id_for_atom(graph, target))
                    features.setdefault("object_entity_id", self._entity_id_for_atom(target))
                    features.setdefault("object_surface", target.surface)
        intent_keys = self._intent_keys(graph, instruction)
        dimension = self._dimension_from_intents(intent_keys)
        if dimension:
            features.setdefault("dimension", dimension)
            features.setdefault("property_dimension", dimension)
        affect = self._affect_from_state_atoms(graph, instruction)
        if affect:
            features.setdefault("affect", affect)
        group = self._find_group(graph, instruction.group_id)
        if group is not None:
            features.update(self._decode_quality(graph, instruction, group))
        return features

    def _decode_quality(self, graph: UOLGraph, instruction: Any, group: Any) -> dict[str, Any]:
        unknown_tokens: list[str] = []
        for candidate_set in graph.candidate_sets:
            if candidate_set.group_id != group.id or candidate_set.reason != "unknown_surface_candidate":
                continue
            surface = str(getattr(candidate_set, "target_surface", "") or "").strip()
            if surface and surface not in unknown_tokens:
                unknown_tokens.append(surface)
        token_count = max(0, int(getattr(group, "end_token", 0) or 0) - int(getattr(group, "start_token", 0) or 0))
        classified_count = max(0, token_count - len(unknown_tokens))
        coverage = (classified_count / token_count) if token_count else 1.0
        content_edges = [
            edge for edge in graph.edges
            if edge.group_id == instruction.group_id
            and edge.edge_type in {"has_property", "is_a", "same_as", "used_for", "part_of"}
            and str((edge.features or {}).get("proposition_mode", "asserted") or "asserted") != "queried"
        ]
        has_complete_relation = any(
            graph.atoms.get(edge.source_id) is not None and graph.atoms.get(edge.target_id) is not None
            for edge in content_edges
        )
        anchors = 0
        for atom_id in instruction.atom_ids:
            atom = graph.atoms.get(atom_id)
            if atom is None or atom.source in {"unknown_lexeme", "role_placeholder", "role_binding"}:
                continue
            if atom.kind in {"intent", "action", "process", "self", "entity", "quality", "modality", "relation"}:
                anchors += 1
        return {
            "decode_token_count": token_count,
            "decode_unknown_tokens": list(unknown_tokens),
            "decode_unknown_content_tokens": list(unknown_tokens),
            "decode_coverage": coverage,
            "decode_anchor_count": anchors,
            "decode_has_complete_relation": has_complete_relation,
            "unknown_token_ratio": (len(unknown_tokens) / token_count) if token_count else 0.0,
        }

    @staticmethod
    def _needs_clarification_before_routing(decode: dict[str, Any]) -> bool:
        unknown_content = list(decode.get("decode_unknown_content_tokens", []) or [])
        token_count = int(decode.get("decode_token_count", 0) or 0)
        coverage = float(decode.get("decode_coverage", 1.0) or 1.0)
        anchors = int(decode.get("decode_anchor_count", 0) or 0)
        has_complete_relation = bool(decode.get("decode_has_complete_relation", False))
        if len(unknown_content) == 1 and not has_complete_relation and coverage < 1.0:
            return True
        if token_count >= 3 and coverage < 0.6:
            return True
        if token_count >= 3 and anchors < 2 and unknown_content:
            return True
        return False

    @staticmethod
    def _has_sufficient_decode_for_profile_query(decode: dict[str, Any]) -> bool:
        unknown_content = list(decode.get("decode_unknown_content_tokens", []) or [])
        if float(decode.get("decode_coverage", 1.0) or 1.0) < 0.75:
            return False
        if len(unknown_content) > 1:
            return False
        return True

    def _is_user_state_report(self, graph: UOLGraph, instruction: Any) -> bool:
        for aid in instruction.atom_ids:
            atom = graph.atoms.get(aid)
            if atom is not None and atom.kind == "state" and atom.group_id == instruction.group_id:
                atom_kind = atom.features.get("atom_kind", "")
                if atom_kind in ("intent", "action"):
                    continue
                # Exclude action-induced state atoms (e.g. cognitive.knowledge:increase
                # from "remember" commands) â€” these are action effects, not user states.
                if atom.features.get("action_key"):
                    continue
                return True
        return False

    @staticmethod
    def _dimension_from_intents(intent_keys: set[str]) -> str:
        for key in intent_keys:
            dim = _PROFILE_DIMENSION_BY_INTENT.get(key) or _SELF_DIMENSION_BY_INTENT.get(key)
            if dim:
                return dim
        return ""

    @staticmethod
    def _affect_from_state_atoms(graph: UOLGraph, instruction: Any) -> str:
        for aid in instruction.atom_ids:
            atom = graph.atoms.get(aid)
            if atom is None or atom.kind != "state":
                continue
            polarity = atom.features.get("polarity", "") or atom.features.get("valence", "")
            if polarity:
                return str(polarity)
        return ""

    def _is_question_like_group(self, graph: UOLGraph, instruction: Any, group: Any) -> bool:
        if getattr(group, "function", "") == "question":
            return True
        for aid in instruction.atom_ids:
            atom = graph.atoms.get(aid)
            if atom is not None and bool(getattr(atom, "features", {}).get("is_question", False)):
                return True
        return False

    def _query_topic_concept(self, graph: UOLGraph, instruction: Any) -> tuple[str, str]:
        topic_atoms: list[tuple[int, int, Any]] = []
        for index, atom in enumerate(graph.atoms.values()):
            if atom.group_id != instruction.group_id or atom.kind != "entity":
                continue
            if atom.key in {"user", "world", "conversation", "memory"}:
                continue
            role = atom.features.get("role", "") or atom.features.get("candidate_role", "")
            is_unknown = atom.source == "unknown_lexeme"
            is_topic = role == "topic"
            if not is_unknown and not is_topic:
                continue
            position = atom.features.get("position")
            if isinstance(position, int) and position >= 0:
                sort_key = position
            elif is_topic:
                sort_key = 10_000 + index
            else:
                sort_key = index
            topic_atoms.append((sort_key, index, atom))

        if not topic_atoms:
            return "", ""

        ordered = [atom for _, _, atom in sorted(topic_atoms, key=lambda item: (item[0], item[1]))]
        keys = [self._normal_concept_part(atom.key) for atom in ordered]
        keys = [key for key in keys if key]
        if not keys:
            return "", ""
        surfaces = [str(atom.surface or atom.key) for atom in ordered if str(atom.surface or atom.key)]
        return f"concept:{'_'.join(keys)}", " ".join(surfaces)

    @staticmethod
    def _normal_concept_part(value: str) -> str:
        return "_".join(part for part in str(value).lower().replace("-", "_").split("_") if part)

    def _concept_id_for_atom(self, graph: UOLGraph, atom: Any) -> str:
        for resolution in graph.concept_resolutions:
            if resolution.atom_id == atom.id:
                return resolution.concept_id
        if atom.kind in {"entity", "relation", "quality", "state", "self"} and atom.key not in {"user", "self", "world", "conversation", "memory"}:
            return atom.key if atom.key.startswith("concept:") else f"concept:{atom.key}"
        return ""

    @staticmethod
    def _entity_id_for_atom(atom: Any) -> str:
        if atom.kind in {"entity", "self"}:
            key = atom.key.replace("entity:", "").replace("self:", "")
            if key in {"user", "self", "world", "conversation", "memory"}:
                return key
        return ""

    def _source_refs(self, graph: UOLGraph, group_id: str) -> list[str]:
        refs: list[str] = []
        for atom in graph.atoms.values():
            if atom.group_id == group_id and atom.kind == "source":
                refs.append(atom.id)
        return refs

    def _evidence_refs(self, graph: UOLGraph, instruction: Any) -> list[str]:
        refs: list[str] = []
        for aid in instruction.atom_ids:
            atom = graph.atoms.get(aid)
            if atom is None:
                continue
            evidence = getattr(atom, "evidence", [])
            for ev in evidence:
                ev_id = ev.get("id", "") if isinstance(ev, dict) else str(ev)
                if ev_id:
                    refs.append(ev_id)
        return refs

    def _default_frame(self, graph: UOLGraph, instruction: Any) -> OperationalMeaningFrame:
        return OperationalMeaningFrame(
            frame_id=f"omf_{uuid.uuid4().hex[:12]}",
            graph_id=graph.id,
            group_id=instruction.group_id,
            frame_type="social_act",
            target_scope="ephemeral_social",
            confidence=instruction.confidence,
            source_atom_ids=list(instruction.atom_ids),
            source_edge_ids=list(instruction.edge_ids),
        )
