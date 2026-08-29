# Hybrid MVP Authority and Regression-Surface Cleanup Design

> **Completed historical evidence:** This document records an earlier tranche;
> it is not an executable current plan and owns no phase status. Current status
> is derived from
> [`governance/replay_status.jsonl`](../../../governance/replay_status.jsonl).

**Status at publication:** approved design; implementation was later completed

**Scope:** `hybrid_mvp/` plus active GitHub workflows capable of mutating it

**Base:** source-only corrective snapshot `0e5cc80195047ae6401070e21c05954e26c3e299`

**Root adoption:** explicitly out of scope

## 1. Purpose

Before further R4 repair or R5 implementation, make the repository tell one
truth about the Hybrid MVP. Active authority must not route an implementer back
to either rejected R4 partition model, bootstrap-authored supervision, input-
surface realization targets, or self-modifying CI publication.

This tranche changes governance, documentation, comments, and regression
checks. It does not change semantic runtime behavior, generate corpus
artifacts, train models, activate an ABI, or append a replay-status record.

## 2. Evidence requiring the cleanup

Two R4 artifact generations produced integrity evidence without producing a
training and evaluation boundary suitable for R5:

1. the ABI-3 independent-axis design produced an empty training intersection;
2. the ABI-4 global connected-component design placed all 248 semantic
   episodes in `train`, leaving `selection`, `calibration`, and `frozen_test`
   with no semantic expressions, operators, derivations, or realizations.

The second result follows from treating common semantic targets, response
families, participant identities, and realization identities as transitive
leakage-union edges. The feasibility gate then selected only dimensions already
spanning four components and trimmed infeasible requirements. That made the
gate self-satisfying rather than proving R5 usability.

Additional active surfaces still permit or describe:

- an empty `ExpectedDerivationContract` set;
- bootstrap-selected programs as proposal targets;
- user input surfaces hashed into realizer classes;
- fixed label-derived confidence values presented as calibration;
- marker-based surface checks presented as semantic equivalence;
- legacy episode/schema/test paths that preserve program-as-meaning behavior;
- branch-triggered workflows that patch and push governed source.

These are repair inputs, not completion evidence.

## 3. Authority model

### 3.1 Repository boundary

The repository-root Stage 0–22 contracts remain unchanged. The Hybrid MVP is a
separately governed six-phase proof, and root adoption still requires a
separate reviewed decision. This cleanup must not reconcile the two runtimes by
rewriting root authority.

### 3.2 One new corrective amendment

Implementation will add one highest-precedence Hybrid amendment covering the
R4.1 data boundary and the prerequisites for R5. It will state these laws:

- a `SemanticSwitchProgram` is a construction derivation, never canonical
  meaning;
- semantic-expression gold and derivation supervision are independent;
- bootstrap output cannot author either reviewed semantic gold or reviewed
  derivation gold;
- every R5-purpose class has a nonzero, explicitly declared semantic
  denominator appropriate to its purpose;
- common semantic labels are stratification dimensions, not automatically
  transitive leakage edges;
- unsupported reviewed minima fail; a gate cannot silently remove or weaken
  them;
- response realization supervision originates from reviewed
  `ResponseMeaning`-to-surface plans with literal-copy alignment, never from the
  user input surface;
- model selection, calibration, and frozen evaluation remain unavailable until
  their independently authenticated semantic payloads satisfy these laws.

### 3.3 Status ownership

`governance/replay_status.jsonl` remains the sole owner of phase status and
admission-run identity. Current-state prose links to the ledger and contains no
copied status table, run ref, or claim that a target ABI is admitted.

The cleanup itself appends no ledger record. Documentation correction is not
phase admission.

## 4. Document routing

### 4.1 Governing documents

`docs/DOCUMENT_AUTHORITY.json` will classify the new amendment before any
subordinate design or plan. The active set will contain only documents that are
needed to understand the architecture, ABI ownership, replay governance, and
the next executable repair.

The August 22 R5/R6 design may remain subordinate governing guidance only after
it receives an explicit prerequisite notice preserving its useful constraints:

- at most five active R5 owner modules;
- one HTTP stack and no streaming expansion;
- CPU reference implementation;
- no new dependency without measured need;
- purpose-scoped partition capabilities;
- budgets before architecture expansion.

Its training, selection, calibration, realization, and activation tasks are not
executable until the new amendment's supervision and semantic-partition
prerequisites are satisfied.

### 4.2 Superseded execution claims

The August 14 global-union R4 partition design and implementation plan will be
removed from executable authority and given a prominent first-page banner. The
banner will identify the successor amendment and explain that the connected-
component mechanism is rejected because it admits semantically empty held-out
classes.

Older independent-axis/intersection plans, obsolete closeout plans, and the
generic completion critical path remain or become superseded execution claims.
Their task history is retained, but their commands and completion language
cannot authorize work.

### 4.3 Historical evidence

Completed implementation plans, progress trackers, readiness reviews,
evaluation reports, old protocols, old limitations, runtime traces, and
generated artifacts are historical evidence. They remain inspectable but do
not define current status, ABI activation, or the next executable task.

Every Hybrid documentation file with an authority-like or status-like title
must be classified exactly once as governing, superseded, or historical.

## 5. Living-document corrections

The cleanup will update these routing surfaces together:

- `README.md` — purpose, six-phase boundary, ledger pointer, and current plan
  routing without copied status;
- `INTEGRATION.md` — preserve the diagnostic history while pointing to the new
  repair owner;
- `docs/ARCHITECTURE.md` — replace the global-union partition prescription with
  the reviewed separation between hard lineage grouping, stratification, and
  explicit challenge holdouts;
- `docs/ABI_REGISTRY.md` — distinguish target, implemented, and admitted ABIs;
  record R4.1 supervision and partition contracts without claiming activation;
- `docs/REPLAY_GOVERNANCE.md` — define document classification and ledger-only
  status ownership;
- `docs/IMPLEMENTATION_PLAN.md` — remain a routing page rather than a parallel
  implementation plan;
- relevant R4/R5 specs, plans, and progress files — receive exact active,
  conditional, completed, or superseded banners.

No living document may prescribe either rejected R4 split, automatic minimum
trimming, bootstrap-authored gold, or input-surface realization supervision.

## 6. Comment and docstring policy

Comments and docstrings must describe what the current implementation actually
does. The cleanup will correct claims that marker matching is exact semantic
equivalence, surface hashing is a dynamic-pointer target, or label constants
are calibrated model confidence.

The cleanup will not disguise incomplete code. Honest annotations identifying
an inactive placeholder, legacy owner, or later-owner gap remain until the
owning TDD tranche replaces that implementation. In particular, the typed R5
realization gap remains visible and active.

Functional source changes are excluded from this tranche. If correcting a
comment exposes a behavior that needs replacement, the comment points to the
governing prerequisite and the defect is covered by a failing future-owner
acceptance test or repair-plan task; it is not patched opportunistically.

## 7. Workflow quarantine

An active workflow may validate governed source, but it may not rewrite and
push it. Obsolete branch-specific workflows that apply embedded patches,
base64 payloads, or automatic commits will be removed from the active workflow
directory. Git history and the forensic ref manifest preserve their evidence;
duplicating disabled workflow files in the checkout is unnecessary bloat.

The retained workflows must be read-only with respect to governed source. A
release publication workflow may publish an already reviewed artifact only
through a separately approved contract; none is introduced here.

## 8. Regression checks

The cleanup adds fast, deterministic checks before expensive admission work.

### 8.1 Document authority checks

Fail when:

- a classified path is missing or appears in multiple authority classes;
- an authority-like/status-like Hybrid document is unclassified;
- a superseded document lacks a prominent successor banner;
- a current-status document does not point to the replay ledger;
- a current-status document embeds a phase-status range, admission run, local
  worktree path, or generated-artifact completion claim;
- a target ABI is described as admitted without authenticated ledger evidence.

### 8.2 Forbidden active-instruction checks

Fail when a governing document prescribes:

- intersection of independently assigned axis partitions;
- one global union over common semantic-target or realization identities;
- data-derived selection or silent trimming of required minima;
- bootstrap proposal output as reviewed gold;
- input utterances as response-realization targets;
- fixed epistemic labels as calibrated probabilities.

The check is intentionally narrow and operates on governed routing surfaces,
not every historical file.

### 8.3 Workflow checks

Fail when an active Hybrid-related workflow:

- grants write permission and invokes `git push`;
- edits governed source before validation;
- applies embedded source payloads;
- selects only a retired branch as its execution authority.

### 8.4 Performance budget

The new preflight checks must parse bounded JSON, Markdown headers, and workflow
YAML/text only. They must not build the corpus, open model weights, recreate a
database, or invoke the complete pytest inventory. The focused cleanup suite is
expected to complete in seconds, not minutes.

## 9. Error handling and preservation

- Ambiguous classification fails closed; the implementation does not guess.
- Historical documents are bannered and classified rather than rewritten to
  look as though their old tasks were executed differently.
- Generated artifacts and ledger rows are not hand-edited.
- A stale claim that cannot be resolved from repository evidence is removed
  from current routing prose and replaced with a pointer to its authority
  source.
- Workflow removal is recorded in the commit and remains recoverable from Git.
- Documentation changes that affect pinned governance inventories regenerate
  those deterministic inventories through their existing owner scripts.

## 10. Non-goals

This cleanup does not:

- repair the R4 partitioner, feasibility solver, schemas, corpus, or artifacts;
- create derivation or realization gold;
- migrate legacy episode consumers;
- replace the neural proposer or realizer;
- change confidence calculation;
- train, select, calibrate, or evaluate a model;
- activate R5 or adopt the Hybrid runtime at repository root;
- delete remote branches or tags.

Those changes follow in separately test-driven tranches under the corrected
authority.

## 11. Acceptance

The cleanup is accepted only when:

1. the worktree diff is limited to approved Hybrid documentation, comments,
   governance tests/inventories, and workflow quarantine;
2. every authority-like Hybrid document is classified exactly once;
3. the two rejected R4 partition strategies cannot be reached through active
   document routing;
4. R5 planning explicitly requires independent derivation gold, reviewed
   realization supervision, and semantically useful purpose classes;
5. no active workflow can patch and push governed Hybrid source;
6. focused governance and documentation regression tests pass;
7. deterministic inventory regeneration is stable on a second run;
8. the replay ledger and generated R4 artifacts are byte-unchanged;
9. root runtime documents and source are byte-unchanged.
