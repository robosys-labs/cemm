# CEMM Native Semantic Spine — Complete Implementation Plan

**Target branch:** `agent/atomic-graph-repair`  
**Pinned preimage:** `8f6edbf6fdf476ccd2fb5e5ca2398c99e6ccecc6`  
**Cutover:** transactional, source-and-generated-assets together  
**Kernel:** unchanged five-operator ABI

This plan is implemented by `install_native_semantic_spine.py`. The phases are separated by ownership so they can be reviewed independently, but they are activated only as one release. Partial installation is not supported.

## Shared invariants

Every phase must preserve all of the following:

- semantic identity is distinct from language form;
- only `op:designation`, `op:type`, `op:relation`, `op:state`, and `op:event` are kernel applications;
- pre-core language processing proposes evidence and alternatives but owns no semantic truth;
- designation lookup remains N-best;
- every consumed unit has one semantic role and every remainder is typed;
- learned designations become compositionally useful without form-pack regeneration;
- no unknown form defaults to `concept`;
- no runtime meaning decision inspects raw surface strings;
- authority is linked and validated before durable import;
- normal turns remain bounded and indexed;
- source changes require process restart.

## Phase 0 — Contract alignment and inventory

### 0A. ABI alignment

- Set Coverage/Form ABI to 6 across active code and documentation.
- Introduce Semantic Contribution ABI 1.
- Introduce Learning Plan ABI 1.
- Introduce Proposition Graph ABI 1.
- Make activation fail when code, generated pack, receipt, or authority disagree.

### 0B. Semantic-protocol inventory

Inventory and classify every occurrence of:

- `semantic_port`;
- `learning_operation` and `resolve_designation`;
- open-class entries in `function_forms`;
- event/capability duplicate designations;
- generated internal-ref labels;
- query/discourse qualifiers;
- phrase-specific semantic branches.

### 0C. Release gate

- Pin repository, branch, HEAD, and every modified preimage blob.
- Require a clean checkout.
- Reject all unreviewed changed paths.

**Implemented by:** governing documents, activation checks, installer preimages, legacy-protocol scan.

## Phase 1 — Semantic Contribution ABI

### 1A. Closed transient model

Implement the bounded contribution kinds:

- anchor;
- predicate;
- binder;
- reference;
- scope;
- discourse;
- connector;
- qualifier;
- literal;
- open variable.

### 1B. Semantic-kind defaults

Derive safe default affordances from the exact target kind:

- entity-like target → argument anchor;
- concept → class predicate and concept anchor;
- event type → event predicate and event-type anchor;
- relation type → relation predicate and relation anchor;
- state dimension → dimension predicate and anchor;
- value → value anchor, plus state predicate only with exactly one reviewed dimension;
- label type → designation-property predicate and anchor;
- capability → capability target and anchor.

### 1C. Explicit frame authority

- Load generation-pinned `rel:has_semantic_frame` links.
- Validate roles, filler kinds, ports, bounds, kernel lowering, and replace/augment policy.
- Permit safe kind defaults for learned world atoms while requiring authority scope for explicit frame contracts.

### 1D. Bounds

- At most four profiles per target in the active form processor.
- At most sixteen ports and twelve roles per frame.
- Malformed ports or roles fail activation.

**Owned files:** `cemm/semantic_contributions.py`, `cemm/native_semantic_validation.py`, `cemm/activation.py`.

## Phase 2 — Form grounding and atomic graph integration

### 2A. Designation expansion

For each designation candidate:

1. retain target, label, context, span, score, and provenance;
2. resolve bounded affordance profiles from the target;
3. create separate semantic candidate alternatives;
4. merge contribution features without replacing language evidence.

### 2B. Open-class boundary

- Open-class lexemes in the form pack provide morphology and non-semantic provenance only.
- Without a designation candidate, an open-class form remains a critical unknown.
- Open-class forms are removed from `function_forms`.

### 2C. Dynamic graph ports

- Merge schema ports, projected ports, and contribution ports.
- Treat unassigned learned predicates as critical residuals.
- Preserve full coverage and provenance receipts.

### 2D. Lattice and ellipsis repair

- Retain the atomic-graph clause/preamble selection fixes.
- Preserve contextual designation-property projection and bounded ellipsis.
- Do not let a grounded leading clause poison a valid query clause.

**Owned files:** `cemm/forms.py`, `cemm/atomic_graph.py`, `cemm/form_algebra.py`.

## Phase 3 — Native frame and learning authority

### 3A. One authority owner

`cemm/data/conversation_foundation.json` is the sole owner of conversational frames and learning contracts. There is no sidecar semantic-spine authority file.

### 3B. Reviewed semantic frames

Seed compact frames for:

- learn;
- teach;
- remember;
- forget;
- define;
- want;
- intend;
- know;
- say;
- translate;
- infer;
- greeting and reaction discourse.

### 3C. Typed learning contract

Seed and validate:

- `contract:designation_learning`;
- `contract:designation_target_answer`;
- `goal:acquire_designation`;
- capability licensing through `rel:licenses_learning_contract`;
- exact commit operator `op:designation`;
- bounded target kinds and licensed query kinds.

### 3D. Explicit language publication

- Remove automatic internal-ref-name lexicalization.
- Publish only reviewed designations.
- Keep verb event senses distinct from nominal capability labels.
- Publish a finite reviewed English inflection bootstrap because the current pre-core has no morphology-to-lemma identity resolver.
- Keep frame/contract/internal relations non-user-visible.

### 3E. Deterministic generation

Generate `conversation_foundation.json` twice and require byte identity.

**Owned files:** `tools/generate_conversation_foundation.py`, `cemm/data/conversation_foundation.json`.

## Phase 4 — Typed learning plans and dialogue continuation

### 4A. Exact plan identity

A `LearningPlan` binds:

- one reviewed contract;
- one exact executed query structure and query ref;
- one query kind;
- one pinned authority generation;
- one unresolved surface and language;
- one goal, capability, commit operator, and answer contract;
- bounded target kinds;
- known bindings and span/candidate provenance;
- expiry;
- later, exact response and goal provenance.

The plan ref is derived from the complete semantic payload; tampering fails reconstruction.

### 4B. Query-result handoff

- Interpreter emits only a contract candidate and exact probe query.
- Runtime creates the plan only after Stage 10 executes that exact query.
- Candidate target kinds are intersected with the contract rather than broadening it.
- Goal arbitration accepts exactly one query-bound plan.

### 4C. Response and common ground

- Response CSIR carries the complete typed plan.
- Response construction verifies plan/query ref, query kind, exact probe query, and surface.
- Dialogue opens one pending obligation only after verified realization.
- Dialogue rechecks the realized response query against the plan.

### 4D. Commit and invalidation

- Stage 13 accepts exactly one licensed application and rechecks the plan against the runtime authority-generation pin.
- Designation surface, label family, language, target, target kind, obligation, and plan ref are verified before commit.
- Obligation consumption occurs only after the Stage-13 receipt.
- Authority reload invalidates any plan licensed against the previous generation.

**Owned files:** `cemm/learning_plans.py`, `cemm/dialogue.py`, `cemm/interpreter.py`, `cemm/goals.py`, `cemm/runtime.py`, `cemm/response.py`, `cemm/reference.py`.

## Phase 5 — Generic proposition, capability, predication, and discourse competence

### 5A. Proposition graph

- Represent nesting with bounded graphs of ordinary five-operator applications.
- Use explicit event refs and role-addressed complements.
- Reject cycles, more than twenty-four applications, or depth above six.

### 5B. Capability inventory

`What can X do?` compiles to:

1. query X's type;
2. query capabilities entitled to that type;
3. project capability refs;
4. preserve the target in query qualifiers and Response CSIR.

No capability phrase intent or response fallback is introduced.

### 5C. Embedded desire and knowledge

`Do you want to know my name?` compiles to two event restrictions with explicit complement refs and a designation target encoded through ordinary semantic roles.

### 5D. Meaning continuation and direct definition

- `It means Y` uses pending dialogue context and commits one designation.
- `X means Y` uses the same `op:designation` substrate without pending state.
- The predicate is the semantic target `event:define`, not a language-pack port string.

### 5E. Generic predication

- Binder evidence never independently chooses an operator.
- Target affordance selects type/state/relation/designation/event semantics.
- A value becomes a bare state predicate only when exact authority identifies one dimension.

### 5F. Discourse reaction

- `wow lol` composes a reviewed reaction/acknowledgment without asserting world state.

**Owned files:** `cemm/propositions.py`, training seed, form-pack generator, language-pack migration, response grammar.

## Phase 6 — Data cleanup and deterministic generated assets

### 6A. Remove legacy semantic shortcuts

- Remove `semantic_port` from active supervision and generated packs.
- Remove `learning_operation` and `resolve_designation` from active runtime, supervision, and generated packs.
- Replace open-class semantic feature lookups with semantic anchor captures.

### 6B. Kernel role extension

Add only the optional event roles required for proposition complements:

- `role:object`;
- `role:target`.

No new operator is introduced.

### 6C. Source-of-truth migration

Migrate together:

- `base.json`;
- `en_form_schema_seed.json`;
- `generate_en_form_pack_v6.py`;
- generated `en.json` form pack;
- English language pack and response grammar.

### 6D. Reproducibility

- Run foundation generator twice.
- Run form generator twice.
- Run language generation/migration twice.
- Require identical manifests.

**Owned files:** asset migrations and generated data/packs.

## Phase 7 — Activation, testing, transactional cutover

### 7A. Activation

Attest:

- ABI 6/1/1/1;
- graph-matcher receipt;
- package-local module provenance and hashes;
- authority frames/contracts and licensing;
- absence of legacy protocol fields.

### 7B. Test matrix

The installed checkout must pass:

- authority ownership and linking validators;
- syntax validator;
- semantic-operational contract validator;
- focused native-spine black-box tests;
- the complete repository `pytest -q` suite.

### 7C. Transactional installer

The installer:

1. acquires an exclusive install lock;
2. verifies origin, branch, HEAD, clean status, and every preimage blob;
3. creates a detached staging worktree;
4. applies source/data migrations;
5. regenerates all derived artifacts deterministically;
6. validates authority and starts a temporary runtime;
7. runs focused and full suites;
8. rejects paths outside the allowlist;
9. snapshots only installer-owned target paths;
10. copies byte-identical validated files;
11. repeats validation on the target;
12. restores only installer-owned paths on failure;
13. writes an install receipt on success.

It has no skip-test, force, partial, or source-drift option.

## Completion definition

Implementation is complete only when the transactional installer exits successfully on the exact pinned checkout and produces `native-semantic-spine-install-receipt.json`. A bundle-level test pass proves installer/module integrity; it is not a substitute for the checkout's full-suite receipt.


## Cross-phase isolation invariant

Realization grammar tokens are output-only and must never be fed back into pre-core form classification. Phase 2 removes the Interpreter fallback from language-pack `function_forms`/`grammar_tokens`; Phase 6 sanitizes any legacy field in generated language assets.
