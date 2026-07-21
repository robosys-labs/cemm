"""Bounded declarative semantic-construction programs for CEMM v3.5.

Construction matching remains language evidence. This module turns reviewed
construction programs into finite semantic plans. It never executes arbitrary
code and never branches on surface words.

The legacy fixed-output compiler exists only to keep signed pre-program boot
records readable while the Phase-9 seed migration is pending. Explicit
ConstructionProgramRecord authority always wins and compatibility is trace-marked.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Iterable, Mapping

from ..facets.closure import SemanticClosureCandidate
from ..schema.model import (
    OpenBindingPurpose,
    PortFillerClass,
    SchemaClass,
    UseDecision,
    UseOperation,
    semantic_fingerprint,
)
from .model import (
    ConstructionProgramOperation,
    ConstructionProgramRecord,
    ConstructionProgramStep,
    ConstructionRecord,
)


@dataclass(frozen=True, slots=True)
class ProgramApplicationSpec:
    symbol_ref: str
    schema_ref: str
    schema_revision: int


@dataclass(frozen=True, slots=True)
class ProgramVariableSpec:
    symbol_ref: str
    expected_filler_classes: tuple[PortFillerClass, ...] = ()
    expected_schema_classes: tuple[SchemaClass, ...] = ()
    expected_type_refs: tuple[str, ...] = ()
    restriction_refs: tuple[str, ...] = ()
    projection_ref: str | None = None
    projection_revision: int | None = None
    open_binding_purpose: OpenBindingPurpose | None = None
    preserve_gap: bool = False


@dataclass(frozen=True, slots=True)
class ProgramBindingSpec:
    application_symbol_ref: str
    port_ref: str
    source_kind: str
    source_ref: str

    def __post_init__(self) -> None:
        if self.source_kind not in {"slot", "symbol"}:
            raise ValueError("program binding source_kind must be slot or symbol")


@dataclass(frozen=True, slots=True)
class ProgramScopeSpec:
    operator_symbol_ref: str
    target_symbol_ref: str
    scope_kind: str


@dataclass(frozen=True, slots=True)
class ConstructionSemanticPlan:
    plan_ref: str
    construction_ref: str
    construction_revision: int
    authority_ref: str
    authority_revision: int | None
    authority_path: str
    applications: tuple[ProgramApplicationSpec, ...]
    variables: tuple[ProgramVariableSpec, ...]
    bindings: tuple[ProgramBindingSpec, ...]
    unifications: tuple[tuple[str, str], ...]
    scopes: tuple[ProgramScopeSpec, ...]
    feature_values: tuple[tuple[str, str, str], ...]
    root_symbol_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    assumptions: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def schema_pins(self) -> tuple[tuple[str, int], ...]:
        return tuple(sorted({(item.schema_ref, item.schema_revision) for item in self.applications}))

    def to_metadata(self) -> Mapping[str, Any]:
        return {
            "plan_ref": self.plan_ref,
            "construction_ref": self.construction_ref,
            "construction_revision": self.construction_revision,
            "authority_ref": self.authority_ref,
            "authority_revision": self.authority_revision,
            "authority_path": self.authority_path,
            "applications": tuple(
                (item.symbol_ref, item.schema_ref, item.schema_revision)
                for item in self.applications
            ),
            "variables": tuple(
                (
                    item.symbol_ref,
                    tuple(value.value for value in item.expected_filler_classes),
                    tuple(value.value for value in item.expected_schema_classes),
                    item.expected_type_refs,
                    item.restriction_refs,
                    item.projection_ref,
                    item.projection_revision,
                    None if item.open_binding_purpose is None else item.open_binding_purpose.value,
                    item.preserve_gap,
                )
                for item in self.variables
            ),
            "bindings": tuple(
                (item.application_symbol_ref, item.port_ref, item.source_kind, item.source_ref)
                for item in self.bindings
            ),
            "unifications": self.unifications,
            "scopes": tuple(
                (item.operator_symbol_ref, item.target_symbol_ref, item.scope_kind)
                for item in self.scopes
            ),
            "feature_values": self.feature_values,
            "root_symbol_refs": self.root_symbol_refs,
            "evidence_refs": self.evidence_refs,
            "assumptions": self.assumptions,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_metadata(cls, value: Mapping[str, Any]) -> "ConstructionSemanticPlan":
        return cls(
            plan_ref=str(value["plan_ref"]),
            construction_ref=str(value["construction_ref"]),
            construction_revision=int(value["construction_revision"]),
            authority_ref=str(value["authority_ref"]),
            authority_revision=None if value.get("authority_revision") is None else int(value["authority_revision"]),
            authority_path=str(value["authority_path"]),
            applications=tuple(
                ProgramApplicationSpec(str(symbol), str(schema_ref), int(revision))
                for symbol, schema_ref, revision in value.get("applications", ())
            ),
            variables=tuple(
                ProgramVariableSpec(
                    symbol_ref=str(item[0]),
                    expected_filler_classes=tuple(PortFillerClass(v) for v in item[1]),
                    expected_schema_classes=tuple(SchemaClass(v) for v in item[2]),
                    expected_type_refs=tuple(map(str, item[3])),
                    restriction_refs=tuple(map(str, item[4])),
                    projection_ref=None if item[5] is None else str(item[5]),
                    projection_revision=None if item[6] is None else int(item[6]),
                    open_binding_purpose=None if item[7] is None else OpenBindingPurpose(str(item[7])),
                    preserve_gap=bool(item[8]),
                )
                for item in value.get("variables", ())
            ),
            bindings=tuple(
                ProgramBindingSpec(str(app), str(port), str(kind), str(source))
                for app, port, kind, source in value.get("bindings", ())
            ),
            unifications=tuple((str(left), str(right)) for left, right in value.get("unifications", ())),
            scopes=tuple(
                ProgramScopeSpec(str(operator), str(target), str(kind))
                for operator, target, kind in value.get("scopes", ())
            ),
            feature_values=tuple(
                (str(symbol), str(name), str(item))
                for symbol, name, item in value.get("feature_values", ())
            ),
            root_symbol_refs=tuple(map(str, value.get("root_symbol_refs", ()))),
            evidence_refs=tuple(map(str, value.get("evidence_refs", ()))),
            assumptions=tuple(map(str, value.get("assumptions", ()))),
            metadata=dict(value.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class ConstructionProgramResolution:
    construction_ref: str
    construction_revision: int
    decision: UseDecision
    authority_path: str
    authority_ref: str
    authority_revision: int | None
    plans: tuple[ConstructionSemanticPlan, ...]
    evidence_refs: tuple[str, ...]
    reason: str


class ConstructionProgramCompiler:
    """Compile reviewed program steps into a finite set of semantic plans."""

    def __init__(self, language_registry, schema_registry, *, maximum_plans: int = 64):
        if maximum_plans < 1:
            raise ValueError("maximum_plans must be positive")
        self.language = language_registry
        self.schemas = schema_registry
        self.maximum_plans = maximum_plans

    def resolve(
        self,
        construction: ConstructionRecord,
        *,
        closure_candidates: Iterable[SemanticClosureCandidate] = (),
    ) -> ConstructionProgramResolution:
        if construction.use_authority_explicit and UseOperation.COMPOSE not in construction.authorized_use_operations:
            return ConstructionProgramResolution(
                construction_ref=construction.construction_ref,
                construction_revision=construction.revision,
                decision=UseDecision.DENY,
                authority_path="typed_construction_use_authority",
                authority_ref=construction.construction_ref,
                authority_revision=construction.revision,
                plans=(),
                evidence_refs=construction.evidence_refs,
                reason="construction does not authorize compose use",
            )
        programs = self.language.programs_for_construction(
            construction.construction_ref, construction.revision
        )
        executable = tuple(
            item for item in programs
            if item.lifecycle_status.value == "active"
            and item.use_operation == UseOperation.COMPOSE
            and item.use_decision == UseDecision.ALLOW
        )
        if len(executable) > 1:
            raise ValueError(
                f"multiple executable construction programs for "
                f"{construction.construction_ref}@{construction.revision}"
            )
        if executable:
            program = executable[0]
            plans = self._compile_program(construction, program, tuple(closure_candidates))
            return ConstructionProgramResolution(
                construction_ref=construction.construction_ref,
                construction_revision=construction.revision,
                decision=UseDecision.ALLOW if plans else UseDecision.DENY,
                authority_path="construction_program",
                authority_ref=program.program_ref,
                authority_revision=program.revision,
                plans=plans,
                evidence_refs=program.evidence_refs,
                reason="explicit reviewed construction program",
            )

        # Migration-only compatibility. The matcher no longer reads this flag.
        # New typed program authority always outranks it.
        if construction.metadata.get("interpretation_enabled") is False:
            return ConstructionProgramResolution(
                construction_ref=construction.construction_ref,
                construction_revision=construction.revision,
                decision=UseDecision.DENY,
                authority_path="legacy_interpretation_metadata_compat",
                authority_ref=construction.construction_ref,
                authority_revision=construction.revision,
                plans=(),
                evidence_refs=construction.evidence_refs,
                reason="legacy boot construction explicitly denied interpretation",
            )

        if construction.output_schema_ref is None:
            if construction.construction_kind.value in {"coordination", "ellipsis"}:
                plan = ConstructionSemanticPlan(
                    plan_ref=_plan_ref(
                        construction.construction_ref,
                        construction.revision,
                        "legacy-structural",
                        (),
                    ),
                    construction_ref=construction.construction_ref,
                    construction_revision=construction.revision,
                    authority_ref=construction.construction_ref,
                    authority_revision=construction.revision,
                    authority_path="legacy_structural_compat",
                    applications=(),
                    variables=(),
                    bindings=(),
                    unifications=(),
                    scopes=(),
                    feature_values=(),
                    root_symbol_refs=(),
                    evidence_refs=construction.evidence_refs
                    or (f"construction:{construction.construction_ref}",),
                    metadata={"structural_kind": construction.construction_kind.value},
                )
                return ConstructionProgramResolution(
                    construction.construction_ref,
                    construction.revision,
                    UseDecision.ALLOW,
                    "legacy_structural_compat",
                    construction.construction_ref,
                    construction.revision,
                    (plan,),
                    plan.evidence_refs,
                    "legacy structural construction compatibility",
                )
            return ConstructionProgramResolution(
                construction.construction_ref,
                construction.revision,
                UseDecision.DENY,
                "no_semantic_program",
                construction.construction_ref,
                construction.revision,
                (),
                construction.evidence_refs,
                "construction has no semantic program",
            )

        steps = [
            ConstructionProgramStep(
                step_ref="legacy:instantiate",
                operation=ConstructionProgramOperation.INSTANTIATE_SCHEMA,
                result_ref="root",
                schema_ref=construction.output_schema_ref,
                schema_revision=construction.output_schema_revision,
            )
        ]
        for slot in construction.slots:
            if slot.semantic_port_ref:
                steps.append(
                    ConstructionProgramStep(
                        step_ref=f"legacy:bind:{slot.slot_ref}",
                        operation=ConstructionProgramOperation.BIND_PORT_FROM_SLOT,
                        input_refs=("root",),
                        slot_ref=slot.slot_ref,
                        port_ref=slot.semantic_port_ref,
                    )
                )
        program = ConstructionProgramRecord(
            program_ref=f"legacy-program:{construction.construction_ref}",
            pack_ref=construction.pack_ref,
            pack_revision=construction.pack_revision,
            construction_ref=construction.construction_ref,
            construction_revision=construction.revision,
            steps=tuple(steps),
            root_symbol_refs=("root",),
            lifecycle_status=construction.lifecycle_status,
            use_operation=UseOperation.COMPOSE,
            use_decision=UseDecision.ALLOW,
            source_refs=construction.source_refs,
            evidence_refs=construction.evidence_refs
            or (f"construction:{construction.construction_ref}",),
            competence_case_refs=construction.competence_case_refs,
            permission_ref=construction.permission_ref,
            metadata={"compatibility_only": True},
        )
        plans = self._compile_program(construction, program, tuple(closure_candidates))
        plans = tuple(
            replace(
                item,
                authority_path="legacy_fixed_output_compat",
                authority_ref=construction.construction_ref,
                authority_revision=construction.revision,
                assumptions=tuple(sorted(set((*item.assumptions, "legacy_fixed_output_compat")))),
            )
            for item in plans
        )
        return ConstructionProgramResolution(
            construction.construction_ref,
            construction.revision,
            UseDecision.ALLOW if plans else UseDecision.DENY,
            "legacy_fixed_output_compat",
            construction.construction_ref,
            construction.revision,
            plans,
            program.evidence_refs,
            "legacy fixed-output construction compiled into bounded program algebra",
        )

    def _compile_program(
        self,
        construction: ConstructionRecord,
        program: ConstructionProgramRecord,
        closure_candidates: tuple[SemanticClosureCandidate, ...],
    ) -> tuple[ConstructionSemanticPlan, ...]:
        branches: list[dict[str, Any]] = [{
            "applications": {},
            "variables": {},
            "bindings": [],
            "unifications": [],
            "scopes": [],
            "features": [],
            "roots": list(program.root_symbol_refs),
        }]
        slot_refs = {item.slot_ref for item in construction.slots}

        for step in program.steps:
            next_branches: list[dict[str, Any]] = []
            for branch in branches:
                if step.operation == ConstructionProgramOperation.INSTANTIATE_SCHEMA:
                    schema = self.schemas.schema(step.schema_ref, step.schema_revision)
                    if not schema.use_profile.permits(UseOperation.COMPOSE, provisional=True):
                        continue
                    updated = _clone_branch(branch)
                    updated["applications"][step.result_ref] = ProgramApplicationSpec(
                        step.result_ref, schema.schema_ref, schema.revision
                    )
                    next_branches.append(updated)

                elif step.operation == ConstructionProgramOperation.ACTIVATE_SCHEMA_CLASS_CANDIDATES:
                    for schema in self._schema_class_candidates(
                        step.schema_classes, closure_candidates
                    ):
                        updated = _clone_branch(branch)
                        updated["applications"][step.result_ref] = ProgramApplicationSpec(
                            step.result_ref, schema.schema_ref, schema.revision
                        )
                        next_branches.append(updated)

                elif step.operation == ConstructionProgramOperation.INTRODUCE_VARIABLE:
                    updated = _clone_branch(branch)
                    updated["variables"][step.result_ref] = ProgramVariableSpec(
                        symbol_ref=step.result_ref,
                        expected_filler_classes=step.expected_filler_classes,
                        expected_schema_classes=step.expected_schema_classes,
                        expected_type_refs=step.expected_type_refs,
                        open_binding_purpose=step.open_binding_purpose,
                    )
                    next_branches.append(updated)

                elif step.operation == ConstructionProgramOperation.BIND_PORT_FROM_SLOT:
                    if step.slot_ref not in slot_refs:
                        raise ValueError(
                            f"construction program references unknown slot:{step.slot_ref}"
                        )
                    if not step.input_refs or step.input_refs[0] not in branch["applications"]:
                        raise ValueError("BIND_PORT_FROM_SLOT requires an application symbol")
                    application_spec = branch["applications"][step.input_refs[0]]
                    application_schema = self.schemas.schema(
                        application_spec.schema_ref,
                        application_spec.schema_revision,
                    )
                    application_schema.port(step.port_ref)
                    updated = _clone_branch(branch)
                    updated["bindings"].append(
                        ProgramBindingSpec(
                            step.input_refs[0], step.port_ref, "slot", step.slot_ref
                        )
                    )
                    next_branches.append(updated)

                elif step.operation == ConstructionProgramOperation.BIND_PORT_FROM_SYMBOL:
                    if len(step.input_refs) != 2:
                        raise ValueError("BIND_PORT_FROM_SYMBOL requires application and source symbols")
                    if step.input_refs[0] not in branch["applications"]:
                        raise ValueError("BIND_PORT_FROM_SYMBOL requires an application symbol")
                    if (
                        step.input_refs[1] not in branch["applications"]
                        and step.input_refs[1] not in branch["variables"]
                    ):
                        raise ValueError("BIND_PORT_FROM_SYMBOL requires a declared source symbol")
                    application_spec = branch["applications"][step.input_refs[0]]
                    application_schema = self.schemas.schema(
                        application_spec.schema_ref,
                        application_spec.schema_revision,
                    )
                    application_schema.port(step.port_ref)
                    updated = _clone_branch(branch)
                    updated["bindings"].append(
                        ProgramBindingSpec(
                            step.input_refs[0],
                            step.port_ref,
                            "symbol",
                            step.input_refs[1],
                        )
                    )
                    next_branches.append(updated)

                elif step.operation == ConstructionProgramOperation.UNIFY:
                    if len(step.input_refs) < 2:
                        raise ValueError("UNIFY requires at least two symbols")
                    updated = _clone_branch(branch)
                    for other in step.input_refs[1:]:
                        updated["unifications"].append((step.input_refs[0], other))
                    next_branches.append(updated)

                elif step.operation == ConstructionProgramOperation.ADD_RESTRICTION:
                    updated = _clone_branch(branch)
                    symbol = _one_input(step)
                    variable = updated["variables"].get(symbol)
                    if variable is None:
                        raise ValueError("ADD_RESTRICTION requires a variable symbol")
                    updated["variables"][symbol] = replace(
                        variable,
                        restriction_refs=tuple(
                            sorted(set((*variable.restriction_refs, step.value_ref)))
                        ),
                    )
                    next_branches.append(updated)

                elif step.operation == ConstructionProgramOperation.SET_PROJECTION:
                    updated = _clone_branch(branch)
                    symbol = _one_input(step)
                    variable = updated["variables"].get(symbol)
                    if variable is None:
                        raise ValueError("SET_PROJECTION requires a variable symbol")
                    updated["variables"][symbol] = replace(
                        variable,
                        projection_ref=step.value_ref,
                        projection_revision=step.value_revision,
                    )
                    next_branches.append(updated)

                elif step.operation == ConstructionProgramOperation.ADD_SCOPE:
                    if len(step.input_refs) != 2:
                        raise ValueError("ADD_SCOPE requires operator and target symbols")
                    updated = _clone_branch(branch)
                    updated["scopes"].append(
                        ProgramScopeSpec(
                            step.input_refs[0],
                            step.input_refs[1],
                            str(step.metadata.get("scope_kind") or "logical"),
                        )
                    )
                    next_branches.append(updated)

                elif step.operation in {
                    ConstructionProgramOperation.ADD_TIME_FEATURE,
                    ConstructionProgramOperation.ADD_ASPECT_FEATURE,
                    ConstructionProgramOperation.ADD_MODALITY,
                }:
                    updated = _clone_branch(branch)
                    symbol = _one_input(step)
                    feature_name = {
                        ConstructionProgramOperation.ADD_TIME_FEATURE: "time",
                        ConstructionProgramOperation.ADD_ASPECT_FEATURE: "aspect",
                        ConstructionProgramOperation.ADD_MODALITY: "modality",
                    }[step.operation]
                    updated["features"].append((symbol, feature_name, step.value_ref))
                    next_branches.append(updated)

                elif step.operation == ConstructionProgramOperation.WRAP_DISCOURSE_ACT:
                    if len(step.input_refs) != 1:
                        raise ValueError("WRAP_DISCOURSE_ACT requires one content symbol")
                    schema = self.schemas.schema(step.schema_ref, step.schema_revision)
                    if schema.schema_class != SchemaClass.DISCOURSE_ACT:
                        raise ValueError("WRAP_DISCOURSE_ACT requires discourse-act schema")
                    schema.port(step.port_ref)
                    updated = _clone_branch(branch)
                    updated["applications"][step.result_ref] = ProgramApplicationSpec(
                        step.result_ref, schema.schema_ref, schema.revision
                    )
                    updated["bindings"].append(
                        ProgramBindingSpec(
                            step.result_ref, step.port_ref, "symbol", step.input_refs[0]
                        )
                    )
                    updated["roots"] = [step.result_ref]
                    next_branches.append(updated)

                elif step.operation == ConstructionProgramOperation.PRESERVE_GAP:
                    updated = _clone_branch(branch)
                    symbol = _one_input(step)
                    variable = updated["variables"].get(symbol)
                    if variable is None:
                        raise ValueError("PRESERVE_GAP requires a variable symbol")
                    updated["variables"][symbol] = replace(
                        variable,
                        preserve_gap=True,
                        open_binding_purpose=(
                            variable.open_binding_purpose
                            or OpenBindingPurpose.PARTIAL_COMPOSITION
                        ),
                    )
                    next_branches.append(updated)
                else:
                    raise ValueError(
                        f"unsupported construction program operation:{step.operation}"
                    )
            branches = next_branches[: self.maximum_plans]
            if not branches:
                break

        plans = []
        for branch in branches[: self.maximum_plans]:
            schema_pins = tuple(
                sorted(
                    (item.schema_ref, item.schema_revision)
                    for item in branch["applications"].values()
                )
            )
            semantic_signature = (
                schema_pins,
                tuple(sorted((item.application_symbol_ref, item.port_ref, item.source_kind, item.source_ref) for item in branch["bindings"])),
                tuple(sorted(set(branch["unifications"]))),
                tuple(sorted((item.operator_symbol_ref, item.target_symbol_ref, item.scope_kind) for item in branch["scopes"])),
                tuple(sorted(branch["features"])),
                tuple(sorted(branch["roots"])),
                tuple(sorted((key, value.symbol_ref, tuple(x.value for x in value.expected_filler_classes), tuple(x.value for x in value.expected_schema_classes), value.expected_type_refs, value.restriction_refs, value.projection_ref, value.projection_revision, None if value.open_binding_purpose is None else value.open_binding_purpose.value, value.preserve_gap) for key, value in branch["variables"].items())),
            )
            plans.append(
                ConstructionSemanticPlan(
                    plan_ref=_plan_ref(
                        construction.construction_ref,
                        construction.revision,
                        program.program_ref,
                        semantic_signature,
                    ),
                    construction_ref=construction.construction_ref,
                    construction_revision=construction.revision,
                    authority_ref=program.program_ref,
                    authority_revision=program.revision,
                    authority_path="construction_program",
                    applications=tuple(
                        branch["applications"][key]
                        for key in sorted(branch["applications"])
                    ),
                    variables=tuple(
                        branch["variables"][key] for key in sorted(branch["variables"])
                    ),
                    bindings=tuple(branch["bindings"]),
                    unifications=tuple(sorted(set(branch["unifications"]))),
                    scopes=tuple(branch["scopes"]),
                    feature_values=tuple(branch["features"]),
                    root_symbol_refs=tuple(branch["roots"]),
                    evidence_refs=program.evidence_refs,
                    metadata={
                        "construction_program_ref": program.program_ref,
                        "closure_constrained": bool(closure_candidates),
                    },
                )
            )
        return tuple(sorted(plans, key=lambda item: item.plan_ref))

    def _schema_class_candidates(
        self,
        classes: tuple[SchemaClass, ...],
        closure_candidates: tuple[SemanticClosureCandidate, ...],
    ):
        closure_constrained = bool(closure_candidates)
        allowed_pins = {
            (item.schema_ref, item.schema_revision)
            for item in closure_candidates
            if item.schema_class in classes and item.usable_for_composition
        }
        # Broad schema-class activation is referent-knowledge closure, never a
        # global ontology scan. An empty closure remains an explicit frontier.
        if not allowed_pins:
            return ()
        result = []
        for schema in self.schemas.iter_schemas():
            if schema.schema_class not in classes:
                continue
            if not schema.use_profile.permits(UseOperation.COMPOSE, provisional=True):
                continue
            if closure_constrained and (schema.schema_ref, schema.revision) not in allowed_pins:
                continue
            result.append(schema)
        return tuple(
            sorted(
                result,
                key=lambda item: (
                    item.schema_class.value, item.schema_ref, item.revision
                ),
            )[: self.maximum_plans]
        )


def _one_input(step: ConstructionProgramStep) -> str:
    if len(step.input_refs) != 1:
        raise ValueError(f"{step.operation.value} requires exactly one input symbol")
    return step.input_refs[0]


def _clone_branch(branch: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "applications": dict(branch["applications"]),
        "variables": dict(branch["variables"]),
        "bindings": list(branch["bindings"]),
        "unifications": list(branch["unifications"]),
        "scopes": list(branch["scopes"]),
        "features": list(branch["features"]),
        "roots": list(branch["roots"]),
    }


def _plan_ref(
    construction_ref: str,
    construction_revision: int,
    authority_ref: str,
    semantic_signature,
) -> str:
    return "construction-semantic-plan:" + semantic_fingerprint(
        "construction-semantic-plan",
        (construction_ref, construction_revision, authority_ref, semantic_signature),
        24,
    )
