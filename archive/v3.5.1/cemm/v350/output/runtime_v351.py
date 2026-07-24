"""Canonical in-process text emission and observed-output discourse commit for Phase 12."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from ..conversation.session_memory import CommonGroundEntry, OutputMemoryEntry
from ..grounding.model import SystemOutputAnchor
from ..learning.model import PinnedRecord
from .authorization_v351 import DisclosureAuthorizationGrantV351, DisclosureAuthorizationError
from ..orchestration import StageExecutionStatus, StageOutcome
from ..runtime_abi import EmissionObservationArtifact, artifact_ref
from ..response.csir_v351 import ResponseFamily
from ..schema.model import semantic_fingerprint


class InProcessTextEmissionEngineV351:
    """Text channel adapter used by Runtime.run_text after Stage-20 effect authorization.

    It has no implicit authority.  A concrete exact channel-contract PinnedRecord must be
    supplied from the boot/release authority set.  The engine only returns the bytes/text
    actually handed to the caller; Stage 20 owns disclosure/emission authorization.
    """

    RUNTIME_ABI = "v351"
    SERVICE_KIND = "in_process_text_emission"

    def __init__(
        self,
        *,
        channel_contract_pin: PinnedRecord | None = None,
        disclosure_authorization_grants: Iterable[DisclosureAuthorizationGrantV351] = (),
    ) -> None:
        self.channel_contract_pin = channel_contract_pin
        values = {}
        for grant in disclosure_authorization_grants:
            values[grant.grant_pin.key] = grant
        self.disclosure_authorization_grants = tuple(values[key] for key in sorted(values, key=str))

    def verification_channel_metadata(self, *, cycle, store):
        """Return the exact pinned channel contract for preservation policy only."""
        if self.channel_contract_pin is None:
            return None
        stored = store.get_record(
            self.channel_contract_pin.record_kind, self.channel_contract_pin.record_ref,
            self.channel_contract_pin.revision,
        )
        if stored is None or stored.record_fingerprint != self.channel_contract_pin.record_fingerprint:
            return None
        contract = stored.payload
        if str(getattr(contract, "channel_ref", cycle.channel_ref)) != cycle.channel_ref:
            return None
        return contract

    def authorize(
        self, *, cycle, capability, store, semantic_capabilities, selected_candidate,
        realization_proof, semantic_preservation, verification_policy, independent_roundtrip,
    ):
        del capability, semantic_capabilities, verification_policy, independent_roundtrip
        if not semantic_preservation.passed:
            return {
                "emission_gate_decision": "deny",
                "frontier_refs": ("frontier:emission:semantic-preservation-failed",),
            }
        if self.channel_contract_pin is None:
            return {
                "emission_gate_decision": "defer",
                "frontier_refs": ("frontier:emission:exact-channel-contract-required",),
            }
        if not self.disclosure_authorization_grants:
            # A transport/channel contract is not disclosure authority.  Keep these
            # governance dimensions split exactly as required by the architecture.
            return {
                "emission_gate_decision": "defer",
                "frontier_refs": ("frontier:emission:exact-disclosure-authorization-required",),
            }
        stored = store.get_record(
            self.channel_contract_pin.record_kind,
            self.channel_contract_pin.record_ref,
            self.channel_contract_pin.revision,
        )
        if stored is None or stored.record_fingerprint != self.channel_contract_pin.record_fingerprint:
            return {
                "emission_gate_decision": "deny",
                "frontier_refs": ("frontier:emission:channel-contract-stale",),
            }
        contract = stored.payload
        if not bool(getattr(contract, "active", False)):
            return {
                "emission_gate_decision": "deny",
                "frontier_refs": ("frontier:emission:channel-contract-inactive",),
            }
        if str(getattr(contract, "channel_ref", cycle.channel_ref)) != cycle.channel_ref:
            return {
                "emission_gate_decision": "deny",
                "frontier_refs": ("frontier:emission:channel-contract-mismatch",),
            }
        allowed_languages = tuple(getattr(contract, "allowed_language_tags", ()) or ())
        language = str(getattr(selected_candidate, "language_tag", "") or "")
        if allowed_languages and language not in allowed_languages:
            return {
                "emission_gate_decision": "deny",
                "frontier_refs": ("frontier:emission:language-not-allowed-by-channel",),
            }
        payload_bytes = len(str(getattr(selected_candidate, "surface", "")).encode("utf-8"))
        if payload_bytes > int(getattr(contract, "max_payload_bytes", 0) or 0):
            return {
                "emission_gate_decision": "deny",
                "frontier_refs": ("frontier:emission:payload-limit-exceeded",),
            }
        semantic_snapshot = cycle.artifacts.get("semantic_authority_snapshot_v351")
        if semantic_snapshot is None:
            return {
                "emission_gate_decision": "defer",
                "frontier_refs": ("frontier:emission:pinned-semantic-authority-required",),
            }
        matching = []
        invalid_reasons = []
        for grant in self.disclosure_authorization_grants:
            try:
                grant.validate_exact_authority(semantic_snapshot)
            except (DisclosureAuthorizationError, Exception) as exc:
                invalid_reasons.append(
                    "frontier:emission:disclosure-grant-invalid:" + str(getattr(grant.grant_pin, "ref", "unknown"))
                )
                continue
            allowed, reasons = grant.matches(cycle=cycle, selected_candidate=selected_candidate)
            if allowed:
                matching.append(grant)
            elif not reasons:
                invalid_reasons.append("frontier:emission:disclosure-grant-rejected")
        if len(matching) != 1:
            if len(matching) > 1:
                frontier = ("frontier:emission:ambiguous-disclosure-authorization",)
            elif invalid_reasons:
                frontier = tuple(sorted(set(invalid_reasons)))
            else:
                frontier = ("frontier:emission:no-disclosure-authorization-matches-scope",)
            return {"emission_gate_decision": "deny", "frontier_refs": frontier}
        grant = matching[0]
        pin_values = {(self.channel_contract_pin.key, self.channel_contract_pin.record_fingerprint): self.channel_contract_pin}
        for pin in grant.substrate_pins:
            disclosed = store.get_record(pin.record_kind, pin.record_ref, pin.revision)
            if disclosed is None or disclosed.record_fingerprint != pin.record_fingerprint:
                return {
                    "emission_gate_decision": "deny",
                    "frontier_refs": ("frontier:emission:disclosure-authorization-substrate-stale",),
                }
            pin_values[(pin.key, pin.record_fingerprint)] = pin
        pins = tuple(pin_values[key] for key in sorted(pin_values, key=str))
        idempotency = str(
            getattr(cycle.input_payload, "emission_idempotency_key", None)
            or artifact_ref("emission-idempotency", cycle.cycle_ref, selected_candidate.candidate_ref)
        )
        return {
            "emission_gate_decision": "allow",
            "disclosure_gate_passed": True,
            "authorization_pins": pins,
            "proof_refs": (
                realization_proof.proof_ref, semantic_preservation.assessment_ref,
                "disclosure-grant:" + grant.grant_pin.ref + "@" + str(grant.grant_pin.revision),
            ),
            "channel_contract_ref": self.channel_contract_pin.record_ref,
            "disclosure_authorization_ref": grant.grant_pin.ref,
            "disclosure_authorization_content_hash": grant.grant_pin.content_hash,
            "disclosure_authorization_grant": grant,
            "idempotency_identity": idempotency,
        }

    def emit(
        self, *, cycle, capability, store, effect_store, selected_candidate,
        realization_proof, semantic_preservation, authorization,
        effect_authorization_receipts,
    ):
        del capability, store, effect_store, semantic_preservation, authorization
        receipt_refs = tuple(
            item.receipt_ref for item in effect_authorization_receipts if getattr(item, "allowed", False)
        )
        if not receipt_refs:
            return {"frontier_refs": ("frontier:emission:effect-authorization-missing",)}
        observation = EmissionObservationArtifact(
            emission_ref=artifact_ref(
                "emission-observation", cycle.cycle_ref, selected_candidate.candidate_ref,
                tuple(sorted(receipt_refs)),
            ),
            surface_candidate_ref=selected_candidate.candidate_ref,
            output_text=selected_candidate.surface,
            evidence_refs=tuple(sorted(set((realization_proof.proof_ref, *receipt_refs)))),
            channel_ref=cycle.channel_ref,
        )
        return {"emission_observation": observation}


class OutputDiscourseCommitterV351:
    """Commit only observed output semantics to bounded session discourse state.

    Emission records what the system sent.  It does not assert recipient receipt,
    acceptance, agreement, or world truth.
    """

    RUNTIME_ABI = "v351"
    SERVICE_KIND = "output_discourse_committer"

    def __init__(self, session_memory) -> None:
        self.session_memory = session_memory

    def commit(self, *, cycle, capability, store, effect_store, semantic_capabilities):
        del capability, store, effect_store, semantic_capabilities
        observation = cycle.artifacts.get("emission_observation")
        decision = cycle.artifacts.get("response_decision")
        if observation is None or decision is None:
            return StageOutcome(
                StageExecutionStatus.PERFORMED,
                artifacts={"output_discourse_commit": (), "common_ground_proposal": ()},
            )
        if getattr(decision, "family", None) is ResponseFamily.NO_RESPONSE_REQUIRED:
            # An observed non-emission completes the stage contract but is not an output
            # occurrence and cannot create common ground.
            return StageOutcome(
                StageExecutionStatus.PERFORMED,
                artifacts={"output_discourse_commit": (), "common_ground_proposal": ()},
            )
        frame = cycle.artifacts.get("participant_frame")
        system_ref = str(getattr(frame, "system_ref", "") or "")
        participant_refs = tuple(sorted(set((*(cycle.audience_refs or ()), *((system_ref,) if system_ref else ())))))
        output = OutputMemoryEntry(
            output_ref=observation.emission_ref,
            response_ref=decision.decision_ref,
            graph=decision.graph,
            surface_candidate_ref=observation.surface_candidate_ref,
            context_ref=cycle.context_ref,
            permission_ref=cycle.permission_ref,
            audience_refs=participant_refs,
            evidence_refs=tuple(observation.evidence_refs),
            turn_index=self.session_memory.snapshot(cycle.context_ref, cycle.permission_ref).revision + 1,
            target_refs=tuple(decision.target_refs),
        )
        common = CommonGroundEntry(
            entry_ref=artifact_ref("common-ground-proposal", observation.emission_ref, decision.decision_ref),
            proposition_ref=decision.decision_ref,
            participant_refs=participant_refs,
            context_ref=cycle.context_ref,
            evidence_refs=tuple(observation.evidence_refs),
            grounded_by_emission=True,
        )
        receipt = self.session_memory.commit_output(
            cycle.context_ref, cycle.permission_ref, output=output, common_ground=common,
        )
        anchor = SystemOutputAnchor(
            output_ref=output.output_ref,
            context_ref=cycle.context_ref,
            content_referent_refs=tuple(
                sorted({term.identity_ref for term in decision.graph.terms if term.identity_ref})
            ),
            target_refs=tuple(decision.target_refs),
            turn_index=output.turn_index,
            evidence_refs=tuple(observation.evidence_refs),
        ) if any(term.identity_ref for term in decision.graph.terms) or decision.target_refs else None
        return StageOutcome(
            StageExecutionStatus.PERFORMED,
            artifacts={
                "output_discourse_commit": (receipt,),
                "common_ground_proposal": (common,),
                "system_output_anchor": (() if anchor is None else (anchor,)),
            },
        )


__all__ = ["InProcessTextEmissionEngineV351", "OutputDiscourseCommitterV351"]
