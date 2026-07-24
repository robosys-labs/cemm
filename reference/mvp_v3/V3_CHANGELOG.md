# MVP v3 changes

v3 pivots the MVP from mandatory response round-trip verification toward the architecture supported by the current canonical CEMM runtime:

- exact semantic authority remains in the meaning DB / CSIR-like structures;
- a bounded Active Semantic Workspace projects relevant world, self, transition, discourse and proof slots;
- a Transformer ranks workspace relevance instead of attending over the entire store;
- self is represented through orthogonal semantic session state (`interpretation_state`, `epistemic_state`, `response_state`) and explicit transitions;
- foundational operational concepts such as evidence, conflict and meaning are ordinary queryable meaning atoms;
- response construction uses ordinary semantic plans rather than opaque response atoms;
- NLG uses trained surface-plan classes plus exact semantic pointers;
- normal emission uses cheap proof-carrying semantic-pointer verification;
- independent full round-trip is reserved for training/release competence/novelty/risk/audit, matching the updated `RUNTIME_PLAN.md`;
- foundational semantic data no longer embeds hand-written `language_examples` or `realization_examples`; `trainer.py` compiles structured language corpora into pinned language packs;
- interpretation uses short reusable clause programs rather than brittle long autoregressive symbolic document programs;
- immutable authority generation is pinned separately from mutable world/read generations;
- the v3 audit fixed stale self epistemic state after successful proof, Unicode label casefolding, denial-state supersession, inference-budget frontiers, unsupported multi-valued role handling, internal-ID leakage, provisional rule authority, repeated observation identity, and other prior regressions.

See `MVP_ARCHITECTURE.md` for the complete architecture, Stage 0–22 mapping, anti-bloat invariants, implemented coverage and explicit gaps.
