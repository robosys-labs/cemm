# Hybrid Semantic Algebra Corrective-Replay Amendment

**Status:** approved target amendment; implementation remains red until admitted
**Date:** 2026-08-02
**Scope:** `hybrid_mvp/` only
**Root adoption:** requires a separate reviewed migration decision
**Source review package:** `hybrid_semantic_algebra_docs`

This amendment is subordinate only to `hybrid_mvp/AGENTS.md` and supersedes every
conflicting semantic-object, identity, corpus, evaluation and realization claim
in the earlier Hybrid MVP documents. It does not reactivate superseded July-29
or July-30 execution plans and does not alter root-runtime authority.

Stage 0–22 remains retired inside the Hybrid MVP and the six-phase runtime
remains a hard cutover. The additional correction is that a proposed
construction program is not settled semantic meaning. The active replay target
requires one coordinated Program ABI 2 / Semantic Expression ABI 1 cut before
any R1 descendant can be admitted.

## Documents and code cross-checked

- `hybrid_mvp/AGENTS.md`
- `hybrid_mvp/README.md`
- `hybrid_mvp/docs/ARCHITECTURE.md`
- `hybrid_mvp/docs/ABI_REGISTRY.md`
- completion design and master roadmap
- M2 and M3 implementation plans
- `programs.py`
- `propositions.py`
- `verifier.py`
- `runtime.py`

## Confirmed defects

### 1. Duplicate semantic program authority

`programs.py` defines the intended recursive `SemanticSwitchProgram`, while
`propositions.py` defines a second legacy program wrapping `PropositionGraph`.
`runtime.py` imports the legacy class. This violates the constitution's one-type
and hard-cut rules.

### 2. No canonical compiled-meaning ABI

The ABI registry defines the program and coverage ABIs but no
`SemanticExpression` or `VerifiedMeaning`. `VerificationResult` carries a
legality verdict and coverage receipt, not the canonical graph produced by exact
compilation.

### 3. EVALUATE consumes the wrong object

The docs and runtime protocol say EVALUATE consumes a verified program. That
makes derivation syntax semantic authority and prevents multiple valid
derivations from sharing one meaning.

### 4. Program identity loses semantic information

`action_encoding_hash` sorts structural action IDs and excludes dynamic pointer
values. Reordering non-commutative actions or swapping Alice/Bob can retain the
same hash. This hash can identify a model action vocabulary, but not a concrete
program instance.

### 5. Claimed recursion is not implemented by the active verifier/masker

The current transition predicate allows only one `select_designation` and one
`instantiate_operator` for the entire prefix. Nested links point to action refs,
not canonical application nodes. This cannot prove the documented multiple
applications, multiple roots and recursive proposition graph.

### 6. VERIFY validates but does not compile

The verifier checks action syntax and selected graph-like constraints but has no
total exact program-to-expression compiler. Roots and depth therefore remain
program metadata rather than independently reconstructed semantic structure.

### 7. The runtime preserves forbidden compatibility behavior

`runtime.py` contains duplicate result classes, signature inspection,
new-style/old-style result adaptation, broad exception swallowing and
`propose_and_verify()`. These are explicitly forbidden by `AGENTS.md`.

### 8. Scope ontology is internally inconsistent

The current program ABI includes both `polarity` and `negation` as scope kinds,
but negation is a polarity value. Attribution is architecturally required but
absent from that closed set. The expression ABI must normalize these distinctions
rather than accumulating overlapping labels.

### 9. Realization direction is inconsistent

`ARCHITECTURE.md` currently describes deterministic verified realization, while
the confirmed completion design requires a learned constrained normal realizer
plus exact equivalence verification. Deterministic reviewed text is valid only
for a closed critical-failure channel.

## Correct architectural chain

```text
EvidencePacket
→ Orientation + ProposalContext
→ ProposalResult[SemanticSwitchProgram]
→ ExactProgramCompiler + ExactProgramVerifier
→ VerificationBatch[VerifiedMeaning]
→ Decision
→ EffectReceipt | NoEffectReceipt
→ ResponseMeaning
→ constrained realization candidates
→ round-trip SemanticExpression
→ RealizationReceipt
```

## Required implementation order

1. Freeze and inventory all duplicate public classes and callers.
2. Introduce Program ABI v2 and Semantic Expression ABI v1 together.
3. Implement full program and expression canonicalization.
4. Implement a total exact compiler.
5. Make verification receipts carry compiled expressions and proofs.
6. Change EVALUATE and every downstream owner to `VerifiedMeaning`.
7. Remove `propositions.py`, runtime adapters and the shortcut path.
8. Regenerate reviewed contracts and every R4/R5 descendant.
9. Implement expression-based realization equivalence.
10. Re-run structural, corruption, ambiguity, model-dependence and release gates.

## Why this is compatible with CEMM's five-operator thesis

The correction does not introduce a sixth persistent operator. It makes explicit
what the five operators compose into. Scope, links and binders are recursive
expression structure around five-operator applications. The six runtime phases
remain ownership boundaries over these artifacts.

## Normative semantic objects

```text
SemanticSwitchProgram
    ordered, content-addressed construction derivation

SemanticExpression
    derivation-independent canonical semantic forest/root set

VerifiedMeaning
    expression + grounding + coverage + compilation proof + verification
    receipt + revision pin + program lineage

SituationContext
    independently verified force/mode, participants, time, source and
    epistemic/session context supplied alongside VerifiedMeaning
```

`expression_ref` plus the required situated qualifiers is the semantic
comparison key. `verified_meaning_ref` may include derivation and proof lineage
and is therefore not itself the derivation-independent semantic identity.
Evidence geometry and source assignments remain in the verification envelope;
they enter an expression only when source or attribution is part of the meaning.

Canonicalization must define ordered versus reviewed-commutative expression
links and exact graph-isomorphism rules. It may alpha-normalize only local IDs
through a proven bijection and must preserve grounded refs, roles, scope,
polarity, modality, attribution, temporal anchoring and licensed qualifiers.

Use `SemanticExpressionCompiler` as the canonical compiler name. VERIFY must
independently prove that every program action and source assignment was
translated exactly once; validating only compiler output is insufficient.

## Correct replay allocation

- **G0:** make this amendment authoritative, record the Program→Meaning defect
  in baseline findings, and quarantine all Program ABI 1 descendants. The
  existing bounded validator remains the single G0 control plane.
- **R1:** hard-cut duplicate program/result types and shortcuts; introduce
  Program ABI 2, Semantic Expression ABI 1, complete identities, canonical
  expression types, the total compiler, Verification Batch ABI 2 and Verified
  Meaning ABI 1. Until later owners land, the runtime stops at a typed gap.
- **R2:** implement authentic multi-application, multi-root and nested
  construction, every switch action, references, binders, scopes, attribution,
  variables and transitions; independently verify compilation and group
  ambiguity by expression.
- **R3:** make query, epistemic, state, transition, learning, decision, effect
  and response owners consume `VerifiedMeaning.expression` plus explicit
  `SituationContext`. Effects retain `program_ref` only as derivation lineage.
- **R4:** rebuild reviewed gold primarily from expected expression plus situated
  decision/effect/response contracts. Canonical derivations are separate
  training labels; bootstrap output cannot author semantic gold.
- **R5:** retrain only after R4 regeneration and report derivation, expression,
  situated decision and expression-based end-to-end accuracy separately.
- **R6–R8:** use one expression/verified-meaning composition root across all
  surfaces; reject Program ABI 1 descendants; authorize realization only after
  round-trip expression equivalence plus situated qualifiers.

This compilation is work inside the existing VERIFY phase and existing replay
admission DAGs. It adds neither a seventh runtime phase nor an extra normal-cycle
or validation gate. Bounds remain candidate-, action-, application-, root- and
depth-local with generation/revision-keyed indexes.
