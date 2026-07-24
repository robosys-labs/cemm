# CEMM v3.4.7 final completion patch 2

This is the additive completion set for the first v3.4.7 semantic-authority patch. It closes the architectural areas that were represented only as a vertical slice in the first delivery while preserving its public runtime API and all original acceptance behavior.

## What patch 2 completes

### Schema lifecycle and operational use

Schema and rule candidates now have durable revisions, field provenance, support lineage, counterevidence, dependencies, competence results, environment fingerprints, promotion status, and invalidation. The kernel projects operation-specific `SchemaUseProfile` and `OperationalPort` records rather than treating activation as a global boolean.

### Multimodal evidence

`ObservationLattice` accepts structured, vision, audio, sensor, and tool observations through modality-neutral contracts. Analyzer outputs remain evidence. Contradictory observations retain separate identities and root lineage until semantic grounding and epistemic policy decide what may be admitted.

### Truth and time

Knowledge supports independent positive and negative evidence, four-state truth (`supported`, `opposed`, `both`, `undetermined`), exact source retraction, dependency invalidation, and validity intervals. Defaults and predictions may influence ranking but do not silently become durable facts.

### General learning

Grounded contributions are classified into lexical alias, definition, strict taxonomic, causal, enabling, and other typed candidate families. Promotion is atomic and competence-gated. Active learned schemas and rules are rehydrated into the ordinary grounding and inference paths after restart; there is no learning overlay.

### Relation and rule semantics

The relation-algebra coordinator compiles schema-declared symmetry, inverses, and transitivity into ordinary strict rules. Consequence policy distinguishes strict entailment, defeasible expectation, causal prediction, enabling possibility, probabilistic support, and sensitive-restricted consequences.

### Goals, operations, and effects

Capabilities are derived from durable live observations with confidence, expiry, revocation, permission, resource, risk, and port-completeness checks. Adapter-returned effect patches are reauthorized before commit and cannot mutate schema authority. Operation attempts and outcomes are durable ledger records.

### Response and realization

Response content remains UOL. Reference and conversational-tone planning are semantic constraints; tone may alter target-language realization but not selected meaning. Realization records round-trip coverage and writes an emission ledger only when its proof is authorized.

### Auditability and release proof

`python -m cemm.v347.audit` exposes selected predicates, selected propositions, gaps, truth assessments, committed patches, emission proof, revisions, and durable record counts. The final suite contains 58 acceptance, restart, multilingual, multimodal, metamorphic, safety, lifecycle, and determinism tests.

## Applying patch 2

Patch 2 expects the first CEMM v3.4.7 delivery to be installed. From the extracted patch-2 directory:

```bash
python apply_patch2.py /path/to/cemm
python validate_patch2.py /path/to/cemm
```

The installer verifies hashes, creates a timestamped backup, writes a receipt, applies only changed/new files, and clears stale bytecode caches.

For a clean installation, use the consolidated final v3.4.7 delivery instead.
