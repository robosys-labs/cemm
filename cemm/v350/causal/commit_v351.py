"""Stage-13 actual-state commit for deterministic proof-bearing causal consequences."""
from __future__ import annotations

from ..learning.model import PinnedRecord
from ..schema.model import semantic_fingerprint
from ..storage.codec import encode_record, record_fingerprints
from ..storage.model import (
    AssignmentStatus, GraphPatch, PatchOperation, PatchOperationKind, RecordDependency,
    RecordKind, StateAssignment,
)
from .authority_v351 import CausalUseAuthorityError, require_exact_use
from .model_v351 import ContextSemantics, CausalSimulationResultV351


class CausalStateCommitterV351:
    """Commit only actual deterministic branch effects with exact mechanism authority.

    Prediction, intervention, counterfactual and planning simulations are never committed as
    world state. Stochastic alternatives remain beliefs/frontiers until independently observed.
    """

    @staticmethod
    def final_state_deltas(deltas):
        """Return one final delta per exact current-state key, preserving causal order.

        Intermediate same-variable deltas remain in the causal proof DAG; only the last
        `(time_step, branch order)` occurrence is eligible to materialize current state.
        """
        final_by_variable = {}
        for index, delta in enumerate(tuple(deltas)):
            key = (delta.holder_ref, delta.dimension_pin.key, delta.context_ref)
            rank = (int(delta.time_step), index)
            current = final_by_variable.get(key)
            if current is None or rank > current[0]:
                final_by_variable[key] = (rank, delta)
        return tuple(
            final_by_variable[key][1]
            for key in sorted(final_by_variable, key=lambda item: (item[0], item[1], item[2]))
        )

    def commit_actual(self, *, cycle, capability, store, effect_store):
        simulations = tuple(
            item for item in tuple(cycle.artifacts.get("causal_simulation_results", ()) or ())
            if isinstance(item, CausalSimulationResultV351)
            and item.context_semantics is ContextSemantics.ACTUAL
            and item.context_ref == cycle.context_ref
        )
        operations = []
        authorization_pins = {}
        proof_refs = set()
        evidence_refs = set()
        committed_delta_refs = []
        observed_delta_refs = []
        persisted_proof_refs = set()
        invalidated_assignment_keys = set()
        semantic_authority = cycle.artifacts.get("semantic_authority_snapshot_v351")

        for simulation in simulations:
            # Actual-world mutation requires one fully resolved deterministic branch.
            if len(simulation.branches) != 1:
                continue
            branch = simulation.branches[0]
            if (
                not branch.resolved
                or abs(branch.probability - 1.0) > 1e-12
                or simulation.unresolved_probability_mass > 1e-12
                or branch.frontier_refs
            ):
                continue
            observed_delta_refs.extend(delta.delta_ref for delta in branch.state_deltas)

            branch_proof = next(
                (proof for proof in simulation.causal_proofs if proof.proof_ref == branch.proof_ref),
                None,
            )
            if branch_proof is None:
                continue
            proof_by_delta = {
                step.delta_ref: (branch_proof, step)
                for step in branch_proof.steps
                if step.delta_ref
            }

            # A causal branch may update the same exact state variable several times. Those
            # intermediate changes remain in the durable proof DAG, but only the final value
            # is materialized as current world state. Otherwise one deterministic chain can
            # create multiple simultaneously ACTIVE assignments for an exclusive dimension.
            for delta in self.final_state_deltas(branch.state_deltas):
                if delta.context_ref != cycle.context_ref:
                    # ACTUAL semantics may never smuggle a different world/context into commit.
                    continue
                pair = proof_by_delta.get(delta.delta_ref)
                if pair is None:
                    continue
                proof, step = pair

                stored_mechanism = store.get_record(
                    RecordKind.TRANSITION_CONTRACT,
                    step.mechanism_pin.ref,
                    step.mechanism_pin.revision,
                )
                if stored_mechanism is None:
                    continue
                mechanism_payload = stored_mechanism.payload
                authority_pin = getattr(mechanism_payload, "authority_pin", None)
                executable = bool(getattr(mechanism_payload, "executable", False))
                if authority_pin is None or authority_pin.key != step.mechanism_pin.key or not executable:
                    continue
                try:
                    exact_use_pins = require_exact_use(
                        semantic_authority,
                        step.mechanism_pin,
                        operation="transition",
                        context_ref=cycle.context_ref,
                        permission_ref=cycle.permission_ref,
                    )
                except (CausalUseAuthorityError, TypeError, ValueError):
                    # Stage 13 independently revalidates the same exact per-use authority
                    # that Stage 12 was required to use. A forged/injected simulation cannot
                    # turn mere ACTIVE lifecycle into world-state mutation.
                    continue
                pinned = PinnedRecord(
                    RecordKind.TRANSITION_CONTRACT,
                    stored_mechanism.record_ref,
                    stored_mechanism.revision,
                    stored_mechanism.record_fingerprint,
                )
                authorization_pins[pinned.key] = pinned
                proof_refs.add(proof.proof_ref)
                proof_refs.update(pin.ref for pin in exact_use_pins)
                proof_refs.update(delta.proof_refs)
                evidence_refs.update(delta.evidence_refs)

                # Persist the exact causal proof DAG once. Every positive causal mechanism
                # in an actual proof must resolve to the same active, explicitly TRANSITION-
                # authorized authority revision that warranted the simulation.
                if proof.proof_ref not in persisted_proof_refs:
                    proof_dependencies = []
                    proof_authority_ok = True
                    for proof_step in proof.steps:
                        # Intervention-cut pseudo steps are impossible in ACTUAL context; a
                        # malformed actual proof containing one must fail closed here.
                        if proof_step.intervention_cut:
                            proof_authority_ok = False
                            break
                        exact = store.get_record(
                            RecordKind.TRANSITION_CONTRACT,
                            proof_step.mechanism_pin.ref,
                            proof_step.mechanism_pin.revision,
                        )
                        if exact is None:
                            proof_authority_ok = False
                            break
                        payload_pin = getattr(exact.payload, "authority_pin", None)
                        if (
                            payload_pin is None
                            or payload_pin.key != proof_step.mechanism_pin.key
                            or not bool(getattr(exact.payload, "executable", False))
                        ):
                            proof_authority_ok = False
                            break
                        try:
                            step_use_pins = require_exact_use(
                                semantic_authority,
                                proof_step.mechanism_pin,
                                operation="transition",
                                context_ref=cycle.context_ref,
                                permission_ref=cycle.permission_ref,
                            )
                        except (CausalUseAuthorityError, TypeError, ValueError):
                            proof_authority_ok = False
                            break
                        proof_refs.update(pin.ref for pin in step_use_pins)
                        proof_dependencies.append(RecordDependency(
                            RecordKind.TRANSITION_CONTRACT,
                            exact.record_ref,
                            exact.revision,
                            exact.record_fingerprint,
                            "causal_proof_mechanism_authority",
                        ))
                        exact_pin = PinnedRecord(
                            RecordKind.TRANSITION_CONTRACT,
                            exact.record_ref,
                            exact.revision,
                            exact.record_fingerprint,
                        )
                        authorization_pins[exact_pin.key] = exact_pin
                    if not proof_authority_ok:
                        continue

                    existing_proof = store.get_record(
                        RecordKind.TRANSITION_PROOF, proof.proof_ref, 1
                    )
                    proof_fp = record_fingerprints(RecordKind.TRANSITION_PROOF, proof)[1]
                    if existing_proof is not None and existing_proof.record_fingerprint != proof_fp:
                        raise ValueError("causal proof exact identity collision at Stage 13")
                    if existing_proof is None:
                        unique_dependencies = {
                            (
                                dep.record_kind,
                                dep.record_ref,
                                dep.revision,
                                dep.fingerprint,
                                dep.dependency_kind,
                            ): dep
                            for dep in proof_dependencies
                        }
                        operations.append(PatchOperation(
                            operation_ref="patch-operation:causal-proof:" + semantic_fingerprint(
                                "causal-proof-persist-v351", (proof.proof_ref, proof_fp), 20,
                            ),
                            operation_kind=PatchOperationKind.UPSERT,
                            record_kind=RecordKind.TRANSITION_PROOF,
                            target_ref=proof.proof_ref,
                            record_revision=1,
                            payload=encode_record(RecordKind.TRANSITION_PROOF, proof),
                            dependencies=tuple(
                                unique_dependencies[key]
                                for key in sorted(unique_dependencies, key=str)
                            ),
                            reason=(
                                "persist exact Phase-16 causal proof DAG for committed "
                                "actual consequence"
                            ),
                        ))
                    persisted_proof_refs.add(proof.proof_ref)

                # Invalidate every prior ACTIVE assignment for this exact current-state key.
                # The exact expected revision/fingerprint on INVALIDATE is the pre-state CAS
                # guard. Intermediate same-branch deltas are proof history, not current state.
                prior_assignments = []
                for stored in store.records(RecordKind.STATE_ASSIGNMENT):
                    item = stored.payload
                    if not isinstance(item, StateAssignment):
                        continue
                    if item.status != AssignmentStatus.ACTIVE:
                        continue
                    if (
                        item.holder_ref == delta.holder_ref
                        and item.dimension_ref == delta.dimension_pin.ref
                        and item.dimension_revision == delta.dimension_pin.revision
                        and item.context_ref == delta.context_ref
                    ):
                        prior_assignments.append(stored)
                for stored in prior_assignments:
                    invalidation_key = (
                        stored.record_kind,
                        stored.record_ref,
                        stored.revision,
                    )
                    if invalidation_key in invalidated_assignment_keys:
                        continue
                    invalidated_assignment_keys.add(invalidation_key)
                    operations.append(PatchOperation(
                        operation_ref="patch-operation:state-invalidate:" + semantic_fingerprint(
                            "state-invalidate-v351",
                            (delta.delta_ref, stored.record_ref, stored.revision),
                            20,
                        ),
                        operation_kind=PatchOperationKind.INVALIDATE,
                        record_kind=RecordKind.STATE_ASSIGNMENT,
                        target_ref=stored.record_ref,
                        record_revision=stored.revision,
                        expected_record_revision=stored.revision,
                        expected_record_fingerprint=stored.record_fingerprint,
                        reason=(
                            "supersede exact pre-state after deterministic authorized "
                            "causal transition"
                        ),
                    ))

                # CLEAR is a real final state transition: prior state is invalidated and no
                # replacement assignment is fabricated. The causal proof remains durable.
                if delta.new_value is None:
                    committed_delta_refs.append(delta.delta_ref)
                    continue

                assignment = StateAssignment(
                    assignment_ref="state-assignment:" + semantic_fingerprint(
                        "state-assignment-v351",
                        (
                            delta.holder_ref,
                            delta.dimension_pin.key,
                            delta.context_ref,
                            delta.new_value.value_ref,
                            delta.delta_ref,
                        ),
                        32,
                    ),
                    holder_ref=delta.holder_ref,
                    dimension_ref=delta.dimension_pin.ref,
                    dimension_revision=delta.dimension_pin.revision,
                    value_ref=(
                        delta.new_value.categorical_pin.ref
                        if delta.new_value.categorical_pin is not None
                        else delta.new_value.value_ref
                    ),
                    value_revision=(
                        delta.new_value.categorical_pin.revision
                        if delta.new_value.categorical_pin is not None
                        else 1
                    ),
                    status=AssignmentStatus.ACTIVE,
                    context_ref=delta.context_ref,
                    confidence=delta.confidence,
                    valid_from=delta.effective_time_ref,
                    evidence_refs=tuple(sorted(set(delta.evidence_refs))),
                    proof_refs=tuple(sorted(set((proof.proof_ref, *delta.proof_refs)))),
                    source_refs=(step.mechanism_pin.ref,),
                    value_document=delta.new_value.document(),
                )
                proof_fp = record_fingerprints(RecordKind.TRANSITION_PROOF, proof)[1]
                operations.append(PatchOperation(
                    operation_ref="patch-operation:state-commit:" + semantic_fingerprint(
                        "state-commit-v351", (delta.delta_ref, assignment.assignment_ref), 20,
                    ),
                    operation_kind=PatchOperationKind.UPSERT,
                    record_kind=RecordKind.STATE_ASSIGNMENT,
                    target_ref=assignment.assignment_ref,
                    record_revision=1,
                    payload=encode_record(RecordKind.STATE_ASSIGNMENT, assignment),
                    dependencies=(
                        RecordDependency(
                            RecordKind.TRANSITION_CONTRACT,
                            pinned.record_ref,
                            pinned.revision,
                            pinned.record_fingerprint,
                            "causal_mechanism_authority",
                        ),
                        RecordDependency(
                            RecordKind.TRANSITION_PROOF,
                            proof.proof_ref,
                            1,
                            proof_fp,
                            "causal_transition_proof",
                        ),
                    ),
                    reason=(
                        "materialize only the final deterministic actual-context state "
                        "for one exact causal variable"
                    ),
                ))
                committed_delta_refs.append(delta.delta_ref)

        if not operations:
            return (), (), ()
        expected_revision = int(effect_store.read_store.revision)
        patch = GraphPatch(
            patch_ref="graph-patch:phase15-actual-state:" + semantic_fingerprint(
                "phase15-actual-state-patch",
                (
                    cycle.cycle_ref,
                    capability.pass_ref,
                    expected_revision,
                    tuple(op.operation_ref for op in operations),
                ),
                24,
            ),
            context_ref=cycle.context_ref,
            scope_ref=f"state:{cycle.context_ref}",
            source_ref="source:phase15:causal-transition-proof",
            permission_ref=cycle.permission_ref,
            operations=tuple(operations),
            expected_store_revision=expected_revision,
            evidence_refs=tuple(sorted(evidence_refs)),
            validation_requirements=(
                "phase15_actual_context_only",
                "phase15_deterministic_branch_only",
                "phase15_exact_transition_use_authority",
                "phase15_prestate_cas",
                "phase15_final_state_per_exact_variable",
                "phase16_durable_causal_proof_dag",
            ),
            metadata={
                "phase": 15,
                "simulation_is_not_commit": False,
                "committed_delta_refs": tuple(sorted(set(committed_delta_refs))),
                "observed_causal_delta_refs": tuple(sorted(set(observed_delta_refs))),
            },
        )
        result, receipt = effect_store.authorize_and_apply_patch(
            patch,
            authorization_pins=tuple(authorization_pins.values()),
            proof_refs=tuple(sorted(proof_refs)),
            publishes_authority=False,
        )
        if not getattr(result, "committed", False):
            return (), ("frontier:commit:phase15-state-cas-conflict",), (receipt,)
        return (result,), (), (receipt,)


__all__=["CausalStateCommitterV351"]

class CompositeStage13CommitterV351:
    """Run Phase-14 learning/session commit, then Phase-15 actual causal state commit.

    The two commits remain separate authorized CAS transactions because they publish into
    different generation domains. A causal state commit is attempted only after the existing
    session/learning coordinator succeeds; hypothetical/interventional branches never enter it.
    """
    RUNTIME_ABI = "v351"
    SERVICE_KIND = "commit_coordinator"

    def __init__(self, session_memory) -> None:
        from ..learning.commit_v351 import Stage13LearningCommitterV351
        self.learning = Stage13LearningCommitterV351(session_memory)
        self.causal = CausalStateCommitterV351()

    def commit(self, *, cycle, capability, store, effect_store, semantic_capabilities):
        from ..orchestration import StageExecutionStatus, StageOutcome
        first = self.learning.commit(
            cycle=cycle, capability=capability, store=store, effect_store=effect_store,
            semantic_capabilities=semantic_capabilities,
        )
        if first.status is not StageExecutionStatus.PERFORMED:
            return first
        causal_receipts, causal_frontiers, causal_effect_receipts = self.causal.commit_actual(
            cycle=cycle, capability=capability, store=store, effect_store=effect_store,
        )
        artifacts = dict(first.artifacts)
        artifacts["commit_receipts"] = tuple((*tuple(artifacts.get("commit_receipts", ()) or ()), *causal_receipts))
        artifacts["_effect_authorization_receipts"] = tuple((
            *tuple(artifacts.get("_effect_authorization_receipts", ()) or ()),
            *causal_effect_receipts,
        ))
        artifacts["causal_state_commit_receipts"] = tuple(causal_receipts)
        if causal_receipts:
            artifacts["committed_read_generation"] = effect_store.read_store.current_read_generation()
        return StageOutcome(
            StageExecutionStatus.PERFORMED,
            artifacts=artifacts,
            frontier_refs=tuple(sorted(set((*first.frontier_refs, *causal_frontiers)))),
        )


__all__=["CausalStateCommitterV351", "CompositeStage13CommitterV351"]
