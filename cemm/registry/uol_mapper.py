from __future__ import annotations
from ..types.uol_atom import EntityRefUOLAtom, ProcessUOLAtom, StateUOLAtom
from ..types.signal import ObservationSemantics
from ..types.context_kernel import ContextKernel
from .registry import Registry
from .semantic_matcher import SemanticMatcher
from ..kernel.semantic_clusters import SemanticClusterRegistry


class UOLMapper:
    def __init__(self, registry: Registry) -> None:
        self._registry = registry
        self._matcher = SemanticMatcher(registry)
        self._cluster_reg = SemanticClusterRegistry(registry=registry)

    def map_signal(self, content: str, kernel: ContextKernel) -> list:
        atoms: list = []
        content_lower = content.lower().strip()
        words = content_lower.split()
        if not words:
            return atoms

        # Entity detection (pronoun-based, not registry-driven)
        if kernel.self_view.self_id:
            for w in words:
                if w in ("you", "your", "yourself", "yours"):
                    atoms.append(EntityRefUOLAtom(
                        entity_id=kernel.self_view.self_id,
                        role="target",
                        confidence=0.8,
                    ))
                    break

        if any(w in ("i", "me", "my", "mine", "myself") for w in words):
            atoms.append(EntityRefUOLAtom(
                entity_id="user",
                role="actor",
                confidence=0.8,
            ))

        # Semantic matching against all registry UOL entries with probability ranking
        uol_matches = self._matcher.match(content, kinds=["uol_semantic"])
        grouped = self._matcher.match_grouped(content, kinds=["uol_semantic"])

        # Map UOL semantic frame_keys to atom types
        state_keys = {"low_competence", "high_quality"}
        command_keys = {"command_remember", "command_reflect", "command_retrieve"}
        intent_keys = {"greeting", "session_exit"}
        conversational_keys = {"acknowledgment", "discourse_marker"}
        relation_prefixes = ("temporal_", "causal_")

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
            elif any(canonical_key.startswith(p) for p in relation_prefixes):
                atoms.append(ProcessUOLAtom(
                    frame_key=canonical_key,
                    modality="observed",
                    polarity="affirmed",
                    intensity=0.7 if canonical_key.startswith("causal_") else 0.6,
                    confidence=prob,
                ))

        # Claim structure detection via registry predicates with probability ranking
        pred_grouped = self._matcher.match_grouped(content, kinds=["predicate"])
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

        atoms = self._cluster_fallback(content, atoms)
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
        atoms.append(ProcessUOLAtom(
            frame_key=frame_key,
            modality="observed",
            polarity="affirmed",
            intensity=0.6,
            confidence=best.confidence,
        ))
        return atoms

    def compile_to_pragmatic_keys(self, atoms: list) -> tuple[list[str], list[str]]:
        quality_keys = []
        process_keys = []
        for atom in atoms:
            if atom.kind == "state":
                quality_keys.append(atom.state_key)
            elif atom.kind == "process":
                process_keys.append(atom.frame_key)
        return quality_keys, process_keys
