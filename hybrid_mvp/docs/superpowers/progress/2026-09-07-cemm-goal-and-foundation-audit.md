# CEMM goal and foundation audit

> **Historical diagnostic evidence:** observations below describe the pre-repair
> source. Current work follows the [foundation amendment](../specs/2026-09-07-foundation-proof-corrective-amendment.md).
> Only `governance/replay_status.jsonl` owns phase status and admission.

Date: 2026-09-07

Status: diagnostic assessment and proposed direction. This document does not
replace execution authority, admit a phase, approve gold, or authorize a new
runtime path. The user's current request is to reassess the goal and weak
foundations before continuing implementation.

## 1. Decision supported by the evidence

Recommend a focused foundation rebuild inside the existing Hybrid MVP, using
the existing exact semantic core. The interpretation-to-answer path needs a
stronger specification and several owner-level replacements. A repository-wide
rewrite has not been justified: it would discard useful invariants while
retaining the unresolved questions that caused the current failures.

The central problem is a gap between **valid internal artifacts** and
**correct, useful interpretation of a conversation**. The current implementation
can produce an accepted, proof-bearing answer to a different question from the
one asked. More training, stronger hashes, and additional downstream review
cannot correct a distinction already erased upstream.

The previous claim that the known-definition closure case passed was too broad.
Its test establishes passage through selected owners, not a correct definition.
The next proposal to distinguish interrogative words was also insufficient:
even after separating `what` from `where`, `What is X?` can request a lexical
meaning, identification, classification, or description. Context and an explicit
answer projection are still required.

## 2. What CEMM is trying to prove

The original proposal separates uncertain language interpretation from exact
semantic identities, typed composition, evidence, memory, and effect authority.
Neural components propose and rank interpretations and surfaces; they do not
create semantic authority. Meaning is independent of the language or procedure
used to express or construct it.

The July completion proposal adds an empirical goal: show that this architecture
can learn useful recursive composition and compete with a frozen small instruct
model in selected domains using smaller trainable capacity. That is a research
claim to measure, not a consequence of having five operators or a verifier.

A practical bounded MVP should therefore demonstrate all of these:

1. Preserve the propositions, participants, roles, attribution, scopes and
   requested information in a bounded class of conversations.
2. Distinguish interpretation uncertainty from missing knowledge, conflicting
   evidence, insufficient permissions and missing execution resources.
3. Query, remember and reason from attributable evidence without silently
   upgrading a speaker's claim to world truth.
4. Clarify an unknown expression, acquire an authorized designation, and reuse
   it compositionally without regenerating a language pack.
5. Produce a readable response that expresses the actual result, including its
   uncertainty, without silently omitting important meaning.
6. Show learned generalization beyond reviewed examples, within measured
   latency, memory and search bounds.

These are different claims. Passing authority validation proves none of them
alone. Passing a deterministic diagnostic proves no learned generalization.
Passing a hand-authored graph test proves no surface-to-graph interpretation.

### Scope worth holding fixed

Keep the five application operators, typed references, recursive graph
composition, language/meaning separation, provenance, transactional admission,
and separation of claims from truth and intent from permission.

Initially prove a bounded conversational domain: people, a few objects and
states, definitions/designations, speech history, clarification, alias learning,
and one safe operation. Exercise unseen combinations and a second language
through the same semantic contracts. This is a proposed scope, not a claim that
the current English-only bootstrap already supports multilingual operation.

Defer broad autonomous research, unrestricted ontology acquisition, universal
language coverage and product-platform expansion until that loop works. Preserve
their extension boundaries now; do not implement all of them to close the MVP.

## 3. Evidence boundary and method

Inspected the root canonical contract set and the Hybrid MVP's active authority,
architecture, replay master, semantic-algebra amendment, R4.1 supervision
amendment, closure design, unresolved-designation design/plan and conditional
R5/R6 design. Root adoption remains separate; historical root implementation
status is not current Hybrid MVP completion evidence.

Also read the original proposal and review supplied under
`C:\Users\Son\Downloads\cemm_true_hybrid_architecture`, and the semantic-algebra
review under `C:\Users\Son\Downloads\hybrid_semantic_algebra_docs`. Donor
packages are evidence, not automatically adopted authority.

Runtime evidence:

- Current repair worktree: `codex/unresolved-designation-r4`, commit `228222d`.
- Main checkout: `f27aa53b82e04972688e479967d309f53a56de37`.
- Public composition root: `load_runtime(..., profile="development")`.
- Fresh disposable SQLite store for each input; default empty resource list;
  no external operation adapters; no user store was modified.
- Twenty-five fresh-input probes, eleven detailed selected-result probes, and
  three search/compilation probes in the repair worktree.
- Six confirmation probes against main. These reproduced the definition,
  interrogative-collapse, declared-capability and multiple-root findings.
- Search diagnostics compiled proposed programs for comparison. Compilation
  was not treated as verification or admission.
- The existing known-definition closure test was rerun separately with pytest
  and passed. The independently inspected expression still answers the wrong
  question. This directly demonstrates the limitation of that assertion.

This was not a full regression run, a training experiment, a release activation,
or a test of contextful dialogue. Fresh-context failures do not establish that a
properly seeded history/fragment test would fail. No acceptance percentage is
derived from this diagnostic sample.

Remote `main` was checked and fetched without pulling: it was at
`24d8b68a4c9b0c992362a1c2e542579b5f0c4280`, an ancestor of local main. This does
not establish the contents or merge-worthiness of every other remote branch.

Unless stated otherwise, code paths below are relative to `hybrid_mvp/` and line
references describe the repair worktree at `228222d`.

## 4. The important failures and their earliest owners

### 4.1 Accepted graphs can answer the wrong question

These three inputs produced the same selected expression and a supported query:

- `What is CEMM?`
- `Where is CEMM?`
- `Who is CEMM?`

The expression, simplified without changing its content, is:

```text
op:type
  predicate: concept:digital_agent
  subject:   concept:digital_agent
  type:      literal("concept")
```

It contains no answer variable, location relation or identification projection.
It establishes an internal atom-kind fact. The query has a proof; the problem is
what that proof proves. `Define mother.` and `What is a mother?` similarly
produce an atom-kind statement about `concept:mother`, not a definition.

Earliest owners:

- `data/languages/en/forms.json:48`: the interrogative entries share `kind=query`.
- `src/cemm_authoritative_hybrid/forms.py:976`: the resolver projects form
  evidence into categories/kinds used downstream.
- `src/cemm_authoritative_hybrid/proposal_context.py:2655`: definition evidence
  specializes a grounded nominal into the atom-kind application above.
- `src/cemm_authoritative_hybrid/r3_cognition.py:137`: reviewed atom kinds supply
  proof-bearing facts for that application.
- `tests/test_r3_r4_predecessor_regressions.py:131`: the known-definition test
  checks selected traversal, query mode and `answer`, not the requested content.

Required repair: specify a query's requested information and answer contract
independently of the implementation. Preserve interrogative/form distinctions,
but do not hardwire one intent to each question word. A known concept without a
reviewed definition is a valid query with missing answer knowledge.

### 4.2 Unknown vocabulary becomes whole-turn failure

`What is zorbulate?` has an ungrounded critical unit, no application frame and
no proposal candidate. `The server is offline. Zorbulate.` also abstains before
the known independent state proposition reaches cognition.

`proposal.py:527` rejects any critical residual before composition. The
non-selected branch of `runtime.py:556` produces no evaluation or response
meaning. Safe refusal to execute an unresolved command has become inability to
respond about what is and is not understood.

Required repair: preserve a scoped unresolved mention and its known structural
relationships. A missing identity is not an identity of kind `concept`, and a
missing fact is not an uninterpretable sentence. Known subgraphs may support
interpretation or clarification; their truth admission and effects must remain
subject to the surrounding scope and policy. In particular, never execute an
embedded command merely because its local clause is understood.

The existing acyclic unresolved frame and designation-expression work are
potentially reusable. They do not yet establish this conversational behavior.

### 4.3 Mode and capability decisions can precede sufficient meaning

`Alice does not like the book.` becomes QUERY, with `like` unresolved. The form
projection treats auxiliary evidence as query evidence, and the known `likes`
designation does not make this inflection usable in the tested activation.

`You learn hello.` and `Learn hello.` both become REQUEST and produce no complete
candidate. `runtime.py:193` derives a single mode from structural projections,
including effect-capable event evidence. Having an operation affordance does
not establish that a speaker issued a directive.

`Can you respond?` returns a supported capability query even though this
activation has no authorized surface realizer. The capability fact comes from
the authority participant/capability map (`r3_cognition.py:203`), not a proof of
current end-to-end availability. This can describe declared competence, but it
cannot by itself answer whether the present system can perform the activity.

Required repair: distinguish declared capability, currently satisfiable
capability, permission and an actual request. Preserve plausible discourse-force
alternatives until composition/context can resolve them. Do not infer authority
from the word `learn`, or duplicate each event as a phrase-shaped capability.

### 4.4 Search spends its budget on alternative construction histories

| Input | Programs | Explored states | Truncated | Successfully compiled / distinct expressions |
|---|---:|---:|---|---:|
| The server is offline. You said goodbye. | 48 | 768 | Yes | 48 / 4 |
| If the server is online, then the lamp is on. | 48 | 768 | Yes | 38 / 8 |
| Alice said Bob left. | 24 | 179 | No | 24 / 2 |

The first two are rejected after truncation. The third remains ambiguous.
Distinct compiled expressions are not necessarily correct interpretations.

`recursive_composer/_search.py:103` keys visited search by action sequence and
completed results by program identity. Meaning-level grouping occurs later.
`verifier.py:2196` rejects candidates from a truncated proposal because sufficient
uniqueness cannot be established.

Required repair: represent equivalent partial states compactly before spending
the search budget, and distinguish derivation diversity from meaning diversity.
Any equivalence key must retain source ownership, unresolved obligations, scope
and future legal continuations; naive early graph hashing is unsafe. Specify
what a bounded neural proposal can establish about candidate sufficiency.
Increasing caps or ignoring truncation is not a justified correction.

### 4.5 R4 closure and R5 activation have a dependency conflict

The September closure objective asks for practically usable meaning/response
behavior before bulk R4 review. The August R5 design prohibits R5 work until
fresh R4.1 admission, and reserves normal learned realization to admitted R5.

The runtime enforces that separation: `bootstrap.py:28` permits development only;
`runtime.py:687` returns `contract:r5:realize_surface` as a later-owner gap. Every
selected diagnostic above remains without a verified surface.

This is a planning dependency conflict, not an accidental missing UI string.
Reviewing or training larger realization families cannot prove a completed
conversation while the only normal realization owner remains unavailable.

Required design decision: introduce an explicitly diagnostic, compositional
meaning/response reference path for the foundation proof, or formally permit a
small experimental neural vertical slice before bulk corpus admission. Either
requires a reviewed change to the current freeze/admission plan. Neither may
silently activate a canned fallback in the product runtime.

Recommended: establish the diagnostic semantic/realization oracle first, then
use the same cases for a small learned pilot. It must share the canonical
semantic model and owner APIs, remain excluded from learned/release claims, and
have a defined retirement or developer-only role. Do not create a second brain.

### 4.6 Bounded output does not imply bounded retrieval work

`r3_cognition.py:110` materializes views of all world facts. The SQLite
`persistence.py:1463` implementation retrieves all facts ordered by reference.
Later matching/inference limits do not bound that initial read and conversion.
They can also make globally ordered prefixes determine what evidence is seen.

This is a static scaling defect/risk, not a measured latency result.

Required repair: indexed retrieval by semantic predicate, relevant arguments,
scope and revision, followed by bounded closure. Measure actual rows visited,
search states and inference work with irrelevant-store growth. Perform authority
linking and static validation at activation; do not add repeated whole-bundle
checks to ordinary turns.

## 5. Weak points in the proposal itself

### Exactness needs a stated boundary

Separate at least four judgments:

1. Is the candidate graph well-formed, authorized and grounded in available
   evidence under the declared composition rules?
2. Does it preserve the speaker's intended meaning, or should alternatives
   remain unresolved?
3. Is its asserted content supported, opposed, unknown or conflicting in the
   relevant evidence store?
4. Is acting on it permitted and currently executable?

The first and much of the third/fourth can be checked exactly against a bounded
formal model. The second needs empirical linguistic evidence, context and
calibrated uncertainty. A unique candidate in an incomplete proposal space does
not prove that interpretation is uniquely correct.

Round-tripping output through the same parser proves internal consistency under
that parser. It is not an independent proof that a human reads the intended
meaning. A shared omission can pass both directions. A controlled compositional
output grammar plus independent semantic review gives a clearer bounded claim.

### Evaluation must follow these boundaries

The older operator/type-set/exact-program metrics are useful component
diagnostics, but they cannot establish usable meaning. Identical operator sets
can reverse participants, lose negation or ask a different question. Different
construction programs can express the same meaning. Likewise, a valid query
with an unknown answer should not be gold-labeled as unintelligible input.

Report separately: gold meaning expressibility; gold candidate recall; selected
meaning correctness; query/response correctness; safe mutation behavior;
clarification usefulness; realization fidelity; and measured resource use.
Comparison must preserve roles, scopes, binders and attribution while allowing
only explicitly defined semantic equivalences. Do not turn these into separate
approval workflows: one behavioral runner can report the distinct outcomes.

### Five operators are a kernel, not a completeness theorem

The full semantics also depend on role typing, identity, binding, quantification,
time, attribution, scope and graph links. Their interpretation must be explicit.
Do not add a sixth phrase-intent operator to hide a missing binder or query
projection. Conversely, do not claim universal meaning coverage merely because
an example can be encoded using five labels and opaque content.

Maintain three distinct identities: evidence occurrence, construction derivation,
and normalized semantic expression. Proof identity additionally depends on the
evidence/revision used. Syntactic normalization is not arbitrary logical
equivalence; document which equivalences canonicalization guarantees.

### Unknown meaning needs a lifecycle

An unknown token does not establish its ontological kind. `What` is a useful
linguistic cue, not proof that an unfamiliar expression cannot name a person.
The safe persistent object is initially an unresolved mention or inquiry,
bound to its evidence and context, not a fabricated `concept:zorbulate`.

Proposed lifecycle:

1. Preserve the literal, context, known grammatical relationships, alternative
   senses/kinds, requested information and unresolved obligations.
2. Check admitted designations and relevant dialogue memory.
3. Ask a targeted clarification when it will resolve the uncertainty.
4. Treat a user's explanation or research result as attributable candidate
   evidence; resolve which meaning it supports.
5. Apply the appropriate acquisition policy: an alias of an existing identity
   and creation of a genuinely new identity are different operations.
6. Commit only through the authorized learning owner, then reuse target
   affordances without form-pack regeneration.

Research is an evidence source within this lifecycle. A future bounded
Wikipedia/WordNet adapter should preserve source/sense identity, retrieval
version, confidence and conflicts. It must not import text as world truth or
create an atom because a search result exists. Query only the necessary term
and approved context; do not automatically send private conversation history.
An unresolved inquiry can remain tracked when research cannot settle it.

### Knowledge, learning and conversation require explicit commitments

Recognizing `mother` is different from possessing a useful definition of it.
Remembering that a speaker made a claim is different from believing the claim.
Understanding a fragment depends on a particular open discourse obligation,
not arbitrary neighboring text. Repeated clarification should depend on the
dialogue state and usefulness of the question, not a universal retry threshold.

For the MVP, make existing-identity designation learning complete before
expanding into autonomous acquisition of arbitrary concepts, frames and rules.
The current `r3_learning.py:310` known-target learning-draft materialization does
not demonstrate the full unknown-query/clarify/learn/reuse loop.

## 6. Why the work has kept returning to earlier milestones

The recurring pattern is now visible:

1. A source is mapped to a structurally legal graph or a broad abstention label.
2. Tests establish artifact shape and pipeline traversal, with inadequate
   independent checks of the requested meaning.
3. The result becomes gold, purpose allocation or a reviewed realization family.
4. Human review exposes a semantic error or unusable response.
5. Correcting the early owner changes content identities and invalidates
   downstream artifacts, receipts, tests and plans.
6. The next sequential example exposes another early-owner issue.

Content addressing correctly reveals changed dependencies. The expensive error
is freezing downstream semantics before the upstream behavior is established.

There is also considerable development surface: 82 Python source files contain
61,008 physical lines; 22 R4-related source files account for 20,738 of those
lines. The 6,101-line validation script is additional to that source count.
These include comments and blanks and are not a profiler result or a deletion
list. They indicate how much machinery can be affected by a small semantic
change. Governance should make evidence interpretable, not substitute for it.

The previous fixed closure set should remain historical evidence. Do not
silently change its authenticated assertions. Add explicit semantic successors
where the old assertion proves the wrong thing. Preserve adversarial authority,
ownership, scope and effect tests even when ordinary success tests are replaced.

## 7. Retain, rebuild and defer

There is working behavior to preserve. The fresh probes distinguish `Alice
likes Bob` from `Bob likes Alice` with correctly swapped subject/object roles.
`The server is offline` produces the expected state application, and the
online/offline conjunction reaches conflict handling with a clarification
response meaning and no effect receipt beyond `NoEffectReceipt`. None of these
produces an authorized surface in the current development activation. They
support retaining useful composition/cognition mechanisms, not a claim of
completed conversational competence.

| Area | Recommended treatment | Evidence needed before retention/completion claims |
|---|---|---|
| Semantic expressions, five operators, codecs and canonicalization | Retain and audit | Independent role/scope/binding contrasts and canonical-equivalence tests |
| Authority linking, typed refs, provenance and transactions | Retain | Existing adversarial gates plus the new loop's authority/mutation checks |
| Form/designation/affordance separation | Retain principle; repair projection/composition | Unseen synonym and inflection, second-language contrasts, no new lexical runtime branches |
| Query interpretation and answer projection | Rebuild earliest owners | Open queries request the right information; definitions contain actual content |
| Partial understanding and dialogue uncertainty | Complete as first-class semantics | Unknown spans and unresolved context produce truthful clarification without unsafe effects |
| Program search | Rework state representation/ranking | Meaning diversity within current bounds, honest truncation, no lost legal continuation |
| Retrieval and inference input selection | Replace whole-store materialization | Relevant indexed evidence and stable behavior as irrelevant data grows |
| Response realization | Establish diagnostic oracle, then learned owner | Readable meaning-equivalent output; no shared-parser-only correctness claim |
| Bulk corpus/review expansion, new UI work and broad research autonomy | Defer | Useful end-to-end loop and independently reviewed semantic gold |

Do not delete R4 modules or historical tests simply to reduce line counts. First
classify them as active authority, reusable mechanism, optional tooling or
retired evidence, and trace their consumers.

## 8. Concrete next work: one foundation proof

### Deliverable A: an executable semantic capability contract

Define expected meanings before asking the current runtime to generate them.
Keep this small: a handful of complete conversations plus contrast families,
not hundreds of recipe approvals. Each case needs real initial facts/context,
permissible interpretations, requested variables/projection, forbidden readings,
allowed mutations, expected response meaning and at least one human-readable
acceptable response.

Examples that expose the important distinctions:

| Case family | Required semantic distinction |
|---|---|
| What does "zorbulate" mean? / Where is Alice? | Unknown designation target versus unknown location fact |
| What is CEMM? / Who is CEMM? / Where is CEMM? | Identification/description candidates versus location; no universal identical graph |
| Define mother / Is Alice a mother? | Concept description versus instance type membership; no atom-kind substitution |
| Alice likes Bob / Bob likes Alice / Alice does not like Bob | Ordered roles and negation survive surface interpretation |
| You learn X / Learn X / Can you learn X? | Event claim, directive and capability question remain distinct |
| You said what? after a verified system turn | Query the correct speech event/content; fresh context asks for context |
| That you learn with and without an open antecedent | Explicit contextual completion versus an unresolved fragment |
| Known clause plus unknown span | Preserve understood structure without committing unresolved truth/effects |
| Conditional or attributed state/command | Preserve embedding; do not assert or execute embedded content unconditionally |

The permission test must specify an actual operation, target and requested value,
then remove its permission. An underspecified sentence such as `Set the state
without permission.` cannot independently prove a permission-denial owner.

One full learning conversation must start with a genuinely unrecognized
expression, ask about its meaning, receive an explicit explanation of an alias
for an existing reviewed identity, obtain the required learning authorization,
commit once, and reuse that alias in a new composition after restart. Add a
nearby case where the explanation would require a new identity and remains
pending under acquisition policy. Neither may default to `concept`.

These case families are semantic criteria, not phrase dispatch rules. Include
surface changes that preserve meaning and minimal changes that alter it.

### Deliverable B: a thin reference execution through existing owners

Run reviewed gold expressions through query, memory/admission, learning/effect
and response construction before involving a learned proposer. This isolates
whether CEMM can reason and respond correctly even when interpretation is
supplied correctly. Then run the same cases from surface evidence and locate
the earliest divergence.

The diagnostic renderer should be compositional over typed response meaning
and explicit designations, with unknown/conflict/permission status represented
in the response graph. It must not use source-phrase matching, ref-name
lexicalization, or generic UI text to cover missing semantic content.

This diagnostic mode is a proposed controlled design change. Existing admitted
R5/release paths remain unavailable until their own prerequisites are met.

### Deliverable C: repair the measured owner gaps, then a small learned pilot

Use the completed case matrix to expose all foundational blockers together.
Repair dependencies in semantic order: evidence and query representation;
partial/context semantics; cognition/retrieval; search; response realization.
Do not regenerate bulk gold after each isolated phrase repair.

Once the reference loop works, train a small proposal/realization pilot on
independently reviewed meanings and compare it with the reference and appropriate
weight ablations. Track candidate recall separately from verifier acceptance.
Evaluate unseen structures, combinations, aliases, contextual changes and a
second language; use several seeds where model selection depends on results.

Only then resume bulk R4 expansion and the admitted R5 pipeline under a single
updated dependency plan. A fully functioning semantic reference is not enough
to declare the hybrid research objective achieved: the learned pilot must add
the promised generalization and meet the agreed resource budget.

### Decision rules that prevent another open-ended replay

- If reviewed gold cannot produce the right query/response, the defect is in
  semantic cognition or its contract; do not change the language model.
- If the correct meaning cannot be expressed or enter proposal space, training
  cannot repair it; fix the earliest representation/evidence owner.
- If the meaning is representable and proposed but ranked poorly, investigate
  supervision, model capacity and calibration with a controlled experiment.
- If an isolated replacement cannot implement the agreed cases through existing
  canonical interfaces without a parallel semantic authority, use that concrete
  obstruction to reconsider the core and the scope of a larger rewrite.
- Complete one usable loop before expanding capability breadth. Report actual
  semantic outcomes, mutation safety and measured runtime work, not only counts
  of passed governance tests.

Do not add a validator per example. Prefer one parameterized behavioral runner,
existing adversarial gates and indexed runtime work counters. Authority, ABI and
artifact checks remain activation/release responsibilities where possible.

## 9. Options and recommendation

1. Continue the current narrow unresolved-designation patch. It can unblock one
   representation but leaves incorrect known answers, mode collapse, search
   duplication, missing surfaces and the R4/R5 dependency conflict unresolved.
2. Rebuild the entire repository. This gives organizational freedom but no
   answer to those semantic specification gaps. It risks recreating them while
   replacing working provenance and safety mechanisms.
3. Rebuild the foundation path described above, retain the audited exact core,
   and prove it with an independent semantic/response reference plus learned
   pilot. This is the recommended direction.

Before code resumes, incorporate the capability contract and corrected
dependency order into one governing amendment. Update the existing authority
router, AGENTS instructions and implementation status together; archive the
superseded closure sequence and narrow continuation as historical evidence.
Do not create another competing master plan or overwrite historical test hashes.

This audit deliberately does not perform that authority migration. Its useful
output is the evidenced scope of the required decision and a concrete proof
that can discriminate between an implementation failure and a flawed proposal.

## 10. Research cross-check

Constrained decoding is a credible component: PICARD demonstrates that
incremental parsing can reject invalid generated sequences and improve
text-to-SQL performance. The inference for CEMM is limited: this supports
constraining proposals, not treating formal validity as proof of intended
natural-language meaning. [PICARD, Scholak et al., 2021](https://aclanthology.org/2021.emnlp-main.779/).

COGS explicitly evaluates familiar words/structures in unfamiliar combinations;
its results show why ordinary held-out accuracy is insufficient to establish
compositional generalization. CEMM's evaluation needs that distinction.
[COGS, Kim and Linzen, 2020](https://aclanthology.org/2020.emnlp-main.731/).

ReCOGS demonstrates that incidental logical-form details can distort semantic
parsing evaluation, while removing representation machinery can also lose
meaning. This supports evaluating CEMM's intended semantic distinctions
independently of program ordering and incidental serialization, without
discarding roles or variable binding.
[ReCOGS, Wu et al., 2023](https://aclanthology.org/2023.tacl-1.96/).

These papers inform the recommendation; they do not validate CEMM's current
architecture or establish its eventual performance.

## Appendix: minimal reproduction of the highest-impact counterexamples

Run from either audited checkout's `hybrid_mvp` directory in PowerShell. This
creates fresh disposable stores and prints semantic results; it does not alter
authority, call external adapters, admit data, or activate a learned profile.

```powershell
$taskAuditPath = Join-Path $env:TEMP ('cemm-goal-audit-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $taskAuditPath | Out-Null
$env:CEMM_AUDIT_STORE = $taskAuditPath
@'
import json, os, sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / 'src'))
from cemm_authoritative_hybrid.bootstrap import load_runtime

cases = [
    'What is CEMM?', 'Where is CEMM?', 'Who is CEMM?',
    'What is a mother?', 'What is zorbulate?',
    'The server is offline. You said goodbye.',
    'The server is offline. Zorbulate.', 'Can you respond?',
]
for index, source in enumerate(cases):
    runtime = load_runtime(
        Path.cwd(), profile='development',
        store_path=Path(os.environ['CEMM_AUDIT_STORE']) / f'{index}.sqlite',
    )
    try:
        result = runtime.process(f'session:audit-{index}', source)
        meaning = result.verification.selected_meaning
        queries = result.evaluation.query_results if result.evaluation else ()
        print(json.dumps({
            'source': source,
            'verification': result.verification.status,
            'proposal_code': result.proposal.abstention_code,
            'truncated': result.proposal.truncated,
            'programs': len(result.proposal.candidates),
            'states': result.proposal.explored_states,
            'cycle': result.status.value,
            'expression': meaning.expression.as_dict() if meaning else None,
            'query_status': [query.status.value for query in queries],
            'proof_present': [query.proof is not None for query in queries],
            'surface_verified': result.realization_receipt is not None,
        }, default=str))
    finally:
        runtime.stores.close()
print(json.dumps({'temporary_stores': os.environ['CEMM_AUDIT_STORE']}))
'@ | python -
```

Confirmed in main: the three CEMM questions share ABI-1 expression
`expression:1e9c4e4891e84235d00938d2`. In the repair worktree they share ABI-2
expression `expression:dc1457da4879ec38bdce3a0e`. The ABI/ref change does not
change the erroneous atom-kind interpretation. The multiple-root example
exhausts 768 states with 48 proposed programs in both checkouts.
