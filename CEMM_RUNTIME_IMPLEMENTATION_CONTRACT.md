# CEMM Semantic–Operational Runtime Contract

**Contract version:** 3.1.3  
**Coverage/Form ABI:** 6  
**Target runtime:** CEMM v1 Stage 0–22  
**Status:** sole normative implementation contract for this rewrite

This file governs the semantic–operational repair. `AGENTS.md`, README files,
phase reports, migration notes, and archived plans may point here but must not
restate or override it.

## 1. Runtime thesis

CEMM has one semantic brain. Text, sensors, operations, and dialogue provide
evidence from which candidate semantic structures are assembled. Exact semantic
structures, authority ownership, epistemic placement, operational observations,
and response obligations remain distinct.

The runtime must preserve this chain:

```text
surface observation
→ reversible form evidence
→ grounded N-best form hypotheses
→ atomic semantic candidates + verified coverage receipts
→ exact compilation and settling
→ discourse/query/claim structure
→ evidence-backed reasoning or operation
→ obligation-bound Response CSIR
→ perspective plan and same-CSIR realization
→ verified common ground
```

No later stage may recover discarded meaning by inspecting raw text. No stage may
replace its input meaning with an easier meaning. No compatibility parser,
phrase router, neural classifier, fact fallback, or legacy authority path may
compete with this chain.

## 2. The three enforced contracts

### Contract A — form evidence to semantic candidate

Every observed unit is either:

1. consumed into one exact semantic role; or
2. retained as one typed residual.

A critical residual blocks execution. A noncritical residual may remain as
background learning evidence without forcing a visible clarification.

### Contract B — semantic action to operational truth

Every runtime resource used by a stage must have one current observation in the
same cycle, authority generation, and world revision. Unknown, degraded,
unavailable, and available are distinct. Missing evidence never becomes numeric
zero. Planned or simulated state never becomes observed or committed state.

### Contract C — response meaning to surface

A response is built from one exact obligation and its source artifact. Realization
must preserve the same Response CSIR, query, bindings, target, polarity,
modality, epistemic status, and speaker perspective. Failure may produce an
equivalent canonical realization or no authorized surface. It may never fall
back to a supporting fact or unrelated self-state.

## 3. Authority ownership

Authority JSON files are one graph split across documents. Every atom has exactly
one defining owner. Other documents may reference but never redefine it.

The active ownership boundary includes:

- `base.json` owns `value:unknown`, `rel:subtype_of`,
  `rel:value_of_dimension`, and the canonical runtime-support dimensions;
- `conversation_foundation.json` owns conversation relations such as
  `rel:knows` and conversation resource identities such as
  `resource:inference_engine`.

### 3.1 Migration rules

A migration must:

1. load all authority documents before writing;
2. reject duplicate definitions even when their payloads are identical;
3. validate every atom, operator, role, fact filler, rule constant, control
   symbol, language constant, and pack hash;
4. preserve every surviving atom byte-semantically;
5. add no authority atom unless an explicit reviewed owner change is part of
   the release;
6. write atomically;
7. validate the complete graph again;
8. produce byte-identical output when rerun.

This rewrite’s authority migration is removal-only. It removes rejected first-
bundle vocabulary and timeless reviewed self-operational facts. It does not add
or replace authority definitions.

Operational `unknown` is cycle-local epistemic absence represented as
`state="unknown", score=None`. It is not a second definition of
`value:unknown`.

## 4. Pre-core form boundary

Only the pre-core form subsystem may use text-oriented machinery such as Unicode
normalization, tokenization, finite-state morphology, tries, quotation parsing,
NER, or bounded language-specific evidence extraction.

That subsystem may emit:

- reversible normalization alternatives;
- token and morphology evidence;
- designation candidates;
- entity/quotation/open-literal spans;
- syntactic-role evidence;
- multiple grounding hypotheses with provenance.

It may not decide semantic identity, discourse force, operator choice, world
truth, state dimension, operation, goal, or response.

The semantic core must not contain raw-string, keyword, substring, punctuation,
or regex branches that decide meaning.

## 5. Atomic construction algebra

There is exactly one active form-to-semantic construction path:
reviewed atomic feature schemas generated from annotated examples.

Schemas may constrain features including:

- discourse-force evidence;
- lexical category or learned semantic port;
- person, number, tense, aspect, polarity, possession, and emphasis;
- semantic anchor kind/reference;
- named/open/quoted span kind;
- syntactic or dependency role;
- bounded optionality and bounded span length.

Active schema conditions must not contain semantic surface matching fields such
as `literal`, `surface`, `regex`, `pattern_text`, `phrase`, or raw token arrays.
Inflectional variants must not multiply semantic schemas.

The English release compiler must prove:

- exactly one executable match for every annotated example;
- no cross-family executable collision;
- exactly one executable match for every non-singleton leave-one-out holdout;
- substantive review justification for singleton families;
- removal of every required critical slot makes the intended schema
  non-executable;
- reviewed negative probes remain non-executable;
- two generation runs are byte-identical;
- the checked-in pack equals the generator output;
- top-level and training-receipt ABI versions are both 5.

## 6. Coverage ABI 5

A serialized `InterpretationCoverage` receipt is untrusted and must be fully
recomputed during loading.

It binds to:

- `schema_ref`;
- `hypothesis_ref`;
- `match_seed_ref`;
- exact expected units;
- exact consumed units;
- typed residuals;
- semantic-role assignments;
- required roles;
- unit weights;
- body and seed hashes.

It explicitly exposes:

- silent units;
- extraneous consumed/residual units;
- duplicate input units;
- duplicate consumed units;
- duplicate residual units;
- consumed/residual overlap;
- role assignments to non-consumed units;
- units assigned to multiple roles;
- consumed units assigned to no semantic role;
- missing required roles;
- critical and noncritical residual references.

A normal receipt is executable only when:

- it has observed units;
- all units form one exact consumed/residual partition;
- all consumed units have exactly one semantic role;
- all required semantic roles are satisfied;
- no critical residual remains;
- every recomputed invariant is true;
- its provenance matches the selected schema, hypothesis, and match seed.

Missing coverage fails closed. A diagnostic receipt is verified but explicitly
non-executable. A receipt from one candidate cannot authorize another candidate.

Critical residual classes are:

- `force_critical`;
- `predicate_critical`;
- `argument_critical`;
- `polarity_critical`;
- `scope_critical`.

Noncritical residual classes are:

- `discourse_noncritical`;
- `punctuation_noncritical`;
- `emphasis_noncritical`;
- `modifier_noncritical`.

Stage 7 may report `stable=1` only for an exact packet whose selected receipt is
executable and whose interpretation status is `resolved`.

## 7. Required semantic competencies

### 7.1 Epistemic relation query

`Do you know Donald Trump?` must preserve:

- query force;
- `rel:knows` as predicate/relation;
- CEMM as subject;
- `Donald Trump` as one object mention span;
- boolean zero-projection query semantics.

A candidate that only consumes `you` is non-executable.

### 7.2 Designation assertion

`my name is Chibueze Opata` must compile to one designation application:

```text
op:designation(
  target=participant:user,
  label_type=label:name,
  surface=literal:text("Chibueze Opata"),
  language=literal:text("en")
)
```

The full name is a literal designation surface, not an independently grounded
person atom.

### 7.3 Optional emphasis

In `What's your own name?`, `own` is noncritical emphasis. The designation query
remains answerable and no visible learning frontier is opened for `own`.

### 7.4 Operational-condition request

`how are you` is an operational-condition summary request over the current
snapshot, not an unrestricted enumeration of arbitrary state dimensions and not
a lookup of seeded permanent states.

### 7.5 Metalinguistic explanation

A question about why a previous response used one surface choice rather than
another must target the exact prior `SurfaceDecisionTrace`, not the world model.
The prior decision must have a verified equivalence receipt.

### 7.6 Attributed open predication

`seems you're just pattern matching` must preserve a user-attributed claim about
CEMM and retain the open predicate surface. It must never trigger an unrelated
operational-state answer.

## 8. Query and retrieval contract

`QueryStructure` owns:

- restrictions;
- declared semantic variables;
- answer projection;
- immutable qualifiers.

An explicitly empty projection is a boolean query and must not be expanded into
all variables.

`QueryResult` must preserve the original qualifiers exactly. Response formation
must not infer query kind from proof fact shape, variable names, or surface text.

Retrieval requires a selective bound index key. It must:

- reject operator-only and disconnected all-variable plans;
- record used constraints and truncation reason;
- recheck returned facts against exact restrictions;
- never broaden through salience or `facts_mentioning`;
- keep rule/fact/depth budgets explicit;
- report underconstraint rather than scanning arbitrary facts.

## 9. Operational snapshot contract

The canonical resource ABI is:

- `resource:runtime_process`;
- `resource:semantic_runtime`;
- `resource:language_realizer`;
- `resource:output_channel`;
- `resource:inference_engine`;
- `resource:designation_index`;
- `resource:semantic_store`;
- `resource:common_ground`.

Startup fails when a provider is missing, duplicated, extra, incorrectly marked
optional, or exposes an invalid ABI.

Every cycle captures exactly one observation for every canonical resource. All
observations must share the cycle, authority generation, and world revision.

Resource states are:

- `available` with score in `[0.8, 1.0]`;
- `degraded` with score in `(0.0, 0.8)`;
- `unavailable` with score `0.0`;
- `unknown` with score `None`.

Invalid provider output is an architecture error. A provider execution exception
is a provider failure and must not be rewritten as evidence that the resource is
unavailable.

A stage calls the operational gate before using a resource. The resulting
`StageResourceUse` receipt is bound to the cycle snapshot and the exact resource
observation. Unknown and unavailable both block use but remain different
explanations. Degraded use requires explicit stage policy.

Adapter execution is gated before the adapter is invoked. Effect-journal and
operation-observation writes are gated before their semantic-store use.

## 10. Epistemic state and transitions

State assertions carry one of:

- observed;
- derived;
- predicted;
- simulated;
- desired;
- committed.

Predicted, simulated, and desired assertions are non-durable. Transition previews
must explicitly carry `epistemic_mode="simulated"`, causal-not-factual proof,
and no committed claim. Only returned operation evidence plus the owning commit
policy may create durable state.

## 11. Dialogue and learning obligations

Dialogue owns at most one bounded pending learning obligation.

A learning obligation may be created only when:

1. an exact query was executed;
2. its QueryResult is `unknown` or `partial`;
3. it has no answer bindings;
4. it has no blocking critical frontier;
5. exactly one learning probe matches the executed QueryStructure;
6. the learning operation is licensed by the immutable query kind;
7. the learning-request response is realized and verified;
8. Stage 21 persists the response/common-ground artifact.

Answered queries never open learning obligations. A second obligation cannot
silently replace a live one.

A confirmation such as `That's my name` may consume an obligation only when the
exact obligation is present, unexpired, matches the pending surface and expected
answer shape, and the designation commit has succeeded. Consumption is recorded
after the Stage-13 commit receipt, never before it.

## 12. Goals and obligations

A goal is bound to one source artifact. Examples include:

- answer one exact QueryResult;
- clarify one exact frontier;
- request evidence for one unanswered exact query;
- explain one prior surface decision;
- acknowledge one attributed claim;
- handle one directive through reviewed authority.

Blocked goals are never selected. When all goals are blocked, selection is
`None`; the runtime must not execute a blocked fallback.

## 13. Response CSIR and reference planning

Response CSIR must preserve:

- discourse action;
- obligation reference;
- source query/frontier/assessment/operation reference;
- target and audience;
- projected bindings and proof provenance;
- polarity, modality, uncertainty, and conflict status;
- evidence literals;
- immutable query qualifiers.

`ReferencePlan` is computed in the output frame:

```text
output speaker = participant:system
output addressee = participant:user
```

Therefore CEMM realizes itself as first person (`I`, `my`, `myself`) and the user
as second person. Ordinary and possessive forms are separate. Third parties use
a reviewed designation when available. Equal-weight incompatible reference or
predicate forms are an integrity error, not a lexical tie-break.

Colon-bearing evidence literals such as URLs and times are literals, not semantic
references.

## 14. Realization contract

Realization has two permitted paths for one Response CSIR:

1. an exact reviewed surface plan whose semantic signature matches; or
2. the constrained canonical grammar for that same Response CSIR.

A learned surface is accepted only when it equals the independently generated
same-CSIR canonical surface and passes placeholder/provenance verification.
Conflicting exact plans for one signature are rejected.

Forbidden fallbacks include:

- rendering a supporting fact;
- selecting a salient world fact;
- changing answer-bindings into a fact assertion;
- replacing a criticism or clarification with self-state;
- exposing internal semantic IDs.

Stage 21 persists the original Response CSIR, reference plan, selected surface,
verification result, and equivalence receipt. It does not reparse the output.

## 15. Stage ownership

| Stage | Owner | Required invariant |
|---|---|---|
| 0 ORIENT | session + service registry | pinned revisions and complete operational snapshot |
| 1 OBSERVE | evidence | immutable source/time/channel lineage |
| 2 ENCODE | pre-core form processor | reversible evidence; no semantic write |
| 3 GROUND | grounding lattice | N-best referent hypotheses retained |
| 4 PROJECT_STATE | state projector | entitlement and current evidence only |
| 5 COMPILE | atomic assembler + exact compiler | coverage/provenance verified |
| 6 RECURRENT_DYNAMICS | settler | exact violations clamped |
| 7 STABILIZE | coverage + settler | resolved/executable only |
| 8 BUILD_STRUCTURES | discourse/query builder | exact force and query structure |
| 9 EPISTEMIC_PLACEMENT | epistemic policy | attributed before admission |
| 10 QUERY_EXPLAIN | selective retrieval + inference | resource gate and qualifier preservation |
| 11 PREDICTION_ERROR | frontier/error layer | scoped typed gaps |
| 12 TRANSITION_SIMULATION | transition engine | simulated, never committed |
| 13 COMMIT | store | CAS, evidence, placement, receipt |
| 14 CAPABILITY_IMPACT | operational/capability algebra | current snapshot-derived assessment |
| 15 GOAL_ARBITRATION | goal arbiter | blocked goals unselectable |
| 16 PLAN_EXECUTE | adapter registry | resource, authority, permission, idempotency gates |
| 17 ASSIMILATE_OPERATION | operation evidence | bounded re-entry; no automatic admission |
| 18 RESPONSE_CSIR | response builder | exact obligation/source binding |
| 19 REALIZE | reference + grammar | same-CSIR realization |
| 20 VERIFY | equivalence/provenance | no semantic downgrade |
| 21 COMMON_GROUND | dialogue/store | verified output only, discourse CAS |
| 22 FINALIZE | runtime | compact receipts and bounded trace |

## 16. Validation architecture

A release validator is part of the product. It must use four independent proof
classes:

1. **serialized artifact validation** — content hashes, ABIs, authority ownership,
   deterministic generator output, idempotent migration;
2. **executable semantic behavior** — coverage, query, operational, dialogue,
   retrieval, response, and realization invariants;
3. **AST-level integration validation** — actual call ordering and dependency
   boundaries, not incidental source strings or variable names;
4. **transactional checkout validation** — exact preimage, clean detached staging
   worktree, full tests, allowed-path diff, target revalidation, exact rollback.

A comment, local variable spelling, or source substring is not proof of semantic
behavior when a structured or executable check exists.

## 17. Installer contract

The installer is valid only for:

```text
repository: robosys-labs/cemm
branch: agent/v1-foundation-integrity
HEAD: 3f541b7b1b6d5c827e9a88a8f0ba907b04c66622
```

It has no source-drift, skip-validation, skip-suite, partial-install, or force
flag.

It must:

1. verify package manifest and per-file hashes;
2. run its rollback fault-injection self-test;
3. verify branch, HEAD, clean status, and every reviewed blob;
4. validate the untouched authority graph;
5. apply each unsealed source target exactly once in a detached worktree and
   write its rewrite seal only after the complete file transformation succeeds;
6. run the source rewrite `--check` as a pure verifier twice, proving checkout
   immutability and isolated-copy idempotence;
7. generate the form pack twice and require byte identity;
8. migrate assets twice and require byte identity;
9. run syntax, ownership, semantic-contract, legacy-contract, focused, and full
   test suites;
10. reject every changed path outside the declared target set;
11. copy only the fully validated bytes to the user checkout;
12. rerun the complete pipeline on the target without re-entering sealed anchors;
13. prove target bytes equal staging bytes;
14. write an uncommitted receipt;
15. on failure, restore HEAD, index, tracked files, untracked files, branch, and
   the complete non-Git file-tree digest, then verify the exact pre-install
   fingerprint.

## 18. Mandatory regression matrix

The release gate must include direct tests for:

- duplicate authority owner rejection, including `value:unknown`;
- removal-only and byte-idempotent migrations;
- deterministic generator and unique replay/holdout matches;
- full-name literal designation;
- noncritical `own` emphasis;
- Donald Trump relation/object preservation;
- critical residual blocking;
- coverage tampering and cross-candidate receipt reuse;
- provider ABI and provider-execution failures;
- unknown/unavailable/degraded distinction;
- snapshot and stage-ledger provenance;
- underconstrained/disconnected retrieval rejection;
- returned-row rechecking and no salience broadening;
- immutable query qualifiers and explicit empty projection;
- blocked-goal rejection;
- exact post-query learning handoff and critical-frontier blocking;
- commit-bound dialogue confirmation;
- metalinguistic surface-choice explanation;
- attributed open-predicate criticism;
- perspective-aware first-person realization;
- ambiguous reference/surface supervision rejection;
- same-CSIR canonical fallback and absence of supporting-fact fallback;
- installer rollback fault injection;
- source-rewrite single-seal integrity, pure-check immutability, isolated-copy idempotence and AST postconditions.

## 19. Change discipline

A change to this runtime is incomplete unless it updates together:

1. the earliest owning code layer;
2. source annotations or authority assets when applicable;
3. deterministic generators and migrations;
4. executable behavior tests;
5. structural/integration validators;
6. this contract when the ABI or invariant changes.

A passing phrase is diagnostic evidence, not sufficient acceptance.

## 20. v3.1.3 regression invariants

The following invariants are normative additions and clarifications:

1. strict semantic settlement remains `require_coverage=True`; compatibility
   fixes may not admit partial coverage;
2. each reversible normalization with at least one hypothesis receives one
   representative before global hypothesis truncation;
3. the matcher evaluates the complete bounded hypothesis × schema product and
   fails explicitly if its per-schema search-state budget is exhausted;
4. a kind named in `allowed_kinds` is permitted; a redundant `allow_*` flag may
   broaden a schema but may not contradict that explicit set;
5. reviewed structural lexical forms outrank heuristic named-entity proposals;
6. unknown single-token proper-name proposals remain available but proposal-only;
7. designation-property queries generalize over participant perspective while
   preserving possessive evidence and exact participant grounding;
8. contextual anaphoric meaning queries preserve the exact antecedent surface in
   both QueryStructure and any post-query learning obligation;
9. reduced diagnostic fixtures that do not expose an optional resource-status
   interface produce `unknown/None`, not an exception or invented outage;
10. a compatibility codec may exist only as a lazy diagnostic property and must
    never be called by semantic composition;
11. full-suite acceptance is differential against the untouched pinned HEAD:
    focused tests must all pass, test collection may not shrink, and no new
    failure/error ID is permitted;
12. construction/hypothesis provenance is audit evidence, not an executable
    semantic distinction; candidates with identical force, applications, query,
    directive, modality and meaning-bearing qualifiers must be grouped before
    posterior settling;
13. provenance grouping may remove only a closed reviewed set of provenance-only
    qualifiers and may never erase query kind, learning operation, discourse
    operation, known bindings or other meaning-bearing qualifiers;
14. runtime snapshots observe every canonical resource, but stage authorization
    checks only the baseline resources plus resources explicitly declared by the
    concrete component operation;
15. an absent resource-use declaration means no additional use, not that unknown
    evidence became available; a component that declares an unknown resource is
    still blocked by `OperationalInvariantChecker`;
16. resource-use declarations must be callable, iterable, nonempty where present,
    and wholly contained in `CANONICAL_RUNTIME_RESOURCES`;
17. the real interpreter declares designation-index use for observation,
    rule-delexicalization and reference resolution, while reduced interpreters
    without that behavior are not coupled to private implementation attributes;
18. `designation_learning` is an immutable query kind licensed only for the
    existing exact `resolve_designation` learning operation.

## 21. Native semantic spine ABI 1

A designation resolves possible semantic identity. A generation-pinned semantic
affordance index derives bounded compositional candidates from the target's
semantic kind and reviewed `rel:has_semantic_frame` links. Language packs may
provide morphology and closed-class structure but do not own open-class semantic
identity. A learned designation must become compositionally usable without form
pack regeneration.

A grounded designation is also a valid semantic-description target. Definition
or meaning-query evidence may select that target through reviewed contribution
metadata and issue a bounded `DescriptionRequest`; it must not be replaced by a
surface-specific dictionary branch or by an unrelated generic event reading.
After a successful semantic commit, the next cycle must bind the new authority
generation before resolving designations, affordances or descriptions.

Runtime learning continuation is represented by `LearningPlan` ABI 1. It is
bound to one executed QueryStructure/QueryResult, one pinned authority generation,
one reviewed contract, one capability, one five-operator commit effect, one answer
contract and one pending dialogue obligation. `learning_operation` strings are forbidden in active source,
training authority, generated packs and Response CSIR.

Nested propositions remain rooted graphs of the five fixed operators. Event
complements use explicit event refs in reviewed roles; no proposition operator or
phrase-intent kernel is introduced.

### 21.1 Reviewed atomic definition graphs

A reviewed composite meaning is an ordered, bounded graph of ordinary
five-operator applications with typed variables, existential witnesses and
ports. Its target is explicit and its applications are persisted through the
existing application/binding substrate. The reviewed definition receipt names
those application refs; it is the semantic authority.

An executable rule projection may be generated only from that graph. It carries
the exact `definition_ref`, cannot outlive the definition generation, and every
derived proof must retain that ref. A projection is an indexed execution view,
not a second rule-authority language and never a lexical or target-ref dispatch.

Possessive relational evidence binds a participant-facing relation port and may
introduce one bounded transient entity referent. A compatible event graph may
reuse that same referent in an event role. This is generic port composition;
surface spelling and semantic-ref fragments are forbidden as selectors.

Activation must attest Coverage/Form ABI 6, Semantic Contribution ABI 1,
LearningPlan ABI 1, PropositionGraph ABI 1, module provenance, generated pack
receipts and the linked frame/contract authority graph before serving input.

## Recursive Atomic Semantic Composition ABI

Stage 5 owns one bounded bottom-up composition chart. Form units may become
transient PropositionGraph ABI 2 units and compose into larger graphs. Graphlets
are never persisted and never create a sixth operator. Candidate-local app-valued
roles are admitted only by reviewed proposition-taking frames and are flattened
child-first before Stage 13.

Semantic description and epistemic explanation extend the exact Stage-10 query
path. Descriptions contain only indexed stored facts. Proof explanations contain
only exact application, claim, occurrence, source, inference, commit or runtime
snapshot refs. Stage 21 records bounded verified semantic focus after realization
verification; surface wording is never semantic authority.

Activation requires Coverage/Form ABI 7, Atomic Composition ABI 1,
PropositionGraph ABI 2, Description ABI 1 and Proof Bundle ABI 1. The obsolete
sentence-shaped embedded proposition family and one-pass Stage-5 fallback are
forbidden.
