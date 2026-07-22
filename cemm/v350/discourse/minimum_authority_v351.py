"""Reviewed exact discourse-wrapper authority for the minimum conversational kernel.

The artifacts returned here are deterministic candidate/release inputs.  They are not
made authoritative merely by importing this module.  Runtime recognition is permitted
only when the exact content-addressed pins are present in the pinned AuthorityGeneration.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json

from ..csir.authority_v351 import FormalPort, OperationalProfile, SemanticDefinition, UseAuthorization
from ..csir.model import CSIRGraph, CSIRNodeKind, ExactAuthorityPin, PortBinding, SemanticApplication, SemanticVariable
from .model import DiscourseActAuthority, DiscourseActKind, DiscourseAuthorityMap


@dataclass(frozen=True, slots=True)
class MinimumDiscourseAuthorityArtifacts:
    semantic_definitions: tuple[SemanticDefinition, ...]
    operational_profiles: tuple[OperationalProfile, ...]
    use_authorizations: tuple[UseAuthorization, ...]
    authority_map: DiscourseAuthorityMap
    semantic_slot_pins: tuple[tuple[str, ExactAuthorityPin], ...]
    competence_case_refs: tuple[str, ...]
    competence_case_pins: tuple[ExactAuthorityPin, ...]

    @property
    def binding_map(self):
        return dict(self.semantic_slot_pins)


def _hash(value) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def _pin(kind: str, ref: str, payload) -> ExactAuthorityPin:
    return ExactAuthorityPin(kind, "cemm:v351:discourse", ref, 1, _hash(payload), "global")


def compile_minimum_discourse_authority() -> MinimumDiscourseAuthorityArtifacts:
    specs = (
        ("discourse:query", DiscourseActKind.QUERY),
        ("discourse:correction", DiscourseActKind.CORRECTION),
        ("discourse:definition", DiscourseActKind.DEFINITION),
        ("discourse:greeting", DiscourseActKind.GREETING),
        ("discourse:request", DiscourseActKind.REQUEST),
        ("discourse:retraction", DiscourseActKind.RETRACTION),
    )
    definitions = []
    profiles = []
    authorizations = []
    authorities = []
    bindings = []
    cases = []
    case_pins = []
    for semantic_slot, act_kind in specs:
        payload = {"semantic_slot": semantic_slot, "act_kind": act_kind.value, "revision": 1}
        definition_pin = _pin("semantic_definition", semantic_slot, payload)
        content_port = _pin("semantic_port", f"{semantic_slot}:port:content", (payload, "content"))
        variable = SemanticVariable(
            variable_ref=f"discourse-var:{act_kind.value}:content",
            allowed_kinds=frozenset({CSIRNodeKind.TERM, CSIRNodeKind.APPLICATION, CSIRNodeKind.COORDINATION}),
            scope_ref="discourse", open_purpose="discourse_content",
        )
        app = SemanticApplication(f"discourse-template:{act_kind.value}", definition_pin)
        body = CSIRGraph(
            variables=(variable,), applications=(app,),
            bindings=(PortBinding(
                binding_ref=f"discourse-binding:{act_kind.value}:content",
                application_ref=app.application_ref, port_pin=content_port,
                fillers=(variable.node_ref,),
            ),),
            root_refs=(app.node_ref,),
        )
        definitions.append(SemanticDefinition(
            definition_pin=definition_pin, body=body,
            formal_ports=(FormalPort(content_port, variable.variable_ref, 1, 1),),
            provenance_refs=("review:v351:phase12:minimum-discourse-authority",),
        ))
        case_ref = f"competence:discourse:{act_kind.value}:reabstraction"
        competence_pin = _pin("competence_case", case_ref, (payload, "competence", "reabstraction"))
        profile_pin = _pin("operational_profile", f"{semantic_slot}:profile", (payload, "profile", competence_pin.key))
        profiles.append(OperationalProfile(
            profile_pin=profile_pin, definition_pin=definition_pin,
            lifecycle_status="active", allowed_operations=("compose",), permission_scopes=(),
            competence_case_pins=(competence_pin,),
        ))
        auth_pin = _pin("use_authorization", f"{semantic_slot}:compose", (payload, "compose", "allow"))
        authorizations.append(UseAuthorization(
            authorization_pin=auth_pin, target_pin=definition_pin,
            operation="compose", decision="allow", evidence_refs=(case_ref,),
        ))
        authorities.append(DiscourseActAuthority(
            definition_pin=definition_pin, act_kind=act_kind, content_port_pin=content_port,
        ))
        bindings.append((semantic_slot, definition_pin))
        cases.append(case_ref)
        case_pins.append(competence_pin)
    return MinimumDiscourseAuthorityArtifacts(
        semantic_definitions=tuple(definitions), operational_profiles=tuple(profiles),
        use_authorizations=tuple(authorizations),
        authority_map=DiscourseAuthorityMap(tuple(authorities)),
        semantic_slot_pins=tuple(bindings), competence_case_refs=tuple(cases),
        competence_case_pins=tuple(case_pins),
    )


__all__ = ["MinimumDiscourseAuthorityArtifacts", "compile_minimum_discourse_authority"]
