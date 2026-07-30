# Runtime, Session Lifecycle, and Effect Safety

## 1. Cycle

```text
ORIENT
→ PROCESS EVIDENCE
→ RETRIEVE AUTHORITY
→ CONSTRUCT CANDIDATES
→ NEURAL RANK
→ COMPILE
→ VERIFY
→ EVALUATE
→ EFFECT
→ REALIZE AND VERIFY
→ RECORD EPISODE
```

This is an ownership sequence, not the historical CEMM Stage 0–22 contract.

## 2. Session lifecycle

A session is a root event with participants, phase, focus and obligations.

Supported phase behaviour:

- direct substantive input can move `opening → active` without forced greeting;
- greeting creates a reciprocal greeting obligation;
- farewell creates a closing obligation and closes the session after realization.

## 3. Semantic modes

### OBSERVE

Admit verified designation, relation, state or event evidence with proof.

### QUERY

Match exact and derived facts, project variables, preserve proof lineage, and avoid mutation.

### REQUEST

Check the event signature plus all of:

```text
capability
permission
adapter
preconditions represented by authority
```

A missing dependency produces a typed denial and no effect.

### SIMULATE

Return a transition preview in an isolated branch. World revision must remain unchanged.

## 4. Query/inference engine

The matcher supports recursive application-valued roles. Query evaluation can use bounded reviewed inference and returns:

- status;
- variable bindings;
- proof refs;
- recursive proof trees;
- unresolved variables;
- blockers.

## 5. Attributed content isolation

An observed speech event may admit its embedded content as attributed evidence. Direct world-event matching uses `actual_only` semantics and excludes attributed child facts.

Therefore:

```text
Mary said Bob left
```

does not make:

```text
Bob left
```

a directly observed world fact.

## 6. Obligations and response meaning

Dialogue control is based on open obligations and semantic response meaning, not a neural response class.

Examples:

- reciprocal greeting;
- close session;
- answer query;
- acknowledge admission;
- report denial blockers;
- report unknown/frontier.

## 7. Deterministic verified realization

The MVP realizer is deterministic. It receives `ResponseMeaning`, produces text, and verifies a receipt containing:

- meaning kind;
- status;
- response hash;
- absence of internal semantic refs;
- preservation of denial/unknown/executed distinctions.

It is intentionally not a neural language generator.
