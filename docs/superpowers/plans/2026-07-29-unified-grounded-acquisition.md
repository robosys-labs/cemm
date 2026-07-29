# Unified Grounded Acquisition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make one typed, evidence-grounded acquisition path turn reviewed language, demonstrations, and corpus annotations into candidate atomic semantic graphs that can be validated, reviewed, published, retrieved, and recursively reasoned over without introducing a second semantic brain.

**Architecture:** A learned proposer consumes only pre-core evidence and existing grounded targets, then emits bounded pointer-based graph proposals. The existing contribution ABI, composition chart, exact compiler, coverage verifier, epistemic policy, and `publish_definition_graph` remain the only settling and authority owners. Durable learning evidence uses existing observations, applications, bindings, rule candidates, and commit receipts; neural scores are never world truth.

**Tech Stack:** Python 3.13, PyTorch, SQLite, JSON/JSONL reviewed corpora, existing five-operator ABI, pytest, FastAPI web demo.

---

## Scope and non-negotiable invariants

- Preserve exactly `op:designation`, `op:type`, `op:relation`, `op:state`, and `op:event`.
- A model may propose only target pointers, contribution alternatives, application topology, variables, and scores. It cannot mint atoms, select unreviewed authority, write facts, or execute an operation.
- All accepted graphs must pass `ExactStructuredCompiler`, Coverage ABI 7, frame/port validation, authority-generation checks, and Stage-13 receipt validation.
- Composite definitions are published only through `Store.publish_definition_graph`; rule rows remain deterministic execution projections carrying `definition_ref`.
- Unknown text remains an evidence/frontier artifact. No raw-corpus path defaults a token to `concept`.
- Keep normal-turn bounds explicit. Large-corpus ingestion is offline/batched; online reasoning must use indexed joins rather than broad fact-first expansion.

## File map

- Create: `cemm/acquisition_proposals.py` — immutable proposal, alignment, evidence, and review-decision artifacts.
- Create: `cemm/semantic_parser.py` — bounded learned pointer proposer and deterministic feature encoder; contains no store writes.
- Create: `cemm/corpus_ingestion.py` — JSONL episode loader, structural validation, and offline proposal replay.
- Create: `tests/test_acquisition_proposals.py` — proposal validation, rejection, and publication lineage tests.
- Create: `tests/test_semantic_parser.py` — parser N-best/pointer bounds and no-authority-write tests.
- Create: `tests/test_corpus_ingestion.py` — deterministic corpus validation and held-out family tests.
- Modify: `cemm/cognition.py` — add typed proposal references to cycle artifacts without adding an operator.
- Modify: `cemm/interpreter.py` — merge parser proposals with chart candidates before exact settling.
- Modify: `cemm/rules.py` — replace direct codec-to-rule promotion with graph-proposal review staging.
- Modify: `cemm/runtime.py` — own proposal evidence, reviewer-only publication, and Stage-13 receipts.
- Modify: `cemm/store.py` — retrieve reviewed definition records by identity independent of source; index/select rules by constrained joins.
- Modify: `cemm/retrieval.py` — cost/order rule antecedent retrieval and preserve required definition chains under configured bounds.
- Modify: `cemm/inference.py` — execute ordered joins with per-join bounds and expose incompleteness precisely.
- Modify: `cemm/trainer.py` — compile ABI-7 semantic episodes into pointer-supervision and family-disjoint splits; remove legacy codec targets.
- Modify: `cemm/web_demo.py`, `cemm/web/index.html` — add proposal inspection and explicit approve/reject actions; never auto-publish.
- Modify: `DATA_ARCHITECTURE.md`, `RUNTIME_ARCHITECTURE.md`, `runtime-core-loop.md`, `V1_ACCEPTANCE.md` — document actual ABI, acquisition ownership, and executable gates.

### Task 1: Define the proposal ABI before any model integration

**Files:**
- Create: `cemm/acquisition_proposals.py`
- Test: `tests/test_acquisition_proposals.py`

- [ ] **Step 1: Write failing proposal validation tests**

```python
def test_definition_proposal_requires_only_five_operator_applications():
    proposal = DefinitionProposal.create(
        evidence_ref="evidence:test",
        target_ref="rel:mother_in_law",
        antecedent=[{"operator": "op:relation", "args": {}}],
        consequent=[{"operator": "op:invent", "args": {}}],
        alignments=(),
        score=0.9,
    )
    with pytest.raises(ValueError, match="five-operator"):
        proposal.validate(store)
```

- [ ] **Step 2: Run the new test and verify it fails because `DefinitionProposal` is absent**

Run: `python -m pytest tests/test_acquisition_proposals.py -q`

Expected: import failure naming `DefinitionProposal`.

- [ ] **Step 3: Implement immutable proposal and alignment records**

```python
@dataclass(frozen=True)
class GraphAlignment:
    unit_ref: str
    application_ref: str
    role_ref: str

@dataclass(frozen=True)
class DefinitionProposal:
    proposal_ref: str
    evidence_ref: str
    target_ref: str
    antecedent: tuple[dict[str, Any], ...]
    consequent: tuple[dict[str, Any], ...]
    alignments: tuple[GraphAlignment, ...]
    score: float
    authority_generation: int

    def validate(self, store: Store) -> None:
        if any(app["operator"] not in FIVE_OPERATORS for app in self.applications):
            raise ValueError("proposal contains a non-five-operator application")
        store.validate_rule({"rule_kind": "definition", "if": list(self.antecedent), "then": list(self.consequent)})
```

`validate()` must also require an existing reviewed target, bounded application count, exact span/application-role alignments, and a generation equal to the proposal pin.

- [ ] **Step 4: Run focused tests**

Run: `python -m pytest tests/test_acquisition_proposals.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add cemm/acquisition_proposals.py tests/test_acquisition_proposals.py
git commit -m "feat: define grounded acquisition proposals"
```

### Task 2: Make parser output a bounded proposal, not a rule or authority write

**Files:**
- Create: `cemm/semantic_parser.py`
- Modify: `cemm/interpreter.py`
- Test: `tests/test_semantic_parser.py`

- [ ] **Step 1: Write failing N-best and no-write tests**

```python
def test_parser_returns_bounded_pointer_graph_proposals_without_mutating_store(runtime):
    before = runtime.s.revisions()
    proposals = runtime.semantic_parser.propose(
        runtime.i.observe("A mother in-law is the mother of a partner.", frame),
        authority_generation=runtime.s.generation,
    )
    assert 0 < len(proposals) <= runtime.config.form_max_semantic_candidates
    assert runtime.s.revisions() == before
    assert all(proposal.target_ref == "rel:mother_in_law" for proposal in proposals)
```

- [ ] **Step 2: Run the test and verify it fails because the parser is absent**

Run: `python -m pytest tests/test_semantic_parser.py::test_parser_returns_bounded_pointer_graph_proposals_without_mutating_store -q`

Expected: attribute error for `semantic_parser`.

- [ ] **Step 3: Implement a pointer-only parser interface**

```python
class SemanticGraphProposer:
    def propose(self, lattice: EvidenceLattice, *, authority_generation: int) -> tuple[GraphProposal, ...]:
        encoded = self.encoder.encode(lattice)
        raw = self.model.predict(encoded, top_k=self.max_candidates)
        return tuple(
            proposal for proposal in map(self.decoder.decode, raw)
            if proposal.authority_generation == authority_generation
        )
```

The decoder may choose only: grounded atom pointers, reviewed frame pointers, `?` variables, `!` existentials, and candidate-local entity/event tokens. Reject logits selecting unknown atom IDs before proposals reach the interpreter.

- [ ] **Step 4: Merge proposals before settling**

In `Interpreter.compose`, append only proposals that independently pass proposal validation and coverage reconstruction to the chart candidates. Preserve provenance as `source="learned_graph_proposal"`; never increase a proposal score beyond the chart/settler score bounds.

- [ ] **Step 5: Run parser and interpreter tests**

Run: `python -m pytest tests/test_semantic_parser.py tests/test_native_semantic_spine.py -q`

Expected: PASS with learned proposals rejected safely when malformed.

- [ ] **Step 6: Commit**

```bash
git add cemm/semantic_parser.py cemm/interpreter.py tests/test_semantic_parser.py
git commit -m "feat: route learned graph proposals through exact settling"
```

### Task 3: Replace the legacy direct neural rule-learning lane

**Files:**
- Modify: `cemm/rules.py`
- Modify: `cemm/runtime.py`
- Modify: `cemm/codec.py`
- Test: `tests/test_acquisition_proposals.py`

- [ ] **Step 1: Write a failing reviewed-teaching lineage test**

```python
def test_reviewed_teaching_publishes_definition_graph_not_unowned_rule(runtime):
    result = runtime.process("A mother in-law is the mother of a partner.", mode="reviewed_teach")
    assert result["proposal"]["status"] == "awaiting_review"
    accepted = runtime.approve_definition(result["proposal"]["proposal_ref"])
    rule = runtime.s.relevant_rules(semantic_refs=("rel:mother_in_law",), consequent=False)[0]
    assert rule["definition_ref"] == accepted["definition_ref"]
```

- [ ] **Step 2: Run the test and verify it fails because reviewed teaching still writes `rule_candidates`**

Run: `python -m pytest tests/test_acquisition_proposals.py::test_reviewed_teaching_publishes_definition_graph_not_unowned_rule -q`

Expected: FAIL; current result is a `provisional_rule` or `promoted_rule`.

- [ ] **Step 3: Replace `RuleLearner.teach` with proposal staging**

Remove `StructuredSemanticCodec.predict_rules()` from the serving path. `reviewed_teach` must emit a `DefinitionProposal` observation and a typed review frontier. Add `Runtime.approve_definition(proposal_ref)` that reloads the exact evidence, validates the generation, and calls only `publish_definition_graph` inside the Stage-13 transaction.

- [ ] **Step 4: Preserve offline model training only**

Keep neural code only behind `SemanticGraphProposer` training/inference interfaces. Remove the `Interpreter.codec` compatibility property after callers migrate; add an activation validator rejecting direct `StructuredSemanticCodec` use in runtime and rule-learning modules.

- [ ] **Step 5: Run focused acquisition tests**

Run: `python -m pytest tests/test_acquisition_proposals.py tests/test_native_semantic_spine.py -q`

Expected: PASS; every learned executable definition has a `definition_ref`.

- [ ] **Step 6: Commit**

```bash
git add cemm/rules.py cemm/runtime.py cemm/codec.py tests/test_acquisition_proposals.py
git commit -m "refactor: unify reviewed teaching with definition authority"
```

### Task 4: Add corpus episodes and train/holdout discipline

**Files:**
- Create: `cemm/corpus_ingestion.py`
- Modify: `cemm/trainer.py`
- Modify: `cemm/curriculum.py`
- Test: `tests/test_corpus_ingestion.py`

- [ ] **Step 1: Write failing corpus-contract tests**

```python
def test_episode_requires_grounded_target_and_family_disjoint_holdout(tmp_path):
    path = tmp_path / "episodes.jsonl"
    path.write_text(json.dumps({"surface": "glorp", "target_ref": "missing:atom"}) + "\n")
    with pytest.raises(ValueError, match="reviewed authority"):
        load_semantic_episodes(path, store)
```

- [ ] **Step 2: Run the test and verify it fails because the loader is absent**

Run: `python -m pytest tests/test_corpus_ingestion.py -q`

Expected: import failure for `load_semantic_episodes`.

- [ ] **Step 3: Define JSONL episode shape and deterministic split**

Each record must contain `episode_ref`, source evidence, language, reviewed mention alignments, expected five-operator graph, construction family, authority generation/hash, optional definition target, and outcome class. Reject records with unknown refs or a train/holdout construction-family overlap.

- [ ] **Step 4: Compile only pointer supervision**

Change `trainer.py` to emit target-pointer vocabularies scoped to the authority snapshot and graph topology/role targets. Do not emit a text-to-fact target or an untyped rule target. Train parser heads for contribution kind, target pointer, role binding, app links, and abstention/frontier.

- [ ] **Step 5: Run corpus tests**

Run: `python -m pytest tests/test_corpus_ingestion.py tests/test_native_semantic_spine.py -q`

Expected: PASS with deterministic byte-identical manifests.

- [ ] **Step 6: Commit**

```bash
git add cemm/corpus_ingestion.py cemm/trainer.py cemm/curriculum.py tests/test_corpus_ingestion.py
git commit -m "feat: add grounded semantic episode ingestion"
```

### Task 5: Repair recursive retrieval before increasing knowledge volume

**Files:**
- Modify: `cemm/retrieval.py`
- Modify: `cemm/inference.py`
- Modify: `cemm/store.py`
- Test: `tests/test_native_semantic_spine.py`

- [ ] **Step 1: Write the failing no-shortcut recursion test**

```python
def test_definition_chain_survives_retrieval_without_direct_married_consequent(runtime):
    publish_mother_in_law_decomposition(runtime.s)
    runtime.process("My mother in-law arrived today.")
    answer = runtime.process("Am I married?", mode="read_only")
    assert answer["query_result"]["status"] == "supported"
    assert answer["retrieval"]["truncated"] is False
```

- [ ] **Step 2: Run the test and verify the current fact-budget truncation**

Run: `python -m pytest tests/test_native_semantic_spine.py::test_definition_chain_survives_retrieval_without_direct_married_consequent -q`

Expected: FAIL with `retrieval.trace.truncation_reason == "fact_budget"`.

- [ ] **Step 3: Implement constrained backward rule expansion**

Start from the query’s fully bound role signatures. Rank consequent rules by matching bound roles, then expand an antecedent one clause at a time, choosing the clause with the most bound/indexed roles. Query each clause with the current variable environment rather than fetching every fact matching an unbound relation. Preserve all limits and return an explicit `join_budget` frontier if exhausted.

- [ ] **Step 4: Add exact join execution**

Expose `Store.matching_facts_for_clause(clause, environment, limit)` and use it in `Inference._matches`; retain exact rechecking and proof parents. Do not broaden through salience or whole-store scans.

- [ ] **Step 5: Run retrieval, inference, and full test suites**

Run: `python -m pytest tests/test_native_semantic_spine.py tests/test_atomic_graph_stress.py -q`

Expected: PASS; the proof includes the reviewed definition reference and no direct marital shortcut.

- [ ] **Step 6: Commit**

```bash
git add cemm/retrieval.py cemm/inference.py cemm/store.py tests/test_native_semantic_spine.py
git commit -m "fix: retrieve recursive definition chains by constrained joins"
```

### Task 6: Make frame semantics, state, and operational transition algebra compositional

**Files:**
- Modify: `cemm/semantic_contributions.py`
- Modify: `cemm/composition.py`
- Modify: `cemm/state.py`
- Modify: `cemm/transitions.py`
- Test: `tests/test_semantic_parser.py`

- [ ] **Step 1: Write a failing frame-orientation test**

```python
def test_possessive_relation_orientation_is_selected_from_reviewed_frame(runtime):
    result = runtime.process("My kinbridge arrived today.", mode="read_only")
    relation = next(app for app in result["packet"]["apps"] if app["operator"] == "op:relation")
    assert relation["args"]["role:object"] == "participant:user"
    assert result["packet"]["qualifiers"]["semantic_frame_ref"] == "frame:possessive-relation-object"
```

- [ ] **Step 2: Run test and verify it fails because orientation is currently hard-coded in composition**

Run: `python -m pytest tests/test_semantic_parser.py::test_possessive_relation_orientation_is_selected_from_reviewed_frame -q`

Expected: FAIL; no reviewed possessive frame appears in the packet.

- [ ] **Step 3: Represent relation orientation and event-role reuse in frame metadata**

Replace `_possessive_relation_event_graphlets` role assumptions with a reviewed frame profile containing participant-facing relation role, introduced referent kind, compatible event role, and optional temporal role. Validate these fields at activation and use only the selected profile to construct graphlets.

- [ ] **Step 4: Extend transition previews only through reviewed causal frames**

Permit a reviewed causal frame to describe relation additions/retractions and event links alongside state deltas, each carrying explicit epistemic mode, role bindings, and proof. Do not commit previews or add a sixth operation.

- [ ] **Step 5: Run focused composition/state/transition tests**

Run: `python -m pytest tests/test_semantic_parser.py tests/test_atomic_graph_stress.py -q`

Expected: PASS; no surface or target-ref dispatch appears in production sources.

- [ ] **Step 6: Commit**

```bash
git add cemm/semantic_contributions.py cemm/composition.py cemm/state.py cemm/transitions.py tests/test_semantic_parser.py
git commit -m "feat: compose frames and transition effects from reviewed ports"
```

### Task 7: Add explicit human review to the web demo

**Files:**
- Modify: `cemm/web_demo.py`
- Modify: `cemm/web/index.html`
- Test: `tests/test_acquisition_proposals.py`

- [ ] **Step 1: Write failing API approval tests**

```python
def test_web_proposal_approval_requires_the_exact_generation(client):
    proposal = client.post("/api/teach", json={"text": "A kinbridge is a partner relation."}).json()
    rejected = client.post("/api/reload").json()
    approval = client.post(f"/api/proposals/{proposal['proposal_ref']}/approve").json()
    assert approval["status"] == "error"
    assert "generation" in approval["error"]
```

- [ ] **Step 2: Run test and verify endpoints are absent**

Run: `python -m pytest tests/test_acquisition_proposals.py::test_web_proposal_approval_requires_the_exact_generation -q`

Expected: FAIL with HTTP 404.

- [ ] **Step 3: Implement proposal-only web endpoints**

Add `POST /api/teach`, `GET /api/proposals/{proposal_ref}`, `POST /api/proposals/{proposal_ref}/approve`, and `POST /api/proposals/{proposal_ref}/reject`. Approval must invoke the same Stage-13 runtime API as non-web review; rejection writes only an attributed review decision/evidence record.

- [ ] **Step 4: Render graph/proof review rather than a free-text rule editor**

Show source spans, target pointers, applications, bindings, score, validation result, authority generation, and definition lineage. Disable approval when validation fails or the generation pin is stale.

- [ ] **Step 5: Run web and acquisition tests**

Run: `python -m pytest tests/test_acquisition_proposals.py tests/test_abi7_release_contract.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add cemm/web_demo.py cemm/web/index.html tests/test_acquisition_proposals.py
git commit -m "feat: add reviewed semantic proposal workflow to web demo"
```

### Task 8: Align contracts, release gates, and benchmark evidence

**Files:**
- Modify: `AGENTS.md`
- Modify: `ARCHITECTURE.md`
- Modify: `RUNTIME_ARCHITECTURE.md`
- Modify: `DATA_ARCHITECTURE.md`
- Modify: `runtime-core-loop.md`
- Modify: `CEMM_RUNTIME_IMPLEMENTATION_CONTRACT.md`
- Modify: `V1_ACCEPTANCE.md`
- Modify: `tools/check_v1_final_contract.py`
- Modify: `tools/validate_semantic_operational_contract.py`
- Test: `tests/test_abi7_release_contract.py`

- [ ] **Step 1: Write failing contract-consistency tests**

```python
def test_canonical_documents_and_release_gates_name_only_active_abis():
    canonical = [ROOT / name for name in ("AGENTS.md", "RUNTIME_ARCHITECTURE.md", "DATA_ARCHITECTURE.md", "runtime-core-loop.md", "CEMM_RUNTIME_IMPLEMENTATION_CONTRACT.md", "V1_ACCEPTANCE.md")]
    assert all("Form/Coverage ABI:** 6" not in path.read_text(encoding="utf-8") for path in canonical)
    assert run_final_contract_checker().returncode == 0
```

- [ ] **Step 2: Run the test and verify it detects any stale ABI/version assertion**

Run: `python -m pytest tests/test_abi7_release_contract.py -q`

Expected: FAIL until every active document, generator, validator, and web health response agrees.

- [ ] **Step 3: Update documents and validators atomically**

Record the exact runtime boundary: learned graph proposals are transient; reviewed definition graphs are authority; inference projections are rebuildable; corpus splits are family-disjoint; retrieval/inference incompleteness is visible and blocks unsupported claims.

- [ ] **Step 4: Add benchmark gates**

Create an executable report that measures: graph exact-match, contribution/role F1, abstention precision, unseen-synonym composition, held-out construction accuracy, recursive proof recall, proof soundness, bounded retrieval latency, and operation safety. Do not describe CEMM as LLM-competitive without publishing these measured results beside an explicit baseline.

- [ ] **Step 5: Run complete release verification**

Run:

```bash
python tools/check_v1_final_contract.py
python tools/validate_semantic_operational_contract.py
python -m pytest -q
git diff --check
```

Expected: all commands exit 0; test collection count is documented from the fresh run rather than copied from an obsolete receipt.

- [ ] **Step 6: Commit**

```bash
git add AGENTS.md ARCHITECTURE.md RUNTIME_ARCHITECTURE.md DATA_ARCHITECTURE.md runtime-core-loop.md CEMM_RUNTIME_IMPLEMENTATION_CONTRACT.md V1_ACCEPTANCE.md tools tests
git commit -m "docs: define unified grounded acquisition contract"
```

## Plan self-review

- The proposal ABI, model integration, review publication, corpus pipeline, recursive retrieval, frame/transition semantics, web review, and release evidence each have an owning task.
- No task adds an operator, grants neural output semantic authority, or relies on raw-surface dispatch.
- The plan preserves the existing five-operator persistence substrate and explicitly removes the split direct-codec rule path.
- Every behavior-changing task starts with a focused failing test and ends with an executable command and an isolated commit.
