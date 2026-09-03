# Unresolved Designation and Research Handoff Design

**Date:** 2026-09-03
**Status:** design, implementation plan and acyclic ownership amendment approved; Tasks 1–3 reviewed; vertical implementation incomplete before Task 4
**Scope:** `hybrid_mvp/` representation closure and its bounded handoff to a
future self-research capability

This design resolves the representation blocker recorded by the R4 closure
slice. It does not admit R4.1, activate R5, authorize network access, publish
authority, or adopt Hybrid behavior at the repository root. Implementation
was authorized by the approved implementation plan. Independent Task 2 quality
review exposed a content-addressed frame/variable ownership cycle. The user
approved the narrow one-way ownership amendment now incorporated in section 4.
Task 2 passed renewed spec and quality review at `aeaad1f`; downstream
implementation advanced through Task 3, which passed spec and quality review
at `40151e8`. Task 4 preflight then proved that the existing generic query
features cannot distinguish designation from location questions. A reviewed
form-evidence amendment is required before unresolved builder emission; do not
introduce a source-word branch or reinterpret every copular query as designation.
The historical stop record and current repair boundary are in
`../plans/2026-09-03-unresolved-designation-implementation-plan.md`.

## 1. Decision

An unknown surface in a designation query is neither a semantic atom nor an
uninterpretable residual. It is exact surface evidence participating in an
open `op:designation` application.

For `What is zorbulate?`, CEMM must preserve all of the following without
creating `concept:zorbulate`:

- the exact literal `zorbulate` and its character span;
- the reviewed lexical-label family;
- one target variable whose value is the requested semantic identity;
- the interrogative binder and query force;
- source, construction, authority-generation and derivation provenance; and
- an unknown query result when no designation fact binds the variable.

The unresolved form can later become the subject of clarification, attributed
external research, or reviewed acquisition. None of those later activities may
change what the original turn meant.

## 2. Rejected approaches

### 2.1 Default concept creation

Automatically creating `concept:zorbulate` is forbidden. It converts surface
evidence into semantic authority, collapses possible semantic kinds, confuses a
designation with its target, and violates the anti-bloat and no-ref-name-
lexicalization contracts. A reviewed acquisition may eventually create a
concept, event type, relation type, entity or other identity, but only after
its kind and meaning are established independently of the spelling.

### 2.2 Optional fields on the existing grounded frame

Making `designation_slot_ref` and `predicate_target_ref` nullable would create
many invalid partial states and weaken the verifier for every grounded frame.
The unresolved case must be an explicit tagged variant with its own exact
invariants.

### 2.3 Network lookup inside grounding or proposal

Grounding and proposal must remain deterministic, bounded and side-effect-
free. A WordNet or Wikimedia response cannot be required to interpret the
user's query and cannot participate in canonical expression identity.

### 2.4 Bulk dictionary import

Preloading every dictionary or encyclopedia entry would make the language pack
an expanding semantic dictionary, introduce unreviewed authority and recreate
the corpus/gate performance problem. Research is selective and query-bound.

## 3. Canonical designation correction

The closure audit exposed a second issue beneath `ApplicationFrameSlot`: the
current designation path commonly uses the designated target itself as
`SemanticApplication.predicate_ref`. That prevents an open target query because
the unknown target is required before the query can exist.

The corrected designation shape is:

```text
op:designation(
  predicate_ref = label:lexical,
  role:label_type = label:lexical,
  role:surface = literal("zorbulate"),
  role:target = ?meaning
)
```

`label:lexical` is existing reviewed authority. It identifies the designation
family; it does not identify the unknown meaning. Known designation facts use
the same shape with a grounded `role:target`. Name queries use their reviewed
label subtype, such as `label:name`, rather than a token-specific branch.

This is a semantic-expression correction, not a query-engine exception.
Designation fact projection, query matching, learning commits, expected
expressions and realization equivalence must agree on the corrected shape.
There must be no operator-specific fallback that silently accepts the legacy
target-as-predicate encoding.

Because this changes canonical expression content and serialized Proposal
Context, implementation must make one explicit hard cut with the minimum
necessary ABI changes. The implementation plan must prove whether Program ABI
2 can remain unchanged; its existing `instantiate_operator`, `bind_role` and
`project_variable` actions are sufficient in principle, so a Program action-
vocabulary bump is not authorized by this design.

## 4. Proposal Context representation

Proposal Context owns a closed tagged application-frame union. The existing
grounded class remains the grounded variant; it is not renamed merely for
symmetry:

```text
ApplicationFrameSlot
  designation_slot_ref
  predicate_target_ref
  predicate_kind
  operator_ref
  roles, source geometry, affordance and provenance

UnresolvedDesignationFrame
  label_type_ref
  literal_contribution_slot_ref
  query_binder_slot_ref
  source_unit_refs
  construction_ref
  provenance_refs
```

Variable ownership is acyclic: the existing `VariableSlot.application_frame_ref`
points to the frame; the frame contains no target-variable pointer. Construct
the frame first, its variable second, and the context last. A derived bounded
`variables_for_frame_role(frame_ref, role_ref)` index resolves the target without
adding a serialized identity or changing the existing variable ownership law.
Each unresolved frame must own exactly one variable, with `role:target`, the
same construction, and source units backed by interrogative `open_variable`
contributions. Unrelated-frame, wrong-role, duplicate and mismatched-construction
variables are invalid. All record fields remain hashed. Placeholder refs,
reciprocal hash dependencies and relaxed compiler ownership are forbidden.

Exactly one `UnresolvedDesignationFrame` may be emitted for one authenticated
designation-query construction and one exact unknown span. It is legal only
when:

1. query and binder evidence are present in the form lattice;
2. the literal contribution covers the exact unresolved span;
3. no admitted designation candidate already resolves that same hypothesis;
4. the target variable expects a bounded, reviewed set of semantic kinds;
5. all source units are assigned once and no critical residual remains; and
6. the normal proposal, graph-depth and search-state limits are preserved.

The variant cannot carry an invented target ref, affordance profile, frame ref
or semantic kind. It cannot be used for an arbitrary unknown in a claim,
directive or event frame. Those cases remain typed frontiers unless another
reviewed construction licenses their structure.

## 5. Composition, verification and query behavior

The recursive composer may instantiate the unresolved frame without a
`select_designation` action because there is no designation fact to select. It
must bind the literal, bind the target variable, project the binder and consume
the exact construction evidence. All other frame and source-assignment rules
remain unchanged.

The compiler produces an ordinary five-operator `SemanticExpression`; the
unresolved-frame tag remains derivation provenance and does not become a sixth
operator or persisted semantic atom. Exact verification reconstructs the
frame, literal, variable, source span and query binder independently.

Stage 10 executes the designation query against the existing indexed
designation owner:

- one proof-bearing binding: `SUPPORTED`;
- multiple insufficiently separated bindings: `PARTIAL` with the existing
  ambiguity/blocker evidence;
- no binding: `UNKNOWN`, not false and not proposal abstention;
- exhausted bound: `BUDGET_EXHAUSTED`, not unknown knowledge.

An unknown result retains the exact query ref, expression ref, surface literal,
target variable, expected target kinds and authority generation. Response
meaning may truthfully say that CEMM does not currently know the designation
and may invite the user to explain it. It may not claim that the term is
meaningless.

## 6. Tracked unresolved meaning

The query result is the durable identity of the knowledge gap. A compact
frontier may be retained in session/episode state, but it must not be stored as
world truth or authority. Repeated occurrences may join the same frontier only
when their normalized literal, language, label family, expected target-kind
set, contextual constraint ref and authority generation are identical.
Contextually different uses remain separate, preserving polysemy.

The existing `LearningPlan` is not reused for research. It requires a known
`target_ref`, a learning permission and an eventual `op:designation` commit.
An unresolved research request has no such target and authorizes no commit.
Likewise, the existing mutating `EffectIntent` cannot be weakened merely to
carry a read-only lookup.

## 7. Self-research handoff

Self-research is a later, optional consumer of the exact unknown QueryResult.
It is not part of the R4 representation repair or closure acceptance path.

The practical flow is:

```text
unknown designation QueryResult
  -> bounded research goal authorized by capability and policy
  -> registered observation-only source adapter
  -> content-addressed external evidence receipt
  -> candidate senses/targets plus conflicts
  -> attributed response and/or reviewed acquisition proposal
  -> no automatic authority or world write
```

For the first MVP slice, research is one-shot and user-requested or explicitly
policy-authorized. It must not run on every unknown token. Background or
proactive research is a later policy choice using the same handoff.

Suitable sources have distinct purposes:

- the local designation and semantic stores are always queried first;
- WordNet-like lexical sources may suggest lemmas, parts of speech, senses and
  polysemy;
- Wikidata/Wikipedia-like sources may provide entity and encyclopedic evidence;
- the user's explanation is attributed dialogue evidence; and
- domain sources may be added only through reviewed, licensed adapters.

Each adapter receipt binds the source family, exact request, source identifier
or URL, revision/version when available, retrieval time, content hash, license
policy, normalized evidence, truncation status and conflicts. Limits cover
source count, response bytes, candidate senses, redirects, latency and total
research operations per unresolved query. Network failure leaves the original
unknown result intact.

`EffectGateway` remains the sole owner of external invocation. A later reviewed
design must add the minimum observation-only intent/result variant beneath that
owner, or prove an existing exact type can represent it without fake state
deltas. It must not create a parallel network/query gateway and must not loosen
the mutating `EffectIntent` contract.

External evidence may support either:

1. a candidate designation to an existing CEMM identity; or
2. a reviewed acquisition bundle for a genuinely new identity, its explicit
   kind, definition graph, designation and provenance.

Neither path publishes automatically. CEMM may immediately report attributed
evidence (for example, that a named source describes a term in a certain way)
without asserting it as admitted truth. Authority changes still require the
existing reviewer/acquisition policy, complete linking, atomic publication and
runtime repinning.

## 8. Error and safety behavior

- Source unavailable, timeout or denied permission: preserve `UNKNOWN` and
  report the research blocker.
- Source disagreement or polysemy: preserve all bounded alternatives and ask a
  context-sensitive clarification; never select the first source result.
- Existing local designation conflicts with external evidence: local reviewed
  authority remains authoritative and the conflict is recorded.
- Unsupported license or unverifiable revision: evidence is display-only or
  discarded according to source policy and cannot enter acquisition bytes.
- Research result arrives after authority reload: re-run the local query under
  the new generation before using it.
- Repeated request: use the exact content-addressed receipt or an explicit
  freshness policy; never perform unbounded retries.

## 9. Acceptance and anti-regression tests

The implementation plan must add the smallest owner-local tests proving:

1. `What is zorbulate?` reaches a verified designation query with exact literal
   and bound target variable, then returns `UNKNOWN` without an atom write;
2. the same structure with a known surface returns a proof-bearing target;
3. polysemous surfaces retain multiple candidates;
4. a plain unknown claim cannot use the query-only unresolved frame;
5. no `concept:zorbulate`, ref-name lexicalization, function-form entry or
   phrase dispatch is introduced;
6. known and unresolved designation expressions use the same label-family
   encoding;
7. Program ABI 2 remains valid unless an independent test proves it cannot
   express the design;
8. research is absent from the R4 closure run and normal unknown-query latency;
9. later research receipts are bounded, permissioned, source-attributed and
   incapable of direct admission;
10. an unseen synonym can be reviewed against an existing target without form-
    pack regeneration; and
11. equivalent multilingual designation queries compile to equivalent semantic
    expressions while retaining language-specific literal evidence.

No new validation tier or pytest process is authorized. Owner tests join the
existing R2/R3/R4 selectors, and the fixed twelve-case closure remains the
vertical acceptance boundary.

## 10. Sequencing and completion

Implementation is intentionally split to prevent another recursive expansion:

1. implement only the canonical designation correction and unresolved-frame
   vertical slice;
2. rerun the three-case diagnostic and then the fixed twelve-case closure;
3. if closure passes, prepare the separately reviewed mechanical R4.1 data
   correction and fresh admission;
4. resume R5 only after that admission; and
5. separately place and approve the observation-only research adapter in the
   downstream runtime roadmap, using the exact handoff in this document. It is
   not part of R5 training merely because R5 follows R4.1.

The first slice is complete only when the intentional unknown-designation RED
turns green without weakening any verifier or inventing authority. Research
capability is explicitly not required to make that test pass.
