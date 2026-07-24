# CEMM v3.5.1 — Phases 13–14 Implementation / Deep Fix Report

**Patch baseline:** `0dc1d64b78d0f1b620b224bdb74265e8b85763c6` (post-Phase-12 `main`)

## 1. Scope and governing contract

This bundle implements the Phase-13 typed recurrent semantic dynamics and the Phase-14
continuous-learning/promotion runtime against the already-applied Phase-12 runtime. It is
anchored to the revised `ARCHITECTURE.md`, `CEMM_CORE_MATHS.md`, `CORE_ISSUES.md`,
`CORE_LOOP.md`, `RUNTIME_PLAN.md`, `AGENTS.md`, `ISSUES_TO_AVOID.md`, and
`IMPLEMENTATION_PLAN.md`.

The implementation preserves these non-negotiable laws:

- CSIR remains the single semantic brain. Dynamic activation is cycle-local inference state,
  never a second representation or source of semantic identity.
- Hard constraints and exact authority prune before soft recurrent ranking. Scores cannot
  manufacture identity, type compatibility, missing fillers, permissions, or semantic truth.
- Posterior competition is over semantic equivalence classes, not parse/proof derivations.
- Budget exhaustion, oscillation and unresolved variables produce partial cognition/frontiers;
  they never become fabricated certainty.
- Stage 11 performs prediction-error classification and candidate preparation only.
- Stage 13 persists candidate/evidence/package DAGs only. Candidate/provisional revisions
  remain audit-domain learning state and do not publish semantic authority.
- Competence, review and activation authorization are independent gates. Promotion happens
  post-pass/maintenance, publishes a new immutable authority generation, and requires
  restart/next-cycle activation.
- No phrase-specific, English-specific, concept-specific, subject/object→semantic-role, or
  unknown-word→noun learning shortcut is introduced.

## 2. Phase 13 — canonical typed recurrent semantic dynamics

### 2.1 Contracts implemented

`cemm/v350/dynamics/model_v351.py` adds:

- `SemanticActivationNode`
- `TypedMessageEdge`
- `HardConstraintMask`
- `CompetitionGroup`
- `DynamicsParameterSet`
- `IterationActivationSummary`
- typed convergence status
- exact coverage for all 12 required message families:
  lexical, construction, port/role, type, identity, scope, time/aspect, context, state,
  causal expectation, discourse, multimodal.

Dynamic nodes preserve evidence lineage and derivation lineage separately. A repeated parse or
proof derivation cannot masquerade as independent evidence mass.

### 2.2 Exact immutable parameter authority

`parameters_v351.py` provides a reviewed content-addressed initial recurrent parameter inventory:

- one exact core artifact;
- one exact artifact for every required typed message family;
- explicit calibration evidence;
- strict inventory equality against the cycle-pinned `AuthoritySnapshotV351`;
- no Stage-6 code fallback if the pinned inventory is partial/custom.

Stage 0 installs the reviewed initial inventory only when the incoming semantic snapshot has no
dynamics inventory. A partial/custom inventory is never silently completed.

### 2.3 Sparse graph compilation

`compiler_v351.py` compiles already kernel-valid CSIR candidates into sparse typed activation:

1. defensively cluster by semantic fingerprint before dynamics;
2. retain one competition node per semantic class;
3. preserve strongest derivational prior rather than summing duplicate derivations;
4. create explicit evidence source nodes;
5. build typed structure/evidence/grounding/state/discourse/multimodal edges;
6. emit causal expectation edges only from exact pinned causal mechanisms;
7. carry hard-mask proof lineage;
8. preserve open variables and unresolved refs.

Raw text never controls semantic edge families.

### 2.4 Recurrent solver

`solver_v351.py` implements:

`exact pruning → sparse typed propagation → local inhibition → bounded iteration → convergence`

Properties:

- deterministic iteration order;
- exact family/channel gains;
- hard mask clamp before every update;
- competition-local inhibition, not global softmax;
- finite bounded sigmoid/damping dynamics;
- convergence epsilon;
- oscillation detection;
- explicit no-admissible/numeric/budget statuses;
- no process-global mutable score cache.

### 2.5 Attractor stabilization

`stabilizer_v351.py`:

- ranks semantic classes, not derivations;
- retains close inequivalent classes within the explicit ambiguity margin;
- never normalizes one weak surviving hypothesis to support `1.0`;
- preserves absolute recurrent support;
- returns partial meaning for unresolved/non-converged single hypotheses;
- refuses to fabricate a common truth when multiple inequivalent meanings remain;
- propagates open variables/frontier reasons and exact dynamics pins.

### 2.6 Runtime cutover

The baseline-locked apply script replaces canonical Stage 6/7 deterministic services with:

- `RecurrentSemanticDynamicsV351`
- `RecurrentAttractorStabilizerV351`

The deterministic Phase-10 implementation is not used as a hidden canonical fallback. It can
remain available only for explicit oracle/shadow comparison outside canonical Stage 6/7.

## 3. Phase 14 — continuous learning, candidate DAGs and promotion

### 3.1 Prediction-error/frontier classification

`frontier_classifier_v351.py` classifies typed runtime gaps into structural learning families.
It fixes a real integration bug in the old path: unknown observations live in
`EvidenceLattice.form_lattice`, not directly on `EvidenceLattice`; Stage 11 now reads the actual
nested artifact.

Typed `FrontierClass` is primary. Compatibility mapping uses protocol contract identifiers only,
never user-language phrases.

Policy/permission blocks do not become semantic-learning evidence.

### 3.2 All eight required inducers

`inducers_v351.py` implements:

1. `FormNormalizationInducer`
2. `LexicalizationInducer`
3. `SenseInducer`
4. `ConstructionInducer`
5. `SemanticDefinitionInducer`
6. `StateSchemaInducer`
7. `TransitionCausalInducer`
8. `ParameterCandidateTrainer`

Important constraints:

- Every proposal is candidate-only.
- Exact semantic/executable dependencies are pinned.
- Primitive semantic/transition candidates with no prerequisites require explicit dependency
  closure proof.
- Construction learning consumes typed slots/triggers/output authority; it does not mine or
  execute sentence templates.
- Causal learning requires intervention/mechanism evidence. Mere temporal coactivation is
  rejected.
- Parameter learning creates immutable next-revision candidate artifacts only; current pinned
  Θ is never mutated in place.

### 3.3 Generic construction-authorized teaching

`teaching_v351.py` implements two generic exact teaching projections:

- `learning_projection_v351` links an unresolved form slot to an already-resolved exact semantic target (lexicalization/sense learning);
- `semantic_definition_projection_v351` links an unresolved term slot to a resolved exact parent-schema slot and a reviewed structural definition relation;
- a reviewed construction explicitly opts in through exact metadata;
- its form slot must be an explicitly reviewed `open_observation_slots` slot;
- one unresolved surface observation must pair with exactly one resolved semantic target;
- ambiguous/multiple targets remain unresolved;
- target, pack and teaching construction are exact-pinned;
- competence/use/review/authorization metadata travels with the projection.

No word order, dependency-label subject/object mapping, English string, or concept name is used
to infer meaning.

### 3.4 Stage-11 learning engine

`engine_v351.py` installs an explicit non-empty inducer inventory and performs pure candidate work.

For first-use lexical teaching:

`unknown observation + exact teaching projection → candidate form + candidate sense + candidate link`

For a genuinely new reviewed subtype definition:

`unknown term + exact definition construction + exact known parent → candidate referent-type schema + candidate form + candidate sense + candidate link`

The new schema has its own semantic identity and an exact parent/dependency edge; it is not a synonym alias to the parent.

If a form is observed without an exact semantic projection, only a non-executable form candidate
is preserved and a semantic-target frontier remains open.

Structurally derived schema/state/transition/causal/construction signals use canonical payloads and
exact dependency closure.

### 3.5 Stage-13 candidate/evidence commit

`commit_v351.py` composes Phase-12 session-memory commit with Phase-14 durable learning commit.

It:

- filters already resolved/superseded frontiers before staging candidates;
- refuses ACTIVE/competence-verified payloads at Stage 13;
- persists exact candidate records, attributable evidence, immutable evidence links, frontiers and
  exact learning packages in one graph patch;
- separates candidate pins from external dependency pins;
- preserves source lineages/counterexample-compatible package structure;
- creates `COMPETENCE_PENDING` only when requested use + competence cases + evidence exist;
- never reopens terminal packages/frontiers implicitly;
- emits package-targeted maintenance events only after successful commit;
- never publishes authority from Stage 13;
- keeps parameter replacements as pending calibration candidates, not active Θ.

### 3.6 Event-driven competence/promotion

`maintenance_v351.py`:

- requires explicit package refs; empty event scope is a no-op;
- never request-frequency scans all learning frontiers/packages;
- accepts only explicit learning evidence/competence/review/consolidation triggers;
- checks event/package scope and permission compatibility;
- runs competence only through an installed executor whose declared runner ref/revision exactly matches the package's `competence_executor_pins` for that use axis;
- synthesizes neither fake competence nor fake review/authorization;
- requires exact package-revision evidence and competence;
- promotes only explicit positive per-use policy decisions;
- reports authority-generation change, restart requirement and replay requirement.

### 3.7 Critical multi-record promotion graph fix

A deep M3 review found an existing cross-revision bug: independently promoting a learned form,
sense and form-sense link creates active revisions, but the promoted link retained exact references
to the old candidate revisions. The language registry correctly rejects such active authority.

`promotion_rewire_v351.py` plus the baseline patch to `learning/promotion.py` fixes promotion as a
**two-pass dependency-closed graph transition**:

1. pre-plan every positively granted future active revision;
2. materialize promoted records;
3. recursively rewrite exact intra-package `*_ref/*_revision`, nested schema parent/dependency,
   and other exact candidate references to the planned active revisions;
4. fail closed if an active record would retain an exact dependency on an unpromoted candidate;
5. derive durable dependencies on promoted intra-package records;
6. publish the whole dependency-closed promotion in the same CAS transaction.

This is the key fix that makes `learn → promote → restart → reuse learned structure` mechanically
possible instead of merely changing lifecycle flags.

## 4. Phase 9–14 regressions/fixes included

The bundle also hardens earlier learning runtime paths so stale callers cannot restore old bugs:

- implicit global frontier scans are forbidden; explicit event-targeted refs are required;
- an empty inducer registry cannot claim learning progress;
- candidate dependency pins are no longer silently reconstructed as empty;
- competence-tested package revisions are not replaced by synthetic `PROMOTABLE` revisions that
  sever competence/evidence exactness;
- resolved frontiers cannot leave orphan candidate audit artifacts;
- promotion scope/permission mismatch fails closed;
- derivation lineage is no longer counted as evidence lineage;
- weak single attractors are no longer normalized to certainty;
- active multi-record promotions cannot retain candidate-revision dependencies.

## 5. Meaningful M3 / use-case coverage

The included tests deliberately use arbitrary nonce symbols generated only inside tests. Production
code contains no sample concept name. Two different learning cases are covered:

### 5.1 New lexicalization for an existing exact concept

1. previously unseen surface observation;
2. reviewed construction-authorized teaching projection to an exact existing semantic target;
3. real candidate `LANGUAGE_FORM → LEXICAL_SENSE → FORM_SENSE_LINK` DAG;
4. candidate/non-authoritative lifecycle before competence/promotion;
5. active-revision rewiring;
6. fresh registry after restart resolves a new occurrence to the taught exact target.

### 5.2 Genuinely unseen concept, not merely a synonym

1. arbitrary unknown term;
2. reviewed definition projection identifies an exact known parent schema and structural `subtype` relation;
3. `SemanticDefinitionInducer` creates a distinct candidate `ReferentTypeSchema` with exact parent/dependency closure;
4. lexical form/sense/link candidates target that *candidate schema*, forming one dependency DAG;
5. promotion planning assigns future active revisions for every positively granted record;
6. promotion rewrites the sense target and link endpoints to the active revisions in one CAS graph transition;
7. a fresh post-restart language registry resolves the arbitrary term to the newly created schema, whose identity is distinct from the parent.

This is the correct M3 mechanism-level proof. A fully deployed `text → learn → promote → process restart →
new composition → query → answer` run still requires the exact lowered definition-teaching authority to be
present in the rebuilt boot generation plus independent competence/review/activation authorization.

## 5.3 Reviewed language-authority activation boundary

A deep review found that the applied baseline's reviewed English source declares the
`DEFINITION_TEACHING` family, but the currently signed boot manifest activates earlier English
package revisions and the source seed itself did not carry the exact lowered Phase-14 slot contract.
The bundle therefore adds:

- `language/phase14_learning_authority_v351.py`: generic source-contract → exact-slot metadata lowering/validation;
- a baseline patch that advances the reviewed minimum-English **source** to revision 4 and attaches a structural definition-learning contract (`term`, `definition_content`, `subtype`) to the definition-teaching family;
- `tools/verify_v351_phases13_14.py`, which fails closed when no ACTIVE lowered construction carries valid `semantic_definition_projection_v351` authority.

The patch deliberately does **not** edit runtime manifest hashes or the boot database. Those artifacts are
signed/release authority and must be regenerated by the canonical release pipeline. Until that happens,
implementation-level M3 is present and tested, but live deployed M3 must not be claimed.

## 5.4 Parameter-candidate boundary

`ParameterCandidateTrainer` produces immutable next-revision Θ candidates with training/evidence lineage.
The current canonical semantic-store `RecordKind` inventory does not define a dynamics-parameter record family,
so this bundle does not smuggle Θ through an unrelated record type or mutate the current pinned parameters.
Parameter candidates remain non-authoritative calibration work until exact dynamics-parameter publication is
performed by the authority/release substrate.

## 6. Tests included

- `test_phase13_recurrent_dynamics_v351.py`
  - exact 12-family Θ inventory;
  - partial inventory fail-closed;
  - hard masks dominate recurrence;
  - budget exhaustion remains partial;
  - absolute support/no fake `1.0` certainty.
- `test_phase14_inducers_v351.py`
  - all eight inducers;
  - generic lexical candidate DAG;
  - dependency-closure proof requirement;
  - immutable parameter candidates;
  - active-revision rewiring/fail-closed missing promoted dependency.
- `test_phase14_learning_authority_contract_v351.py`
  - reviewed English source revision 4 carries a definition-learning contract;
  - generic source category contract lowers to unique exact construction slot refs;
  - lowered authority validates `open_observation_slots` + `semantic_definition_projection_v351`.
- `test_phase14_learning_lifecycle_v351.py`
  - event-driven no-global-scan behavior;
  - legacy safety patch regression assertions.
- `test_phase13_14_runtime_wiring_v351.py`
  - canonical Stage6/7 and Stage11/13 cutover;
  - no concept-specific sample nonce in production code.
- `test_phase14_m3_contract_v351.py`
  - arbitrary unseen concept candidate-first path;
  - fresh-registry post-restart resolution through promoted exact graph.

## 7. Verification status

Static/package verification performed before packaging:

- all Python files AST-parse/compile;
- `compileall` passes for bundle payload/tests/apply script;
- machine-readable status JSON validates;
- no TODO/FIXME/NotImplemented placeholders in production payload;
- no M3 sample nonce appears in production implementation;
- manifest hashes are generated only after the final frozen file set is complete (packaging step).

**Not claimed:** full repository `pytest`, deployed revision-4 language boot/authority publication, M2+M3 end-to-end web-demo conversation, concurrency/performance soak, or real independent competence executor outcomes. Those require applying
the bundle to the exact checkout and running the full repository environment. The apply script includes
`--dry-run` anchor validation to fail closed on source drift before mutation.
