# CEMM Authoritative Hybrid MVP

An isolated, executable neural-symbolic semantic cognition runtime that combines
CEMM's strongest exact semantics with a true-hybrid ownership model and a real
trainable PyTorch ranker.

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
- **VERIFY** independently recomputes structural, reference, scope, capability
  and transition legality; invalid candidates receive typed rejection codes.
- **EVALUATE** consumes one verified program and produces one typed `Decision`.
- **EFFECT** is the only owner of world mutation and external operation
  invocation; it accepts verified decisions and returns idempotent receipts.
- **REALIZE** constructs `ResponseMeaning` from the exact decision, proof,
  blockers, effects and obligation, then verifies the realized surface.

Stage 0–22 ordering is not an activation invariant. The legacy stage-bound
architecture is superseded.

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
- Deterministic realization emits a semantic verification receipt and does not
  expose internal refs.

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

## Run tests

```bash
pytest
```

No active release test may use skip or xfail markers. Final release gates
contain zero skips, xfails, xpasses, fallback paths, compatibility adapters or
unverified surfaces.

## Documentation

- [`AGENTS.md`](AGENTS.md) — project-level constitution and hard-cutover contract.
- [`docs/ABI_REGISTRY.md`](docs/ABI_REGISTRY.md) — active ABI owner files, validators and activation gates.
- [`docs/superpowers/specs/2026-07-29-authoritative-mvp-completion-design.md`](docs/superpowers/specs/2026-07-29-authoritative-mvp-completion-design.md) — approved architecture-completion specification.
- [`docs/superpowers/plans/2026-07-29-authoritative-mvp-master-roadmap.md`](docs/superpowers/plans/2026-07-29-authoritative-mvp-master-roadmap.md) — authoritative master roadmap and milestone-plan index.
