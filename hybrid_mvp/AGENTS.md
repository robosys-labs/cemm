# CEMM Authoritative Hybrid MVP — Governing Agent Instructions

**Status:** highest-priority implementation contract for this worktree
**Runtime cutover: hard**

This is the project-level constitution for the CEMM Authoritative Hybrid MVP
worktree. It is a hard cutover from the legacy stage-bound runtime. It carries
no backward-compatible runtime, ABI adapter, legacy candidate family, checkpoint
loader, migration branch, or legacy behavioral test whose only purpose is
preserving the superseded architecture. Useful semantic data and independently
valid safety assertions may be regenerated under the new contracts; obsolete
structure is deleted.

## 1. Unchanging thesis

```text
meaning != language
surface evidence != semantic identity
semantic identity != compositional role
candidate != settled meaning
settled meaning != admitted truth
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
dialogue are expressed through ordinary five-operator graphs, scopes,
event/state structures, policies and obligations. They are not additional
kernel operators or phrase intents.

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
- **VERIFY** independently recomputes structural, reference, scope, capability
  and transition legality; invalid candidates receive typed rejection codes.
- **EVALUATE** consumes one verified program and produces one typed `Decision`.
- **EFFECT** is the only owner of world mutation and external operation
  invocation; it accepts verified decisions and returns idempotent receipts.
- **REALIZE** constructs `ResponseMeaning` from the exact decision, proof,
  blockers, effects and obligation, then verifies the realized surface.

## 4. Active ABIs

The following ABIs are active for this MVP:

```text
Semantic Contribution ABI: 1
Semantic Switch Program ABI: 1
Coverage ABI: 1
Phase Receipt ABI: 1
Gap Receipt ABI: 1
Learning Plan ABI: 1
Response Meaning ABI: 1
Realization Receipt ABI: 1
```

Owner file, serialized/transient status, validator and activation gate for each
ABI are recorded in `docs/ABI_REGISTRY.md`.

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
- **unverified effects:** `EffectGateway` is the only owner of world mutation
  and external operation invocation, and only accepts verified decisions;
- **unverified response focus:** verified semantic focus is recorded only after
  exact realization equivalence verification.

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
