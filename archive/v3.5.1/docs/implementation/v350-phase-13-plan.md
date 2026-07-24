# CEMM v3.5 Phase 13 — Learning-first promotion coordinator implementation plan

**Status:** comprehensive implementation plan; not implemented by Phase 12
**Prerequisite:** Phases 0–12 phase-verified, especially Phase-12 proof that learned/test packages can traverse generic semantic machinery without kernel edits.

## 1. Objective

Implement the authority that turns unresolved frontiers, explicit teaching, repeated grounded evidence, corrections, counterexamples, and failed competence into **reviewable semantic learning packages** that can be promoted per use without turning examples, embeddings, LLM output, or frequency into definitions automatically.

Phase 13 is the bridge between “the system can represent a learned concept” and “the system can safely acquire, verify, activate, retract, supersede, restart, and invalidate learned semantic structure.”

## 2. Governing laws

1. **Evidence is not definition.** Examples and repeated correlations support candidates; they do not become schemas automatically.
2. **Proposal is not authority.** Inducers/LLMs/statistical models may propose structures only; promotion requires deterministic validation and competence.
3. **Per-use authorization.** A package may be safe for mention/grounding while still forbidden for composition, inference, transition, operation, realization, etc.
4. **Exact dependencies.** Every promoted record pins exact required authorities/revisions or explicit authoritative-selection policies permitted by its record contract.
5. **Counterexamples survive.** Promotion never deletes contrary evidence; defeaters and unresolved conflicts remain lineage.
6. **No kernel ontology growth.** Learning a new type/event/property/state/relation/lexeme must not require Python branches/enums/templates.
7. **No hidden automatic world mutation.** Learning a transition contract does not retroactively fire historical events unless an explicit replay/revalidation policy authorizes it.
8. **Promotion is atomic CAS.** A package is validated against one snapshot and commits all mutually dependent records atomically or not at all.
9. **Retraction is lineage-aware.** Retraction/supersession invalidates dependents; it does not destructively erase history.
10. **Restart is semantic continuity.** Promoted authority must behave equivalently after restart without relying on in-memory caches.

## 3. Proposed durable record families

Exact names may be adjusted during implementation, but responsibilities must remain separate.

### 3.1 `LearningPackageRecord`

Identity and lifecycle of one promotable semantic package:

```text
package_ref
package_kind
revision / supersedes_revision
lifecycle_status
candidate_record_refs
exact_dependency_pins
frontier_refs
example_evidence_refs
counterexample_evidence_refs
competence_case_refs
requested_use_authorizations
promotion_policy_ref
review_refs
provenance / permission / sensitivity
```

The package is an envelope; it must not duplicate the semantic content of the records it proposes.

### 3.2 `LearningFrontierRecord`

Durable unresolved need:

```text
frontier_ref
frontier_kind
origin_cycle/stage
required_structure_classes
known_constraints
candidate_refs
missing_dependency_refs
question/teaching target UOL refs
status
proof/evidence lineage
```

Frontiers must be typed semantically; generic “I don't understand” strings are not the authority.

### 3.3 `LearningEvidenceLink`

Links examples/counterexamples to candidate semantic assertions without converting them into definitions.

Important fields:

```text
package_ref
candidate_ref
example_or_counterexample
observation/evidence refs
context/time
weight/confidence as evidence only
scope/permission
```

### 3.4 `CompetenceResultRecord`

Immutable result of executing a competence case against exact candidate package revisions and exact substrate snapshot.

```text
case_ref
package_ref/revision
use_operation
snapshot fingerprints
passed/failed/partial
proof refs
counterexample refs
performance evidence
failure frontier refs
runner version
```

### 3.5 `PromotionDecisionRecord`

Separate policy/review decision:

```text
decision_ref
package_ref/revision
approved use operations
blocked use operations
competence result pins
review/authorization refs
risk/sensitivity constraints
decision = promote | preserve_candidate | reject | retract | supersede
```

No semantic record should infer promotion merely from lifecycle metadata on itself.

### 3.6 `LearningInvalidationRecord`

Records why previously derived/promoted authority became stale:

```text
invalidation_ref
changed dependency pins
affected package/record refs
required recomputation/replay classes
status
proof/evidence
```

## 4. Package families

Implement one generic package protocol with family-specific validators/adapters for:

- referent/identity;
- referent type/inheritance;
- facet entitlement;
- property/value contract;
- state dimension/value domain;
- action/event schema;
- transition/capability dependency rule;
- relation/role;
- inference/default/causal rule;
- lexical form/sense/construction;
- realization morphology/construction;
- response policy.

This list is a record-family coverage list, not a catalogue of learnable concepts.

## 5. Runtime components

### 13A — `LearningFrontierCollector`

Collect typed unresolved outputs from grounding, composition, epistemics, transition, query, realization, and later stages. Deduplicate by semantic dependency fingerprint rather than surface wording.

### 13B — `LearningEvidenceAggregator`

Group compatible evidence by exact referents/schema candidates/context/time/permission. Preserve conflicting clusters separately. Similarity may retrieve candidates but cannot assert equivalence.

### 13C — `CandidateStructureInducer` protocol

Pluggable proposal sources may include deterministic rules, statistical induction, external models, or explicit teaching. Output must be typed candidate records + evidence lineage + uncertainty, never direct writes.

No inducer is semantic authority.

### 13D — `LearningPackageAssembler`

Build a package DAG from candidate records, exact dependency pins, unresolved prerequisites, examples, counterexamples, and requested use profiles. Detect cycles and recursive-learning explosions.

### 13E — `LearningDependencyResolver`

Resolve existing exact authorities, candidate-in-package dependencies, missing prerequisites, revision conflicts, permission/sensitivity restrictions, and supersession requirements.

### 13F — `CompetenceCaseBuilder`

Create/retrieve declarative competence cases from teaching evidence and counterexamples. A case must target a semantic behavior/use, not memorize one sentence.

### 13G — `LearningCompetenceRunner`

Execute candidate packages in isolated temporary overlays against exact pinned snapshots. Must support:

- positive examples;
- counterexamples;
- structural renaming;
- cross-language equivalence where applicable;
- restart;
- context isolation;
- ambiguity/frontier behavior;
- performance budgets;
- adversarial bypass cases.

### 13H — `PromotionPolicyEngine`

Determine which use operations may be activated based on exact competence evidence, review, source quality, risk, sensitivity, dependencies, and policy.

Example outcome:

```text
mention: allow
ground: allow
compose: allow
query: allow
inference: provisional
transition: deny
operation: deny
realization: candidate
```

### 13I — `LearningPromotionCoordinator`

Compile one atomic GraphPatch containing only approved semantic records/revisions and first-class promotion/audit records. Revalidate all authority at the commit boundary and use CAS snapshot pins.

### 13J — `LearningInvalidationManager`

On correction, retraction, supersession, dependency revision, permission change, or counterexample:

```text
changed authority
-> dependency index
-> mark dependent packages/views stale
-> revoke affected use authorization if required
-> schedule/reify recomputation frontier
-> preserve historical decisions/proofs
```

Never silently keep stale derived authority active.

### 13K — `LearningRetractionCoordinator`

Retraction must be explicit, authorized, source/lineage scoped, and non-destructive. It may produce superseding lifecycle records and invalidations, not erase old evidence.

### 13L — `LearningRehydrationCoordinator`

After restart:

- rebuild exact active package/use indexes;
- verify dependency fingerprints;
- refuse stale packages;
- restore pending frontiers;
- preserve competence/review lineage;
- ensure equivalent behavior to pre-restart state.

### 13M — learning trace/observability

Every cycle must expose:

- frontier origin;
- candidate induction lineage;
- package dependencies;
- competence decisions;
- promotion policy reasons;
- invalidations;
- budgets/timeouts.

## 6. Package lifecycle

Recommended state machine:

```text
observed_frontier
-> candidate
-> assembled
-> dependency_resolved | blocked_on_dependency
-> reviewed
-> competence_running
-> competence_verified | competence_failed | partial
-> promotion_authorized_per_use
-> active_per_use
-> superseded | retracted | invalidated
```

A package can be active for some uses while remaining candidate/blocked for others.

## 7. Explicit teaching path

Explicit teaching is high-value evidence, not an unchecked write path.

```text
teaching observation
-> grounded teacher/source/target/content
-> attributed claim/evidence
-> candidate semantic records
-> dependency resolution
-> competence/counterexample checks
-> review/promotion policy
-> atomic promotion
```

Teaching cannot bypass schema validation, epistemic/source policy, or competence.

## 8. Repeated-observation learning

Repeated examples must not create definitions by frequency.

The system may:

- increase candidate retrieval priority;
- propose a reusable schema;
- propose argument/holder constraints;
- propose a lexical sense;
- generate a clarification/teaching frontier.

It may not:

- declare a universal rule from repetition alone;
- collapse correlated concepts into identity;
- infer causality from sequence alone;
- activate transition effects without reviewed transition competence.

## 9. Counterexamples and defeaters

Counterexamples are first-class.

Required behavior:

- exact candidate/rule they oppose is pinned;
- context/type/time conditions are preserved;
- a default may be narrowed instead of deleted;
- contradictory evidence can preserve multiple candidates;
- promotion policy reevaluates affected use operations;
- downstream derived views invalidate deterministically.

## 10. Learning transition/event semantics

Any learned event/transition package must reuse Phase 11/12 machinery:

1. learn/propose EventSchema and participant ports;
2. learn lexical senses independently;
3. learn state dimensions/values or reference existing exact revisions;
4. propose TransitionContractRecord separately;
5. provide positive and negative/non-occurring/context contrasts;
6. pass structural renaming and cross-domain genericity where applicable;
7. activate `transition` use only after dedicated competence;
8. never encode event-name effects in Python.

Historical replay after newly learned effects is a separate explicit policy and must not happen automatically.

## 11. Lexical and multilingual learning

Forms, senses, constructions, and realization remain separated.

A learned surface form may:

- map to multiple sense candidates;
- be language/span specific;
- have reversible normalization evidence;
- be authorized for grounding before realization;
- share one semantic target with forms in other languages.

Cross-language equivalence is semantic UOL equivalence, not translation-string equality.

## 12. Identity learning

Provisional referents and identity merge/split proposals remain reviewable. Learning evidence must not auto-merge identities because names/descriptions match repeatedly.

Promotion must preserve:

- identity criteria/anchors;
- conflicting facets;
- temporal/context scope;
- merge/split provenance;
- rollback/invalidation lineage.

## 13. Recursive learning and budgets

Learning dependencies can recurse. Enforce:

- maximum package DAG depth per cycle;
- maximum unresolved dependency expansion;
- maximum candidate fan-out;
- CPU/time/memory budgets;
- resumable frontier checkpoints;
- deterministic ordering under equal priority.

Budget exhaustion yields a durable frontier, never a guessed schema.

## 14. Security, privacy, and permissions

Learning must preserve evidence access scope.

Do not promote a globally visible semantic record from evidence whose permission/sensitivity scope does not authorize that use. Competence fixtures must use sanitized/minimized evidence references where required.

Untrusted external content cannot silently modify:

- self identity;
- high-risk transition authority;
- permissions;
- operation contracts;
- safety policy;
- privileged response policy.

## 15. Determinism and fingerprints

Package fingerprint must include all meaning/authority-bearing content:

- candidate record content fingerprints;
- exact dependency pins;
- examples/counterexamples;
- requested per-use activation;
- competence case definitions/results;
- review/policy refs;
- permission/sensitivity.

Generated local IDs and runtime ordering must not alter semantic package equivalence.

## 16. Persistence and normalized store

Add normalized tables/indexes for package/frontier/competence/promotion/invalidation records. Required indexes include:

- package lifecycle/use status;
- unresolved dependency -> packages;
- evidence -> packages;
- candidate record -> packages;
- competence case -> package revisions;
- changed authority -> dependents;
- frontier status/session/context.

Compiler remains deterministic and boot source contains only explicitly reviewed/promoted packages.

## 17. Performance strategy

Performance optimizations must preserve authority:

- snapshot-keyed package/dependency caches;
- content-addressed competence-result reuse only when all exact fingerprints match;
- incremental invalidation by dependency index;
- bounded parallel competence execution for independent cases;
- batched GraphPatch validation;
- deduplicated frontier/evidence clustering.

Never cache across changed schema/evidence/permission/policy fingerprints.

Capture P50/P95/P99 for frontier collection, package assembly, dependency resolution, competence, promotion validation, commit, invalidation, and restart rehydration.

## 18. Acceptance matrix

### New type

Teach a genuinely novel synthetic type and verify inherited facets and grounding after restart without source-code change.

### New state

Teach a new dimension/value domain; prove applicability and unknown/default distinction without auto-asserting a current value.

### New event

Teach a new event with participant contracts, then separately teach a transition contract; prove negative/modal/non-occurring contrasts and Phase-12-style genericity.

### New lexicalization

Teach multiple forms/languages for an existing semantic target; prove same UOL and independent realization authorization.

### Counterexample

Add a counterexample that narrows/defeats a rule without deleting historical evidence.

### Per-use activation

Make a package pass grounding competence but fail transition competence; grounding must activate while transition remains denied.

### Retraction

Retract evidence/authority and verify exact dependent invalidation, no destructive history loss, and correct behavior after restart.

### Concurrent promotion

Two promotions from the same stale snapshot cannot both silently commit incompatible authority.

### Renaming/genericity

Mechanically rename learned semantic refs/forms; behavior remains structurally equivalent with zero kernel edits.

## 19. Adversarial tests

Must include:

- example memorization masquerading as definition;
- competence case that passes only because of exact phrase matching;
- LLM proposal trying to self-authorize transition/operation use;
- stale competence result reused after dependency revision;
- counterexample omitted from package fingerprint;
- package dependency cycle;
- permission escalation through promotion;
- identity auto-merge attempt;
- direct GraphPatch bypass of PromotionDecision;
- partial package commit;
- restart with stale dependency fingerprints;
- mass frontier explosion/budget exhaustion;
- two packages defining incompatible active revisions;
- malicious package refs/names attempting kernel behavior changes.

## 20. Implementation order

```text
13A durable package/frontier/evidence/competence/promotion/invalidation models
13B codec + deterministic SQLite + typed repositories
13C commit-boundary validators and exact dependency graph
13D frontier collection/deduplication
13E candidate-inducer protocol boundary
13F package assembler + recursion/budget control
13G isolated competence runner using temporary overlays
13H per-use promotion policy
13I atomic CAS promotion coordinator
13J invalidation/retraction/supersession manager
13K restart rehydration/stale-authority refusal
13L cross-family competence suites and adversarial tests
13M shadow wiring into Core Loop Stage 11 learning-frontier path
```

Do not wire Phase 13 as public semantic authority until promotion/retraction/restart/adversarial gates pass.

## 21. Deliverables

Expected artifacts:

```text
cemm/v350/learning/...
reviewed learning record codecs/models/repositories
normalized persistence migrations
learning contract + declarative competence suites
tools/verify_v350_learning.py
docs/implementation/v350-phase-13.md
docs/audits/v350-phase13-authority-review.md
CI wiring and deterministic restart tests
```

## 22. Phase-13 exit gate

Phase 13 passes only when a previously unknown synthetic semantic package can be proposed from evidence, remain non-authoritative while incomplete, satisfy independent per-use competence, atomically promote, survive restart, participate through existing generic grounding/composition/epistemic/transition machinery where authorized, be corrected/retracted with deterministic dependent invalidation, and do all of this without adding a semantic kernel branch or memorizing a demonstration phrase.
