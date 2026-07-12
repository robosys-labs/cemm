# CEMM v3.4 — Final Integrated Kernel Folder Structure

```text
cemm/
├── kernel/
│   ├── __init__.py
│   │
│   ├── model/                         # immutable canonical records; stdlib only
│   │   ├── refs.py
│   │   ├── identity.py
│   │   ├── signal.py
│   │   ├── surface.py
│   │   ├── referent.py
│   │   ├── value.py
│   │   ├── role_binding.py
│   │   ├── predication.py
│   │   ├── proposition.py
│   │   ├── context_frame.py
│   │   ├── evidence.py
│   │   ├── structural_link.py
│   │   ├── semantic_graph.py
│   │   ├── workspace.py
│   │   ├── epistemic.py
│   │   ├── capability.py
│   │   ├── gap.py
│   │   ├── goal.py
│   │   ├── plan.py
│   │   ├── operation.py
│   │   ├── execution.py
│   │   ├── learning.py
│   │   ├── message.py
│   │   ├── mutation.py
│   │   ├── failure.py
│   │   └── trace.py
│   │
│   ├── schema/                        # sole executable semantic-schema authority
│   │   ├── store.py
│   │   ├── resolver.py
│   │   ├── envelope.py
│   │   ├── scope.py
│   │   ├── versioning.py
│   │   ├── validation.py             # grounding assessment only
│   │   ├── grounding_spec.py
│   │   ├── dependency.py             # typed dependency graph
│   │   ├── activation.py             # atomic CAS / cluster activation
│   │   ├── use_profile.py            # derived per-snapshot usability
│   │   ├── lexeme.py
│   │   ├── construction.py
│   │   ├── predicate.py
│   │   ├── role.py
│   │   ├── entity_kind.py
│   │   ├── state_dimension.py
│   │   ├── context.py
│   │   ├── operation.py
│   │   ├── capability.py
│   │   ├── realization.py
│   │   ├── policy.py
│   │   └── metalanguage.py
│   │
│   ├── cycle/                         # canonical event-driven cognitive state machine
│   │   ├── kernel.py                  # CognitiveKernel orchestrator
│   │   ├── cycle.py
│   │   ├── snapshot.py
│   │   ├── trigger.py
│   │   ├── scheduler.py
│   │   ├── checkpoint.py
│   │   ├── budgets.py
│   │   ├── authority.py
│   │   └── invariants.py
│   │
│   ├── understanding/                 # input meaning construction
│   │   ├── composer.py                # sole semantic composition authority
│   │   ├── candidate_graph.py
│   │   ├── predication_builder.py
│   │   ├── proposition_builder.py
│   │   ├── context_builder.py
│   │   ├── communicative_builder.py
│   │   ├── grounding.py               # sole role/referent grounding authority
│   │   ├── reference_resolution.py
│   │   ├── coreference.py
│   │   ├── temporal_grounding.py
│   │   ├── spatial_grounding.py
│   │   ├── context_resolution.py
│   │   ├── interpretation.py          # sole branch selector
│   │   └── legacy_import.py           # one-way v3.3 adapter; migration only
│   │
│   ├── world/                         # world-state and event semantics
│   │   ├── identity.py
│   │   ├── state_occupancy.py
│   │   ├── state_transition.py
│   │   ├── events.py
│   │   ├── temporal.py
│   │   ├── spatial.py
│   │   ├── causal.py
│   │   ├── simulation.py
│   │   └── prediction_error.py
│   │
│   ├── discourse/                     # participant-relative conversation model
│   │   ├── common_ground.py
│   │   ├── commitments.py
│   │   ├── obligations.py
│   │   ├── expected_evidence.py
│   │   ├── salience.py
│   │   ├── topic.py
│   │   └── repair.py
│   │
│   ├── memory/                        # read/retrieval/consolidation over shared records
│   │   ├── interfaces.py
│   │   ├── query_pattern.py
│   │   ├── retrieval.py               # sole semantic retrieval authority
│   │   ├── working_index.py
│   │   ├── discourse_index.py
│   │   ├── episodic_index.py
│   │   ├── semantic_index.py
│   │   ├── procedural_index.py
│   │   ├── schema_index.py
│   │   ├── consolidation.py
│   │   └── forgetting.py
│   │
│   ├── epistemics/                    # truth, contradiction, knowledge derivation
│   │   ├── evaluator.py               # sole epistemic authority
│   │   ├── truth_maintenance.py
│   │   ├── evidence_aggregation.py
│   │   ├── lineage.py                 # derivation/independence graph
│   │   ├── admissibility.py            # context-specific schema/fact use
│   │   ├── contradiction.py
│   │   ├── temporal_validity.py
│   │   ├── accessibility.py
│   │   ├── source_policy.py
│   │   ├── knowledge_derivation.py
│   │   └── explanation_graph.py
│   │
│   ├── self_model/                    # ordinary semantic introspection over self referent
│   │   ├── registry.py
│   │   ├── component_observer.py
│   │   ├── resource_observer.py
│   │   ├── channel_observer.py
│   │   ├── capability_evaluator.py    # sole capability authority
│   │   ├── competence_tracker.py
│   │   ├── limitation_deriver.py
│   │   └── projection.py              # cache/read model only
│   │
│   ├── workspace/                     # bounded global semantic workspace
│   │   ├── controller.py              # sole focus authority
│   │   ├── relevance.py
│   │   ├── novelty.py
│   │   ├── appraisal.py
│   │   ├── activation.py
│   │   └── decay.py
│   │
│   ├── gaps/                          # concrete blocked-competency detection
│   │   ├── detector.py
│   │   ├── classifier.py
│   │   ├── closure.py
│   │   └── probe_options.py
│   │
│   ├── learning/                      # recursive schema acquisition
│   │   ├── coordinator.py             # transaction lifecycle authority
│   │   ├── transaction.py
│   │   ├── hypothesis_factory.py
│   │   ├── expected_evidence.py
│   │   ├── lineage.py                  # derivation and independence graph
│   │   ├── assimilator.py
│   │   ├── provisional_revision.py
│   │   ├── replay.py
│   │   ├── replay_queue.py             # dedup/snapshot/idempotence
│   │   ├── grounding_frontier.py
│   │   ├── competence_harness.py       # sandboxed, non-mutating
│   │   ├── competency.py
│   │   ├── promotion.py
│   │   ├── correction.py
│   │   ├── retraction.py
│   │   └── rollback.py
│   │
│   ├── goals/                         # desired propositions and arbitration
│   │   ├── need_derivation.py
│   │   ├── discourse_derivation.py
│   │   ├── goal_factory.py
│   │   ├── arbiter.py                 # sole active-goal authority
│   │   ├── satisfaction.py
│   │   ├── conflicts.py
│   │   └── lifecycle.py
│   │
│   ├── planning/                      # operation selection and simulation
│   │   ├── planner.py                 # sole plan authority
│   │   ├── operator_catalog.py
│   │   ├── preconditions.py
│   │   ├── simulation.py
│   │   ├── causal_prediction.py
│   │   ├── temporal_ordering.py
│   │   ├── cost.py
│   │   ├── risk.py
│   │   └── selection.py
│   │
│   ├── execution/                     # authorization, execution, reconciliation
│   │   ├── authorizer.py              # sole permission/safety/capability gate
│   │   ├── executor.py
│   │   ├── cognitive.py
│   │   ├── communicative.py
│   │   ├── adapters.py
│   │   ├── ledger.py
│   │   ├── reconciliation.py
│   │   └── idempotency.py
│   │
│   ├── response/                      # language-neutral response content planning
│   │   ├── planner.py                 # sole public-content authority
│   │   ├── content_selection.py
│   │   ├── discourse_plan.py
│   │   ├── information_structure.py
│   │   ├── stance.py
│   │   ├── referring_expressions.py
│   │   ├── aggregation.py
│   │   ├── message_validation.py
│   │   └── provenance.py
│   │
│   ├── commit/                        # only persistent-mutation authority
│   │   ├── coordinator.py
│   │   ├── validator.py
│   │   ├── identity.py
│   │   ├── cardinality.py
│   │   ├── conflict.py
│   │   ├── optimistic_lock.py
│   │   ├── write_outcome.py
│   │   └── journal.py
│   │
│   ├── persistence/                   # interfaces + concrete stores
│   │   ├── interfaces.py
│   │   ├── semantic_store.py
│   │   ├── event_store.py
│   │   ├── schema_store.py
│   │   ├── discourse_store.py
│   │   ├── transaction_store.py
│   │   ├── projection_store.py
│   │   └── unit_of_work.py
│   │
│   ├── boot/                          # validated minimum cognitive closure
│   │   ├── entity_kinds.py
│   │   ├── roles.py
│   │   ├── predicates.py
│   │   ├── state_dimensions.py
│   │   ├── contexts.py
│   │   ├── cognitive_operations.py
│   │   ├── communicative_operations.py
│   │   ├── capability_schemas.py
│   │   ├── policy_schemas.py
│   │   ├── metalanguage.py
│   │   └── validation.py
│   │
│   └── diagnostics/
│       ├── cycle_trace.py
│       ├── semantic_trace.py
│       ├── grounding_trace.py
│       ├── epistemic_trace.py
│       ├── capability_trace.py
│       ├── planning_trace.py
│       ├── execution_trace.py
│       ├── learning_trace.py
│       ├── response_trace.py
│       └── invariant_report.py
│
├── language/                          # surface analysis and realization only
│   ├── interfaces.py
│   ├── stream.py
│   ├── detection.py
│   ├── packs/
│   │   ├── en/
│   │   │   ├── lexicon.*
│   │   │   ├── morphology.*
│   │   │   ├── constructions.*
│   │   │   ├── syntax.*
│   │   │   └── realization.*
│   │   └── <language>/
│   └── validation/
│       ├── graph_equivalence.py
│       └── round_trip.py
│
├── adapters/                          # environment/channel/tool boundary
│   ├── interfaces.py
│   ├── text/
│   ├── audio/
│   ├── sensors/
│   ├── tools/
│   └── effectors/
│
├── app/                               # dependency assembly; no semantic decisions
│   ├── runtime.py
│   ├── sessions.py
│   ├── scheduler.py
│   └── transports/
│
├── legacy/
│   └── v3_3/                          # isolated migration reference
│
└── tests/
    ├── architecture/
    ├── model/
    ├── schema/
    ├── understanding/
    ├── world/
    ├── discourse/
    ├── epistemics/
    ├── self_model/
    ├── workspace/
    ├── learning/
    ├── goals/
    ├── planning/
    ├── execution/
    ├── response/
    ├── commit/
    ├── multilingual/
    └── end_to_end/
```

## Import boundaries

```text
kernel/model       → standard library only
kernel/schema      → model
kernel engines     → model + schema + read-only interfaces
kernel/commit      → model + schema + writable persistence interfaces
kernel/persistence → model interfaces; no semantic decision logic
language           → public model/schema interfaces; never persistence
adapters           → signal/operation interfaces; never semantic stores
app                → dependency assembly only
legacy             → may import legacy; canonical kernel never imports legacy
```

## Forbidden dependency directions

- `model` imports no engine.
- `understanding` imports no commit or writable store.
- `response` imports no raw language analyzer or persistence implementation.
- `language` imports no planner, epistemic evaluator, or commit coordinator.
- `learning` cannot install a parallel resolver.
- `self_model` cannot maintain independent truth facts.
- `app` cannot contain query, grounding, capability, or response heuristics.

## Package-level authority tests

Architecture tests must fail if:

- more than one class registers for the same authority key;
- canonical kernel imports `legacy.v3_3`;
- a non-commit package imports writable persistence;
- language packs import runtime/commit modules;
- semantic relation edge enums reappear;
- `instruction_kind`, `answer_concept`, or `store_patch` becomes a semantic control enum;
- a response renderer imports raw user text for factual slot filling.


## Foundational reliability boundary

These additions are refinements inside existing packages, not new top-level cognitive stages:

- `schema/validation.py` derives structure; it cannot activate;
- `schema/activation.py` performs atomic lifecycle commit through the store;
- `epistemics/admissibility.py` decides context-specific belief/knowledge admission;
- `learning/lineage.py` tracks information ancestry;
- `learning/replay_queue.py` provides bounded idempotent replay;
- truth-maintenance invalidation reaches all derived artifacts through typed dependencies.
