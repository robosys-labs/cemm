"""Structural episode curriculum and family-level holdout validation."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping
from cemm.model import stable


@dataclass(frozen=True)
class SemanticEpisode:
    episode_ref: str
    family: str
    pre: Mapping[str, Any]
    input_evidence: tuple[Mapping[str, Any], ...]
    target: Mapping[str, Any]
    tags: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, value):
        family = str(value["family"])
        pre = dict(value.get("pre", {}))
        evidence = tuple(dict(x) for x in value.get("input_evidence", ()))
        target = dict(value["target"])
        tags = tuple(sorted(set(value.get("tags", ()))))
        ref = str(value.get("episode_ref") or stable("episode", family, pre, evidence, target, tags))
        return cls(ref, family, pre, evidence, target, tags)

    def as_dict(self):
        return {
            "episode_ref": self.episode_ref,
            "family": self.family,
            "pre": dict(self.pre),
            "input_evidence": [dict(x) for x in self.input_evidence],
            "target": dict(self.target),
            "tags": list(self.tags),
        }


@dataclass(frozen=True)
class CurriculumManifest:
    train_families: tuple[str, ...]
    holdout_families: tuple[str, ...]
    episodes: tuple[SemanticEpisode, ...]
    required_contrasts: tuple[str, ...]

    def validate(self):
        overlap = set(self.train_families) & set(self.holdout_families)
        if overlap:
            raise ValueError(f"family leakage into holdout: {sorted(overlap)}")
        no_delta = [x for x in self.episodes if x.target.get("transition") == "NO_TRANSITION"]
        if not no_delta:
            raise ValueError("curriculum requires explicit NO_TRANSITION episodes")
        for episode in self.episodes:
            target = episode.target
            for key in ("stable_csir", "discourse_act", "epistemic_placement", "response_csir"):
                if key not in target:
                    raise ValueError(f"episode {episode.episode_ref} missing {key}")
            if "transition" not in target:
                raise ValueError(f"episode {episode.episode_ref} missing transition/NO_TRANSITION")
        return True

    def as_dict(self):
        return {
            "train_families": list(self.train_families),
            "holdout_families": list(self.holdout_families),
            "episodes": [x.as_dict() for x in self.episodes],
            "required_contrasts": list(self.required_contrasts),
        }
