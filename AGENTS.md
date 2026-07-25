# CEMM v1 — Governing Agent Instructions

**Status:** highest-priority local implementation contract  
**Target:** one exact semantic cognition runtime; no compatibility brain, phrase router, or hidden fallback

Read these active contracts before changing code:

1. `AGENTS.md`
2. `ARCHITECTURE.md`
3. `runtime-core-loop.md`
4. `CURRENT_RUNTIME_WEAKNESSES.md`
5. `V1_ACCEPTANCE.md`
6. `README.md`

Documents under `docs/archive/` are historical evidence only. A historical test, plan, patch report, demo transcript, or frozen MVP cannot override the active contracts.

---

## 1. Core thesis

```text
meaning != language
exact semantics are authority
neural/dynamic computation proposes, ranks, composes and realizes
```

There is one semantic brain. The exact plane and dynamic plane have different computational roles, but they converge on one semantic authority. Never preserve a legacy parser, phrase recognizer, sidecar pack, compatibility ontology, or alternate runtime as a second source of meaning.

New domains normally extend atoms, designations, existing operator applications, dimensions, rules, mechanisms, profiles, evidence and learned parameters. They do not expand kernel branch count or database schema count.

---

## 2. Mandatory root-cause workflow

A failing phrase is a diagnostic probe, not a feature request.

Before editing code:

1. Reproduce the failure with a typed stage trace and exact authority generation.
2. Locate the earliest stage where the expected artifact diverges.
3. Identify the missing or malformed **general capability**: normalization, form evidence, reference candidates, identity grounding, state entitlement, CSIR expressiveness, inference, admission, transition, goal, Response CSIR, or realization.
4. Review all existing foundational atoms, roles, relations, rules and stage contracts that could represent the capability.
5. Decide whether the defect is data, authority linkage, retrieval, candidate generation, exact validation, settling, persistence ownership, or training supervision.
6. Define a cross-domain and multilingual acceptance test before implementation.
7. Change the earliest correct owning layer. Do not patch a later symptom.
8. Run authority-link, no-hidden-write, multi-hypothesis, anti-bloat and regression gates.
9. Update active documentation and archive superseded plans.

A patch is rejected when its justification is merely “this makes the example pass.”

---

## 3. Absolute prohibition on stealth text cognition

Do not add regexes, token lists, substring checks, punctuation checks, exact transcript checks, special question-word branches, or phrase-specific conditions to infer semantic meaning inside the core loop.

The only permitted surface-pattern machinery is inside an explicitly bounded **pre-core form-processing subsystem**. Its responsibility is reversible normalization and form evidence, not semantic authority. It may produce multiple candidates with provenance; it may not decide referent identity, discourse force, operator choice, world truth, state dimension, event effect, goal, or response meaning.

```text
raw signal/text
→ reversible normalization alternatives
→ morphology/token/span/construction evidence alternatives
→ sentence/document resolution pass
→ ResolvedFormLattice (N-best, provenance preserved)
→ semantic Stage 1–22 core loop
```

Until that subsystem is implemented, do not scatter temporary text matching through `runtime.py`, `interpreter.py`, `goals.py`, `response.py`, or domain data loaders.

---

## 4. Multi-resolution law

Ambiguity must remain parallel until sufficient semantic and contextual evidence settles it.

Forbidden:

```text
surface → first label match → one referent → one meaning
surface → punctuation/keyword → one force
unknown token → concept
```

Required:

```text
surface evidence
→ candidate forms/spans/constructions
→ candidate designations/reference requirements
→ candidate referents/identities
→ candidate CSIR graphs
→ exact clamps + state/type/context factors
→ recurrent bounded settling
→ stable, partial, ambiguous, or unresolved result
```

No stage may collapse N-best candidates merely for API convenience. A top candidate may be selected only with an explicit margin/convergence decision and retained alternatives/provenance.

---

## 5. Foundation and authority integrity

Authority JSON files are one graph split across files, not independent mini-ontologies.

Before any durable import:

- link the complete authority bundle;
- verify every atom, operator, role, control symbol, fact filler, rule constant and language-pack constant;
- reject concept-as-instance hierarchy encoding;
- reject state applications without `role:dimension`;
- reject incomplete reified state specifications;
- reject duplicate/conflicting atom kinds or role contracts;
- validate language-pack hashes and authority constants;
- write the bundle atomically only after all checks pass.

Generic relations and generic rules belong in foundational authority, never in a family, vehicle, medical, security, or other demo/domain file.

Do not create a new foundational atom until you have searched existing primitives and documented why composition of existing atoms/operators cannot represent the meaning. When a new foundational primitive is genuinely required, update architecture, bundle validation, multilingual data, tests and migration together.

---

## 6. Designation, label and name law

Referent identity is opaque and distinct from every label.

```text
referent
← op:designation(label_type, surface, language, context, provenance)
```

`name` is a designation family/property query, not an identity, state value, English keyword, or custom response branch. `label:name_full` and `label:name_alias` are subtypes of `label:name`.

A query for a name must construct a designation restriction graph and project the appropriate surface literal/designation evidence. Never implement `if "name" in text` or a `NAME_QUERY` semantic program.

---

## 7. Fixed semantic laws

- Exactly five compact operator shapes remain the v1 ABI: designation, type, relation, state and event.
- `op:type(instance, class)` is instance membership. Concept hierarchy uses `rel:subtype_of`.
- State always has subject, dimension and value.
- State specifications may reify a dimension/value pair; their relations must be foundational and complete.
- Defaults are expectations, not observations.
- Claims are source-attributed before admission.
- Prediction, simulation and desired state are not observed world state.
- Subject/object positions never imply causal roles.
- Response semantics precede words.
- Partial meaning is valid cognition and must not be discarded.
- Unknown material must not create semantic authority or poison unrelated self/world state.

---

## 8. Backward compatibility and tests

Backward compatibility is not a goal when it preserves an invalid semantic contract.

Old tests are evidence, not authority. Retire or rewrite tests that assert:

- exact phrase responses;
- Ask/Learn/Teach as different cognition;
- global SessionSelf semantics;
- omitted dimensions;
- concept-as-instance hierarchy;
- function words inferred from examples;
- autonomous concept creation;
- generic outcome response templates;
- whole-store runtime scans.

Never weaken a new exact gate merely to keep a historical test green.

---

## 9. Performance laws

Normal cycles must use bounded indexed retrieval, generation/revision keyed caches, bounded recursive closure, bounded recurrent settling and bounded re-entry.

Forbidden on ordinary turns:

- whole-store hashes;
- whole-graph/base-fact scans;
- full closure materialization;
- per-turn model retraining;
- global designation rebuilds;
- one regex evaluation per stored label;
- persistence of transient candidates or query closure.

Hard-required semantic/proof slots cannot be dropped by learned ranking, but they remain within explicit budgets.

---

## 10. Definition of a valid fix

A fix is complete only when:

- the root cause is stated;
- the owning stage/module is identified;
- the exact semantic representation is documented;
- the solution generalizes beyond the triggering phrase/domain/language;
- authority linkage and import are atomic;
- N-best alternatives and partial meaning are preserved;
- persistence ownership is unchanged or explicitly justified;
- performance budgets are maintained;
- active docs and acceptance tests agree;
- superseded plans/tests are archived or retired.

When uncertain, stop and deepen the architecture review. Do not add a clever fallback.
