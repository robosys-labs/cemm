"""Generic causal mechanisms, role-addressed transition previews and prediction error."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from cemm.model import Fact, canonical, isexist, isvar, stable


@dataclass(frozen=True)
class StateDelta:
    subject_ref: str
    dimension_ref: str
    before: tuple[Any, ...]
    after: Any
    stance: str = "support"
    context_ref: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "subject_ref": self.subject_ref,
            "dimension_ref": self.dimension_ref,
            "before": list(self.before),
            "after": self.after,
            "stance": self.stance,
            "context_ref": self.context_ref,
        }


@dataclass(frozen=True)
class TransitionPreview:
    preview_ref: str
    mechanism_ref: str
    trigger_refs: tuple[str, ...]
    role_bindings: Mapping[str, Any]
    precondition_refs: tuple[str, ...]
    deltas: tuple[StateDelta, ...]
    secondary_events: tuple[dict[str, Any], ...] = ()
    confidence: float = 1.0
    uncertainty: tuple[str, ...] = ()
    proof: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "preview_ref": self.preview_ref,
            "mechanism_ref": self.mechanism_ref,
            "trigger_refs": list(self.trigger_refs),
            "role_bindings": dict(self.role_bindings),
            "precondition_refs": list(self.precondition_refs),
            "deltas": [x.as_dict() for x in self.deltas],
            "secondary_events": [dict(x) for x in self.secondary_events],
            "confidence": self.confidence,
            "uncertainty": list(self.uncertainty),
            "proof": dict(self.proof),
        }


@dataclass(frozen=True)
class PredictionError:
    error_ref: str
    kind: str
    target_ref: str
    expected: Any
    observed: Any
    confidence: float
    proof_refs: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "error_ref": self.error_ref,
            "kind": self.kind,
            "target_ref": self.target_ref,
            "expected": self.expected,
            "observed": self.observed,
            "confidence": self.confidence,
            "proof_refs": list(self.proof_refs),
        }


class TransitionEngine:
    """Simulate promoted causal rules without committing predicted effects."""

    def __init__(self, store, inference, authority_generation: int):
        self.s = store
        self.inf = inference
        self.authority_generation = int(authority_generation)

    @staticmethod
    def _instantiate(value, env):
        if isinstance(value, str) and (isvar(value) or isexist(value)):
            return env.get(value, value)
        return value

    @staticmethod
    def _projection_values(projections, subject_ref, dimension_ref):
        raw = projections.get(subject_ref, {}) if isinstance(projections, Mapping) else {}
        for dimension in raw.get("dimensions", ()):  # StateSpaceProjection.as_dict()
            if dimension.get("dimension_ref") == dimension_ref:
                return tuple(dimension.get("values", ()))
        return ()

    def _causal_rules(self, trigger_apps: Iterable[Mapping[str, Any]]):
        operator_refs = {str(x.get("operator")) for x in trigger_apps if x.get("operator")}
        semantic_refs = {
            str(value)
            for app in trigger_apps
            for value in app.get("args", {}).values()
            if isinstance(value, str) and not value.startswith(("?", "!"))
        }
        return self.s.relevant_rules(
            rule_kinds=("causal",),
            consequent=False,
            operator_refs=operator_refs,
            semantic_refs=semantic_refs,
            authority_generation=self.authority_generation,
        )

    def preview(self, trigger_apps, current_facts, projections, *, context_ref=None):
        trigger_apps = tuple(dict(x) for x in trigger_apps)
        if not trigger_apps:
            return ()
        trigger_facts = [
            Fact(stable("trigger", app), app["operator"], dict(app.get("args", {})), app.get("stance", "support"))
            for app in trigger_apps
        ]
        previews = []
        for row in self._causal_rules(trigger_apps):
            antecedent = json.loads(row["antecedent"])
            consequent = json.loads(row["consequent"])
            matches = self.inf.match_clauses(antecedent, list(current_facts) + trigger_facts)
            for env, parents in matches:
                deltas = []
                secondary = []
                unresolved = []
                parent_refs = tuple(sorted({x.ref for x in parents}))
                existential_refs = {}

                def instantiate(value):
                    if isinstance(value, str) and isvar(value):
                        return env.get(value, value)
                    if isinstance(value, str) and isexist(value):
                        existential_refs.setdefault(
                            value,
                            stable("preview-existential", row["rule_ref"], parent_refs, value),
                        )
                        return existential_refs[value]
                    return value

                for clause in consequent:
                    args = {
                        role: instantiate(value)
                        for role, value in clause.get("args", {}).items()
                    }
                    if any(isinstance(value, str) and (isvar(value) or isexist(value)) for value in args.values()):
                        unresolved.append(canonical(clause))
                        continue
                    if clause.get("operator") == "op:state":
                        subject = args.get("role:subject")
                        dimension = args.get("role:dimension")
                        if not isinstance(subject, str) or not isinstance(dimension, str):
                            unresolved.append(canonical(clause))
                            continue
                        deltas.append(
                            StateDelta(
                                subject,
                                dimension,
                                self._projection_values(projections, subject, dimension),
                                args.get("role:value"),
                                clause.get("stance", "support"),
                                context_ref,
                            )
                        )
                    elif clause.get("operator") == "op:event":
                        secondary.append({"operator": "op:event", "args": args, "stance": clause.get("stance", "support")})
                if not deltas and not secondary:
                    continue
                payload = (row["rule_ref"], env, parent_refs, [x.as_dict() for x in deltas], secondary)
                previews.append(
                    TransitionPreview(
                        stable("transition-preview", payload),
                        str(row["rule_ref"]),
                        tuple(sorted(x.ref for x in trigger_facts)),
                        dict(env),
                        parent_refs,
                        tuple(deltas),
                        tuple(secondary),
                        float(row["confidence"]),
                        tuple(unresolved),
                        {
                            "rule_ref": row["rule_ref"],
                            "parents": list(parent_refs),
                            "causal_not_factual": True,
                            "epistemic_mode": "simulated",
                            "committed": False,
                        },
                    )
                )
        unique = {preview.preview_ref: preview for preview in previews}
        return tuple(unique[key] for key in sorted(unique))

    @staticmethod
    def prediction_errors(previews, observed_state_apps=()):
        observed = {
            (app.get("args", {}).get("role:subject"), app.get("args", {}).get("role:dimension")): app.get("args", {}).get("role:value")
            for app in observed_state_apps
            if app.get("operator") == "op:state"
        }
        output = []
        for preview in previews:
            for delta in preview.deltas:
                key = (delta.subject_ref, delta.dimension_ref)
                target = stable("state-target", *key)
                if key not in observed:
                    kind = "unobserved_prediction"
                    actual = None
                elif canonical(observed[key]) == canonical(delta.after):
                    kind = "prediction_confirmed"
                    actual = observed[key]
                else:
                    kind = "prediction_mismatch"
                    actual = observed[key]
                output.append(
                    PredictionError(
                        stable("prediction-error", preview.preview_ref, target, kind, delta.after, actual),
                        kind,
                        target,
                        delta.after,
                        actual,
                        preview.confidence,
                        preview.precondition_refs,
                    )
                )
        return tuple(output)

# CEMM_SOURCE_REWRITE:transitions:v3.1.3
