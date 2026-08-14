# R4 Partition Corrective Replay Design

**Date:** 2026-08-14
**Status:** approved and independently reviewed specification
**Scope:** `hybrid_mvp/` R4 data partition evidence, artifacts, admission, and descendant reset only

## 1. Decision

R4 must be corrected before R5 neural activation. The admitted R4 artifact graph
contains an empty training allowlist, so it cannot truthfully own the training
boundary required by R5. The defect is not a lack of epochs or model capacity.
It is a partition-architecture error in the admitted data owner.

The repair replaces independently hashed per-axis split assignments followed by
set intersection with one globally coherent, leakage-safe four-class assignment.
Per-axis evidence remains independently reconstructable. Every exact protected
identity required by the seven admitted axes remains a namespaced leakage key
and therefore participates in the one global component graph. Only coarse
categories, missing-value sentinels, and aggregate coverage dimensions are
stratification labels; they do not union unrelated episodes.

The four physical classes are:

```text
train
selection
calibration
frozen_test
```

R4 is invalidated before replacement artifacts are admitted. G0-R3 remain
green. R5 remains red throughout this corrective replay. R5 training and neural
activation may begin only after the repaired R4 artifact graph is admitted.

## 2. Evidence and earliest divergence

The current admitted source universe contains 400 authentic R4 episodes.
`artifacts/r4/training_allowlist.json` contains zero `train_refs`.

The first visible defect is the lexical axis. It emits a standalone
`language_family` value for every episode. Because every current case is
English, all 400 episodes become one connected component and that component is
assigned wholly to test.

Removing the lexical axis does not repair the result. The current independent
axis assignments intersect as follows:

| Intersection applied | Remaining common train episodes |
|---|---:|
| mutation | 400 |
| + dialogue | 5 |
| + general | 2 |
| + realization | 2 |
| + topology | 2 |
| + semantic target | 0 |

Therefore the root cause is broader than one lexical key. Independently hashing
each axis and intersecting the independently selected train sets has no global
feasibility objective and can yield the empty set even when every individual
axis appears valid.

The old `data/partitions/train.jsonl`, `validation.jsonl`, and `test.jsonl`
files are not a repair. They are legacy 234/78/78 descendants and are not bound
to the admitted R4 artifact graph.

The defective artifact is bound exactly by:

- allowlist ref `training_allowlist_v2:51c0cc234805cdda54f8e2c7`;
- checked-in allowlist file SHA-256
  `3c47c3e66771add72a541342a5669ef5c93286356eb1ae0c0de9eb86d9b3d2db`;
- Build Receipt ref `r4_build_v3:5d5eee0ee8c0e7bb1bcba522`; and
- checked-in Build Receipt file SHA-256
  `0069ae2c8a301700498aba4801df96205f9166938e1b21d3336aa1768d75dec6`.

The governing spec committed at the invalidation `source_base` owns this defect
evidence. The existing replay-ledger schema retains its generic invalidation
rationale; this corrective replay does not claim that the ledger row itself has
new artifact-evidence fields.

## 3. Goals

1. Make the R4 training boundary non-vacuous, deterministic, leakage-safe, and
   independently reconstructable.
2. Materialize exact, mutually disjoint `train`, `selection`, `calibration`,
   and `frozen_test` payloads from the admitted R4 source universe.
3. Preserve per-axis evidence explaining every leakage edge and every
   stratification label without letting coarse labels collapse the corpus.
4. Require non-vacuous class and coverage sufficiency before R4 admission.
5. Invalidate and re-admit R4 through the append-only replay ledger with exact
   regenerated artifacts and repository-owned integrity evidence.
6. Keep R5 red and keep all model training, selection, calibration, weight-use,
   reproduction, and public cutover outside this corrective increment.
7. Preserve the root/Hybrid boundary. Root adoption remains a separate review.
8. Migrate the already-active R5 train-only foundation interface from legacy
   `data/partitions` authority to an authenticated, class-scoped R4 train
   capability; selection, calibration, and frozen-test consumers remain
   deferred to R5 Neural Activation.

## 4. Non-goals

- Do not train, tune, select, calibrate, reproduce, or activate a neural model.
- Do not treat 100 epochs, a lower loss, or an inherited checkpoint as repair
  evidence.
- Do not reuse the legacy three-way `data/partitions` artifacts.
- Do not open or evaluate the frozen-test payload during R4 repair.
- Do not implement R5 proposal, realization, or runtime cutover.
- Do not modify the five semantic operators or any G0-R3 semantic ABI.
- Do not weaken leakage protection merely to make every class nonempty.
- Do not preserve Partition Axis Manifest ABI 2 or Training Allowlist ABI 2
  through a compatibility decoder.
- Do not update root runtime acceptance or claim Hybrid adoption.

## 5. Partition model

### 5.1 Source universe

The partition owner accepts only the exact authenticated R4 episode universe.
Every input episode must have a unique `episode_ref` and exact references to its
expanded case, expected contract, generator lineage, and review provenance.
The source-set reference is content-addressed over the sorted complete episode
reference set.

No partition stage may silently omit an episode, introduce a non-source
episode, or read legacy partition membership.

### 5.2 Leakage-equivalence keys

Leakage keys answer one question: which episodes must never be placed in
different data classes because one may reveal the other?

The reviewed leakage graph preserves exact protected identities from all seven
current axes. It uses concrete, namespaced identities only:

- **general:** reviewed scenario, case, trajectory, and generator lineage that
  identifies a shared reviewed source;
- **lexical:** reviewed surface family, exact normalized surface qualified by
  language, and exact normalized construction/template identities where
  present;
- **semantic target:** exact semantic-expression, predicate, grounded-target,
  and reviewed dynamic-slot family identities;
- **topology:** exact canonical expression-topology identity;
- **dialogue:** non-null trajectory and exact obligation/descendant lineage;
- **mutation:** exact mutation parent/child lineage and exact reviewed mutation
  family identity when it denotes derived variants of one source; and
- **realization:** exact response-expression and response-semantic family
  identity.

Missing, default, or broad categorical values never become shared leakage keys.
For example, standalone `language=en`, `obligation=none`, `mutation=none`,
operator counts, and `outcome=supported` cannot union unrelated episodes.
Language still participates in the qualified normalized-surface identity; an
exact obligation, mutation, target, topology, or response identity still joins
its true descendants. If preserving those exact keys makes four-way assignment
infeasible, generation fails and the reviewed corpus must expand. The repair
never reclassifies an exact leakage identity as a label merely to obtain rows.

Every leakage edge is emitted as exact evidence containing the key namespace,
key content reference, and sorted member episode references.

The serialized representation is a bounded hyperedge-membership record per
protected key, not an expanded pairwise edge list. Union/find consumes each
member list once, preserving near-linear construction and exact independent
reconstruction.

### 5.3 Stratification labels

Stratification labels guide balanced assignment but do not create graph edges:

- language as a coarse coverage category;
- operator/kind and target-category coverage, distinct from exact protected
  target identities;
- topology shape/category coverage, distinct from exact topology identity;
- presence/type of dialogue obligation, distinct from exact obligation lineage;
- mutation dimension/category, distinct from exact parent/family lineage;
- response discourse-action/category coverage, distinct from exact
  response-expression and response-semantic identities;
- expected outcome/gap family;
- reviewed surface and environment coverage dimensions.

Each label is namespaced and content-addressed. Assignment uses label counts,
never internal ref spelling or raw surface dispatch.

### 5.4 Connected components

A deterministic union/find builds connected components from leakage edges.
Every episode belongs to exactly one component. Components are indivisible:
all members receive one data class.

Component identity binds:

- sorted member episode refs;
- sorted leakage-key refs;
- source-set ref; and
- the active partition ABI.

The verifier independently reconstructs all edges, components, identities, and
source-universe coverage.

### 5.5 Four-class assignment

The reviewed target ratios are:

```text
train        60%
selection    15%
calibration  15%
frozen_test  10%
```

Whole components are assigned by deterministic seeded stratified bin packing.
Components are processed in canonical difficulty order: larger components,
rarer-label components, then stable component ref. For every allowed class, a
fixed integer objective scores:

1. class-size deviation from the reviewed target;
2. per-label deviation from the target distribution;
3. class minimum and maximum violations; and
4. deterministic stable-ref tie breaking.

Floating-point comparison is forbidden. The objective definition, weights,
seed, ratios, limits, and tie-break material are serialized in reviewed config
and content-addressed into the split manifest.

The identity graph is acyclic: source/component/solver material produces a
feasibility-basis ref and minima-witness ref; Partition Config ABI 1 binds those
two inputs; the final feasibility receipt binds the completed config ref; and
the split manifest/Build Receipt bind that final receipt. Config never points
to a receipt that points back to config.

The partitioner fails closed when the connected-component topology makes the
reviewed requirements infeasible. It never splits a leakage component or
silently relaxes a minimum.

## 6. Sufficiency contract

Admission requires all of the following:

1. the four class sets are nonempty, disjoint, and exactly exhaustive;
2. every leakage component is wholly contained in one class;
3. no leakage-key ref appears in more than one class;
4. `train` contains enough source diversity for the later bounded models;
5. `selection`, `calibration`, and `frozen_test` each contain independently
   useful held-out coverage;
6. every configured minimum is an exact positive integer, not a percentage
   denominator that can become vacuous;
7. each reviewed dimension reports source support, feasible component support,
   observed per-class support, and any infeasibility reason;
8. zero-source or zero-feasible denominators fail rather than pass; and
9. the complete sufficiency receipt is independently reconstructed from the
   source episodes, leakage graph, labels, and split manifest.

The implementation plan must choose exact minimum counts only after a
source-derived feasibility report is checked in for review. Thresholds may not
be selected from model performance or frozen-test results.

## 7. Access and payload architecture

R4 materializes canonical payloads under a new artifact namespace:

```text
artifacts/r4/splits/train.jsonl
artifacts/r4/splits/selection.jsonl
artifacts/r4/splits/calibration.jsonl
artifacts/r4/splits/frozen_test.jsonl
artifacts/r4/split_manifest.json
artifacts/r4/partition_sufficiency.json
```

Each JSONL file is ordered by `episode_ref`, newline-normalized, strictly
decoded, and hashed in the manifest. The manifest binds exact counts, hashes,
episode refs, component refs, label coverage, source-set ref, generator source
revision, authority generation, and partition config ref.

The complete split manifest is restricted to the R4 generator and repository-
owned integrity verifier. Those owners may generate and strictly decode every
payload solely to prove source membership, canonical bytes, hashes, leakage
isolation, and sufficiency. They never train, select, calibrate, or compute
frozen-test model metrics.

Consumers receive an authenticated class-scoped capability/snapshot containing
only the authorized class payload, its payload ref/hash/count, the source-set
ref, and the exact ancestor artifact refs required to authenticate it. It does
not reveal other class paths, hashes, counts, or bytes:

```text
training owner    -> train only
selection owner   -> selection only
calibration owner -> calibration only, after selection receipt
evaluation owner  -> frozen_test only, after selection and calibration freeze
```

No owner receives paths or hashes for an unauthorized class. R4 tests may
verify bytes and identities as integrity owners, but they must not compute model
metrics from the frozen-test payload. The frozen-test evaluation capability is
minted only after exact selected-model and calibration receipts exist.

A capability is not its own trust root. R4 also emits a class-scoped
authorization projection containing the expected capability ref/SHA, exact
artifact-graph ref, generator source revision, and authority generation, with
no sibling identities. Build Receipt ABI 4 binds this authorization SHA, and
the repository admission receipt binds its exact ref/SHA. A consumer resolves
those expected values from the admitted R4 run and passes them separately into
its isolated process. Replacing authorization, capability, and payload together
therefore fails the external admission identity check.

The repository-owned parent controller performs ledger/run verification, then
starts an isolated training child with only the expected authorization ref/SHA
and a private snapshot containing authorization, train capability, and train
payload. The child cannot open the ledger, admission receipt, global manifest,
Build Receipt, or sibling artifacts. The parent does not import trainer/model
code.

This corrective increment implements only the active train capability. It
migrates the existing R5 foundation training loader, trainer entry points,
metadata provenance, governed data-isolation tests, and validation inputs from
`data/partitions` to the authenticated R4 train payload. The legacy
`PartitionManifest`, `Partitioner`, three-way manifest, and legacy loader
authority are retired without a compatibility decoder. Structural tests reject
their return. Selection, calibration, and frozen-test capability consumers are
defined by the ABI but remain unavailable until R5 Neural Activation.

## 8. ABI hard cut

This corrective replay makes a hard data-ABI cut:

- retire Partition Axis Manifest ABI 2;
- retire Training Allowlist ABI 2;
- introduce Partition Evidence ABI 3 for leakage edges, stratification labels,
  globally assigned components, and per-dimension evidence;
- introduce R4 Split Manifest ABI 1 for four physical classes and payload
  identities;
- introduce R4 Partition Sufficiency ABI 1 for non-vacuous feasibility and
  coverage evidence;
- introduce R4 Class Capability ABI 1 for a single authorized payload with no
  sibling-class disclosure;
- introduce R4 Class Authorization ABI 1 for the admission-authenticated,
  class-scoped expected capability identity;
- introduce Partition Config ABI 1 for ratios, integer formulas, bounds,
  minima/maxima, and feasibility identity; and
- bump R4 Build Receipt ABI 3 to ABI 4 because its owned artifact set and exact
  fields change.

Build Receipt ABI 4 replaces `training_allowlist_sha256` with exact partition
evidence, split-manifest, split-payload, and partition-sufficiency identities.
Old artifacts fail decoding. There is no compatibility loader.

The unregistered legacy `PartitionManifest`/`Partitioner` and train-loader wire
contract in `partitions.py`/`training.py` are also retired. All governed tests,
configuration, metadata provenance, artifact/admission input paths and hashes
move to the new R4 class capability in the same corrective replay, so two
partition authorities cannot coexist.

The ABI registry, schemas, deterministic generator, admission reconstructor,
validation evidence policy, and active documentation change together.

## 9. Replay and admission sequence

The append-only governance sequence is:

```text
approved governing corrective spec and plan
-> reviewed R4 red invalidation bound to the admitted defective artifact
-> deterministic source implementation
-> two byte-identical candidate artifact builds
-> all final source/config/test/doc changes committed
-> final two byte-identical builds from that exact source commit
-> checked-in ABI 4 artifact-only commit whose single parent is that source
-> R4 owner and phase verification
-> repository-owned clean R4 admission run
-> append-only R4 green transition
-> replay-chain verification
```

The red transition's committed `source_base` contains this governing spec with
the exact defective allowlist and Build Receipt refs/hashes. The ledger record
uses the existing generic invalidation rationale and resets descendants
according to normal ledger semantics; R5 is already red and remains red.

No green transition is appended until committed inputs reconstruct exactly and
the admission run proves the complete new artifact graph.

Historical ABI 3 admission receipts continue to reconstruct their old evidence
path set from their stored source base. Current candidates require only the ABI
4 evidence path set. A bounded union may police dirty-path containment, but it
is never accepted as one ambiguous admission policy.

## 10. Validation ownership

Existing R4 owners remain bounded. The `mutation-partition` owner gains the new
partition contracts; `artifact-integrity` reconstructs their committed bytes.
No extra owner tier is required merely because there are four classes.

The validation graph must retain at most one pytest process per tier and the
existing step bound. Expensive corpus generation is not duplicated across each
owner gate. Deterministic generation runs at the artifact-generation checkpoint
and admission independently reconstructs identities without retraining or
rerunning R5.

Closeout runs one complete G0-R5 phase sweep before admission. The ordinary R4
admission owns the one full active-suite process. The ledger-only admission
commit is followed by governance/artifact checks, not another phase/full-suite
sweep. The aggregate broad-test budget is therefore at most seven pytest
processes and 1,800 seconds on the reviewed Windows host.

Required corruption tests include:

- coarse language or sentinel values creating a global component;
- one leakage key appearing across two classes;
- overlapping, missing, or extra episode refs;
- empty class or vacuous sufficiency denominator;
- split payload/hash/count mismatch;
- altered seed, ratio, objective weight, or tie break;
- label evidence not derivable from the authenticated episode;
- component or assignment nondeterminism;
- unauthorized class-path exposure; and
- stale ABI 2 allowlist/build receipt acceptance.
- any R5 foundation training path that still treats `data/partitions` as
  admitted R4 authority; and
- a class capability that reveals a sibling path, hash, ref, count, or payload.

## 11. Performance bounds

The current corpus has 400 episodes. Partition construction is offline and
bounded by reviewed constants:

- maximum source episodes;
- maximum leakage keys and stratification labels per episode;
- maximum total graph edges;
- maximum components;
- exactly four data classes;
- integer-only objective evaluation; and
- bounded canonical artifact sizes.

Expected complexity is near-linear union/find plus deterministic component
assignment over four choices. No partition code enters the normal semantic
runtime cycle, and no normal cycle scans the corpus.

## 12. Documentation and progress ownership

The written design and subsequent implementation plan become governing only
through `docs/DOCUMENT_AUTHORITY.json`. Historical R4 admission documents remain
evidence and receive narrow supersession notices where necessary; their
original execution history is not silently rewritten.

The companion progress tracker records tasks, evidence, decisions, risks, and
publication history. It is operational evidence only. Effective phase status
is always derived from `governance/replay_status.jsonl`; the tracker cannot make
R4 red or green.

## 13. Acceptance criteria

The corrective replay is complete only when:

- an append-only record truthfully invalidates the defective R4 admission;
- the old empty training allowlist and three-way legacy partitions are not
  accepted as R5 training authority;
- globally coherent leakage components and all labels reconstruct exactly;
- all four physical classes are nonempty, disjoint, exhaustive, and sufficient;
- no leakage key crosses a class boundary;
- generation is byte-identical in two independent clean output roots;
- Build Receipt ABI 4 binds every new artifact;
- R4 repository-owned admission passes from a clean committed snapshot;
- the ledger reconstructs G0-R4 green and R5-R8 red after re-admission;
- G0-R3 phase gates and the governed active suite remain green;
- no root runtime or adoption document is changed; and
- the branch is reviewed and published without merging or starting R5 neural
  training implicitly.

## 14. Next increment

After R4 is re-admitted, `R5-Neural-Activation` may consume the new purpose-bound
classes. It must still replace the stale Program ABI 1 neural stack, calibrate
from actual model predictions, prove selected weight use and ablation, reproduce
selected artifacts byte-for-byte, and convert the frozen R5 disposition from
17 successors / 25 deferrals / 1 retirement to 42 successors / 0 deferrals /
1 retirement before R5 admission.
