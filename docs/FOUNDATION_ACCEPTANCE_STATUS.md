# CEMM foundation — executable acceptance and remaining blockers

**Decision:** structured-semantic reference foundation validated for the
documented subset; **general conversational cognition NOT admitted**.
A green CI/build or deterministic hash does not establish semantic coverage.

## Source and recovery

- PR: https://github.com/robosys-labs/cemm/pull/21 (draft).
- Recovery: `codex/cemm-foundation-end-to-end-20261008`.
- Start commit: `24d8b68a4c9b0c992362a1c2e542579b5f0c4280`.
- Frozen pre-recovery source: `archive/cemm-pre-foundation-20261008`.
- Active wheel/CLI selects one six-phase `cemm_authoritative_hybrid` runtime.
- Previous Stage 0–22 package, root test tooling, historical archive and
  `.lineage-recovery` are absent from the active checkout, not deleted
  from immutable Git history.

## Demonstrated and regression-gated

| Capability / invariant | Gate | Limit |
| --- | --- | --- |
| Root install, wheel hard cut, one public CycleResult, no legacy reachable brain | `test_foundation_public_api.py`, `test_foundation_source_boundaries.py` | Static import graph is conservative, not a general dynamic-loader proof |
| Actual text -> ORIENT/PROPOSE/VERIFY -> R3 decision/effect -> structured ResponseMeaning | `test_foundation_semantic_surface.py` | Realized output is canonical JSON, not validated natural-language prose |
| Strict semantic identity, alpha renaming, role direction and scope distinctions | `test_foundation_algebra.py` | Correct identity does not alone establish executable logical semantics |
| Leading-WH subject variable and grounded post-verbal object | `test_foundation_query_role_direction.py` | English reviewed schema and known designations only |
| Source-backed query answer, exact binding and proof through public runtime | `test_foundation_evidence_bound_query.py` | Trusted evidence injected via the existing reviewed-fact persistence port |
| Multiple incompatible answer bindings produce a typed clarification, not arbitrary first answer | `test_foundation_query_cardinality.py` | Exhaustive set-valued answer ABI still required |
| Indefinite/universal determiners block unsupported scoped semantics | `test_foundation_unlicensed_quantification.py` | Existential/universal evaluation deliberately unavailable |
| Temporal/aspect and causal/purpose/sequence links cannot be inferred from bare fact conjunction | `test_foundation_scope_evaluation.py` | Temporal inference and nonlogical relation semantics deliberately unavailable |
| Query world retrieval respects configured budget, no unbounded table materialization, overflow fail closed | `test_foundation_bounded_retrieval.py` | Indexed predicate/role retrieval and million-fact scale remain unproven |
| Two reviewed-rule inference, proof lineage and nonfabrication | `test_foundation_inference.py` | Verified structured input, not general linguistic understanding |
| Four typed R3 modes and explicit no-effect for QUERY/SIMULATE | `test_foundation_modes.py` | R3 post-VERIFY canaries, not complete surface-to-surface mode admission |
| SQLite restart with revision preservation | `test_foundation_restart.py` | Not distributed concurrency/recovery certification |
| Unreviewed lexical teaching/report cannot silently enter world truth | `test_foundation_epistemic_safety.py` | Does not yet establish authorized acquisition/attributed-query competence |

CI additionally enforces adjacent R2/R3 proposer, verifier, query, effect and
realization-boundary owner regressions. The public-path diagnostic probe is
informational and cannot itself promote a capability.

## Examples: evidence-aware interpretations

- `Who owns the book?`: verified input graph has a subject variable and
  grounded `entity:book` object. With exactly one matching reviewed fact the
  binding and source proof are returned; with none it remains unknown.
- `Who owns a book?`: existential meaning is not established; fail closed,
  rather than quietly treating `a` as the uniquely designated `the`.
- `Alice owns a book.`: cannot be treated as an unqualified specific-book
  assertion; the indefinite construction is unresolved.
- Two distinct owners of the book: typed clarification, not one chosen owner.
- Historical-time query from a current unqualified fact: partial with a typed
  temporal blocker, not supported.
- Causation from two otherwise true propositions: partial with a causal/link
  semantics blocker, not supported.
- `Mary said Bob left.`: currently ambiguous; attribution composition is
  not yet independently proven.
- `yoz means hello`: an ordinary utterance cannot publish new authority;
  authorized learning and reuse are not yet complete.
- `What is your name?`: unresolved without a reviewed, indexed name fact.

## Release blockers, in dependency order

1. **Reviewed acquisition and reactivation**: a reviewer-authorized
   designation commit must atomically join the semantic data and persistent
   world/authority generation, refresh grounding, survive restart, and be
   provably reusable in an unseen compositional query. Ordinary text may not
   self-authorize.
2. **Independent semantic gold on compositional constructions**: support
   polarity, nested attribution, referent identity/coreference, quantified
   scope, temporally qualified facts, and proof-bearing causal/conditional
   semantics rather than structurally valid but ineffective graph wrappers.
3. **Real linguistic realization**: generate from exact ResponseMeaning with
   dynamic bindings and prove graph-equivalent round-trip. Marker checks,
   canned text or output-slot hashes are never acceptance.
4. **Neural ABI repair**: the historical neural proposer still accepts an
   `Orientation`, not the canonical `ProposalContext`, and constructs
   `ProposalResult` with an invalid direct constructor. It remains outside
   the active foundation until reconciled and independently measured.
5. **Query completeness and scale**: reviewed set-valued result ABI,
   indexed bounded retrieval by operator/predicate/role, strict provenance
   and temporal validity; transactional rollback, concurrent writers, and
   enterprise scale are still separate qualifications.
6. **Governed release migration**: changes to reviewed form schemas and R3
   meaning/effect code invalidate older source-pinned R4/R5 receipts.
   Rebuild/review source corpora and artifacts before claiming renewed R4+
   admissions. Historical green results must not be relabelled current.
7. **Package portability**: bundle reviewed authority as an authenticated,
   relocatable release with clean-install/read-only verification.

## Completion law

No change is accepted as **general end-to-end cognition** until previously
unseen supported combinations work through one public text-to-meaning-to-action-
to-language cycle with independently reviewed expected semantics, real
authorization, provenance, restart, and semantic-equivalence verification.

Do not weaken gold, reopen legacy execution paths, or substitute a successful
structured JSON response for verified natural-language cognition.
