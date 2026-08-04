# R2 Recursive Composition and Independent Verification Implementation Plan

**Status:** implementation-ready remaining-work specification  
**Date:** 2026-08-04  
**Scope:** `hybrid_mvp/` only  
**Audited branch:** `main`  
**Audited head:** `79040b6bd42ef02130b63d906d337f1a1b1e1c2a`  
**Admitted predecessor:** R1 — `run:5eb271d7fcaa56e8febee288`  
**Target outcome:** fresh governed R2 admission with `G0=green`, `R1=green`, `R2=green`, `R3-R8=red`

---

## 1. Purpose

R2 does **not** redesign the semantic algebra and does **not** introduce new ABIs. R1 already admitted the hard-cut ABI seam:

```text
Evidence ABI 1
→ Proposal Context ABI 1
→ Semantic Switch Program ABI 2
→ Semantic Expression ABI 1
→ Compilation Proof ABI 1
→ Source Coverage ABI 2
→ Proposal Result ABI 2
→ Verification Batch ABI 2
→ Verified Meaning ABI 1
```

R2 activates the recursive semantics already reserved by those ABIs. It completes authentic bounded construction and independent verification for:

- all five persistent operators;
- all four semantic modes;
- all twelve switch actions;
- multiple applications;
- multiple roots, including at least three roots in admission canaries;
- nested proposition-valued roles;
- expression links;
- scope;
- projected variables;
- references and literals;
- reviewed transition proposals;
- canonical expression-level ambiguity.

R2 ends after VERIFY. A selected `VerifiedMeaning` must still terminate at the exact typed R3 boundary:

```text
LaterOwnerNotAdmitted(
    verified_meaning_ref,
    "contract:r3:evaluate",
)
```

R2 must not implement decisions, effects, learning, response meaning, realization, neural training, corpus authority, product surfaces, or release evaluation.

---

## 2. Governing authority

Implementation must follow this precedence:

1. `hybrid_mvp/AGENTS.md`
2. `hybrid_mvp/docs/superpowers/specs/2026-08-02-hybrid-semantic-algebra-corrective-replay-amendment.md`
3. `hybrid_mvp/docs/superpowers/specs/2026-07-31-hybrid-mvp-corrective-replay-admission-design.md`
4. `hybrid_mvp/docs/superpowers/plans/2026-07-31-hybrid-mvp-corrective-replay-master-plan.md`
5. `hybrid_mvp/docs/superpowers/plans/2026-07-31-hybrid-mvp-g0-r1-implementation-plan.md`
6. `hybrid_mvp/docs/ARCHITECTURE.md`
7. `hybrid_mvp/docs/ABI_REGISTRY.md`

The July 29 completion design and M2 implementation plan remain useful implementation evidence, but their execution ordering is superseded. In particular:

| Historical M2 work | Current replay owner |
|---|---|
| Reversible forms and grounding | R2 |
| Affordances and bounded semantic context | R2 |
| Recursive exact composition | R2 |
| Exact verifier and masks | R2 |
| Deterministic bootstrap composer | R2 development/admission instrument |
| Episode/corpus generation | R4 |
| Neural proposer, confidence, calibration | R5 |
| Production neural cutover | R5/R6 |

No R4 or R5 work may be pulled forward merely because it appeared in the historical M2 milestone.

---

## 3. Exact R2 completion contract

R2 is green only when one authentic public runtime path proves all of the following.

### 3.1 Evidence and context

- One `FormResolver` owns exact source-character segmentation.
- Joining every source unit reproduces the input byte-for-byte at the Unicode string level.
- No downstream owner retokenizes or creates a second coordinate system.
- `ProposalContext` contains only current-cycle bounded slots and exact revision lineage.
- No proposer, compiler, verifier, or mask opens an authority-wide target inventory after ORIENT.
- Unknown content is retained as typed unresolved evidence or causes explicit abstention; it never creates semantic refs.
- Reviewed aliases can target existing identities without regenerating the closed-class form pack.

### 3.2 Composition

- All five persistent operators are constructible:
  `op:designation`, `op:type`, `op:relation`, `op:state`, `op:event`.
- All four modes are constructible:
  `OBSERVE`, `QUERY`, `REQUEST`, `SIMULATE`.
- All twelve Program ABI 2 actions have positive, non-vacuous behavioral proof.
- The deterministic proposer can construct more than one application and more than one root.
- Admission canaries include at least one valid three-root expression.
- Nested proposition-valued roles are constructible through `bind_nested_application("role", ...)`.
- Coordination, conjunction, disjunction, condition, cause, purpose, contrast, and sequence are represented through the existing link variant, not a thirteenth action.
- Scope supports the reviewed polarity, modality, tense, aspect, attribution, epistemic, quotation, and simulation distinctions required by current authority.
- Variables are introduced only through exact `VariableSlot` pointers and valid binders.
- Literals preserve exact source value and admitted type.
- Transition proposals are reviewed decision hints bound to a source application; they do not manufacture applications or mutate state.

### 3.3 Compilation and verification

- `SemanticExpressionCompiler` is total over the admitted R2 action grammar.
- Every successful compilation returns one canonical `SemanticExpression` and one complete `CompilationProof`.
- Every program action, source assignment, and declared root appears exactly once in its proof domain.
- Equivalent derivations compile to one `expression_ref`.
- Swapped grounded pointers, roles, ordered operands, scope, or roots produce different expression identities where semantics differ.
- VERIFY independently reconstructs the expression and graph laws instead of trusting compiler output.
- Coverage is independently recomputed from the exact context.
- Ambiguity is grouped by distinct `expression_ref`; duplicate derivations are not score-summed.
- Truncation fails closed and cannot yield a unique selected meaning.

### 3.4 Runtime boundary

- `HybridRuntime.process()` remains the only public cognitive path.
- Real evidence reaches ORIENT, PROPOSE, and VERIFY through the same immutable `ProposalContext`.
- Valid R2 recursive inputs produce a selected `VerifiedMeaning` and stop at the R3-not-admitted gap.
- Unknown, ambiguous, rejected, and budget-exhausted cases return their existing typed outcomes.
- No world, session-focus, effect, or authority mutation occurs in R2.
- Programming exceptions propagate.

### 3.5 Admission

- Every retained predecessor test due by R2 is active and meaningful.
- Every R2 rewrite obligation has all required successor nodes.
- No active R2 test is vacuous, stale, skipped, xfailed, or xpassed.
- R2 has explicit owner, phase, structural, SQLite activation, and admission selectors.
- One fresh admission run passes against one clean committed source.
- The exact receipt is consumed once into the append-only replay ledger.
- Chain verification passes with R3-R8 remaining red.

---

## 4. Current implementation inventory

The following is already implemented and should be retained unless a focused defect requires correction.

| Owner | Current state | R2 treatment |
|---|---|---|
| `forms.py` | Exact reversible Evidence/Form ABIs, bounded tokenization, source spans, closed-class features | Retain; extend reviewed structural evidence and migrate stale tests |
| `grounding.py` | Indexed designation grounding, typed unresolved evidence, nonlinguistic evidence path, no atom creation | Retain; add authentic unknown-frontier integration proof |
| `affordances.py` / `contributions.py` | Kind/frame-derived bounded semantic affordances and typed contribution ports | Retain; verify all R2 frame shapes |
| `proposal_context.py` | Content-addressed designation, contribution, mode, frame, reference, scope, link, variable, transition and residual slots with indexes | Retain ABI; harden slot derivation and reviewed-value legality |
| `programs.py` | Frozen twelve-action Program ABI 2, ordered identity, exact assignments, multiple root field | Retain ABI unchanged |
| `proposal.py` | Proposal Result ABI 2 and deterministic context-local proposer | Replace flat construction algorithm with bounded recursive search |
| `expressions.py` | Recursive Semantic Expression ABI 1, canonicalization, proof and `VerifiedMeaning` | Remove R1-only lowering restrictions; retain ABI |
| `coverage.py` | Exact Source Coverage ABI 2 and no-repair validation | Extend recursive assignment corruption coverage only |
| `verifier.py` | Exact proposal envelope, action replay, coverage, compilation, expression-level grouping | Complete independent recursive reconstruction and graph laws |
| `runtime.py` | Single path to VERIFY and exact R3 typed boundary | Add recursive public-path canaries; do not extend into R3 |
| `state.py` | Pure transition preview, precondition checking and sequence composition already exist | Keep preview-only R2 subset; direct commits remain R3 |
| Governance | G0 and R1 admission machinery is operational | Add R2 selectors, structural step, admission, receipt and ledger transition |

### 4.1 Deliberate R1 restrictions that R2 must remove

The current compiler intentionally rejects:

```text
bind_nested_application
attach_scope
project_variable
propose_transition
```

It also requires:

- exactly one `instantiate_operator`;
- no proposition-valued frame roles;
- exactly one application root.

The current bootstrap proposer similarly emits only:

- one selected application frame;
- one local application;
- flat role/reference bindings;
- one root;
- no link, scope, binder, or transition action.

These are valid R1 restrictions, but they are the primary R2 implementation blockers.

---

## 5. Audit findings that must be corrected before implementation evidence is trusted

R2 cannot simply activate every inherited test currently labelled R2. Several tests retain useful intent but no longer prove it.

### 5.1 Vacuous or stale tests

1. **Bootstrap paraphrase test does not use its `surface` parameter.**  
   It proposes from the same fixture context for every parameterized phrase.

2. **Typed-gap proposer test is tautological.**  
   An assertion equivalent to `len(candidates) >= 0` proves nothing.

3. **Candidate-order assertion is outdated.**  
   Sorting by candidate or program ref conflicts with preserved proposer order and rank authority.

4. **Action-mask enumeration covers only a subset of actions.**  
   It does not independently enumerate nested role/link, scope, variable, and transition actions.

5. **Several mutation tests accept constructor `ValueError` as a substitute for verifier-owned typed rejection.**  
   R2 needs explicit earliest-owner distinctions.

6. **Program operator extraction tests inspect `op:` strings in dynamic action arguments.**  
   Program ABI 2 `instantiate_operator` points to an application frame; the operator must be resolved from the context, not guessed from argument spelling.

7. **Scope and transition tests only assert retired wrapper classes are absent.**  
   They do not prove `attach_scope` or `propose_transition`.

8. **Form/grounding immutability tests use obsolete direct constructors.**  
   They must use canonical factories and exact round trips.

9. **The “authority generation changes” grounding test does not actually publish or relink a changed authority generation.**

10. **Some adversarial cycle/depth tests use malformed fixture mutations that do not construct the claimed graph.**

### 5.2 Missing governed successor

The frozen inventory already requires:

```text
tests/test_r2_unknown_frontier.py::
    test_unknown_surface_abstains_or_emits_typed_unresolved_candidate
```

That successor does not exist and blocks truthful completion of its rewrite obligation.

### 5.3 Missing validation phase

`configs/validation_gates.json` currently defines only G0 and R1. R2 has no:

- owner selectors;
- phase selector;
- structural validator;
- admission graph;
- governed receipt;
- green ledger row.

---

## 6. Non-goals

Do not implement any of the following in this plan:

- neural proposal or neural realization;
- checkpoint loading or safetensors release activation;
- model confidence, calibration, selection, ablation, or training;
- reviewed gold compilation or semantic corpus generation;
- episode regeneration, hard-negative generation, or sealed partitions;
- query execution, epistemic placement, state admission, effects, learning, response meaning, or realization;
- CLI, API, or web product cutover;
- competitive evaluation or release thresholds;
- direct world mutation from transition previews;
- root CEMM adoption.

These belong to R3-R8.

---

## 7. Implementation sequence

Each task follows:

1. introduce or repair the exact failing test;
2. run the focused owner tier and observe the intended failure;
3. implement the earliest owner;
4. run focused tests;
5. perform contract review;
6. perform code-quality/performance review;
7. run the coalesced phase tier only when the cross-owner boundary changes;
8. commit one coherent task.

No task may weaken a bound or convert a programming error into a semantic gap.

---

# Task 0 — Freeze this R2 execution plan and establish the diagnostic baseline

## Goal

Make the remaining-work plan reviewable and generate a truthful diagnostic inventory without claiming R2 admission.

## Files

- Create: `specification/r2-implementation-plan.md` or the reviewed canonical repository location chosen for this plan
- Modify, only after review: `docs/DOCUMENT_AUTHORITY.json`
- Create: `tests/test_r2_plan_contract.py`
- Create: diagnostic output outside governed admission artifacts

## Work

- Pin the exact admitted R1 predecessor and audited main commit.
- Add a source-level contract test ensuring R2 does not import R3-R8 owners.
- Enumerate every predecessor node whose activation phase is R2.
- Enumerate every R2 rewrite obligation and required successor.
- Run a diagnostic collection only; do not append a status row.
- Record:
  - exact due-node count;
  - missing successor nodes;
  - constructor/collection failures;
  - currently passing but vacuous tests;
  - wall time and peak RSS.

## Exit criteria

- The plan is approved as the R2 execution contract.
- Every due predecessor assertion is mapped to retained, corrected, superseded, or newly introduced evidence.
- No R2 implementation begins against an unknown test set.

## Suggested commit

```text
docs: freeze remaining R2 recursive-composition plan
```

---

# Task 1 — Repair the R2 test lifecycle before relying on it

## Goal

Make the due R2 test suite executable, non-vacuous, ABI-current, and semantically aligned.

## Files

Modify:

- `tests/test_form_lattice.py`
- `tests/test_grounding.py`
- `tests/test_program_abi.py`
- `tests/test_action_masks.py`
- `tests/test_exact_verifier.py`
- `tests/test_adversarial_programs.py`
- `tests/test_bootstrap_proposer.py`
- `tests/test_coverage.py`
- applicable test metadata/supersession files

Create:

- `tests/test_r2_unknown_frontier.py`
- `tests/test_r2_test_integrity.py`

## Work

### 1.1 Canonical constructor migration

Replace obsolete direct constructors with:

- `EvidenceItem.create`;
- `EvidencePacket.create`;
- `FormUnit.create`;
- `FormHypothesis.create`;
- `GroundingResult.create`, where available;
- canonical `as_dict` / `from_dict` round trips.

Immutability tests must mutate canonical values, not invalid legacy instances.

### 1.2 Remove vacuous assertions

Replace:

- unused paraphrase parameters;
- `len(...) >= 0`;
- class-absence-only “scope” and “transition” tests;
- empty prefix parity tests that compare two paths sharing the same enumerator;
- malformed cycle/depth mutations.

Every test name must accurately describe the proof it performs.

### 1.3 Correct outdated semantic assertions

- Replace ref-sorted candidate expectations with preserved proposer-order/rank expectations.
- Resolve operators through `ApplicationFrameSlot.operator_ref`, not ref spelling.
- Rename “authority-constructed LegalActionIndex” assertions to context-local legality.
- Require typed verifier errors when the malformed artifact reaches VERIFY.
- Use constructor failure only for malformed wire/ABI artifacts that cannot legally cross the owner boundary.

### 1.4 Fulfil the unknown-frontier rewrite obligation

Add the exact governed node:

```text
tests/test_r2_unknown_frontier.py::
test_unknown_surface_abstains_or_emits_typed_unresolved_candidate
```

Required behavior:

- Grounding emits a typed unresolved designation.
- Proposal either:
  - abstains with a specific proposal code because critical evidence remains unresolved; or
  - emits a candidate with an exact unresolved filler only where the role contract permits it.
- VERIFY never accepts a critical unresolved referent as a settled grounded identity.
- No semantic ref is manufactured.
- No mutation occurs.

### 1.5 Add test-quality guards

`test_r2_test_integrity.py` should statically reject:

- unused parameterized surface arguments in R2 semantic tests;
- comparisons against trivially true numeric bounds;
- assertions that inspect internal ref spelling to infer operators;
- expected-exception alternatives that conflate constructor and verifier ownership;
- R2 tests whose only assertion is absence of a retired class.

## Exit criteria

- All due R2 tests collect.
- Every required successor exists.
- Every remaining expected failure points to a real missing R2 owner behavior.
- No test metadata is inferred by filename or mutable registry.
- Frozen predecessor inventory is not rewritten; approved supersession metadata is used.

## Suggested commit

```text
test: make R2 predecessor evidence ABI-current and non-vacuous
```

---

# Task 2 — Complete reviewed structural slot derivation

## Goal

Ensure `ProposalContextBuilder` exposes every required recursive structural slot without minting semantic refs or overclaiming syntax.

## Files

Modify:

- `src/cemm_authoritative_hybrid/forms.py`
- `src/cemm_authoritative_hybrid/proposal_context.py`
- `data/languages/en/forms.json`
- at least one second reviewed language form pack
- relevant authority frame/scope/link registries

Create:

- `tests/test_r2_structural_slots.py`
- `tests/test_r2_multilingual_forms.py`
- `tests/test_r2_literal_pointers.py`

## Work

### 2.1 Scope values must be reviewed

Current scope construction converts raw feature values into `value:<surface-feature>`. Replace this with a reviewed mapping supplied by the language/authority contract.

Required behavior:

- no `value:` ref is created by string prefixing;
- every scope slot binds a reviewed value ref;
- polarity normalizes negation into `scope:polarity` with an admitted polarity value;
- attribution, epistemic, quotation, and simulation distinctions are available where reviewed evidence licenses them;
- unknown scope evidence remains typed unresolved/critical.

### 2.2 Complete link coverage

Support the existing expression link registry:

```text
link:coordination
link:conjunction
link:disjunction
link:condition
link:cause
link:purpose
link:contrast
link:sequence
```

- Add purpose evidence.
- Preserve exact connector source geometry rather than assigning an entire clause hypothesis without justification.
- Respect reviewed min/max arity.
- Permit multioperand coordination and sequence within bounds.
- Do not infer commutativity from wording at runtime; use the reviewed link schema.

### 2.3 Harden proposition frame derivation

- Ensure proposition-valued roles come only from reviewed frame metadata.
- Reject a frame whose proposition role is absent from required/optional roles.
- Bind each frame to exact designation and affordance provenance.
- Cover speech/content, condition branches, cause/effect, and purpose structures required by R2 canaries.

### 2.4 Complete variable slots

- Bind query/open-variable evidence to exact candidate frame roles.
- Keep required filler kinds explicit.
- Ensure one source variable cannot silently project into incompatible roles without distinct alternatives.
- Keep local variable identity separate from grounded identities.

### 2.5 Correct transition slot ownership

Transition slots must be derived from reviewed transition/event signatures and bind:

- source application frame;
- event type/signature;
- compatible modes;
- required roles;
- capability and permission refs;
- adapter lineage when present.

Do not treat the transition as an extra semantic application. Do not invoke adapters or mutate stores.

### 2.6 Typed literal preservation

Support the existing admitted literal types:

```text
string
integer
boolean
```

- Preserve exact source value.
- Never derive type by internal ref spelling.
- Reject overflow, noncanonical booleans, or unreviewed coercion.
- Keep literal source assignment and proof lineage.

### 2.7 Multilingual evidence

Add one reviewed non-English form pack and canaries that prove:

- exact reversible spans;
- the same semantic target/action structures;
- no English-specific runtime regex or phrase branch;
- an unseen reviewed synonym resolves through designation authority without pack regeneration.

## Exit criteria

- Context creation yields all required slot families from real evidence.
- No raw feature value becomes a manufactured semantic ref.
- Context remains bounded and serializes canonically.
- The builder does not call resolver/grounder or scan all authority.
- English and the second reviewed language satisfy the same structural contract.

## Suggested commit

```text
feat: complete reviewed R2 structural proposal slots
```

---

# Task 3 — Complete the context-local legal action relation

## Goal

Make one pure legality relation cover the full twelve-action ABI under exact R2 bounds.

## Files

Modify:

- `src/cemm_authoritative_hybrid/verifier.py`
- optionally a narrowly extracted pure legality module if one owner remains canonical
- `tests/test_action_masks.py`
- `tests/test_exact_verifier.py`

Create:

- `tests/test_r2_legal_action_matrix.py`
- `tests/test_r2_prefix_corruption.py`

## Work

### 3.1 Define complete prefix state

Track, without authority access:

- selected context and mode;
- selected designation slots;
- declared applications and frames;
- declared link, scope, and binder nodes;
- bound roles and proposition parents;
- transition hints per application;
- consumed contribution/source slots;
- terminal state;
- application, action, root, and graph-depth budget use.

### 3.2 Legal rules per action

Implement exact legality for:

- `select_context`
- `select_mode`
- `select_designation`
- `instantiate_operator`
- `bind_role`
- `bind_reference`
- `bind_nested_application("role", ...)`
- `bind_nested_application("link", ...)`
- `attach_scope`
- `project_variable`
- `propose_transition`
- `complete_program`
- `abstain`

`complete_program` is legal only when:

- required roles are satisfied;
- all critical evidence is consumed or represented by an admitted unresolved contract;
- roots can be derived unambiguously from parent cardinality;
- all declared nodes are reachable;
- no cycle exists;
- bounds are respected.

### 3.3 Independent exhaustive enumerator

The test enumerator must not simply call the same production candidate generator and compare it to itself.

Create a separately implemented exhaustive reference enumerator over small contexts. For generated bounded prefixes:

```text
ActionMasker legal IDs == exhaustive legal IDs
```

Cover every action type and both nested-action variants.

### 3.4 Bounds

Enforce frozen bounds:

- 64 input units;
- 16 orientation alternatives;
- 32 beam states;
- 48 complete candidates;
- 24 applications;
- depth 6;
- current Program ABI maximum roots of 8;
- admission proof with at least 3 roots.

Budget exhaustion remains a typed frontier; no fallback.

## Exit criteria

- Every action has positive and negative legality tests.
- Masker/exhaustive parity is proven on generated small contexts.
- Legality is pure, deterministic, bounded, and context-local.
- No ref-name inspection or authority scan exists.

## Suggested commit

```text
feat: complete context-local R2 action legality
```

---

# Task 4 — Replace the flat bootstrap proposer with bounded recursive composition

## Goal

Construct authentic recursive Program ABI 2 candidates from one immutable `ProposalContext`.

## Files

Modify:

- `src/cemm_authoritative_hybrid/proposal.py`
- possibly `src/cemm_authoritative_hybrid/config.py` only if an already-authorized bound is not exposed
- `tests/test_bootstrap_proposer.py`

Create:

- `tests/test_r2_recursive_proposer.py`
- `tests/test_r2_proposer_bounds.py`
- `tests/test_r2_proposer_determinism.py`

## Work

### 4.1 Search strategy

Use deterministic bounded beam search or deterministic bounded DFS over legal prefixes.

Each state should contain only:

- action prefix;
- local node table;
- source/contribution consumption state;
- partial root/parent topology;
- exact fixed-point score;
- provenance refs;
- budget counters.

Do not invoke VERIFY inside PROPOSE.

### 4.2 Candidate construction

Generate alternatives for:

- designation/frame selections;
- several applications;
- grounded role bindings;
- reference bindings;
- proposition-valued role nesting;
- expression links;
- scopes;
- binders;
- transitions;
- explicit root sets;
- exact source assignments.

The proposer must not stop after the first complete frame.

### 4.3 Root derivation

Program `root_refs` remain part of the completed program header, not a new switch action.

Derive candidate roots from declared nodes with no semantic parent after:

- proposition role parenting;
- link operands;
- scope wrapping;
- binder wrapping.

Validate and preserve the exact root set in proposer order or a reviewed deterministic topology order. Do not sort by ref as semantic policy.

### 4.4 Scoring

Use exact fixed-point integers only.

Score may combine current-cycle evidence quality and reviewed structural compatibility, but cannot:

- call the verifier;
- use gold labels;
- inspect internal ref spelling;
- sum scores from duplicate derivations after verification;
- create authority.

### 4.5 Abstention and truncation

Return explicit abstention when:

- no mode/frame exists;
- critical evidence cannot be consumed;
- no complete legal candidate exists.

Set `truncated=True` only when a real search bound prevents exhaustive completion. A truncated proposal cannot become a selected meaning.

### 4.6 Required proposer canaries

Construct from real context:

- two independent applications;
- a three-root program;
- attributed speech with proposition content;
- scoped negation;
- a query binder;
- coordination of three operands;
- a reviewed transition hint;
- all five operators and four modes across the matrix.

## Exit criteria

- No valid recursive canary requires hand-injected programs.
- Same context/config produces byte-identical proposal output.
- Search stays within bounds.
- Every candidate is canonical Program ABI 2.
- PROPOSE never imports or invokes exact verification.

## Suggested commit

```text
feat: construct bounded recursive R2 programs
```

---

# Task 5 — Complete the total recursive Semantic Expression compiler

## Goal

Remove the R1-only compiler restrictions and lower every admitted R2 action exactly.

## Files

Modify:

- `src/cemm_authoritative_hybrid/expressions.py`
- `tests/test_semantic_expression_compiler.py`
- `tests/test_compilation_proof_abi1.py`

Create:

- `tests/test_r2_recursive_compiler.py`
- `tests/test_r2_expression_canonicalization.py`
- `tests/test_r2_compilation_proof.py`

## Work

### 5.1 Parse the complete derivation

Build a local derivation table for:

- applications;
- ordinary role/reference bindings;
- proposition-valued role edges;
- links;
- scopes;
- binders;
- transition hints;
- declared roots.

Reject:

- duplicate local node declarations;
- undeclared references;
- duplicate role assignments;
- multiple semantic parents where forbidden;
- missing required roles;
- invalid link arity;
- invalid scope/binder target;
- unbound variable;
- unreachable node;
- cycle;
- excess depth or count.

### 5.2 Lower applications

For each application:

- resolve its exact frame;
- retain the persistent operator and predicate identity;
- bind reviewed derived roles;
- lower grounded refs, literals, variables, unresolved fillers, and expression-node fillers;
- preserve qualifiers separately from core roles where the frame contract requires it.

### 5.3 Lower proposition roles and links

- `bind_nested_application("role", ...)` becomes an `ApplicationFiller`.
- `bind_nested_application("link", ...)` becomes one `ExpressionLink`.
- Ordered links retain operand order.
- Only reviewed-commutative links canonicalize operands.
- Link-local refs remain derivation-local and are alpha-normalized in expression identity.

### 5.4 Lower scopes

- Create `ScopeOperator` nodes with reviewed operator/value refs.
- Preserve nesting order where it changes meaning.
- Normalize only distinctions explicitly authorized by the ABI.
- Negation must already be normalized as polarity.

### 5.5 Lower variables

- Create exact `VariableBinder` nodes.
- Ensure every bound-variable filler resolves to one enclosing binder.
- Alpha-normalize variable names only through a proven bijection.
- Preserve binder nesting and body structure.

### 5.6 Transition proof treatment

`propose_transition`:

- validates the exact transition slot and source application;
- contributes a proof translation row;
- enters `VerifiedMeaning` lineage through proof/grounding as appropriate;
- does not create another semantic application;
- does not alter expression identity unless transition semantics are independently represented in the expression by ordinary five-operator content.

### 5.7 Multiple roots

Compile the exact non-empty root set, supporting at least three roots and no more than the existing ABI bound.

### 5.8 Complete proof

`CompilationProof` must contain exactly one row for:

- every program action;
- every source assignment;
- every declared root.

No proof row may be missing, duplicated, or target an undeclared compiled artifact.

## Exit criteria

- No valid R2 action returns `action_shape_not_admitted`.
- The old R1 negative canary is replaced by positive R2 compilation tests.
- Equivalent derivations share one expression identity.
- Semantic pointer/role/order/scope changes change identity correctly.
- Compiler returns typed semantic failures; programming exceptions propagate.

## Suggested commit

```text
feat: compile complete recursive R2 expressions
```

---

# Task 6 — Complete independent verifier reconstruction

## Goal

Ensure VERIFY proves the program-to-expression mapping independently rather than merely validating compiler output.

## Files

Modify:

- `src/cemm_authoritative_hybrid/verifier.py`
- `src/cemm_authoritative_hybrid/coverage.py` only for exact recursive assignment validation
- `tests/test_exact_verifier.py`
- `tests/test_adversarial_programs.py`

Create:

- `tests/test_r2_independent_reconstruction.py`
- `tests/test_r2_recursive_corruptions.py`
- `tests/test_r2_expression_ambiguity.py`

## Work

### 6.1 Keep compiler and verifier algorithms separate

The verifier may invoke the canonical compiler to obtain the proposed compiled artifact, but it must also reconstruct expected semantic structure through a separately implemented verification path.

It must not:

- call the compiler twice and compare outputs;
- reuse compiler-private topology tables as independent evidence;
- trust `root_refs`, source criticality, or proof rows without recomputation.

### 6.2 Independently reconstruct graph laws

Recompute:

- exact selected mode/context;
- designation and frame lineage;
- application and role map;
- proposition parent cardinality;
- scope/link/binder graph;
- transition linkage;
- root set;
- reachability;
- acyclicity;
- maximum depth;
- application/root/action counts;
- state dimension/value compatibility;
- event signature and transition compatibility.

### 6.3 Recompute source coverage

Validate:

- every exact context source unit appears once;
- every contribution slot exists;
- every assignment points to the correct action/role;
- residual kind and criticality match the context;
- connector/scope/query evidence is assigned to the structural action that consumed it;
- no assignment is synthesized or repaired.

### 6.4 Compare exact semantic content

Compare the canonical compiler expression with the independent reconstruction by exact `expression_ref` and complete canonical content.

Mismatch must produce a typed verification error such as:

```text
independent_expression_mismatch
compilation_proof_domain_mismatch
root_reconstruction_mismatch
```

### 6.5 Corruption matrix

Reject at the earliest correct owner:

- unknown context slot;
- stale revision;
- forged action/program/candidate/proof refs;
- missing/duplicate role;
- wrong filler kind;
- unknown or duplicate local node;
- nested role into a non-proposition role;
- duplicate proposition parent;
- cycle;
- unreachable node;
- unbound variable;
- invalid link arity;
- ordered operand swap where semantics changes;
- illegal commutative declaration;
- invalid scope value;
- state dimension/value mismatch;
- transition frame/mode mismatch;
- missing/duplicate source assignment;
- false residual criticality;
- excess action/application/root/depth bound;
- truncated proposal with otherwise valid candidates.

### 6.6 Expression-grouped ambiguity

Verify:

- several derivations of one expression count as one semantic contender;
- scores are not summed across duplicate derivations;
- two distinct expressions within margin yield `ambiguous`;
- distinct expressions outside margin yield the unique highest-ranked expression;
- tie breaking remains deterministic and rank-aware.

## Exit criteria

- Independent corruption tests fail when either compiler or verifier is monkeypatched to accept a bad structure.
- Every accepted candidate carries canonical expression, coverage, proof, and complete lineage.
- No verification repair path exists.
- No proposal score/logit influences legality.

## Suggested commit

```text
feat: independently verify recursive R2 meaning
```

---

# Task 7 — Activate the R2 transition-preview boundary without crossing into R3

## Goal

Prove transition structures are compositional and safe while retaining effect ownership for R3.

## Files

Modify:

- `src/cemm_authoritative_hybrid/state.py` only if preview semantics require correction
- `src/cemm_authoritative_hybrid/proposal_context.py`
- `src/cemm_authoritative_hybrid/expressions.py`
- `src/cemm_authoritative_hybrid/verifier.py`
- `tests/test_transition_simulation.py`

Create:

- `tests/test_r2_transition_action.py`

## Work

- Construct `propose_transition` only from reviewed transition slots.
- Bind the transition slot to the exact source application frame.
- Validate compatible mode and required event roles.
- Retain capability/permission/adapter requirements as reviewed lineage, not as authorization.
- Compile the action into proof only.
- Verify transition preview and sequence composition are pure.
- Verify preview/precondition failure does not mutate revisions.
- Keep `TransitionEngine.commit()` and all world mutation tests inactive until R3.
- Add a static check that no R2 owner calls transition commit or `EffectGateway`.

## Exit criteria

- Valid transition hints survive verification.
- Invalid frame/mode/precondition structures are rejected.
- No R2 runtime or test performs a durable transition.
- The same program without the transition hint has the same canonical expression when no ordinary semantic content differs, but different proof/program lineage.

## Suggested commit

```text
feat: admit proof-only R2 transition proposals
```

---

# Task 8 — Prove the authentic public runtime boundary

## Goal

Demonstrate that real recursive evidence travels through the sole public path and stops truthfully before R3.

## Files

Modify narrowly if required:

- `src/cemm_authoritative_hybrid/runtime.py`
- `src/cemm_authoritative_hybrid/bootstrap.py`

Create:

- `tests/test_r2_runtime_boundary.py`
- `tests/test_r2_recursive_public_path.py`

## Work

### 8.1 Public-path canaries

Using the real development composition root, process inputs that yield:

- a flat selected expression;
- a nested proposition expression;
- a multi-root expression;
- a scoped expression;
- a query binder;
- a transition-hint expression;
- a typed unknown frontier;
- a true expression-level ambiguity.

### 8.2 Exact stop behavior

For selected meaning:

- ORIENT, PROPOSE, and VERIFY receipts are present;
- `selected_meaning` is complete;
- the cycle stops with `LaterOwnerNotAdmitted(contract:r3:evaluate)`;
- EVALUATE/EFFECT/REALIZE artifacts are absent;
- no surface response is fabricated.

### 8.3 Identity and mutation invariants

- Same context object identity reaches PROPOSE and VERIFY.
- Trace on/off does not alter semantic cycle identity.
- No world/effect revision changes.
- Session focus is not updated.
- Programming errors propagate.

## Exit criteria

- No fixture proposal or direct hand-injected program is required for the public-path positive canaries.
- All public outcomes are typed and reproducible.
- Runtime remains a single path.

## Suggested commit

```text
test: prove authentic recursive R2 runtime boundary
```

---

# Task 9 — Add the complete R2 acceptance matrix

## Goal

Turn the governing R2 contract into explicit, non-vacuous coverage evidence.

## Files

Create:

- `tests/test_r2_operator_mode_matrix.py`
- `tests/test_r2_action_matrix.py`
- `tests/test_r2_topology_matrix.py`
- `tests/test_r2_scope_link_matrix.py`
- `tests/test_r2_language_invariance.py`
- `tests/test_r2_phase_integration.py`
- `tests/test_r2_structure.py`

## Required positive matrix

### Operators

- designation
- type
- relation
- state
- event

### Modes

- OBSERVE
- QUERY
- REQUEST
- SIMULATE

### Actions

Each of the twelve actions must occur in at least one accepted authentic candidate. Both variants of `bind_nested_application` must occur.

### Topology

- one application;
- two applications;
- three or more applications;
- one root;
- two roots;
- at least three roots;
- proposition nesting;
- scope over application;
- scope over link;
- binder over application;
- binder over scoped/link body;
- depths from 1 through the configured maximum;
- maximum valid application/root/action cases.

### Links

- coordination;
- conjunction;
- disjunction;
- condition;
- cause;
- purpose;
- contrast;
- sequence;
- ordered versus reviewed-commutative identity behavior;
- multioperand coordination and sequence.

### Fillers and context

- grounded reference;
- participant/deictic reference;
- literal string;
- literal integer;
- literal boolean;
- bound variable;
- proposition/application filler;
- typed unresolved noncritical filler if the contract admits one;
- transition hint.

### Language/invariance

- English;
- one second reviewed language;
- unseen reviewed synonym;
- word-order alternative that preserves meaning;
- derivational reorder that preserves expression;
- internal ref renaming that does not affect semantics or legality;
- no raw-surface semantic dispatch.

## Required negative matrix

- unknown/fabricated ref;
- wrong semantic kind;
- stale revision;
- duplicate/missing role;
- duplicate parent;
- cycle;
- unreachable node;
- excess depth;
- excess applications;
- excess roots;
- bad link arity;
- illegal commutativity;
- ordered operand swap;
- invalid scope value;
- invalid nested role;
- unbound variable;
- duplicate binder;
- transition mismatch;
- state dimension/value mismatch;
- missing/duplicate source coverage;
- critical residual;
- forged proof;
- truncated proposal;
- budget exhaustion;
- unknown designation without manufactured identity.

## Structural source scan

`test_r2_structure.py` must reject:

- the compiler’s `_R2_ONLY_ACTIONS` restriction;
- single-application/single-root R1 error strings in active compilation;
- phrase family or raw text routing;
- authority-wide enumeration in proposer/verifier/mask;
- verifier calls from proposer;
- direct transition/effect commits in R2 owners;
- duplicate public program/expression/result classes;
- R3-R8 imports in the normal R2 owner graph.

## Exit criteria

- Every governing requirement maps to at least one exact test node.
- No denominator is empty.
- Every matrix row identifies the owner it proves.
- Test metadata is literal and governed.

## Suggested commit

```text
test: cover complete R2 recursive semantic matrix
```

---

# Task 10 — Build and run the governed R2 validation DAG

## Goal

Create one bounded, dependency-aware R2 gate and formally admit the completed phase.

## Files

Modify:

- `configs/validation_gates.json`
- validation dependency manifest/config inputs
- test metadata for new R2 nodes

Create:

- `tests/test_r2_validation_gate.py`
- optional dedicated `r2_structure` handler if not expressed as exact pytest nodes

Generated only after clean admission:

- `artifacts/validation/runs/<run-ref>.json`
- append-only R2 row in `governance/replay_status.jsonl`

## Required owner groups

Recommended owner selectors:

```text
form-context
recursive-composer
expression-compiler
exact-verifier
runtime-boundary
```

### `form-context`

Covers:

- forms;
- grounding;
- affordances/contributions;
- proposal context;
- literals;
- multilingual evidence;
- unknown frontier.

### `recursive-composer`

Covers:

- complete action legality;
- masks;
- recursive bootstrap proposer;
- bounds and determinism.

### `expression-compiler`

Covers:

- all action lowering;
- canonicalization;
- proof completeness;
- multi-root/nested structures.

### `exact-verifier`

Covers:

- independent reconstruction;
- coverage;
- corruption matrix;
- ambiguity grouping.

### `runtime-boundary`

Covers:

- sole public path;
- authentic recursive canaries;
- exact R3 stop;
- no mutation;
- exception propagation.

## Required phase selector

`r2_phase_tests` should cover only cross-owner integration and remain disjoint from owner nodes.

## Required admission graph

```text
governance
→ source_compile
→ authority_link
→ pytest_active
→ r2_structure
→ sqlite_activation
```

The admission tier must:

- collect the exact governed active set;
- reject missing, extra, duplicate, skipped, xfailed, or xpassed nodes;
- execute the active set once;
- bind exact source, authority, configuration, predecessor, test-set, and artifact identities;
- record wall time, peak RSS, and slowest cases.

## Admission procedure

1. Commit all deterministic source, tests, authority, and validation inputs.
2. Ensure the working tree is clean.
3. Run one fresh R2 admission.
4. Inspect the complete receipt.
5. Generate the dry-run R2 green status row.
6. Append exactly that row using its expected `record_ref`.
7. Verify the entire replay chain.
8. Commit only the generated receipt and ledger append in an evidence commit.
9. Integrate with history-preserving fast-forward or merge.

## Required final effective state

```text
G0 = green
R1 = green
R2 = green
R3 = red
R4 = red
R5 = red
R6 = red
R7 = red
R8 = red
```

## Suggested commits

Candidate source commit:

```text
feat: complete canonical hybrid replay R2 candidate
```

Evidence commit:

```text
chore: admit canonical hybrid replay R2
```

---

## 8. Recommended file-change map

### Production files expected to change

```text
hybrid_mvp/src/cemm_authoritative_hybrid/forms.py
hybrid_mvp/src/cemm_authoritative_hybrid/proposal_context.py
hybrid_mvp/src/cemm_authoritative_hybrid/proposal.py
hybrid_mvp/src/cemm_authoritative_hybrid/expressions.py
hybrid_mvp/src/cemm_authoritative_hybrid/coverage.py
hybrid_mvp/src/cemm_authoritative_hybrid/verifier.py
hybrid_mvp/src/cemm_authoritative_hybrid/runtime.py          # only if boundary wiring needs correction
hybrid_mvp/src/cemm_authoritative_hybrid/bootstrap.py        # only composition-root wiring
hybrid_mvp/src/cemm_authoritative_hybrid/state.py            # preview-only corrections
hybrid_mvp/data/languages/en/forms.json
hybrid_mvp/data/languages/<second-language>/forms.json
hybrid_mvp/configs/validation_gates.json
```

### Existing tests expected to be repaired

```text
hybrid_mvp/tests/test_form_lattice.py
hybrid_mvp/tests/test_grounding.py
hybrid_mvp/tests/test_program_abi.py
hybrid_mvp/tests/test_action_masks.py
hybrid_mvp/tests/test_exact_verifier.py
hybrid_mvp/tests/test_adversarial_programs.py
hybrid_mvp/tests/test_bootstrap_proposer.py
hybrid_mvp/tests/test_coverage.py
hybrid_mvp/tests/test_semantic_expression_compiler.py
hybrid_mvp/tests/test_transition_simulation.py
```

### New tests expected

```text
hybrid_mvp/tests/test_r2_plan_contract.py
hybrid_mvp/tests/test_r2_test_integrity.py
hybrid_mvp/tests/test_r2_unknown_frontier.py
hybrid_mvp/tests/test_r2_structural_slots.py
hybrid_mvp/tests/test_r2_multilingual_forms.py
hybrid_mvp/tests/test_r2_literal_pointers.py
hybrid_mvp/tests/test_r2_legal_action_matrix.py
hybrid_mvp/tests/test_r2_prefix_corruption.py
hybrid_mvp/tests/test_r2_recursive_proposer.py
hybrid_mvp/tests/test_r2_proposer_bounds.py
hybrid_mvp/tests/test_r2_proposer_determinism.py
hybrid_mvp/tests/test_r2_recursive_compiler.py
hybrid_mvp/tests/test_r2_expression_canonicalization.py
hybrid_mvp/tests/test_r2_compilation_proof.py
hybrid_mvp/tests/test_r2_independent_reconstruction.py
hybrid_mvp/tests/test_r2_recursive_corruptions.py
hybrid_mvp/tests/test_r2_expression_ambiguity.py
hybrid_mvp/tests/test_r2_transition_action.py
hybrid_mvp/tests/test_r2_runtime_boundary.py
hybrid_mvp/tests/test_r2_recursive_public_path.py
hybrid_mvp/tests/test_r2_operator_mode_matrix.py
hybrid_mvp/tests/test_r2_action_matrix.py
hybrid_mvp/tests/test_r2_topology_matrix.py
hybrid_mvp/tests/test_r2_scope_link_matrix.py
hybrid_mvp/tests/test_r2_language_invariance.py
hybrid_mvp/tests/test_r2_phase_integration.py
hybrid_mvp/tests/test_r2_structure.py
hybrid_mvp/tests/test_r2_validation_gate.py
```

The list may be coalesced where a smaller number of focused files preserves literal ownership and keeps test modules manageable. Do not create one giant R2 test file.

---

## 9. Performance and anti-bloat requirements

R2 must preserve the frozen normal-cycle bounds:

| Bound | Maximum |
|---|---:|
| Input units | 64 |
| Designation candidates per span | 8 |
| Affordance profiles per target | 4 |
| Orientation alternatives | 16 |
| Beam states per step | 32 |
| Complete candidates | 48 |
| Semantic applications | 24 |
| Graph depth | 6 |
| Program roots | existing ABI bound of 8 |
| Operation re-entry | not active in R2 |
| Pending learning obligation | not active in R2 |

Additional requirements:

- Context builds each lookup index once.
- Proposer states do not copy the complete context at every expansion.
- Compiler and verifier use bounded local maps, not repeated linear tuple scans.
- No normal cycle imports validation, corpus, training, evaluation, or Torch.
- No recursive algorithm is exponential without a hard beam/state/application bound.
- Admission reports slowest tests and peak RSS; unexplained regressions are investigated rather than hidden by raising budgets.

---

## 10. Resolved implementation decisions

These decisions should not be reopened during implementation unless a higher-priority authority conflict is discovered.

### 10.1 Root count

- Retain the current Program ABI maximum of 8 roots.
- R2 admission must positively demonstrate at least 3 roots.
- No ABI version change is needed.

### 10.2 Root ownership

- `root_refs` remain part of the completed program, not a thirteenth action.
- Proposer derives them from topology.
- Compiler lowers them.
- Verifier independently reconstructs and compares them.

### 10.3 Transition identity

- A transition proposal is proof/decision lineage.
- It does not create a persistent operator or extra expression node.
- Direct commit remains R3.

### 10.4 Unknown critical evidence

- Critical unknown evidence cannot be accepted as settled meaning.
- Default behavior is explicit proposal abstention/frontier.
- An unresolved filler is allowed only where an exact role contract explicitly permits unresolved semantic content and VERIFY retains it as unresolved, not grounded truth.

### 10.5 Compiler independence

- Compiler and independent verifier reconstruction must use separate algorithms/data flows.
- Shared immutable ABI types and context indexes are allowed.
- Shared semantic reconstruction implementation is not.

### 10.6 Candidate order

- Preserve proposer rank/order.
- Do not sort candidates by program ref.
- Expression grouping occurs in VERIFY.

### 10.7 Neural work

- No neural proposer is required for R2 green.
- The deterministic proposer is the admitted R2 construction instrument.
- Production neural selection remains R5.

### 10.8 Corpus work

- No bootstrap output becomes semantic gold.
- R2 canaries are executable tests, not R4 corpus authority.

---

## 11. Definition of done

R2 is complete only when all boxes below are true.

### Code

- [ ] Valid recursive actions no longer hit the R1 `action_shape_not_admitted` restriction.
- [ ] Bootstrap proposer constructs authentic recursive candidates from real context.
- [ ] Compiler lowers all admitted R2 actions.
- [ ] Verifier independently reconstructs complete recursive meaning.
- [ ] Coverage validates structural source consumption exactly.
- [ ] Expression ambiguity is grouped by canonical meaning.
- [ ] Runtime reaches selected recursive `VerifiedMeaning` through the sole public path.
- [ ] Runtime stops exactly at the R3 boundary.
- [ ] Transition hints do not mutate state.
- [ ] No ABI or alternate runtime is introduced.

### Tests

- [ ] Every due R2 predecessor node is active or validly superseded.
- [ ] Every R2 rewrite obligation has complete successor nodes.
- [ ] No R2 test is vacuous or stale.
- [ ] Five operators are positively covered.
- [ ] Four modes are positively covered.
- [ ] Twelve actions and both nested variants are positively covered.
- [ ] At least three roots are positively covered.
- [ ] Depth, scope, links, binders, references, literals, and transitions are covered.
- [ ] Multilingual and unseen-synonym canaries pass.
- [ ] Full recursive corruption matrix passes.
- [ ] Zero active skips, xfails, xpasses, collection errors, missing, extra, or duplicate nodes.

### Governance

- [ ] R2 validation DAG exists and is bounded.
- [ ] One clean committed R2 candidate is admitted.
- [ ] Receipt binds exact source and admitted R1 predecessor.
- [ ] All technical steps pass.
- [ ] Ledger appends exactly one R2 green consumer row.
- [ ] Chain verification passes.
- [ ] R3-R8 remain red.

---

## 12. Immediate first implementation slice

The safest first coding slice after this plan is approved is:

1. repair the R2 test lifecycle;
2. add the missing unknown-frontier successor;
3. add positive failing tests for:
   - two applications;
   - three roots;
   - nested proposition role;
   - one scope;
   - one link;
   - one variable;
   - one transition hint;
4. run the diagnostic R2 owner set;
5. implement the complete legal action relation;
6. then extend proposer, compiler, and independent verifier in that order.

This sequencing prevents the existing broad but partially vacuous test suite from falsely reporting R2 progress and ensures each later owner receives a valid artifact from its predecessor.
