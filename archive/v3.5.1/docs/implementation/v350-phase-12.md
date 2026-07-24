# CEMM v3.5 Phase 12 — Cross-domain transition vertical-slice proof

**Base:** remote Phase-11 commit `735d13d11f112d0062972a9a66d59100fa8a406c`
**Status:** implemented and phase-verified; verification authority only; not public-runtime-authoritative
**Canonical domain seed added:** zero

## 1. Purpose

Phase 12 is an adversarial proof that Phases 7–11 form a reusable semantic path. It is intentionally not a domain feature phase. Synthetic packages are installed into fresh temporary overlays, exercised, discarded, and forbidden from leaking their lexical or semantic names into the kernel.

## 2. Full-path packages

Five full-path executions prove four structurally distinct transition classes plus explicit non-actual context isolation:

```text
reviewed overlay package
-> raw text/form lattice
-> joint grounding
-> UOL factor-graph composition
-> attributed proposition/source assessment
-> explicit epistemic admission bridge
-> exact target-context event occurrence
-> transition-contract compilation
-> non-mutating preview
-> revision-pinned proof + state delta
-> immutable state projection
-> capability dependency reevaluation where applicable
-> atomic CAS GraphPatch
-> restart/history verification
```

The packages cover structural classes rather than privileged concepts:

- terminal-style state transition with dependent capability becoming unavailable;
- activation-style transition with dependent capability becoming available;
- ordered decrease with explicit target ordering;
- externally caused relocation/state change while a self-action capability remains unavailable.

## 3. Contrast and genericity cases

The pinned competence suite additionally proves:

- attempted occurrence does not fire success effects;
- hypothetical occurrence does not mutate the target context;
- negative proposition cannot authorize the corresponding positive event effect;
- attributed/unadmitted report cannot mutate the target context;
- unresolved time emits a frontier and no timeline delta;
- a transition committed in a non-actual context does not alter parallel actual-context state;
- mechanical renaming of package refs/forms preserves structural behavior;
- one surface form may preserve multiple senses and be selected through reviewed type/port compatibility;
- simultaneously authorized transition contracts block on an explicit composition frontier;
- competing capability dependencies block on an explicit composition frontier;
- failed, prevented, and explicitly non-occurring events are blocked across the full Phase-7→11 path;
- a retracted epistemic admission cannot authorize transition;
- a pre-state change after preview makes the execution plan stale and commit is rejected before patch generation.

## 4. New verification authority

- `cemm/v350/verification/transition_slices.py` — generic overlay-only full-path harness.
- `cemm/v350/verification/contract.py` — pinned Phase-12 package auditor.
- `cemm/data/v350/vertical_slice_contract.json` — exact review contract.
- `cemm/data/v350/competence/transition_vertical_slices.jsonl` — declarative cases.
- `tools/verify_v350_vertical_slices.py` — deterministic audit/execution report.

The verifier scans `grounding`, `composition`, `epistemics`, and `transitions` for competence-fixture lexical/package tokens. A fixture name appearing in semantic kernel code fails the audit.

## 5. Phase-11 hardening included as prerequisite corrections

Phase 12 includes prerequisite correctness fixes discovered by the adversarial audit:

- exact event and participant-application revision pins in `TransitionProofRecord`;
- temporal/revision-exact state-condition evaluation;
- attempted-event blocking;
- unresolved-time frontier at preview;
- retroactive/out-of-order timeline rejection pending replay/invalidation;
- runtime coreference duplicate-effect detection;
- competing-contract/dependency frontiers;
- explicit stale-snapshot rejection before recomputation;
- canonical plan recomputation before patch creation;
- durable state-projection completeness validation;
- direct GraphPatch capability-ambiguity rejection;
- context-specific capability precedence;
- derived rather than hard-coded capability confidence;
- normalized transition-proof persistence schema version advanced to 5.

## 6. Performance design

Phase-12 timing is evidence, not authority. Each full-path case records:

- package overlay validation/install;
- form + grounding + composition;
- epistemic bridge persistence;
- transition discovery/preview;
- transition commit;
- restart verification.

No optimization may skip exact revision, context, proof, or CAS checks. Later performance work should cache immutable schema/contract compilation by exact snapshot fingerprint and batch repository reads without weakening proof reconstruction.

## 7. Boundaries preserved

Phase 12 does not:

- add domain event/state/action/type concepts to boot source;
- add event-name mutation branches;
- add relation/role effects by encoding them as state strings;
- infer arithmetic from scalar magnitude without explicit semantics;
- promote examples into definitions;
- implement Phase-13 learning/promotion authority;
- perform public runtime cutover.

## 8. Exit gate

Phase 12 is phase-complete only when the pinned verifier (currently 19 declarative cases), architecture lint, predecessor phase verifiers, focused test suite, deterministic compiler, restart checks, and full-repository CI all pass on the real checkout. Local isolated-snapshot validation must never be reported as full historical-repository verification.
