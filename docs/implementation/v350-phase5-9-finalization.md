# CEMM v3.5 — Phases 5–9 Semantic Activation Finalization

**Patch baseline:** `5c2bd17f37f94b523c737d2359f38684680206c1` (`Apply fixes phase3-4 patch`)

**Scope:** complete the semantic/query/self-state/response/learning/seed-cutover substrate described by `ARCHITECTURE.md`, `CORE_LOOP.md`, `docs/architecture/FOUNDATIONAL_SEMANTIC_ALGEBRA.md`, and `phased-fixes.md`, while repairing integration drift discovered after the Phase 3–4 patch was applied.

This implementation is intentionally fail-closed. It does not make a demo sentence pass by adding English phrase handlers, predicate-name switches, fake adapters, default-as-fact state, or invented linguistic competence.

---

## 1. Governing invariants

### 1.1 Semantic Contribution Law

A recognized form contributes only the smallest meaning justified by reviewed authority: target candidates, variables, restrictions, projections, scope, arguments, grammatical features, or construction triggers.

A WH/query contribution is not itself `ASK`. A modal is not itself a capability answer. A state default is not an observed state.

### 1.2 Query Separation Law

The runtime keeps these independent:

```text
information gap
≠ answer projection
≠ matrix discourse force
≠ response obligation
```

An embedded interrogative may contain a query variable without requesting a response. A matrix question requires separate reviewed discourse-force authority.

### 1.3 Meaning Closure Law

Open meaning closes only from compatible evidence:

```text
lexical contributions
+ construction program
+ participant/discourse anchors
+ grounding
+ ReferentKnowledgeView
+ type/facet/state/capability closure
+ time/context
→ bounded candidate domain
```

The runtime must not globally enumerate every schema merely because a WH-like variable is broad.

### 1.4 No invented authority

The Phase-9 migration deliberately does **not** synthesize an active punctuation-to-`ASK` rule or fabricate competence references. Existing query-variable senses that directly targeted `discourse-act:ask` are decomposed into information-gap contributions. Matrix interrogative force must come from separately reviewed construction/discourse authority.

This can expose a typed frontier for a language pack whose old behavior depended on the conflation. That is correct and preferable to preserving a semantic bug.

---

# 2. Phase 3–4 regressions repaired first

The Phase 5–9 patch treats these as prerequisites rather than assuming Phase 3–4 is complete.

## 2.1 Stage 4 closure was not exported on the base runtime path

The Phase-3/4 closure compiler existed, but base Stage 4 returned only `referent_projections`, while Stage 5 consumed `semantic_closure_candidates`.

Fixed path:

```text
Stage 3 grounding preparation
→ Stage 4 ReferentKnowledgeView(s)
→ ReferentKnowledgeClosureCompiler
→ semantic_closure_candidates
→ Stage 5 MeaningComposer
```

## 2.2 Round-trip analyzer still used the obsolete post-hoc binder API

The independent target-language analyzer now follows the same closure-aware path as normal understanding:

```text
form lattice
→ grounding
→ referent projection
→ semantic closure
→ MeaningComposer
→ UOL
```

There is no second semantic pipeline for realization verification.

## 2.3 Construction semantic-plan identity was under-specified

Plan identity now includes the complete branch semantics, not only output schema pins:

- applications and exact schema pins;
- port bindings;
- variables and expected filler/schema/type constraints;
- unifications;
- restrictions and projections;
- scope;
- grammatical/temporal/aspect/modal feature assignments;
- roots.

Two branches with the same schemas but different bindings can no longer collide.

## 2.4 Referent closure leaked across unrelated constructions

Construction schema-class activation is now scoped through:

```text
construction candidate
→ its slot/sense evidence
→ linked grounding mentions
→ candidate referents for those mentions
→ only those referents' closure candidates
```

A type entitlement of referent B cannot activate a schema candidate for an unrelated construction about referent A.

## 2.5 Query lexical variable and construction gap could diverge

When a reviewed construction slot contains exactly one QUERY lexical variable and its semantic port explicitly permits `OpenBindingPurpose.QUERY`, materialization binds that exact variable to the port.

Otherwise it preserves an independent `PARTIAL_COMPOSITION` gap rather than guessing.

---

# 3. Phase 5 — Typed interrogatives and universal answer binding

## 3.1 Exact/N-best answer projection contract

`SemanticVariable` now preserves:

- `projection_ref` + exact revision when one projection is selected;
- `projection_candidates: tuple[(schema_ref, revision), ...]` when multiple reviewed projections remain;
- expected schema classes;
- expected filler classes;
- expected type refs;
- restriction refs;
- open-binding purpose;
- scope.

The codec and UOL equivalence signature preserve all of these fields.

Multiple projections are no longer converted into unresolved string references.

## 3.2 Ground analyzer obeys explicit per-use lexical authority

A migrated or learned sense may have multiple authorized operations. `FormLatticeAnalyzer` is the GROUND path and now includes a sense only when `sense.supports_use(GROUND)`.

A REALIZE-only sense can no longer leak into understanding merely because its primary record is active.

## 3.3 `UniversalSemanticBinder`

Stage 10 now compiles typed query requests and binds them over normalized semantic storage families instead of only exact `SemanticApplication` rows.

Supported structural families include:

- exact `SemanticApplication` bindings;
- `StateAssignment` and qualified `DefaultExpectation` from `ReferentKnowledgeView`;
- `CapabilityInstance` when an explicit reviewed capability query adapter/restriction licenses that interpretation;
- `ReferentTypeAssertion`;
- `IdentityFacetRecord` only with an explicit reviewed facet selector;
- `EventOccurrence` when explicitly projected through event-occurrence authority;
- `KnowledgeRecord`;
- referents, including quantity/time/context/schema-topic storage kinds through ordinary typed referent/application binding;
- property/relation/role/function/resource applications projected in `ReferentKnowledgeView`.

### Critical non-conflation

An open variable whose expected class is `ACTION` is **not automatically treated as a capability query**.

That would incorrectly collapse:

```text
what did X do?
what can X do?
```

Capability binding therefore requires explicit semantic restriction/query-adapter authority.

## 3.4 `property:name` is deliberately not mapped to the broad identity-facet store

Current `IdentityFacetRecord` storage does not structurally distinguish the self `name` facet from `identifier` strongly enough for a generic bridge.

Therefore the migration does not add:

```text
property:name → identity_facet
```

by string convention. Existing exact `property:name` semantic applications remain the safe answer authority. A future identity-facet bridge must carry an explicit reviewed `identity_facet_selector_ref`.

## 3.5 Defaults remain qualified

If no active state assignment exists, a default can be returned only as:

```text
default_expected
```

with exact rule/evidence lineage. It is never converted into an active fact.

---

# 4. Phase 6 — Runtime-backed self state and capability truth

`RuntimeSelfObserver` runs before Stage 0 so cycle pins capture the post-observation semantic substrate.

The observer accepts only mechanical signals. Built-in authority is deliberately narrow:

```text
runtime:core-loop = operational
```

Reaching an initialized canonical runtime proves neither connectivity, health, emotional state, external service availability, nor action capability.

## 4.1 Reviewed semantic mapping

Schemas opt in using reviewed metadata:

```text
runtime_state_bindings
runtime_capability_bindings
```

Each mapping contains an exact signal/value contract and exact state/action schema pins.

The migration adds only the mechanically justified operational-state mapping:

```text
runtime:core-loop=operational
→ state:operational_status
→ state-value:operational_status:operational
→ context: global
```

It does not seed fake availability/connectivity.

## 4.2 Exclusive state replacement

For an exclusive state dimension, an observed state change retires the prior current overlay assignment before adding the new immutable observation, preventing contradictory simultaneous current values.

## 4.3 Capability truth

Capabilities are updated only when a reviewed action schema declares `runtime_capability_bindings`. The runtime never infers capability merely because a Python implementation exists.

---

# 5. Phase 7 — Generic goals, Response UOL, and bound-value realization

## 5.1 Structural query response artifacts

Response cognition gains an artifact trigger family:

```text
BOUND_QUERY
PARTIAL_QUERY
```

This patch activates only `BOUND_QUERY` generically.

An incomplete query remains a typed learning frontier unless independently reviewed clarification UOL exists. The runtime does not manufacture a clarification sentence from the existence of a gap.

## 5.2 Generic bound-query policy

The Phase-9 migration removes executable predicate-specific answer rules/transforms and installs exactly one structural bound-query policy plus one bound-query transform.

Newly learned schemas therefore do not need one Python branch + one response policy + one transform per predicate.

## 5.3 Epistemic authorization bug fixed

`GoalAuthorizationGate` now checks `KnowledgeRecord.truth_status` and accepts supported/both truth states where epistemic support is required. The old `status` lookup could reject valid knowledge because the field does not exist on `KnowledgeRecord`.

## 5.4 Response UOL copies proof-bearing bound meaning

`BoundQueryResponsePlanner`:

- pins the exact selected goal and generic transform rule;
- requires durable source lineage;
- preserves qualifications such as `default_expected` and capability status;
- carries the bound answer graph directly into Response UOL;
- records the query-result fingerprint so stale results cannot be substituted.

## 5.5 Bound-value realization

The realization layer can now handle query answer roots that are not only semantic applications.

### Schema-topic answer

```text
exact schema pin
→ REALIZE-authorized lexical sense
→ lexeme-sense link
→ lexeme
→ form
→ morphology
→ surface
```

### Literal answer

Literal output is allowed only when the synthetic bound answer node carries an exact source-record pin that:

- exists;
- has the expected fingerprint;
- is included in Response UOL source lineage;
- remains permission-visible.

No transcript text, schema-key prettification, or guessed fallback is used.

### Lexeme-first realization

Predicate realization now prefers the canonical reverse path:

```text
semantic target
← sense
← lexeme-sense link
← lexeme
← lemma form
→ morphology
```

Direct form→sense is retained only as bounded legacy/multiword compatibility when no canonical lexeme path is available.

---

# 6. Phase 8 — Learning runtime cutover

## 6.1 Typed frontiers from artifacts, not frontier-name semantics

`TypedRuntimeFrontierCompiler` derives learning requirements primarily from actual artifacts:

- unresolved form spans;
- unresolved grounding mentions;
- unresolved semantic query variables and their exact expected schema/filler/type/projection constraints.

Only exact canonical runtime prefixes are used for backward-compatible realization/operation/construction frontiers. Unknown frontier strings remain generic. The compiler does not infer meaning from substrings such as `"query" in ref` or `"ground" in ref`.

## 6.2 Promotion before Stage 0

`LearningRuntimeActivator` considers only effective `PROMOTABLE` package revisions and requires:

- evidence links;
- competence results;
- review refs;
- explicit authorization refs;
- promotion policy success.

Promotion happens before Stage 0 so the cycle pins either the pre-promotion or post-promotion substrate deterministically—not a mid-cycle mutation.

## 6.3 Exact per-use promotion

Promotion now writes the exact operations granted by positive promotion grants onto records that expose `authorized_use_operations`, and marks the authority explicit.

For a learned lexical sense, for example:

```text
GROUND allowed
REALIZE denied
```

cannot silently become “active for everything.”

Frequency or repeated observation never grants authority.

---

# 7. Phase 9 — Seed authority migration and activation cleanup

The migration tool is:

```text
tools/migrate_v350_phase9_semantic_seed.py
```

It is deterministic and has a `--check` mode that:

1. copies the source tree to a temporary directory;
2. migrates it;
3. validates invariants;
4. migrates it a second time;
5. requires byte-for-byte idempotence.

## 7.1 Ordinary lexical authority

For ordinary token/clitic/affix records:

```text
form → sense
```

becomes:

```text
form → lexeme → sense → semantic contribution specs
```

The old direct link is retained as `superseded` migration lineage rather than silently deleted.

Genuine multiword/idiomatic direct authority remains available where appropriate.

## 7.2 Query senses

Legacy query-variable senses that directly target `discourse-act:ask` have that target removed and compile to typed `VARIABLE` / `PROJECTION` contribution specs.

The migration does not fabricate matrix-question competence to compensate.

## 7.3 Typed construction authority

`metadata.interpretation_enabled` is removed.

Every construction receives explicit `authorized_use_operations` and `use_authority_explicit=true`.

A construction previously disabled with `interpretation_enabled=false` remains denied for COMPOSE unless an already executable construction program supplies real authority. Removing the legacy boolean cannot accidentally activate the Phase-20 catalogue.

Fixed-output constructions that are genuinely COMPOSE-authorized are migrated to declarative `ConstructionProgramRecord` programs.

## 7.4 Predicate answer catalogue cleanup

The migration removes:

- predicate-specific executable answer policy rules;
- predicate-specific response transforms;
- now-unused predicate-specific `response_policy` schemas such as `response-policy:answer:event-X`.

It preserves the foundational `response-policy:answer-query` schema and installs the generic bound-query rule/transform.

## 7.5 Broad state applicability drift

`state:availability` and `state:connectivity` are marked `requires_applicability_evidence` so type entitlement alone does not manufacture query closure for those dimensions without active applicability/state evidence.

This is especially important because availability was historically over-broad across `type:referent`.

---

# 8. Files changed by the source patch

The fail-closed applier modifies the existing baseline files:

```text
cemm/v350/language/model.py
cemm/v350/language/analyzer.py
cemm/v350/language/codec.py
cemm/v350/language/registry.py
cemm/v350/language/programs.py
cemm/v350/learning/authority.py
cemm/v350/learning/promotion.py
cemm/v350/uol/model.py
cemm/v350/uol/codec.py
cemm/v350/uol/equivalence.py
cemm/v350/composition/builder.py
cemm/v350/composition/materializer.py
cemm/v350/facets/closure.py
cemm/v350/goals/model.py
cemm/v350/goals/codec.py
cemm/v350/goals/policy.py
cemm/v350/response/model.py
cemm/v350/response/codec.py
cemm/v350/realization/authority.py
cemm/v350/realization/engine.py
cemm/v350/runtime.py
cemm/v350/runtime_services.py
```

New files:

```text
cemm/v350/querying.py
cemm/v350/runtime_state.py
cemm/v350/goals/query_policy.py
cemm/v350/response/query_response.py
cemm/v350/realization/bound_values.py
cemm/v350/learning/runtime.py
tools/migrate_v350_phase9_semantic_seed.py
tests/v350/test_phase5_9_semantic_cutover.py
docs/implementation/v350-phase5-9-finalization.md
```

---

# 9. Application and release sequence

The patch applier is baseline-pinned and fail-closed.

```bash
python apply_phase5_9.py --repo /path/to/cemm --check
python apply_phase5_9.py --repo /path/to/cemm
```

Do not use `--allow-head` unless the exact source drift has been manually reviewed.

Then validate and apply the deterministic seed migration:

```bash
python tools/migrate_v350_phase9_semantic_seed.py cemm/data/v350 --check
python tools/migrate_v350_phase9_semantic_seed.py cemm/data/v350
```

After source migration, run the repository's canonical deterministic v3.5 boot compiler and signed runtime-authority generation workflow. The patch deliberately does not hand-edit:

```text
boot.sqlite
runtime_authority_manifest.json
source fingerprints
signed verification artifacts
```

Those must be regenerated from the migrated source so hashes remain meaningful.

Then run, in order:

1. source/migration invariant tests;
2. focused Phase 5–9 tests;
3. full `tests/v350` suite;
4. deterministic boot rebuild reproducibility check;
5. runtime-authority verifier;
6. final cutover verifier;
7. representative multilingual + synthetic-vocabulary productivity tests;
8. restart/reload learning-promotion tests.

---

# 10. Required acceptance behavior

A release is not complete merely because one English prompt works.

The following must hold:

### Query decomposition

```text
embedded interrogative
→ query variable/projection may exist
→ no automatic ASK
```

```text
matrix interrogative
→ separate reviewed discourse-force authority
→ response_requested=true
```

### Variable-port unification

A WH variable filling a reviewed semantic slot becomes the exact QUERY variable on that port; no duplicate unrelated gap is created.

### Referent-driven closure

Changing only the grounded referent type/entitlements changes available semantic candidates without changing kernel code.

### Generic binding

The same Stage-10 binder handles exact properties, state assignments, qualified defaults, type assertions, capabilities when explicitly restricted, events/knowledge, and typed referents without predicate-name branches.

### Runtime truth

Runtime state transitions change answers through state records/evidence. No conversational response seeds a convenient self-state fact.

### Generic response

A newly promoted answerable semantic schema does not require a new Python response branch or per-predicate response transform.

### Learning restart

A reviewed/promoted nonce concept or construction survives restart through durable promoted records and is available only for explicitly granted use operations.

---

# 11. Explicit non-claims

This patch completes the **kernel/runtime substrate and migration path** for Phases 5–9. It does not fabricate linguistic competence that is absent from reviewed language data.

In particular:

- it does not claim every EN/FR/SW WH/copula/auxiliary construction is already present;
- it does not infer matrix ASK from punctuation without reviewed authority;
- it does not claim `what can you do?` is solved by an English phrase rule;
- it does not map `property:name` to ambiguous identity facets by string convention;
- it does not treat an ACTION variable as a capability query without an explicit capability restriction;
- it does not turn defaults into state facts;
- it does not bypass boot/signature regeneration.

Missing reviewed language constructions should now fail as typed frontiers rather than silently collapsing into incorrect semantics. That is the intended architecture.
