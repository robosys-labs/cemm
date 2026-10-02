# CEMM Hybrid ABI Registry

**Status:** active target registry under the Hybrid-only semantic-algebra and foundation-proof amendments; no admission claim
**Runtime cutover:** hard
**Scope:** `hybrid_mvp/` only; root adoption requires separate review

This registry distinguishes derivation ABIs from semantic-content ABIs. An ABI
version change invalidates every dependent scenario, episode, partition,
checkpoint, calibration, evaluation, activation and release artifact.
The [foundation amendment](superpowers/specs/2026-09-07-foundation-proof-corrective-amendment.md)
and [implementation plan](superpowers/plans/2026-09-07-foundation-proof-implementation-plan.md)
own current repair dependencies; the September 3 narrow Task 4 route is historical.

The canary row below records the current bounded R3 implementation, not a waiver
of the July 31 admission design's full-cycle evidence requirement. Public
interpretation, useful response behavior and later realization remain separate
unproved obligations. Historical R3 admission is not an end-to-end MVP proof.

## 1. Active target registry

| ABI | Version | Canonical owner | Persistence | Validator / compiler | Activation gate |
|---|---:|---|---|---|---|
| Orientation ABI | 1 | `src/cemm_authoritative_hybrid/cycle.py` | Transient / episode-serializable | `OrientationProjector` / `Orientation.from_dict` | Complete-content `orientation_ref` covers every serialized semantic and lineage field with `RevisionPin` as sole revision owner; transient `cache_key` is omitted and cannot affect identity. |
| Evidence ABI | 1 | `src/cemm_authoritative_hybrid/forms.py` | Transient / episode-serializable | `FormResolver` | Exact reversible source geometry; one immutable evidence packet; no downstream retokenization authority. |
| Semantic Contribution ABI | 1 | `src/cemm_authoritative_hybrid/contributions.py` | Transient | `ContributionExpander` | Every source unit yields bounded typed contributions or one typed unresolved contribution. |
| Proposal Context ABI | **3** | `src/cemm_authoritative_hybrid/proposal_context.py` | Transient / episode-serializable | `ProposalContextBuilder` | Independently reviewed unadmitted construction: mandatory query-projection slots, exact immutable records, closed transient ports, activated-match lineage and source geometry. Complete contribution evidence authenticates against the actual activated authority/configuration and cached affordance view. Public candidate rows and exact derivation are implemented; bare content questions retain equal description/definition readings, not a settled answer. ABI 2 rejects. |
| Semantic Switch Program ABI | **3** | `src/cemm_authoritative_hybrid/programs.py` | Episode-serializable | `SemanticExpressionCompiler` and `ExactProgramVerifier` | Independently reviewed unadmitted projection derivation. Retains twelve action families and the three-argument binder; adds the two-argument query-projection selector. Exactly one class owner and complete ordered content identity; no resolved expression or sorted action identity. ABI 2 rejects. |
| Semantic Expression ABI | **3** | `src/cemm_authoritative_hybrid/expressions.py` | Episode/world/reference serializable as permitted; query projection is transient request content, not a world fact | `SemanticExpressionCompiler` | Approved unadmitted October 1 migration target: canonical five-operator forest plus one nonpersistent QueryProjection leaf with explicit description/definition content and grounded target. Request-only forests need no dummy application; empty forests remain invalid. ABI 2 is a hard-cut predecessor. Compiler, independent VERIFY, source coverage, genuine query lineage and dependent artifact migration must agree before public projection activation or packaging. |
| Compilation Proof ABI | **1** | `src/cemm_authoritative_hybrid/expressions.py` | Episode-serializable | `ExactProgramVerifier` | Binds program/context/expression/revision and proves every action, source assignment and declared root translated exactly once; proof rows are retained, not only hashed. |
| Source Coverage ABI | **3** | `src/cemm_authoritative_hybrid/coverage.py` | Episode-serializable | `CoverageVerifier` | Independently reviewed unadmitted projection derivation. Reconstructs context-owned criticality and exact source/contribution/action assignments, including non-role projection ports; no missing/extra/duplicate units or manufactured expression structure. ABI 2 rejects. |
| Proposal Result ABI | 2 | `src/cemm_authoritative_hybrid/proposal.py` | Episode-serializable | candidate-batch validator | Content-addressed ranked envelopes preserve contiguous rank, fixed-point score, provenance, model/revision identity and exact context ref; truncation fails closed and abstention is explicit. |
| Verification Batch ABI | **2** | `src/cemm_authoritative_hybrid/verifier.py` | Episode-serializable | `ExactProgramVerifier` | One receipt per candidate; accepted receipts carry `expression_ref` and compilation proof; disposition is selected/ambiguous/rejected/abstained. |
| Verified Meaning ABI | **1** | `src/cemm_authoritative_hybrid/expressions.py` | Transient / episode-serializable | `VerifiedMeaningValidator` | Binds program lineage, canonical expression, grounding, coverage, compilation proof, verification receipt and revision pin. |
| Decision ABI | **2** | `src/cemm_authoritative_hybrid/decision.py` | Transient / episode-serializable, unadmitted extension | `DecisionEvaluator` | Hard-cut ABI 1. Adds identity-covered selection ref for a non-claim RESPOND consequence; no answer, query, claim, admission, transition, effect intent or learning authority. Actual source authentication is required at live sinks. Ordinary decisions retain their prior protections. Scoped communicative SPEC and QUALITY pass; C5/full regression and admission remain open. |
| Activation Canary Receipt ABI | **1** | `scripts/run_r3_canaries.py` + `scripts/validation_gate.py` | Serialized admission evidence | R3-owned post-VERIFY `R3Kernel.run` replay + admission verifier | Fixed independently supplied expressions bind observed `semantic_mode`, VerifiedMeaning, SituationContext, Decision, effect/no-effect, ResponseMeaning and final RevisionPin across OBSERVE, QUERY, REQUEST and SIMULATE. These canaries do not exercise public ORIENT/PROPOSE/VERIFY or R5 surface realization; the structural check separately checks the typed R5 handoff. |
| Diagnostic Semantic Episode ABI | **2** | `src/cemm_authoritative_hybrid/episodes.py` | Serialized diagnostic / future corpus source | `validate_episode` | Separates Program ABI 3 derivation lineage from `VerifiedMeaning`; binds the exact action-schema hash and rejects all Program-as-meaning Episode ABI 1 partitions. R1 records later artifacts as not admitted and cannot serve as R4 gold. |
| Situation Context ABI | **2** | `src/cemm_authoritative_hybrid/situation.py` | Transient / episode-serializable, unadmitted extension | `SituationContextValidator` / activated `CommunicativeOwner` | Hard-cut ABI 1. Retains optional exact Communicative Source 1; independently binds original evidence, force, local roles and actual orientation. A missing performed source cannot fall through to claim evaluation. Scoped communicative SPEC and QUALITY pass; C5/full regression and admission remain open. |
| Communicative Source ABI | **1** | `src/cemm_authoritative_hybrid/communicative.py` | Transient / episode-serializable, unadmitted | activated `CommunicativeOwner` | Bounded original evidence/context, selected construction/root and immutable original pin. Actual Program/receipt and cached activation owners authenticate geometry, complete primitive ownership, selected designation provenance, coverage and proof translation. Structural codec identity is not authorization. |
| Response Selection ABI | **1** | `src/cemm_authoritative_hybrid/communicative.py` | Transient / episode-serializable, unadmitted | activated `CommunicativeOwner` | Identity precedes containing artifacts. Exact source force/root, situation, policy, grant and participants derive one same-target outgoing event. Requires `cap:respond`; third-party recipient or missing grant yields non-claim NO_OP. No arbitrary graph replacement or normal-realization admission. |
| Effect / No-Effect Receipt ABI | 2 | `src/cemm_authoritative_hybrid/r3_effects.py` | Serialized | `EffectGateway` | Exactly one receipt per cycle; all mutations/adapters bind decision and verified-meaning refs and are idempotent. No-effect learning lineage uses `source_obligation_ref`; incompatible ABI 1 receipts fail activation rather than being silently migrated. |
| Gap Receipt ABI | 1 | `src/cemm_authoritative_hybrid/gaps.py` | Serialized | `GapClassifier` | Strict full-content identity covers every ordered semantic field; exact decoding rejects forged refs and oversized wire values before hashing. R1 stops after VERIFY with `LaterOwnerNotAdmitted(verified_meaning_ref, contract_ref)` and no surface or continuation. |
| Learning Plan ABI | 3 | `src/cemm_authoritative_hybrid/r3_learning.py` | Serialized | `LearningCoordinator` | Plans hash the required original generic `source_obligation_ref` alongside exact verified meaning, source query, target-kind contract, provenance, permission, revision and expiry; conversation cannot self-publish authority. |
| Generic Dialogue Obligation ABI | 1 | `src/cemm_authoritative_hybrid/dialogue.py` | Serialized | `DialogueObligation.from_dict` / `bind_learning_answer` | Sole continuation record owner; exact pending source query, session, answer contract and exclusive turn window. Learning materialization returns this record unchanged. |
| R3 Artifacts ABI | 2 | `src/cemm_authoritative_hybrid/r3_kernel.py` | Episode-serializable | `R3Artifacts.create` | Cross-links evaluation, situation, effect, response and revision pins; learning content binds the exact original generic obligation and current answer window. |
| Evaluation Bundle ABI | **3** | `src/cemm_authoritative_hybrid/r3_artifacts.py` | Episode-serializable, unadmitted extension | `R3EvaluationOwner` / exact live consequence sinks | Dedicated hard cut from 2 retains Response Selection 1 and its non-claim decision. Shared R3 artifacts and ProofGraph remain 2; QueryResult remains 3. Actual source authorization and persisted no-effect lineage are required independently of pure decoding. Scoped communicative SPEC and QUALITY pass; C5/full regression and admission remain open. |
| QueryResult ABI | **3** | `src/cemm_authoritative_hybrid/r3_artifacts.py` | Episode-serializable after exact integration | `QueryDecisionOwner` / `EvaluationBundle` | Independently reviewed unadmitted component. Hard-cut ABI 2; identity-covered proposition/projection kind and optional signed Description/Proof Bundle 2. Projection requires that exact bundle, no ordinary proof/bindings, request/pin correspondence and completeness-derived status. Deny-only information supports the request, not affirmative world truth. Shared artifacts and ProofGraph remain ABI 2. Candidate construction is reviewed; bare content ambiguity, useful public answers, signed realization and neural activation remain unresolved. |
| Description ABI | **2** | `src/cemm_authoritative_hybrid/descriptions.py` + `QueryDecisionOwner.describe` in `r3_cognition.py` | Transient / episode-serializable after public integration | strict `DescriptionRequest` / `DescriptionResult` codecs plus the bounded read-only query builder | Request-first component: derives expression/projection/content/target/situation refs and original pin from one exact pure query-projection expression and QUERY situation, with bounded answer depth and fact count. ABI 1 and caller-supplied source-query refs reject. One pinned indexed read authenticates normalized claims before target-focus filtering. Definition stays MISSING without reviewed content/policy. Genuine final query-result component is independently reviewed; signed Response Meaning 4 is independently reviewed; public dispatch, admission and realization remain pending. |
| Proof Bundle ABI | **2** | `src/cemm_authoritative_hybrid/proof_bundle.py` + `QueryDecisionOwner.describe_with_proof` in `r3_cognition.py` | Transient / episode-serializable after public integration | strict `ClaimEvidence` / `ProofBundle` codecs and existing pinned lineage reader | Request-first read-only component, not public dispatch or admission. Owns the exact request through DescriptionResult, answer/persistent-application correspondence and pin; no QueryResult back-reference or duplicated stored source-expression ref. ABI 1 rejects. Preserves signed, occurrence-local fact/source/decision/placement/ordered-proof/generation/revision/transaction evidence using existing limits and one indexed read. Structural decoding is not store authentication or affirmative truth. |
| Designation-learning authority source | 1 (manifest source extension) | `src/cemm_authoritative_hybrid/authority.py` + `data/authority/alias_learning.json` | Reviewed owner source, linked at activation | `DesignationLearningContract` / `AuthorityLinker` | Exact source-event, role, capability, permission, internal EFFECT lowering, goal, answer-contract and review-policy edges are validated and content-hashed. This is not a reviewer grant or runtime publication admission. |
| Reviewed semantic-frame authority source | 1 (manifest source extension) | `src/cemm_authoritative_hybrid/authority.py` + `data/authority/frames/semantic_affordances.json` | Reviewed owner source, linked at activation | `ReviewedSemanticFrame` / `AuthorityLinker` | Exact generation, target kind, contribution kinds, ports, role candidates and signature compatibility are validated once and included in content/compatibility identities. Affordances consume the linked index; invalid registered sources never fall back to kind defaults. |
| Reviewed communicative-control authority source | 1 (strict manifest source extension; unadmitted) | `src/cemm_authoritative_hybrid/authority.py` + `data/authority/frames/semantic_affordances.json` | Reviewed owner source, linked at activation | `CommunicativeControl` / `AuthorityLinker` | Active generation `authority-v1-2026-10-02-communicative-source`; generation-only wire cut preserves the independently reviewed October 1 frame/control contents. Exact event/frame, participant-compatible roles, `cap:respond` policy and immutable target index remain. Registered malformed/stale sources and predecessor stores reject; no repinning. Coupled source/selection SPEC and QUALITY pass; C5/full regression and admission remain open. |
| Response Meaning ABI | **5** | `src/cemm_authoritative_hybrid/r3_response.py` | Episode-serializable, unadmitted | `ResponseBuilder` / `R3Artifacts` / authenticated cycle terminal | Hard-cut ABI 4. Retains exact Response Selection 1 and only its authenticated outgoing derivation. Preserves the independently reviewed signed Proof Bundle 2 contract, neutral attributed projection answers, original proof/output pins, alias-free wire and detached 64-by-64 proof content. Ordinary substitution/negation and nested learning lineage remain exact; unsigned projection realization rejects. Scoped communicative SPEC and QUALITY pass; C5/full regression, useful public answers, signed realization and neural activation remain pending. |
| Realization Receipt ABI | **2** | `src/cemm_authoritative_hybrid/realization.py` | Serialized | `RealizationVerifier` | Surface is reinterpreted through the same evidence/proposal/compile/verify contracts and compared by canonical semantic expression. |
| Phase Receipt ABI | 2 | `src/cemm_authoritative_hybrid/cycle.py` | Serialized when trace/evaluation enabled | `CycleFinalizer` | Each phase binds exact input/output refs, revisions, disposition, rejection codes and budget use. |
| Cycle Result ABI | **4** | `src/cemm_authoritative_hybrid/r3_cycle.py` | Serialized | `CycleFinalizer` | R3 active target: canonical three-/six-phase results plus exactly one read-only ORIENT budget terminal carrying the input evidence, performance gap and unchanged revision pin without synthetic downstream artifacts. `cycle.py` ABI 2 is admitted predecessor history only; ABI 3 is a hard-cut predecessor and is not accepted by the active decoder. |
| R5 Test Disposition ABI | **1** | `governance/r5_test_dispositions.json` | Reviewed governance input; generated receipt is evidence only | `schemas/r5_test_dispositions.schema.json`, `scripts/r5_test_dispositions.py`, `scripts/generate_r5_test_dispositions.py` | Requires an exact 17-successor/25-deferred/1-retired partition of the frozen R5 predecessor set. Deferral is not admission evidence, and `artifacts/validation/R5_TEST_DISPOSITIONS.json` is deterministic evidence rather than authority. |
| R5 Foundation Contract ABI | **1** | `configs/r5_foundation.json` | Reviewed phase-boundary configuration | `schemas/r5_foundation.schema.json` and `tests/test_r5_foundation.py` | Declares five exact foundation owners, red effective status, unavailable admission and four future data-access classes. It does not activate a neural model or materialize selection, calibration or frozen-test partitions. |

Description/Proof Bundle ABI 2 replaces the retired ABI 1 UNKNOWN-QueryResult
seam with exact canonical request-first expression and situation linkage.
The bundle has no final-query back-reference, so genuine QueryResult ownership
follows evidence construction without an identity cycle under dedicated
QueryResult ABI 3. That unadmitted query/evaluation component has passed independent
specification and quality review. Signed Response Meaning ABI 4 has also passed
both reviews. Candidate construction and exact derivation also passed both
reviews; useful public answers and signed realization remain pending. Bare
content questions retain competing readings. These changes are not neural
activation or admission. `definition_refs` names retained claim
roots, and SUFFICIENT means focused neighbourhood reconstruction, not an
intensional definition. Definition requests remain MISSING without reviewed
definition content and sufficiency policy. Foundation amendment section 8 and
Task 7's existing checklist own the approved execution sequence. Semantic
Expression ABI 3 is not a public description/definition completion claim.
The existing builder authenticates all
bounded target postings before retaining reviewed, nonmetadata-focused claims;
irrelevant postings cannot supply answer graphs or conflicts, but corruption and
raw posting overflow remain rejecting or typed budget terminals.

Task 5 canonical-continuation migration uses the hard-cut versions above. The existing effect
journal request payload may retain the canonical EvaluationBundle for one exact
unknown QUERY; this is attributable query-content evidence, not truth or learning
authority. There is one generic dialogue-obligation owner, not an interchangeable
plan-derived second type. A LearningPlan hashes its exact source obligation ref;
R3Artifacts and ResponseMeaning retain that source record. NoEffectReceipt's
`source_obligation_ref` is paired with a learning plan, not populated by inventing
a plan for an initial unknown query.
Automatic generic continuation creation uses the existing UNKNOWN no-effect
journal transaction, with exact source-session reservation and obligation
snapshot revalidation. A source turn `n` expires exclusively at `n+5`; a live
record is not renewed and expired retirement/replacement is atomic. This is not
alias publication. Learning proposals retain canonical meaning, evaluation,
LearningPlan and original pending/source-query witnesses in the existing journal
request; they use the current `LEARNING_OBLIGATION_ONLY` no-effect receipt, not a
new artifact ABI or obligation record. Terminal retry is read-only; unfinished
recovery remains bound to the original answer reservation. The duplicate
plan-derived type is removed. Candidate out-of-band publication uses a distinct
request in the existing EFFECT journal and current EffectReceipt ABI 2; it adds
no semantic role, artifact ABI, table or phase. It requires independently
configured store-bound review authentication, preserves the historical meaning
and answer pins, and atomically completes the original obligation with one
designation fact and receipt without advancing a dialogue turn. Explicit alias
language and publication-key locators are review/proof metadata, not designation
roles or authority by themselves. The candidate shared admitted reader adds no
serialized ABI: its transient evidence keeps canonical designation identity,
actual world-fact identity and publication provenance distinct. It reconstructs
committed records inside indexed, revision-pinned read batches; expiry limits
publication time, not later reuse. This trusts gateway-owned committed storage,
not complete offline-database fabrication. Grounding and canonical designation
composition share one ORIENT read batch; lexical query uses the same reader at
its exact situation pin. Signed publication/restart composition has executable
integration proof; multiword teaching, fragment/response usability and final
foundation closure remain open. Ordinary runtime construction still has no
review verifier. No serialized ABI changes in this integration. Non-null
journal receipts must decode under the current receipt ABI on activation;
planned rows with no receipt retain their existing recovery semantics.

The linked-alias checkpoint used generation
`authority-v1-2026-09-08-linked-alias-contract`. Its four internal authority kinds
change the compatibility hash; no existing model is implicitly reactivated.
Existing-generation stores must not be reset or silently repinned. The reviewed
owner JSON is source data, not output of the historical monolith splitter. That
splitter now refuses nonempty authority output. Runtime contract consumption was
implemented at `e703d49`; candidate authenticated publication followed at
`4c574be`. These checkpoints do not complete foundation Task 5.
The September 8 frame-preservation repair additionally links the six existing
reviewed profiles under `authority-v1-2026-09-08-linked-frames`, changing generation,
content and compatibility identities. A new generation is required because the
existing store activation owner pins that label rather than the content hash.
Do not reset or silently repin an existing store or reactivate a model to bypass
these identity changes. Frame preservation was verified at `b3df099`; it is no
longer a blocker to the approved canonical-continuation artifact migration.
The canonical-continuation codec migration is now implemented as a candidate;
its verification checkpoint is tracked in the foundation plan. That migration
alone did not enable publication; the later authenticated transaction has its
own recorded evidence. Neither admits a replay phase or reactivates descendants.

## 2. Canonical program identity

The Program ABI v3 hash includes the complete ordered payload:

```text
abi_version
orientation_ref + proposal_context_ref
ordered actions {
    action_index
    action_ref
    action_type
    dynamic arguments and pointers
    source_unit_refs
}
root refs
mode / goals
source assignments and residuals
revision pin
```

The following are ABI violations:

- sorting actions before hashing;
- hashing structural action names while omitting dynamic targets;
- excluding roots, roles, assignments or revisions;
- treating a model-vocabulary/action-encoding hash as a program-instance hash.

`action_abi_hash` identifies the closed action types and exact slot schemas. It is
independent of a candidate's order and pointer values. `program_ref` identifies one
concrete derivation instance. They are different fields; `action_encoding_hash`
is retired by the Program ABI 2 hard cut.

### 2.1 Frozen action slot schemas

```text
select_context(context_slot_ref)
select_mode(mode_slot_ref)
select_designation(designation_slot_ref)
instantiate_operator(application_local_ref, application_frame_ref)
bind_role(application_local_ref, role_ref, contribution_slot_ref)
bind_reference(application_local_ref, role_ref, reference_slot_ref)
bind_nested_application("role", parent_application_ref, role_ref, child_node_ref)
bind_nested_application("link", link_local_ref, expression_link_slot_ref,
                        operand_node_ref, operand_node_ref, ...)
attach_scope(scope_local_ref, scope_slot_ref, operand_node_ref)
project_variable(binder_local_ref, variable_slot_ref, body_node_ref)
project_variable(projection_local_ref, query_projection_slot_ref)
propose_transition(transition_slot_ref, source_application_ref)
complete_program()
abstain()
```

Every action has one contiguous non-negative `action_index`. Local node refs are
derivation-local handles and never become grounded identities. The expression
link variant is licensed only by an exact context link slot that fixes link type,
arity and ordered/commutative behavior. Transition proposals are verified
lineage/decision hints and do not manufacture semantic applications.

Program ABI 3 never contains resolved applications, expression nodes or another
semantic graph. Those values exist only after exact compilation.
The two-argument projection variant constructs one nonpersistent request leaf,
not a sixth operator, binder body or world assertion. Its selected target and
content must independently rematch the activated schema and original evidence.
Generic content/copula rows retain equal description/definition readings;
available facts and target kinds do not choose between them.

## 3. Canonical semantic-expression identity

A `SemanticExpression` is a bounded forest with an explicit non-empty root-ref
set, not an implicit single-root tree. Ordered links preserve operand order;
only link types explicitly registered as commutative may canonicalize operands,
and graph canonicalization must prove an exact bijection over local IDs.

The expression hash is derived from semantic content after exact compilation.
It is independent of derivation ordering and may alpha-normalize only local
application/variable IDs.

It retains:

```text
persistent operator
predicate identity
role names and fillers
grounded refs and licensed literals
roots and expression links
scope/binder structure
polarity, modality, attribution and temporal distinctions
```

## 4. Required public types

Conceptual minimum:

```python
@dataclass(frozen=True)
class SemanticExpression:
    expression_ref: str
    applications: tuple[SemanticApplication, ...]
    root_refs: tuple[str, ...]
    scope_operators: tuple[ScopeOperator, ...]
    expression_links: tuple[ExpressionLink, ...]
    binders: tuple[VariableBinder, ...]
    unresolved_fillers: tuple[UnresolvedFiller, ...]
    query_projections: tuple[QueryProjection, ...]

@dataclass(frozen=True)
class VerifiedMeaning:
    verified_meaning_ref: str
    program_ref: str
    expression: SemanticExpression
    grounding_refs: tuple[str, ...]
    coverage_receipt_ref: str
    compilation_proof_ref: str
    verification_receipt_ref: str
    revision_pin: RevisionPin
```

`verified_meaning_ref` may include proof and derivation lineage. Semantic
comparison therefore uses `expression_ref` plus required verified situated
qualifiers, not `verified_meaning_ref` alone. Evidence geometry and coverage do
not enter expression identity unless attribution/source is itself meaning.

Names may change only through a reviewed registry update. The separation of
program, expression and verified meaning may not change.

## 5. Invalidation rule

The current repair uses Proposal Context ABI v3, Program/Coverage ABI v3 and
Semantic Expression ABI v3. Construction, exact derivation and the
request/query/evidence/response components are independently reviewed but
unadmitted. Task 7.2b is closed; enabled candidate rows retain unresolved
description/definition ambiguity. Public answer usability and realization are
not established by the ABI declaration or component review. Dependent artifacts require fresh
reviewed regeneration/admission; the foundation-proof route does not authorize
bulk R4.1 rebuilding, training or R5 activation. Invalidated descendants include:

```text
reviewed expected contracts
canonical derivation targets
episodes
hard negatives
partitions
proposal checkpoints
realizer checkpoints
calibration
evaluation
activation receipts
release bundles
```

No descendant generated under the duplicate/legacy program ABI may remain green.

The R5 disposition receipt is regenerated with
`python scripts/generate_r5_test_dispositions.py --output artifacts/validation/R5_TEST_DISPOSITIONS.json`,
authenticated with
`python scripts/generate_r5_test_dispositions.py --check artifacts/validation/R5_TEST_DISPOSITIONS.json`,
and exercised by
`python -m pytest tests/test_r5_legacy_hard_cut.py -q -p no:cacheprovider`.
The foundation contract and its strict schema are checked by
`python -m pytest tests/test_r5_foundation.py -q -p no:cacheprovider`. These
commands validate evidence and configuration; neither command constitutes R5
admission.

## 6. Forbidden compatibility

- no duplicate `SemanticSwitchProgram`;
- no `propositions.py` runtime owner;
- no result-shape adapter;
- no signature inspection;
- no implicit conversion from program to meaning;
- no semantic equality based on action sets, refs, markers or strings;
- no evaluator accepting a raw program;
- no old checkpoint loader translating Program ABI v1 at runtime.

## R4 partition corrective hard cut

Partition Axis Manifest ABI 2 and Training Allowlist ABI 2 are retired as
current R4 inputs and are deliberately absent from the active allocation table.
R4 Build Receipt ABI 3 is historical evidence only. It may be reconstructed
solely for the exact admitted historical source/receipt tuple through the
source-pinned validation policy; no current candidate may decode, submit, or
admit ABI 3 evidence. Build Receipt ABI 4 and its global semantic-union evidence
are also ineligible predecessor candidates under the approved R4.1 amendment.
No current R4 candidate is admissible until the ABI 5 target evidence set below
is implemented. The registered target contracts do not claim that replacement
artifacts have been committed, admitted or activated.

## R3 implemented, R4 predecessor and approved R4.1 target allocation

| ABI / required contract | Version | Canonical owner | Persistence | Validator / compiler | Admission | Activation gate |
|---|---:|---|---|---|---|---|
| Query / Proof ABI | **3 / 2** | `src/cemm_authoritative_hybrid/r3_artifacts.py` | Episode-serializable | `QueryDecisionOwner` in `r3_cognition.py` | QueryResult 3 independently reviewed unadmitted component; public projection and signed realization pending | Dedicated `QUERY_RESULT_ABI_VERSION = 3` splits result kind and signed projection evidence from unchanged ProofGraph/shared artifact ABI 2. Ordinary proposition proofs/bindings and exact lexical lookup remain; projection results require request-first bundle/pin/status correspondence. No second query engine, authority or enlarged bound. Unknown is not false; definition content/policy remain missing. |
| Description ABI | **2** | `src/cemm_authoritative_hybrid/descriptions.py` + `QueryDecisionOwner.describe` in `r3_cognition.py` | Transient candidate | strict canonical codecs plus bounded read-only normalized-claim reconstruction | request-first component implemented; final query independently reviewed, signed response independently reviewed; public dispatch, realization and R4 use pending | Exact source expression/projection/content/target and original QUERY situation/pin replace the retired QueryResult-bound request. Codec bounds, persistent `fact:` category, operator-aware focus and one pinned indexed authentication remain. A neighbourhood is not definition authority; definition stays MISSING without reviewed content/policy. No parallel definition plane or writer. |
| Proof Bundle ABI | **2** | `src/cemm_authoritative_hybrid/proof_bundle.py` + `QueryDecisionOwner.describe_with_proof` in `r3_cognition.py` | Transient candidate | exact bounded wire codecs plus existing indexed claim-lineage authentication | request-first component implemented; public routing/admission pending | Owns DescriptionResult and its request without final-query back-reference; source expression is derived, not duplicated in stored fields. Exact persistent-application correspondence, signed occurrence-local evidence and ordered proof sequences retain existing bounds and one read. Structural decoding is not authentication. Generic description reconstruction still rejects alias-publication lineage until its dedicated owner is linked. |
| Authentic Semantic Episode ABI | **3** | `src/cemm_authoritative_hybrid/r4_episodes.py` | Serialized corpus candidate | `AuthenticEpisodeBuilder` | implemented predecessor | Keeps expected contract, observed public-runtime cycle and comparison receipt separate; no bootstrap output authors semantic gold. |
| Expected Cycle Contract ABI | **2** | `src/cemm_authoritative_hybrid/r4_contracts.py` | Serialized reviewed contract | `ExpectedCycleContractCompiler` | implemented predecessor | Total reviewed-assertion compilation with no PROPOSE/runtime dependency and no default-to-designation fallback. |
| Semantic Mutation ABI | **2** | `src/cemm_authoritative_hybrid/r4_mutations.py` | Serialized corpus candidate | `MutationExecutor` | implemented predecessor | One declared semantic/environment/persistence change; the authentic execution owner, not the generator, supplies the observed earliest-owner result. |
| Partition Evidence ABI | **3** | `src/cemm_authoritative_hybrid/r4_partition_contracts.py` | Serialized predecessor candidate | `GlobalLeakagePartitioner` plus `verify_partition_assignment` | implemented predecessor; ineligible for R4.1 | The global semantic-identity union is rejected; this decoder remains forensic source evidence only. |
| R4 Split Manifest ABI | **1** | `src/cemm_authoritative_hybrid/r4_partition_contracts.py` | Serialized predecessor candidate | `R4SplitManifest.from_dict` plus R4 admission reconstruction | implemented predecessor; requires R4.1 replacement | Existing class payload binding is insufficient without meaningful class-local semantic denominators. |
| R4 Partition Sufficiency ABI | **1** | `src/cemm_authoritative_hybrid/r4_partition_contracts.py` | Serialized predecessor candidate | `R4PartitionSufficiencyReceipt.from_dict` plus `r4_sufficiency.py` | implemented predecessor; requires R4.1 replacement | Existing non-vacuity checks do not authorize solver-trimmed minima or semantically empty held-out classes. |
| R4 Class Capability ABI | **1** | `src/cemm_authoritative_hybrid/r4_partition_contracts.py` | Serialized single-class projection | `R4ClassCapability.from_json_bytes` and `r4_partition_access.py` | implemented predecessor | Purpose isolation remains required but cannot compensate for defective class membership. |
| R4 Class Authorization ABI | **1** | `src/cemm_authoritative_hybrid/r4_partition_contracts.py` | Serialized trust projection | `R4ClassAuthorization.from_json_bytes` and `r4_partition_access.py` | implemented predecessor | Artifact binding remains necessary but is not semantic admission. |
| Partition Config ABI | **1** | `src/cemm_authoritative_hybrid/r4_partition_config.py` | Reviewed predecessor configuration | `R4PartitionConfig.from_json_bytes` | implemented predecessor; ineligible for R4.1 | Solver-selected or trimmed minima cannot serve as reviewed configuration authority. |
| R4 Build Receipt ABI | **4** | `src/cemm_authoritative_hybrid/r4_pipeline.py` | Serialized predecessor artifact-graph root | `R4BuildReceipt.from_json_bytes` and `verify_r4_admission` | implemented predecessor; requires fresh R4.1 admission | Integrity reconstruction remains necessary, but the receipt cannot admit the rejected partition or supervision contracts. |
| R4 Review Manifest ABI | **1** | `src/cemm_authoritative_hybrid/r4_supervision.py` | Reviewed source root | strict decoder plus content-addressed source-bundle reconstruction | strict decoder and authenticated loader implemented; checked-in reviewed data, publication and admission pending | Binds the reviewed base, exact source files, hashes, counts, reviewer identity and source-bundle identity without self-referential commit identity. |
| Proposal Supervision ABI | **1** | `src/cemm_authoritative_hybrid/r4_supervision.py` | Reviewed semantic gold | `ReviewedDerivationCompiler` plus exact-expression validator | strict decoder implemented; source compiler, checked-in reviewed data, publication and admission pending | Gold derivations compile independently of bootstrap selection, runtime proposal output and predecessor subset/intersection expectations. |
| Realization Supervision ABI | **1** | `src/cemm_authoritative_hybrid/r4_supervision.py` | Reviewed response gold | `ReviewedRealizationCompiler` plus semantic round-trip validator | strict decoder implemented; source compiler, checked-in reviewed data, publication and admission pending | ResponseMeaning-to-surface targets preserve slots, perspective and literal-copy alignment; input utterances never author response targets. |
| Mutation Contract ABI | **1** | `src/cemm_authoritative_hybrid/r4_supervision.py` | Reviewed mutation truth | strict decoder plus independent mutation-contract compiler | strict decoder implemented; source compiler, checked-in reviewed data, publication and admission pending | Expected earliest owner, effect class and admissible observation are reviewer-authored, not derived from the mutation executor under test. |
| Purpose Contract ABI | **1** | `src/cemm_authoritative_hybrid/r4_purpose.py` | Reviewed purpose and sufficiency policy | strict decoder plus purpose-membership validator | strict decoder implemented; source compiler, checked-in reviewed data, publication and admission pending | Declares source-case classification, supervised-universe membership, purpose, split eligibility and untrimmed class-local minima. |
| R4 Supervised Case ABI | **1** | `src/cemm_authoritative_hybrid/r4_supervision.py` | Compact compiled candidate | strict decoder plus source-to-case reconstruction | approved R4.1 target; implementation pending | Inlines complete canonical expression gold and expected contract while keeping observed cycles diagnostic and non-authoritative. |
| Duplicate-Risk Evidence ABI | **1** | `src/cemm_authoritative_hybrid/r4_purpose.py` | Deterministic candidate evidence | transitive reviewed-group reconstruction | approved R4.1 target; implementation pending | Reviewed overlap membership forms transitive components; every component stays in one purpose and split. |
| Class-local Sufficiency ABI | **1** | `src/cemm_authoritative_hybrid/r4_purpose.py` | Deterministic admission evidence | exact denominator reconstruction plus reviewed-minima validator | approved R4.1 target; implementation pending | Every admitted purpose class proves its own semantic denominators with no solver selection, trimming or feasibility downgrade. |
| R4 Split Manifest ABI | **2** | `src/cemm_authoritative_hybrid/r4_partition_contracts.py` | Serialized candidate partition | strict decoder plus deterministic purpose/split reconstruction | approved R4.1 target; implementation pending | Splits are exhaustive over the supervised universe; diagnostic-only source cases remain outside training/evaluation payloads. |
| R4 Class Capability ABI | **2** | `src/cemm_authoritative_hybrid/r4_partition_contracts.py` | Serialized single-class projection | strict decoder plus `r4_partition_access.py` | approved R4.1 target; implementation pending | Grants access only to one admitted purpose-class payload and its exact evidence identities. |
| R4 Class Authorization ABI | **2** | `src/cemm_authoritative_hybrid/r4_partition_contracts.py` | Serialized candidate-time trust projection | strict decoder plus artifact-graph reconstruction | approved R4.1 target; implementation pending | Binds the candidate graph without an admission reference; the later repository admission receipt authenticates this exact ref and SHA after admission succeeds. |
| R4 Build Receipt ABI | **5** | `src/cemm_authoritative_hybrid/r4_pipeline.py` | Serialized artifact-graph root | `verify_r4_admission` plus full source and evidence reconstruction | approved R4.1 target; implementation pending | The only current-admission target; binds review, supervision, purpose, partition, sufficiency, capability and authorization evidence after independent validation. |

Corpus Review Manifest ABI 2, Approved R4 Build ABI 1, R4 Build Receipt
ABI 2, Partition Axis Manifest ABI 2, and Training Allowlist ABI 2 are retired.
They have no active candidate decoder, verifier, authorization role, or
compatibility path. Source-pinned ABI 3 and ABI 4 reconstruction is bounded to
historical or predecessor evidence and cannot authorize current artifacts or R5.
