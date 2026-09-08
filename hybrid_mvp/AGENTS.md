# CEMM Authoritative Hybrid MVP — Governing Agent Instructions

**Status:** highest-priority implementation contract within `hybrid_mvp/` only
**Runtime cutover: hard**

This is the subtree-level constitution for the CEMM Authoritative Hybrid MVP.
It does not override repository-root authority. It is a hard cutover from the legacy stage-bound runtime. It carries
no backward-compatible runtime, ABI adapter, legacy candidate family, checkpoint
loader, migration branch, or legacy behavioral test whose only purpose is
preserving the superseded architecture. Useful semantic data and independently
valid safety assertions may be regenerated under the new contracts; obsolete
structure is deleted.

## Authority and scope

This contract governs only `hybrid_mvp/`. The repository-root `../AGENTS.md`
continues to govern the root runtime, and Hybrid MVP adoption at root requires a
separate reviewed decision. Document precedence within this subtree is owned by
`docs/DOCUMENT_AUTHORITY.json`. Immediately beneath this contract, the approved
2026-09-07 foundation-proof amendment and implementation plan own the current
execution route. They supersede the September 3 closure and narrow unresolved-
designation sequencing, not the August 29 R4.1 data/supervision protections.
The August 29 amendment retains precedence over conflicting older partition,
feasibility, proposal-gold, realization-target and calibration instructions.
The August 2 semantic-algebra amendment and July 31 corrective-replay laws
retain their classified authority beneath these documents. Generated artifacts,
the September 7 audit and inherited receipts are evidence, not authority.
Only `governance/replay_status.jsonl` owns replay status and admission identities;
this routing neither promotes a phase nor reactivates a superseded plan.

## 1. Unchanging thesis

```text
meaning != language
surface evidence != semantic identity
semantic identity != compositional role
candidate program != compiled semantic expression
compiled semantic expression != situated meaning
situated meaning != admitted truth
program identity != semantic identity
admitted truth != executable external operation
response meaning != response wording
training data != semantic authority
```

CEMM has one semantic brain. Language, sensors, dialogue and operation output
supply evidence. The exact semantic plane owns identities, operators, roles,
facts, state, rules, frames and proof. Dynamic computation proposes and ranks
candidates but cannot invent semantic authority.

## 2. Fixed kernel

Exactly five persistent application operators exist:

```text
op:designation
op:type
op:relation
op:state
op:event
```

Learning, naming, capability, memory, desire, speech, modality, correction and
dialogue are expressed through ordinary five-operator expressions, scopes,
event/state structures, policies and obligations. They are not additional
kernel operators or phrase intents.

A `SemanticSwitchProgram` is an ordered construction derivation. VERIFY compiles
it exactly into a derivation-independent canonical `SemanticExpression` forest
with explicit applications, roots, roles, fillers, scopes, links and binders.
`VerifiedMeaning` binds that expression to grounding, source coverage,
compilation proof, verification receipt, revision pin and program lineage.
EVALUATE receives `VerifiedMeaning` plus independently verified
`SituationContext`; it never treats a raw program or program hash as meaning.

Two programs may compile to one expression. Similar action shapes with different
dynamic pointers, roles, scope or roots may compile to different expressions.
Evidence geometry remains in the verification envelope unless source or
attribution is itself semantic content.

## 3. Six-phase runtime

The runtime is a six-phase semantic kernel. The phases are mathematical
ownership boundaries, not separate services and not a constitutional module
count:

```text
ORIENT → PROPOSE → VERIFY → EVALUATE → EFFECT → REALIZE
```

Stage 0–22 ordering is not an activation invariant. The legacy stage-bound
architecture is superseded; no code path may branch on a legacy stage number.

- **ORIENT** captures only the context required for the current cycle.
- **PROPOSE** produces bounded `SemanticSwitchProgram` candidates from evidence
  and orientation.
- **VERIFY** independently validates the complete ordered program, exactly
  compiles it into canonical semantic expressions, proves the program-to-expression
  mapping and selects/merges alternatives by expression identity.
- **EVALUATE** consumes one `VerifiedMeaning` plus `SituationContext` and
  produces one typed `Decision`; a raw program is invalid input.
- **EFFECT** is the only owner of world mutation and external operation
  invocation; it accepts verified decisions and returns idempotent receipts.
- **REALIZE** constructs `ResponseMeaning` from the exact decision, proof,
  blockers, effects and obligation, then verifies the realized surface.

## 4. Candidate ABIs

The following are active target ABIs for the corrective replay. Existing
Program ABI 1 implementations and descendants remain quarantined; a target ABI
is not implemented or activated until its owning replay admission succeeds:

```text
Semantic Contribution ABI: 1
Proposal Context ABI: 2 (unadmitted repair target)
Semantic Switch Program ABI: 2
Semantic Expression ABI: 2 (unadmitted repair target)
Compilation Proof ABI: 1
Source Coverage ABI: 2
Proposal Result ABI: 2
Verification Batch ABI: 2
Verified Meaning ABI: 1
Phase Receipt ABI: 2
Gap Receipt ABI: 1
Learning Plan ABI: 3
Generic Dialogue Obligation ABI: 1
R3 Artifacts ABI: 2
Effect / No-Effect Receipt ABI: 2
Response Meaning ABI: 3
Realization Receipt ABI: 2
```

Owner file, serialized/transient status, validator and intended activation gate for
each candidate ABI are recorded in `docs/ABI_REGISTRY.md`.

## 5. Forbidden behaviors

The following are explicitly forbidden:

- **stage-number ownership:** no runtime branch may select semantics or control
  flow based on a legacy stage number;
- **compatibility runtime branches:** no code path exists solely to preserve the
  superseded architecture;
- **raw-surface semantic dispatch:** no phrase-string semantic dispatch in the
  runtime; surface evidence is not semantic identity;
- **internal-ref lexicalization:** internal refs are not language and must not
  be exposed as user-visible designations by spelling;
- **implicit atom creation:** the proposer/ranker cannot create atoms, relation
  types, state dimensions, event schemas, capabilities, permissions or
  adapters; unknown literals remain frontiers;
- **program-as-meaning:** program identity, action vocabulary identity and
  semantic-expression identity are distinct; EVALUATE cannot consume a raw
  program and semantic equality cannot use action-set, marker or string equality;
- **self-authored gold:** bootstrap proposal output cannot become reviewed
  semantic-expression gold;
- **self-satisfying corpus gates:** required semantic minima are reviewed input;
  a solver cannot derive, trim, or weaken them to make a partition pass;
- **input-as-output supervision:** user input surfaces cannot become response
  realization targets;
- **integrity-only admission:** artifact reconstruction without class-local
  semantic usability and independent gold is insufficient for R5;
- **unverified effects:** `EffectGateway` is the only owner of world mutation
  and external operation invocation, and only accepts verified decisions;
- **unverified response focus:** verified semantic focus is recorded only after
  round-trip canonical-expression equivalence plus required situated qualifiers.

## 6. Performance bounds

Normal cycles remain bounded. The frozen release bounds are owned by
`RuntimeConfig` in `src/cemm_authoritative_hybrid/config.py`:

- 64 input tokens;
- 8 designation candidates per span;
- 4 affordance profiles per target;
- 16 orientation/retrieval alternatives;
- 32 constrained beam states per decoding step;
- 48 complete candidates;
- 24 semantic applications;
- graph depth 6;
- one operation re-entry;
- one pending learning obligation.

Budget exhaustion yields a typed frontier, never a phrase fallback.

## 7. Definition of completion

A change is complete only when code, authority data, deterministic generators,
migrations, active docs, activation validation and executable tests agree.
Partial implementation must remain explicitly disabled rather than hidden
behind permissive fallback behaviour. No active release test may use skip or
xfail markers; final release gates contain zero skips, xfails, xpasses,
fallback paths, compatibility adapters or unverified surfaces.

## 8. Current foundation-proof contract

The approved
[foundation amendment](docs/superpowers/specs/2026-09-07-foundation-proof-corrective-amendment.md)
and [implementation plan](docs/superpowers/plans/2026-09-07-foundation-proof-implementation-plan.md)
own current work. Inspect the complete independent semantic case matrix, record
missing owners together and repair the earliest dependencies. The September 3
closure and unresolved-designation designs/plans are historical evidence; their
stop-at-first-unrelated-failure route no longer governs. Preserve their exact
stop records and independently valid acyclic frame/canonical designation work.
Task 2 may first contain the already-audited false atom-kind answer; broader
capability repairs follow the independent matrix, as the amendment specifies.

Keep graph validity, intended-meaning correspondence, evidential support and
permission/current executability separate. The historical known-definition
pass proved traversal, not a correct definition. The atom-kind answer to a
generic question is retired; suppressing it is containment, not completion of
definition/query projection or a useful response loop. Same-parser round-trip
consistency still requires independent meaning contrasts.

The foundation permits an explicitly development-only compositional response
reference through existing semantic owners. It must preserve roles, scopes,
perspective, provenance and uncertainty; it is neither learned output, a normal
fallback nor a second semantic runtime. Normal verified focus still requires
the existing exact realization-equivalence checks. No new phase or gate is added.

Bulk R4.1 authoring, review/export, purpose allocation, realization-recipe review,
corpus expansion and source-package publication remain frozen. Historical review
selections and action logs are diagnostic evidence, not semantic gold. R5
training, selection, calibration, frozen evaluation and realization activation
remain unavailable until fresh R4.1 admission; no pilot training is authorized
before that admission and explicit isolated R4.1-compliant data authorization.

No fake designation, default-to-concept target, internal-ref lexicalization or
surface-phrase dispatch is authorized. Existing-target alias learning retains
capability, permission, provenance and transactional effect checks; new identity
acquisition remains separate. Later external research is a bounded permissioned
consumer of an exact unknown QueryResult, never grounding or automatic authority.
This increment authorizes no network adapter or root adoption.

Continuation answers must bind the exact pending snapshot and the original
gateway-persisted query evaluation, not only a query-ref string. Unknown-query
journal retention, plan materialization and proposal persistence do not authorize
alias publication. LearningPlan ABI 3 binds the original generic obligation through its
required, identity-covered `source_obligation_ref`; materialization returns that
exact record. A learning proposal retains its canonical meaning, evaluation,
plan and original source-query witnesses in the existing effect journal. Its
terminal no-effect receipt consumes the answer turn once, without world mutation,
renewal or completion of the pending record. Exact journal-bound retries preserve
that receipt, including after restart; unfinished proposals cannot repin their
source reservation. This is not authenticated review or alias acquisition.
The duplicate plan-derived obligation type and direct learning-outcome writer
are removed; do not restore either as a compatibility path. The candidate
out-of-band `publish_learning` path uses the existing EFFECT journal and atomic
commit owner. It defaults to denial without a separately configured store-bound
review verifier; dialogue cannot install that verifier or issue its signed grant.
Its verification and remaining runtime integration are tracked in the foundation
plan. The candidate shared admitted-designation reader reconstructs actual
committed publication evidence under a bounded, revision-pinned store snapshot;
a reviewer-looking fact label is not admission. It distinguishes the canonical
designation identity from its persisted world-fact and publication provenance.
Grounding, designation composition and lexical query must share this reader
when integrated; do not reconnect mutable-first lookup or silently truncate
alternatives. Publication must preserve the original answer history and complete the
original pending record only with its atomic successful receipt. Automatic generic query-continuation
creation is implemented in the current Task 5 repair, with acceptance and
remaining dependencies tracked in the foundation plan. The user approved its
four-subsequent-same-session-turn lifecycle on September 8, as recorded in the
foundation implementation plan. Do not reopen that policy approval, silently
renew a live continuation, or mistake lifecycle approval for alias-publication
authority or repair completion.

Reviewed semantic frames are explicit manifest-owned authority, not optional
ambient files. Link and validate their generation, content and target/signature
compatibility at activation; consume the linked target index during grounding.
A missing, stale or malformed registered frame source must fail linking, never
silently erase refinements into kind defaults. Preserve all existing reviewed
profile fields when changing authority generations. The foundation plan records
the September 8 preservation repair and remaining continuation/publication work.

Test names and historical successor metadata are not implementation authority.
A category smoke check cannot prove unrelated assertion identities. Use explicit
assertion-specific evidence; unreviewed successor mappings must fail descriptively,
not inherit a cached pass. Preserve frozen evidence and valid protections without
restoring retired paths. A directly inserted fact with a reviewer-looking source
string is not authenticated alias acquisition. The foundation plan records the
stale-test audit and approved scope correction; it does not add a runtime gate.

Pure transition previews are not write authority. Do not restore dormant direct
commit helpers to satisfy historical tests. A new effectful request must retain
its verified current revision pin at journal reservation; the gateway must not
silently rebase a stale decision onto newer state. An exact journal-bound retry
is different: authenticate its persisted request and preserve terminal receipt
identity without a second invocation. Keep these checks in the existing effect
and transactional persistence owners, not a parallel writer or validation tier.
