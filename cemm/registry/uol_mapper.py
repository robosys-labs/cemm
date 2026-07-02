from __future__ import annotations
from ..types.uol_atom import EntityRefUOLAtom, ProcessUOLAtom, StateUOLAtom
from ..types.signal import ObservationSemantics
from ..types.context_kernel import ContextKernel
from .registry import Registry
from .semantic_matcher import SemanticMatcher
from ..kernel.semantic_clusters import SemanticClusterRegistry
from ..kernel.teaching_interpreter import TeachingInterpreter, TeachingEvent
from ..learning.lexeme_memory import LexemeMemory, LexemeStatus


class UOLMapper:
    def __init__(
        self,
        registry: Registry,
        lexeme_memory: LexemeMemory | None = None,
        teaching_interpreter: TeachingInterpreter | None = None,
    ) -> None:
        self._registry = registry
        self._matcher = SemanticMatcher(registry)
        self._cluster_reg = SemanticClusterRegistry(registry=registry)
        self._lexeme_memory = lexeme_memory
        self._teaching_interpreter = teaching_interpreter or TeachingInterpreter()
        self._self_query_frames = {
            "self_identity_query": ["who are you", "what are you", "what is your name", "introduce yourself"],
            "self_capability_query": ["what do you do", "what can you do", "your capabilities", "how do you work"],
            "self_knowledge_query": ["what do you know", "what do you know about yourself"],
        }
        self._self_ref_phrases = tuple(
            phrase for phrases in self._self_query_frames.values() for phrase in phrases
        )
        self._user_query_frames = {
            "user_identity_query": ["do you remember me", "do you know me", "do you know who i am", "who am i"],
            "user_name_query": ["what's my name", "what is my name", "do you know my name"],
        }
        self._user_query_phrases = tuple(
            phrase for phrases in self._user_query_frames.values() for phrase in phrases
        )
        # Interrogative prefixes that indicate a question, not a command.
        self._interrogative_prefixes = (
            "do you ", "can you ", "could you ", "did you ",
            "have you ", "are you ", "is ", "what ", "whats ",
            "who ", "where ", "when ", "why ", "how ",
        )

    def map_signal(self, content: str, kernel: ContextKernel) -> list:
        atoms: list = []
        content_lower = content.lower().strip()
        words = content_lower.split()
        if not words:
            return atoms

        # Use normalized signal forms when available for robust noisy/casual matching
        extra_forms = []
        latest_signal = getattr(kernel, "latest_signal", None)
        if latest_signal and latest_signal.normalized:
            extra_forms = latest_signal.normalized.normalized_forms

        # Entity detection (pronoun-based, not registry-driven)
        # Map second-person pronouns to self when the input is clearly a
        # self-reference query or an insult targeting the assistant.
        _insult_phrases = ("dumb", "stupid", "fool", "idiot", "useless", "broken")
        _targets_self = (
            any(phrase in content_lower for phrase in self._self_ref_phrases)
            or (any(w in _insult_phrases for w in words) and any(w in ("you", "your", "yourself") for w in words))
        )
        # User-identity query detection (e.g. "do you remember me?", "what's my name?")
        if any(phrase in content_lower for phrase in self._user_query_phrases):
            for frame_key, phrases in self._user_query_frames.items():
                if any(phrase in content_lower for phrase in phrases):
                    atoms.append(ProcessUOLAtom(
                        frame_key=frame_key,
                        modality="observed",
                        polarity="affirmed",
                        intensity=0.7,
                        confidence=0.85,
                    ))
                    break

        if kernel.self_view.self_id and _targets_self:
            for frame_key, phrases in self._self_query_frames.items():
                if any(phrase in content_lower for phrase in phrases):
                    atoms.append(ProcessUOLAtom(
                        frame_key=frame_key,
                        modality="observed",
                        polarity="affirmed",
                        intensity=0.7,
                        confidence=0.85,
                    ))
                    break
            for w in words:
                if w in ("you", "your", "yourself", "yours"):
                    atoms.append(EntityRefUOLAtom(
                        entity_id=kernel.self_view.self_id,
                        role="target",
                        confidence=0.85,
                    ))
                    break

        if any(w in ("i", "me", "my", "mine", "myself") for w in words):
            atoms.append(EntityRefUOLAtom(
                entity_id="user",
                role="actor",
                confidence=0.8,
            ))

        # Semantic matching against all registry UOL entries with probability ranking
        uol_matches = self._matcher.match(content, kinds=["uol_semantic"], extra_forms=extra_forms)
        grouped = self._matcher.match_grouped(content, kinds=["uol_semantic"], extra_forms=extra_forms)

        # Map UOL semantic frame_keys to atom types
        state_keys = {"low_competence", "high_quality"}
        command_keys = {"command_remember", "command_reflect", "command_retrieve"}
        intent_keys = {"greeting", "session_exit"}
        conversational_keys = {"acknowledgment", "discourse_marker", "playful_acknowledgment"}
        relation_prefixes = ("temporal_", "causal_")
        self_query_keys = {"self_identity_query", "self_capability_query", "self_knowledge_query"}
        user_query_keys = {"user_identity_query", "user_name_query"}

        emitted_keys: set[str] = set()

        for canonical_key, matches in grouped.items():
            if not matches:
                continue
            best = matches[0]
            prob = best.probability

            if prob < 0.3:
                continue

            if canonical_key in emitted_keys:
                continue
            emitted_keys.add(canonical_key)

            if canonical_key in state_keys:
                polarity = "negative" if canonical_key == "low_competence" else "positive"
                intensity = 0.7 if canonical_key == "low_competence" else 0.6
                atoms.append(StateUOLAtom(
                    state_key=canonical_key,
                    polarity=polarity,
                    intensity=intensity,
                    confidence=prob,
                ))
            elif canonical_key in command_keys:
                # Interrogative guard: do not emit command atoms for questions.
                # "do you remember me?" is a question, not a remember command.
                is_question = (
                    content_lower.endswith("?")
                    or any(content_lower.startswith(p) for p in self._interrogative_prefixes)
                )
                if is_question and canonical_key == "command_remember":
                    continue
                atoms.append(ProcessUOLAtom(
                    frame_key=canonical_key,
                    modality="observed",
                    polarity="affirmed",
                    intensity=0.8,
                    confidence=prob,
                ))
            elif canonical_key in intent_keys:
                atoms.append(ProcessUOLAtom(
                    frame_key=canonical_key,
                    modality="observed",
                    polarity="affirmed",
                    intensity=0.9 if canonical_key == "session_exit" else 0.6,
                    confidence=prob,
                ))
            elif canonical_key == "assert_evaluation":
                negated = any(n in content_lower for n in ("not", "n't", "never"))
                atoms.append(ProcessUOLAtom(
                    frame_key=canonical_key,
                    modality="observed",
                    polarity="negated" if negated else "affirmed",
                    intensity=0.7,
                    confidence=prob,
                ))
            elif canonical_key == "request_clarification":
                atoms.append(ProcessUOLAtom(
                    frame_key=canonical_key,
                    modality="observed",
                    polarity="affirmed",
                    intensity=0.6,
                    confidence=prob,
                ))
            elif canonical_key in conversational_keys:
                atoms.append(ProcessUOLAtom(
                    frame_key=canonical_key,
                    modality="observed",
                    polarity="affirmed",
                    intensity=0.5,
                    confidence=prob,
                ))
            elif canonical_key in self_query_keys:
                atoms.append(ProcessUOLAtom(
                    frame_key=canonical_key,
                    modality="observed",
                    polarity="affirmed",
                    intensity=0.7,
                    confidence=prob,
                ))
            elif canonical_key in user_query_keys:
                atoms.append(ProcessUOLAtom(
                    frame_key=canonical_key,
                    modality="observed",
                    polarity="affirmed",
                    intensity=0.7,
                    confidence=prob,
                ))
            elif any(canonical_key.startswith(p) for p in relation_prefixes):
                atoms.append(ProcessUOLAtom(
                    frame_key=canonical_key,
                    modality="observed",
                    polarity="affirmed",
                    intensity=0.7 if canonical_key.startswith("causal_") else 0.6,
                    confidence=prob,
                ))

        # Claim structure detection via registry predicates with probability ranking
        pred_grouped = self._matcher.match_grouped(content, kinds=["predicate"], extra_forms=extra_forms)
        for canonical_key, matches in pred_grouped.items():
            if not matches:
                continue
            best = matches[0]
            if best.probability < 0.4:
                continue
            atoms.append(ProcessUOLAtom(
                frame_key=f"claim_{canonical_key}",
                modality="observed",
                polarity="affirmed",
                intensity=0.6,
                confidence=best.probability,
            ))

        # Detect teaching/learning surface patterns and emit teaching atoms
        atoms = self._apply_teaching_interpreter(content, atoms)

        # Resolve learned lexeme/command aliases into process atoms
        atoms = self._apply_lexeme_memory(content, atoms)

        atoms = self._cluster_fallback(content, atoms)
        self._enrich_atoms(atoms, kernel, content_lower)
        return atoms

    def _apply_teaching_interpreter(self, content: str, atoms: list) -> list:
        """Detect definition/alias/correction patterns and emit teaching process atoms."""
        events = self._teaching_interpreter.interpret(content)
        for ev in events:
            if ev.kind == "command_alias":
                atoms.append(ProcessUOLAtom(
                    frame_key="command_alias_teaching",
                    modality="observed",
                    polarity="affirmed",
                    intensity=0.7,
                    confidence=ev.confidence,
                    params=ev.to_dict(),
                ))
            elif ev.kind == "definition":
                atoms.append(ProcessUOLAtom(
                    frame_key="definition_teaching",
                    modality="observed",
                    polarity="affirmed",
                    intensity=0.7,
                    confidence=ev.confidence,
                    params=ev.to_dict(),
                ))
            elif ev.kind == "correction":
                atoms.append(ProcessUOLAtom(
                    frame_key="correction",
                    modality="observed",
                    polarity="affirmed",
                    intensity=0.8,
                    confidence=ev.confidence,
                    params=ev.to_dict(),
                ))
        return atoms

    def _apply_lexeme_memory(self, content: str, atoms: list) -> list:
        """If a learned active command alias appears in the input, emit a command atom.

        Questions are guarded so a learned alias word does not collapse a
        question like "do you remember zibble?" into an imperative command.
        """
        if not self._lexeme_memory:
            return atoms
        content_lower = content.lower().strip()
        is_question = (
            content_lower.endswith("?")
            or any(content_lower.startswith(p) for p in self._interrogative_prefixes)
        )
        if is_question:
            return atoms
        words = content_lower.split()
        for w in words:
            lex = self._lexeme_memory.lookup_active(w)
            if lex and lex.role == "command_alias":
                atoms.append(ProcessUOLAtom(
                    frame_key="command_remember",
                    modality="observed",
                    polarity="affirmed",
                    intensity=0.7,
                    confidence=lex.trust,
                    params={"alias_surface": lex.surface, "alias_meaning": lex.maps_to},
                ))
                break
        return atoms

    def _cluster_fallback(self, content: str, atoms: list) -> list:
        has_process = any(atom.kind == "process" for atom in atoms)
        if has_process:
            return atoms
        ranked = self._cluster_reg.match_ranked(content)
        if not ranked:
            return atoms
        best = ranked[0]
        if best.confidence < 0.5:
            return atoms
        speech_act_to_frame = {
            "greeting": "greeting",
            "acknowledgment": "acknowledgment",
            "clarification": "request_clarification",
            "exit": "session_exit",
            "command": "command_remember",
        }
        frame_key = speech_act_to_frame.get(best.speech_act, "")
        if not frame_key:
            return atoms
        # Interrogative guard for cluster fallback too
        if frame_key == "command_remember":
            cl = content.lower().strip()
            is_question = (
                cl.endswith("?")
                or any(cl.startswith(p) for p in self._interrogative_prefixes)
            )
            if is_question:
                return atoms
        atoms.append(ProcessUOLAtom(
            frame_key=frame_key,
            modality="observed",
            polarity="affirmed",
            intensity=0.6,
            confidence=best.confidence,
        ))
        return atoms

    def _enrich_atoms(self, atoms: list, kernel: ContextKernel, content_lower: str) -> None:
        self_id = getattr(kernel.self_view, "self_id", None)
        has_self_query = self_id and any(p in content_lower for p in self._self_ref_phrases)
        has_user = any(w in content_lower for w in ("i", "me", "my", "mine", "myself"))
        entity_atoms = [a for a in atoms if isinstance(a, EntityRefUOLAtom)]
        user_atom = next((a for a in entity_atoms if a.entity_id == "user"), None)
        self_atom = next((a for a in entity_atoms if self_id and a.entity_id == self_id), None)
        state_atoms = [a for a in atoms if isinstance(a, StateUOLAtom)]
        state_keys = [a.state_key for a in state_atoms if a.state_key]

        for atom in atoms:
            if isinstance(atom, StateUOLAtom):
                atom.state_model_id = atom.state_model_id or atom.state_key
                if atom.state_key in {"low_competence", "high_quality"}:
                    atom.holder_entity_id = self_id
                elif atom.state_key == "user_state":
                    atom.holder_entity_id = "user"
                elif has_self_query:
                    atom.holder_entity_id = self_id

        # Frames that create or change a state get output_state_keys; others get input_state_keys.
        _output_frame_keys = {"state_preference", "assert_evaluation", "command_remember", "command_retrieve", "command_reflect"}
        _output_prefixes = ("temporal_", "causal_", "claim_")

        for atom in atoms:
            if not isinstance(atom, ProcessUOLAtom):
                continue
            atom.process_model_id = atom.process_model_id or atom.frame_key
            if state_keys:
                if (
                    atom.frame_key in _output_frame_keys
                    or any(atom.frame_key.startswith(p) for p in _output_prefixes)
                ):
                    atom.output_state_keys = list(state_keys)
                else:
                    atom.input_state_keys = list(state_keys)
            participants: list[dict] = []
            seen: set[tuple[str, str]] = set()
            if has_user or user_atom:
                participants.append({"entity_id": "user", "role": "actor"})
                seen.add(("user", "actor"))
            if has_self_query or self_atom:
                participants.append({"entity_id": self_id, "role": "target"})
                seen.add((self_id, "target"))
            for ref in entity_atoms:
                if ref.entity_id in ("user", self_id):
                    continue
                key = (ref.entity_id, ref.role)
                if key not in seen:
                    seen.add(key)
                    participants.append({"entity_id": ref.entity_id, "role": ref.role})
            atom.participants = participants

    def compile_to_pragmatic_keys(self, atoms: list) -> tuple[list[str], list[str]]:
        quality_keys = []
        process_keys = []
        for atom in atoms:
            if atom.kind == "state":
                quality_keys.append(atom.state_key)
            elif atom.kind == "process":
                process_keys.append(atom.frame_key)
        return quality_keys, process_keys
