# Evaluation Protocol

> **Historical evidence:** This document is retained for analysis and forensic
> provenance only. It owns no current execution or phase status. Current status
> is derived from
> [`governance/replay_status.jsonl`](../governance/replay_status.jsonl).

## Required partitions

- normalized text disjoint;
- template ID disjoint;
- lexical value partition disjoint for names and aliases;
- composition tags recorded and reported.

## Semantic metrics

The primary metric is correct graph-action candidate selection, not response string similarity.

Runtime gates assert:

- exact selected family and graph roles;
- no authority mutation;
- no world mutation on query, frontier, or simulation;
- alias target exists in authority;
- permission/capability/adapter enforcement;
- proof-bearing inference;
- attributed content isolation;
- session opening/closing obligations;
- revision pinning.

## Mandatory adversarial cases

- `do you have a telescope?` does not create an entity or concept;
- malformed unknown input abstains;
- unknown operation target abstains;
- request without transition is rejected;
- fabricated sixth operator is rejected;
- recursive application cycle is rejected.
