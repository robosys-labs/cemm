# R4.1 Supervision Authoring Automation Design

**Status:** approved design; implementation and reviewed-data publication pending

**Scope:** complete the offline authoring path that converts the approved R4.1
source universe into exact proposal, designation, mutation and realization
supervision without allowing a Program, runtime result, external dataset or
language model to become semantic authority. This design amends the R4.1
source-readiness correction before main replay Tasks 4-7 resume.

This document governs only `hybrid_mvp/`. It does not admit R4, activate an R5
model, authorize a root-level adoption, or make any external source part of the
runtime.

## 1. Decision and proof boundary

The approved approach is an offline, bounded, evidence-assisted authoring
sidecar. It may reduce repetitive human work, but it may not manufacture gold.

The governing distinctions remain:

```text
SemanticExpression != SemanticSwitchProgram
reviewed source != generated recipe member
external evidence != CEMM authority
compiler success != human approval
runtime output != realization gold
normal expected effect != adversarial mutation truth
```

The exact `SemanticExpression` set and relation remain canonical meaning. A
generated Program is only a procedural witness. It becomes selectable only
when an independent compiler reconstructs the exact source-owned expression
and complete source assignments. No Program identity, action sequence or
runtime candidate may be substituted for meaning identity.

The authoring system proves bounded deterministic conformance to reviewed
source. It does not prove unrestricted natural-language generalization. R5
generalization claims require separately authored, frozen families that recipe
generation, training and selection cannot inspect.

## 2. Empirical baseline

The approved successor universe before the operation-environment correction
contains 408 cases:

| Classification | Count | Supervised |
|---|---:|---|
| semantic | 256 | yes |
| typed gap | 112 | yes |
| verifier rejection | 20 | yes |
| restart diagnostic | 20 | no |

The supervised denominator is therefore 388. Restart diagnostics remain
excluded from proposal, designation, mutation, realization and purpose
supervision.

Fresh source-only probes found:

- proposal authoring has 56 normalized families: 34 semantic, 21 typed-gap and
  one verifier-rejection family;
- designation authoring has 40 topology/kind families, 327 nonempty cases and
  61 exact-empty gap/rejection cases;
- every semantic case has at least one explicit authority-backed designation,
  with at most six matched spans per case, at most one target per span and 22
  intentional overlap cases;
- the six currently applicable adversarial mutation families expand to 1,932
  contracts over the 388 supervised cases;
- all 37 normal-effect cases join uniquely: 18 to reviewed adapter receipts and
  19 to reviewed state transitions;
- realization has a lower bound of 57 normalized families before output
  alignment patterns, while only eight cases have non-selectable surface
  suggestions and 380 have none; and
- all 36 bootstrap realization episodes use a predecessor representation and
  fail the current Realization Supervision ABI 1 schema.

These counts are evidence for feasibility, not constants in production code.
Every build derives eligibility and counts from the authenticated successor
source.

## 3. Architecture and one-way data flow

The authoring sidecar contains five focused components:

1. **Input snapshotter.** Authenticates the reviewed scenario universe,
   authority generation, form pack, configuration, compiler sources, purpose
   decisions and review policy. It produces one content-addressed input set.
2. **Evidence fetcher.** Downloads only approved revision-pinned external
   snapshots and records exact bytes, source revision, retrieval receipt,
   license and permitted use.
3. **Evidence normalizer.** Converts permitted evidence to bounded typed hints
   without minting CEMM refs, expressions, designations or surfaces.
4. **Recipe-family compiler.** Expands human-reviewed, purpose-scoped recipe
   families into concrete case-local candidate rows and explicit exceptions.
5. **Review-bundle publisher.** Runs independent reconstruction, emits exact
   review bytes and publishes only after explicit approval under the existing
   authenticated R4 review-bundle boundary.

The flow is strictly one way:

```text
reviewed CEMM source + pinned advisory evidence
  -> non-authoritative sidecar
  -> bounded recipe candidates and exceptions
  -> independent reconstruction
  -> explicit human review
  -> existing R4 publication and admission path
```

Recipes are worksheet-local authoring records. They never enter a runtime ABI,
activation index, model payload or admitted supervised case. Final bundles
contain only concrete existing supervision records and the repaired unpublished
Mutation Contract ABI 1 records.

No normal runtime import, network request, external service, new validation
tier, new activation phase, new pytest process or persistent recipe owner is
introduced.

## 4. External evidence policy

External data can help a reviewer find omissions or conflicts. It cannot
authorize meaning.

Initial staged sources are:

1. Open English WordNet for English lemma, sense and polysemy suggestions;
2. targeted, revision-pinned Wikidata Lexeme records only for foreign forms
   explicitly present in the reviewed English scenarios; and
3. CLDR only for locale, orthography and realization conventions.

UD, UniMorph, FrameNet and VerbNet remain deferred until a named reviewed gap
requires their specific morphology, syntax or frame evidence. Broad crawling
is forbidden.

Each external source remains a separate evidence family with its own hash,
revision, license, normalization receipt, abstention and conflicts. Correlated
agreement cannot promote a candidate. Unknown or incompatible license terms
make a source advisory-only and prohibit derived bytes from entering the
candidate or published bundle. A source with reviewed commercial-compatible
terms may produce bounded non-authoritative suggestions, but a human still
approves the exact CEMM-owned meaning, designation or surface independently.

Network retrieval is permitted only while creating the pinned evidence
snapshot. Candidate regeneration, review, publication and admission consume
only authenticated local snapshot bytes and perform no network access.

An LLM may summarize evidence, flag anomalies or prioritize review. It may not
emit selectable candidates, assign gold, resolve conflicts, mint identities,
change a content hash, approve a recipe or participate in deterministic
publication. Authoring and publication must succeed with all LLM access
disabled.

No source outside the explicit staged allowlist may appear in fetch
configuration, evidence manifests, hashes, normalizers, candidates, tests or
fallback paths.

## 5. Review-context identity

Every selectable child row requires a non-circular review identity. Define one
`source_review:<hash>` context solely from material available before any child
row, file, bundle or manifest identity is computed:

- review-policy ref and exact policy bytes;
- frozen reviewer identities and roles;
- reviewed base revision;
- authenticated authority generation;
- form/coverage ABI and form-pack hash;
- the literal review scope `r4_1_supervision_authoring`; and
- exact input-set ref.

The identity explicitly excludes worksheet refs, row refs, file hashes, bundle
refs and manifest refs. The existing authenticated loader independently
recomputes it and requires every child row and source file to name it exactly.

Draft rows remain inert under `draft_non_authoritative` even when they contain
the prospective review-context ref. Only explicit approval plus the approved
manifest makes the expanded bytes eligible for the existing publication path.

One accountable reviewer may approve recipe families and their expansions,
with risk escalation for exceptions and conflicts. That act does not replace
the separate second data-review checkpoint required later in main replay Task
4. Adding an escalation reviewer changes the frozen reviewer set and therefore
mints a new review-context and all dependent candidate identities.

Every generated suggestion uses one closed, non-authoritative candidate
envelope containing candidate kind, source case, purpose, recipe ref, exact
input/evidence refs, generator source identity, provenance, independent
verification receipt, selectability and explicit exception codes. Candidate
envelopes remain worksheet-only and are absent from the approved ABI payload.

## 6. Proposal authoring and independent derivation

Proposal recipes are keyed by complete canonical structure, not text:

- mode and outcome kind;
- expression relation;
- all five-operator application topology;
- predicate semantic kinds;
- ordered role/filler kinds;
- roots, binders, scopes and expression links;
- typed-gap kind and optional error shape; and
- verifier-rejection owner, disposition and error contract.

Concrete refs, literals, surface geometry, contribution pointers and
case-local action identities are recipe parameters. Exact derivation
blueprints are necessarily case-specific; anti-bloat therefore bounds
normalized recipe shapes and explicit exceptions, not `blueprint_ref` count.

Before a proposal candidate becomes selectable, a pure
`ReviewedDerivationCompiler` must:

1. independently rebuild the immutable `ProposalContext` once for the case;
2. resolve every grounded selector against pinned FormLattice, Grounding and
   exact character-span geometry;
3. validate every structural selector and action against the closed Program
   ABI;
4. reconstruct complete source assignments, consuming or retaining every
   observed unit exactly once;
5. compile the Program without calling the runtime proposer/composer; and
6. require exact equality with the source-owned expression set and relation.

The Program ref and expression ref remain distinct. Compilation failure,
incomplete assignment, critical residual, source mismatch or expression drift
creates a non-selectable exception for review. It never fabricates gold or
falls back to an opaque predicate.

These derivation requirements apply to semantic `derive` targets. A typed-gap
target contains the exact reviewed gap and no Program or expression. A
verifier-rejection target contains its exact reviewed adversarial payload,
expected VERIFY owner, disposition and error contract, but no accepted Program
or expression. Neither outcome may be passed through the semantic derivation
compiler merely to obtain a row.

The compiler core is brought forward from main replay Task 5 and reused there;
the worksheet builder may not implement a private duplicate.

## 7. Canonical designation authoring

The authority layer must retain one canonical explicit designation-fact
identity and expose an indexed lookup by normalized surface, language and
target. The identity is derived from the reviewed authority record, never from
case, unit, grounding attempt or runtime observation.

Candidate spans come only from the pinned FormLattice, Grounding and
ProposalContext geometry. Substring scans, regex-derived spans, token guessing
and invented designation refs are forbidden. Whole-unit boundaries and exact
Unicode slices are required. Overlapping spans such as `mother` within
`mother-in-law` remain explicit alternatives; no longest-match shortcut may
delete reviewed evidence.

The authoring bound is eight targets per exact span. Polysemy is preserved
until exact composition/settling. A missing open-class designation does not
default to `concept`, and internal ref spelling never becomes a surface.

The 61 reviewed gap/rejection cases with no explicit designation candidates
emit canonical exact-empty designation sets. An empty set is valid only when
independent case classification and geometry reconstruction prove that no
explicit authority designation applies.

## 8. Realization authoring and equivalence

Realization recipes use the approved neutral, concise canonical voice. A recipe
key contains the complete response meaning:

- response subject and expression relation;
- complete bindings and semantic slot extraction;
- required qualifiers;
- discourse action, polarity, modality and epistemic status;
- speaker/addressee perspective;
- language;
- explicit reviewed surface template; and
- designation, reference, literal, morphology and omission alignment rules.

The expected response-contract projection alone is not a valid recipe key.
Input text and runtime output are not realization gold. Existing eight surface
suggestions can seed review but carry no authority. The 36 predecessor
bootstrap episodes are forensic evidence only and cannot be migrated by a
permissive decoder.

A pure `ReviewedRealizationCompiler`, brought forward from main replay Task 6,
independently reconstructs the complete Response CSIR signature and verifies:

- subject and expression equality;
- bindings and every required semantic slot;
- action, polarity, modality and epistemic status;
- participant perspective and reference realization;
- output character spans and canonical designation-fact identities;
- independently authenticated literal sources;
- morphology and reviewed omissions; and
- one authorized, nonempty surface with exact provenance.

Every supervised semantic, typed-gap and verifier-rejection case receives one
initial concrete ABI-1 realization row. Diagnostic restart cases receive none.
Later reviewed bundles may contain at most four alternatives per case.
Compiler failure or missing authorized surface remains a non-selectable
exception; `""`, `None`, input echo and `[no authorized surface]` are forbidden.

Recipe-derived surfaces prove conformance only. Frozen-test realization
families are independently authored and hidden from training, selection,
prompt iteration and recipe derivation.

## 9. Normal effects and adversarial mutation truth

Normal expected effects remain owned by the source
`ExpectedCycleContract.expected_effect` and their exact reviewed receipts or
state transitions. The 37 currently observed normal-effect joins are verified
independently and are not serialized as Task 7 adversarial mutation contracts.

Mutation Contract ABI 1 is unpublished and receives an in-place repair before
any reviewed R4.1 package is published. Each concrete contract carries:

- source case and reviewed mutation-family refs;
- closed scope and changed dimension;
- a typed structural selector/path and closed mutation operation;
- exact expected-before and replacement-after values;
- family applicability evidence;
- expected earliest owner;
- exact expected status and error code;
- effect kind and optional exact effect ref; and
- review-context and source provenance refs.

Six currently active reviewed families replace Python-authored `_SPECS` truth:

| Family | Applicable successor cases before operation correction |
|---|---:|
| invalid role | 256 semantic |
| missing predicate | 256 semantic |
| dangling root | 256 semantic |
| untrusted source | 388 supervised |
| stale revision | 388 supervised |
| decision/action mismatch | 388 supervised |

This expands to 1,932 contracts before the operation-environment correction.
The number is not hard-coded.

The two previously dormant families, permission removal and adapter removal,
are required for R5 effect safety. Every reviewed `request_effect` source case
must explicitly name `adapter:state` in
`situation_constraints.adapter_refs` and `permission:set_state` in
`situation_constraints.permission_refs`. Both refs already belong to the
linked state-operation authority. The source expander then determines exact
applicability and the successor mutation count. The correction may enrich an
existing reviewed operation environment; it may not invent a permission or
adapter during mutation generation.

The repaired validator derives the complete applicable `(case, family)` set,
requires exactly one contract for every member and rejects missing, extra,
duplicate or inapplicable contracts. A pure mutation compiler reconstructs the
mutated bytes and expected observation independently. The executor receives
the mutation and reviewed environment but never its expected owner, status,
error or effect labels.

No `_SPECS`, executor branch or Python constant may continue to author expected
mutation truth after the hard cut.

## 10. Purpose isolation and leakage control

Purpose decisions occur before recipe approval. Recipe families are scoped to
exactly one of `train`, `selection`, `calibration` or `frozen_test`. A recipe,
paraphrase, translation, lexical substitution, mutation, contrast pair and
other descendant cannot cross purposes.

Recipe ancestry is recorded as explicit reviewed duplicate-risk lineage and
joined into the existing purpose/component validation. It does not create a
new global partitioner, semantic-union solver or pairwise scan. Existing
purpose contracts remain authoritative; recipe structure cannot silently
reassign a case.

Reports include row accuracy, family-macro accuracy and worst-family accuracy
as diagnostics. These metrics do not add a gate or replace exact case-level
admission.

Public deterministic families serve regression and conformance. Frozen-test
families remain reviewer-controlled, independently authored and unreadable by
training and selection consumers. R4 may claim bounded deterministic semantic
coverage only; R5 may make broader quality claims only after the sealed
holdout passes.

## 11. Bounds and performance contract

All work occurs offline under the existing review publication boundary.

- maximum source cases per authoring run: 512;
- maximum normalized recipe families per supervision kind per purpose: 128;
- maximum purpose-scoped recipe instances per supervision kind: 512;
- maximum designation targets per exact span: 8;
- maximum realization alternatives per case: 4;
- maximum mutation families per case: 8;
- maximum concrete mutation contracts: 4,096;
- maximum files per external evidence snapshot: 64;
- maximum bytes per external evidence snapshot: 16 MiB;
- maximum bytes per worksheet: 16 MiB;
- ProposalContext is built once per case;
- designation, case, recipe, purpose and family joins use prebuilt indexes;
- validation uses linear passes over rows and declared memberships; and
- pairwise whole-corpus comparison, runtime scans and network access are
  forbidden.

The 128-family-per-purpose ceiling replaces the unproven 64-family ceiling.
Proposal already requires 56 universe-wide structural families and realization
requires at least 57 before alignment patterns. Each recipe identity belongs
to one purpose. Related descendants remain in that purpose; an independently
authored family in another purpose may share a structural signature but shares
no recipe identity or ancestry. A purpose/kind run exceeding 128 fails before
publication and requires a reviewed design amendment; it may not merge
families by dropping semantic keys.

These limits are enforced inside existing build/authentication owners with
operation counters. They introduce no normal-cycle cost and no additional
release gate.

## 12. Failure handling

The authoring path fails closed and produces no selectable output when:

- source, authority, form-pack, config, recipe or evidence bytes drift;
- external evidence lacks an exact revision, hash, license or permitted use;
- a recipe crosses purposes or collides after normalization;
- a selector span, source assignment or designation identity cannot be
  independently reconstructed;
- Program compilation diverges from the canonical expression;
- response realization loses or invents meaning;
- a literal authenticates itself from the input/output row;
- mutation applicability or family membership differs from reviewed truth;
- review-context identity is cyclic or inconsistent;
- a configured bound is exceeded; or
- two clean generations are not byte-identical.

Failed cases become explicit non-selectable exceptions tied to the exact input
set. There is no permissive fallback, inferred concept, opaque predicate,
surface echo, UI placeholder or reuse of an observed runtime result.

Publication uses the existing transactional staging, authentication, atomic
rename and rollback behavior. No partially generated or partially approved
bundle is visible to admission.

## 13. Verification and corruption matrix

Implementation begins with failing tests and adds coverage to existing R4
owner processes. At minimum, tests must reject:

- Program/expression identity conflation and exact compilation divergence;
- incomplete, duplicate or unresolvable source assignments;
- case-local blueprint geometry reused for another case;
- forged designation refs, substring spans, Unicode drift and lost overlap or
  polysemy;
- missing, extra or automatically invented open-class designations;
- response subject, binding, slot, qualifier, action, polarity, modality,
  epistemic status or perspective drift;
- missing, duplicated or unauthenticated realization alignments;
- input echo, empty surface and UI placeholder realization;
- recipe-family collisions or cross-purpose ancestry;
- missing, extra, duplicate or inapplicable mutation contracts;
- mutation executor access to expected truth;
- remaining `_SPECS` authority leakage;
- permission/adapter removal without source-owned prerequisites;
- review-ref cycles and forged review contexts;
- external-source or LLM authority promotion;
- nondeterministic bytes; and
- any bound exceeded before materialization.

Positive canaries cover all five operators, all four modes, all twelve switch
actions, nested propositions, linked expressions, multiple roots, references,
scopes, query variables, state transitions, typed gaps, verifier rejections,
foreign forms explicitly present in English scenarios, safe realization and
R5-relevant permission/adapter denial.

Independent verifier implementations may share canonical wire decoders and
hash primitives. They may not call the runtime proposer, composer, realizer,
mutation executor or candidate compiler they are verifying.

## 14. Ordered implementation boundary

The implementation plan must preserve this dependency order:

1. repair Mutation Contract ABI 1, schema and cross-source invariants;
2. define the non-circular review-context identity and loader reconstruction;
3. add canonical authority designation-fact identity and indexed lookup;
4. bring forward the pure derivation, realization and mutation compiler cores;
5. correct reviewed `request_effect` environments with explicit adapter and
   permission prerequisites and regenerate the successor inventory;
6. define purpose-scoped worksheet-local recipe records and exception rows;
7. generate proposal and designation candidates and independently verify them;
8. author and verify complete neutral realization recipes and concrete rows;
9. expand reviewed mutation families into exact applicable contracts;
10. generate twice, authenticate exact bytes and obtain recipe/expansion
    approval;
11. preserve main Task 4's separate second data review; and
12. resume the existing publication, admission and R5 handoff sequence.

Tasks 1-5 are prerequisites for mass candidate authoring. Candidate counts or
green unit tests before those repairs cannot satisfy SR5/SR6.

## 15. Expected outcome and limitations

If implemented as designed, R4.1 will have exact independently reconstructed
proposal, designation, realization and adversarial mutation supervision tied
to one authenticated reviewed source universe. It will remove Program-as-
meaning, runtime-as-gold and Python-as-mutation-oracle regressions before R5
consumes any target.

The expected performance outcome is bounded offline linear work with no added
normal runtime latency. The expected R5 outcome is a train-only authenticated
supervision surface with explicit operation prerequisites, while selection,
calibration and frozen-test families remain isolated.

The result still does not prove open-world language competence. Recipe-derived
rows can be easier than independently authored data, and related templates can
inflate evaluation when split across purposes. Consequently, frozen-test
families and later multilingual/unseen-synonym canaries remain mandatory.

Research supporting these limitations includes:

- Gill, Ravichander and Marasovic, *What Has Been Lost with Synthetic
  Evaluation?* (Findings of EMNLP 2025),
  <https://aclanthology.org/2025.findings-emnlp.526/>;
- Elangovan, He and Verspoor, *Memorization vs. Generalization: Quantifying
  Data Leakage in NLP Performance Evaluation* (EACL 2021),
  <https://aclanthology.org/2021.eacl-main.113/>; and
- Zheng et al., *Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena*,
  <https://arxiv.org/abs/2306.05685>.

## 16. Definition of done

This authoring correction is complete only when:

- code, schemas, ABI registry, reviewed source, deterministic generators,
  active architecture and tests agree;
- every supervised successor case has one exact proposal target, one exact
  designation set and one initial exact realization row;
- every applicable `(case, mutation-family)` pair has exactly one independently
  verified Mutation Contract and no inapplicable pair has one;
- Programs independently compile to source-owned meanings without sharing
  identity with them;
- every realization independently reconstructs the complete response meaning
  and an authorized nonempty surface;
- every normal effect resolves to its source-owned receipt or transition;
- every `request_effect` case has reviewed adapter and permission prerequisites;
- recipe ancestry cannot cross purposes and frozen-test recipes are
  independently authored;
- draft and approved review identities remain non-circular and exact;
- two clean generations are byte-identical and all bounds hold;
- the existing transactional publisher and independent admission path accept
  the exact approved bundle; and
- R5 remains red until its separately governed consumer replacement and
  activation requirements are satisfied.

No root adoption, neural training, model publication or runtime cutover is
authorized by completing this design.
