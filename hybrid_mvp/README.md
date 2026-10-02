# CEMM Authoritative Hybrid MVP

An isolated development proof for a neural-symbolic semantic cognition runtime.
Its target combines CEMM's exact semantics with learned proposal and realization;
an admitted learned model and a complete useful conversation loop are not claimed.
Current work repairs and tests the interpretation-to-answer foundation.

**Runtime cutover: hard.** This is a hard cutover from the legacy stage-bound
runtime. It carries no backward-compatible runtime, ABI adapter, legacy
candidate family, checkpoint loader, migration branch, or legacy behavioral test
whose only purpose is preserving the superseded architecture.

## Six-phase semantic kernel

The runtime is a six-phase semantic kernel. The phases are mathematical
ownership boundaries, not separate services:

```text
ORIENT → PROPOSE → VERIFY → EVALUATE → EFFECT → REALIZE
```

- **ORIENT** captures only the context required for the current cycle.
- **PROPOSE** produces bounded `SemanticSwitchProgram` candidates from evidence
  and orientation.
- **VERIFY** independently validates and exactly compiles ordered program
  derivations into canonical `SemanticExpression` values, then selects by
  expression identity.
- **EVALUATE** consumes `VerifiedMeaning` plus verified situation context and
  produces one typed `Decision`; it never consumes a raw program.
- **EFFECT** is the only owner of world mutation and external operation
  invocation; it accepts verified decisions and returns idempotent receipts.
- **REALIZE** constructs `ResponseMeaning` from the exact decision, proof,
  blockers, effects and obligation, then verifies the realized surface.

Stage 0–22 ordering is not an activation invariant. The legacy stage-bound
architecture is superseded.

## Replay status and next authority

Current replay status and exact admission identities are derived only from
[`governance/replay_status.jsonl`](governance/replay_status.jsonl). This page
does not copy or promote phase status. Use
[`docs/DOCUMENT_AUTHORITY.json`](docs/DOCUMENT_AUTHORITY.json) for document
precedence. The approved
[foundation amendment](docs/superpowers/specs/2026-09-07-foundation-proof-corrective-amendment.md)
and [implementation plan](docs/superpowers/plans/2026-09-07-foundation-proof-implementation-plan.md)
own current work, with the
[August 29 R4.1 amendment](docs/superpowers/specs/2026-08-29-r4-1-data-supervision-corrective-amendment.md)
retaining all data and supervision protections. The September 3 closure and
unresolved-designation documents are historical evidence, not the active route.

Exact graph acceptance is not proof that the graph answers the intended question.
The historical known-definition pass established traversal despite an incorrect
atom-kind answer. Removing that answer is containment; useful open-query and
response behavior remain separate acceptance obligations. Inspect the complete
independent foundation matrix before repairing its missing semantic owners.

An explicitly development-only compositional response reference is permitted
through existing owners. It is not learned output, a product fallback or release
activation, and cannot bypass exact equivalence for normal verified focus.
Bulk R4.1 authoring, review/export, purpose allocation, realization-recipe review,
corpus expansion and source-package publication remain frozen.

R5 training, selection, calibration, frozen evaluation and realization
activation are unavailable until a fresh R4.1 admission proves meaningful
purpose-class semantic coverage and independent derivation/realization gold.
No pilot training is authorized before fresh R4.1 admission and explicit isolated
R4.1-compliant data authorization. No network research adapter is authorized by
the foundation increment.

`SemanticSwitchProgram` is a construction procedure, not canonical meaning.
Program identity is ordered and includes every dynamic pointer and binding.
`SemanticExpression` is the derivation-independent semantic identity compiled
from that procedure. `VerifiedMeaning` carries expression, grounding, coverage,
proof, revision and derivation lineage. Distinct derivations may express one
meaning; pointer-distinct meanings must not collapse.

## Five persistent operators

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

## Safety and governance properties

- No phrase-string semantic dispatch in the runtime.
- No default-to-concept or implicit atom creation.
- Unknown literals remain frontiers; `do you have a telescope?` does not create
  `entity:telescope`.
- Authority, world, sessions, episodes and model artifacts are separate
  revision-pinned stores.
- Recursive proposition graphs support embedded applications and enforce bounded
  depth, application count and acyclicity.
- Reviewed rules support bounded inference and proof lineage.
- Existential witnesses are transient and never become durable entities.
- Capability, permission and adapter dependencies are checked independently.
- Queries and simulations cannot mutate world memory.
- Attributed content is not automatically admitted as world truth.
- The release realization target is constrained and learned; emission is authorized only
  after round-trip canonical-expression equivalence plus situated qualifiers.
  Release static text is limited to closed critical-failure semantics; the
  foundation's development-only reference is not a release path.

## Frozen configuration

The release configuration is frozen and bounded, owned by
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

## Installation

Requires Python 3.11+ and PyTorch.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
```

## Development diagnostics — isolated state

From `hybrid_mvp/`, in PowerShell:

```powershell
$demoStore = Join-Path ([IO.Path]::GetTempPath()) ("cemm-demo-" + [guid]::NewGuid().ToString("N") + ".db")
$env:PYTHONPATH = "src"
python -m cemm_authoritative_hybrid.cli --interactive --development-reference --store $demoStore
```

`--development-reference` is controlled diagnostic wording, not learned R5
realization or an authorized response receipt. The isolated store contains no
production authority changes. `/trace` includes exact meaning and provenance;
`/new` starts a separate session; `/quit` ends the conversation.

Independent role controls include `Bob likes you`, `Alice likes me` and
`Bob likes Alice`. Capability questions `Can you respond?` and
`Can you learn aliases?` produce supported answers with the exact subject.
`Who likes Bob?`, `Bob likes who?` and `Who is a mother?` preserve the queried
role; an empty store yields UNKNOWN, not an invented person or a negative fact.
Unknown lookup: `What does zorbulate mean?`.

This is not a general conversation demo. Direct greetings still yield attributed
claim wording rather than a selected reciprocal response. Input inflections
such as `I like Bob`, ambiguous description/definition requests, actual definition
content and other unresolved owners remain open under the foundation plan.
Neither an unresolved interpretation nor a missing output rule counts as a
supported answer.

## Run tests

During corrective replay, a plain `pytest` invocation is diagnostic only; it is
not an admission receipt. Use the focused owner command specified by the active
phase plan and the admitted validation runner for governed owner, phase and
admission tiers. No test command alone advances replay status; only a verified
admission receipt consumed by the append-only ledger can do so.

No active release test may use skip or xfail markers. Final release gates
contain zero skips, xfails, xpasses, fallback paths, compatibility adapters or
unverified surfaces.

## Documentation

- [`AGENTS.md`](AGENTS.md) — Hybrid MVP constitution and hard-cutover contract.
- [`docs/DOCUMENT_AUTHORITY.json`](docs/DOCUMENT_AUTHORITY.json) — machine-readable document precedence and scope.
- [Foundation proof amendment](docs/superpowers/specs/2026-09-07-foundation-proof-corrective-amendment.md) — current semantic/response proof contract, with no phase admission.
- [Foundation proof implementation plan](docs/superpowers/plans/2026-09-07-foundation-proof-implementation-plan.md) — single current execution checklist.
- [`docs/superpowers/specs/2026-08-29-r4-1-data-supervision-corrective-amendment.md`](docs/superpowers/specs/2026-08-29-r4-1-data-supervision-corrective-amendment.md) — current R4.1 data/supervision repair contract and R5 prerequisite.
- [`docs/superpowers/specs/2026-08-02-hybrid-semantic-algebra-corrective-replay-amendment.md`](docs/superpowers/specs/2026-08-02-hybrid-semantic-algebra-corrective-replay-amendment.md) — active Program→Expression corrective amendment.
- [`docs/REPLAY_GOVERNANCE.md`](docs/REPLAY_GOVERNANCE.md) — precedence, evidence and status-ownership boundaries.
- [`docs/superpowers/specs/2026-07-31-hybrid-mvp-corrective-replay-admission-design.md`](docs/superpowers/specs/2026-07-31-hybrid-mvp-corrective-replay-admission-design.md) — approved corrective-replay design.
- [`docs/superpowers/plans/2026-07-31-hybrid-mvp-corrective-replay-master-plan.md`](docs/superpowers/plans/2026-07-31-hybrid-mvp-corrective-replay-master-plan.md) — governing replay sequence and admission boundaries.
- [`docs/ABI_REGISTRY.md`](docs/ABI_REGISTRY.md) — active target ABIs and their activation gates.
