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
`docs/DOCUMENT_AUTHORITY.json`: the approved 2026-08-02 semantic-algebra
amendment and the 2026-07-31 corrective-replay design/plans supersede conflicting
execution or completion claims in the July 29 and July 30 documents. The
amendment does not reactivate those superseded plans. Generated artifacts and inherited receipts are evidence,
not authority. The append-only replay status ledger is introduced by G0 Task 2.

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
Semantic Switch Program ABI: 2
Semantic Expression ABI: 1
Source Coverage ABI: 2
Proposal Result ABI: 2
Verification Batch ABI: 2
Verified Meaning ABI: 1
Phase Receipt ABI: 2
Gap Receipt ABI: 1
Learning Plan ABI: 2
Response Meaning ABI: 2
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
