"""Cycle-local runtime evidence, usage receipts, and transition-state epistemics.

This module is the sole operational truth boundary for the Stage 0-22 runtime.
Resource health is observed from registered providers for the current cycle.  It
is never seeded as timeless authority and never converted from missing evidence
into numeric zero.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping, Sequence

from cemm.model import Fact, lit, now, stable

EPISTEMIC_MODES = frozenset(
    {"observed", "derived", "predicted", "simulated", "desired", "committed"}
)
RESOURCE_STATES = frozenset({"available", "degraded", "unavailable", "unknown"})
ASSESSMENT_STATES = frozenset(
    {"operating_normally", "degraded", "unavailable", "unknown"}
)

CANONICAL_RUNTIME_RESOURCES = (
    "resource:runtime_process",
    "resource:semantic_runtime",
    "resource:language_realizer",
    "resource:output_channel",
    "resource:inference_engine",
    "resource:designation_index",
    "resource:semantic_store",
    "resource:common_ground",
)

_AVAILABLE_THRESHOLD = 0.8



class OperationalProviderContractError(ValueError):
    """A registered provider or its returned value violates the provider ABI."""


class OperationalProviderExecutionError(RuntimeError):
    """A provider failed while collecting evidence; this is not an outage fact."""


class OperationalSnapshotIntegrityError(ValueError):
    """A snapshot is incomplete, mixed across cycles, or internally inconsistent."""


class OperationalInvariantError(RuntimeError):
    """A stage attempted to use resources outside its observed operating policy."""

def declared_operation_resources(
    component: Any,
    operation: str,
    *,
    baseline: Iterable[str] = (),
    allowed_resources: Iterable[str] = CANONICAL_RUNTIME_RESOURCES,
) -> tuple[str, ...]:
    """Resolve the exact resource-use contract for one component operation.

    Resource observation and resource use are separate concerns. A cycle may
    contain unknown evidence for an optional resource without blocking a test
    double or alternate implementation that does not use that resource. The
    concrete component declares additional use through
    ``operational_resources_for``; every declaration is checked against the
    canonical runtime ABI before a stage may rely on it.
    """
    allowed = frozenset(str(ref) for ref in allowed_resources)
    resources = {str(ref) for ref in baseline}
    invalid_baseline = sorted(resources - allowed)
    if invalid_baseline:
        raise OperationalProviderContractError(
            "baseline resources are outside runtime ABI: "
            + ",".join(invalid_baseline)
        )
    declaration = getattr(component, "operational_resources_for", None)
    if declaration is None:
        return tuple(sorted(resources))
    if not callable(declaration):
        raise OperationalProviderContractError(
            "operational_resources_for must be callable when present"
        )
    declared = declaration(str(operation))
    if isinstance(declared, (str, bytes)) or declared is None:
        raise OperationalProviderContractError(
            "operational resource declaration must be an iterable of resource refs"
        )
    try:
        declared_refs = tuple(str(ref) for ref in declared)
    except TypeError as exc:
        raise OperationalProviderContractError(
            "operational resource declaration is not iterable"
        ) from exc
    if any(not ref for ref in declared_refs):
        raise OperationalProviderContractError(
            "operational resource declaration contains an empty ref"
        )
    invalid = sorted(set(declared_refs) - allowed)
    if invalid:
        raise OperationalProviderContractError(
            "component declared resources outside runtime ABI: "
            + ",".join(invalid)
        )
    resources.update(declared_refs)
    return tuple(sorted(resources))


def validate_resource_state_score(state: str, score: float | None, *, label: str) -> None:
    if state not in RESOURCE_STATES:
        raise ValueError(f"{label}: invalid state {state!r}")
    if state == "unknown":
        if score is not None:
            raise ValueError(f"{label}: unknown evidence requires score=None")
        return
    if score is None:
        raise ValueError(f"{label}: {state} evidence requires a numeric score")
    numeric = float(score)
    if not 0.0 <= numeric <= 1.0:
        raise ValueError(f"{label}: score must be in [0,1]")
    if state == "available" and numeric < _AVAILABLE_THRESHOLD:
        raise ValueError(f"{label}: available score must be >= {_AVAILABLE_THRESHOLD}")
    if state == "degraded" and not 0.0 < numeric < _AVAILABLE_THRESHOLD:
        raise ValueError(f"{label}: degraded score must be in (0,{_AVAILABLE_THRESHOLD})")
    if state == "unavailable" and numeric != 0.0:
        raise ValueError(f"{label}: unavailable score must be exactly 0.0")


@dataclass(frozen=True)
class RuntimeResourceObservation:
    observation_ref: str
    resource_ref: str
    state: str
    score: float | None
    provider_ref: str
    observed_at: str
    cycle_ref: str
    authority_generation: int
    world_revision: int
    evidence: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.observation_ref:
            raise ValueError("runtime observation requires observation_ref")
        if not self.resource_ref.startswith("resource:"):
            raise ValueError(f"invalid runtime resource ref: {self.resource_ref}")
        if not self.provider_ref.startswith("provider:"):
            raise ValueError(f"invalid runtime provider ref: {self.provider_ref}")
        if not self.cycle_ref:
            raise ValueError("runtime observation requires cycle_ref")
        if int(self.authority_generation) < 1 or int(self.world_revision) < 0:
            raise ValueError("runtime observation carries invalid revision metadata")
        validate_resource_state_score(self.state, self.score, label=self.resource_ref)

    def as_dict(self) -> dict[str, Any]:
        return {
            "observation_ref": self.observation_ref,
            "resource_ref": self.resource_ref,
            "state": self.state,
            "score": self.score,
            "provider_ref": self.provider_ref,
            "observed_at": self.observed_at,
            "cycle_ref": self.cycle_ref,
            "authority_generation": self.authority_generation,
            "world_revision": self.world_revision,
            "evidence": dict(self.evidence),
            "epistemic_mode": "observed",
            "durable": False,
        }


@dataclass(frozen=True)
class OperationalAssessment:
    assessment_ref: str
    snapshot_ref: str
    status: str
    score: float | None
    critical_blockers: tuple[str, ...]
    degraded_resources: tuple[str, ...]
    unknown_resources: tuple[str, ...]
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.status not in ASSESSMENT_STATES:
            raise ValueError(f"invalid operational assessment: {self.status}")
        if self.status == "unknown":
            if self.score is not None or not self.unknown_resources:
                raise ValueError("unknown operational assessment requires unknown evidence and score=None")
        elif self.score is None or not 0.0 <= float(self.score) <= 1.0:
            raise ValueError("known operational assessment requires score in [0,1]")
        if self.status == "unavailable" and not self.critical_blockers:
            raise ValueError("unavailable operational assessment requires blockers")
        if self.status == "operating_normally" and (
            self.critical_blockers or self.degraded_resources or self.unknown_resources
        ):
            raise ValueError("normal operational assessment cannot carry blockers/degradation/unknowns")

    def as_dict(self) -> dict[str, Any]:
        return {
            "assessment_ref": self.assessment_ref,
            "snapshot_ref": self.snapshot_ref,
            "status": self.status,
            "score": self.score,
            "critical_blockers": list(self.critical_blockers),
            "degraded_resources": list(self.degraded_resources),
            "unknown_resources": list(self.unknown_resources),
            "evidence_refs": list(self.evidence_refs),
            "epistemic_mode": "derived",
            "durable": False,
        }


@dataclass(frozen=True)
class OperationalSnapshot:
    snapshot_ref: str
    self_ref: str
    cycle_ref: str
    authority_generation: int
    world_revision: int
    observations: tuple[RuntimeResourceObservation, ...]
    required_resources: tuple[str, ...] = CANONICAL_RUNTIME_RESOURCES
    critical_blockers: tuple[str, ...] = ()
    captured_at: str = field(default_factory=now)

    def __post_init__(self) -> None:
        required = tuple(self.required_resources)
        if len(required) != len(set(required)):
            raise OperationalSnapshotIntegrityError("required resource refs are duplicated")
        if set(required) != set(CANONICAL_RUNTIME_RESOURCES):
            raise OperationalSnapshotIntegrityError(
                "snapshot required-resource set differs from canonical runtime ABI"
            )
        refs = [item.resource_ref for item in self.observations]
        duplicates = sorted({ref for ref in refs if refs.count(ref) > 1})
        if duplicates:
            raise OperationalSnapshotIntegrityError(
                f"duplicate runtime observations: {duplicates}"
            )
        missing = sorted(set(required) - set(refs))
        extra = sorted(set(refs) - set(required))
        if missing or extra:
            raise OperationalSnapshotIntegrityError(
                f"runtime snapshot resource mismatch: missing={missing}, extra={extra}"
            )
        for item in self.observations:
            if item.cycle_ref != self.cycle_ref:
                raise OperationalSnapshotIntegrityError("runtime observation crosses cycle boundary")
            if int(item.authority_generation) != int(self.authority_generation):
                raise OperationalSnapshotIntegrityError("runtime observation crosses authority generation")
            if int(item.world_revision) != int(self.world_revision):
                raise OperationalSnapshotIntegrityError("runtime observation crosses world revision")
        expected_blockers = tuple(
            sorted(
                item.resource_ref
                for item in self.observations
                if item.resource_ref in set(required) and item.state == "unavailable"
            )
        )
        if tuple(sorted(self.critical_blockers)) != expected_blockers:
            raise OperationalSnapshotIntegrityError(
                "critical blockers must equal required resources observed unavailable"
            )
        by_ref = {item.resource_ref: item for item in self.observations}
        expected_ref = stable(
            "operational-snapshot",
            self.self_ref,
            self.cycle_ref,
            int(self.authority_generation),
            int(self.world_revision),
            [by_ref[ref].as_dict() for ref in required],
            required,
        )
        if self.snapshot_ref != expected_ref:
            raise OperationalSnapshotIntegrityError("operational snapshot_ref does not match content")

    @property
    def by_resource(self) -> dict[str, RuntimeResourceObservation]:
        return {item.resource_ref: item for item in self.observations}

    def observation(self, resource_ref: str) -> RuntimeResourceObservation:
        item = self.by_resource.get(resource_ref)
        if item is None:
            raise OperationalSnapshotIntegrityError(
                f"snapshot has no observation for {resource_ref}"
            )
        return item

    def score(self, resource_ref: str) -> float | None:
        item = self.observation(resource_ref)
        return None if item.state == "unknown" else float(item.score)

    def state(self, resource_ref: str) -> str:
        return self.observation(resource_ref).state

    def assess(self) -> OperationalAssessment:
        unknown = tuple(sorted(x.resource_ref for x in self.observations if x.state == "unknown"))
        degraded = tuple(sorted(x.resource_ref for x in self.observations if x.state == "degraded"))
        known_scores = [float(x.score) for x in self.observations if x.score is not None]
        minimum = min(known_scores) if known_scores else None
        if self.critical_blockers:
            status = "unavailable"
            score = 0.0
        elif unknown:
            status = "unknown"
            score = None
        elif degraded:
            status = "degraded"
            score = minimum
        else:
            status = "operating_normally"
            score = minimum if minimum is not None else 1.0
        payload = (
            self.snapshot_ref,
            status,
            score,
            self.critical_blockers,
            degraded,
            unknown,
        )
        return OperationalAssessment(
            stable("operational-assessment", payload),
            self.snapshot_ref,
            status,
            score,
            tuple(self.critical_blockers),
            degraded,
            unknown,
            tuple(x.observation_ref for x in sorted(self.observations, key=lambda y: y.resource_ref)),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "snapshot_ref": self.snapshot_ref,
            "self_ref": self.self_ref,
            "cycle_ref": self.cycle_ref,
            "authority_generation": self.authority_generation,
            "world_revision": self.world_revision,
            "observations": [x.as_dict() for x in sorted(self.observations, key=lambda y: y.resource_ref)],
            "required_resources": list(self.required_resources),
            "critical_blockers": list(self.critical_blockers),
            "captured_at": self.captured_at,
            "assessment": self.assess().as_dict(),
            "epistemic_mode": "observed",
            "durable": False,
        }

    def semantic_facts(self) -> tuple[Fact, ...]:
        """Expose compact, cycle-local self-support facts using base-owned dimensions."""
        by = self.by_resource

        def known_score(resource_ref: str) -> float | None:
            item = by[resource_ref]
            return None if item.state == "unknown" else float(item.score)

        dependencies = (
            "resource:semantic_runtime",
            "resource:inference_engine",
            "resource:designation_index",
            "resource:semantic_store",
            "resource:common_ground",
        )
        dependency_scores = [known_score(ref) for ref in dependencies]
        values: list[tuple[str, Any, str]] = []
        runtime_score = known_score("resource:runtime_process")
        if runtime_score is not None:
            values.append(("dim:runtime_process_support", runtime_score, "float"))
        if all(value is not None for value in dependency_scores):
            values.append(
                (
                    "dim:semantic_runtime_support",
                    min(float(value) for value in dependency_scores if value is not None),
                    "float",
                )
            )
        realizer_score = known_score("resource:language_realizer")
        if realizer_score is not None:
            values.append(("dim:language_realizer_support", realizer_score, "float"))
        values.append(("dim:critical_blocker_count", len(self.critical_blockers), "int"))
        return tuple(
            Fact(
                stable("runtime-support-fact", self.snapshot_ref, dimension, value),
                "op:state",
                {
                    "role:subject": self.self_ref,
                    "role:dimension": dimension,
                    "role:value": lit(value, literal_type),
                },
                "support",
                1.0,
                True,
                {
                    "runtime_provider": True,
                    "snapshot_ref": self.snapshot_ref,
                    "epistemic_mode": "derived",
                    "durable": False,
                },
            )
            for dimension, value, literal_type in values
        )


@dataclass(frozen=True)
class _ServiceProbe:
    resource_ref: str
    provider_ref: str
    probe: Callable[[], Any]
    required: bool = True


class RuntimeServiceRegistry:
    """Exact registry and live probe source for all runtime resources."""

    def __init__(self) -> None:
        self._probes: dict[str, _ServiceProbe] = {}

    def register(
        self,
        resource_ref: str,
        probe: Callable[[], Any],
        *,
        provider_ref: str | None = None,
        required: bool = True,
    ) -> None:
        if resource_ref not in CANONICAL_RUNTIME_RESOURCES:
            raise OperationalProviderContractError(
                f"resource is outside canonical runtime ABI: {resource_ref}"
            )
        if not callable(probe):
            raise TypeError("runtime resource probe must be callable")
        if resource_ref in self._probes:
            raise OperationalProviderContractError(
                f"runtime resource already registered: {resource_ref}"
            )
        provider = provider_ref or f"provider:{resource_ref.split(':', 1)[1]}"
        if not provider.startswith("provider:"):
            raise OperationalProviderContractError(f"invalid provider_ref: {provider}")
        self._probes[resource_ref] = _ServiceProbe(
            resource_ref, provider, probe, bool(required)
        )

    def register_object(
        self,
        resource_ref: str,
        owner: Any,
        attribute: str,
        *,
        health_method: str | None = None,
        required: bool = True,
    ) -> None:
        if not isinstance(attribute, str) or not attribute:
            raise OperationalProviderContractError("object probe requires attribute name")

        def probe() -> Any:
            if not hasattr(owner, attribute):
                raise OperationalProviderContractError(
                    f"registered owner has no attribute {attribute!r}"
                )
            value = getattr(owner, attribute)
            if value is None:
                return {"state": "unavailable", "score": 0.0, "present": False}
            if health_method:
                method = getattr(value, health_method, None)
                if not callable(method):
                    raise OperationalProviderContractError(
                        f"registered service lacks health method {health_method!r}"
                    )
                health = method()
                if isinstance(health, Mapping):
                    return {**dict(health), "present": True, "health_method": health_method}
                return health, {"present": True, "health_method": health_method}
            return True, {"attribute": attribute, "present": True}

        self.register(resource_ref, probe, required=required)

    @staticmethod
    def _normalize_probe_result(result: Any) -> tuple[str, float | None, dict[str, Any]]:
        evidence: dict[str, Any] = {}
        raw = result
        if isinstance(result, tuple):
            if len(result) != 2:
                raise OperationalProviderContractError(
                    "probe tuple must contain exactly (value, evidence)"
                )
            raw, supplied = result
            if supplied is not None and not isinstance(supplied, Mapping):
                raise OperationalProviderContractError(
                    "probe evidence must be a mapping or None"
                )
            evidence.update(dict(supplied or {}))
        if isinstance(raw, Mapping):
            state = str(raw.get("state", "unknown"))
            score = raw.get("score")
            if state == "available" and score is None:
                score = 1.0
            if state == "unavailable" and score is None:
                score = 0.0
            if score is not None:
                try:
                    score = float(score)
                except (TypeError, ValueError) as exc:
                    raise OperationalProviderContractError("probe score must be numeric") from exc
            try:
                validate_resource_state_score(state, score, label="provider result")
            except ValueError as exc:
                raise OperationalProviderContractError(str(exc)) from exc
            evidence.update({k: v for k, v in raw.items() if k not in {"state", "score"}})
            return state, score, evidence
        if isinstance(raw, bool):
            return ("available", 1.0, evidence) if raw else ("unavailable", 0.0, evidence)
        if isinstance(raw, (int, float)):
            score = float(raw)
            state = "available" if score >= _AVAILABLE_THRESHOLD else "degraded" if score > 0 else "unavailable"
            try:
                validate_resource_state_score(state, score, label="numeric provider result")
            except ValueError as exc:
                raise OperationalProviderContractError(str(exc)) from exc
            return state, score, evidence
        if raw is None:
            return "unknown", None, evidence
        raise OperationalProviderContractError(
            f"unsupported probe result type: {type(raw).__name__}"
        )

    def validate_resources(self, expected: Sequence[str] = CANONICAL_RUNTIME_RESOURCES) -> None:
        expected_tuple = tuple(expected)
        if len(expected_tuple) != len(set(expected_tuple)):
            raise OperationalProviderContractError("expected resource ABI contains duplicates")
        actual = set(self._probes)
        required = set(expected_tuple)
        missing = sorted(required - actual)
        extra = sorted(actual - required)
        if missing or extra:
            raise OperationalProviderContractError(
                f"runtime service registry mismatch: missing={missing}, extra={extra}"
            )
        nonrequired = sorted(ref for ref, item in self._probes.items() if not item.required)
        if nonrequired:
            raise OperationalProviderContractError(
                f"canonical runtime resources must all be required: {nonrequired}"
            )

    def capture(
        self,
        *,
        self_ref: str,
        cycle_ref: str,
        authority_generation: int,
        world_revision: int,
    ) -> OperationalSnapshot:
        self.validate_resources()
        observed_at = now()
        observations: list[RuntimeResourceObservation] = []
        for resource_ref in CANONICAL_RUNTIME_RESOURCES:
            service = self._probes[resource_ref]
            try:
                result = service.probe()
            except OperationalProviderContractError:
                raise
            except Exception as exc:
                raise OperationalProviderExecutionError(
                    f"runtime provider execution failed: {service.provider_ref} for {resource_ref}"
                ) from exc
            state, score, evidence = self._normalize_probe_result(result)
            payload = (
                resource_ref,
                state,
                score,
                service.provider_ref,
                cycle_ref,
                int(authority_generation),
                int(world_revision),
                evidence,
            )
            observations.append(
                RuntimeResourceObservation(
                    stable("runtime-resource-observation", payload),
                    resource_ref,
                    state,
                    score,
                    service.provider_ref,
                    observed_at,
                    cycle_ref,
                    int(authority_generation),
                    int(world_revision),
                    evidence,
                )
            )
        blockers = tuple(sorted(x.resource_ref for x in observations if x.state == "unavailable"))
        snapshot_ref = stable(
            "operational-snapshot",
            self_ref,
            cycle_ref,
            int(authority_generation),
            int(world_revision),
            [x.as_dict() for x in observations],
            CANONICAL_RUNTIME_RESOURCES,
        )
        return OperationalSnapshot(
            snapshot_ref,
            self_ref,
            cycle_ref,
            int(authority_generation),
            int(world_revision),
            tuple(observations),
            CANONICAL_RUNTIME_RESOURCES,
            blockers,
            observed_at,
        )

    def resources(self) -> tuple[str, ...]:
        return tuple(ref for ref in CANONICAL_RUNTIME_RESOURCES if ref in self._probes)


@dataclass(frozen=True)
class StageResourceUse:
    use_ref: str
    snapshot_ref: str
    cycle_ref: str
    stage: int
    resource_ref: str
    observation_ref: str
    observed_state: str
    observed_score: float | None
    minimum_score: float
    degraded_allowed: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "use_ref": self.use_ref,
            "snapshot_ref": self.snapshot_ref,
            "cycle_ref": self.cycle_ref,
            "stage": self.stage,
            "resource_ref": self.resource_ref,
            "observation_ref": self.observation_ref,
            "observed_state": self.observed_state,
            "observed_score": self.observed_score,
            "minimum_score": self.minimum_score,
            "degraded_allowed": self.degraded_allowed,
        }


class OperationalUsageLedger:
    def __init__(self, snapshot: OperationalSnapshot):
        self.snapshot_ref = snapshot.snapshot_ref
        self.cycle_ref = snapshot.cycle_ref
        self._uses: list[StageResourceUse] = []

    def record(self, use: StageResourceUse) -> None:
        if use.snapshot_ref != self.snapshot_ref or use.cycle_ref != self.cycle_ref:
            raise OperationalInvariantError("resource-use receipt crosses snapshot/cycle")
        if any(existing.use_ref == use.use_ref for existing in self._uses):
            return
        self._uses.append(use)

    @property
    def uses(self) -> tuple[StageResourceUse, ...]:
        return tuple(self._uses)

    def as_dict(self) -> dict[str, Any]:
        return {
            "snapshot_ref": self.snapshot_ref,
            "cycle_ref": self.cycle_ref,
            "uses": [x.as_dict() for x in self._uses],
        }


class OperationalInvariantChecker:
    @staticmethod
    def require_resource(
        snapshot: OperationalSnapshot,
        resource_ref: str,
        *,
        stage: int,
        ledger: OperationalUsageLedger | None = None,
        allow_degraded: bool = False,
        minimum_score: float = _AVAILABLE_THRESHOLD,
    ) -> StageResourceUse:
        item = snapshot.observation(resource_ref)
        if item.state == "unknown":
            raise OperationalInvariantError(
                f"stage {stage} used {resource_ref} without resolved operational evidence"
            )
        if item.state == "unavailable":
            raise OperationalInvariantError(
                f"stage {stage} used {resource_ref} despite observed unavailability"
            )
        if item.state == "degraded" and not allow_degraded:
            raise OperationalInvariantError(
                f"stage {stage} used degraded {resource_ref} without explicit policy"
            )
        numeric = float(item.score)
        if numeric < float(minimum_score) and not (allow_degraded and item.state == "degraded"):
            raise OperationalInvariantError(
                f"stage {stage} used {resource_ref} below minimum support {minimum_score}"
            )
        payload = (
            snapshot.snapshot_ref,
            stage,
            resource_ref,
            item.observation_ref,
            item.state,
            item.score,
            float(minimum_score),
            bool(allow_degraded),
        )
        use = StageResourceUse(
            stable("stage-resource-use", payload),
            snapshot.snapshot_ref,
            snapshot.cycle_ref,
            int(stage),
            resource_ref,
            item.observation_ref,
            item.state,
            item.score,
            float(minimum_score),
            bool(allow_degraded),
        )
        if ledger is not None:
            ledger.record(use)
        return use

    @staticmethod
    def check_stage_usage(
        snapshot: OperationalSnapshot,
        used_resources: Iterable[str],
        *,
        stage: int,
        ledger: OperationalUsageLedger | None = None,
        allow_degraded: bool = False,
        minimum_score: float = _AVAILABLE_THRESHOLD,
    ) -> tuple[StageResourceUse, ...]:
        return tuple(
            OperationalInvariantChecker.require_resource(
                snapshot,
                resource_ref,
                stage=stage,
                ledger=ledger,
                allow_degraded=allow_degraded,
                minimum_score=minimum_score,
            )
            for resource_ref in sorted(set(used_resources))
        )

    @staticmethod
    def check_transition_preview(preview: Any) -> None:
        proof = dict(getattr(preview, "proof", {}) or {})
        if proof.get("committed") is True:
            raise OperationalInvariantError(
                "transition preview claims committed state before operation evidence"
            )
        if proof.get("causal_not_factual") is not True:
            raise OperationalInvariantError(
                "transition preview must remain explicitly causal/not factual"
            )
        if proof.get("epistemic_mode") != "simulated":
            raise OperationalInvariantError(
                "transition preview must carry epistemic_mode=simulated"
            )


@dataclass(frozen=True)
class StateAssertion:
    assertion_ref: str
    subject_ref: str
    dimension_ref: str
    value: Any
    epistemic_mode: str
    source_ref: str
    confidence: float = 1.0
    context_ref: str | None = None
    cycle_ref: str | None = None
    durable: bool = False

    def __post_init__(self) -> None:
        if self.epistemic_mode not in EPISTEMIC_MODES:
            raise ValueError(f"invalid epistemic mode: {self.epistemic_mode}")
        if self.epistemic_mode in {"predicted", "simulated", "desired"} and self.durable:
            raise ValueError(f"{self.epistemic_mode} state cannot be durable")
        if self.durable and self.epistemic_mode not in {"observed", "committed"}:
            raise ValueError(
                f"durable state requires observed or committed mode, got {self.epistemic_mode}"
            )
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError("state confidence must be in [0,1]")

    def as_dict(self) -> dict[str, Any]:
        return {
            "assertion_ref": self.assertion_ref,
            "subject_ref": self.subject_ref,
            "dimension_ref": self.dimension_ref,
            "value": self.value,
            "epistemic_mode": self.epistemic_mode,
            "source_ref": self.source_ref,
            "confidence": self.confidence,
            "context_ref": self.context_ref,
            "cycle_ref": self.cycle_ref,
            "durable": self.durable,
        }


@dataclass(frozen=True)
class TransitionReceipt:
    receipt_ref: str
    preview_ref: str
    mode: str
    preconditions_satisfied: bool
    deltas: tuple[Mapping[str, Any], ...]
    operation_ref: str | None = None
    observed_evidence_refs: tuple[str, ...] = ()
    committed_fact_refs: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.mode not in {"simulated", "committed", "rejected"}:
            raise ValueError(f"invalid transition receipt mode: {self.mode}")
        if self.mode != "committed" and self.committed_fact_refs:
            raise ValueError("non-committed transition cannot carry committed facts")
        if self.mode == "committed" and not self.preconditions_satisfied:
            raise ValueError("committed transition requires satisfied preconditions")
        if self.mode == "committed" and not self.observed_evidence_refs:
            raise ValueError("committed transition requires operation/observation evidence")

    def as_dict(self) -> dict[str, Any]:
        return {
            "receipt_ref": self.receipt_ref,
            "preview_ref": self.preview_ref,
            "mode": self.mode,
            "preconditions_satisfied": self.preconditions_satisfied,
            "deltas": [dict(item) for item in self.deltas],
            "operation_ref": self.operation_ref,
            "observed_evidence_refs": list(self.observed_evidence_refs),
            "committed_fact_refs": list(self.committed_fact_refs),
            "blockers": list(self.blockers),
        }
