# CEMM v1 Foundation Learning and Form Integrity Implementation

## Status

This patch implemented the first production-bounded form-resolution and semantic learning foundation required by `AGENTS.md`, `ARCHITECTURE.md`, `CURRENT_RUNTIME_WEAKNESSES.md`, and `V1_ACCEPTANCE.md`.

**Extended by:** the semantic-operational rewrite (v3.1.3) governed by `CEMM_RUNTIME_IMPLEMENTATION_CONTRACT.md`. That rewrite adds atomic feature-driven construction assembly (`form_algebra.py`), perspective-aware reference planning (`reference.py`), fail-closed span-coverage receipts (`semantic_coverage.py`), cycle-local operational truth (`operational.py`), bounded dialogue obligations (`dialogue.py`), and immutable surface-plan indexes (`surface_plans.py`). Where this document and `CEMM_RUNTIME_IMPLEMENTATION_CONTRACT.md` differ, the latter is normative.

It does **not** claim that general multilingual grounding or open-ended language realization is complete. The remaining state-conditioned settling, broad morphology, embedded discourse, chained-property, and production concurrency work remains active.

## Root cause repaired

The previous interpreter detected an unknown token and skipped the entire containing clause before semantic candidate generation. Consequently, grounded participants, designation families, query structure, and known relations were discarded. The runtime then created a generic frontier and realized a clarification sentence from a literal, without first constructing and executing an exact semantic learning query.

## Implemented architecture

```text
raw text EvidenceEnvelope
→ bounded reversible normalization alternatives
→ token/span/construction evidence
→ generation-pinned trie designation/reference matching
→ N-best grounding hypotheses
→ reviewed construction + neural semantic candidates
→ exact compiler clamps
→ recurrent settling
→ resolved/partial/unresolved CSIR
→ exact designation query for unresolved forms
→ sparse Stage-10 retrieval and proof
→ answer known meaning or request targeted learning evidence
```

### Pre-core form processing

`cemm/forms.py` owns only form evidence:

- raw text is retained before normalization;
- Unicode, apostrophe, whitespace, contraction, control, zero-width, and bidi transformations retain provenance;
- normalizations, spans, grounding hypotheses, and construction matches are explicitly bounded;
- stored designation/reference matching uses a token trie, not one regex evaluation per stored label;
- the index is refreshed only when the world revision changes;
- ambiguity remains N-best until semantic settling.

The form subsystem proposes candidates but cannot decide world truth, referent identity, state, operator validity, discourse obligations, or durable knowledge.

### Partial meaning

Unknown units no longer erase the surrounding clause. Reviewed constructions may preserve unknown units as scoped blockers while compiling grounded semantic structure. For example, an unresolved discourse token cannot delete a valid user-name designation claim.

### Native learning operation

Unknown-form learning is represented as an ordinary exact `QueryStructure` over `op:designation`:

```text
op:designation(
  target=?target,
  label_type=?label_type,
  surface=<observed literal>,
  language=<active language>
)
```

Stage 10 queries existing reviewed and learned data before Stage 15 may select a clarification goal. Known forms therefore produce proof-bearing answers; unknown forms produce a `request_learning_evidence` Response CSIR containing the exact probe query, expected kinds, surface evidence, and known bindings.

### Generic designation competence

The English structured pack now includes all five fixed operators, including `op:designation`. Name, alias, identifier, abbreviation, acronym, and lexical-meaning behavior use the same designation operator and query engine. No `NAME_QUERY`, transcript branch, or runtime keyword check was added.

### Response realization

Response pointerization now preserves atom, literal, and numeric provenance. Designation property answers and learned designation answers are realized from exact Response CSIR semantics and are authorized only when the language pack contains the exact reviewed transformation.

### Atomic conversational foundation

`cemm/data/conversation_foundation.json` is a linked authority extension loaded with `base.json` through one `Store.import_bundle()` call. It seeds reusable semantic capabilities rather than a phrase catalogue:

- designation families and subtype structure;
- learning, knowledge, memory, query, clarification, correction, evidence, context, and conversation concepts;
- learning/query/clarification/remember/designate/explain capabilities and dependencies;
- common state-domain/value relations;
- the system's reviewed name, full name, and acronym;
- common reviewed lexical designations, including `lol` → `concept:laughing_out_loud`;
- English designations and selected Spanish designations.

All data uses the fixed five-operator ABI and passes the authority bundle validator.

## Performance bounds

The implementation preserves the runtime performance laws:

- no whole-store hash or closure in ordinary turns;
- no per-turn retraining;
- no regex-per-designation scan;
- bounded normalizations, spans, grounding hypotheses, construction matches, semantic hypotheses, and semantic candidates;
- sparse indexed Stage-10 retrieval;
- generation/revision keyed cache refresh;
- no durable writes before Stage 13.

## Acceptance coverage

The focused suite verifies:

- reversible contraction alternatives for `What's`;
- semantic equivalence of contracted and expanded name queries;
- learned-data lookup before probing for `lol`;
- first-class learning query and Response CSIR for a novel form;
- same-clause partial meaning preservation;
- user name admission followed by proof-bearing retrieval;
- bounded trie matching;
- absence of a concept default in reviewed acquisition;
- substantial fixed-ABI conversational seed data.
