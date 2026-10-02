"""Bounded source authentication and reviewed reciprocal response selection.

The codecs establish identity, not trust. Live owners require the original
selected Program and CandidateVerificationReceipt and a current reader batch.
"""
from __future__ import annotations

from dataclasses import dataclass, fields

from .canonical import stable_ref
from .authority import LinkedAuthority
from .cycle import Orientation, SemanticMode
from .expressions import GroundedReference, RoleBinding, SemanticApplication, SemanticExpression, VerifiedMeaning, TranslationRow
from .forms import EvidencePacket, FormResolver
from .persistence import RevisionPin
from .programs import SemanticSwitchProgram
from .proposal_context import (ProposalContext, _participant_feature_target,
    _primitive_form_ref, _primitive_form_signature, _primitive_form_ports, _reference_roles)
from .r3_designations import AdmittedDesignationReader
from .role_schemas import CommunicativeRoleMatch, ReviewedRoleSchemaIndex, communicative_role_errors
from .verifier import CandidateVerificationReceipt


class _Codec:
    """Exact closed identity codec; deliberately independent of activated state."""
    _nested = {}
    _namespace = ""
    _ref = ""

    @classmethod
    def create(cls, **values):
        names = {f.name for f in fields(cls)} - {"abi_version", cls._ref}
        if set(values) != names:
            raise ValueError(f"{cls.__name__} fields mismatch")
        for name, kind in cls._nested.items():
            value = values[name]
            if type(value) is not kind or kind.from_dict(value.as_dict()) != value:
                raise ValueError(f"noncanonical {name}")
        return cls._from_canonical_children(values)

    @classmethod
    def _from_canonical_children(cls, values):
        """Construct identity after the caller's exact child decoding."""
        names = {f.name for f in fields(cls)} - {"abi_version", cls._ref}
        if set(values) != names:
            raise ValueError(f"{cls.__name__} fields mismatch")
        for name, value in values.items():
            kind = cls._nested.get(name)
            if kind is not None:
                if type(value) is not kind:
                    raise ValueError(f"noncanonical {name}")
            elif type(value) is not str or not value or len(value) > 512:
                raise ValueError(f"invalid bounded {name}")
        cls._shape(values)
        material = {"abi_version": 1, **{k: v.as_dict() if k in cls._nested else v for k, v in values.items()}}
        obj = object.__new__(cls)
        object.__setattr__(obj, "abi_version", 1)
        object.__setattr__(obj, cls._ref, stable_ref(cls._namespace, material))
        for name, value in values.items():
            object.__setattr__(obj, name, value)
        return obj

    def as_dict(self):
        return {f.name: getattr(self, f.name).as_dict() if f.name in self._nested
            else getattr(self, f.name) for f in fields(self)}

    @classmethod
    def from_dict(cls, row):
        # Lazy reuse avoids a module import cycle: response imports these
        # codecs, but decoding only occurs after owner modules are loaded.
        from .r3_response import _strict_response_wire
        _strict_response_wire(row)
        if type(row) is not dict or set(row) != {f.name for f in fields(cls)}:
            raise ValueError(f"{cls.__name__} fields mismatch")
        if type(row["abi_version"]) is not int or row["abi_version"] != 1:
            raise ValueError(f"unsupported {cls.__name__} ABI")
        rebuilt = cls._from_canonical_children({k: cls._nested[k].from_dict(v) if k in cls._nested else v
            for k, v in row.items() if k not in {"abi_version", cls._ref}})
        if rebuilt.as_dict() != row:
            raise ValueError(f"noncanonical {cls.__name__}")
        return rebuilt


@dataclass(frozen=True, init=False)
class CommunicativeSource(_Codec):
    abi_version: int
    source_ref: str
    evidence: EvidencePacket
    context: ProposalContext
    force: str
    construction_kind: str
    verified_meaning_ref: str
    expression_ref: str
    program_ref: str
    coverage_receipt_ref: str
    compilation_proof_ref: str
    verification_receipt_ref: str
    canonical_root_ref: str
    program_root_ref: str
    frame_slot_ref: str
    designation_slot_ref: str
    schema_ref: str
    index_ref: str
    match_ref: str
    frame_ref: str
    control_ref: str
    authority_generation: str
    authority_content_hash: str
    form_pack_hash: str
    actor_ref: str
    addressee_ref: str
    original_revision_pin: RevisionPin

    _namespace = "communicative_source"
    _ref = "source_ref"
    _nested = {"evidence": EvidencePacket, "context": ProposalContext, "original_revision_pin": RevisionPin}

    @staticmethod
    def _shape(values):
        if values["force"] not in {"claim", "performed"} or values["construction_kind"] != "direct_performed":
            raise ValueError("unsupported communicative source force/construction")


@dataclass(frozen=True, init=False)
class ResponseSelection(_Codec):
    abi_version: int
    selection_ref: str
    source_ref: str
    source_force: str
    source_root_ref: str
    situation_ref: str
    control_ref: str
    authority_generation: str
    authority_content_hash: str
    capability_ref: str
    capability_grant_ref: str
    actor_ref: str
    addressee_ref: str
    original_revision_pin: RevisionPin
    outgoing_expression: SemanticExpression

    _namespace = "response_selection"
    _ref = "selection_ref"
    _nested = {"original_revision_pin": RevisionPin, "outgoing_expression": SemanticExpression}

    @staticmethod
    def _shape(values):
        if values["source_force"] != "performed" or values["capability_ref"] != "cap:respond":
            raise ValueError("unsupported response selection force/capability")


def selected_owned_inputs(proposal, verification, meaning):
    """Select only actual retained proposal/verification owners, never decode copies."""
    candidates = tuple(c for c in proposal.candidates if c.program.program_ref == meaning.program_ref)
    receipts = tuple(r for r in verification.candidate_receipts
        if r.receipt_ref == meaning.verification_receipt_ref and r.program_ref == meaning.program_ref)
    if len(receipts) != 1:
        raise ValueError("selected verification receipt is not uniquely owned")
    receipt = receipts[0]
    candidates = tuple(c for c in candidates if c.candidate_ref == receipt.candidate_ref)
    if len(candidates) != 1:
        raise ValueError("selected program candidate lineage is not uniquely owned")
    return candidates[0].program, receipt


class CommunicativeOwner:
    def __init__(self, authority, resolver, index, reader):
        if (type(resolver) is not FormResolver or type(index) is not ReviewedRoleSchemaIndex
                or type(reader) is not AdmittedDesignationReader or reader.authority is not authority
                or index._activation_authority is not authority):
            raise TypeError("communicative owner requires exact activated input owners")
        index.validate_activation(authority)
        if resolver.form_pack_hash != index.form_pack_hash:
            raise ValueError("communicative activation form pack mismatch")
        self.authority, self.resolver, self.index, self.reader = authority, resolver, index, reader

    def _authenticate_form_evidence(self, evidence, context, orientation):
        lattice = self.resolver.resolve_evidence(evidence)
        if (lattice.lattice_ref != context.form_lattice_ref
                or tuple(u.unit_ref for u in lattice.units) != context.source_unit_refs
                or tuple((u.unit_ref, u.source_start, u.source_end) for u in lattice.units) != context.source_unit_spans):
            raise ValueError("communicative source geometry differs from evidence")
        expected = []
        participant_roles = {}
        for match in self.index.matches(context.designation_slots, context.contribution_slots, context.source_unit_spans):
            if type(match) is CommunicativeRoleMatch:
                for binding in match.bindings:
                    if binding.designation_slot_ref is None and binding.role in {"role:actor", "role:addressee"}:
                        participant_roles.setdefault(binding.source_unit_refs[0], []).append(binding.role)
        for unit in lattice.units:
            for category, value in unit.features:
                kind, constraints = _primitive_form_signature(category, value, unit.features)
                if kind is None:
                    continue
                target = _participant_feature_target(value, orientation, self.authority.atoms) if category == "participant" else None
                ports = _primitive_form_ports(kind, category)
                expected.append((unit.unit_ref, kind, constraints, target,
                    _primitive_form_ref(unit.unit_ref, category, value, target), ports, category))
        def authentic(c, row):
            unit, kind, constraints, target, ref, ports, category = row
            if (c.source_unit_refs != (unit,) or c.kind != kind or c.constraints != constraints
                    or c.target_ref != target or c.contribution_ref != ref or c.provenance_refs != (unit,)
                    or c.input_ports != ports[0] or c.literal_value is not None):
                return False
            if category == "participant":
                atom = self.authority.atoms.get(target)
                output = tuple(dict.fromkeys(participant_roles.get(unit, ()))) or (
                    ports[1] if atom is None else _reference_roles(atom.kind))
                return c.target_kind == (None if atom is None else atom.kind) and c.output_ports == output
            return c.target_kind is None and c.output_ports == ports[1]
        # Require every actual feature, even when its untrusted contribution has
        # been removed/retyped or the source was relabelled as noncritical.
        for row in expected:
            if not any(authentic(c, row) for c in context.contribution_slots):
                raise ValueError("communicative primitive evidence missing or retyped")
        primitive_categories = {row[2][0][0] for row in expected}
        for c in context.contribution_slots:
            if (c.contribution_ref.startswith("form_contribution:")
                    or c.constraints and c.constraints[0][0] in primitive_categories):
                if not any(authentic(c, row) for row in expected):
                    raise ValueError("communicative primitive evidence has a foreign owner")
        return lattice

    def source(self, *, evidence, context, meaning, orientation, program, receipt):
        """Only the initial reviewed direct construction can establish source force."""
        expression = meaning.expression
        if (not self.requires_source(expression, orientation)
                or any(r.critical for r in context.residual_evidence)):
            return None
        app = expression.applications[0]
        control = self.authority.communicative_control_for_target(app.predicate_ref)
        if type(program) is not SemanticSwitchProgram or type(receipt) is not CandidateVerificationReceipt:
            raise ValueError("communicative source requires original selected program/receipt")
        actions = tuple(a for a in program.actions if a.action_type == "instantiate_operator")
        if len(actions) != 1 or any(a.action_type in {"attach_scope", "bind_nested_application"} for a in program.actions):
            return None
        frame = context.frame(actions[0].arguments[1])
        matches = tuple(m for m in self.index.matches(context.designation_slots,
            context.contribution_slots, context.source_unit_spans) if type(m) is CommunicativeRoleMatch
            and m.predicate_slot_ref == frame.designation_slot_ref and set(m.provenance) <= set(frame.provenance_refs))
        if len(matches) != 1:
            return None
        match = matches[0]
        roles = {r.role_ref: r.filler for r in app.roles}
        if set(roles) != {control.actor_role_ref, control.addressee_role_ref} or any(type(v) is not GroundedReference for v in roles.values()):
            raise ValueError("communicative source roles differ from control")
        source = CommunicativeSource.create(evidence=evidence, context=context,
            force="claim" if match.source_actor_explicit else "performed",
            construction_kind=control.construction_kind,
            verified_meaning_ref=meaning.verified_meaning_ref, expression_ref=expression.expression_ref,
            program_ref=program.program_ref, coverage_receipt_ref=meaning.coverage_receipt_ref,
            compilation_proof_ref=meaning.compilation_proof_ref, verification_receipt_ref=receipt.receipt_ref,
            canonical_root_ref=app.application_ref, program_root_ref=actions[0].arguments[0],
            frame_slot_ref=frame.slot_ref, designation_slot_ref=frame.designation_slot_ref,
            schema_ref=match.schema_ref, index_ref=match.index_ref, match_ref=match.match_ref,
            frame_ref=match.frame_ref, control_ref=match.control_ref,
            authority_generation=self.authority.generation, authority_content_hash=self.authority.content_hash,
            form_pack_hash=evidence.form_pack_hash, actor_ref=roles[control.actor_role_ref].target_ref,
            addressee_ref=roles[control.addressee_role_ref].target_ref, original_revision_pin=meaning.revision_pin)
        self.authenticate_source(source, meaning=meaning, orientation=orientation, program=program, receipt=receipt)
        return source

    def requires_source(self, expression, orientation):
        """Conservative envelope requirement, never a grant of performed force."""
        if (orientation.mode is not SemanticMode.OBSERVE or len(expression.applications) != 1
                or expression.scope_operators or expression.expression_links or expression.binders
                or expression.query_projections or expression.unresolved_fillers):
            return False
        app = expression.applications[0]
        return (app.operator == "op:event" and not app.qualifiers
            and expression.root_refs == (app.application_ref,)
            and self.authority.communicative_control_for_target(app.predicate_ref) is not None)

    def authenticate_selected_witnesses(self, *, meaning, orientation, program, receipt):
        """Bind controlled content to actual selected witnesses even without a source."""
        for value, kind in ((meaning, VerifiedMeaning), (orientation, Orientation),
                (program, SemanticSwitchProgram), (receipt, CandidateVerificationReceipt)):
            if type(value) is not kind or kind.from_dict(value.as_dict()) != value:
                raise ValueError("communicative source requires exact canonical actual owners")
        proof, coverage, pin = receipt.compilation_proof, receipt.coverage_receipt, meaning.revision_pin
        if (not receipt.accepted or proof is None or not self.index.identity_is_current
                or self.index.authority_generation != pin.authority_generation
                or self.index.authority_generation != self.authority.generation
                or self.index.authority_content_hash != self.authority.content_hash
                or any(p != pin for p in (orientation.revision_pin, program.revision_pin,
                    coverage.revision_pin, proof.revision_pin))
                or any(ref != program.program_ref for ref in (meaning.program_ref, receipt.program_ref,
                    coverage.program_ref, proof.program_ref))
                or receipt.expression != meaning.expression or proof.expression_ref != meaning.expression.expression_ref
                or meaning.verification_receipt_ref != receipt.receipt_ref
                or meaning.coverage_receipt_ref != coverage.coverage_receipt_ref
                or meaning.compilation_proof_ref != proof.proof_ref or meaning.grounding_refs != proof.grounding_refs
                or program.orientation_ref != orientation.orientation_ref
                or program.proposal_context_ref != coverage.proposal_context_ref
                or program.proposal_context_ref != proof.proposal_context_ref
                or coverage.assignments != program.source_assignments
                or coverage.program_source_unit_refs != program.source_unit_refs):
            raise ValueError("communicative selected witness lineage/activation mismatch")
        roots = proof.root_translations
        assignments = tuple(TranslationRow(a.assignment_ref,
            "retained" if a.assignment_kind == "residual" else "translated",
            tuple(r for r in (a.target_action_ref or a.contribution_slot_ref, a.target_role_ref) if r is not None))
            for a in program.source_assignments)
        if (tuple(r.source_ref for r in roots) != program.root_refs
                or any(r.disposition != "translated" or len(r.target_refs) != 1 for r in roots)
                or len(roots) != len(meaning.expression.root_refs)
                or {r.target_refs[0] for r in roots} != set(meaning.expression.root_refs)
                or proof.assignment_translations != assignments):
            raise ValueError("communicative selected witness root/assignment lineage mismatch")

    def authenticate_source(self, source, *, meaning, orientation, program, receipt):
        if type(source) is not CommunicativeSource or CommunicativeSource.from_dict(source.as_dict()) != source:
            raise ValueError("communicative source requires exact canonical actual owners")
        self.authenticate_selected_witnesses(meaning=meaning, orientation=orientation, program=program, receipt=receipt)
        context, pin, index = source.context, source.original_revision_pin, self.index
        proof, coverage = receipt.compilation_proof, receipt.coverage_receipt
        if (source.authority_generation != self.authority.generation
                or source.authority_content_hash != self.authority.content_hash
                or source.form_pack_hash != self.resolver.form_pack_hash
                or source.index_ref != index.index_ref
                or context.revision_pin != pin or meaning.revision_pin != pin
                or source.program_ref != program.program_ref
                or source.verified_meaning_ref != meaning.verified_meaning_ref
                or source.expression_ref != meaning.expression.expression_ref
                or source.coverage_receipt_ref != coverage.coverage_receipt_ref
                or source.compilation_proof_ref != proof.proof_ref or meaning.compilation_proof_ref != proof.proof_ref
                or source.verification_receipt_ref != receipt.receipt_ref
                or meaning.verification_receipt_ref != receipt.receipt_ref
                or context.context_ref != program.proposal_context_ref
                or context.context_ref != coverage.proposal_context_ref or context.context_ref != proof.proposal_context_ref
                or context.orientation_ref != orientation.orientation_ref
                or context.evidence_packet_ref != source.evidence.packet_ref
                or orientation.source_text != source.evidence.source_text
                or coverage.source_unit_refs != context.source_unit_refs
                ):
            raise ValueError("communicative source lineage/activation mismatch")
        if (orientation.participant_frame not in orientation.participants
                or self.authority.atoms.get(orientation.participant_frame) is None
                or self.authority.atoms[orientation.participant_frame].kind != "participant"):
            raise ValueError("communicative speaker is not an actual orientation participant")
        lattice = self._authenticate_form_evidence(source.evidence, context, orientation)
        units = {u.unit_ref: u for u in lattice.units}
        errors = communicative_role_errors(context, program, index, authority=self.authority)
        if errors:
            raise ValueError("communicative role authentication: " + ",".join(errors))
        frame = context.frame(source.frame_slot_ref)
        matches = tuple(m for m in index.matches(context.designation_slots, context.contribution_slots,
            context.source_unit_spans) if type(m) is CommunicativeRoleMatch and m.match_ref == source.match_ref)
        if len(matches) != 1 or frame is None:
            raise ValueError("communicative source reviewed construction missing")
        match = matches[0]
        if ((source.index_ref, source.schema_ref, source.match_ref, source.control_ref) != match.provenance
                or source.designation_slot_ref != match.predicate_slot_ref or source.frame_ref != match.frame_ref
                or source.force != ("claim" if match.source_actor_explicit else "performed")):
            raise ValueError("communicative source force/construction mismatch")
        control = self.authority.communicative_control_for_target(match.target_ref)
        if control is None or control.control_ref != source.control_ref or source.construction_kind != control.construction_kind:
            raise ValueError("communicative source control missing")
        selected = tuple(context.designation(a.arguments[0]) for a in program.actions if a.action_type == "select_designation")
        with self.reader.batch(self.reader.stores.revision_pin()) as batch:
            for slot in selected:
                if slot is None:
                    raise ValueError("communicative selected designation missing")
                evidence = batch.authenticate_selected(slot.designation_fact_ref, slot.provenance_refs, pin)
                refs = slot.source_unit_refs
                rows = tuple(units[r] for r in refs)
                if not rows or any(a.source_end != b.source_start for a, b in zip(rows, rows[1:])):
                    raise ValueError("communicative selected designation is not contiguous")
                observed = source.evidence.source_text[rows[0].source_start:rows[-1].source_end].strip()
                if (evidence.designation.target_ref != slot.target_ref
                        or self.authority.atoms[slot.target_ref].kind != slot.target_kind
                        or evidence.designation.language != self.resolver._pack["language"]
                        or observed.casefold() != evidence.designation.surface.casefold()):
                    raise ValueError("communicative selected designation surface/kind mismatch")
        apps = tuple(a for a in program.actions if a.action_type == "instantiate_operator")
        expression = meaning.expression
        if (orientation.mode is not SemanticMode.OBSERVE or len(apps) != 1
                or len(expression.applications) != 1 or expression.root_refs != (source.canonical_root_ref,)
                or expression.scope_operators or expression.expression_links or expression.binders
                or expression.unresolved_fillers or expression.query_projections
                or any(r.critical for r in context.residual_evidence)
                or program.root_refs != (source.program_root_ref,)
                or apps[0].arguments != (source.program_root_ref, source.frame_slot_ref)
                or len(proof.root_translations) != 1
                or proof.root_translations[0].source_ref != source.program_root_ref
                or proof.root_translations[0].disposition != "translated"
                or proof.root_translations[0].target_refs != (source.canonical_root_ref,)):
            raise ValueError("communicative source is not the selected direct root")
        action_rows = []
        for action in program.actions:
            if action.action_type in {"select_context", "select_mode", "select_designation"}:
                disposition, targets = "validated", action.arguments
            elif action.action_type == "instantiate_operator":
                disposition, targets = "translated", (source.canonical_root_ref,)
            elif action.action_type in {"bind_reference", "bind_role"}:
                disposition, targets = "translated", (source.canonical_root_ref, action.arguments[1])
            elif action.action_type == "complete_program":
                disposition, targets = "translated", (expression.expression_ref,)
            else:
                raise ValueError("communicative unsupported direct translation")
            action_rows.append(TranslationRow(action.action_ref, disposition, targets))
        if proof.action_translations != tuple(action_rows):
            raise ValueError("communicative exact compilation translation mismatch")
        roles = []
        for a in program.actions:
            if a.action_type not in {"bind_reference", "bind_role"}:
                continue
            filler = context.reference(a.arguments[2]) if a.action_type == "bind_reference" else context.contribution(a.arguments[2])
            if filler is None:
                raise ValueError("communicative selected role missing")
            if a.action_type == "bind_reference" and filler.resolution_kind == "situated_participant":
                eligible = tuple(p for p in orientation.participants
                    if self.authority.atoms.get(p) is not None and self.authority.atoms[p].kind == "participant")
                others = tuple(p for p in eligible if p != orientation.participant_frame)
                expected = orientation.participant_frame if a.arguments[1] == control.actor_role_ref else (others[0] if others else None)
                if expected not in orientation.participants or filler.target_ref != expected:
                    raise ValueError("communicative default differs from actual orientation")
            roles.append(RoleBinding(a.arguments[1], GroundedReference(filler.target_ref)))
        expected = SemanticApplication("candidate:source", "op:event", match.target_ref, tuple(roles))
        incoming = SemanticExpression.create(applications=(expected,), root_refs=(expected.application_ref,))
        targets = {r.role_ref: r.filler.target_ref for r in incoming.applications[0].roles}
        if (incoming != expression or source.actor_ref != targets[control.actor_role_ref]
                or source.addressee_ref != targets[control.addressee_role_ref]):
            raise ValueError("communicative source exact graph/roles mismatch")
        return source

    def selection(self, source, situation, orientation):
        if source.force != "performed":
            return None, ()
        control = self.authority.communicative_control_for_target(situation.communicative_source.context
            .designation(source.designation_slot_ref).target_ref)
        blockers = []
        if source.addressee_ref != "participant:system":
            blockers.append("communicative:other_recipient")
        if (control.required_capability_ref not in orientation.capability_summary
                or not self.authority.capability_granted("participant:system", control.required_capability_ref)):
            blockers.append("communicative:capability_missing")
        if any(p not in orientation.participants or self.authority.atoms[p].kind != "participant"
                for p in ("participant:system", situation.speaker_ref)):
            blockers.append("communicative:participant_missing")
        signature = self.authority.by_event_signature(control.target_ref)
        phase = situation.session_phase_ref.removeprefix("session_phase:")
        if phase not in signature.valid_session_phases:
            blockers.append("communicative:phase_ineligible")
        if blockers:
            return None, tuple(blockers)
        app = SemanticApplication("candidate:reciprocal", "op:event", control.target_ref, (
            RoleBinding(control.actor_role_ref, GroundedReference("participant:system")),
            RoleBinding(control.addressee_role_ref, GroundedReference(situation.speaker_ref))))
        outgoing = SemanticExpression.create(applications=(app,), root_refs=(app.application_ref,))
        return ResponseSelection.create(source_ref=source.source_ref, source_force=source.force,
            source_root_ref=source.canonical_root_ref, situation_ref=situation.situation_ref,
            control_ref=control.control_ref, authority_generation=source.authority_generation,
            authority_content_hash=source.authority_content_hash, capability_ref=control.required_capability_ref,
            capability_grant_ref=stable_ref("capability_grant", ("participant:system", control.required_capability_ref,
                source.authority_generation, source.authority_content_hash)),
            actor_ref="participant:system", addressee_ref=situation.speaker_ref,
            original_revision_pin=source.original_revision_pin, outgoing_expression=outgoing), ()

    def authenticate(self, *, situation, meaning, orientation, program, receipt, selection=None, effect=None,
            evaluation=None, situation_inputs=None):
        source = situation.communicative_source
        if source is None:
            if selection is not None:
                raise ValueError("response selection requires actual source")
            return
        self.authenticate_source(source, meaning=meaning, orientation=orientation, program=program, receipt=receipt)
        if (situation.orientation_ref != orientation.orientation_ref or situation.proposal_context_ref != source.context.context_ref
                or situation.revision_pin != source.original_revision_pin
                or situation.speaker_ref != orientation.participant_frame
                or situation.capability_refs != orientation.capability_summary
                or situation.participant_refs != orientation.participants
                or situation.session_ref != orientation.session_ref or situation.turn_ref != orientation.turn_ref
                or situation.mode is not orientation.mode or situation.temporal_frame_ref != orientation.temporal_frame
                or situation.active_event_refs != orientation.event_refs
                or situation.permission_refs != orientation.permission_summary
                or situation.focus_refs != orientation.focus_refs or situation.obligation_refs != orientation.obligation_refs
                or situation.actor_ref is not None
                or situation.source_refs != tuple(dict.fromkeys((source.evidence.packet_ref,
                    *(item.item_ref for item in source.evidence.items))))
                or situation.evidence_kinds != tuple(dict.fromkeys(item.source for item in source.evidence.items))):
            raise ValueError("communicative situation differs from actual orientation")
        if effect is None:
            from .situation import SituationInputBundle, SituationContextVerifier
            if type(situation_inputs) is not SituationInputBundle:
                raise ValueError("initial communicative consequence requires original SituationInputBundle")
            SituationContextVerifier(self.authority).verify(situation, orientation, source.context,
                communicative_source=source, **situation_inputs.as_kwargs())
        else:
            self._authenticate_terminal(situation, source, evaluation, effect)
        expected, blockers = self.selection(source, situation, orientation)
        if selection != expected and (selection is not None or evaluation is not None):
            raise ValueError("response selection differs from authenticated derivation")
        if evaluation is not None:
            decision = evaluation.decision
            if source.force == "performed":
                if (decision.action.value != ("respond" if expected else "no_op")
                        or decision.blocker_refs != blockers or decision.selection_ref != (expected.selection_ref if expected else None)
                        or any((evaluation.claim_occurrences, evaluation.admission_decisions, evaluation.query_results,
                            evaluation.state_deltas, evaluation.state_query_results, evaluation.capability_evaluations,
                            evaluation.transition_evaluations, evaluation.effect_intents, evaluation.learning_drafts))):
                    raise ValueError("communicative consequence is not the exact nonclaim decision")

    def _authenticate_terminal(self, situation, source, evaluation, effect):
        from .r3_effects import NoEffectReceipt, R3EffectGateway
        from .r3_persistence import effect_journal_get, thaw_json
        if type(effect) is not NoEffectReceipt or evaluation is None:
            raise ValueError("communicative response requires actual read-only effect")
        stored = effect_journal_get(self.reader.stores, effect.idempotency_key)
        origin = stable_ref("effect_journal_origin", {
            "decision_ref": evaluation.decision.decision_ref, "kind": f"no_effect:{effect.reason.value}"})
        expected_request = {"journal_origin_ref": origin, "kind": "no_effect", "reason": effect.reason.value,
            "decision_ref": evaluation.decision.decision_ref, **R3EffectGateway._turn_payload(situation),
            "communicative_evaluation": evaluation.as_dict()}
        if (stored is None or not stored.entry.state.terminal
                or R3EffectGateway._terminal_receipt(stored) != effect
                or stored.entry.intent_ref != origin or stored.entry.decision_ref != evaluation.decision.decision_ref
                or effect.idempotency_key != R3EffectGateway._effect_key(evaluation.decision.decision_ref,
                    None, f"no_effect:{effect.reason.value}")
                or thaw_json(stored.entry.request_payload) != expected_request
                or effect.input_revision_pin != source.original_revision_pin):
            raise ValueError("communicative effect is not the persisted exact consequence")


def require_live_authority(owner, authority, revision_pin):
    """Live finalization/execution require an actual activated authority owner."""
    if type(owner) is CommunicativeOwner:
        if authority is not None and authority is not owner.authority:
            raise ValueError("live consequence activated authority owners differ")
        authority = owner.authority
    if type(authority) is not LinkedAuthority:
        raise ValueError("live consequence requires activated authority")
    if authority.generation != revision_pin.authority_generation:
        raise ValueError("live consequence authority generation differs from source pin")
    return authority


def authenticate_consequence(owner, *, situation, authority=None, **inputs):
    meaning = inputs.get("meaning")
    activated = owner.authority if type(owner) is CommunicativeOwner else authority
    # A controlled target only requires original witnesses. It never grants
    # performed force; the reviewed construction remains the sole force owner.
    if (type(activated) is LinkedAuthority and type(meaning) is VerifiedMeaning
            and any(activated.communicative_control_for_target(app.predicate_ref) is not None
                for app in meaning.expression.applications)):
        if type(owner) is not CommunicativeOwner:
            raise ValueError("controlled communicative target requires activated classification owner")
        if any(type(inputs.get(name)) is not kind for name, kind in (
                ("orientation", Orientation), ("program", SemanticSwitchProgram),
                ("receipt", CandidateVerificationReceipt))):
            raise ValueError("communicative source requires actual selected witnesses")
        if situation.communicative_source is None:
            owner.authenticate_selected_witnesses(meaning=meaning, orientation=inputs["orientation"],
                program=inputs["program"], receipt=inputs["receipt"])
            if owner.requires_source(meaning.expression, inputs["orientation"]):
                raise ValueError("actual selected bare controlled construction requires retained source")
    if situation.communicative_source is not None or inputs.get("selection") is not None:
        if type(owner) is not CommunicativeOwner:
            raise ValueError("communicative consequence requires activated owner and actual selected inputs")
        owner.authenticate(situation=situation, **inputs)
