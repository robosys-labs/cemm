# CEMM Authoritative Hybrid MVP Architecture

> **Activation note:** Replay status is derived only from
> [`governance/replay_status.jsonl`](../governance/replay_status.jsonl). This
> document describes architecture and does not own phase status.

## Purpose

This isolated development proof targets bounded conversation that preserves
meaning, reasons from attributable evidence, clarifies uncertainty, learns
authorized aliases and produces faithful readable responses. It retains the
five-operator exact core, reviewed authority, bounded inference, session context
and sole effect ownership. Learned proposal and realization are release targets,
not claims that an admitted neural runtime or complete conversation loop exists.

The target runtime pipeline is:

```text
closed-class form evidence + reviewed/world designations
→ bounded revision-pinned ProposalContext
→ ranked ordered SemanticSwitchProgram derivations
→ exact program validation and SemanticExpression compilation
→ VerificationBatch[VerifiedMeaning]
→ expression-based query / admission / effect decisions
→ exact ResponseMeaning
→ constrained learned surfaces
→ round-trip canonical-expression equivalence
```

## Semantic algebra and ownership boundary

A `SemanticSwitchProgram` is an ordered construction procedure. It is not the
canonical meaning graph. `SemanticExpressionCompiler` compiles a complete
Program ABI 3 derivation into a canonical multi-root `SemanticExpression` whose
applications use only the five persistent operators. Scopes, expression links,
variable binders and proposition-valued fillers are recursive expression
structure rather than additional persistent operators.

Program hashes include the exact proposal-context ref, ordered indexed actions,
dynamic pointers, roles, roots, source assignments and revision pins.
Expression hashes are derivation-independent and
normalize only bijectively alpha-renamable local IDs plus explicitly reviewed
commutative links. `VerifiedMeaning` binds expression to grounding, coverage,
compilation proof, verification receipt, revision and program lineage.
EVALUATE also receives an explicit verified `SituationContext`; program lineage
is never substituted for semantic identity.

ORIENT builds one bounded `ProposalContext` with current designation,
contribution, mode, application-frame, reference, scope, expression-link,
variable, transition and residual slots plus exact source geometry. PROPOSE and
VERIFY reuse that same object and its prebuilt bounded lookup indexes. VERIFY
retains a `CompilationProof` that accounts exactly once for every program action,
source assignment and root; compilation remains internal to VERIFY rather than a
new runtime phase.

The ranker receives only action programs built from retrieved reviewed authority and literal spans. It cannot create semantic atoms, event signatures, state dimensions, relation types, capabilities, permissions, or adapters.

Unknown content such as `telescope` remains a literal frontier. The proposal phase cannot create `entity:telescope` or `concept:telescope`.

## Store separation

- **AuthorityStore:** immutable reviewed atoms, designations, signatures, rules, capabilities, permissions, adapters.
- **WorldStore:** admitted facts and learned aliases targeting existing authority.
- **SessionStore:** lifecycle, participants, focus, obligations.
- **EpisodeStore:** immutable turn receipts.
- **ModelRegistry:** model revision and training-manifest identity.

Every turn emits a revision pin across all five.

## Recursive meaning

A graph can contain up to 24 applications and depth 6. Application-valued roles
use exact links. The target speech-attribution representation is:

```text
EVENT(say, actor=Mary, content={app:leave})
EVENT(leave, actor=Bob)
```

The public surface path now composes a single reported clause with clause-local
roles, content and scope, including explicit child actors and bounded speaker
control for reviewed communicative children. It does not invent an unspoken
embedded addressee. The reviewed multi-root repair now deduplicates equivalent
semantic search states while preserving future legal continuations and source
ownership. The independent two-sentence report reaches selected VERIFY within
unchanged limits; genuinely competing interpretations remain ambiguous.
Clause-local occurrence/admission traversal retains source attribution.
Attributed content must not become unscoped world truth.

The unadmitted communicative increment retains original evidence/context in a
typed source envelope and authenticates the actual selected program, receipt,
coverage, root translation, local roles and orientation. A direct performed act
is not a claim. A reviewed reciprocal policy requiring `cap:respond` may select
one outgoing event with system-to-speaker roles; third-party recipients grant
no system reply. Source force, response selection and wording are separate.
Every live consequence sink authenticates the source; codecs only check shape
and identity. Missing source cannot silently restore attribution.
Live finalization and execution require activated authority matching the
original semantic generation, independently of optional source/reply artifacts.
Authority-free codecs cannot authorize a
journal write; omitting authority is not an ordinary-claim fallback.

Source pins are not response pins or current read pins. Keyed selected-evidence
authentication proves that a learned designation predates its original source;
it does not reground the text. The existing no-effect journal binds the exact
evaluation and original pin, rejects stale initial requests and preserves exact
terminal retry receipts. Before EFFECT, the actual original SituationInputBundle
and existing verifier own full situated reconstruction, including phase and
turn index. After EFFECT, the original journal is authenticated before consuming
phase or selection; no additional Cycle payload is retained.
Necessary wire versions are Situation 2, Decision 2,
Evaluation Bundle 3 and Response Meaning 5, with Source/Selection 1 and unchanged
shared R3 ABI 2. Authority generation `authority-v1-2026-10-02-communicative-source`
uses the existing store activation check to reject incompatible predecessors.
Independent review and living-selector reconciliation remain pending; this is
not R4/R5 admission or learned realization. Generic diagnostic graph wording
does not authorize normal surfaces, world mutation or verified focus.

The reviewed-rule dependency index is generation-bound. `LinkedAuthority.rules`
and every nested rule clause are immutable within a generation. Generic rule
publication is deliberately unavailable in the predecessor learning coordinator:
a complete replacement bundle must eventually be linked and activated with its
stores rather than mutating a live authority object. The index is populated at
query-owner activation. Each QUERY captures one immutable authority snapshot,
gets an O(1) lock-free cache hit in the normal case, passes its local immutable
rule maps through retrieval/proof validation, and rejects an authority change
before returning. This prevents newly published rules from being evaluated under
an old store pin without adding a normal-cycle scan. Persisted derived evidence
cannot add provenance: its exact source set is reconstructed from the reviewed
rule and recursively validated premises. Only exact `support` and `deny` fact
and rule stances enter this evaluator.

Naming literals preserve complete construction-local source spans, including
already known words. The literal and target must belong to the selected naming
frame; a valid output port alone is insufficient. The proposer caches its bounded
legal-choice index once, while verification reconstructs locality independently.
Known event words inside labels or designation targets are mentions, not
directives. Affordance profiles are reused across occurrences without deleting
later occurrences or increasing global limits. The reviewed EN/ES form sources
now retain straight/curly quotation and guillemet boundaries as critical discourse
residuals, including boundaries inside full-span designation occurrences. Source-
local containment preserves unquoted aliases and prevents stripped naming
fragments. General quotation interpretation and punctuation-prefixed label
ownership remain unavailable; boundary evidence alone cannot license a literal.

## Exact inference

Reviewed rules run in bounded forward chaining. Existential consequents produce transient `exists:*` proof witnesses and never become authority or durable world entities.

Nonlexical QUERY uses the existing revision-pinned read snapshot and a physical
predicate/argument posting index maintained atomically by the world store. It
backward-closes only relevant reviewed rule heads, retains conjunctive premises
and intermediate entities, and validates persisted proof dependencies by exact
key inside the same snapshot. Incomplete retrieval, rule selection, joins,
closure or proof reconstruction yields `BUDGET_EXHAUSTED` with no answer or
proof. The configured bounds are unchanged. Lexical authenticated-designation
lookup remains a separate consumer, and scoped/proposition queries that lack an
admitted representation remain partial rather than being widened by indexing.

The included chain is:

```text
mother_in_law(Alice, Bob)
→ has_partner(Bob, ∃partner)
→ marital_status(Bob, married)
```

## Neural model target

The retained neural design uses a PyTorch Transformer to encode:

- normalized input plus closed-class/semantic features;
- candidate graph-action token sequence.

A learned scorer is intended to rank candidate programs; ranking cannot own
semantic authority. Exact owners validate and compile programs, group derivations
by expression, and retain truth, effects and realization-equivalence authority.
This describes a conditional model target, not current learned activation.

Graph validity, intended-meaning correspondence, evidential support and permission
are distinct judgments. Same-parser round-trip proves consistency under that
parser; independently specified contrasts must also test human meaning. Internal
atom kind is not a definition, and proof of that different proposition is not a
correct answer to a definition request.

The approved October 1 foundation migration adds a nonpersistent canonical
query-projection leaf under Semantic Expression ABI 3. It preserves requested
description/definition content and a grounded target without inventing a dummy
world assertion. The read-only description component now binds that request
before its pinned read under Description/Proof Bundle ABI 2, without a final-query
back-reference. Dedicated QueryResult ABI 3 now owns the final signed bundle and
distinguishes projection information from ordinary proposition support. This
unadmitted query/evaluation component has passed independent spec/quality review.
Response Meaning ABI 4 also passed both reviews: exact neutral answers retain
signed evidence and attributed status; other terminals retain the request.
Actual-source sinks bind the decision, bundle, situation and effect, preserving
distinct original proof and journal-advanced response pins. Codec identity alone
does not authenticate the source or stored claims. ProofGraph and the shared
artifact envelope remain ABI 2. Manufactured UNKNOWN sources
are not public query authority. Codec, source reconstruction, signed proof lineage,
answer linkage and signed surface realization have separate owners in the
existing foundation plan. Unsigned diagnostic realization rejects projections.
Public activation remains unavailable while any owner is
unfinished. Neighbourhood reconstruction is not definition sufficiency.

## R3 cognition and R4 reviewed-data activation

R3's semantic contract consumes selected `VerifiedMeaning.expression` plus an
independently verified `SituationContext`, producing a canonical Decision,
exactly one Effect/No-Effect receipt and one `ResponseMeaning`. Program identity
remains derivation lineage. Normal learned surface realization remains subject
to R5 admission rather than being implied by a selected expression.

The approved [foundation amendment](superpowers/specs/2026-09-07-foundation-proof-corrective-amendment.md)
and [implementation plan](superpowers/plans/2026-09-07-foundation-proof-implementation-plan.md)
own current execution. Inspect the whole independent semantic matrix before
choosing dependency repairs. The September 3 closure and unresolved-designation
designs/plans are historical evidence, including their exact stops and reusable
acyclic-frame/canonical-designation work. The historical known-definition green
proved traversal despite a false atom-kind answer; removing that answer is only
containment, with open-query and useful-response acceptance still required.

An explicitly development-only compositional response reference may use existing
semantic owners before R5. It preserves roles, scopes, perspective, provenance
and uncertainty; it cannot become a release fallback, a second semantic runtime
or purported learned output. Normal verified focus still requires exact
realization equivalence. This adds no phase or gate.
The bounded reference is implemented in `development_reference.py`, with an
explicit development-profile runtime method and `--development-reference` CLI
option. Independent specification and quality reviews pass. It emits transient
readable diagnostics and provenance, not a normal realization receipt or focus
write. Direct mixed participant/entity role correspondence is now repaired and
independently reviewed; named negative/embedded preservation and genuine
polysemy remain tested. Mixed scope/embedding and other ordinary-input paths
still block conversation completion. A running CLI or readable graph retelling
is not acceptance of a useful conversation.

The October 1 ordinary-input audit separates complete meaning with missing
wording from missing response meaning. Unary capability answers and single-variable
relation/type queries now have independently reviewed complete diagnostic grammar.
It retains exact queried roles, binder identity, participant perspective,
designation provenance and uncertainty; the binder does not license an inferred
person-kind restriction or existence claim. Unsupported structures fail closed.
At that audit checkpoint, greetings entered observation/admission and the response
builder retained the source expression for non-answer decisions; no reciprocal
response was selected. The coupled C3b/C4 implementation addresses semantic
response selection rather than replying to a surface string; its current review
status is recorded in the foundation plan. The form pack's
declared suffix lists are not consumed by the current resolver/grounder, so they
do not prove usable input morphology. The existing foundation plan owns these
distinct earliest-owner repairs; no new kernel operator or release claim follows.

Foundation amendment section 9 now authorizes a bounded communicative-act
extension. Reviewed source construction and exact local roles must distinguish
performed communication from mention or an attributed event claim. Unsupported
quotation retains critical unresolved evidence. A manifest-owned semantic control,
not a word-specific reply, may select an outgoing event by reciprocal participant
substitution only after exact source force, policy, capability and original pin
authentication. The non-claim consequence uses existing evaluation/effect/response
owners and read-only idempotent journaling; it neither admits the received event as
truth nor manufactures a query. Source and selection evidence must survive actual
artifact and cycle sinks. Implementation and independent evidence are tracked as
C1–C5 in the existing foundation plan; incomplete owners remain unavailable.
Controlled-target witness linkage must be authenticated before mode dispatch,
including paths without a retained source. A bare single-root controlled
OBSERVE event requires source evidence regardless of receipt provenance; the
requirement does not infer force. Before journal reservation, the effect gateway
must share the exact trusted store handle with the source owner's reader.
C3b/C4 pass independent SPEC and QUALITY review. Existing owner/phase selectors
are refreshed from current literal metadata; numeric limits, frozen evidence
and admission roots are unchanged. C5 fixture alignment and full regression
remain open, and the extension is not phase-admitted.

Attributed claim evidence retains each claim's `support` / `deny` stance; this
is not a cryptographic signature over answer meaning. Artifact identity,
publication authorization and learned contribution prove different properties.
Functional development output cannot establish R5 capability. The retained R5
design requires content-sensitive structural/pointer decisions and
graph-conditioned surface-unit decoding, not status-based canned sentences or
fixed-label confidence. Its existing weight-use evidence must test semantic
performance, not a deliberately invalid zero-logit output. These distinctions
neither change semantic authority nor authorize training before R4.1 admission.

Bulk R4.1 authoring, review/export, purpose allocation, realization-recipe review,
corpus expansion and source-package publication remain frozen. R5 training,
selection, calibration, frozen evaluation and realization activation remain
unavailable until fresh R4.1 admission. No pilot training is authorized before
that admission plus explicit isolated R4.1-compliant data authorization. Later
research is a separate bounded permissioned evidence consumer; no network adapter
is authorized by the foundation increment.

R4.1 separates duplicate-risk grouping from semantic stratification. Reviewed
lineage groups prevent source, paraphrase, normalization, mutation and
environment duplicates from crossing a protected boundary. Operators, roles,
modes, common participants, response actions, semantic targets and realization
actions remain class-local coverage labels unless an explicit challenge-holdout
contract promotes one identity into a holdout key. Every purpose class proves
its own semantic denominators. Unsupported reviewed minima fail rather than
being trimmed.

Expected semantic expressions, reviewed derivations, typed abstentions and
reviewed response surfaces are independently authored contracts. Runtime or
bootstrap proposal output remains diagnostic lineage and cannot become gold.

## R5 hard-cut foundation boundary

The R5 hard-cut foundation is shaped so its source, owner and phase gates pass
independently while admission remains unavailable until a separately reviewed
activation increment provides its missing owners. This is a static architectural
boundary subordinate to the foundation-proof amendment, not a replay-status
claim. Current status is derived only from the replay ledger named above; this
document is not admission evidence.

The foundation authenticates the artifact, proposal, data-isolation,
realization and legacy-hard-cut boundaries without claiming that neural proposal
or realization is active. Only after fresh R4.1 admission may release training
open the authenticated, authorization- and capability-bound canonical train
partition. The isolated
consumer receives one immutable train snapshot and its provenance; it receives
no sibling class path, hash, ref, count, payload, or manifest identity. The
`train`, `selection`, `calibration`, and `frozen_test` names are current R4
purpose classes, but only the train class is consumable by the R5 foundation.
Selection, calibration, and frozen-test access remain owned by
`R5-Neural-Activation`. A deferred neural obligation is not an admitted model,
checkpoint, calibration, or evaluation result.
