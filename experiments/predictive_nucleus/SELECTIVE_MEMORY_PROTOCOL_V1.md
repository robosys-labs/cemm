# G5 selective memory v1 — prospective bounded comparison

## Decision and sequence

Freeze and publish this contract before implementation, preparation or fitting.
Continue from `a32c0e81281b4d272a03781ae4415e9a77978c29`; the temporal v1,
TRAIN trace and prefix-protection studies are closed. Their artifacts are
dependencies and evidence, not experiments to rerun. This tests whether learned
soft memory addressing can improve correction without damaging other meanings.
It does not activate production, advance full G5 admission or authorize G6–G8.

Publish in order: contract, implementation, prepared observations, all fitted
checkpoints, raw challenge predictions, scored decision. Run one fit per arm and
seed and one complete challenge collection. Any failed gate yields
`REVISE_SELECTIVE_MEMORY_V1`; all gates yield `KEEP_SELECTIVE_MEMORY_V1` for
bounded development only. No budget extension, seed selection, loss schedule
retry or opened-challenge tuning belongs to this version. Defective execution is
reported separately and cannot be silently replaced by a successful run.

## New histories and split

Keep the frozen physical laws NAND/NOR, two modes, three participants and four
primitive operations from the temporal study. Preparation alone may import the
simulator and separate table oracle; every endpoint must agree. Learners see
observations and the existing frozen native forecast basis, never true operation,
cause, mode/law labels, semantic change masks or evaluation posteriors.

Each split contains 256 public contexts: law (2) × mode (2) × old operation for
word 0 (4) × independently chosen old operation for word 1 (4) × the two target
scopes (local/sibling independently, 4). For each context select a tuple of four
active inputs `(a0,a1,b0,b1)` using Python Random seed 20261110101, in canonical
split/law/mode/old0/old1/scope0/scope1 order. TRAIN permits
`(a0+a1+b0+b1) mod 4` in {0,1}; TEST permits {2,3}. Select uniformly from the
lexicographically enumerated permitted tuples. Claim state for word w is `2*aw`;
target state is `2*bw+1`. Within each split all old pairs, modes and target scope
pairs occur. Starting word is `(old0+old1+mode+2*scope0_index+scope1_index) mod 2`;
scope index 0 means local and 1 means sibling. It depends on no new operation or
cause, and is balanced. Opaque handles and evidence IDs never become features.

For each word independently enumerate all three distinct proposed new operations
and the four causes: report-only, one-event exception, local correction, parent
correction. Retain all 144 joint alternatives per public context (36,864 per
split). Report-only and one-event exception preserve future physical meanings;
local correction changes only local future meaning; parent correction changes
both local and sibling future meanings. Claims report the proposed new operation
at time 0 for each word, regardless of whether that report governs future events.

Teach four parent-scope physical endpoints per word at time -1, over active
inputs 0,1,2,3 and spectator 0. Alternate the two words, starting with the context's
starting word. Then deliver both local claims at time 0 in that same word order.
Each word has two time-1 physical probes at active inputs `(bw+1) mod 4` and
`(bw+2) mod 4`, spectators 0 and 1. The first probe is local for even aw and sibling
for odd aw; the second uses the other scope. Neither probe has its word's target
active input. Queries are separate time-2 events, with no copied target answers.

TRAIN probe word orders are 0101/1010; TEST orders are 0110/1001 (according to
starting word). Each word's first probe precedes its second. The combination of
independent old meanings, two claims, joint change alternatives, disjoint active
input sums and held-out cross-word receipt order is prospectively new observable
structure. Reusing the old opened bank with new handles is prohibited.

TRAIN selects eight alternatives per context: two uniformly without replacement
from each persistent-change mask (neither/word0/word1/both), with Python Random
seed 20261110102 in context then mask order. Each mask has 36 alternatives, so
this preserves the joint population prior in expectation. Total TRAIN is 2,048
histories. TEST retains all 36,864 alternatives. The mask is evaluator-only.
Identical public prefixes have identical handles regardless of hidden world.

## Frozen observations and models

Reuse the five already-published `data/temporal-native-transfer-v1/native-*.json.xz`
tables and their manifest hashes as frozen native endpoint forecasts. No language
or world refit/projection rerun is needed. Query features remain 41 values and
receipt features 18 values, exactly as `temporal_native_models_v1.receipt`.
TRAIN uses existing SVO/OSV layouts, TEST existing VOS. Native inputs still supply
four interpretation hypotheses; this experiment does not discover that family
or acquire a new sentence family. IDs are custody metadata, not neural inputs.

Use PyTorch 2.10.0 and NumPy 2.3.5, matching the repository's numerical pins;
record the exact Python and library versions in execution receipts.
All models use CPU float64, 16 recurrent scalar coordinates and learned initial
state values drawn independently from Normal(0,.05) with the model seed. The
initial vectors are generic, with no assigned word, scope or meaning. Two
identical initial slots are forbidden because shared updates preserve that
symmetry. All other layers use PyTorch defaults under the same isolated seed.

**Selective native (2,188 parameters):** two 8-value slots M. One shared
GRUCell(18,8) proposes each slot's update. A shared receipt MLP 18→8→8 with tanh
after each layer yields k. Attention is softmax over `dot(Ms,k)/sqrt(8)`.
Update `Ms = Ms + attention_s * (GRU(receipt,Ms)-Ms)` for both slots using the
same old state. Query MLP 41→8→8 with tanh yields a read key; the same soft
attention pools the two slots to eight values. Concatenate pooled state and
query, use Linear(49,16), tanh, Linear(16,4), softmax and mix the four native
endpoint rows. Inventory: initial16 + GRU672 + write224 + read408 + trunk800 +
head68 = 2,188. Slot order is exchangeable. No hard slot selection, word-indexed
storage, identity equality mask, protected flag or answer-copy path is allowed.

**Dense native (2,244 parameters):** learned initial16, GRUCell(18,16),
Linear(57,8), tanh, Linear(8,4), softmax, native endpoint mixture.
**Dense flat (2,280 parameters):** same dense state/trunk, Linear(8,8) endpoint
softmax. All three receive identical tensors. Parameter differences are +2.56%
and +4.20% relative to selective native. The dense native arm is a memory
architecture comparison: parameter allocation and trunk widths also differ.

## One matched fit

Seeds 7,11,23,37,53. Adam lr .01, other defaults, 256 updates, batch128,
sampling with replacement using Python Random `20261110200+seed`. Save exact
minibatch digest, initialization/final parameter hashes and all losses. No
clipping, early stopping, regularization, calibration fit or hyperparameter search.
Use six equally weighted observed endpoint NLL terms: each of the four physical
probe predictions immediately before its own receipt, plus both final target
predictions after all four receipts. Claims are inputs, not truth loss labels.
Every arm has 32,768 sampled episodes and 196,608 forecast terms per seed.
The objective is symmetric across words and is fixed before any fit.

## Collection and question policy

Freeze all fifteen fitted checkpoints before reading TEST observations. Save both
target distributions after teaching, after both claims, after the first pair of
physical answers, after the third answer and after all four. Save every next-probe
forecast. The cleared control uses each fitted model with the first pair of
post-claim physical updates omitted, then receives the remaining two answers;
this is an evidence ablation, not full episodic clearing.

At the prefix after the first pair of answers, offer each word's own second
probe as a separate one-question decision about that word's target. These two
decisions use the same prefix and are fixed before either optional answer.
For each word predict all eight question outcomes, simulate each possible receipt
and save its target distribution. Expected gain is the question-distribution
weighted maximum of the conditional target predictions minus current maximum.
Ask strictly above fee (.05,1,unavailable), tolerance 1e-12. A purchased answer
updates that decision's state alone; the other optional answer is not free
evidence. Also collect the full four-answer sequence as a distinct fixed-schedule
diagnostic. Make the same decisions for cleared state and both dense controls.

No learner or fit reads private evaluator records. Preparation saves TRAIN and
TEST observations separately and a separate oracle file; scoring opens that file
only after raw forecasts are published. Source and input hashes, consumed prefix
IDs and all weight hashes are retained. Exact receipt replay is ignored, while
conflicting reuse of an evidence ID fails. Independent custody is not claimed:
this is a same-team prospective development experiment with separated stages.

## Observational oracle, decision and complete reporting

For each public context compute posterior support over all 144 equally weighted
joint alternatives using only actually delivered claim/physical endpoints.
Exhaustive teaching must identify each old operation from observations; assert
this rather than silently conditioning on an unidentifiable old label. The
native mode calibration remains observed physical evidence. Retain ambiguity.
Compute exact conditional endpoint distributions for each saved prefix, cleared
prefix and optional-question branch. Never condition a posterior on the hidden
change mask, actual proposed operation, future answer or target outcome.

Report all law × seed × target-scope-change-mask cells (40), both words, all
arms and cleared controls. A target changes iff its current operation in its
queried scope differs from its old operation. Retention uses unchanged targets
only; a both-changed cell has no retention denominator and records N/A. Preserve
persistent-change mask and cause/scope diagnostics too. For accuracy comparison
within a hidden stratum, score the fixed observational oracle MAP on those same
rows; do not substitute mean maximum probability or condition the oracle on the
stratum. Report expected attainable accuracy separately. Proper-score excess is
the mean squared Euclidean distance from the observational conditional vector.

Keep the selective model only if every law/seed/target-change cell has final
accuracy at least oracle realized accuracy minus .02; excess Brier <=.02;
unchanged-target accuracy >=.95 where applicable; confident (.95+) wrong
targets <=1% of all targets; observed Brier no worse than dense flat by >1e-12
and better than selective-cleared by >1e-4; and cheap-question realized net reward
no worse than dense flat or selective-cleared by >1e-12. These retain the prior
numeric gates and add explicit change-stratum requirements. If a comparison has
no evidence benefit, report that fact; do not relax a failed frozen gate.

Publish pooled and worst-cell accuracy, full multiclass Brier, uncapped NLL,
conditional proper-score distance, confidence errors, retention, paid questions,
realized/net reward, native-versus-dense-native comparisons and every adverse
case ID. Report parameter/state counts, source Python growth, CPU/wall time and
RSS. Save complete models and raw endpoint arrays with deterministic rescoring.
Use synthetic invariants for soft slot exchangeability, no target/future-answer
leakage, exposure equality, split/order correctness, full oracle support and
scorer denominators. Run affected tests and one isolated regression gate; do not
repeat historical audits absent a concrete defect.

Full G5 admission, new linguistic families, full episodic-clear competence,
matched-correctness clarification savings, independent reproduction and the
inclusive 2,000-line objective remain open regardless of this result.
