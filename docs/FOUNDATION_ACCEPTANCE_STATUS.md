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
| Newly reviewed entity and predicate synonyms inherit semantics without form-pack regeneration, reject stale authority generations and survive restart | `test_foundation_reviewed_snapshot_reuse.py` | Reviewed file-snapshot publication, not authenticated live conversational teaching |
| Real R3 learning REQUEST plus externally signed reviewer decision commits the alias through the existing effect gateway | `test_foundation_reviewed_learning_effect.py` | Approval authentication and signing-key issuance must run in a separate trusted reviewer service |
| One active learning obligation, bounded four-turn expiry and later renewal | `test_foundation_reviewed_learning_effect.py` | Expired rows are retained as immutable historical evidence; cleanup/retention policy remains |
| Atomic SQLite approval, nonce/plan single-use, effect receipt, world revision and obligation resolution | `test_foundation_reviewed_learning_effect.py` | SQLite reference backend; not yet certified for distributed transactions |
| Signed review evidence survives restart, tampered/forged and replayed approvals fail, a forged world fact cannot enter the approved alias index | `test_foundation_reviewed_learning_effect.py` | Signed handoff source must be retained by an external review service; production key rotation and operator audit remain |
| Independently reviewed new entity aliases transfer into evidence-backed text queries after approval and restart | `test_foundation_reviewed_learning_effect.py` | Exact reviewed target reuse, not autonomous ontology creation |
| Read-only candidate English assertions are independently ORIENT/PROPOSE/VERIFY reparsed and compared by canonical answer expression with fresh evidence; wrong names, direction, scope and illocution fail closed | `test_foundation_surface_equivalence.py` | A bounded positive QUERY answer checker only; no text generation or general R5 realization |
| A restricted grammar-owned reference generator constructs supported binary-relation answers from reviewed designation facts, then independently reparses and rejects mismatched candidates | `test_foundation_reference_generation.py` | Verified **one-clause** SVO fragment only; not neural R5 or general language competence |
| Signed learned synonyms and original designations reparse into one proof-backed answer graph across restart | `test_foundation_surface_learning_integration.py` | The same parser can share systematic errors; independent gold remains mandatory |
| Four typed R3 modes and explicit no-effect for QUERY/SIMULATE | `test_foundation_modes.py` | R3 post-VERIFY canaries, not complete surface-to-surface mode admission |
| SQLite restart with revision preservation | `test_foundation_restart.py` | Not distributed concurrency/recovery certification |
| Cross-connection SQLite revision pins refresh all current store dimensions; stale response surfaces are rejected even when only session/effects changed | `test_foundation_live_revisions.py` | Bounded reference SQLite isolation, not distributed snapshot transactions |
| Persistent semantic ABI fingerprint pins exact linked authority content, English form pack and proposal model | `test_foundation_contract_pinning.py` | Same-generation content drift and unpinned legacy stores fail closed; explicit migration remains required |
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
- `yoz means hello`: ordinary statement stays attributed; it cannot publish.
  `learn yoz means hello` produces a reviewable R3 learning obligation; after
  independent signed approval, EFFECT records a new, rev-pinned world designation
  of existing `event:greeting`, usable in subsequent/restarted sessions.
- `What is your name?`: unresolved without a reviewed, indexed name fact.

## Reference surface content canary

For a supported reviewed query `Who owns the book?` with one independently
observed owner, the candidate `Alice owns the book.` reparses to the exact
bound answer expression while world, session and effect revisions remain
unchanged. `Bob owns the book.`, question-shaped substitutes, unlicensed
indefinites, reversed roles, new predicates and compound unsupported clauses
must be rejected. After approved lexical learning of `tome`, both
`Alice owns the tome.` and `Alice owns the book.` reparse to the same
canonical content. This is an exact **candidate verification** boundary,
not learned surface generation.

See `docs/SURFACE_EQUIVALENCE_BOUNDARY.md` for its restricted scope, the
shared-parser limitation and independent-evaluation requirements.

## Release blockers, in dependency order

1. **Reviewer-service production integration**: the library now supports
   real R3 REQUEST -> stored obligation -> independently HMAC-signed review ->
   atomic R3 EFFECT-committed new designation -> immediate/restarted reuse.
   A standalone enterprise reviewer identity provider/UI, signing-key custody
   and rotation, reviewer segregation-of-duties, revocation/correction,
   distributed ledger/transaction guarantees, and secure review-queue retention
   are not included. An issuer class does NOT authenticate human reviewers.
   Unreviewed chat cannot self-authorize learning or create new atom types.
2. **Independent semantic gold on compositional constructions**: support
   polarity, nested attribution, referent identity/coreference, quantified
   scope, temporally qualified facts, and proof-bearing causal/conditional
   semantics rather than structurally valid but ineffective graph wrappers.
3. **Real linguistic realization**: the reference foundation now *checks*
   supplied candidate sentences AND deterministically constructs a strictly
   bounded single-clause SVO answer from approved role bindings and reviewed
   designations. It refuses lexical gaps and verifies the proposed sentence
   by read-only graph re-interpretation before release. It is NOT an R5
   neural generator and cannot produce multi-clause, modal, quantified,
   attributed, temporal or explanatory language. A learned graph-conditioned
   generative owner, independent language understanding gold, context-aware
   inflection/coreference and differential verification remain release gates.
   Marker checks, phrase-specific canned text and output-slot hashes
   are never acceptable substitutes.
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
