# CEMM Runtime Architecture — Semantic Contribution and Native Learning Spine

## 1. Macro flow

```text
PRE-CORE FORM RESOLUTION
  raw text
  → reversible form lattice

A ORIENT
B OBSERVE / ENCODE
C GROUND / PROJECT
D CONTRIBUTE / COMPOSE / SETTLE
E STRUCTURE / REASON
F COMMIT / CAPABILITY
G GOAL / ACT / RECONCILE
H RESPOND / VERIFY / FINALIZE
```

The Stage 0–22 trace remains intact. The semantic-contribution expansion belongs between designation grounding and atomic composition and does not own a durable stage.

## 2. Pre-core responsibilities

Pre-core code may use Unicode processing, tokenisation, finite morphology, tries, quotation recognition and bounded span proposals. It outputs evidence and does not decide world meaning.

Closed-class lexical records provide structural features. Designation lookup provides semantic target candidates. Target affordance expansion adds compositional candidates without consulting surface text.

## 3. Grounding artifact

Each grounding hypothesis can contain several alternatives for one surface span:

```text
SurfaceCandidate(target_ref, label evidence)
  × AffordanceProfile(target_ref)
→ FormUnit/semantic contribution alternative
```

Scores combine designation prior, usage/salience evidence and affordance prior. The cross-product is bounded before global hypothesis expansion.

## 4. SemanticAffordanceIndex

The index is pinned to:

- authority generation;
- world revision;
- configured candidate bound.

Lookup order:

1. load target atom and semantic kind;
2. retrieve authority-linked explicit frames;
3. validate frame metadata;
4. derive semantic-kind defaults;
5. apply reviewed replacement policy;
6. deduplicate and keep bounded N-best profiles;
7. cache by target and revision.

No ordinary turn performs a whole-graph affordance scan.

## 5. Atomic graph integration

Schema slot constraints may inspect:

- `contribution_kind`;
- `semantic_kind`;
- `affordance_ref` where a specific frame is semantically required;
- `predicate`, reference or scope features;
- target atom kind/ref;
- typed ports.

The matcher merges:

```text
schema ports
+ dynamic contribution ports
+ reviewed projection ports
```

Required ports must be a subset of provided ports. Dynamic ports must be bounded sequences; malformed features are architecture errors.

## 6. Residual classification

A grounded contribution with `contribution_kind=predicate` is predicate-critical when unassigned, even if no language-pack `predicate=true` feature existed. This prevents learned predicates from being silently treated as harmless anchors.

## 7. Generic composition families

The runtime should converge toward a small set of families:

1. reference/nominal graph;
2. generic predication;
3. event/relation/state/designation assertion;
4. projection/boolean query;
5. modal proposition;
6. proposition complement;
7. correction/retraction;
8. discourse reaction/acknowledgment;
9. learning/definition query;
10. learning answer/teaching claim.

Possessive relational nominal evidence is a generic instance of
reference/nominal composition: it binds the participant-facing relation port,
introduces one candidate-local entity referent and permits a compatible event
frame to consume that referent. State-value predication uses the same graph for
claims and boolean queries; an unobserved but semantically valid dimension is
answerable as unknown, not rejected before query execution.

Language-specific examples supervise how form evidence fills these graphs. They do not define new semantics per phrase.

## 7.1 Reviewed definition graphs and projections

Composite meaning authority is a reviewed graph of five-operator applications.
Its deterministic rule projection supports sparse bounded retrieval but retains
the graph's `definition_ref` and source application refs in every derivation.
The runtime never selects a definition, port or conclusion from a surface word,
regex, target-ref spelling or domain-specific branch.

## 8. Typed learning flow

### 8.1 Query formation

A meaning question constructs an exact designation/definition query. Packet qualifiers carry a canonical learning contract ref, not an executable operation string.

### 8.2 Query execution

Stage 10 executes the exact query. Only an unknown/partial result with no binding and no critical frontier may be converted into a learning request.

### 8.3 Plan binding

The runtime binds the exact QueryResult to a `LearningPlan`:

```text
source_query_ref = QueryResult.query_ref
source_query = exact executed QueryStructure
authority_generation = pinned runtime authority generation
contract_ref = contract:designation_learning
capability_ref = cap:learn
commit_operator_ref = op:designation
surface_literal = exact observed surface
```

### 8.4 Goal and response

Goal arbitration receives the typed plan. Response CSIR carries the same plan and exact query metadata. Realization exposes one evidence literal and one expected answer contract.

### 8.5 Dialogue obligation

After verified realization/common-ground commit, DialogueState binds response and goal provenance into one pending obligation.

### 8.6 Continuation and commit

A continuation such as “it means hi” resolves the anaphor to the pending surface, resolves `hi` to its semantic target, constructs an `op:designation` proposal and commits it at Stage 13. Before the write, Stage 13 revalidates the exact plan, query, contract, target kind and authority-generation pin. The obligation is consumed after the commit receipt.

## 9. Capability composition

Modal capability queries are graph operations:

```text
capability modality
+ event/relation predicate
+ subject
→ required capability ref
→ capability assessment
```

The runtime resolves event/action → required capability through authority. It does not require the lexical verb to designate the capability atom directly.

## 10. Proposition embedding

A frame may declare `proposition_taking=true`. Its object/content role may bind an application reference or proposition graph. Nesting depth is bounded and included in coverage receipts.

Unknown embedded content becomes a typed open proposition and blocks only the owning graph region.

## 11. Activation

Runtime initialization should attest:

- semantic contribution ABI;
- form/coverage ABI;
- affordance frame relation availability;
- required learning contract atoms;
- generator/data hashes;
- module source hashes and checkout path.

Authority reload refreshes generation-pinned indexes and invalidates any pending learning plan licensed against the previous generation. Source changes still require process restart.

## 12. Observability

Stage traces should expose compact counts and refs:

- designation candidate count;
- affordance expansion count;
- contribution-kind distribution;
- explicit/default frame counts;
- dynamic-port validation result;
- learning plan ref/contract ref;
- pending obligation ref;
- commit receipt ref.

Do not expose internal semantic refs in user-facing surface output.


## Input/output vocabulary isolation

Realization grammar tokens are output-only and must never be fed back into pre-core form classification. The Interpreter supplies no language-pack `grammar_tokens` or legacy `function_forms` to the `FormProcessor`; only the generated form pack owns pre-core form classification.

## 13. Recursive Stage-5 and Stage-10 ownership

The Stage-5 chart preserves N-best alternatives under explicit state, scope, graphlet and depth budgets. Every final graph expands to the original form units and receives an ordinary fail-closed Coverage ABI 7 receipt before exact settling. Structural gaps remain typed frontiers and cannot trigger lexical learning unless their residual evidence is genuinely unknown.

Stage 10 executes semantic-description and provenance requests through the existing semantic store/query owner. Both paths declare operational resource use, remain read-only and emit exact typed results for Response CSIR.
