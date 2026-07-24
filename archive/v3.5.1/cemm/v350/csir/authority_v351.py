"""Exact v3.5.1 semantic-definition authority and closure compilation.

This module implements the Phase-7 authority split required by ARCHITECTURE.md and
CEMM_CORE_MATHS.md.  Semantic definitions are immutable meaning authority.  Lifecycle,
use, privacy, competence, recurrent parameters, observation models and causal mechanisms
are separate exact artifacts and cannot silently redefine semantic identity.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
import hashlib
import json
import math
from typing import Any, Iterable, Mapping

from .authority import CURRENT_KERNEL_ABI
from .canonical_v351 import exact_fingerprint, normalize, semantic_fingerprint
from .model import (
    CSIRGraph,
    CSIRNodeKind,
    CSIRRef,
    Coordination,
    ExactAuthorityPin,
    PortBinding,
    ProofLink,
    Qualifier,
    ScopeEmbedding,
    SemanticApplication,
    SemanticTerm,
    SemanticVariable,
)
from .operations import bind


SEMANTIC_DEFINITION_COMPILER_ABI = "cemm-semantic-definition-compiler-v1"
DEFINITION_CLOSURE_ABI = "cemm-definition-closure-v1"


class SemanticAuthorityError(ValueError):
    pass


class MissingExactDependency(SemanticAuthorityError):
    pass


class CyclicDefinitionClosure(SemanticAuthorityError):
    pass


class NonConservativeDefinition(SemanticAuthorityError):
    pass


class ClosureProofError(SemanticAuthorityError):
    pass


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha(value: Any) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _pin_key(pin: ExactAuthorityPin) -> tuple[str, str, str, int, str, str]:
    return pin.key


def _require_unique(values: Iterable[Any], label: str) -> None:
    values = tuple(values)
    if len(values) != len(set(values)):
        raise SemanticAuthorityError(f"duplicate {label}")


def semantic_structural_exact_fingerprint(graph: CSIRGraph) -> str:
    """Exact occurrence structure excluding proofs and non-semantic operational profiles."""
    normalized = normalize(graph)
    semantic_structure = replace(
        normalized,
        applications=tuple(
            replace(application, operational_profile_pins=())
            for application in normalized.applications
        ),
        proof_links=(),
    )
    return exact_fingerprint(semantic_structure)


def _graph_authority_pins(graph: CSIRGraph) -> tuple[ExactAuthorityPin, ...]:
    pins: dict[tuple[str, str, str, int, str, str], ExactAuthorityPin] = {}

    def add(pin: ExactAuthorityPin | None) -> None:
        if pin is not None:
            pins[pin.key] = pin

    for term in graph.terms:
        for pin in (*term.type_pins, *term.authority_pins):
            add(pin)
    for variable in graph.variables:
        for pin in variable.required_type_pins:
            add(pin)
    for application in graph.applications:
        add(application.predicate_pin)
        for pin in application.operational_profile_pins:
            add(pin)
    for binding in graph.bindings:
        add(binding.port_pin)
    for qualifier in graph.qualifiers:
        add(qualifier.value_pin)
    for embedding in graph.scope_embeddings:
        add(embedding.scope_kind_pin)
    for coordination in graph.coordinations:
        add(coordination.coordination_kind_pin)
    for proof in graph.proof_links:
        for pin in proof.authority_pins:
            add(pin)
    return tuple(pins[key] for key in sorted(pins))


@dataclass(frozen=True, slots=True)
class FormalPort:
    """A definition-local formal port backed by a CSIR variable.

    Port identity is itself exact authority.  The variable name is local occurrence
    mechanics and is alpha-renamed during compilation.
    """

    port_pin: ExactAuthorityPin
    variable_ref: str
    minimum: int = 1
    maximum: int | None = 1

    def __post_init__(self) -> None:
        if not self.variable_ref.strip():
            raise SemanticAuthorityError("formal port variable_ref must be non-empty")
        if self.minimum < 0:
            raise SemanticAuthorityError("formal port minimum cannot be negative")
        if self.maximum is not None and self.maximum < self.minimum:
            raise SemanticAuthorityError("formal port maximum cannot be below minimum")


@dataclass(frozen=True, slots=True)
class DefinitionInvocation:
    """One exact higher-order definition invocation inside a definition body.

    ``argument_bindings`` maps child formal port refs to node refs in the parent body.
    No string lookup such as "latest schema" is permitted.
    """

    invocation_ref: str
    definition_pin: ExactAuthorityPin
    argument_bindings: tuple[tuple[ExactAuthorityPin, CSIRRef], ...] = ()

    def __post_init__(self) -> None:
        if not self.invocation_ref.strip():
            raise SemanticAuthorityError("definition invocation requires identity")
        _require_unique(
            (_pin_key(port_pin) for port_pin, _ in self.argument_bindings),
            "invocation exact port bindings",
        )


@dataclass(frozen=True, slots=True)
class SemanticDefinition:
    definition_pin: ExactAuthorityPin
    body: CSIRGraph
    formal_ports: tuple[FormalPort, ...] = ()
    semantic_dependency_pins: tuple[ExactAuthorityPin, ...] = ()
    invocations: tuple[DefinitionInvocation, ...] = ()
    constraint_pins: tuple[ExactAuthorityPin, ...] = ()
    expected_semantic_fingerprint: str | None = None
    executable: bool = True
    provenance_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_unique((item.port_pin.key for item in self.formal_ports), "formal port pins")
        _require_unique((item.variable_ref for item in self.formal_ports), "formal port variables")
        _require_unique((item.key for item in self.semantic_dependency_pins), "semantic dependencies")
        _require_unique((item.invocation_ref for item in self.invocations), "definition invocations")
        _require_unique((item.key for item in self.constraint_pins), "constraint pins")
        variables = {item.variable_ref for item in self.body.variables}
        missing = {item.variable_ref for item in self.formal_ports}.difference(variables)
        if missing:
            raise SemanticAuthorityError(f"formal ports reference missing CSIR variables:{sorted(missing)}")
        if self.body.proof_links:
            raise SemanticAuthorityError(
                "semantic definition body cannot bundle occurrence proof lineage"
            )
        if self.executable and self.body.unresolved_refs:
            raise SemanticAuthorityError(
                "executable semantic definition body cannot contain unresolved refs"
            )
        if any(app.operational_profile_pins for app in self.body.applications):
            raise SemanticAuthorityError(
                "semantic definition body cannot bundle operational profile pins"
            )
        dependency_keys = {_pin_key(pin) for pin in self.semantic_dependency_pins}
        invoked_keys = {_pin_key(item.definition_pin) for item in self.invocations}
        if not invoked_keys.issubset(dependency_keys):
            raise SemanticAuthorityError("definition invocation must pin a declared exact semantic dependency")
        # Semantic dependencies include exact type/operator/value authority referenced
        # by the body as well as higher-order definitions. Only the latter require an
        # explicit invocation. Treating every dependency as an invocation would make
        # typed definitions impossible and would conflate reference with expansion.
        declared_authority = {self.definition_pin.key}
        declared_authority.update(dependency_keys)
        declared_authority.update(port.port_pin.key for port in self.formal_ports)
        declared_authority.update(pin.key for pin in self.constraint_pins)
        hidden_authority = {pin.key for pin in _graph_authority_pins(self.body)}.difference(
            declared_authority
        )
        if hidden_authority:
            raise SemanticAuthorityError(
                f"semantic definition body contains undeclared exact authority pins:{sorted(hidden_authority)}"
            )
        if self.executable and self.invocations and not self.expected_semantic_fingerprint:
            raise SemanticAuthorityError(
                "executable higher-order definition requires expected semantic fingerprint for conservativity"
            )


@dataclass(frozen=True, slots=True)
class OperationalProfile:
    """Non-semantic operational authority for one exact semantic definition."""

    profile_pin: ExactAuthorityPin
    definition_pin: ExactAuthorityPin
    lifecycle_status: str
    allowed_operations: tuple[str, ...] = ()
    permission_scopes: tuple[str, ...] = ()
    competence_case_pins: tuple[ExactAuthorityPin, ...] = ()
    policy_pins: tuple[ExactAuthorityPin, ...] = ()

    def __post_init__(self) -> None:
        if not self.lifecycle_status.strip():
            raise SemanticAuthorityError("operational profile requires lifecycle status")
        _require_unique(self.allowed_operations, "allowed operations")
        _require_unique(self.permission_scopes, "permission scopes")
        _require_unique((x.key for x in self.competence_case_pins), "competence pins")
        _require_unique((x.key for x in self.policy_pins), "policy pins")


@dataclass(frozen=True, slots=True)
class DynamicsParameterArtifact:
    parameter_pin: ExactAuthorityPin
    parameter_family: str
    values: tuple[tuple[str, float], ...]
    calibration_evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.parameter_family.strip():
            raise SemanticAuthorityError("dynamics parameter family is required")
        if not self.values:
            raise SemanticAuthorityError("dynamics parameter artifact requires explicit immutable values")
        _require_unique((name for name, _ in self.values), "dynamics parameter names")
        for name, value in self.values:
            if not name.strip() or not math.isfinite(value):
                raise SemanticAuthorityError("dynamics parameters require named finite values")


@dataclass(frozen=True, slots=True)
class ObservationModel:
    model_pin: ExactAuthorityPin
    modality_ref: str
    output_definition_pins: tuple[ExactAuthorityPin, ...]
    calibration_pin: ExactAuthorityPin | None = None

    def __post_init__(self) -> None:
        if not self.modality_ref.strip():
            raise SemanticAuthorityError("observation model modality_ref is required")
        if not self.output_definition_pins:
            raise SemanticAuthorityError("observation model requires exact semantic outputs")
        _require_unique((x.key for x in self.output_definition_pins), "observation outputs")


@dataclass(frozen=True, slots=True)
class CausalMechanism:
    mechanism_pin: ExactAuthorityPin
    trigger_definition_pin: ExactAuthorityPin
    participant_port_pins: tuple[ExactAuthorityPin, ...] = ()
    precondition_definition_pins: tuple[ExactAuthorityPin, ...] = ()
    transition_template_pins: tuple[ExactAuthorityPin, ...] = ()

    def __post_init__(self) -> None:
        _require_unique((x.key for x in self.participant_port_pins), "causal participant ports")
        _require_unique((x.key for x in self.precondition_definition_pins), "causal preconditions")
        _require_unique((x.key for x in self.transition_template_pins), "causal transition templates")


@dataclass(frozen=True, slots=True)
class UseAuthorization:
    authorization_pin: ExactAuthorityPin
    target_pin: ExactAuthorityPin
    operation: str
    decision: str
    context_scopes: tuple[str, ...] = ()
    permission_scopes: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.operation.strip() or not self.decision.strip():
            raise SemanticAuthorityError("use authorization requires operation and decision")
        if self.decision.casefold() not in {"allow", "deny", "preserve_only", "provisional"}:
            raise SemanticAuthorityError("use authorization decision is not a recognized structural decision")
        _require_unique(self.context_scopes, "authorization context scopes")
        _require_unique(self.permission_scopes, "authorization permission scopes")


@dataclass(frozen=True, slots=True)
class AuthoritySnapshotV351:
    generation: int
    authority_fingerprint: str
    semantic_definitions: tuple[SemanticDefinition, ...] = ()
    operational_profiles: tuple[OperationalProfile, ...] = ()
    dynamics_parameters: tuple[DynamicsParameterArtifact, ...] = ()
    observation_models: tuple[ObservationModel, ...] = ()
    causal_mechanisms: tuple[CausalMechanism, ...] = ()
    use_authorizations: tuple[UseAuthorization, ...] = ()
    # Exact inventory for separately governed constraint/policy/adapter/language/etc.
    # artifacts that are part of this immutable AuthorityGeneration but are not semantic
    # definitions. Presence here is authority inventory, never semantic bundling.
    auxiliary_exact_pins: tuple[ExactAuthorityPin, ...] = ()
    kernel_abi_fingerprint: str = CURRENT_KERNEL_ABI.fingerprint

    def __post_init__(self) -> None:
        if self.generation < 1 or not self.authority_fingerprint.strip():
            raise SemanticAuthorityError("authority snapshot requires exact generation/fingerprint")
        if self.kernel_abi_fingerprint != CURRENT_KERNEL_ABI.fingerprint:
            raise SemanticAuthorityError("authority snapshot kernel ABI mismatch")
        families = (
            ("semantic definition", (x.definition_pin.key for x in self.semantic_definitions)),
            ("operational profile", (x.profile_pin.key for x in self.operational_profiles)),
            ("dynamics parameter", (x.parameter_pin.key for x in self.dynamics_parameters)),
            ("observation model", (x.model_pin.key for x in self.observation_models)),
            ("causal mechanism", (x.mechanism_pin.key for x in self.causal_mechanisms)),
            ("use authorization", (x.authorization_pin.key for x in self.use_authorizations)),
            ("auxiliary exact pin", (x.key for x in self.auxiliary_exact_pins)),
        )
        for label, keys in families:
            _require_unique(tuple(keys), label)
        _require_unique(
            (item.parameter_family for item in self.dynamics_parameters),
            "dynamics parameter families",
        )

        definition_keys = {item.definition_pin.key for item in self.semantic_definitions}
        for profile in self.operational_profiles:
            if profile.definition_pin.key not in definition_keys:
                raise MissingExactDependency(
                    f"operational profile targets missing semantic definition:{profile.definition_pin.key}"
                )
        for model in self.observation_models:
            missing = [pin.key for pin in model.output_definition_pins if pin.key not in definition_keys]
            if missing:
                raise MissingExactDependency(f"observation model outputs missing definitions:{missing}")
        for mechanism in self.causal_mechanisms:
            required_definitions = (mechanism.trigger_definition_pin, *mechanism.precondition_definition_pins)
            missing = [pin.key for pin in required_definitions if pin.key not in definition_keys]
            if missing:
                raise MissingExactDependency(f"causal mechanism references missing definitions:{missing}")

        # Now that top-level families are known, every separately governed exact reference
        # used operationally must resolve inside this generation's inventory.
        for profile in self.operational_profiles:
            for pin in (*profile.competence_case_pins, *profile.policy_pins):
                self.require_known_pin(pin)
        for model in self.observation_models:
            if model.calibration_pin is not None:
                self.require_known_pin(model.calibration_pin)
        for mechanism in self.causal_mechanisms:
            for pin in (*mechanism.participant_port_pins, *mechanism.transition_template_pins):
                self.require_known_pin(pin)
        for authorization in self.use_authorizations:
            self.require_known_pin(authorization.target_pin)

    @property
    def snapshot_fingerprint(self) -> str:
        """Content-address the split authority snapshot independently of mutable world state."""
        payload = {
            "generation": self.generation,
            "authority_fingerprint": self.authority_fingerprint,
            "kernel_abi": self.kernel_abi_fingerprint,
            "semantic_definitions": tuple(
                (
                    item.definition_pin.key,
                    exact_fingerprint(item.body),
                    tuple(sorted(port.port_pin.key for port in item.formal_ports)),
                    tuple(sorted(pin.key for pin in item.semantic_dependency_pins)),
                    tuple(
                        (
                            inv.invocation_ref,
                            inv.definition_pin.key,
                            tuple(sorted((pin.key, (ref.kind.value, ref.ref)) for pin, ref in inv.argument_bindings)),
                        )
                        for inv in sorted(item.invocations, key=lambda x: x.invocation_ref)
                    ),
                    tuple(sorted(pin.key for pin in item.constraint_pins)),
                    item.expected_semantic_fingerprint,
                    item.executable,
                )
                for item in sorted(self.semantic_definitions, key=lambda x: x.definition_pin.key)
            ),
            "operational_profiles": tuple(
                (
                    item.profile_pin.key, item.definition_pin.key, item.lifecycle_status,
                    tuple(sorted(item.allowed_operations)), tuple(sorted(item.permission_scopes)),
                    tuple(sorted(pin.key for pin in item.competence_case_pins)),
                    tuple(sorted(pin.key for pin in item.policy_pins)),
                )
                for item in sorted(self.operational_profiles, key=lambda x: x.profile_pin.key)
            ),
            "dynamics_parameters": tuple(
                (item.parameter_pin.key, item.parameter_family, tuple(sorted(item.values)), tuple(sorted(item.calibration_evidence_refs)))
                for item in sorted(self.dynamics_parameters, key=lambda x: x.parameter_pin.key)
            ),
            "observation_models": tuple(
                (
                    item.model_pin.key, item.modality_ref,
                    tuple(sorted(pin.key for pin in item.output_definition_pins)),
                    None if item.calibration_pin is None else item.calibration_pin.key,
                )
                for item in sorted(self.observation_models, key=lambda x: x.model_pin.key)
            ),
            "causal_mechanisms": tuple(
                (
                    item.mechanism_pin.key, item.trigger_definition_pin.key,
                    tuple(sorted(pin.key for pin in item.participant_port_pins)),
                    tuple(sorted(pin.key for pin in item.precondition_definition_pins)),
                    tuple(sorted(pin.key for pin in item.transition_template_pins)),
                )
                for item in sorted(self.causal_mechanisms, key=lambda x: x.mechanism_pin.key)
            ),
            "use_authorizations": tuple(
                (
                    item.authorization_pin.key, item.target_pin.key, item.operation, item.decision,
                    tuple(sorted(item.context_scopes)), tuple(sorted(item.permission_scopes)), tuple(sorted(item.evidence_refs)),
                )
                for item in sorted(self.use_authorizations, key=lambda x: x.authorization_pin.key)
            ),
            "auxiliary_exact_pins": tuple(sorted(pin.key for pin in self.auxiliary_exact_pins)),
        }
        return _sha(payload)

    @property
    def definition_index(self) -> Mapping[tuple[str, str, str, int, str, str], SemanticDefinition]:
        return {item.definition_pin.key: item for item in self.semantic_definitions}

    def require_definition(self, pin: ExactAuthorityPin) -> SemanticDefinition:
        try:
            return self.definition_index[pin.key]
        except KeyError as exc:
            raise MissingExactDependency(f"missing exact semantic definition:{pin.key}") from exc

    @property
    def operational_profile_index(self) -> Mapping[tuple[str, str, str, int, str, str], OperationalProfile]:
        return {item.profile_pin.key: item for item in self.operational_profiles}

    def require_operational_profile(self, pin: ExactAuthorityPin) -> OperationalProfile:
        try:
            return self.operational_profile_index[pin.key]
        except KeyError as exc:
            raise MissingExactDependency(f"missing exact operational profile:{pin.key}") from exc

    def validate_executable_graph(self, graph: CSIRGraph) -> None:
        """Validate concrete application ports/profiles against exact split authority.

        This is deliberately generic structural validation. It never branches on named
        concepts or language forms. It makes a closure proof reusable across composed
        candidates while still preventing arbitrary graphs from borrowing that proof.
        """
        for application in graph.applications:
            definition = self.require_definition(application.predicate_pin)
            formal = {item.port_pin.key: item for item in definition.formal_ports}
            observed = {item.port_pin.key: item for item in graph.bindings_for(application.application_ref)}
            unknown = sorted(set(observed).difference(formal))
            if unknown:
                raise SemanticAuthorityError(
                    f"application binds ports outside exact semantic definition:{unknown}"
                )
            for key, port in formal.items():
                count = len(observed[key].fillers) if key in observed else 0
                if count < port.minimum or (port.maximum is not None and count > port.maximum):
                    raise SemanticAuthorityError(
                        f"application port cardinality violates exact definition:{port.port_pin.key}:{count}"
                    )
            for profile_pin in application.operational_profile_pins:
                profile = self.require_operational_profile(profile_pin)
                if profile.definition_pin.key != application.predicate_pin.key:
                    raise SemanticAuthorityError(
                        "application operational profile targets another semantic definition"
                    )

    @staticmethod
    def _context_scope_matches(scopes: tuple[str, ...], value: str) -> bool:
        return not scopes or value in scopes or "global" in scopes

    @staticmethod
    def _permission_scope_matches(scopes: tuple[str, ...], value: str) -> bool:
        # Public permission is universally usable; it is not a semantic context wildcard.
        return not scopes or value in scopes or "public" in scopes

    @staticmethod
    def _scope_matches(scopes: tuple[str, ...], value: str) -> bool:
        """Backward-compatible context matcher retained for migration tooling."""
        return AuthoritySnapshotV351._context_scope_matches(scopes, value)

    def select_operational_profile(
        self,
        definition_pin: ExactAuthorityPin,
        *,
        operation: str,
        permission_ref: str,
    ) -> OperationalProfile:
        candidates = [
            item for item in self.operational_profiles
            if item.definition_pin.key == definition_pin.key
            and item.lifecycle_status.casefold() == "active"
            and operation in item.allowed_operations
            and self._permission_scope_matches(item.permission_scopes, permission_ref)
        ]
        if len(candidates) != 1:
            raise SemanticAuthorityError(
                f"exact operational profile selection requires one active profile:{definition_pin.key}:{operation}:{len(candidates)}"
            )
        return candidates[0]

    def select_use_authorizations(
        self,
        *,
        definition_pin: ExactAuthorityPin,
        profile_pin: ExactAuthorityPin,
        operation: str,
        context_ref: str,
        permission_ref: str,
    ) -> tuple[UseAuthorization, ...]:
        target_keys = {definition_pin.key, profile_pin.key}
        matching = [
            item for item in self.use_authorizations
            if item.target_pin.key in target_keys
            and item.operation == operation
            and self._context_scope_matches(item.context_scopes, context_ref)
            and self._permission_scope_matches(item.permission_scopes, permission_ref)
        ]
        if any(item.decision.casefold() == "deny" for item in matching):
            raise SemanticAuthorityError(
                f"exact use authorization denies {operation}:{definition_pin.key}"
            )
        allowed = tuple(
            sorted(
                (item for item in matching if item.decision.casefold() == "allow"),
                key=lambda item: item.authorization_pin.key,
            )
        )
        if not allowed:
            raise SemanticAuthorityError(
                f"missing exact ALLOW use authorization:{operation}:{definition_pin.key}"
            )
        return allowed

    def bind_execution_authority(
        self,
        graph: CSIRGraph,
        *,
        operation: str,
        context_ref: str,
        permission_ref: str,
        projection_authority_pins: Iterable[ExactAuthorityPin] = (),
        causal_mechanism_pins: Iterable[ExactAuthorityPin] = (),
        policy_adapter_pins: Iterable[ExactAuthorityPin] = (),
        require_projection_authority: bool = False,
    ) -> tuple[CSIRGraph, "ExecutableAuthorityEnvelope"]:
        applications: list[SemanticApplication] = []
        profile_pins: dict[tuple[str, str, str, int, str, str], ExactAuthorityPin] = {}
        authorization_pins: dict[tuple[str, str, str, int, str, str], ExactAuthorityPin] = {}
        required_policy_pins: dict[tuple[str, str, str, int, str, str], ExactAuthorityPin] = {}
        for application in graph.applications:
            selected_profile = self.select_operational_profile(
                application.predicate_pin, operation=operation, permission_ref=permission_ref
            )
            if application.operational_profile_pins:
                if len(application.operational_profile_pins) != 1:
                    raise SemanticAuthorityError("application requires exactly one operational profile pin")
                profile = self.require_operational_profile(application.operational_profile_pins[0])
                if profile.profile_pin.key != selected_profile.profile_pin.key:
                    raise SemanticAuthorityError(
                        "pre-pinned operational profile does not equal the unique exact profile selection"
                    )
            else:
                profile = selected_profile
                application = replace(application, operational_profile_pins=(profile.profile_pin,))
            authorizations = self.select_use_authorizations(
                definition_pin=application.predicate_pin,
                profile_pin=profile.profile_pin,
                operation=operation,
                context_ref=context_ref,
                permission_ref=permission_ref,
            )
            applications.append(application)
            profile_pins[profile.profile_pin.key] = profile.profile_pin
            for policy_pin in profile.policy_pins:
                required_policy_pins[policy_pin.key] = policy_pin
            for authorization in authorizations:
                authorization_pins[authorization.authorization_pin.key] = authorization.authorization_pin

        projection = tuple(sorted(projection_authority_pins, key=lambda pin: pin.key))
        explicit_causal = {pin.key: pin for pin in causal_mechanism_pins}
        graph_predicates = {application.predicate_pin.key for application in graph.applications}
        for mechanism in self.causal_mechanisms:
            if mechanism.trigger_definition_pin.key in graph_predicates:
                explicit_causal[mechanism.mechanism_pin.key] = mechanism.mechanism_pin
        causal = tuple(explicit_causal[key] for key in sorted(explicit_causal))
        explicit_policies = {pin.key: pin for pin in policy_adapter_pins}
        explicit_policies.update(required_policy_pins)
        policies = tuple(explicit_policies[key] for key in sorted(explicit_policies))
        for pin in (*projection, *causal, *policies):
            self.require_known_pin(pin)
        mechanism_index = {item.mechanism_pin.key: item for item in self.causal_mechanisms}
        for pin in causal:
            mechanism = mechanism_index.get(pin.key)
            if mechanism is None or mechanism.trigger_definition_pin.key not in graph_predicates:
                raise SemanticAuthorityError(
                    "causal mechanism pin is not structurally applicable to a selected predicate"
                )
        if require_projection_authority and graph.applications and not projection:
            raise SemanticAuthorityError("executable language/multimodal candidate lacks exact projection authority")
        dynamics = tuple(
            item.parameter_pin
            for item in sorted(self.dynamics_parameters, key=lambda item: item.parameter_family)
        )
        if graph.applications and not dynamics:
            raise SemanticAuthorityError("executable semantic candidate lacks exact dynamics parameter artifact")
        bound_graph = replace(graph, applications=tuple(applications))
        envelope = ExecutableAuthorityEnvelope(
            semantic_authority_snapshot_fingerprint=self.snapshot_fingerprint,
            operational_profile_pins=tuple(profile_pins[key] for key in sorted(profile_pins)),
            dynamics_parameter_pins=dynamics,
            causal_mechanism_pins=causal,
            use_authorization_pins=tuple(authorization_pins[key] for key in sorted(authorization_pins)),
            projection_authority_pins=projection,
            policy_adapter_pins=policies,
            projection_authority_required=require_projection_authority,
        )
        return bound_graph, envelope

    @property
    def known_exact_pin_keys(self) -> frozenset[tuple[str, str, str, int, str, str]]:
        pins = {item.definition_pin.key for item in self.semantic_definitions}
        pins.update(
            port.port_pin.key
            for definition in self.semantic_definitions
            for port in definition.formal_ports
        )
        pins.update(item.profile_pin.key for item in self.operational_profiles)
        pins.update(item.parameter_pin.key for item in self.dynamics_parameters)
        pins.update(item.model_pin.key for item in self.observation_models)
        pins.update(item.mechanism_pin.key for item in self.causal_mechanisms)
        pins.update(item.authorization_pin.key for item in self.use_authorizations)
        pins.update(item.key for item in self.auxiliary_exact_pins)
        return frozenset(pins)

    def require_known_pin(self, pin: ExactAuthorityPin) -> None:
        if pin.key not in self.known_exact_pin_keys:
            raise MissingExactDependency(f"missing exact auxiliary authority pin:{pin.key}")


@dataclass(frozen=True, slots=True)
class ExecutableAuthorityEnvelope:
    """Exact non-semantic authority selections attached to one executable CSIR candidate."""

    semantic_authority_snapshot_fingerprint: str
    operational_profile_pins: tuple[ExactAuthorityPin, ...]
    dynamics_parameter_pins: tuple[ExactAuthorityPin, ...]
    causal_mechanism_pins: tuple[ExactAuthorityPin, ...] = ()
    use_authorization_pins: tuple[ExactAuthorityPin, ...] = ()
    projection_authority_pins: tuple[ExactAuthorityPin, ...] = ()
    policy_adapter_pins: tuple[ExactAuthorityPin, ...] = ()
    projection_authority_required: bool = False
    envelope_ref: str = field(init=False)

    def __post_init__(self) -> None:
        if not self.semantic_authority_snapshot_fingerprint.strip():
            raise SemanticAuthorityError("execution authority requires semantic snapshot fingerprint")
        for label, pins in (
            ("operational profiles", self.operational_profile_pins),
            ("dynamics parameters", self.dynamics_parameter_pins),
            ("causal mechanisms", self.causal_mechanism_pins),
            ("use authorizations", self.use_authorization_pins),
            ("projection authority", self.projection_authority_pins),
            ("policy/adapters", self.policy_adapter_pins),
        ):
            _require_unique((pin.key for pin in pins), f"execution {label}")
        payload = (
            self.semantic_authority_snapshot_fingerprint,
            tuple(pin.key for pin in self.operational_profile_pins),
            tuple(pin.key for pin in self.dynamics_parameter_pins),
            tuple(pin.key for pin in self.causal_mechanism_pins),
            tuple(pin.key for pin in self.use_authorization_pins),
            tuple(pin.key for pin in self.projection_authority_pins),
            tuple(pin.key for pin in self.policy_adapter_pins),
            self.projection_authority_required,
        )
        object.__setattr__(self, "envelope_ref", "execution-authority:" + _sha(payload))

    def verify(self, graph: CSIRGraph, snapshot: AuthoritySnapshotV351) -> None:
        if self.semantic_authority_snapshot_fingerprint != snapshot.snapshot_fingerprint:
            raise SemanticAuthorityError("execution authority snapshot mismatch")
        for pin in (
            *self.operational_profile_pins, *self.dynamics_parameter_pins,
            *self.causal_mechanism_pins, *self.use_authorization_pins,
            *self.projection_authority_pins, *self.policy_adapter_pins,
        ):
            snapshot.require_known_pin(pin)
        observed_profiles = {
            pin.key for application in graph.applications for pin in application.operational_profile_pins
        }
        if observed_profiles != {pin.key for pin in self.operational_profile_pins}:
            raise SemanticAuthorityError("execution envelope profile pins differ from CSIR applications")
        if self.projection_authority_required and graph.applications and not self.projection_authority_pins:
            raise SemanticAuthorityError("execution envelope requires exact projection authority")
        expected_dynamics = {item.parameter_pin.key for item in snapshot.dynamics_parameters}
        if {pin.key for pin in self.dynamics_parameter_pins} != expected_dynamics:
            raise SemanticAuthorityError("execution envelope does not pin exact active dynamics parameter set")


@dataclass(frozen=True, slots=True)
class DefinitionClosure:
    root_pin: ExactAuthorityPin
    ordered_definitions: tuple[SemanticDefinition, ...]
    ordered_pins: tuple[ExactAuthorityPin, ...]
    dependency_edges: tuple[tuple[ExactAuthorityPin, ExactAuthorityPin], ...]

    @property
    def pins(self) -> tuple[ExactAuthorityPin, ...]:
        # Includes exact non-definition semantic leaves (types/operators/values/etc.)
        # in deterministic dependency-before-dependent order; root definition remains last.
        return self.ordered_pins

    @property
    def constraint_pins(self) -> tuple[ExactAuthorityPin, ...]:
        unique = {
            pin.key: pin
            for definition in self.ordered_definitions
            for pin in definition.constraint_pins
        }
        return tuple(unique[key] for key in sorted(unique))


class DefinitionClosureResolver:
    """Resolve least exact dependency closure under one immutable AuthorityGeneration."""

    def __init__(self, snapshot: AuthoritySnapshotV351) -> None:
        self.snapshot = snapshot
        self._cache: dict[tuple[str, str, str, int, str, str], DefinitionClosure] = {}

    def resolve(self, root_pin: ExactAuthorityPin) -> DefinitionClosure:
        cached = self._cache.get(root_pin.key)
        if cached is not None:
            return cached
        ordered: list[SemanticDefinition] = []
        ordered_pins: list[ExactAuthorityPin] = []
        edges: list[tuple[ExactAuthorityPin, ExactAuthorityPin]] = []
        visiting: set[tuple[str, str, str, int, str, str]] = set()
        visited: set[tuple[str, str, str, int, str, str]] = set()
        pin_seen: set[tuple[str, str, str, int, str, str]] = set()
        definition_keys = set(self.snapshot.definition_index)

        def append_pin(pin: ExactAuthorityPin) -> None:
            if pin.key not in pin_seen:
                pin_seen.add(pin.key)
                ordered_pins.append(pin)

        def visit(pin: ExactAuthorityPin) -> None:
            if pin.key in visited:
                return
            if pin.key in visiting:
                raise CyclicDefinitionClosure(f"cyclic exact semantic definition closure at:{pin.key}")
            visiting.add(pin.key)
            definition = self.snapshot.require_definition(pin)
            for constraint_pin in definition.constraint_pins:
                self.snapshot.require_known_pin(constraint_pin)
            for dependency in sorted(definition.semantic_dependency_pins, key=lambda item: item.key):
                edges.append((definition.definition_pin, dependency))
                if dependency.key in definition_keys:
                    visit(dependency)
                else:
                    # Exact semantic leaf authority participates in the closure but is not
                    # recursively expanded as though it were a SemanticDefinition.
                    self.snapshot.require_known_pin(dependency)
                    append_pin(dependency)
            visiting.remove(pin.key)
            visited.add(pin.key)
            ordered.append(definition)
            append_pin(definition.definition_pin)

        visit(root_pin)
        closure = DefinitionClosure(root_pin, tuple(ordered), tuple(ordered_pins), tuple(edges))
        self._cache[root_pin.key] = closure
        return closure


@dataclass(frozen=True, slots=True)
class ClosureProof:
    root_definition_pin: ExactAuthorityPin
    authority_generation: int
    authority_fingerprint: str
    semantic_authority_snapshot_fingerprint: str
    closure_pins: tuple[ExactAuthorityPin, ...]
    dependency_edges: tuple[tuple[ExactAuthorityPin, ExactAuthorityPin], ...]
    constraint_pins: tuple[ExactAuthorityPin, ...]
    expanded_template_semantic_fingerprint: str
    compiled_semantic_fingerprint: str
    compiled_structural_exact_fingerprint: str
    expected_semantic_fingerprint: str | None
    conservative: bool
    compiler_abi: str = SEMANTIC_DEFINITION_COMPILER_ABI
    closure_abi: str = DEFINITION_CLOSURE_ABI
    kernel_abi_fingerprint: str = CURRENT_KERNEL_ABI.fingerprint
    proof_ref: str = field(init=False)

    def __post_init__(self) -> None:
        if self.authority_generation < 1 or not self.authority_fingerprint.strip():
            raise ClosureProofError("closure proof requires exact AuthorityGeneration")
        if not self.semantic_authority_snapshot_fingerprint.strip():
            raise ClosureProofError("closure proof requires exact semantic authority snapshot fingerprint")
        if (
            not self.expanded_template_semantic_fingerprint
            or not self.compiled_semantic_fingerprint
            or not self.compiled_structural_exact_fingerprint
        ):
            raise ClosureProofError("closure proof requires template and compiled fingerprints")
        if not self.closure_pins or self.closure_pins[-1].key != self.root_definition_pin.key:
            raise ClosureProofError("closure proof must end with its root definition")
        _require_unique((pin.key for pin in self.constraint_pins), "closure constraint pins")
        if self.kernel_abi_fingerprint != CURRENT_KERNEL_ABI.fingerprint:
            raise ClosureProofError("closure proof kernel ABI mismatch")
        payload = (
            self.root_definition_pin.key,
            self.authority_generation,
            self.authority_fingerprint,
            self.semantic_authority_snapshot_fingerprint,
            tuple(pin.key for pin in self.closure_pins),
            tuple((left.key, right.key) for left, right in self.dependency_edges),
            tuple(pin.key for pin in self.constraint_pins),
            self.expanded_template_semantic_fingerprint,
            self.compiled_semantic_fingerprint,
            self.compiled_structural_exact_fingerprint,
            self.expected_semantic_fingerprint,
            self.conservative,
            self.compiler_abi,
            self.closure_abi,
            self.kernel_abi_fingerprint,
        )
        object.__setattr__(self, "proof_ref", "closure-proof:" + _sha(payload))

    def verify_authority(self, authority_snapshot: "AuthoritySnapshotV351") -> None:
        """Verify closure lineage against the actual immutable semantic authority snapshot."""
        if (self.authority_generation, self.authority_fingerprint) != (
            authority_snapshot.generation, authority_snapshot.authority_fingerprint
        ):
            raise ClosureProofError("closure proof belongs to another AuthorityGeneration")
        if self.kernel_abi_fingerprint != CURRENT_KERNEL_ABI.fingerprint:
            raise ClosureProofError("closure proof kernel ABI is stale")
        if authority_snapshot.snapshot_fingerprint != self.semantic_authority_snapshot_fingerprint:
            raise ClosureProofError("closure proof semantic authority snapshot fingerprint mismatch")
        resolved = DefinitionClosureResolver(authority_snapshot).resolve(self.root_definition_pin)
        if tuple(pin.key for pin in resolved.pins) != tuple(pin.key for pin in self.closure_pins):
            raise ClosureProofError("closure proof pins differ from exact authority closure")
        expected_edges = tuple((left.key, right.key) for left, right in resolved.dependency_edges)
        observed_edges = tuple((left.key, right.key) for left, right in self.dependency_edges)
        if observed_edges != expected_edges:
            raise ClosureProofError("closure proof dependency edges differ from exact authority closure")
        if tuple(pin.key for pin in self.constraint_pins) != tuple(
            pin.key for pin in resolved.constraint_pins
        ):
            raise ClosureProofError("closure proof constraint pins differ from exact authority closure")
        for constraint_pin in self.constraint_pins:
            authority_snapshot.require_known_pin(constraint_pin)
        template_graph = SemanticDefinitionCompiler(authority_snapshot).expanded_template(
            self.root_definition_pin
        )
        template_fp = semantic_fingerprint(normalize(template_graph))
        if template_fp != self.expanded_template_semantic_fingerprint:
            raise ClosureProofError("closure proof expanded-template fingerprint mismatch")
        if (
            self.expected_semantic_fingerprint is not None
            and template_fp != self.expected_semantic_fingerprint
        ):
            raise ClosureProofError("closure proof expected definition-template fingerprint mismatch")
        if not self.conservative:
            raise ClosureProofError("non-conservative higher-order definition is not executable")

    def verify(
        self,
        graph: CSIRGraph,
        *,
        authority_generation: int,
        authority_fingerprint: str,
        authority_snapshot: "AuthoritySnapshotV351 | None" = None,
    ) -> None:
        if (self.authority_generation, self.authority_fingerprint) != (
            authority_generation,
            authority_fingerprint,
        ):
            raise ClosureProofError("closure proof belongs to another AuthorityGeneration")
        if self.kernel_abi_fingerprint != CURRENT_KERNEL_ABI.fingerprint:
            raise ClosureProofError("closure proof kernel ABI is stale")
        if authority_snapshot is not None:
            if (authority_snapshot.generation, authority_snapshot.authority_fingerprint) != (
                authority_generation, authority_fingerprint
            ):
                raise ClosureProofError("closure proof snapshot differs from pinned AuthorityGeneration")
            self.verify_authority(authority_snapshot)
            closure_keys = {pin.key for pin in self.closure_pins}
            uncovered = sorted(
                application.predicate_pin.key
                for application in graph.applications
                if application.predicate_pin.key not in closure_keys
            )
            if uncovered:
                raise ClosureProofError(f"candidate contains predicates outside proven closure:{uncovered}")
        normalized = normalize(graph)
        semantic = semantic_fingerprint(normalized)
        structural = semantic_structural_exact_fingerprint(normalized)
        if semantic != self.compiled_semantic_fingerprint:
            raise ClosureProofError("closure proof semantic fingerprint mismatch")
        if structural != self.compiled_structural_exact_fingerprint:
            raise ClosureProofError("closure proof structural exact fingerprint mismatch")
        if not self.conservative:
            raise ClosureProofError("non-conservative higher-order definition is not executable")
        if (
            self.expected_semantic_fingerprint is not None
            and self.expanded_template_semantic_fingerprint != self.expected_semantic_fingerprint
        ):
            raise ClosureProofError("closure proof expected definition-template fingerprint mismatch")


@dataclass(frozen=True, slots=True)
class HardConstraintEvaluation:
    constraint_pin: ExactAuthorityPin
    satisfied: bool
    evidence_refs: tuple[str, ...] = ()
    evaluator_pin: ExactAuthorityPin | None = None

    def __post_init__(self) -> None:
        _require_unique(self.evidence_refs, "constraint evaluation evidence refs")


@dataclass(frozen=True, slots=True)
class HardConstraintTrace:
    authority_generation: int
    authority_fingerprint: str
    semantic_authority_snapshot_fingerprint: str
    graph_structural_exact_fingerprint: str
    evaluations: tuple[HardConstraintEvaluation, ...]
    trace_ref: str = field(init=False)

    def __post_init__(self) -> None:
        if self.authority_generation < 1 or not self.authority_fingerprint.strip():
            raise SemanticAuthorityError("hard constraint trace requires exact AuthorityGeneration")
        if not self.semantic_authority_snapshot_fingerprint.strip():
            raise SemanticAuthorityError("hard constraint trace requires semantic authority snapshot fingerprint")
        _require_unique((item.constraint_pin.key for item in self.evaluations), "constraint evaluations")
        payload = (
            self.authority_generation,
            self.authority_fingerprint,
            self.semantic_authority_snapshot_fingerprint,
            self.graph_structural_exact_fingerprint,
            tuple(
                (
                    item.constraint_pin.key,
                    item.satisfied,
                    tuple(sorted(item.evidence_refs)),
                    None if item.evaluator_pin is None else item.evaluator_pin.key,
                )
                for item in sorted(self.evaluations, key=lambda x: x.constraint_pin.key)
            ),
        )
        object.__setattr__(self, "trace_ref", "hard-constraint-trace:" + _sha(payload))

    def verify(
        self,
        graph: CSIRGraph,
        *,
        authority_snapshot: AuthoritySnapshotV351,
        required_constraint_pins: Iterable[ExactAuthorityPin],
    ) -> None:
        if (self.authority_generation, self.authority_fingerprint) != (
            authority_snapshot.generation, authority_snapshot.authority_fingerprint
        ):
            raise SemanticAuthorityError("hard constraint trace belongs to another AuthorityGeneration")
        if self.semantic_authority_snapshot_fingerprint != authority_snapshot.snapshot_fingerprint:
            raise SemanticAuthorityError("hard constraint trace semantic authority snapshot mismatch")
        structural = semantic_structural_exact_fingerprint(graph)
        if structural != self.graph_structural_exact_fingerprint:
            raise SemanticAuthorityError("hard constraint trace graph fingerprint mismatch")
        required = {pin.key for pin in required_constraint_pins}
        observed = {item.constraint_pin.key for item in self.evaluations}
        if observed != required:
            raise SemanticAuthorityError("hard constraint trace does not exactly cover required constraints")
        for evaluation in self.evaluations:
            authority_snapshot.require_known_pin(evaluation.constraint_pin)
            if evaluation.evaluator_pin is not None:
                authority_snapshot.require_known_pin(evaluation.evaluator_pin)
            if not evaluation.satisfied:
                raise SemanticAuthorityError(
                    f"hard constraint not satisfied:{evaluation.constraint_pin.key}"
                )


@dataclass(frozen=True, slots=True)
class CompiledDefinition:
    graph: CSIRGraph
    closure_proof: ClosureProof


class CSIRNormalizer:
    ABI = CURRENT_KERNEL_ABI.normalizer_abi

    @staticmethod
    def normalize(graph: CSIRGraph, *, budget: int = 100_000) -> CSIRGraph:
        return normalize(graph, budget=budget)

    @staticmethod
    def semantic_fingerprint(graph: CSIRGraph, *, budget: int = 100_000) -> str:
        return semantic_fingerprint(graph, budget=budget)


class SemanticDefinitionCompiler:
    """Compile exact higher-order definitions to kernel CSIR under a pinned snapshot.

    Compilation is generic graph substitution; it contains no named concepts, English
    tokens, event-specific mutation code or ontology branches.
    """

    ABI = SEMANTIC_DEFINITION_COMPILER_ABI

    def __init__(self, snapshot: AuthoritySnapshotV351) -> None:
        self.snapshot = snapshot
        self.closure_resolver = DefinitionClosureResolver(snapshot)

    @staticmethod
    def _rename_graph(
        graph: CSIRGraph, prefix: str
    ) -> tuple[CSIRGraph, Mapping[tuple[str, str], str]]:
        mapping: dict[tuple[str, str], str] = {}
        for kind, values, attr in (
            ("term", graph.terms, "term_ref"),
            ("variable", graph.variables, "variable_ref"),
            ("application", graph.applications, "application_ref"),
            ("coordination", graph.coordinations, "coordination_ref"),
            ("binding", graph.bindings, "binding_ref"),
            ("qualifier", graph.qualifiers, "qualifier_ref"),
            ("scope", graph.scope_embeddings, "embedding_ref"),
            ("proof", graph.proof_links, "proof_ref"),
        ):
            for value in values:
                old = str(getattr(value, attr))
                mapping[(kind, old)] = f"{prefix}:{kind}:{old}"

        def ref(value: CSIRRef) -> CSIRRef:
            return CSIRRef(value.kind, mapping[(value.kind.value, value.ref)])

        renamed = CSIRGraph(
            terms=tuple(replace(x, term_ref=mapping[("term", x.term_ref)]) for x in graph.terms),
            variables=tuple(replace(x, variable_ref=mapping[("variable", x.variable_ref)]) for x in graph.variables),
            applications=tuple(replace(x, application_ref=mapping[("application", x.application_ref)]) for x in graph.applications),
            bindings=tuple(
                replace(
                    x,
                    binding_ref=mapping[("binding", x.binding_ref)],
                    application_ref=mapping[("application", x.application_ref)],
                    fillers=tuple(ref(item) for item in x.fillers),
                )
                for x in graph.bindings
            ),
            qualifiers=tuple(
                replace(
                    x,
                    qualifier_ref=mapping[("qualifier", x.qualifier_ref)],
                    target=ref(x.target),
                    value_ref=None if x.value_ref is None else ref(x.value_ref),
                )
                for x in graph.qualifiers
            ),
            scope_embeddings=tuple(
                replace(
                    x,
                    embedding_ref=mapping[("scope", x.embedding_ref)],
                    operator=ref(x.operator),
                    scoped=ref(x.scoped),
                )
                for x in graph.scope_embeddings
            ),
            coordinations=tuple(
                replace(
                    x,
                    coordination_ref=mapping[("coordination", x.coordination_ref)],
                    members=tuple(ref(item) for item in x.members),
                )
                for x in graph.coordinations
            ),
            proof_links=tuple(
                replace(
                    x,
                    proof_ref=mapping[("proof", x.proof_ref)],
                    subject_refs=tuple(ref(item) for item in x.subject_refs),
                    parent_proof_refs=tuple(mapping[("proof", item)] for item in x.parent_proof_refs),
                )
                for x in graph.proof_links
            ),
            root_refs=tuple(ref(item) for item in graph.root_refs),
            unresolved_refs=graph.unresolved_refs,
        )
        return renamed, mapping

    @staticmethod
    def _merge(left: CSIRGraph, right: CSIRGraph) -> CSIRGraph:
        # Constructors validate duplicate/dangling refs. Prefixing makes definition-local
        # refs collision-free; caller-supplied external graphs are required to be unique.
        return CSIRGraph(
            terms=(*left.terms, *right.terms),
            variables=(*left.variables, *right.variables),
            applications=(*left.applications, *right.applications),
            bindings=(*left.bindings, *right.bindings),
            qualifiers=(*left.qualifiers, *right.qualifiers),
            scope_embeddings=(*left.scope_embeddings, *right.scope_embeddings),
            coordinations=(*left.coordinations, *right.coordinations),
            proof_links=(*left.proof_links, *right.proof_links),
            root_refs=(*left.root_refs, *right.root_refs),
            unresolved_refs=tuple(sorted(set((*left.unresolved_refs, *right.unresolved_refs)))),
        )

    def _expand(
        self,
        definition: SemanticDefinition,
        path: tuple[str, ...],
    ) -> tuple[
        CSIRGraph,
        Mapping[tuple[str, str, str, int, str, str], str],
        Mapping[tuple[str, str], str],
    ]:
        prefix = "def:" + _sha((definition.definition_pin.key, path))[:20]
        graph, local_map = self._rename_graph(definition.body, prefix)
        formal_variables = {
            _pin_key(port.port_pin): local_map[("variable", port.variable_ref)]
            for port in definition.formal_ports
        }

        for invocation in sorted(definition.invocations, key=lambda item: item.invocation_ref):
            child = self.snapshot.require_definition(invocation.definition_pin)
            child_graph, child_formals, _child_map = self._expand(
                child, (*path, invocation.invocation_ref)
            )
            graph = self._merge(graph, child_graph)
            provided = {_pin_key(port_pin): value for port_pin, value in invocation.argument_bindings}
            child_ports = {_pin_key(item.port_pin): item for item in child.formal_ports}
            unknown = set(provided).difference(child_ports)
            if unknown:
                raise SemanticAuthorityError(
                    f"invocation binds unknown child ports:{sorted(unknown)}"
                )
            for port_key, port in child_ports.items():
                value = provided.get(port_key)
                if value is None:
                    if port.minimum > 0:
                        raise SemanticAuthorityError(
                            f"invocation missing required child port:{port.port_pin.key}"
                        )
                    continue
                parent_key = (value.kind.value, value.ref)
                if parent_key not in local_map:
                    raise SemanticAuthorityError(
                        f"invocation argument must reference parent-local node:{value}"
                    )
                replacement = CSIRRef(value.kind, local_map[parent_key])
                graph = bind(graph, child_formals[port_key], replacement)
        return graph, formal_variables, local_map

    def expanded_template(self, root_pin: ExactAuthorityPin) -> CSIRGraph:
        # Definition-level conservativity is checked before grounding/instantiation.
        # Concrete referent arguments are occurrence content and must not change the
        # semantic identity of the higher-order definition itself.
        self.closure_resolver.resolve(root_pin)
        root = self.snapshot.require_definition(root_pin)
        graph, _formals, _local_map = self._expand(root, (root_pin.ref,))
        return graph

    def compile(
        self,
        root_pin: ExactAuthorityPin,
        *,
        external_graph: CSIRGraph | None = None,
        arguments: Mapping[ExactAuthorityPin, CSIRRef] | None = None,
        canonicalization_budget: int = 100_000,
    ) -> CompiledDefinition:
        closure = self.closure_resolver.resolve(root_pin)
        root = self.snapshot.require_definition(root_pin)
        graph, formals, _local_map = self._expand(root, (root_pin.ref,))
        expanded_template_semantic = semantic_fingerprint(
            normalize(graph, budget=canonicalization_budget),
            budget=canonicalization_budget,
        )
        if external_graph is not None:
            graph = self._merge(external_graph, graph)
        arguments = {_pin_key(pin): value for pin, value in dict(arguments or {}).items()}
        root_ports = {_pin_key(item.port_pin): item for item in root.formal_ports}
        unknown = set(arguments).difference(root_ports)
        if unknown:
            raise SemanticAuthorityError(f"root arguments bind unknown ports:{sorted(unknown)}")
        for port_key, port in root_ports.items():
            value = arguments.get(port_key)
            if value is None:
                if port.minimum > 0:
                    raise SemanticAuthorityError(
                        f"missing required root port:{port.port_pin.key}"
                    )
                continue
            if graph.node(value) is None:
                raise SemanticAuthorityError(
                    f"root argument filler does not exist in compiled/external graph:{value}"
                )
            graph = bind(graph, formals[port_key], value)

        normalized = normalize(graph, budget=canonicalization_budget)
        semantic = semantic_fingerprint(normalized, budget=canonicalization_budget)
        structural = semantic_structural_exact_fingerprint(normalized)
        conservative = (
            root.expected_semantic_fingerprint is None
            or root.expected_semantic_fingerprint == expanded_template_semantic
        )
        if root.executable and not conservative:
            raise NonConservativeDefinition(
                f"definition {root.definition_pin.ref} expansion is not conservative"
            )
        proof = ClosureProof(
            root_definition_pin=root.definition_pin,
            authority_generation=self.snapshot.generation,
            authority_fingerprint=self.snapshot.authority_fingerprint,
            semantic_authority_snapshot_fingerprint=self.snapshot.snapshot_fingerprint,
            closure_pins=closure.pins,
            dependency_edges=closure.dependency_edges,
            constraint_pins=closure.constraint_pins,
            expanded_template_semantic_fingerprint=expanded_template_semantic,
            compiled_semantic_fingerprint=semantic,
            compiled_structural_exact_fingerprint=structural,
            expected_semantic_fingerprint=root.expected_semantic_fingerprint,
            conservative=conservative,
        )
        proof.verify(
            normalized,
            authority_generation=self.snapshot.generation,
            authority_fingerprint=self.snapshot.authority_fingerprint,
            authority_snapshot=self.snapshot,
        )
        return CompiledDefinition(normalized, proof)


__all__ = [
    "AuthoritySnapshotV351",
    "CausalMechanism",
    "ClosureProof",
    "ClosureProofError",
    "CompiledDefinition",
    "CSIRNormalizer",
    "CyclicDefinitionClosure",
    "DEFINITION_CLOSURE_ABI",
    "DefinitionClosure",
    "DefinitionClosureResolver",
    "DefinitionInvocation",
    "DynamicsParameterArtifact",
    "ExecutableAuthorityEnvelope",
    "FormalPort",
    "HardConstraintEvaluation",
    "HardConstraintTrace",
    "MissingExactDependency",
    "NonConservativeDefinition",
    "ObservationModel",
    "OperationalProfile",
    "SEMANTIC_DEFINITION_COMPILER_ABI",
    "SemanticAuthorityError",
    "SemanticDefinition",
    "SemanticDefinitionCompiler",
    "semantic_structural_exact_fingerprint",
    "UseAuthorization",
]
