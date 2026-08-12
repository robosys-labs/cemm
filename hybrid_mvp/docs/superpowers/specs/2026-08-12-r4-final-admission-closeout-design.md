# Hybrid MVP R4 Final Admission and Integration Design

**Status:** approved closeout design; implementation remains red until admitted
**Date:** 2026-08-12
**Scope:** `hybrid_mvp/` plus repository integration only
**Starting commit:** `0a52bd6b53244cddd2545b70835b7ab6f2bfed31`
**Integration target:** repository `main`
**Root adoption:** excluded; requires a separate reviewed migration decision

## 1. Goal

Close R4 through the existing corrective-replay governance machinery, prove the
effective ledger is green from G0 through R4, and merge the complete admitted
Hybrid MVP ancestry into `main` without squashing, cherry-picking, or bypassing
external review.

Completion means all of the following are true together:

1. the checked-in authentic R4 corpus exists and reconstructs from reviewed
   inputs;
2. every R4 owner tier, the R4 phase tier, and the R4 admission tier pass from a
   clean committed checkout;
3. the external review manifest authenticates the exact committed artifact set;
4. the append-only replay ledger verifies as `G0=green R1=green R2=green
   R3=green R4=green`;
5. the full G0-to-R4 commit ancestry is merged into `main` with its identities
   intact; and
6. the merged result passes the same governed verification from a clean checkout.

## 2. Starting evidence and known gaps

The admitted lineage at the starting commit verifies as:

```text
G0=green
R1=green
R2=green
R3=green
R4=red
```

The R3 phase tier passes. All four R4 owner tiers pass:

- `expected-contract`;
- `mutation-partition`;
- `structural-sufficiency`; and
- `surface-review`.

The R4 phase tier fails for two independently observable reasons:

1. `artifacts/r4/episodes.jsonl` is absent, so authentic episode integrity tests
   cannot execute against a committed corpus; and
2. an inherited diagnostic Episode ABI test still requires an empty
   `legal_proposals` collection even though the active diagnostic contract
   retains bounded Program ABI 2 derivation lineage.

The latest reviewed public-runtime probe matches 22 of 400 cases. The remaining
cases are not to be hidden through expectation broadening. They must be grouped
by the earliest divergent owner and repaired at form evidence, designation,
contribution, composition, verification, situation, decision, effect, response,
or expected-contract authority as appropriate.

## 3. Approaches considered

### Approach A — close R4 on the current linear lineage, then merge once

Continue from `0a52bd6`, repair the corpus and runtime gaps under TDD, obtain
external review, append the R4 admission, and merge the complete ancestry to
`main` only after all gates pass.

This is the selected approach. It preserves receipt ancestry, keeps `main`
release-grade, and gives R4 one exact source identity.

### Approach B — merge G0 through R3 now and land R4 later

This shortens the immediate branch distance from `main`, but creates two
integration events and exposes an intermediate Hybrid MVP state whose own
governing closeout is known red. It also increases the chance that R4 artifacts
are generated against a different tree from the eventual merge target.

This approach is rejected.

### Approach C — cherry-pick useful commits from diagnostic and recovery branches

Several remote branches contain probes, source snapshots, and workflow recovery
steps. Cherry-picking them would obscure which exact lineage owns an admission
receipt and could reintroduce superseded bytes.

This approach is rejected. Divergent branches may be read as evidence, but a
change is reimplemented or merged only when its semantic owner and ancestry are
proved compatible with the selected linear tip.

## 4. Architecture and ownership

The closeout does not add a new runtime path. It completes the existing R4 data
and admission pipeline:

```text
reviewed scenario authority
→ ExpectedCycleContract compiler
→ bounded reviewed surface/context expansion
→ authentic public HybridRuntime R3 cycle
→ expected/observed comparison receipt
→ semantic and environmental mutations
→ seven independent partition axes
→ deterministic R4 build receipt
→ external review manifest verification
→ governed R4 admission
→ append-only R4 green ledger record
```

Owner boundaries remain exact:

- `r4_contracts.py` owns independently compiled expected semantic contracts;
- the R2/R3 form, grounding, contribution, composer, verifier, and cognition
  modules own authentic observed behavior;
- `r4_episodes.py` owns expected/observed separation and episode identity;
- `r4_mutations.py` owns one-declared-dimension mutations;
- `r4_partitions.py` owns independent-axis sealing and the intersection-only
  training allowlist;
- `r4_pipeline.py` owns deterministic artifact assembly and build receipts;
- `r4_review.py` owns external authorization verification; and
- `validation_gate.py` plus `update_replay_status.py` own admission and ledger
  transitions.

No expected-contract compiler may call PROPOSE or the runtime. No observed
runtime artifact may author semantic gold. No lexical surface or internal ref
spelling may select semantic meaning after the form boundary.

## 5. Repair strategy

### 5.1 Diagnostic Episode ABI alignment

The stale diagnostic assertion is repaired at its contract owner. The retained
`legal_proposals` payload remains derivation lineage only and must not be
interpreted as settled meaning or R4 gold. Tests must reconstruct the active ABI
and assert the exact separation between diagnostic proposal lineage and the
canonical `VerifiedMeaning`/R3 artifacts.

### 5.2 Authentic runtime coverage

The 400 reviewed cases are executed through the sole public runtime path. Each
mismatch is assigned one earliest-owner classification. Fixes are accepted only
when they generalize across the relevant semantic family and preserve:

- bounded candidates and search states;
- exact one-source/one-role coverage;
- critical residual blocking;
- designation/affordance separation;
- five-operator semantic expressions;
- expected/observed independence; and
- multilingual and unseen-synonym anti-bloat constraints.

The first repair tranche targets multi-unit state and relation composition and
the residual designation cases already identified by the public probe. Later
tranches follow measured owner counts, not phrase-by-phrase convenience.

### 5.3 Artifact generation and external review

The complete R4 artifact graph is generated from a clean committed source twice.
Both runs must be byte-identical. Checked-in artifacts include the authentic
episode corpus and every admission-required receipt, mutation, partition,
allowlist, sufficiency, and build identity defined by the active schemas and
gate configuration.

The repository produces an unsigned review request. An external reviewer signs
the exact source and artifact hashes through the existing trust-root mechanism.
The runtime, generator, and admission process cannot self-sign or substitute a
template manifest.

## 6. Failure handling

Every failure remains typed and fail-closed:

- a semantic mismatch records the earliest owner and exact expected/observed
  identities;
- a structural or critical residual prevents episode acceptance;
- generator nondeterminism blocks review;
- missing or invalid review evidence blocks R4 admission;
- a dirty governed checkout blocks admission;
- a ledger/source/predecessor mismatch blocks the green transition; and
- any post-merge gate failure aborts integration and leaves the closeout branch
  intact for repair.

No UI fallback, expectation relaxation, synthetic episode, skipped test, xfail,
or manual ledger edit may convert a failure to green.

## 7. Verification contract

Development proceeds test-first for each earliest-owner repair:

1. add or select the smallest governed test that reproduces the divergence;
2. verify it fails for the expected semantic reason;
3. implement the minimal owner-level correction;
4. verify the focused test and its owner tier;
5. run the R3 phase tier to prevent predecessor regression; and
6. rerun the authentic 400-case comparison to measure the exact delta.

Before admission, verification must include:

- source compilation;
- governance chain reconstruction;
- metadata and structural hard-cut checks;
- strict legacy audit with zero findings;
- every R4 owner tier;
- complete R3 and R4 phase tiers;
- deterministic double artifact generation;
- external review verification;
- R4 admission from the exact clean commit; and
- reconstruction of the appended G0-through-R4 green ledger.

The repository-wide suite must not shrink and may introduce no new failure or
error identity relative to the admitted predecessor policy.

## 8. Git and integration contract

The closeout branch begins at:

```text
main 79040b6
→ R2 49c6903
→ R3 4eb6c27
→ R4 contracts 6d89178
→ R4 phase 15e996f
→ R4 authentic surfaces 0a52bd6
→ R4 final admission commits
```

Commits remain reviewable and owner-scoped. The final integration uses a normal
non-squash merge into an up-to-date `main`. Before merging, the closeout branch
must be pushed and its exact remote tip verified. After merging, the complete
governed verification is rerun on the merge commit before `main` is pushed.

Existing unrelated worktrees, untracked files, locally ahead branches, and
diagnostic branches are not modified. Root-runtime adoption is explicitly out of
scope even after the `hybrid_mvp/` subtree lands on `main`.

## 9. Definition of done

This closeout is complete only when:

- the authentic R4 artifact graph is present, deterministic, externally
  reviewed, and reconstructable;
- all reviewed cases have a truthful accepted result or an explicitly governed
  typed exclusion permitted by the approved R4 contract;
- all R4 owner, phase, and admission tiers pass without skips or xfails;
- `update_replay_status.py --verify-chain` reports G0 through R4 green;
- the full lineage is merged into `main` without history rewriting;
- post-merge governed and repository tests pass; and
- the pushed `main` commit is the exact verified merge commit.
# Superseded

Superseded by [R4 Repository-Owned Admission Design](2026-08-12-r4-repository-owned-admission-design.md). Retained as historical evidence only.
