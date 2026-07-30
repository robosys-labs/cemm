# Authoritative Hybrid MVP Evaluation Report

## 1. Evaluation scope

This report evaluates the isolated MVP's architecture contracts and compact neural candidate-ranking task. It does not claim open-domain natural-language competence or parity with a general language model.

## 2. Neural ranking result

The final included checkpoint records:

| Metric | Value |
|---|---:|
| Training rows | 62 |
| Held-out rows | 38 |
| Unique training rows | 62 |
| Unique held-out rows | 38 |
| Normalized text overlap | 0 |
| Template-ID overlap | 0 |
| Lexical-value partition overlap | 0 |
| Held-out correct selections | 38 |
| Held-out selection accuracy | 100% |
| Best epoch | 17 |
| Parameter count | 438,817 |

All rows are generated semantic-ranking examples. The score demonstrates correct selection in the included finite candidate space; it is not an open-domain benchmark.

## 3. Composition holdout

The `attributed_event_query` family appears in the held-out set and is absent from training. Both training and test contain simple and embedded compositions, but this family-level holdout checks transfer to an unseen semantic task family built from known graph primitives.

## 4. Semantic/governance test suite

The final suite contains **52 passing tests** covering:

### Authority and inference

- authority is immutable and reviewed;
- unreviewed refs are rejected;
- aliases require reviewed targets;
- mother-in-law inference creates a transient partner witness;
- married state is derived with recursive proof lineage;
- the existential witness is not durable.

### Session and dialogue

- semantic greeting events;
- direct substantive opening;
- farewell closure;
- obligation-driven realization.

### Unknown-content governance

- telescope query does not create an atom/entity/concept;
- malformed input abstains;
- unknown operation target abstains;
- unknown residual blocks `hello telescope`;
- unknown alias target abstains;
- proposal is read-only.

### Recursive semantics

- embedded proposition graph accepted;
- cycle rejected;
- attributed leave is isolated from world leave;
- attributed-event query works.

### Effect safety

- query does not mutate world;
- simulation does not mutate world;
- exact state operation changes state;
- missing capability denies operation;
- missing permission denies operation;
- missing adapter denies operation;
- alias operation without permission is denied;
- capability query reports missing runtime dependency.

### Model governance

- ranker is a real PyTorch module;
- semantic action candidates are not response templates;
- strict split partitions have no recorded overlap;
- composition holdout family is absent from training;
- checkpoint authority revision mismatch fails startup;
- checkpoint authority content-hash mismatch fails startup.

### Kernel and realization

- exactly five operators;
- fabricated `op:intent` rejected;
- request without transition rejected;
- realization receipt is exact;
- internal refs are not exposed;
- episode revision pin includes the current turn.

## 5. Adversarial traces

### Governance defect prevented

```text
do you have a telescope?
```

Expected and observed contract:

- no authority mutation;
- no world atom or fact for telescope;
- no default concept;
- frontier/unknown response.

### Residual-content attack prevented

```text
hello telescope
```

Expected and observed contract:

- `hello` may retrieve greeting;
- `telescope` remains an uncovered literal;
- greeting candidate is rejected rather than silently ignoring the residual.

### Attribution safety

```text
Mary said Bob left
```

Expected and observed contract:

- recursive graph admitted as attributed evidence;
- direct world query for Bob leaving remains unknown;
- attributed query can retrieve the report.

### Operation denial

Removing any one of capability, permission or adapter causes a typed denial and no world revision.

## 6. Reproducibility

The release includes:

- authority revision and content hash;
- dataset manifest hash;
- model revision;
- checkpoint hash;
- worktree history bundle;
- test output;
- demo output;
- source manifest;
- clean-extraction validation receipt.

## 7. Correct interpretation

The supported conclusion is:

> A small real neural ranker can select bounded multi-application semantic graph programs from authority-retrieved candidates while exact code owns vocabulary, graph legality, truth, inference, effects, operations, session obligations and realization.

The result does not yet establish broad paraphrase robustness, large-authority retrieval, unrestricted graph generation, multilinguality or neural realization.
