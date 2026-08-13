# CEMM Recursive Semantic Composition — Final Implementation Plan

> **Root snapshot scope:** This completed plan is pinned to root preimage
> `f20ed73c1c5d84fd4a468a8de6480cbc9eb767d9`; it is not the current Hybrid MVP
> execution plan. The Hybrid MVP proof is governed by
> [`hybrid_mvp/governance/replay_status.jsonl`](hybrid_mvp/governance/replay_status.jsonl)
> and does not adopt its runtime or admissions into the root runtime. Root
> adoption requires a separate reviewed decision.

**Repository:** `robosys-labs/cemm`  
**Target branch:** `main`  
**Pinned preimage:** `f20ed73c1c5d84fd4a468a8de6480cbc9eb767d9`  
**Compatibility policy:** no backward-compatibility brain, sentence router or legacy semantic path

## Objective

Complete the native semantic spine with bounded recursive proposition composition while retaining one exact Stage 0–22 runtime, the five fixed operators and existing authority/query/store owners.

## Workstream 1 — Proposition Graph ABI 2

- Define transient, immutable proposition applications and graphs.
- Permit only the five kernel operators.
- Require deterministic semantic signatures, application identities, cycle checks, source coverage and bounded depth/size.
- Represent proposition-valued fillers as candidate-local `{"app": application_ref}` links.
- Flatten child-first before Stage 13; never persist graphlets as a second ontology.

## Workstream 2 — Recursive Stage-5 chart

- Make one bounded bottom-up chart the sole semantic-composition orchestrator.
- Reuse the reviewed atomic graph matcher and exact Coverage ABI.
- Preserve N-best alternatives with per-hypothesis state and graphlet budgets.
- Compose reviewed semantic frames, proposition units, scope and reference evidence.
- Convert unresolved known structure into typed composition gaps; lexical learning remains available only for true unknown forms.

## Workstream 3 — Exact compiler and persistence legality

- Preserve exact operator-role validation.
- Permit app-valued fillers only when a reviewed proposition-taking frame licenses the exact operator, predicate and role.
- Distinguish candidate-local links from already persisted app references.
- Resolve local references to exact store signatures and insert children before parents.
- Reject dangling, duplicate, cyclic or unlicensed app links.

## Workstream 4 — Generic frame authority and data cutover

- Add reviewed proposition-taking frames for desire, knowledge, speech, learning and related event content.
- License standalone greeting behavior through the `event:greeting` frame, not a token list.
- Remove `desire_knowledge_designation_query` and its singleton justification.
- Upgrade source supervision, generator and receipt contracts to Form/Coverage ABI 7.
- Keep open-class semantic identity in designation/frame authority rather than language-pack features.

## Workstream 5 — Semantic description and proof

- Extend the real Stage-10 owner with typed description requests/results and proof bundles.
- Traverse only bounded indexed semantic neighbourhoods.
- Return exact fact, claim, source, occurrence, inference, commit and runtime-snapshot refs.
- Mark proof focus stale when authority generation or world revision changes.
- Keep description/proof operations read-only and operationally declared.

## Workstream 6 — Dialogue focus and realization

- Record bounded verified semantic focus only after Response CSIR realization equivalence succeeds.
- Resolve provenance follow-ups from focus/proof identities, never prior wording.
- Add typed response actions and exact grammar rules for descriptions, proof explanations and structural gaps.
- Make semantic-slot requirements conditional on the response's typed completeness state.

## Workstream 7 — Activation, migration and release gates

- Attest ABIs 1/1/2/1/7/7/1/1 and module digests.
- Validate reviewed frames, app-valued roles, standalone licenses and learning contracts.
- Run source rewrite, data migration and all generators twice.
- Reject second-run changes, active legacy fields, sentence-shaped families and unexpected paths.
- Run focused and complete repository suites in detached staging and again after exact-byte target copy.
- Package a clean manifest-verified ZIP with no caches, zero-byte files or stale artifacts.

## Acceptance contract

The release is accepted only when:

- unknown material does not default to `concept`;
- learned synonyms inherit semantic affordances without pack regeneration;
- embedded propositions use app-valued links and no sixth operator;
- ambiguity remains N-best until exact settling;
- critical residuals and graph gaps block execution;
- semantic descriptions and proofs are bounded and source-grounded;
- response semantics precede surface text;
- activation fails closed on any ABI, authority, generator or source drift;
- no retired test is made green by restoring an invalid compatibility path.
