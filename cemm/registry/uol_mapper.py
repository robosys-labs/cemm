from __future__ import annotations
import json
from pathlib import Path
from ..types.uol_atom import EntityRefUOLAtom, ProcessUOLAtom, StateUOLAtom
from ..types.signal import ObservationSemantics
from ..types.context_kernel import ContextKernel
from .registry import Registry
from .semantic_matcher import SemanticMatcher
from ..kernel.semantic_clusters import SemanticClusterRegistry
from ..kernel.teaching_interpreter import TeachingInterpreter, TeachingEvent
from ..learning.lexeme_memory import LexemeMemory, LexemeStatus


_UOL_SEMANTICS_PATH = Path(__file__).parent.parent / "data" / "uol_semantics.json"
_PRONOUNS_PATH = Path(__file__).parent.parent / "data" / "pronouns.json"


def _load_json_data(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


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
        # Data-driven semantic frames: the JSON file is the source of truth for
        # language-specific surface aliases. UOLMapper loads it directly so it can
        # detect frames even when the registry is empty (e.g., in unit tests).
        self._query_frames = self._load_query_frames()
        self._self_ref_phrases = tuple(
            phrase for phrases in self._query_frames.get("self", {}).values() for phrase in phrases
        )
        self._user_query_phrases = tuple(
            phrase for phrases in self._query_frames.get("user", {}).values() for phrase in phrases
        )
        self._pronouns = self._load_pronouns()
        self._insult_phrases = self._load_insult_aliases()
        self._question_aliases = self._load_question_aliases()
        self._speech_act_to_frame = self._load_speech_act_to_frame()

    def _load_query_frames(self) -> dict[str, dict[str, list[str]]]:
        data = _load_json_data(_UOL_SEMANTICS_PATH)
        frames: dict[str, list[str]] = {
            entry["canonical_key"]: entry.get("aliases", [])
            for entry in data.get("uol_semantics", [])
        }
        return {
            "self": {
                "self_identity_query": frames.get("self_identity_query", []),
                "self_capability_query": frames.get("self_capability_query", []),
                "self_knowledge_query": frames.get("self_knowledge_query", []),
            },
            "user": {
                "user_identity_query": frames.get("user_identity_query", []),
                "user_name_query": frames.get("user_name_query", []),
            },
        }

    def _load_pronouns(self) -> dict[str, dict[str, list[str]]]:
        data = _load_json_data(_PRONOUNS_PATH)
        return data.get("pronouns", {})

    def _load_insult_aliases(self) -> set[str]:
        data = _load_json_data(_UOL_SEMANTICS_PATH)
        for entry in data.get("uol_semantics", []):
            if entry["canonical_key"] == "low_competence":
                return set(entry.get("aliases", []))
        return set()

    def _load_question_aliases(self) -> set[str]:
        data = _load_json_data(_UOL_SEMANTICS_PATH)
        aliases: set[str] = set()
        for key in ("ask_question", "request_clarification", "unknown_intent"):
            for entry in data.get("uol_semantics", []):
                if entry["canonical_key"] == key:
                    aliases.update(entry.get("aliases", []))
                    break
        return aliases

    def _load_speech_act_to_frame(self) -> dict[str, str]:
        data = _load_json_data(_UOL_SEMANTICS_PATH)
        return dict(data.get("speech_act_to_frame", {}))

    def _is_question(self, content_lower: str, grouped: dict | None = None) -> bool:
        """Return True if the surface is a question.

        Uses the language-agnostic terminal '?' and the presence of question
        UOL frames (from the registry matcher or the data file aliases).
        No English-specific prefixes are used.
        """
        if content_lower.endswith("?"):
            return True
        if grouped:
            question_keys = {"ask_question", "request_clarification", "unknown_intent"}
            if any(k in question_keys for k in grouped):
                return True
        return any(alias in content_lower for alias in self._question_aliases)

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
        content_forms = [content_lower] + [f.lower().strip() for f in extra_forms]

        # Entity detection is driven by the pronouns data file and the UOL
        # semantic query frames, not by hardcoded English pronouns.
        self_pronouns = set(self._pronouns.get("self", {}).get("target", []))
        user_pronouns = set(self._pronouns.get("user", {}).get("actor", []))
        _targets_self = (
            any(phrase in form for form in content_forms for phrase in self._self_ref_phrases)
            or (any(w in self._insult_phrases for w in words) and any(w in self_pronouns for w in words))
        )
        # User-identity query detection (e.g. "do you remember me?", "what's my name?")
        if any(phrase in form for form in content_forms for phrase in self._user_query_phrases):
            for frame_key, phrases in self._query_frames.get("user", {}).items():
                if any(phrase in form for form in content_forms for phrase in phrases):
                    atoms.append(ProcessUOLAtom(
                        frame_key=frame_key,
                        modality="observed",
                        polarity="affirmed",
                        intensity=0.7,
                        confidence=0.85,
                    ))
                    break

        if kernel.self_view.self_id and _targets_self:
            for frame_key, phrases in self._query_frames.get("self", {}).items():
                if any(phrase in form for form in content_forms for phrase in phrases):
                    atoms.append(ProcessUOLAtom(
                        frame_key=frame_key,
                        modality="observed",
                        polarity="affirmed",
                        intensity=0.7,
                        confidence=0.85,
                    ))
                    break
            for w in words:
                if w in self_pronouns:
                    atoms.append(EntityRefUOLAtom(
                        entity_id=kernel.self_view.self_id,
                        role="target",
                        confidence=0.85,
                    ))
                    break

        if any(w in user_pronouns for w in words):
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
        intent_keys = {"greeting", "session_exit", "assistance_request"}
        conversational_keys = {"acknowledgment", "discourse_marker", "playful_acknowledgment"}
        relation_prefixes = ("temporal_", "causal_")
        self_query_keys = {"self_identity_query", "self_capability_query", "self_knowledge_query"}
        user_query_keys = {"user_identity_query", "user_name_query"}

        emitted_keys: set[str] = {
            atom.frame_key for atom in atoms
            if isinstance(atom, ProcessUOLAtom) and atom.frame_key
        }

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
                if self._is_question(content_lower, grouped) and canonical_key == "command_remember":
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
        content_lower = content.lower().strip()
        if self._is_question(content_lower):
            return atoms
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
        if self._is_question(content_lower):
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
        frame_key = self._speech_act_to_frame.get(best.speech_act, "")
        if not frame_key:
            return atoms
        # Interrogative guard for cluster fallback too
        if frame_key == "command_remember":
            cl = content.lower().strip()
            if self._is_question(cl):
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
        user_pronouns = set(self._pronouns.get("user", {}).get("actor", []))
        has_user = any(w in content_lower for w in user_pronouns)
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
