"""Deterministic all-surface, all-context R4 case expansion.

Every expanded case receives a newly compiled ExpectedCycleContract whose
case/surface/context identities exactly match the expanded record.  A base
scenario contract is never re-used across surfaces or environmental contexts.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Iterable, Mapping

from .authority import LinkedAuthority
from .canonical import stable_ref
from .persistence import RevisionPin
from .r3_codec import (
    exact_fields,
    exact_int,
    exact_refs,
    exact_text,
    freeze_json,
    thaw_json,
    wire_refs,
)
from .r4_contracts import (
    ExpectedCycleContract,
    ExpectedCycleContractCompiler,
    ReviewedScenario,
    SourceDisposition,
    classify_source_disposition,
)

CASE_EXPANSION_ABI_VERSION = 2
_MAX_ENVIRONMENTS = 64
_MAX_SCENARIOS = 512
_MAX_EXPANDED_CASES = 4096

__all__ = [
    "ExpandedCase",
    "CaseExpander",
    "SourceDisposition",
    "SourceUniverse",
    "expand_reviewed_source_universe",
    "CASE_EXPANSION_ABI_VERSION",
]


def _bounded_items(
    iterable: Iterable[Any],
    maximum: int,
    name: str,
    *,
    operation_counts: dict[str, int] | None = None,
    operation_name: str | None = None,
) -> tuple[Any, ...]:
    iterator = iter(iterable)
    rows: list[Any] = []
    for _ in range(maximum + 1):
        try:
            row = next(iterator)
        except StopIteration:
            if operation_counts is not None and operation_name is not None:
                operation_counts[operation_name] += 1
            return tuple(rows)
        if operation_counts is not None and operation_name is not None:
            operation_counts[operation_name] += 1
        if len(rows) == maximum:
            raise ValueError(f"{name} exceeds bound")
        rows.append(row)
    raise AssertionError("bounded iterator loop did not terminate")


@dataclass(frozen=True)
class SourceUniverse:
    cases: tuple["ExpandedCase", ...]
    scenario_count: int
    expanded_count: int
    disposition_counts: Mapping[str, int]
    case_set_digest: str
    operation_counts: Mapping[str, int]

    def __post_init__(self) -> None:
        if type(self.cases) is not tuple:
            raise TypeError("source universe cases must be an exact tuple")
        object.__setattr__(
            self, "disposition_counts", MappingProxyType(dict(self.disposition_counts))
        )
        object.__setattr__(
            self, "operation_counts", MappingProxyType(dict(self.operation_counts))
        )


def _mapping(value: object, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be a mapping")
    result = freeze_json(dict(value))
    if not isinstance(result, Mapping):
        raise TypeError(f"{name} must freeze to a mapping")
    return result


@dataclass(frozen=True, init=False)
class ExpandedCase:
    abi_version: int
    case_ref: str
    scenario_ref: str
    surface_ref: str
    context_ref: str
    contract: ExpectedCycleContract
    surface: str
    surface_index: int
    environment_index: int
    language: str
    environment: Mapping[str, Any]
    trajectory_ref: str
    turn_index: int
    lineage_refs: tuple[str, ...]

    _FIELDS = frozenset(
        {
            "abi_version",
            "case_ref",
            "scenario_ref",
            "surface_ref",
            "context_ref",
            "contract",
            "surface",
            "surface_index",
            "environment_index",
            "language",
            "environment",
            "trajectory_ref",
            "turn_index",
            "lineage_refs",
        }
    )

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise TypeError("use ExpandedCase.create")

    @staticmethod
    def identity_material(
        *,
        scenario_ref: str,
        surface_ref: str,
        context_ref: str,
        surface_index: int,
        environment_index: int,
        trajectory_ref: str,
        turn_index: int,
    ) -> dict[str, Any]:
        return {
            "abi_version": CASE_EXPANSION_ABI_VERSION,
            "scenario_ref": scenario_ref,
            "surface_ref": surface_ref,
            "context_ref": context_ref,
            "surface_index": surface_index,
            "environment_index": environment_index,
            "trajectory_ref": trajectory_ref,
            "turn_index": turn_index,
        }

    @classmethod
    def create(
        cls,
        *,
        scenario_ref: str,
        surface_ref: str,
        context_ref: str,
        contract: ExpectedCycleContract,
        surface: str,
        surface_index: int,
        environment_index: int,
        language: str,
        environment: Mapping[str, Any],
        trajectory_ref: str,
        turn_index: int,
        lineage_refs: tuple[str, ...],
    ) -> "ExpandedCase":
        if cls is not ExpandedCase:
            raise TypeError("ExpandedCase factories require exact class")
        if type(contract) is not ExpectedCycleContract:
            raise TypeError("contract must be exact ExpectedCycleContract")
        scenario = exact_text(scenario_ref, "scenario_ref")
        surface_identity = exact_text(surface_ref, "surface_ref")
        context_identity = exact_text(context_ref, "context_ref")
        surface_position = exact_int(surface_index, "surface_index")
        environment_position = exact_int(environment_index, "environment_index")
        trajectory = exact_text(trajectory_ref, "trajectory_ref")
        turn = exact_int(turn_index, "turn_index", minimum=0)
        material = cls.identity_material(
            scenario_ref=scenario,
            surface_ref=surface_identity,
            context_ref=context_identity,
            surface_index=surface_position,
            environment_index=environment_position,
            trajectory_ref=trajectory,
            turn_index=turn,
        )
        case_ref = stable_ref("expanded_case_v2", material)
        if (
            contract.scenario_ref != scenario
            or contract.case_ref != case_ref
            or contract.surface_ref != surface_identity
            or contract.context_ref != context_identity
        ):
            raise ValueError("expanded case contract does not bind exact case identities")
        values = {
            "case_ref": case_ref,
            "scenario_ref": scenario,
            "surface_ref": surface_identity,
            "context_ref": context_identity,
            "contract": contract,
            "surface": exact_text(surface, "surface", allow_empty=True, maximum=16_384),
            "surface_index": surface_position,
            "environment_index": environment_position,
            "language": exact_text(language, "language"),
            "environment": _mapping(environment, "environment"),
            "trajectory_ref": trajectory,
            "turn_index": turn,
            "lineage_refs": exact_refs(lineage_refs, "lineage_refs", nonempty=True),
        }
        obj = object.__new__(cls)
        object.__setattr__(obj, "abi_version", CASE_EXPANSION_ABI_VERSION)
        for name, value in values.items():
            object.__setattr__(obj, name, value)
        return obj

    @property
    def contract_ref(self) -> str:
        return self.contract.contract_ref

    @property
    def source_disposition(self) -> SourceDisposition:
        return {
            "gap": SourceDisposition.EXPLICIT_GAP,
            "verification_rejection": SourceDisposition.VERIFICATION_REJECTION,
            "restart": SourceDisposition.RESTART_DIAGNOSTIC_CANDIDATE,
        }.get(self.contract.outcome_kind.value, SourceDisposition.SEMANTIC)

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": self.abi_version,
            "case_ref": self.case_ref,
            "scenario_ref": self.scenario_ref,
            "surface_ref": self.surface_ref,
            "context_ref": self.context_ref,
            "contract": self.contract.as_dict(),
            "surface": self.surface,
            "surface_index": self.surface_index,
            "environment_index": self.environment_index,
            "language": self.language,
            "environment": thaw_json(self.environment),
            "trajectory_ref": self.trajectory_ref,
            "turn_index": self.turn_index,
            "lineage_refs": list(self.lineage_refs),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ExpandedCase":
        row = exact_fields(value, cls._FIELDS, "ExpandedCase")
        if row["abi_version"] != CASE_EXPANSION_ABI_VERSION:
            raise ValueError("unsupported Expanded Case ABI")
        if type(row["contract"]) is not dict or type(row["environment"]) is not dict:
            raise TypeError("expanded case nested artifacts must be exact dicts")
        rebuilt = cls.create(
            scenario_ref=row["scenario_ref"],
            surface_ref=row["surface_ref"],
            context_ref=row["context_ref"],
            contract=ExpectedCycleContract.from_dict(row["contract"]),
            surface=row["surface"],
            surface_index=row["surface_index"],
            environment_index=row["environment_index"],
            language=row["language"],
            environment=row["environment"],
            trajectory_ref=row["trajectory_ref"],
            turn_index=row["turn_index"],
            lineage_refs=wire_refs(row["lineage_refs"], "lineage_refs", nonempty=True),
        )
        if rebuilt.case_ref != row["case_ref"] or rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical ExpandedCase encoding")
        return rebuilt


class CaseExpander:
    """Compile a distinct expected contract for every reviewed surface/context."""

    def __init__(
        self,
        compiler: ExpectedCycleContractCompiler,
        *,
        max_environments_per_surface: int = 16,
    ) -> None:
        if type(compiler) is not ExpectedCycleContractCompiler:
            raise TypeError("compiler must be exact ExpectedCycleContractCompiler")
        self._compiler = compiler
        self._maximum = exact_int(
            max_environments_per_surface,
            "max_environments_per_surface",
            minimum=1,
            maximum=_MAX_ENVIRONMENTS,
        )

    @staticmethod
    def _situation_constraints(environment: Mapping[str, Any]) -> Mapping[str, Any]:
        explicit = environment.get("situation_constraints")
        if explicit is not None:
            if not isinstance(explicit, Mapping):
                raise TypeError("situation_constraints environment field must be a mapping")
            constraints = dict(explicit)
        else:
            constraints = {
                key: value
                for key, value in environment.items()
                if key
                not in {
                    "evidence_items",
                    "language",
                    "trajectory_ref",
                    "turn_index",
                    "session_ref",
                }
            }
        return constraints

    def expand(
        self,
        scenario: ReviewedScenario,
        *,
        revision_pin: RevisionPin,
        environments: Iterable[Mapping[str, Any]] = ({},),
    ) -> tuple[ExpandedCase, ...]:
        if type(scenario) is not ReviewedScenario:
            raise TypeError("scenario must be exact ReviewedScenario")
        if type(revision_pin) is not RevisionPin:
            raise TypeError("revision_pin must be exact RevisionPin")
        envs = _bounded_items(environments, self._maximum, "reviewed environment")
        if not envs:
            envs = ({},)
        if any(not isinstance(row, Mapping) for row in envs):
            raise TypeError("environments must contain mappings")
        language_default = str(thaw_json(scenario.metadata).get("language", "en"))
        rows: list[ExpandedCase] = []
        for surface_index, surface in enumerate(scenario.surface_examples):
            language_surface_ref = stable_ref(
                "reviewed_surface",
                {
                    "scenario_ref": scenario.scenario_ref,
                    "surface": surface,
                    "surface_index": surface_index,
                    "language": language_default,
                },
            )
            for environment_index, raw_environment in enumerate(envs):
                environment = dict(raw_environment)
                language = str(environment.get("language", language_default))
                context_ref = stable_ref(
                    "reviewed_environment",
                    {
                        "scenario_ref": scenario.scenario_ref,
                        "environment_index": environment_index,
                        "environment": environment,
                    },
                )
                trajectory_ref = str(
                    environment.get(
                        "trajectory_ref",
                        stable_ref(
                            "reviewed_trajectory",
                            {
                                "scenario_ref": scenario.scenario_ref,
                                "surface_index": surface_index,
                                "environment_index": environment_index,
                            },
                        ),
                    )
                )
                turn_index = int(environment.get("turn_index", 0))
                material = ExpandedCase.identity_material(
                    scenario_ref=scenario.scenario_ref,
                    surface_ref=language_surface_ref,
                    context_ref=context_ref,
                    surface_index=surface_index,
                    environment_index=environment_index,
                    trajectory_ref=trajectory_ref,
                    turn_index=turn_index,
                )
                case_ref = stable_ref("expanded_case_v2", material)
                contract = self._compiler.compile(
                    scenario_ref=scenario.scenario_ref,
                    case_ref=case_ref,
                    surface_ref=language_surface_ref,
                    context_ref=context_ref,
                    assertions=scenario.assertions,
                    situation_constraints=self._situation_constraints(environment),
                    revision_pin=revision_pin,
                    surface_text=surface,
                    surface_language=language,
                )
                rows.append(
                    ExpandedCase.create(
                        scenario_ref=scenario.scenario_ref,
                        surface_ref=language_surface_ref,
                        context_ref=context_ref,
                        contract=contract,
                        surface=surface,
                        surface_index=surface_index,
                        environment_index=environment_index,
                        language=language,
                        environment=environment,
                        trajectory_ref=trajectory_ref,
                        turn_index=turn_index,
                        lineage_refs=(
                            scenario.scenario_ref,
                            contract.contract_ref,
                            stable_ref(
                                "surface_family",
                                {"scenario_ref": scenario.scenario_ref},
                            ),
                            stable_ref(
                                "environment_family",
                                {
                                    "scenario_ref": scenario.scenario_ref,
                                    "environment": environment,
                                },
                            ),
                            trajectory_ref,
                        ),
                    )
                )
        return tuple(rows)


def expand_reviewed_source_universe(
    scenarios: Iterable[ReviewedScenario],
    *,
    authority: LinkedAuthority,
    reviewed_environments: Mapping[str, Iterable[Mapping[str, Any]]] | None = None,
    max_scenarios: int = _MAX_SCENARIOS,
    max_environments_per_surface: int = 16,
    max_expanded_cases: int = _MAX_EXPANDED_CASES,
) -> SourceUniverse:
    """Reconstruct the reviewed source universe without runtime/model state."""

    if type(authority) is not LinkedAuthority:
        raise TypeError("authority must be exact authenticated LinkedAuthority")
    scenario_limit = exact_int(
        max_scenarios, "max_scenarios", minimum=1, maximum=_MAX_SCENARIOS
    )
    environment_limit = exact_int(
        max_environments_per_surface,
        "max_environments_per_surface",
        minimum=1,
        maximum=_MAX_ENVIRONMENTS,
    )
    case_limit = exact_int(
        max_expanded_cases,
        "max_expanded_cases",
        minimum=1,
        maximum=_MAX_EXPANDED_CASES,
    )
    if reviewed_environments is not None and type(reviewed_environments) is not dict:
        raise TypeError("reviewed_environments must be an exact dict")
    if reviewed_environments is not None and len(reviewed_environments) > scenario_limit:
        raise ValueError("reviewed environment map exceeds scenario bound")
    operation_counts = {
        "scenario_next_calls": 0,
        "environment_next_calls": 0,
        "disposition_classifications": 0,
        "aggregate_bound_checks": 0,
        "case_emissions": 0,
    }
    source_rows = _bounded_items(
        scenarios,
        scenario_limit,
        "reviewed scenario",
        operation_counts=operation_counts,
        operation_name="scenario_next_calls",
    )
    if any(type(row) is not ReviewedScenario for row in source_rows):
        raise TypeError("source scenarios must contain exact ReviewedScenario values")
    scenario_refs = tuple(row.scenario_ref for row in source_rows)
    if len(scenario_refs) != len(set(scenario_refs)):
        raise ValueError("source scenario refs must be unique")
    if reviewed_environments is not None:
        unknown = set(reviewed_environments) - set(scenario_refs)
        if unknown:
            raise ValueError(f"reviewed environments contain unknown scenarios: {sorted(unknown)}")

    pin = RevisionPin(authority.generation, 0, 0, 0, 0, None)
    expander = CaseExpander(
        ExpectedCycleContractCompiler(authority, abi_registry_ref="abi_registry:active"),
        max_environments_per_surface=environment_limit,
    )
    cases: list[ExpandedCase] = []
    disposition_counts = {row.value: 0 for row in SourceDisposition}
    for scenario in source_rows:
        disposition = classify_source_disposition(scenario)
        operation_counts["disposition_classifications"] += 1
        metadata = scenario.metadata
        raw_environments: Iterable[Mapping[str, Any]]
        if reviewed_environments is not None and scenario.scenario_ref in reviewed_environments:
            raw_environments = reviewed_environments[scenario.scenario_ref]
        else:
            raw_environments = metadata.get("environments", ({},))
        envs = _bounded_items(
            raw_environments,
            environment_limit,
            "reviewed environment",
            operation_counts=operation_counts,
            operation_name="environment_next_calls",
        )
        if not envs:
            envs = ({},)
        if any(not isinstance(row, Mapping) for row in envs):
            raise TypeError("environments must contain mappings")
        environment_refs = tuple(
            stable_ref("reviewed_environment_value", dict(row)) for row in envs
        )
        if len(environment_refs) != len(set(environment_refs)):
            raise ValueError("duplicate reviewed environments are forbidden")
        reserved = len(scenario.surface_examples) * len(envs)
        operation_counts["aggregate_bound_checks"] += 1
        if reserved > case_limit - len(cases):
            raise ValueError("aggregate expanded case stream exceeds bound")
        expanded = expander.expand(scenario, revision_pin=pin, environments=envs)
        if len(expanded) != reserved:
            raise ValueError("case expansion cardinality differs from reservation")
        for case in expanded:
            if case.source_disposition is not disposition:
                raise ValueError("expanded contract disposition differs from source assertion")
            cases.append(case)
            disposition_counts[disposition.value] += 1
            operation_counts["case_emissions"] += 1
    case_refs = sorted(row.case_ref for row in cases)
    if len(case_refs) != len(set(case_refs)):
        raise ValueError("expanded case refs must be unique")
    digest_bytes = ("\n".join(case_refs) + "\n").encode("utf-8")
    return SourceUniverse(
        cases=tuple(cases),
        scenario_count=len(source_rows),
        expanded_count=len(cases),
        disposition_counts=disposition_counts,
        case_set_digest=hashlib.sha256(digest_bytes).hexdigest(),
        operation_counts=operation_counts,
    )
