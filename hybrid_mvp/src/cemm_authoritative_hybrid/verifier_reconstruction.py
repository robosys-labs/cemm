"""Independent R2 expression reconstruction for verification.

This module independently reconstructs the expected SemanticExpression
from a Program ABI 3, providing a separate code path from the compiler
to verify compilation correctness.  It mirrors the compiler's logic but
is implemented independently to catch compilation errors.
"""

from __future__ import annotations

from typing import Any

from .authority import LinkedAuthority
from .expressions import (
    ApplicationFiller,
    BoundVariable,
    ExpressionBounds,
    ExpressionLink,
    GroundedReference,
    QueryProjection,
    LiteralValue,
    RoleBinding,
    ScopeOperator,
    SemanticApplication,
    SemanticExpression,
    VariableBinder,
)
from .programs import PERSISTENT_OPERATORS
from .literal_codec import decode_literal_slot
from .proposal_context import UnresolvedDesignationFrame, _primitive_form_ref, _primitive_form_signature
from .canonical import stable_ref

_R2_EXPRESSION_ACTIONS = frozenset(
    {
        "select_context",
        "select_mode",
        "select_designation",
        "instantiate_operator",
        "bind_role",
        "bind_reference",
        "bind_nested_application",
        "attach_scope",
        "project_variable",
        "propose_transition",
        "complete_program",
    }
)


class _ReconstructState:
    __slots__ = (
        "role_bindings", "node_map", "scopes", "links", "binders",
        "grounding", "var_counter",
    )

    def __init__(self) -> None:
        self.role_bindings: dict[str, dict[str, RoleBinding]] = {}
        self.node_map: set[str] = set()
        self.scopes: list[ScopeOperator] = []
        self.links: list[ExpressionLink] = []
        self.binders: list[VariableBinder] = []
        self.grounding: set[str] = set()
        self.var_counter: int = 0


def _find_frame(program: Any, app_ref: str, context: Any) -> Any | None:
    for a in program.actions:
        if a.action_type == "instantiate_operator" and a.arguments[0] == app_ref:
            return context.frame(a.arguments[1])
    return None


def _designation_frame_is_exact(frame: Any) -> bool:
    if frame.operator_ref != "op:designation":
        return True
    derived_roles = dict(frame.derived_role_targets)
    licensed_roles = set(frame.required_roles)
    licensed_roles.update(frame.optional_roles)
    licensed_roles.update(derived_roles)
    return (
        frame.predicate_kind == "label_type"
        and frame.structural_role_ref == "role:label_type"
        and not frame.proposition_roles
        and licensed_roles
        == {"role:label_type", "role:surface", "role:target"}
        and derived_roles.get("role:label_type") == frame.predicate_target_ref
    )


def _node_children(program: Any) -> dict[str, tuple[str, ...]]:
    grouped: dict[str, list[str]] = {}
    for action in program.actions:
        if action.action_type == "bind_nested_application":
            if action.arguments[0] == "role":
                _, parent_ref, _role_ref, child_ref = action.arguments
                grouped.setdefault(parent_ref, []).append(child_ref)
            else:
                _, link_ref, _slot_ref, *operands = action.arguments
                grouped.setdefault(link_ref, []).extend(operands)
        elif action.action_type == "attach_scope":
            scope_ref, _slot_ref, operand_ref = action.arguments
            grouped.setdefault(scope_ref, []).append(operand_ref)
        elif action.action_type == "project_variable" and len(action.arguments) == 3:
            binder_ref, _slot_ref, body_ref = action.arguments
            grouped.setdefault(binder_ref, []).append(body_ref)
    return {key: tuple(value) for key, value in grouped.items()}


def _nominal_form_feature(context: Any, source: str, kind: str, category: str, value: str | None = None) -> bool:
    """Authenticate a single form-owned feature, independent of frame claims."""
    for row in context.contributions_for_source(source):
        if (row.source_unit_refs != (source,) or row.kind != kind
            or row.target_ref is not None or row.target_kind is not None
            or row.provenance_refs != (source,) or not row.constraints):
            continue
        key, feature = row.constraints[0]
        if key != category or (value is not None and feature != value):
            continue
        metadata = row.constraints[1:]
        if metadata and not (category == "determiner" and feature == "determiner"
            and metadata == (("construction_role", "query_target_article"),)):
            continue
        expected_kind, expected_constraints = _primitive_form_signature(key, feature, row.constraints)
        if expected_kind != kind or row.constraints != expected_constraints:
            continue
        if row.contribution_ref != _primitive_form_ref(source, key, feature):
            continue
        if category == "orthography" and (row.input_ports or row.output_ports):
            continue
        return True
    return False


def _nominal_whitespace(context: Any, source: str) -> bool:
    rows = context.contributions_for_source(source)
    return _nominal_form_feature(context, source, "discourse", "orthography", "whitespace") and all(
        row.kind == "discourse" and not row.input_ports and not row.output_ports
        for row in rows
    )


def _nominal_binder_position(frame: Any, context: Any) -> int | None:
    """Reconstruct the full binder→nominal interval from typed source units."""
    designation = context.designation(frame.designation_slot_ref)
    if (designation is None or designation.target_kind != "concept"
        or frame.predicate_kind != "concept"
        or frame.predicate_target_ref != designation.target_ref
        or frame.structural_role_ref != "role:class"
        or frame.required_roles != ("role:instance",)
        or frame.optional_roles or frame.proposition_roles
        or frame.derived_role_targets != (("role:class", designation.target_ref),)):
        return None
    positions = {source: index for index, source in enumerate(context.source_unit_refs)}
    nominal = set(designation.source_unit_refs)
    source = set(frame.source_unit_refs)
    extras = source - nominal
    binders = tuple(ref for ref in extras if _nominal_form_feature(context, ref, "binder", "binder", "copula"))
    if len(binders) != 1 or not nominal < source:
        return None
    binder = positions[binders[0]]
    start, end = min(positions[ref] for ref in nominal), max(positions[ref] for ref in nominal)
    if binder >= start or frame.source_unit_refs != tuple(sorted(source, key=positions.__getitem__)):
        return None
    owned = {binders[0], *nominal}
    determiner = polarity = False
    for ref in context.source_unit_refs[binder + 1:start]:
        if _nominal_whitespace(context, ref):
            continue
        if not polarity and not determiner and _nominal_form_feature(context, ref, "scope", "polarity"):
            polarity = True
        elif not determiner and _nominal_form_feature(context, ref, "qualifier", "determiner"):
            determiner = True
            owned.add(ref)
        else:
            return None
    if any(ref not in nominal and not _nominal_whitespace(context, ref)
           for ref in context.source_unit_refs[start:end + 1]):
        return None
    return binder if source == owned else None


def _nominal_instance_is_local(frame: Any, slot: Any, context: Any) -> bool:
    binder = _nominal_binder_position(frame, context)
    if binder is None or slot.target_kind not in {"entity", "participant", "concept"} or not slot.source_unit_refs:
        return False
    positions = {source: index for index, source in enumerate(context.source_unit_refs)}
    # Authenticate the entire referent span, not only its rightmost position.
    witnessed = False
    for designation in context.designation_slots:
        if (designation.target_ref != slot.target_ref or designation.target_kind != slot.target_kind
            or designation.slot_ref not in slot.provenance_refs):
            continue
        nominal = set(designation.source_unit_refs)
        supplied = set(slot.source_unit_refs)
        if supplied == nominal:
            witnessed = True
            break
        extra = supplied - nominal
        if not nominal < supplied or len(extra) != 1:
            continue
        determiner = next(iter(extra))
        first = min(positions[ref] for ref in nominal)
        before = positions[determiner]
        if (before < first and _nominal_form_feature(context, determiner, "qualifier", "determiner")
            and all(_nominal_whitespace(context, ref) for ref in context.source_unit_refs[before + 1:first])):
            witnessed = True
            break
    if not witnessed and len(slot.source_unit_refs) == 1:
        source = slot.source_unit_refs[0]
        witnessed = any(
            row.kind == "reference" and row.target_ref == slot.target_ref
            and row.target_kind == slot.target_kind and row.source_unit_refs == (source,)
            and row.provenance_refs == (source,) and len(row.constraints) == 1
            and row.constraints[0][0] == "participant"
            and row.contribution_ref == stable_ref("form_contribution", (source, *row.constraints[0], slot.target_ref))
            for row in context.contributions_for_source(source)
        )
    if not witnessed:
        return False
    end = max(positions[ref] for ref in slot.source_unit_refs)
    return end < binder and all(_nominal_whitespace(context, ref) for ref in context.source_unit_refs[end + 1:binder])


def _nominal_scope_is_local(program: Any, app_ref: str, frame: Any, context: Any) -> bool:
    binder = _nominal_binder_position(frame, context)
    if binder is None:
        return False
    positions = {source: index for index, source in enumerate(context.source_unit_refs)}
    designation = context.designation(frame.designation_slot_ref)
    start = min(positions[ref] for ref in designation.source_unit_refs)
    expected = {source for source in context.source_unit_refs[binder + 1:start]
                if _nominal_form_feature(context, source, "scope", "polarity")}
    attached = set()
    for action in program.actions:
        if action.action_type != "attach_scope":
            continue
        _, slot_ref, operand = action.arguments
        scope = context.scope(slot_ref)
        if scope is None or scope.operator_type != "scope:polarity":
            continue
        if app_ref not in _reachable_nodes(program, operand):
            continue
        if operand != app_ref or not set(scope.source_unit_refs) <= expected:
            return False
        attached.update(scope.source_unit_refs)
    return attached == expected


def _reachable_nodes(program: Any, body_ref: str) -> tuple[str, ...]:
    children = _node_children(program)
    result: list[str] = []
    stack = [body_ref]
    seen: set[str] = set()
    while stack:
        ref = stack.pop()
        if ref in seen:
            continue
        seen.add(ref)
        result.append(ref)
        stack.extend(reversed(children.get(ref, ())))
    return tuple(result)


def _resolve_variable_application(
    program: Any,
    context: Any,
    st: _ReconstructState,
    body_ref: str,
    slot: Any,
) -> str | None:
    frame_by_application = {
        action.arguments[0]: action.arguments[1]
        for action in program.actions
        if action.action_type == "instantiate_operator"
    }
    matches = tuple(
        ref
        for ref in _reachable_nodes(program, body_ref)
        if frame_by_application.get(ref) == slot.application_frame_ref
        and slot.role_ref not in st.role_bindings.get(ref, {})
    )
    return matches[0] if len(matches) == 1 else None


def _naming_role_is_local(frame: Any, slot: Any, role: str, context: Any) -> bool:
    """Reconstruct naming ownership independently of the proposal choice index."""
    naming = frame.predicate_kind == "event_type" and all(
        ref in frame.required_roles for ref in ("role:surface", "role:target")
    )
    if not naming and frame.operator_ref != "op:designation":
        return True
    teaching = tuple(value for predicate in context.contribution_slots
        if predicate.kind == "predicate" and predicate.target_ref == frame.predicate_target_ref
        and predicate.source_unit_refs == frame.source_unit_refs
        for key, value in predicate.constraints if key == "teaching_evidence_ref")
    if role == "role:surface":
        if naming:
            return getattr(slot, "kind", None) == "literal" and ("naming_frame_ref", frame.slot_ref) in slot.constraints
        if teaching:
            return (getattr(slot, "kind", None) == "literal" and slot.source_unit_refs == frame.source_unit_refs
                and any(("teaching_evidence_ref", ref) in slot.constraints for ref in teaching))
    if not naming or role != "role:target":
        return True
    form_features = {}
    for source in context.source_unit_refs:
        for evidence in context.contributions_for_source(source):
            if (evidence.source_unit_refs == (source,) and evidence.provenance_refs == (source,)
                and len(evidence.constraints) == 1):
                key, value = evidence.constraints[0]
                if evidence.contribution_ref == stable_ref("form_contribution", (source, key, value)):
                    form_features.setdefault(source, set()).add((key, value))
    marker_positions = []
    for literal in context.contribution_slots:
        if literal.kind != "literal" or ("naming_frame_ref", frame.slot_ref) not in literal.constraints:
            continue
        markers = [source for source in literal.source_unit_refs
            if ("discourse", "definition_marker") in form_features.get(source, ())]
        if len(markers) == 1:
            marker_positions.append(context.source_span(tuple(markers))[1])
    if not marker_positions:
        return False  # Missing form evidence never grants unrestricted targets.
    target_span = context.source_span(slot.source_unit_refs)
    if target_span is None:
        return False
    for marker_end in marker_positions:
        if target_span[0] < marker_end:
            continue
        if not any(marker_end <= start < target_span[1]
            and form_features.get(source, set()) - {("orthography", "whitespace")}
            for source, start, _ in context.source_unit_spans):
            return True
    return False


def _source_span(context: Any, source_refs: tuple[str, ...]) -> tuple[int, int] | None:
    """Read exact source geometry from real or semantic-only test contexts."""
    source_span = getattr(context, "source_span", None)
    if callable(source_span):
        return source_span(source_refs)
    spans = {
        source_ref: (start, end)
        for source_ref, start, end in getattr(context, "source_unit_spans", ())
    }
    selected = tuple(spans.get(source_ref) for source_ref in source_refs)
    if not selected or any(span is None for span in selected):
        return None
    return min(span[0] for span in selected), max(span[1] for span in selected)


def _report_regions(context: Any) -> tuple[tuple[str, int, int, int, int], ...]:
    """Independently reconstruct typed report clause geometry."""
    report_sources = tuple(
        row.source_unit_refs
        for row in context.contribution_slots
        if row.kind == "discourse"
        and ("discourse", "report") in row.constraints
        and row.source_unit_refs
    )
    sentence_boundaries = tuple(
        _source_span(context, row.source_unit_refs)
        for row in context.contribution_slots
        if row.kind == "discourse"
        and row.constraints == (("orthography", "sentence_boundary"),)
    )
    result: list[tuple[str, int, int, int, int]] = []
    for refs in report_sources:
        report_span = _source_span(context, refs)
        if report_span is None:
            continue
        clause_start = max(
            (
                span[1]
                for span in sentence_boundaries
                if span is not None and span[1] <= report_span[0]
            ),
            default=0,
        )
        content_end = min(
            (
                span[0]
                for span in sentence_boundaries
                if span is not None and span[0] >= report_span[1]
            ),
            default=max(end for _, _, end in context.source_unit_spans),
        )
        for frame in context.application_frames:
            frame_span = _source_span(context, frame.source_unit_refs)
            if (
                "role:content" in frame.proposition_roles
                and "role:actor" in frame.required_roles
                and frame_span is not None
                and report_span[0] <= frame_span[0]
                and frame_span[1] <= report_span[1]
            ):
                result.append(
                    (
                        frame.slot_ref,
                        clause_start,
                        report_span[0],
                        report_span[1],
                        content_end,
                    )
                )
    return tuple(result)


def _report_subtree_is_local(
    program: Any,
    context: Any,
    report_regions: tuple[tuple[str, int, int, int, int], ...],
    parent_frame_ref: str,
    child_ref: str,
) -> bool:
    regions = tuple(row for row in report_regions if row[0] == parent_frame_ref)
    if not regions:
        return True
    reachable = frozenset(_reachable_nodes(program, child_ref))
    frames = tuple(
        context.frame(action.arguments[1])
        for action in program.actions
        if action.action_type == "instantiate_operator"
        and action.arguments[0] in reachable
    )
    return bool(frames) and any(
        all(
            (span := _source_span(context, frame.source_unit_refs)) is not None
            and content_start <= span[0]
            and span[1] <= content_end
            for frame in frames
        )
        for _parent, _clause, _report_start, content_start, content_end in regions
    )


def _controlled_reported_speaker(
    frame: Any,
    reference: Any,
    parent_ref: str,
    context: Any,
    program: Any,
    authority: LinkedAuthority | None,
    local_refs_by_frame: dict[str, list[str]],
    reference_bindings: set[tuple[str, str, str]],
    nested_role_bindings: dict[tuple[str, str], list[str]],
) -> bool:
    if (
        authority is None
        or authority.generation != context.revision_pin.authority_generation
    ):
        return False
    parent = context.frame(parent_ref)
    if parent is None:
        return False
    control = authority.reported_role_inheritance_control(
        parent.predicate_target_ref,
        "role:content",
        frame.predicate_target_ref,
        "role:actor",
    )
    source_control = authority.source_attribution_control(
        parent.predicate_target_ref, "role:content"
    )
    if (
        control is None
        or source_control is None
        or control.source_attribution_control_ref != source_control.control_ref
    ):
        return False
    source_references = tuple(
        row
        for ref in reference.provenance_refs
        if (row := context.reference(ref)) is not None
        and row.source_unit_refs
    )
    if len(source_references) != 1:
        return False
    source = source_references[0]
    if (
        source.target_ref != reference.target_ref
        or source.target_kind != reference.target_kind
        or "role:actor" not in source.compatible_roles
        or parent_ref not in source.provenance_refs
        or reference.compatible_roles != ("role:actor",)
        or reference.score_q != source.score_q
        or reference.provenance_refs
        != (source.slot_ref, parent_ref, frame.slot_ref, control.control_ref)
    ):
        return False
    parent_locals = local_refs_by_frame.get(parent_ref, [])
    child_locals = local_refs_by_frame.get(frame.slot_ref, [])
    if len(parent_locals) != 1 or len(child_locals) != 1:
        return False
    parent_local = parent_locals[0]
    child_local = child_locals[0]
    if (
        (parent_local, source_control.source_role_ref, source.slot_ref)
        not in reference_bindings
        or not any(
            child_local in _reachable_nodes(program, content_root)
            for content_root in nested_role_bindings.get(
                (parent_local, source_control.content_role_ref), []
            )
        )
    ):
        return False
    return not any(
        row.slot_ref != reference.slot_ref
        and row.source_unit_refs
        and "role:actor" in row.compatible_roles
        and frame.slot_ref in row.provenance_refs
        for row in context.reference_slots
    )


def _report_reference_is_local(
    frame: Any,
    reference: Any,
    context: Any,
    report_regions: tuple[tuple[str, int, int, int, int], ...],
    program: Any,
    authority: LinkedAuthority | None,
    local_refs_by_frame: dict[str, list[str]],
    reference_bindings: set[tuple[str, str, str]],
    nested_role_bindings: dict[tuple[str, str], list[str]],
) -> bool:
    scoped = tuple(
        ref for ref in reference.provenance_refs
        if context.frame(ref) is not None
    )
    if scoped and frame.slot_ref not in scoped:
        return False
    span = _source_span(context, reference.source_unit_refs)
    if reference.source_unit_refs:
        frame_span = _source_span(context, frame.source_unit_refs)
        geometry = getattr(context, "source_unit_spans", ())
        if span is None or frame_span is None:
            return not geometry
        sentence_boundaries = tuple(
            _source_span(context, row.source_unit_refs)
            for row in context.contribution_slots
            if row.kind == "discourse"
            and row.constraints == (("orthography", "sentence_boundary"),)
        )
        clause_start = max(
            (
                value[1]
                for value in sentence_boundaries
                if value is not None and value[1] <= span[0]
            ),
            default=0,
        )
        clause_end = min(
            (
                value[0]
                for value in sentence_boundaries
                if value is not None and value[0] >= span[1]
            ),
            default=max(end for _, _, end in geometry),
        )
        if not (
            clause_start <= frame_span[0]
            and frame_span[1] <= clause_end
        ):
            return False
    for (
        parent_ref,
        clause_start,
        report_start,
        content_start,
        content_end,
    ) in report_regions:
        if frame.slot_ref == parent_ref:
            return (
                span is not None
                and clause_start <= span[0]
                and span[1] <= report_start
            )
        frame_span = _source_span(context, frame.source_unit_refs)
        if (
            frame_span is not None
            and content_start <= frame_span[0]
            and frame_span[1] <= content_end
        ):
            if reference.resolution_kind == "reported_speaker_coreference":
                return (
                    not reference.source_unit_refs
                    and parent_ref in reference.provenance_refs
                    and frame.slot_ref in reference.provenance_refs
                    and _controlled_reported_speaker(
                        frame,
                        reference,
                        parent_ref,
                        context,
                        program,
                        authority,
                        local_refs_by_frame,
                        reference_bindings,
                        nested_role_bindings,
                    )
                )
            return span is not None and content_start <= span[0] and span[1] <= content_end
    return reference.resolution_kind != "reported_speaker_coreference"


def _report_scope_is_local(
    program: Any,
    context: Any,
    report_regions: tuple[tuple[str, int, int, int, int], ...],
    slot: Any,
    target_ref: str,
) -> bool:
    span = _source_span(context, getattr(slot, "source_unit_refs", ()))
    if span is None:
        return True
    regions = tuple(
        row for row in report_regions
        if row[3] <= span[0] and span[1] <= row[4]
    )
    if not regions:
        return True
    reachable = frozenset(_reachable_nodes(program, target_ref))
    frames = tuple(
        context.frame(action.arguments[1])
        for action in program.actions
        if action.action_type == "instantiate_operator"
        and action.arguments[0] in reachable
    )
    return bool(frames) and any(
        all(
            (frame_span := _source_span(context, frame.source_unit_refs)) is not None
            and content_start <= frame_span[0]
            and frame_span[1] <= content_end
            for frame in frames
        )
        for _parent, _clause, _report_start, content_start, content_end in regions
    )


def reconstruct_expected_expression(
    program: Any,
    context: Any,
    *,
    authority: LinkedAuthority | None = None,
    role_schema_index: Any = None,
) -> SemanticExpression | None:
    """Independently reconstruct the expected expression from a program.

    Returns None if the program contains actions outside the admitted
    R2 subset or if reconstruction is not possible.
    """
    from .role_schemas import relation_query_errors, query_projection_errors, relation_declarative_errors, communicative_role_errors
    if (relation_query_errors(context, program, role_schema_index, authority=authority)
        or query_projection_errors(context, program, role_schema_index, authority=authority)
        or relation_declarative_errors(context, program, role_schema_index, authority=authority)
        or communicative_role_errors(context, program, role_schema_index, authority=authority)):
        return None
    actions = tuple(program.actions)
    if not actions or actions[-1].action_type != "complete_program":
        return None
    if any(a.action_type not in _R2_EXPRESSION_ACTIONS for a in actions):
        return None

    projections = tuple(a for a in actions if a.action_type == "project_variable" and len(a.arguments) == 2)
    if projections:
        action = projections[0]
        slot = context.query_projection(action.arguments[1])
        target = context.designation(slot.target_designation_slot_ref)
        # Independent graph construction, not compiler output or proof rows.
        try:
            return SemanticExpression.create(applications=(), root_refs=program.root_refs,
                query_projections=(QueryProjection(action.arguments[0], slot.requested_content, target.target_ref),))
        except (ValueError, TypeError):
            return None

    instantiations = tuple(
        a for a in actions if a.action_type == "instantiate_operator"
    )
    if not instantiations:
        return None

    st = _ReconstructState()
    report_regions = _report_regions(context)
    local_refs_by_frame: dict[str, list[str]] = {}
    reference_bindings: set[tuple[str, str, str]] = set()
    nested_role_bindings: dict[tuple[str, str], list[str]] = {}
    for action in actions:
        if action.action_type == "instantiate_operator":
            local_refs_by_frame.setdefault(action.arguments[1], []).append(
                action.arguments[0]
            )
        elif action.action_type == "bind_reference":
            reference_bindings.add(
                (action.arguments[0], action.arguments[1], action.arguments[2])
            )
        elif (
            action.action_type == "bind_nested_application"
            and action.arguments[0] == "role"
        ):
            nested_role_bindings.setdefault(
                (action.arguments[1], action.arguments[2]), []
            ).append(action.arguments[3])

    # Collect grounding from designations
    for a in actions:
        if a.action_type != "select_designation":
            continue
        slot = context.designation(a.arguments[0])
        if slot is None:
            return None
        st.grounding.update({slot.slot_ref, slot.target_ref, slot.designation_fact_ref, *slot.provenance_refs})

    # Collect applications and derived role targets
    for a in instantiations:
        app_ref, frame_slot_ref = a.arguments
        frame = context.frame(frame_slot_ref)
        if frame is None or frame.operator_ref not in PERSISTENT_OPERATORS:
            return None
        if not _designation_frame_is_exact(frame):
            return None
        if type(frame) is UnresolvedDesignationFrame:
            surface = context.contribution(frame.literal_contribution_slot_ref)
            query = context.contribution(frame.query_binder_slot_ref)
            if (a.source_unit_refs != () or frame.label_type_ref != "label:lexical"
                or frame.label_type_ref not in frame.provenance_refs
                or surface is None or surface.kind != "literal" or surface.target_ref is not None
                or surface.source_unit_refs != frame.source_unit_refs
                or query is None or query.kind != "binder"):
                return None
            expected_provenance = (frame.construction_ref, context.form_lattice_ref)
            if surface.provenance_refs != expected_provenance or query.provenance_refs != expected_provenance:
                return None
            if query.constraints != (("binder", "explicit_lexical_target_query"),) or len(query.source_unit_refs) != 2:
                return None
            original = tuple(row for row in context.contribution_slots if len(row.source_unit_refs) == 1)
            wh = tuple(row.source_unit_refs[0] for row in original if row.kind == "open_variable" and ("interrogative", "content") in row.constraints and ("query", "query") in row.constraints)
            if len(wh) != 1:
                return None
            for ref, feature in zip(query.source_unit_refs, ("lexical_query_auxiliary", "lexical_query_terminal"), strict=True):
                if not any(row.source_unit_refs == (ref,) and ("construction_role", feature) in row.constraints for row in original):
                    return None
            whitespace = {row.source_unit_refs[0] for row in original if row.constraints == (("orthography", "whitespace"),)}
            punctuation = {row.source_unit_refs[0] for row in original if ("discourse", "question") in row.constraints}
            significant = tuple(ref for ref in context.source_unit_refs if ref not in whitespace)
            if significant and significant[-1] in punctuation:
                significant = significant[:-1]
            literal_sources = tuple(ref for ref in surface.source_unit_refs if ref not in whitespace)
            if significant != (wh[0], query.source_unit_refs[0], *literal_sources, query.source_unit_refs[1]):
                return None
        if frame.operator_ref == "op:type" and _nominal_binder_position(frame, context) is None:
            return None
        st.grounding.add(frame.predicate_target_ref)
        st.grounding.update(t for _, t in frame.derived_role_targets)
        st.role_bindings[app_ref] = {
            role: RoleBinding(role, GroundedReference(target))
            for role, target in frame.derived_role_targets
        }
        st.node_map.add(app_ref)

    # Collect role/reference bindings
    for a in actions:
        if a.action_type not in {"bind_role", "bind_reference"}:
            continue
        app_ref, role_ref, slot_ref = a.arguments
        if app_ref not in st.role_bindings:
            return None
        frame = _find_frame(program, app_ref, context)
        if frame is None:
            return None
        legal = set(frame.required_roles) | set(frame.optional_roles)
        if role_ref not in legal or role_ref in st.role_bindings[app_ref]:
            return None
        if a.action_type == "bind_role":
            if type(frame) is UnresolvedDesignationFrame and (role_ref != "role:surface" or slot_ref != frame.literal_contribution_slot_ref):
                return None
            slot = context.contribution(slot_ref)
            if slot is None or role_ref not in slot.output_ports:
                return None
            if not _naming_role_is_local(frame, slot, role_ref, context):
                return None
            if role_ref == "role:surface" and ("naming_frame_ref" in dict(slot.constraints)
                or "teaching_evidence_ref" in dict(slot.constraints)) and a.source_unit_refs != slot.source_unit_refs:
                return None
            if type(frame) is UnresolvedDesignationFrame and a.source_unit_refs != slot.source_unit_refs:
                return None
            if frame.operator_ref == "op:type" and not _nominal_instance_is_local(frame, slot, context):
                return None
            if slot.target_ref is not None:
                filler: Any = GroundedReference(slot.target_ref)
                st.grounding.add(slot.target_ref)
            elif slot.literal_value is not None:
                literal_kind, literal_value = decode_literal_slot(slot)
                filler = LiteralValue(literal_kind, literal_value)
            else:
                return None
            st.grounding.update(slot.provenance_refs)
        else:
            if type(frame) is UnresolvedDesignationFrame:
                return None
            slot = context.reference(slot_ref)
            if slot is None or role_ref not in slot.compatible_roles:
                return None
            if not _report_reference_is_local(
                frame,
                slot,
                context,
                report_regions,
                program,
                authority,
                local_refs_by_frame,
                reference_bindings,
                nested_role_bindings,
            ):
                return None
            if role_ref == "role:surface" and frame.predicate_kind == "event_type" and {"role:surface", "role:target"} <= set(frame.required_roles):
                return None
            if not _naming_role_is_local(frame, slot, role_ref, context):
                return None
            if frame.operator_ref == "op:type" and not _nominal_instance_is_local(frame, slot, context):
                return None
            filler = GroundedReference(slot.target_ref)
            st.grounding.update({slot.target_ref, *slot.provenance_refs})
        st.role_bindings[app_ref][role_ref] = RoleBinding(role_ref, filler)

    # Materialize scopes before proposition binding because a scoped child is
    # itself the exact proposition node placed in the parent's content role.
    for a in actions:
        if a.action_type != "attach_scope":
            continue
        scope_ref, slot_ref, target_ref = a.arguments
        slot = context.scope(slot_ref)
        if slot is None or target_ref not in st.node_map:
            return None
        if not _report_scope_is_local(
            program, context, report_regions, slot, target_ref
        ):
            return None
        st.scopes.append(ScopeOperator(scope_ref, slot.operator_type, slot.value_ref, target_ref))
        st.node_map.add(scope_ref)
        st.grounding.add(slot.value_ref)

    # Collect nested role bindings (proposition roles)
    for a in actions:
        if a.action_type != "bind_nested_application" or not a.arguments or a.arguments[0] != "role":
            continue
        _, app_ref, role_ref, nested_ref = a.arguments
        if app_ref not in st.role_bindings or nested_ref not in st.node_map:
            return None
        frame = _find_frame(program, app_ref, context)
        if frame is None or role_ref not in frame.proposition_roles:
            return None
        if not _report_subtree_is_local(
            program, context, report_regions, frame.slot_ref, nested_ref
        ):
            return None
        if role_ref in st.role_bindings[app_ref]:
            return None
        st.role_bindings[app_ref][role_ref] = RoleBinding(role_ref, ApplicationFiller(nested_ref))

    # Collect expression links
    for a in actions:
        if a.action_type != "bind_nested_application" or not a.arguments or a.arguments[0] != "link":
            continue
        _, link_ref, slot_ref, *operands = a.arguments
        slot = context.expression_link(slot_ref)
        if slot is None:
            return None
        if any(op not in st.node_map for op in operands):
            return None
        st.links.append(ExpressionLink(link_ref, slot.link_type, tuple(operands)))
        st.node_map.add(link_ref)

    # Collect variable binders
    for a in actions:
        if a.action_type != "project_variable":
            continue
        binder_ref, slot_ref, target_ref = a.arguments
        slot = context.variable(slot_ref)
        if slot is None or target_ref not in st.node_map:
            return None
        var_ref = f"?v{st.var_counter}"
        st.var_counter += 1
        st.binders.append(VariableBinder(binder_ref, var_ref, target_ref))
        st.node_map.add(binder_ref)
        owner_ref = _resolve_variable_application(
            program, context, st, target_ref, slot
        )
        if owner_ref is None:
            return None
        role_ref = slot.role_ref
        frame = context.frame(slot.application_frame_ref)
        if type(frame) is UnresolvedDesignationFrame:
            evidence = context.contribution(frame.query_binder_slot_ref)
            qualifying_queries = tuple(
                row
                for row in context.contribution_slots
                if row.kind == "open_variable"
                and len(row.source_unit_refs) == 1
                and ("query", "query") in row.constraints
                and ("interrogative", "content") in row.constraints
            )
            interrogative_sources = (
                set(slot.source_unit_refs) - set(evidence.source_unit_refs)
                if evidence is not None
                else set()
            )
            if (evidence is None or not set(evidence.source_unit_refs) < set(slot.source_unit_refs)
                or len(qualifying_queries) != 1
                or set(qualifying_queries[0].source_unit_refs) != interrogative_sources
                or role_ref != "role:target" or slot.construction_ref != frame.construction_ref
                or a.source_unit_refs != slot.source_unit_refs):
                return None
            assigned = {row.source_unit_ref: row.contribution_slot_ref for row in program.source_assignments}
            if any(assigned.get(ref) != evidence.slot_ref for ref in evidence.source_unit_refs):
                return None
            query = qualifying_queries[0]
            if assigned.get(query.source_unit_refs[0]) != query.slot_ref:
                return None
        st.role_bindings[owner_ref][role_ref] = RoleBinding(
            role_ref, BoundVariable(var_ref)
        )

    # Build applications
    applications: list[SemanticApplication] = []
    for a in instantiations:
        app_ref, frame_slot_ref = a.arguments
        frame = context.frame(frame_slot_ref)
        if frame is None:
            return None
        if frame.operator_ref == "op:type" and not _nominal_scope_is_local(program, app_ref, frame, context):
            return None
        bindings = st.role_bindings.get(app_ref, {})
        if any(r not in bindings for r in frame.required_roles):
            return None
        prop_roles = set(frame.proposition_roles)
        # Include ALL role bindings, including proposition-valued roles
        # which carry ApplicationFiller fillers.
        roles = tuple(bindings[r] for r in sorted(bindings))
        if not roles:
            return None
        applications.append(SemanticApplication(app_ref, frame.operator_ref, frame.predicate_target_ref, roles))

    # Validate roots
    for root_ref in program.root_refs:
        if root_ref not in st.node_map:
            return None

    try:
        return SemanticExpression.create(
            applications=applications,
            root_refs=program.root_refs,
            scope_operators=st.scopes,
            expression_links=st.links,
            binders=st.binders,
            bounds=ExpressionBounds(),
        )
    except (ValueError, TypeError):
        return None
