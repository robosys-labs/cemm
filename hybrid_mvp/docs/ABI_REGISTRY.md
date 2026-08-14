# CEMM Hybrid ABI Registry

**Status:** active target contract under the 2026-08-02 Hybrid-only amendment
**Runtime cutover:** hard
**Scope:** `hybrid_mvp/` only; root adoption requires separate review

This registry distinguishes derivation ABIs from semantic-content ABIs. An ABI
version change invalidates every dependent scenario, episode, partition,
checkpoint, calibration, evaluation, activation and release artifact.

## 1. Active target registry

| ABI | Version | Canonical owner | Persistence | Validator / compiler | Activation gate |
|---|---:|---|---|---|---|
| Orientation ABI | 1 | `src/cemm_authoritative_hybrid/cycle.py` | Transient / episode-serializable | `OrientationProjector` / `Orientation.from_dict` | Complete-content `orientation_ref` covers every serialized semantic and lineage field with `RevisionPin` as sole revision owner; transient `cache_key` is omitted and cannot affect identity. |
| Evidence ABI | 1 | `src/cemm_authoritative_hybrid/forms.py` | Transient / episode-serializable | `FormResolver` | Exact reversible source geometry; one immutable evidence packet; no downstream retokenization authority. |
| Semantic Contribution ABI | 1 | `src/cemm_authoritative_hybrid/contributions.py` | Transient | `ContributionExpander` | Every source unit yields bounded typed contributions or one typed unresolved contribution. |
| Proposal Context ABI | 1 | `src/cemm_authoritative_hybrid/proposal_context.py` | Transient / episode-serializable | `ProposalContextBuilder` | Contains only current grounded designation/contribution/mode/application/reference/scope/link/variable/transition/residual slots, exact source spans and revision pin; builds bounded lookup indexes once. |
| Semantic Switch Program ABI | **2** | `src/cemm_authoritative_hybrid/programs.py` | Episode-serializable | `SemanticExpressionCompiler` and `ExactProgramVerifier` | Exactly one class owner; frozen per-action slot schemas; complete ordered full-content program hash including ABI, context ref, indexed actions, pointers, roots, assignments and revisions; no resolved expression and no sorted action identity. |
| Semantic Expression ABI | **1** | `src/cemm_authoritative_hybrid/expressions.py` | Episode/world/reference serializable as permitted | `SemanticExpressionCompiler` | Canonical recursive five-operator expression forest/root set with applications, scope operators, expression links, binders and typed unresolved fillers. |
| Compilation Proof ABI | **1** | `src/cemm_authoritative_hybrid/expressions.py` | Episode-serializable | `ExactProgramVerifier` | Binds program/context/expression/revision and proves every action, source assignment and declared root translated exactly once; proof rows are retained, not only hashed. |
| Source Coverage ABI | 2 | `src/cemm_authoritative_hybrid/coverage.py` | Episode-serializable | `CoverageVerifier` | Reconstructs context-owned criticality and validates exact source/contribution/action/role assignments, no missing/extra/duplicate units and typed residuals; coverage never manufactures expression structure. |
| Proposal Result ABI | 2 | `src/cemm_authoritative_hybrid/proposal.py` | Episode-serializable | candidate-batch validator | Content-addressed ranked envelopes preserve contiguous rank, fixed-point score, provenance, model/revision identity and exact context ref; truncation fails closed and abstention is explicit. |
| Verification Batch ABI | **2** | `src/cemm_authoritative_hybrid/verifier.py` | Episode-serializable | `ExactProgramVerifier` | One receipt per candidate; accepted receipts carry `expression_ref` and compilation proof; disposition is selected/ambiguous/rejected/abstained. |
| Verified Meaning ABI | **1** | `src/cemm_authoritative_hybrid/expressions.py` | Transient / episode-serializable | `VerifiedMeaningValidator` | Binds program lineage, canonical expression, grounding, coverage, compilation proof, verification receipt and revision pin. |
| Decision ABI | **1** | `src/cemm_authoritative_hybrid/decision.py` | Transient / episode-serializable | `DecisionEvaluator` | Consumes exactly one `VerifiedMeaning` plus one independently verified `SituationContext`; produces one typed `Decision` with query/proof/admission/transition/capability refs; never accepts a raw program. |
| Activation Canary Receipt ABI | **1** | `scripts/run_r3_canaries.py` + `scripts/validation_gate.py` | Serialized admission evidence | public `HybridRuntime` replay + admission verifier | Every row is freshly replayed and binds observed `semantic_mode`, cycle, VerifiedMeaning, SituationContext, Decision, effect/no-effect, ResponseMeaning, exact R5 gap and final RevisionPin; admission requires coverage of OBSERVE, QUERY, REQUEST and SIMULATE. |
| Diagnostic Semantic Episode ABI | **2** | `src/cemm_authoritative_hybrid/episodes.py` | Serialized diagnostic / future corpus source | `validate_episode` | Separates Program ABI 2 derivation lineage from `VerifiedMeaning`; binds the exact action-schema hash and rejects all Program-as-meaning Episode ABI 1 partitions. R1 records later artifacts as not admitted and cannot serve as R4 gold. |
| Situation Context ABI | 1 | `src/cemm_authoritative_hybrid/situation.py` | Transient / episode-serializable | `SituationContextValidator` | Independently binds force/mode, participants, temporal/source/epistemic and session context; never inferred from program identity. |
| Effect / No-Effect Receipt ABI | 1 | `src/cemm_authoritative_hybrid/r3_effects.py` | Serialized | `EffectGateway` | Exactly one receipt per cycle; all mutations/adapters bind decision and verified-meaning refs and are idempotent. |
| Gap Receipt ABI | 1 | `src/cemm_authoritative_hybrid/gaps.py` | Serialized | `GapClassifier` | Strict full-content identity covers every ordered semantic field; exact decoding rejects forged refs and oversized wire values before hashing. R1 stops after VERIFY with `LaterOwnerNotAdmitted(verified_meaning_ref, contract_ref)` and no surface or continuation. |
| Learning Plan ABI | 2 | `src/cemm_authoritative_hybrid/r3_learning.py` | Serialized | `LearningCoordinator` | Plans bind exact verified meaning, source query, target-kind contract, provenance, permission, revision and expiry; conversation cannot self-publish authority. |
| Response Meaning ABI | **2** | `src/cemm_authoritative_hybrid/r3_response.py` | Episode-serializable | `ResponseBuilder` | Constructed from decision, proof, blockers, effect/no-effect receipt and obligation; contains an exact semantic-expression contract. |
| Realization Receipt ABI | **2** | `src/cemm_authoritative_hybrid/realization.py` | Serialized | `RealizationVerifier` | Surface is reinterpreted through the same evidence/proposal/compile/verify contracts and compared by canonical semantic expression. |
| Phase Receipt ABI | 2 | `src/cemm_authoritative_hybrid/cycle.py` | Serialized when trace/evaluation enabled | `CycleFinalizer` | Each phase binds exact input/output refs, revisions, disposition, rejection codes and budget use. |
| Cycle Result ABI | **3** | `src/cemm_authoritative_hybrid/r3_cycle.py` | Serialized | `CycleFinalizer` | R3 active target: one canonical six-phase result carrying EvaluationBundle, exact Effect/No-Effect receipt and ResponseMeaning. `cycle.py` ABI 2 is admitted predecessor history only and cannot serialize an R3-complete cycle. |
| R5 Test Disposition ABI | **1** | `governance/r5_test_dispositions.json` | Reviewed governance input; generated receipt is evidence only | `schemas/r5_test_dispositions.schema.json`, `scripts/r5_test_dispositions.py`, `scripts/generate_r5_test_dispositions.py` | Requires an exact 17-successor/25-deferred/1-retired partition of the frozen R5 predecessor set. Deferral is not admission evidence, and `artifacts/validation/R5_TEST_DISPOSITIONS.json` is deterministic evidence rather than authority. |
| R5 Foundation Contract ABI | **1** | `configs/r5_foundation.json` | Reviewed phase-boundary configuration | `schemas/r5_foundation.schema.json` and `tests/test_r5_foundation.py` | Declares five exact foundation owners, red effective status, unavailable admission and four future data-access classes. It does not activate a neural model or materialize selection, calibration or frozen-test partitions. |

## 2. Canonical program identity

The Program ABI v2 hash includes the complete ordered payload:

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
propose_transition(transition_slot_ref, source_application_ref)
complete_program()
abstain()
```

Every action has one contiguous non-negative `action_index`. Local node refs are
derivation-local handles and never become grounded identities. The expression
link variant is licensed only by an exact context link slot that fixes link type,
arity and ordered/commutative behavior. Transition proposals are verified
lineage/decision hints and do not manufacture semantic applications.

Program ABI 2 never contains resolved applications, expression nodes or another
semantic graph. Those values exist only after exact compilation.

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

Program ABI v2 and Semantic Expression ABI v1 require regeneration of:

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
current R4 inputs. R4 Build Receipt ABI 3 remains historical evidence only and
is reconstructible from the invalidated source base; it has no current decoder
or admission authority. The newly registered contracts above do not claim that
four-class artifacts have been generated, admitted, or activated.

## R3–R4 implemented ABI allocation

| Query / Proof ABI | **1** | `src/cemm_authoritative_hybrid/r3_artifacts.py` | Episode-serializable | `ExpressionQueryOwner` | Expression-compiled query patterns, revision-pinned retrieval receipts and bounded proof DAGs; unknown is not false. |
| Authentic Semantic Episode ABI | **3** | `src/cemm_authoritative_hybrid/r4_episodes.py` | Serialized corpus candidate | `AuthenticEpisodeBuilder` | Keeps expected contract, observed public-runtime cycle and comparison receipt separate; no bootstrap output authors semantic gold. |
| Expected Cycle Contract ABI | **1** | `src/cemm_authoritative_hybrid/r4_contracts.py` | Serialized reviewed contract | `ExpectedCycleContractCompiler` | Total reviewed-assertion compilation with no PROPOSE/runtime dependency and no default-to-designation fallback. |
| Semantic Mutation ABI | **2** | `src/cemm_authoritative_hybrid/r4_mutations.py` | Serialized corpus candidate | `MutationExecutor` | One declared semantic/environment/persistence change; the authentic execution owner, not the generator, supplies the observed earliest-owner result. |
| Partition Axis Manifest ABI | **2** | Retired historical R4 artifact; no current decoder or admission authority after the corrective hard cut. |
| Training Allowlist ABI | **2** | Retired historical R4 artifact; no current training authorization after the corrective hard cut. |
| Partition Evidence ABI | **3** | Strict global leakage-hypergraph, component, source-set, and assignment contract; generation/admission pending. |
| R4 Split Manifest ABI | **1** | Exact four-class payload/member/component/label manifest; generation/admission pending. |
| R4 Partition Sufficiency ABI | **1** | Positive-denominator, four-class, per-dimension sufficiency receipt; generation/admission pending. |
| R4 Class Capability ABI | **1** | Purpose-bound single-class capability with no sibling-class disclosure; minting/admission pending. |
| R4 Class Authorization ABI | **1** | Independent admitted trust projection over one capability and the artifact graph; minting/admission pending. |
| Partition Config ABI | **1** | Reviewed integer objective, hard bounds, exact 60/15/15/10 weights, and acyclic feasibility basis. |
| R4 Build Receipt ABI | **4** | Corrective artifact-graph receipt; registered target; generation and activation remain pending. |

Corpus Review Manifest ABI 2, Approved R4 Build ABI 1, and R4 Build Receipt ABI 2 are retired. They have no active decoder, verifier, or compatibility path.
