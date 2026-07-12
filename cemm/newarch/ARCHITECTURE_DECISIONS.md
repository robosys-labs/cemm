# CEMM v3.4 — Final Binding Architecture Decisions

## ADR-001: Replace fixed UOL atom ontology

**Decision:** The v3.4 canonical model uses semantic graph objects, schema records, and cognitive-control records. The v3.3 fixed atom list is legacy import format only.

**Reason:** The old list mixed referents, values, predication kinds, control drives, modality, permission, evidence, and self.

## ADR-002: Structural graph links only

**Decision:** Semantic relations are predications. Graph links only express structure.

**Reason:** Dual encoding of `causes`, `before`, `is_a`, and similar meanings creates duplicate authority and inconsistent query/effect behavior.

## ADR-003: Separate predication, proposition, context, and communicative use

**Decision:** Predication is reusable content; proposition adds truth context; communicative acts are predications over proposition content.

**Reason:** Query, negation, report, belief, modality, and hypothetical context are independent axes.

## ADR-004: Self is an ordinary stable referent

**Decision:** `self` uses the same semantic and epistemic substrate as other referents.

**Reason:** A special self truth system prevents normal querying, evidence, contradiction, and learning.

## ADR-005: One schema store

**Decision:** Predicate, action/process semantics, roles, states, entity kinds, capabilities, operations, constructions, lexemes, and realization schemas use one versioned store/resolver.

**Reason:** Parallel registries create inconsistent executable meaning. Operation schemas remain separate record kinds because execution metadata differs, but semantic preconditions/effects reference predicate schemas.

## ADR-006: No learning overlay

**Decision:** Provisional learning uses child versions of the canonical schema store.

**Reason:** Transaction isolation is required; a second resolver is not.

## ADR-007: Replay proves learning

**Decision:** A learned artifact is valid only when the ordinary pipeline successfully replays the blocked case and competency tests pass.

**Reason:** Administrative state change does not demonstrate operational learning.

## ADR-008: Four-state truth maintenance

**Decision:** Proposition support is `supported`, `refuted`, `both`, or `neither`; confidence is separate.

**Reason:** Absence is not falsity, and contradictory evidence must remain representable.

## ADR-009: Capability is derived live

**Decision:** Capability requires competence, implementation, health, channels, resources, permission, and context.

**Reason:** Static schema declarations cannot truthfully describe current ability.

## ADR-010: Goals are desired semantic conditions

**Decision:** Goals reference desired propositions/information states, not intent labels.

**Reason:** String goals cannot support planning, satisfaction, conflict, explanation, or learning.

## ADR-011: Predicted effects do not mutate state

**Decision:** Only observed/executed and reconciled effects may become actual-world mutations.

**Reason:** Interpretation and simulation must not become action.

## ADR-012: Critical commit precedes completion claims

**Decision:** Required facts/effects/schema writes commit before response content is selected.

**Reason:** The system must never report success from a planned or auxiliary operation.

## ADR-013: Output commit follows dispatch

**Decision:** Common ground and pending questions update only after actual output dispatch.

**Reason:** Intended text is not communication.

## ADR-014: Event-driven cognitive cycles

**Decision:** External/internal triggers create immutable cycles; scheduled wake events provide continuity.

**Reason:** This supports bounded cognition, reproducibility, concurrency, and no hidden busy loop.

## ADR-015: Language packs are reversible evidence/expression modules

**Decision:** Language packs propose meaning candidates and realize message plans; they never own truth or response content.

**Reason:** Language-specific rules must not recreate English phrase routing.

## ADR-016: Functional awareness uses workspace + self-model + continuity

**Decision:** The sentience simulation target is functional access through a bounded workspace connected to self, memory, goals, appraisal, action, and explanation.

**Reason:** A self-profile object alone is not awareness.


## ADR-14 — Structural executability is not epistemic admission

**Decision:** Definition closure and competence make a schema usable as structure; `EpistemicEvaluator` separately decides the contexts and operations in which its definition claims are admitted.

**Reason:** A false but compositional user theory must not become actual-world knowledge.

## ADR-15 — Provisional replaces narrow-scope self-certification

**Decision:** A schema with only definition-derived or same-lineage discrimination remains `provisional`, even at session/user scope. It may be used with explicit qualification but cannot support unqualified `understands` or actual-world inference.

## ADR-16 — Evidence independence is lineage-based

**Decision:** Evidence and competence cases carry derivation roots and independence clusters. Transformations of one source do not multiply independent support.

## ADR-17 — Recursive schemas require declared evaluation semantics

**Decision:** Recursive clusters are inverse, positive-monotone, stratified-defeasible, or unsupported. Joint activation is atomic and restricted to supported classes.

## ADR-18 — Scope and epistemic context are separate

**Decision:** Access/ownership scope never acts as an automatic truth-precedence ladder. Context-specific definitions coexist unless an explicit supersession/override is justified.

## ADR-19 — Field-level provenance is mandatory

**Decision:** Every learned schema field/pattern records how it was obtained. Hypotheses/defaults may guide learning but are never represented as assertions.

## ADR-20 — Effect authority is always live

**Decision:** Schema grounding can permit effect interpretation/prediction/proposal only. Operation authorization and critical commit re-evaluate live conditions.

## ADR-21 — Invalidation reaches derived cognition

**Decision:** Every derived semantic/control artifact carries supporting revision fingerprints and is retracted/staled when dependencies change.

## ADR-22 — Replay and activation are transactional

**Decision:** Replay is deduplicated and snapshot-pinned. Schema/cluster activation uses compare-and-swap against the exact assessed environment.

## ADR-23 — Correction, retraction, archival, and deletion differ

**Decision:** These operations have distinct records, permissions, and downstream effects. Reversible archival cannot satisfy privacy deletion.
