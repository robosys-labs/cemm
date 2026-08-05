"""Deterministic all-surface, all-context R4 case expansion.

Every expanded case receives a newly compiled ExpectedCycleContract whose
case/surface/context identities exactly match the expanded record.  A base
scenario contract is never re-used across surfaces or environmental contexts.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

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
)

CASE_EXPANSION_ABI_VERSION = 2
_MAX_ENVIRONMENTS = 64

__all__ = ["ExpandedCase", "CaseExpander", "CASE_EXPANSION_ABI_VERSION"]


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
        envs = tuple(environments) or ({},)
        if len(envs) > self._maximum:
            raise ValueError("reviewed environment expansion exceeds bound")
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
                            {"scenario_ref": scenario.scenario_ref},
                        ),
                    )
                )
                turn_index = int(environment.get("turn_index", surface_index))
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
