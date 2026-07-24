# CEMM v3.5.1 — Phases 7–9 implementation and Phase 0–6 corrective review

Baseline reviewed: `e09fdfd5e4db041a46165e7f3573605fbc88cacd` (`main`, “Apply phases 4-6 patches”).

This patch is governed by `AGENTS.md`, `ARCHITECTURE.md`, `CORE_LOOP.md`, `RUNTIME_PLAN.md`, `CEMM_CORE_MATHS.md`, `IMPLEMENTATION_PLAN.md`, `CORE_ISSUES.md`, and `ISSUES_TO_AVOID.md` in that order.

## Non-negotiable invariants preserved

- one public semantic brain: exact CSIR; legacy UOL is migration/shadow input only;
- exact immutable `AuthorityGeneration` per cycle;
- semantic identity is independent of lifecycle, privacy, competence, operational profiles, runtime parameter revisions, and language package revisions;
- every executable higher-order definition has finite exact dependency closure and a verifiable closure proof;
- Stage 5 accepts explicit CSIR fragments only and never duck-types legacy objects;
- grounded referent identity is distinct from state continuity, mention/coreference confidence, and epistemic admission;
- claims remain attributed/contextual and are not automatically world truth;
- English is package data, never a kernel branch;
- Stage 4 vocabulary applicability uses an authority-generation index, not a per-referent global schema scan, and builds the index outside runtime-global locks;
- normalization is reversible through preserved source evidence and correct across Unicode code-point boundaries;
- Phase 9 does not pre-implement Phase 10’s deterministic semantic composer.

---

## Phase 0–6 defects found and corrected as prerequisites

### P06-01 — Operational profile pins contaminated semantic identity — CRITICAL

Current Phase-6 canonicalization includes `SemanticApplication.operational_profile_pins` in proof-free application attributes. Rotating a lifecycle/use/permission/competence profile therefore changes semantic fingerprint even if meaning is unchanged.

**Fix:** `canonical_v351.py` creates a profile-free semantic view for semantic canonicalization and alpha-labeling, while exact/executable identity retains profile pins. Kernel semantic/canonicalization/normalizer/operations/compiler ABI revisions are bumped so cached or persisted v2 identity cannot be silently reinterpreted.

### P06-02 — Duck-typed Stage-5 legacy ingress — CRITICAL

`ExactCSIRCompiler._fragment()` accepts arbitrary objects exposing `to_csir_fragment()`. This is an executable wrapper path around the migration-only boundary.

**Fix:** Stage 5 now accepts only `CSIRCandidateFragment` and `CSIRGraph`. Legacy conversion lives only under `cemm.migration`.

### P06-03 — Closure-proof spoofing by string reference — CRITICAL

A non-empty `closure_proof_refs` tuple is currently enough to admit graphs with applications.

**Fix:** candidate fragments carry typed `ClosureProof` payloads separately from historical/audit refs. Stage 5 replays each proof against the exact `AuthoritySnapshotV351`, unions the proven closures to cover every executable predicate, validates concrete ports/profiles structurally against exact definitions, and keeps occurrence-specific semantic/structural fingerprints available for direct compiler-proof verification.

### P06-04 — Closure lineage detached from selected exact derivation — HIGH

Equivalent candidates currently union closure refs and then choose one exact representative, potentially attaching proofs from other derivations to the selected graph.

**Fix:** evidence and hard-constraint evidence may be unioned at semantic-class level; exact closure lineage remains attached to the exact representative it proves.

### P06-05 — Definition conservativity checked against grounded instances — CRITICAL

A higher-order definition’s expected semantic fingerprint must describe its expanded definition template, not a concrete occurrence after binding `Alice`, `Mango`, a timestamp, etc.

**Fix:** Phase 7 computes and verifies `expanded_template_semantic_fingerprint` before grounding/instantiation. Concrete candidate fingerprint remains separate.

### P06-06 — Canonical storage transitively imports quarantined UOL — CRITICAL

`storage/model.py` imports `CapabilityStatus` from `uol/model.py`, so canonical runtime storage transitively loads legacy semantic code.

**Fix:** the structural capability-status discriminator is owned by canonical storage. Action/capability concepts remain data-driven exact schema refs.

### P06-07 — Unbounded Stage-4 property scan — HIGH

The current closure compiler loops over every active property schema for every projected referent.

**Fix:** `SchemaApplicabilityIndex` is built once per immutable `AuthorityGeneration`, indexed by exact holder type, cached only for the active generation, and consumed by Stage 4.

### P06-08 — Stage-5 service could return pre-final candidates carrying only proof refs — CRITICAL

The runtime converts `CSIRCandidateSet`/`ExactCompilationResult` back to fragments after discarding typed proof payloads.

**Fix:** Stage-5 proposal services return `CSIRCandidateFragment` values with typed closure proofs. Pre-final candidate objects cannot re-authorize themselves.

### P06-09 — Split semantic authority not actually pinned into Stage 0 — CRITICAL

The runtime pins the old aggregate authority snapshot but has no distinct exact definition/profile/parameter authority artifact.

**Fix:** Stage 0 now pins `semantic_authority_snapshot_v351`. If no signed semantic-definition artifact is installed, it creates an exact empty snapshot for the same generation—honest absence, not fallback. Stage 5 receives that exact snapshot for closure validation.

### P06-10 — Reversible normalization was locally correct but globally Unicode-incorrect — HIGH

Character-by-character NFKC can differ from whole-string NFKC for combining/composition sequences.

**Fix:** normalize the whole string, retain an alignment ledger to source spans, preserve exact original text as reversal authority, and expose normalization evidence to the form lattice.

### P06-11 — Stage-4 legacy `use_profile` acted as an overarching semantic gate — HIGH

The old closure projector can suppress structurally valid candidate evidence using the bundled legacy schema use profile before exact v3.5.1 operational/use authority is consulted.

**Fix:** Stage 4 now emits structural/evidential applicability only. Executable use authority is enforced by the exact split authority pinned at Stage 0 and the Stage-5+ pipeline; the legacy profile cannot silently erase an interpretation candidate.


### P06-12 — Bare port identity can collapse exact revisions — CRITICAL

Higher-order invocation arguments cannot be keyed by a plain `port_ref`: the same textual role may exist in multiple namespaces/revisions.

**Fix:** definition invocations and root bindings use full `ExactAuthorityPin` keys `(kind, namespace, ref, revision, content_hash, scope)`.

### P06-13 — A self-consistent closure proof was not enough — CRITICAL

A typed proof object can still be fabricated around the wrong dependency universe unless replayed against the actual pinned semantic-authority snapshot.

**Fix:** `ClosureProof.verify_authority()` resolves the root again from `AuthoritySnapshotV351`, compares exact closure pins/edges/constraints, replays the expanded template, verifies ABI and conservativity, and Stage 5 requires union coverage of every executable predicate.

### P06-14 — Semantic definitions could hide undeclared exact authority — CRITICAL

A definition body can otherwise smuggle type/port/operator/profile authority that is not represented in its declared closure.

**Fix:** definition construction rejects operational-profile bundling, occurrence proof lineage, unresolved executable refs, and any exact authority pin not declared as root/dependency/formal-port/constraint authority. Semantic dependencies may be referenced without being higher-order invocations; only explicit invocations are expanded.

### P06-15 — Hard-constraint refs were opaque strings — CRITICAL

`hard_constraint_trace_refs` alone cannot prove that the current exact candidate satisfied the exact constraint closure.

**Fix:** typed `HardConstraintTrace` payloads bind the current semantic structure, exact snapshot, exact constraint set, evaluator authority and evidence; Stage 5 fails closed on missing, extra, stale or unsatisfied constraints.

### P06-16 — Exact executable authority was incomplete — CRITICAL

The architecture requires executable structures to pin operational profiles, dynamics parameters, use authorization, projection authority and other applicable exact artifacts—not only semantic closure.

**Fix:** `ExecutableAuthorityEnvelope` deterministically binds the unique exact active profile and explicit ALLOW use-authorizations, pins the active dynamics parameter set, and carries exact language/multimodal projection, causal and policy/adapter authority where applicable. A pre-pinned profile cannot bypass unique profile selection, and the runtime Stage-5 boundary—not a proposal service—requires projection authority for executable meaning derived from input evidence. Stage 5 records these pins on final candidates.

### P06-17 — Recurrent/attractor artifacts could drift from split authority — CRITICAL

Stage 6/7 artifacts only carried the aggregate authority generation/fingerprint and kernel ABI. A recurrent service could therefore return an artifact produced with different dynamics parameters or semantic split snapshot.

**Fix:** `CognitiveCyclePins`, `ActivationGraph` and `SemanticAttractorSet` carry the semantic-authority snapshot fingerprint and exact dynamics parameter pins; Stage 6/7 validate them against Stage-0 pins.

### P06-18 — A Phase-6 regression test encoded the unsafe proof-ref behavior — HIGH

The existing deduplication test expected opaque `closure_proof_refs` to survive as authorization.

**Fix:** the patch rewrites that regression case to test deduplication with non-executable term graphs; opaque proof strings remain covered only by rejection tests.

### P06-19 — Semantic unification still treated operational profile rotation as a meaning change — CRITICAL

Phase-6 `unify()` compares both the exact predicate pin and `operational_profile_pins`. After the Phase-7 authority split, this would contradict canonical semantic equivalence: two applications could have the same semantic fingerprint but fail semantic unification solely because lifecycle/use authority rotated.

**Fix:** semantic unification compares exact predicate meaning and semantic annotations only. Operational-profile/use/dynamics compatibility remains enforced by `ExecutableAuthorityEnvelope` at the execution boundary. The kernel semantic ABI is bumped accordingly.

### P06-20 — Candidate sets did not verify kernel-derived exact graph identity — CRITICAL

`CSIRCandidateSet` recomputes the semantic fingerprint but trusts `candidate.exact_fingerprint` as supplied. A forged or stale exact identity can therefore survive the ABI boundary even when the semantic graph is unchanged.

**Fix:** candidate-set validation now recomputes both semantic and exact fingerprints with the v3.5.1 canonicalizer. Stage 6 additionally replays each executable authority envelope against the pinned split snapshot, context and permission instead of trusting stored non-semantic authority refs.

---

# Phase 7 — Definition/profile/parameter authority split + exact closure compiler

## Implemented authority families

### `SemanticDefinition`
Pure meaning authority:

- exact `definition_pin`;
- CSIR definition body;
- exact formal port pins;
- exact semantic dependency pins;
- explicit higher-order invocations;
- exact constraint pins;
- reviewed expected expanded-template semantic fingerprint;
- provenance.

It does **not** contain lifecycle state, permission policy, competence promotion state, recurrent parameters, observation models, or causal transition rules.

### `OperationalProfile`
Non-semantic operational authority:

- target exact semantic definition;
- lifecycle status;
- allowed operations;
- permission scopes;
- exact competence case pins;
- exact policy pins.

Rotating this artifact does not change semantic fingerprint.

### `DynamicsParameterArtifact`
Exact recurrent dynamics parameters, independently revisioned and pinned.

### `ObservationModel`
Exact evidence/observation authority independent of semantic definition identity.

### `CausalMechanism`
Explicit participant/precondition/transition mechanism authority, separate from event lexical meaning and co-occurrence.

### `UseAuthorization`
Context/permission/use decision authority distinct from meaning and probability.

### `AuthoritySnapshotV351`
One immutable split authority snapshot pinned to the same Stage-0 `AuthorityGeneration`. Its content fingerprint is order-stable for set-like authority fields, rejects duplicate dynamics families, and exposes deterministic exact profile/use selection.

### `ExecutableAuthorityEnvelope`
Exact non-semantic authority selected for an executable candidate: operational profiles, dynamics parameters, use authorizations, language/multimodal projection authority, causal mechanisms and policy/adapter pins. Meaning equality ignores profile rotation; exact executable identity retains the selection.

## Exact closure

`DefinitionClosureResolver` performs a finite DFS over **exact pins only**:

- no `latest` lookup;
- no minimum revision for executable closure;
- semantic-definition dependencies recurse; exact type/operator/value/other semantic dependencies are verified closure leaves rather than being miscast as definitions;
- missing exact dependency fails closed;
- cycles fail closed;
- dependency order is deterministic and dependency-before-dependent with the root last;
- closure can be cached because authority generation is immutable.

`SemanticDefinitionCompiler`:

1. resolves exact least closure;
2. alpha-renames definition-local nodes deterministically;
3. recursively expands explicit higher-order invocations;
4. binds formal ports using typed CSIR substitution;
5. checks definition-level conservativity on the ungrounded expanded template;
6. binds grounded/external occurrence arguments;
7. normalizes CSIR;
8. emits `ClosureProof`.

`ClosureProof` verifies exact authority generation/snapshot, kernel/compiler/closure ABI, root definition, replayed exact closure pins/edges/constraints, expanded-template fingerprint and conservativity. Direct compiler output can additionally verify its occurrence semantic/structural fingerprint. At Stage 5, multiple typed proofs may cover one composed graph: the kernel requires the **union** of their exact closures to cover every executable predicate, then validates concrete exact ports/profiles and typed hard constraints against the current graph.

## CSIR normalization split

Semantic equivalence intentionally ignores operational profile pins. Exact executable fingerprint retains them. This fixes the semantic/non-semantic authority boundary without weakening exact runtime attestation.

---

# Phase 8 — UOL/schema → CSIR compatibility compiler + Stage-5 shadow

Implemented in `cemm/migration/v351_csir_compat.py` so the canonical runtime cannot import it under the signed denylist.

## One-way compiler

Explicit supported legacy occurrence classes are translated deterministically to exact CSIR only when exact mappings exist for:

- schemas;
- ports;
- referent types;
- scope operators;
- coordination operators;
- closure proofs verified against the pinned `AuthoritySnapshotV351`.

Legacy `MeaningSchema` authority records have a separate one-way split migration path. `LOSSLESS` requires the exact reviewed source **record fingerprint**, exact semantic-definition mapping, verified closure proof, exact operational-profile mapping, exact parent/dependency revisions, mapped ports, and equivalent effective use/lifecycle/permission/competence authority. Floating parents/dependencies, bundled constraints without exact mappings, content drift, or split-authority mismatch are classified `REQUIRES_EXPLICIT_INTERPRETATION`, never guessed. Empty or mixed authority/occurrence record groups quarantine.

There is no duck-typed conversion hook and no runtime fallback.

## Migration classifications

- `LOSSLESS`
- `REQUIRES_EXPLICIT_INTERPRETATION`
- `AMBIGUOUS`
- `DEPRECATED`
- `QUARANTINED`

Missing exact authority never floats to a latest revision. Unsupported shapes quarantine. Legacy constraints without an exact CSIR mapping require explicit interpretation. Explicitly retired records classify as deprecated.

## Stage-5 shadow comparison

`Stage5ShadowComparator` is observation-only:

- receives replay/migration legacy record groups;
- compiles them one way to normalized CSIR;
- compares semantic fingerprints against authoritative Stage-5 CSIR;
- reports match/mismatch/classification;
- cannot return or replace authoritative candidates.

**Important:** the canonical runtime deliberately does not import `cemm.migration`. Shadow execution belongs in replay/migration tooling so `CI-018` is not “fixed” by creating two brains.

---

# Phase 9A — Grounded referents and minimum semantic substrate

Implemented in `cemm/v350/grounded/model.py` as cycle-local canonical semantic structures.

Included primitives:

- semantic contexts with kind, permission scope and acyclic parent-context identity;
- referents with exact type pins;
- type assertions;
- aliases/names;
- unresolved/resolved/disputed identity candidates with independent evidence;
- properties and relations;
- entitled state variables with categorical exact pins, CSIR value refs, or finite literal candidates;
- explicit time/context records;
- participant roles;
- mentions and mention chains;
- propositions;
- attributed claims with distinct source/reported contexts;
- information gaps;
- answer projections;
- queries;
- corrections/retractions.

Key invariants:

- confidence never resolves identity by itself;
- identity continuity does not imply state continuity;
- categorical pinned state candidates must be inside enumerated entitlement; non-categorical values remain governed by the exact dimension definition;
- propositions are content, claims are attributed acts;
- source context and reported/world context are distinct semantic roles; they may legitimately reference the same context without becoming world admission;
- query variable/gap/projection are separate objects;
- correction and retraction are explicit semantic records, not text replacement hacks.

This substrate is intentionally not durable world admission. Core Stage 9 epistemic placement/admission and the later composition/discourse phases decide how cycle-local meaning becomes eligible for durable commit.

---

# Phase 9B — Minimum reviewed English package

Implemented in `cemm/v350/language/minimum_english_v351.py` as package data, not kernel branches.

Coverage includes all required families:

1. pronouns/deixis;
2. proper names;
3. determiners;
4. identity/classification;
5. property/state predication;
6. possession;
7. simple relations;
8. simple events;
9. negation;
10. modality/capability;
11. WH queries;
12. yes/no queries;
13. corrections;
14. definition/teaching;
15. greetings;
16. requests/imperatives.

The package contains:

- reviewed form seeds;
- grammatical features;
- symbolic semantic contribution slots;
- declarative construction programs expressed only through the repository's existing generic `ConstructionProgramOperation` VM primitives;
- reversible morphology rules;
- competence case refs;
- exact semantic-binding validation against the Stage-0 `AuthoritySnapshotV351`.

A package cannot activate unless its content-addressed package pin and every symbolic semantic slot resolve inside the exact pinned AuthorityGeneration. English package data cannot introduce a private pseudo-operation interpreter, and no word or phrase is interpreted by kernel `if token == ...` logic.

## Reversible normalization

`reversible_normalization.py` performs whole-input NFKC + casefold, records alignment spans/operations, preserves exact source evidence, maps normalized spans back to source, and supports exact reversal by preserved evidence.

---

# Integration boundaries deliberately not crossed

This patch does **not**:

- implement Phase 10 deterministic semantic composition execution;
- fake Phase 6 recurrent dynamics or Phase 7 attractor behavior with English rules;
- implement Phase 11 discourse/epistemic admission policies;
- close `CI-014`, `CI-016`, `CI-020`, or `CI-021` prematurely;
- add a UOL runtime fallback;
- activate English revision 3 by hand-editing the signed runtime manifest;
- rewrite the boot database manually;
- invent release attestation artifacts.

The new English package and semantic authority source must be projected into canonical boot/release artifacts by the later build/activation phases, followed by regeneration of hashes/manifest/verification report.

---


## Issue-register honesty

The apply script deliberately does **not** rewrite `CORE_ISSUES.md` statuses. `CI-017`, `CI-018`, and `CI-019` are implementation candidates for `FIXED_UNVERIFIED` only after this patch is applied to a full checkout and the required regression/shadow/architecture gates pass. This avoids converting implementation intent into a false verified status.

---

# Test additions

`tests/v350/test_v351_phase7_authority_closure.py`

- operational-profile rotation preserves semantic identity but changes exact identity;
- missing exact dependency fails closed;
- opaque string proof cannot authorize Stage 5;
- duck-typed legacy wrapper cannot enter Stage 5;
- typed closure proof is accepted only against matching exact authority snapshot;
- higher-order conservativity is definition-template-level, not concrete grounded-instance-level.

`tests/v350/test_v351_phase8_migration_shadow.py`

- unsupported legacy object quarantines;
- shadow report is observation-only;
- explicit deprecated legacy record classifies `DEPRECATED`.

`tests/v350/test_v351_phase9_grounded_english.py`

- claim attribution remains structural even when source and reported context identifiers are equal;
- query gap and answer projection remain distinct;
- high identity confidence does not resolve identity;
- minimum English package covers every required construction family;
- normalization preserves exact source reversal;
- normalization correctly composes across combining-code-point and Hangul Jamo boundaries;
- reviewed English package identity is content-addressed by an exact language-package pin.

---

# Verification required after applying

Run at minimum:

```bash
python -m compileall -q cemm tests
pytest -q tests/v350/test_v351_phase7_authority_closure.py
pytest -q tests/v350/test_v351_phase8_migration_shadow.py
pytest -q tests/v350/test_v351_phase9_grounded_english.py
pytest -q tests/v350/test_v351_phase6_csir_kernel.py
pytest -q tests/v350
```

Then run architecture scans:

```bash
rg -n "to_csir_fragment|from \.{0,2}uol|cemm\.v347|cemm\.migration" cemm/v350 cemm/app
rg -n "if .*['\"](?:how|are|you|what|who|hello|hi|name)['\"]" cemm/v350
rg -n "active_schemas\(SchemaClass\.PROPERTY\)" cemm/v350
```

Expected:

- no Stage-5 duck conversion;
- no canonical storage/runtime import of UOL;
- no canonical runtime import of migration;
- English strings only in language-package/data/test surfaces;
- no per-referent all-property vocabulary scan in Stage 4.

## Release artifact rule

The kernel ABI and source graph change. Existing signed runtime artifacts therefore become stale by design. Do not patch hashes manually. Rebuild boot artifacts, runtime-authority manifest, source-root hashes, and verification reports through the canonical release pipeline when the implementation-plan activation phase calls for it.
