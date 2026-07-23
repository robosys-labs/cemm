"""Reviewed source compiler for the minimum Phase-12 response-family authority.

This module creates deterministic *candidate authority artifacts*.  It never mutates an
active AuthorityGeneration.  Release/activation tooling must explicitly include the
returned definitions/profiles/use-authorizations in a new immutable snapshot after
competence review.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from ..csir.authority_v351 import FormalPort, OperationalProfile, SemanticDefinition, UseAuthorization
from ..csir.model import CSIRGraph, CSIRNodeKind, ExactAuthorityPin, PortBinding, SemanticApplication, SemanticVariable
from .csir_v351 import ResponseAuthorityMapV351, ResponseFamily, ResponseFamilyAuthority


@dataclass(frozen=True, slots=True)
class MinimumResponseAuthorityArtifacts:
    semantic_definitions: tuple[SemanticDefinition, ...]
    operational_profiles: tuple[OperationalProfile, ...]
    use_authorizations: tuple[UseAuthorization, ...]
    authority_map: ResponseAuthorityMapV351
    competence_case_refs: tuple[str, ...]
    competence_case_pins: tuple[ExactAuthorityPin, ...]


def _hash(value) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return hashlib.sha256(encoded).hexdigest()


def _pin(kind: str, ref: str, payload, *, namespace: str = "cemm:v351:response") -> ExactAuthorityPin:
    return ExactAuthorityPin(kind, namespace, ref, 1, _hash(payload), "global")


def compile_minimum_response_authority() -> MinimumResponseAuthorityArtifacts:
    # Each tuple is (family, port names with minimum cardinality).  Port names are reviewed
    # semantic-role identifiers inside this authority package; they are never emitted.
    specs = (
        (ResponseFamily.ANSWER_QUERY, (("content", 1),)),
        (ResponseFamily.GREET, ()),
        (ResponseFamily.REPORT_STATE, (("content", 1),)),
        (ResponseFamily.REPORT_RELATION, (("content", 1),)),
        (ResponseFamily.REPORT_EVENT, (("content", 1),)),
        (ResponseFamily.ACKNOWLEDGE_TARGETED_CLAIM, ()),
        (ResponseFamily.REQUEST_CLARIFICATION, ()),
        (ResponseFamily.CORRECT_PRIOR_OUTPUT, (("content", 1),)),
        (ResponseFamily.QUALIFY_UNCERTAINTY, ()),
        (ResponseFamily.REPORT_CAPABILITY, (("content", 1),)),
        (ResponseFamily.PROVIDE_CAUSAL_EXPLANATION, (("cause", 1), ("effect", 1))),
        (ResponseFamily.ASK_LEARNING_QUESTION, ()),
    )
    definitions = []
    profiles = []
    authorizations = []
    mappings = []
    cases = []
    case_pins = []

    for family, ports in specs:
        base = {"family": family.value, "ports": ports, "revision": 1}
        definition_pin = _pin("semantic_definition", f"response:{family.value}", base)
        app_ref = f"response-template:{family.value}"
        variables = []
        formals = []
        bindings = []
        role_pins = {}
        for name, minimum in ports:
            port_pin = _pin("semantic_port", f"response:{family.value}:port:{name}", (base, name, minimum))
            variable_ref = f"response-var:{family.value}:{name}"
            variable = SemanticVariable(
                variable_ref=variable_ref,
                allowed_kinds=frozenset({CSIRNodeKind.TERM, CSIRNodeKind.APPLICATION, CSIRNodeKind.COORDINATION}),
                scope_ref="response",
                open_purpose="response_formal",
            )
            variables.append(variable)
            formals.append(FormalPort(port_pin, variable_ref, minimum=minimum, maximum=1))
            bindings.append(PortBinding(
                binding_ref=f"response-binding:{family.value}:{name}",
                application_ref=app_ref,
                port_pin=port_pin,
                fillers=(variable.node_ref,),
            ))
            role_pins[name] = port_pin
        app = SemanticApplication(app_ref, definition_pin)
        body = CSIRGraph(
            variables=tuple(variables), applications=(app,), bindings=tuple(bindings),
            root_refs=(app.node_ref,),
        )
        definition = SemanticDefinition(
            definition_pin=definition_pin,
            body=body,
            formal_ports=tuple(formals),
            provenance_refs=("review:v351:phase12:minimum-response-authority",),
        )
        competence_ref = f"competence:response:{family.value}:semantic-preservation"
        competence_pin = _pin(
            "competence_case", competence_ref, (base, "competence", "semantic-preservation"),
        )
        profile_pin = _pin("operational_profile", f"response:{family.value}:profile", (base, "profile", competence_pin.key))
        profile = OperationalProfile(
            profile_pin=profile_pin,
            definition_pin=definition_pin,
            lifecycle_status="active",
            allowed_operations=("compose", "realize"),
            permission_scopes=(), competence_case_pins=(competence_pin,),
        )
        for operation in ("compose", "realize"):
            auth_pin = _pin(
                "use_authorization", f"response:{family.value}:{operation}",
                (base, operation, "allow"),
            )
            authorizations.append(UseAuthorization(
                authorization_pin=auth_pin, target_pin=definition_pin,
                operation=operation, decision="allow", context_scopes=(),
                permission_scopes=(), evidence_refs=(competence_ref,),
            ))
        definitions.append(definition)
        profiles.append(profile)
        cases.append(competence_ref)
        case_pins.append(competence_pin)
        mappings.append(ResponseFamilyAuthority(
            family=family,
            definition_pin=definition_pin,
            content_port_pin=role_pins.get("content"),
            target_port_pin=role_pins.get("target"),
            uncertainty_port_pin=role_pins.get("uncertainty"),
            cause_port_pin=role_pins.get("cause"),
            effect_port_pin=role_pins.get("effect"),
        ))

    return MinimumResponseAuthorityArtifacts(
        semantic_definitions=tuple(definitions),
        operational_profiles=tuple(profiles),
        use_authorizations=tuple(authorizations),
        authority_map=ResponseAuthorityMapV351(tuple(mappings)),
        competence_case_refs=tuple(cases), competence_case_pins=tuple(case_pins),
    )


__all__ = ["MinimumResponseAuthorityArtifacts", "compile_minimum_response_authority"]
