"""Pure authority validation for the native semantic contribution spine.

This validator runs while all authority documents are still in memory. It never
queries mutable world state and never repairs malformed authority. Every issue is
reported to the bundle linker before the first durable write.
"""
from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

_PORT = re.compile(r"^[a-z][a-z0-9_.-]*:[A-Za-z0-9_.-]+$")
_ALLOWED_CONTRIBUTIONS = frozenset({
    "anchor", "predicate", "binder", "reference", "scope", "discourse",
    "connector", "qualifier", "literal", "open_variable",
})
_ALLOWED_CONTRACT_TARGET_KINDS = frozenset({
    "concept", "entity", "participant", "resource", "source", "event",
    "event_type", "relation_type", "state_dimension", "value", "label_type",
    "capability", "time", "place", "quantity",
})
_MAX_PORTS = 16
_MAX_FRAME_ROLES = 12
_MAX_TARGET_KINDS = 16
_MAX_QUERY_KINDS = 16
_PREDICATE_OPERATOR_BY_TARGET_KIND = {
    "concept": "op:type",
    "event_type": "op:event",
    "relation_type": "op:relation",
    "state_dimension": "op:state",
    "value": "op:state",
    "label_type": "op:designation",
}


def _metadata(atom: Mapping[str, Any] | Any) -> Mapping[str, Any]:
    if isinstance(atom, Mapping):
        value = atom.get("metadata", {})
        return value if isinstance(value, Mapping) else {}
    return {}


def _ref_list(value: Any, *, label: str, issues: list[str], limit: int) -> tuple[str, ...]:
    if value in (None, ()):
        return ()
    if not isinstance(value, (list, tuple)):
        issues.append(f"{label} must be a bounded list")
        return ()
    refs = tuple(str(item) for item in value)
    if len(refs) > limit:
        issues.append(f"{label} exceeds bound {limit}")
    if any(not item or not _PORT.fullmatch(item) for item in refs):
        issues.append(f"{label} contains malformed semantic refs/ports")
    if len(refs) != len(set(refs)):
        issues.append(f"{label} contains duplicates")
    return refs


def validate_native_semantic_authority(
    *,
    atom_defs: Mapping[str, Mapping[str, Any]],
    role_defs: Mapping[tuple[str, str], Mapping[str, Any]],
    facts: Sequence[tuple[Mapping[str, Any], str]],
) -> tuple[str, ...]:
    """Return all native semantic authority issues without mutating input."""
    issues: list[str] = []
    atom_kinds = {str(ref): str(item.get("kind")) for ref, item in atom_defs.items()}

    frame_links: dict[str, list[tuple[str, str]]] = {}
    capability_contract_links: set[tuple[str, str]] = set()
    for fact, location in facts:
        if fact.get("operator") != "op:relation":
            continue
        args = fact.get("args", {})
        if not isinstance(args, Mapping):
            continue
        subject = args.get("role:subject")
        relation = args.get("role:relation")
        obj = args.get("role:object")
        if relation == "rel:has_semantic_frame" and isinstance(subject, str) and isinstance(obj, str):
            frame_links.setdefault(subject, []).append((obj, location))
        if relation == "rel:licenses_learning_contract" and isinstance(subject, str) and isinstance(obj, str):
            capability_contract_links.add((subject, obj))

    linked_frame_refs = {frame_ref for links in frame_links.values() for frame_ref, _ in links}

    for target_ref, links in sorted(frame_links.items()):
        if target_ref not in atom_kinds:
            issues.append(f"semantic frame target is missing: {target_ref}")
        if len(links) > 8:
            issues.append(f"semantic target {target_ref} exceeds frame profile bound 8")
        seen: set[str] = set()
        for frame_ref, location in links:
            if frame_ref in seen:
                issues.append(f"{location}: duplicate semantic frame link {target_ref}->{frame_ref}")
                continue
            seen.add(frame_ref)
            if atom_kinds.get(frame_ref) != "semantic_frame":
                issues.append(f"{location}: frame link object {frame_ref} is not semantic_frame")

    for ref, atom in sorted(atom_defs.items()):
        kind = atom_kinds[ref]
        metadata = _metadata(atom)
        frame = metadata.get("semantic_frame")
        contract = metadata.get("learning_contract")

        if kind == "semantic_frame":
            if not isinstance(frame, Mapping):
                issues.append(f"semantic frame {ref} lacks semantic_frame metadata")
                continue
            contribution = str(frame.get("contribution_kind") or "")
            if contribution not in _ALLOWED_CONTRIBUTIONS:
                issues.append(f"semantic frame {ref} has invalid contribution kind {contribution!r}")
            predicate = bool(frame.get("predicate", contribution == "predicate"))
            if predicate != (contribution == "predicate"):
                issues.append(f"semantic frame {ref} predicate flag contradicts contribution kind")
            _ref_list(frame.get("ports_provided", ()), label=f"{ref}.ports_provided", issues=issues, limit=_MAX_PORTS)
            _ref_list(frame.get("ports_required", ()), label=f"{ref}.ports_required", issues=issues, limit=_MAX_PORTS)
            score = frame.get("score", 0.0)
            if not isinstance(score, (int, float)) or not -4.0 <= float(score) <= 4.0:
                issues.append(f"semantic frame {ref} score is outside [-4,4]")
            operator_ref = str(frame.get("kernel_operator_ref") or "")
            if predicate and atom_kinds.get(operator_ref) != "operator":
                issues.append(f"semantic frame {ref} references invalid kernel operator {operator_ref!r}")
            if ref not in linked_frame_refs:
                issues.append(f"semantic frame {ref} is not linked to any semantic target")
            for target_ref, links in frame_links.items():
                if ref not in {frame_ref for frame_ref, _ in links}:
                    continue
                target_kind = atom_kinds.get(target_ref)
                expected_operator = _PREDICATE_OPERATOR_BY_TARGET_KIND.get(target_kind)
                if predicate and expected_operator and operator_ref != expected_operator:
                    issues.append(
                        f"semantic frame {ref} lowers {target_ref}:{target_kind} "
                        f"through {operator_ref!r}, expected {expected_operator}"
                    )
                if predicate and target_kind not in _PREDICATE_OPERATOR_BY_TARGET_KIND:
                    issues.append(
                        f"semantic frame {ref} cannot predicate target kind {target_kind!r}"
                    )
            roles = frame.get("roles", ())
            if not isinstance(roles, list):
                issues.append(f"semantic frame {ref}.roles must be a list")
                roles = []
            if len(roles) > _MAX_FRAME_ROLES:
                issues.append(f"semantic frame {ref} exceeds role bound {_MAX_FRAME_ROLES}")
            seen_roles: set[str] = set()
            for index, raw_role in enumerate(roles):
                label = f"semantic frame {ref}.roles[{index}]"
                if not isinstance(raw_role, Mapping):
                    issues.append(f"{label} must be an object")
                    continue
                role_ref = str(raw_role.get("role_ref") or "")
                if role_ref in seen_roles:
                    issues.append(f"semantic frame {ref} repeats role {role_ref}")
                seen_roles.add(role_ref)
                if atom_kinds.get(role_ref) != "role":
                    issues.append(f"{label} references non-role {role_ref!r}")
                if operator_ref and (operator_ref, role_ref) not in role_defs:
                    issues.append(f"{label} is not licensed by {operator_ref}")
                cardinality = str(raw_role.get("cardinality", "one"))
                if cardinality not in {"one", "many"}:
                    issues.append(f"{label} has unsupported cardinality {cardinality}")
                filler_kinds = raw_role.get("filler_kinds", ())
                if not isinstance(filler_kinds, list) or not filler_kinds or len(filler_kinds) > 8:
                    issues.append(f"{label}.filler_kinds must contain 1..8 kinds")
                else:
                    operator_spec = role_defs.get((operator_ref, role_ref), {})
                    expected = operator_spec.get("filler_kind")
                    for filler_kind in filler_kinds:
                        value = str(filler_kind)
                        if expected not in {None, "atom", "state_value"} and value not in {str(expected), "atom"}:
                            issues.append(f"{label} filler kind {value} conflicts with {operator_ref}:{role_ref}={expected}")
                _ref_list(raw_role.get("ports_required", ()), label=f"{label}.ports_required", issues=issues, limit=_MAX_PORTS)
                default_source = raw_role.get("default_source")
                if default_source not in {None, "speaker", "addressee", "self"}:
                    issues.append(f"{label} has unsupported default_source {default_source!r}")
                semantic_port = raw_role.get("semantic_port")
                if semantic_port is not None and not _PORT.fullmatch(str(semantic_port)):
                    issues.append(f"{label} has malformed semantic_port {semantic_port!r}")
                if isinstance(filler_kinds, list) and "app" in set(map(str, filler_kinds)) and not frame.get("proposition_taking"):
                    issues.append(f"{label} licenses app without proposition_taking")
            proposition_taking = bool(frame.get("proposition_taking", False))
            if proposition_taking and not any(
                isinstance(item, Mapping) and "app" in set(map(str, item.get("filler_kinds", ())))
                for item in roles
            ):
                issues.append(f"semantic frame {ref} is proposition_taking without an app-valued role")
            if frame.get("standalone_licensed"):
                if operator_ref != "op:event":
                    issues.append(f"semantic frame {ref} licenses standalone use outside op:event")
                if frame.get("default_force") not in {
                    "claim", "query", "directive", "description", "correction",
                    "retraction", "acknowledgment",
                }:
                    issues.append(f"semantic frame {ref} has invalid standalone default_force")
        elif frame is not None:
            issues.append(f"non-frame atom {ref} carries semantic_frame metadata")

        if contract is not None:
            if not isinstance(contract, Mapping):
                issues.append(f"learning contract {ref} metadata must be an object")
                continue
            if kind != "concept":
                issues.append(f"learning contract {ref} must be owned by a concept atom")
            goal_ref = str(contract.get("goal_ref") or "")
            capability_ref = str(contract.get("capability_ref") or "")
            operator_ref = str(contract.get("commit_operator_ref") or "")
            answer_ref = str(contract.get("answer_contract_ref") or "")
            label_ref = str(contract.get("label_type_ref") or "")
            expected = contract.get("expected_target_kinds", ())
            query_kinds = contract.get("licensed_query_kinds", ())
            for field, target, expected_kind in (
                ("goal_ref", goal_ref, "goal"),
                ("capability_ref", capability_ref, "capability"),
                ("commit_operator_ref", operator_ref, "operator"),
                ("answer_contract_ref", answer_ref, "concept"),
                ("label_type_ref", label_ref, "label_type"),
            ):
                if atom_kinds.get(target) != expected_kind:
                    issues.append(f"learning contract {ref}.{field} references {target!r}, expected {expected_kind}")
            if not isinstance(expected, list) or not 1 <= len(expected) <= _MAX_TARGET_KINDS:
                issues.append(f"learning contract {ref}.expected_target_kinds must contain 1..{_MAX_TARGET_KINDS}")
            elif len(expected) != len(set(map(str, expected))):
                issues.append(f"learning contract {ref}.expected_target_kinds contains duplicates")
            elif any(str(item) not in _ALLOWED_CONTRACT_TARGET_KINDS for item in expected):
                issues.append(f"learning contract {ref}.expected_target_kinds contains unsupported kinds")
            if not isinstance(query_kinds, list) or not 1 <= len(query_kinds) <= _MAX_QUERY_KINDS:
                issues.append(f"learning contract {ref}.licensed_query_kinds must contain 1..{_MAX_QUERY_KINDS}")
            elif any(not str(item) for item in query_kinds) or len(query_kinds) != len(set(map(str, query_kinds))):
                issues.append(f"learning contract {ref}.licensed_query_kinds is malformed")
            if (capability_ref, ref) not in capability_contract_links:
                issues.append(f"learning contract {ref} is not licensed by {capability_ref} through rel:licenses_learning_contract")

    for capability_ref, contract_ref in sorted(capability_contract_links):
        if atom_kinds.get(capability_ref) != "capability":
            issues.append(f"learning-license subject {capability_ref} is not a capability")
        contract = atom_defs.get(contract_ref)
        if not contract or not isinstance(_metadata(contract).get("learning_contract"), Mapping):
            issues.append(f"learning-license object {contract_ref} is not a learning contract")

    return tuple(dict.fromkeys(issues))
