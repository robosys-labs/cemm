# CEMM foundation acceptance — explicit admitted scope

This status is attached to the **draft** foundation PR. It separates passing
code-level gates from not-yet-proven cognitive behavior. A green workflow
does not make a red capability green.

## Source baseline

- Start: root `main` commit `24d8b68a4c9b0c992362a1c2e542579b5f0c4280`.
- Recovery branch: `codex/cemm-foundation-end-to-end-20261008`.
- Historical archive branch: `archive/cemm-pre-foundation-20261008`.
- Proposal: https://github.com/robosys-labs/cemm/pull/21

## Validated in the current branch

| Invariant | Status | Executable evidence |
| --- | --- | --- |
| One installed six-phase runtime and public ABI | green | wheel/import gate; `test_foundation_public_api.py` |
| No root Stage 0-22, recovery snapshots, or reachable historical realizer | green | `test_foundation_source_boundaries.py` |
| Authentic text -> proposed/verified semantic meaning -> R3 decision/effect | green for supported cases | `test_foundation_semantic_surface.py` |
| Lossless structured response encoding, exact roundtrip and tamper rejection | green | `test_foundation_semantic_surface.py` |
| Identity distinguishes role direction, negation, attribution, condition ordering | green | `test_foundation_algebra.py` |
| Recursive reviewed-rule proof with no false subject unification | green | `test_foundation_inference.py` |
| Four typed R3 decision modes and no world mutation on query/simulation | green | `test_foundation_modes.py` |
| Persistent store reopen and resumed semantic execution | green | `test_foundation_restart.py` |
| Unreviewed lexical claims and unverified reported events cannot silently become world truth | green | `test_foundation_epistemic_safety.py` |

The public-path probe is an **observational diagnostic**, not an oracle.
Examples on the current authority/data baseline:

- `hello`: verified semantic acknowledgment.
- `What is your name?`: unknown (no reviewed self-name binding admitted).
- `Alice owns a book.`: attributed/acknowledged, not asserted into world truth.
- `Who owns a book?`: unknown in the absence of admissible matching world evidence.
- `Mary said Bob left.`: ambiguous; nested attribution not fully resolved.
- `yoz means hello`: no automatic authority publication (correct).
- `What does yoz mean?`: unresolved without a reviewed acquisition.
- `please turn on the lamp`: unsupported; no external adapter assumed.

## Release-blocking cognitive gaps

1. **Reviewed novel-designation acquisition and continuation:** issue a
   trustworthy authorized learning operation, commit one designation through
   the effect owner, refresh generation/revision-pinned grounding, demonstrate
   a new composition and query, reopen the store, and prove that the alias
   still resolves. An unreviewed user statement must never be enough.
2. **Independent compositional language semantics:** prove multiple previously
   unseen participant/relation/value combinations, temporal state, and nested
   reported propositions. The R4 corpus still shows broad structural gaps.
3. **Real linguistic realization:** generate proposition-bearing answers with
   exact dynamic slot alignment, then independently re-interpret and verify
   graph equivalence. Marker/template checks are not admissible.
4. **Neural ABI recovery:** `NeuralSwitchProposer.propose(orientation)` and
   direct `ProposalResult(...)` are incompatible with the current
   `ProposalOwner.propose(context)` / `ProposalResult.create` contract.
   Those legacy sources remain ineligible for the active foundation.
5. **Distribution and scale:** package the reviewed authority in a
   self-contained, reproducible release; verify concurrency, index behavior,
   crash recovery and benchmark policy before production exposure.

## Completion law

An architecture version may be called **general cognitive foundation
validated** only when the green structured-semantic gates AND every cognitive
release blocker above have executable independent acceptance proofs. No
phrase-specific patch, direct world write from natural-language input,
test-generated gold, or weaker response verifier may satisfy the contract.
