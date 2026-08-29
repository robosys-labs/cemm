# Neural Graph-Action Ranker

> **Historical evidence:** This document is retained for analysis and forensic
> provenance only. It owns no current execution or phase status. Current status
> is derived from
> [`governance/replay_status.jsonl`](../governance/replay_status.jsonl).

## 1. Role

The model performs uncertain ranking only:

```text
EvidencePacket + retrieved authority candidates
→ score(ActionCandidate)
```

It never generates an unrestricted semantic atom and never writes truth.

## 2. Candidate-first architecture

Before neural scoring:

1. normalize text;
2. extract closed-class form evidence;
3. resolve reviewed and learned designations;
4. retrieve legal semantic candidates;
5. construct bounded graph-action programs;
6. include an explicit abstention candidate.

The model sees the input representation and each candidate action representation. It learns which legal candidate best matches the evidence.

This differs from both unsafe extremes:

- it is not a phrase-dispatch rule engine;
- it is not a free-form neural graph generator with authority over vocabulary.

## 3. Model

`GraphActionRanker` is a real PyTorch module with independent Transformer encoders for:

- normalized input plus evidence tokens;
- canonical graph-action candidate tokens.

The resulting text and action vectors are combined by a learned scoring network.

Recorded checkpoint:

| Property | Value |
|---|---:|
| Parameters | 438,817 |
| Training rows | 62 |
| Held-out rows | 38 |
| Best epoch | 17 |
| Held-out candidate-selection accuracy | 38/38 |
| Authority revision | `authority-v1-2026-07-29` |
| Authority content hash | `authority-content:8981f399f50cdd6e59a9fb60` |
| Dataset manifest SHA-256 | `0a92d739fd4e7e95bf528449c0919ce87e8071cf6f9ee71f133aa8d8c319899c` |

## 4. What is learned

The ranker learns preferences among semantic program families such as:

- abstention;
- greeting/farewell event;
- alias learning;
- state observation/query/projection/simulation/request;
- relation observation/query;
- event observation/query/admissibility;
- capability inventory;
- attributed event query.

It learns from action structure, not response templates.

## 5. What is exact

Candidate construction and later verification constrain:

- operators;
- semantic refs;
- roles;
- local variables;
- source coverage;
- recursive app links;
- transition ownership;
- event signatures;
- state domains;
- permissions/capabilities/adapters.

## 6. Checkpoint governance

The checkpoint contains:

- model weights;
- text/action vocabularies;
- ranker configuration;
- dataset manifest;
- authority revision;
- authority content hash;
- model revision.

`load_runtime()` refuses an authority mismatch.

## 7. Evaluation partitioning

The data generator enforces:

- normalized text disjointness;
- template-ID disjointness;
- lexical-value partition disjointness;
- unique rows;
- training-only vocabulary construction;
- a recorded composition-holdout family.

The included score is intentionally narrow. It validates the ranker boundary, not open-domain language competence.

## 8. Production evolution

The next model should move from ranking enumerated candidates to a retrieved graph-action decoder with incremental exact masks. It must still remain downstream of reviewed semantic retrieval and upstream of exact verification.
