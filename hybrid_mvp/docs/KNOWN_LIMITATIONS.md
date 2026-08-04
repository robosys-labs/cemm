# Known Limitations

## 1. Neural scope

The ranker selects among bounded candidates produced by an exact generator. It is not yet an autoregressive graph-action decoder.

## 2. Authority size

The reviewed authority corpus is intentionally small and demonstration-focused. The runtime architecture supports retrieval, but the MVP does not test million-atom authority scale.

## 3. Language coverage

- English only;
- compact tokenizer/form evidence;
- limited paraphrase corpus;
- no speech, images or other modalities;
- no broad natural-language realization model.

## 4. Evaluation scale

The held-out set has 38 rows. It is strictly partitioned by the recorded dimensions but remains synthetic and small. The 100% score should not be extrapolated beyond this benchmark.

## 5. Graph composition

Recursive attributed graphs are supported, but the MVP does not yet cover arbitrary deep definitions, quantified clauses, coordination, temporal intervals, negation trees, or unrestricted rule induction.

## 6. Learning

The MVP supports governed alias learning and admitted facts. It does not yet promote newly induced event signatures, state dimensions, relation types, rules or policies into authority without review.

## 7. Inference

Inference is bounded exact forward chaining. It does not implement probabilistic, defeasible, abductive, analogical or utility-based reasoning.

## 8. Operations

Operations are demonstration adapters. There are no external service connectors, irreversible transactions, retry semantics, compensation plans or distributed operation receipts.

## 9. Realization

Realization is deterministic and verified for the implemented response meanings. It does not yet provide rich multilingual or stylistic generation.

## 10. Session context model

The session lifecycle is exact, but the neural ranker does not yet encode a rich active event stack, long-term discourse history, or learned context selection.
