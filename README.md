# CEMM — Contextual Event Memory Model

CEMM is a learning-first grounded semantic kernel.

> **Repository status:** the current executable baseline remains v3.4.7 until the v3.5 cutover is implemented and verified. The active documentation specifies the v3.5 target architecture. Do not describe v3.5 as implemented, wired, authoritative, or verified until the corresponding release gates pass.

## v3.5 direction

v3.5 rebuilds CEMM around:

- data-driven referent types;
- inherited knowledge-facet entitlements;
- multimodal state and event timelines;
- explicit claim, proposition, evidence, and knowledge separation;
- generic state-transition and capability-dependency contracts;
- learning packages and grounding frontiers;
- stakeholder-relative impact and importance;
- response meaning generated before language realization;
- multilingual grammar rather than per-predicate sentence templates.

```text
multimodal evidence
→ referent and schema candidates
→ referent type/facet projection
→ UOL meaning hypotheses
→ selected MeaningBundle
→ claims, knowledge, learning, and events
→ state/capability transitions
→ impact, importance, goals, and operations
→ response UOL
→ multilingual realization
→ semantic verification
```

## Canonical documentation

Read these in order:

1. [`AGENTS.md`](AGENTS.md)
2. [`ARCHITECTURE.md`](ARCHITECTURE.md)
3. [`docs/architecture/TERMINOLOGY.md`](docs/architecture/TERMINOLOGY.md)
4. [`docs/architecture/FOUNDATIONAL_KNOWLEDGE_ARCHITECTURE.md`](docs/architecture/FOUNDATIONAL_KNOWLEDGE_ARCHITECTURE.md)
5. [`docs/architecture/LEARNING_ARCHITECTURE.md`](docs/architecture/LEARNING_ARCHITECTURE.md)
6. [`docs/architecture/CLAIMS_EVENTS_STATE_AND_IMPACT.md`](docs/architecture/CLAIMS_EVENTS_STATE_AND_IMPACT.md)
7. [`docs/architecture/UOL.md`](docs/architecture/UOL.md)
8. [`CORE_LOOP.md`](CORE_LOOP.md)
9. [`docs/architecture/DATA_ARCHITECTURE.md`](docs/architecture/DATA_ARCHITECTURE.md)
10. [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md)
11. [`ACCEPTANCE_CONTRACT.md`](ACCEPTANCE_CONTRACT.md)

Historical contracts live under `docs/archive/`. Release evidence lives under `docs/releases/`. Neither overrides the canonical files above.

## Status vocabulary

- **specified** — required by the active contracts;
- **implemented** — code/data exists;
- **wired** — the canonical runtime invokes it;
- **authoritative** — no competing path makes the same decision;
- **verified** — end-to-end tests prove it.

## Development

```bash
python -m venv .venv
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
pytest -q
python -m cemm --chat
```

The v3.4.7 runtime remains a migration source and behavioral baseline. It is not the authority for new v3.5 semantic design.
