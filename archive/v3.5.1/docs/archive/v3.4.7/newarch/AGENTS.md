# CEMM v3.5 Governing Agent Instructions

This file is the highest-priority local implementation contract for v3.5 work.

## 1. Authority order

1. `AGENTS.md`
2. `ARCHITECTURE.md`
3. `TERMINOLOGY.md`
4. `FOUNDATIONAL_KNOWLEDGE_ARCHITECTURE.md`
5. `LEARNING_ARCHITECTURE.md`
6. `CLAIMS_EVENTS_STATE_AND_IMPACT.md`
7. `UOL.md`
8. `CORE_LOOP.md`
9. `DATA_ARCHITECTURE.md`
10. `IMPLEMENTATION_PLAN.md`
11. `ACCEPTANCE_CONTRACT.md`
12. executable architecture tests
13. implementation code and data

Archive conflicts. Do not retain competing authorities in the canonical runtime.

## 2. Status claims

Use:

```text
specified
implemented
wired
authoritative
verified
```

Never call work complete unless every applicable status is true.

## 3. Learning-first law

CEMM learns reusable semantic structure, not phrases.

A fix is invalid if it requires:

- a transcript phrase;
- a full-sentence construction for compositional meaning;
- a per-predicate output sentence;
- a Python enum for a learned type;
- a hard-coded state mutation for one event;
- an ungrounded default;
- a targetless acknowledgement.

## 4. Referent law

`Referent` is the only identity-bearing semantic filler family.

Semantic type is data-driven and supports multiple inheritance.

Properties, states, roles, capabilities, functions, importance, claims, and events are semantic applications/records, not mutable fields casually added to a referent object.

## 5. Entitlement law

Every state/property/capability use must be licensed by a type-derived facet entitlement or explicit schema extension.

Distinguish:

```text
active
latent
default_expected
unknown
blocked
terminated
inapplicable
contradicted
```

## 6. Semantic-axis law

Never collapse:

- truth negation;
- decrease;
- loss;
- deactivation;
- prohibition;
- harmful valence;
- low importance.

They are separate UOL meanings.

## 7. Claim law

An utterance is evidence of a discourse/claim act. It is not automatically actual-world truth.

Keep proposition, claim occurrence, source evidence, and CEMM epistemic stance separate.

## 8. Event law

Events affect state only through typed transition contracts and proof-bearing deltas.

Hypothetical, reported, fictional, planned, and counterfactual events must remain context-isolated.

## 9. Capability law

Distinguish affordance, disposition, capability, permission, competence, intention, and function.

Capabilities are recomputed from dependencies and state. Do not erase historical capability schemas.

## 10. Impact and response law

Impact and importance are stakeholder/context-relative assessments.

Do not console, congratulate, warn, or remain silent based on a surface word. Generate these goals from selected meaning, epistemics, impact, importance, relationship, and policy.

A literal programmed response must be represented as an explicit scoped semantic policy.

## 11. Language law

Language modules may contain language-specific form and grammar knowledge. Kernel modules may not branch on surface words.

NLG must use reusable grammar, morphology, and argument frames. Ordinary semantic schemas do not own full response sentences.

## 12. Learning lifecycle

```text
candidate
→ structurally_closed
→ provisional
→ competence_verified
→ active
→ superseded/rejected
```

Use profiles are independent. Interpretation activation does not imply inference or execution activation.

## 13. Required tests

Every implementation affecting semantics must add:

- positive case;
- paraphrase;
- cross-type contrast;
- negation/modality contrast;
- context isolation;
- counterexample;
- restart;
- trace assertion;
- no-shortcut lint.

## 14. Repository hygiene

- do not edit archived contracts as active guidance;
- do not leave temporary compatibility fallbacks authoritative;
- do not duplicate semantic data across JSON and code;
- report skipped tests;
- preserve migration and rollback paths;
- prefer removal of competing authority over adding another wrapper.
