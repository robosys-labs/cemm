from __future__ import annotations
import json
from pathlib import Path
from ..types.uol_atom import UOLAtom
from ..types.signal import ObservationSemantics
from ..types.context_kernel import ContextKernel
from .registry import Registry
from .semantic_matcher import SemanticMatcher
from ..kernel.semantic_clusters import SemanticClusterRegistry
from ..kernel.teaching_interpreter import TeachingInterpreter, TeachingEvent
from ..kernel.text_match import any_phrase_in_text, any_token_in_text, phrase_in_text, tokenize_surface
from ..learning.lexeme_memory import LexemeMemory, LexemeStatus
from .semantic_model_store import SemanticModelStore


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
        semantic_model_store: SemanticModelStore | None = None,
    ) -> None:
        self._registry = registry
        self._matcher = SemanticMatcher(registry)
        self._cluster_reg = SemanticClusterRegistry(registry=registry)
        self._lexeme_memory = lexeme_memory
        self._teaching_interpreter = teaching_interpreter or TeachingInterpreter()
        self._semantic_model_store = semantic_model_store
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
        self._frame_meta = self._load_frame_metadata()

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

    def _load_frame_metadata(self) -> dict[str, dict]:
        data = _load_json_data(_UOL_SEMANTICS_PATH)
        meta: dict[str, dict] = {}
        for entry in data.get("uol_semantics", []):
            key = entry["canonical_key"]
            meta[key] = {
                "act_type": entry.get("act_type", "unknown"),
                "polarity": entry.get("polarity", "neutral"),
                "intensity": entry.get("intensity", 0.5),
                "cue_type": entry.get("cue_type"),
            }
        return meta

    def _is_question(self, content_lower: str, grouped: dict | None = None) -> bool:
        if content_lower.endswith("?"):
            return True
        if grouped:
            question_keys = {"ask_question", "request_clarification", "unknown_intent"}
            if any(k in question_keys for k in grouped):
                return True
        for alias in self._question_aliases:
            if " " in alias:
                if phrase_in_text(alias, content_lower):
                    return True
            else:
                if alias in tokenize_surface(content_lower):
                    return True
        return False

    def map_signal(self, content: str, kernel: ContextKernel) -> list:
        atoms: list = []
        content_lower = content.lower().strip()
        words = content_lower.split()
        if not words:
            return atoms

        extra_forms = []
        latest_signal = getattr(kernel, "latest_signal", None)
        if latest_signal and latest_signal.normalized:
            extra_forms = latest_signal.normalized.normalized_forms
        content_forms = [content_lower] + [f.lower().strip() for f in extra_forms]

        self_pronouns = set(self._pronouns.get("self", {}).get("target", []))
        user_pronouns = set(self._pronouns.get("user", {}).get("actor", []))
        _targets_self = (
            any(phrase_in_text(phrase, form) for form in content_forms for phrase in self._self_ref_phrases)
            or (any(w in self._insult_phrases for w in words) and any(w in self_pronouns for w in words))
        )
        if any(phrase_in_text(phrase, form) for form in content_forms for phrase in self._user_query_phrases):
            for frame_key, phrases in self._query_frames.get("user", {}).items():
                if any(phrase_in_text(phrase, form) for form in content_forms for phrase in phrases):
                    atoms.append(UOLAtom(
                        id=frame_key,
                        kind="process",
                        key=frame_key,
                        confidence=0.85,
                        features={"modality": "observed", "polarity": "affirmed", "intensity": 0.7},
                    ))
                    break

        if kernel.self_view.self_id and _targets_self:
            for frame_key, phrases in self._query_frames.get("self", {}).items():
                if any(phrase_in_text(phrase, form) for form in content_forms for phrase in phrases):
                    atoms.append(UOLAtom(
                        id=frame_key,
                        kind="process",
                        key=frame_key,
                        confidence=0.85,
                        features={"modality": "observed", "polarity": "affirmed", "intensity": 0.7},
                    ))
                    break
            for w in words:
                if w in self_pronouns:
                    atoms.append(UOLAtom(
                        id=kernel.self_view.self_id,
                        kind="entity",
                        key=kernel.self_view.self_id,
                        confidence=0.85,
                        features={"role": "target"},
                    ))
                    break

        if any(w in user_pronouns for w in words):
            atoms.append(UOLAtom(
                id="user",
                kind="entity",
                key="user",
                confidence=0.8,
                features={"role": "actor"},
            ))

        if self._semantic_model_store:
            for form in content_forms:
                bindings = self._semantic_model_store.lookup_surface(form)
                if not bindings:
                    continue
                for binding in bindings:
                    if binding.maps_to_frame_key:
                        atoms.append(UOLAtom(
                            id=binding.maps_to_frame_key,
                            kind="process",
                            key=binding.maps_to_frame_key,
                            confidence=binding.confidence,
                            features={
                                "modality": "observed",
                                "polarity": "affirmed",
                                "intensity": 0.7,
                                "source": "learned_binding",
                                "binding_id": binding.id,
                            },
                        ))
                break

        uol_matches = self._matcher.match(content, kinds=["uol_semantic"], extra_forms=extra_forms)
        grouped = self._matcher.match_grouped(content, kinds=["uol_semantic"], extra_forms=extra_forms)

        state_keys = {"low_competence", "high_quality"}
        relation_prefixes = ("temporal_", "causal_")
        self_query_keys = {"self_identity_query", "self_capability_query", "self_knowledge_query"}
        user_query_keys = {"user_identity_query", "user_name_query"}

        emitted_keys: set[str] = {
            atom.key for atom in atoms
            if atom.kind == "process" and atom.key
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

            meta = self._frame_meta.get(canonical_key, {})
            if meta.get("cue_type"):
                continue

            if canonical_key == "command_remember" and self._is_question(content_lower, grouped):
                continue

            frame_polarity = meta.get("polarity", "neutral")
            frame_intensity = meta.get("intensity", 0.5)

            if canonical_key in state_keys:
                atom_polarity = "negative" if frame_polarity == "negative" else "positive"
                atoms.append(UOLAtom(
                    id=canonical_key,
                    kind="state",
                    key=canonical_key,
                    confidence=prob,
                    features={"polarity": atom_polarity, "intensity": frame_intensity, "source": "surface_alias"},
                ))
            elif canonical_key == "frustration_signal":
                atoms.append(UOLAtom(
                    id="frustration_signal",
                    kind="state",
                    key="frustration_signal",
                    confidence=prob,
                    features={"polarity": "negative", "intensity": frame_intensity, "source": "surface_alias"},
                ))
                atoms.append(UOLAtom(
                    id=canonical_key,
                    kind="process",
                    key=canonical_key,
                    confidence=prob,
                    features={"modality": "candidate", "polarity": "affirmed", "intensity": frame_intensity, "source": "surface_alias"},
                ))
            elif canonical_key == "assert_evaluation":
                negated = any_token_in_text(["not", "never"], content_lower) or "n't" in content_lower
                atoms.append(UOLAtom(
                    id=canonical_key,
                    kind="process",
                    key=canonical_key,
                    confidence=prob,
                    features={
                        "modality": "candidate",
                        "polarity": "negated" if negated else "affirmed",
                        "intensity": frame_intensity,
                        "source": "surface_alias",
                    },
                ))
            elif any(canonical_key.startswith(p) for p in relation_prefixes):
                atoms.append(UOLAtom(
                    id=canonical_key,
                    kind="process",
                    key=canonical_key,
                    confidence=prob,
                    features={
                        "modality": "candidate",
                        "polarity": "affirmed",
                        "intensity": 0.7 if canonical_key.startswith("causal_") else 0.6,
                        "source": "surface_alias",
                    },
                ))
            else:
                atoms.append(UOLAtom(
                    id=canonical_key,
                    kind="process",
                    key=canonical_key,
                    confidence=prob,
                    features={
                        "modality": "candidate",
                        "polarity": "affirmed",
                        "intensity": frame_intensity,
                        "source": "surface_alias",
                    },
                ))

        pred_grouped = self._matcher.match_grouped(content, kinds=["predicate"], extra_forms=extra_forms)
        for canonical_key, matches in pred_grouped.items():
            if not matches:
                continue
            best = matches[0]
            if best.probability < 0.4:
                continue
            claim_key = f"claim_{canonical_key}"
            atoms.append(UOLAtom(
                id=claim_key,
                kind="process",
                key=claim_key,
                confidence=best.probability,
                features={"modality": "observed", "polarity": "affirmed", "intensity": 0.6},
            ))

        atoms = self._apply_teaching_interpreter(content, atoms)
        atoms = self._apply_lexeme_memory(content, atoms)
        atoms = self._cluster_fallback(content, atoms)
        self._enrich_atoms(atoms, kernel, content_lower)
        return atoms

    def _apply_teaching_interpreter(self, content: str, atoms: list) -> list:
        content_lower = content.lower().strip()
        if self._is_question(content_lower):
            return atoms
        events = self._teaching_interpreter.interpret(content)
        for ev in events:
            if ev.kind == "command_alias":
                atoms.append(UOLAtom(
                    id="command_alias_teaching",
                    kind="process",
                    key="command_alias_teaching",
                    confidence=ev.confidence,
                    features={"modality": "observed", "polarity": "affirmed", "intensity": 0.7, **ev.to_dict()},
                ))
            elif ev.kind == "definition":
                atoms.append(UOLAtom(
                    id="definition_teaching",
                    kind="process",
                    key="definition_teaching",
                    confidence=ev.confidence,
                    features={"modality": "observed", "polarity": "affirmed", "intensity": 0.7, **ev.to_dict()},
                ))
            elif ev.kind == "correction":
                atoms.append(UOLAtom(
                    id="correction",
                    kind="process",
                    key="correction",
                    confidence=ev.confidence,
                    features={"modality": "observed", "polarity": "affirmed", "intensity": 0.8, **ev.to_dict()},
                ))
        return atoms

    def _apply_lexeme_memory(self, content: str, atoms: list) -> list:
        if not self._lexeme_memory:
            return atoms
        content_lower = content.lower().strip()
        if self._is_question(content_lower):
            return atoms
        words = content_lower.split()
        for w in words:
            lex = self._lexeme_memory.lookup_active(w)
            if lex and lex.role == "command_alias":
                atoms.append(UOLAtom(
                    id="command_remember",
                    kind="process",
                    key="command_remember",
                    confidence=lex.trust,
                    features={
                        "modality": "observed",
                        "polarity": "affirmed",
                        "intensity": 0.7,
                        "alias_surface": lex.surface,
                        "alias_meaning": lex.maps_to,
                    },
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
        if frame_key == "command_remember":
            cl = content.lower().strip()
            if self._is_question(cl):
                return atoms
        atoms.append(UOLAtom(
            id=frame_key,
            kind="process",
            key=frame_key,
            confidence=best.confidence,
            features={"modality": "observed", "polarity": "affirmed", "intensity": 0.6},
        ))
        return atoms

    def _enrich_atoms(self, atoms: list, kernel: ContextKernel, content_lower: str) -> None:
        self_id = getattr(kernel.self_view, "self_id", None)
        has_self_query = self_id and any(phrase_in_text(p, content_lower) for p in self._self_ref_phrases)
        user_pronouns = set(self._pronouns.get("user", {}).get("actor", []))
        has_user = any_token_in_text(list(user_pronouns), content_lower)
        entity_atoms = [a for a in atoms if a.kind == "entity"]
        user_atom = next((a for a in entity_atoms if a.key == "user"), None)
        self_atom = next((a for a in entity_atoms if self_id and a.key == self_id), None)
        state_atoms = [a for a in atoms if a.kind == "state"]
        state_keys = [a.key for a in state_atoms if a.key]

        for atom in atoms:
            if atom.kind == "state":
                atom.features.setdefault("state_model_id", atom.key)
                if atom.key in {"low_competence", "high_quality"}:
                    atom.features["holder_entity_id"] = self_id
                elif atom.key == "user_state":
                    atom.features["holder_entity_id"] = "user"
                elif has_self_query:
                    atom.features["holder_entity_id"] = self_id

        _output_frame_keys = {"state_preference", "assert_evaluation", "command_remember", "command_retrieve", "command_reflect"}
        _output_prefixes = ("temporal_", "causal_", "claim_")

        for atom in atoms:
            if atom.kind != "process":
                continue
            atom.features.setdefault("process_model_id", atom.key)
            if state_keys:
                if (
                    atom.key in _output_frame_keys
                    or any(atom.key.startswith(p) for p in _output_prefixes)
                ):
                    atom.features["output_state_keys"] = list(state_keys)
                else:
                    atom.features["input_state_keys"] = list(state_keys)
            participants: list[dict] = []
            seen: set[tuple[str, str]] = set()
            if has_user or user_atom:
                participants.append({"entity_id": "user", "role": "actor"})
                seen.add(("user", "actor"))
            if has_self_query or self_atom:
                participants.append({"entity_id": self_id, "role": "target"})
                seen.add((self_id, "target"))
            for ref in entity_atoms:
                if ref.key in ("user", self_id):
                    continue
                role = ref.features.get("role", "")
                key = (ref.key, role)
                if key not in seen:
                    seen.add(key)
                    participants.append({"entity_id": ref.key, "role": role})
            atom.features["participants"] = participants

    def compile_to_pragmatic_keys(self, atoms: list) -> tuple[list[str], list[str]]:
        quality_keys = []
        process_keys = []
        for atom in atoms:
            if atom.kind == "state":
                quality_keys.append(atom.key)
            elif atom.kind == "process":
                process_keys.append(atom.key)
        return quality_keys, process_keys
