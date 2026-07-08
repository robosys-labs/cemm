# Causal-Runtime Wiring Fix — Breakthrough Implementation Plan

Status: **PARTIALLY ADDRESSED — schema kernel refactor complete, remaining gaps tracked below**
Priority: High — remaining items are the next blocker after schema kernel completion
Audience: AI coding agents and maintainers implementing CEMM

> **Note:** Several items in this plan have been resolved by the Semantic Schema Kernel
> refactor (see `newarch/semantic-schema-refactor.md`). Per-culprit status after deep
> code review:
>
> - **Culprit 1 (ConstructionMatcher)**: PARTIALLY OPEN — `graph_patch_templates` still
>   emits metadata only. Compensated by `_add_emotional_evaluations` in graph builder which
>   handles `evaluates` edge creation directly from schema. Low priority.
> - **Culprit 2 (MeaningGraphBuilder evaluates edges)**: ✅ FIXED — `_add_emotional_evaluations`
>   creates `evaluates` edges with `emotional_verb` feature, using schema `emotional_valence`.
> - **Culprit 3 (AffordancePredictor)**: ✅ FIXED — Rules loaded from `AffordanceRegistry`.
>   `affordance_schemas.json` includes `evaluation_shift` rules for `likes`/`dislikes`.
> - **Culprit 4 (Affordance predictions consumed)**: ✅ FIXED — Runtime passes
>   `affordance_predictions` to `schedule()`. Scheduler stores them in `context` field.
> - **Culprit 5 (CausalInference)**: PARTIALLY FIXED — `CausalBridge` exists and is called
>   from runtime, but is a no-op without legacy `Store`. Full `DurableSemanticStore`-backed
>   bridge not yet implemented.
> - **Culprit 6 (update_user_affect)**: ✅ FIXED — Called in `run_turn()` step 1a with
>   `affect_markers_to_semantics` conversion.
> - **Culprit 7 (Patch extraction filter)**: ✅ FIXED — Dedicated
>   `_extract_emotional_evaluation_patches` method handles `evaluates` edges separately.
> - **Culprit 8 (RelationFrameCompiler)**: ✅ FIXED — `evaluates` has
>   `projection_policy: "object"`. Feature-based projection distinguishes emotional vs
>   discourse `evaluates` edges.
> - **Culprit 9 (Obligation scheduler)**: ✅ FIXED — `acknowledge_emotional_context`
>   obligation kind exists. `_refine_obligation` routes `evaluation_shift` predictions to it.
> - **Culprit 10 (Realizer templates)**: ✅ FIXED — `emotional_response` and
>   `emotional_acknowledgment` templates in `response_templates.json`.
> - **Culprit 11 (AnaphoraResolver)**: ✅ FIXED — Accepts `prior_salience`, assigns
>   `entity_id` for third-person pronouns. `SessionStore` persists/restores `entity_salience`.
> - **Culprit 12 (AttentionController)**: ✅ FIXED — Tier 8b processes
>   `AffordancePrediction` objects from `graph.affordance_predictions`.
>
> **Summary: 10 of 12 culprits fully fixed, 2 partially open (Culprits 1 and 5).**

---

## 1. Problem Statement

The causal and recursive foundational architecture was designed to handle
cross-turn semantic understanding, emotional context persistence, and
entity salience tracking. The modules exist (`AffordancePredictor`,
`CausalInference`, `PragmaticInterpreter.update_user_affect`,
`EntitySalienceTracker`, `SessionStore`) but are **island components** —
built but never wired into the `SemanticKernelRuntime.run_turn()` pipeline.

### The Broken Chain

```
Architecture intended:
  Construction → evaluates edge → affordance prediction (evaluation_shift)
  → planner (empathetic response + patch) → durable store → cross-turn retrieval

What's implemented:
  Construction → intent label only (no relation patch)
  ✗ no evaluates edge for emotional predicates
  ✗ no evaluation_shift affordance rule
  ✗ affordance predictions never consumed by scheduler/realizer
  ✗ patch extractor filters out likes/evaluates
  ✗ causal inference engine disconnected from semantic runtime
  ✗ update_user_affect never called — affect state never updated during turns
  ✗ anaphora resolver doesn't resolve third-person pronouns cross-turn
  ✓ durable store can store/retrieve (but nothing to store)
```

### End-to-End Example: "I love him so much"

What should happen (architecture intent):
1. ConstructionMatcher matches "I love X" → proposes `evaluates` edge patch template
2. MeaningGraphBuilder creates `Entity(user) --evaluates--> Entity(target)` with `{"valence": "positive", "predicate": "likes"}`
3. AffordancePredictor detects `likes` relation → produces `evaluation_shift` prediction
4. SemanticAttentionController prioritises the evaluation atoms
5. SemanticObligationScheduler routes to `acknowledge_emotional_context` (not `store_patch`)
6. SemanticRealizer produces empathetic response
7. GraphPatchExtractor extracts `upsert_relation_candidate` for `likes(user, target)`
8. PatchValidator + PatchCommitter persist to `DurableSemanticStore`
9. `update_user_affect` updates `kernel.user.affect` during the turn
10. `SessionStore` persists updated affect for next turn

What actually happens:
1. ConstructionMatcher matches "love" → `state_preference` → intent `statement` → `graph_patch_templates` = metadata only
2. MeaningGraphBuilder creates `action(love)` atom — no `evaluates` edge
3. AffordancePredictor: no rule matches → zero predictions
4. AttentionController: no affordance tier processes anything
5. ObligationScheduler: `statement` → `store_patch` (generic)
6. Realizer: "Got it. I've learned that ..." (generic store confirmation)
7. PatchExtractor: `evaluates`/`likes` not in allowed set → no patch
8. Nothing committed to durable store
9. `update_user_affect` never called → affect unchanged
10. SessionStore persists stale affect

## 2. Non-Drift Principle

Fix the class of failure, not the example sentence.

- **No** "love"-specific code
- **No** "Donald Trump"-specific code
- **No** one-off "I love him" answer path
- **No** more fallback strings to hide semantic failure
- **No** hardcoded emotional response strings in Python

**Instead:**
- Add emotional predicate construction operators (data-driven)
- Add `evaluates` edge creation for affect-bearing relations
- Add `evaluation_shift` affordance rules
- Wire affordance predictions into the obligation scheduler
- Wire `update_user_affect` into the runtime turn cycle
- Wire `CausalInference` into the runtime as a prediction source
- Expand patch extraction to include `likes`/`dislikes`/`evaluates`
- Add cross-turn pronoun resolution via `EntitySalienceTracker`
- Add obligation kinds for emotional context follow-up
- Add realization templates for affect-aware responses

## 3. The 12 Culprits — Detailed Code Trace

Each culprit includes exact file, line numbers, current code, and the gap.

### Culprit 1: ConstructionMatcher — No Emotional Predicate Constructions

**File:** `cemm/kernel/construction_matcher.py`
**Lines:** 218-222 (`graph_patch_templates`), 77-78 (`_FRAME_TO_INTENT`)

Current `graph_patch_templates` at line 218:
```python
graph_patch_templates=[{
    "target": "construction_lattice",
    "operation": "observe_construction_match",
    "construction_key": record.construction_id,
}],
```

The `state_preference` frame in `uol_semantics.json` (line 17) has aliases `["prefer", "like", "favorite", "love"]` but maps to intent `statement` via `_FRAME_TO_INTENT` at line 78. The `grammatical_preference_marker` frame (line 77) has aliases `["i like", "i love", "i prefer", "i enjoy", ...]` but is skipped because it starts with `grammatical_`.

**Gap:** No construction produces a `graph_patch_templates` entry with `upsert_relation_candidate` for emotional predicates. The verb-to-relation mapping already exists in `MeaningGraphBuilder._REMEMBER_RELATION_VERBS` (line 1058) but is only used for "remember" commands.

### Culprit 2: MeaningGraphBuilder — No `evaluates` Edge for Emotional Predicates

**File:** `cemm/kernel/meaning_graph_builder.py`
**Lines:** 644-658 (`_parse_surface_relation`), 344-383 (`_add_actions`)

`_parse_surface_relation` at line 644:
```python
def _parse_surface_relation(self, tokens: list[str]) -> tuple[str, str, str] | None:
    cues = ("means", "mean", "equals", "called", "refers", "is", "are")
```

Emotional verbs like "love" become `action` atoms via `_add_actions` at line 344. The action atom gets `has_role` edges for actor/object but **no `evaluates` edge** is created linking subject to object.

The `evaluates` edge type is used only for discourse relations (concession/contrast) at line 256-257:
```python
"concession": "evaluates",
"contrast": "evaluates",
```

**Gap:** No method detects emotional verb patterns (subject + emotional verb + object) and creates `evaluates` edges with valence features.

### Culprit 3: AffordancePredictor — No `evaluation_shift` Rule

**File:** `cemm/kernel/affordance_predictor.py`
**Lines:** 64-94 (`_seed_rules`)

Current seed rules (3 total):
1. `fresh_source_requirement` — triggers on `{"kind": "evidence", "key": "fresh_external_evidence_required"}`
2. `clarity_need` — triggers on `{"kind": "intent", "key": "repair"}`
3. `cold_context_comfort_relevance` — triggers on `{"kind": "state", "key": "cold"}`

The `_atom_matches_patterns` method at line 54 checks `atom.kind` and `atom.key` — so it **can** match relation atoms with key `likes` or `dislikes` if rules existed.

**Gap:** No rule triggers on `likes`/`dislikes` relation atoms or `evaluates` edges. The `evaluation_shift` effect type defined in `ARCHITECTURE.md` §10 has no implementation.

### Culprit 4: SemanticKernelRuntime — Affordance Predictions Never Consumed

**File:** `cemm/kernel/semantic_kernel_runtime.py`
**Lines:** 172 (`_predict_affordances` call in builder), 253-313 (scheduler call), 319-515 (rest of run_turn)

The graph builder calls `_predict_affordances` at line 172, storing predictions on `uol_graph.affordance_predictions`. But `run_turn()` never reads them:

- `schedule()` at line 253: `self._obligation_scheduler.schedule(semantic_program, working_set, kernel, uol_graph)` — no `affordance_predictions` parameter
- `build_contract()` at line 325: `self._query_engine.build_contract(obligation_frame, answer_binding, semantic_program)` — no affordance context
- `realize()` — no affordance context

**Gap:** Predictions are computed but dead data. No downstream component reads `uol_graph.affordance_predictions`.

### Culprit 5: CausalInference — Disconnected from Runtime

**File:** `cemm/causal/inference.py`
**Lines:** 11-161 (entire class)

`CausalInference.__init__` takes a `Store` (line 12). `predict()` at line 15 reads from `self._store.models.find_by_kind()`. The `_graph_predicates` method at line 118 can read from a `UOLGraph` but is only called if `graph` is passed to `predict()`.

`SemanticKernelRuntime` never imports or calls `CausalInference`. The runtime uses `DurableSemanticStore` for relation frames, but `CausalInference` operates on the old `Store`/`Claim`/`Model` system.

**Gap:** Two separate storage systems. No adapter converts `RelationFrame`s to `Claim`-compatible inputs. No code path calls `CausalInference.predict()` from the runtime.

### Culprit 6: PragmaticInterpreter.update_user_affect — Never Called

**File:** `cemm/kernel/pragmatic_interpreter.py`
**Lines:** 135-178 (`update_user_affect`)

The function signature:
```python
def update_user_affect(
    current: UserAffectState, semantics: ObservationSemantics,
    kernel: ContextKernel, signal_id: str | None = None,
) -> UserAffectState:
```

It decays prior affect values and applies new affect from `semantics.affect` dict (frustration, hostility, playfulness). It computes a `current_stance` from the values.

`SemanticKernelRuntime.run_turn()` restores `kernel.user.affect` from `SessionStore` at turn start (line ~160) but **never calls `update_user_affect`** during the turn. The `ObservationSemantics` is produced by `pragmatic_interpreter.interpret_observation()` at line 62 but is never called from the runtime either.

`MeaningPerceptPacket` has `affect_markers` (line 533 of `meaning_percept.py`) populated by `self._language.detect_affect()` at line 230 of `meaning_perceptor.py`, but these markers are never converted to `ObservationSemantics` or passed to `update_user_affect`.

**Gap:** Affect infrastructure exists end-to-end (detection → interpretation → update → persistence) but the runtime never calls the update step. Affect state is frozen at whatever was restored from session.

### Culprit 7: Patch Extraction Filter — Excludes Emotional Relations

**File:** `cemm/kernel/meaning_graph_builder.py`
**Lines:** 1170-1216 (`_extract_graph_patches`)

The filter at line 1174:
```python
if edge.edge_type in {"is_a", "same_as", "has_property", "used_for", "part_of"}
```

`likes`, `dislikes`, and `evaluates` are **not in this set**. Even if `evaluates` edges existed (Culprit 2), they would never produce patch candidates.

The only path to persist a `likes` relation is through `_extract_remember_relation_patches` at line 1077, which requires a "remember" command prefix.

**Gap:** Emotional relations are excluded from durable patch extraction. The filter is a hardcoded set that doesn't include evaluation/preference relation types.

### Culprit 8: RelationFrameCompiler — `evaluates` Has `projection_policy: "none"`

**File:** `cemm/kernel/relation_frame_compiler.py`
**Lines:** 101-112 (`_EDGE_PROJECTION_POLICY`)

Current mapping at line 110:
```python
"evaluates": "none",
```

This means `evaluates` edges are compiled into `RelationFrame`s but marked as non-answerable. Even if the graph contained `evaluates` edges and the query engine found them, they would be filtered out of answer bindings.

**Gap:** `evaluates` is classified as a structural edge (line 97) with `projection_policy: "none"`, preventing it from ever being returned as an answer.

### Culprit 9: SemanticObligationScheduler — No Emotional Context Obligation

**File:** `cemm/kernel/semantic_obligation_scheduler.py`
**Lines:** 34-47 (`_KIND_TO_OBLIGATION`), 99-153 (`schedule()`), 155-192 (`_refine_obligation()`)

The obligation kind map at line 34:
```python
_KIND_TO_OBLIGATION: dict[str, str] = {
    "safety": "abstain_policy",
    "question": "answer_concept",
    ...
    "assertion": "store_patch",
    "command": "store_patch",
    ...
    "social": "social_reply",
    ...
}
```

Emotional predicates map to `statement` intent → `assertion` kind → `store_patch` obligation. There is no obligation kind for empathetic response or emotional context acknowledgement.

The `_refine_obligation` method at line 155 can refine `answer_concept` and `social_reply` but has no branch for `store_patch` when affordance predictions contain `evaluation_shift`.

The `schedule()` method at line 100 accepts `uol_graph` but **not** `affordance_predictions`:
```python
def schedule(self, program, working_set, kernel, uol_graph) -> ObligationFrame:
```

**Gap:** No obligation kind for emotional context. No logic to detect `evaluation_shift` predictions and route to empathetic response.

### Culprit 10: SemanticRealizer — No Emotional Follow-up Templates

**File:** `cemm/kernel/semantic_realizer.py`, `cemm/data/response_templates.json`
**Lines:** templates file line 67-76

Current templates:
```json
"evidence_answer": "{answer}",
"store_confirmation": "Got it. I've learned that {answer}.",
"social_response": "Hello!",
```

No template exists for `acknowledge_emotional_context` or `acknowledge_evaluation`. The realizer's `_template_for_obligation` method maps obligation kinds to template keys — any unmapped obligation falls back to `general_conversation`.

**Gap:** No realization templates for empathetic or affect-aware responses. The system can only produce generic store confirmations or social replies.

### Culprit 11: AnaphoraResolver — No Cross-Turn Pronoun Resolution

**File:** `cemm/kernel/anaphora_resolver.py`
**Lines:** 100-125 (third-person pronoun handling)

Current code at line 108:
```python
# Third-person pronouns: leave unresolved for graph builder,
# but record best candidate in evidence for downstream use.
target_type = self._match_type(ref.entity_type)
if target_type is None:
    continue
match = self._find_best_match(ref.surface, target_type, known_entities)
if match is not None:
    ref.evidence.append(AtomEvidence(
        source="anaphora_candidate",
        surface=ref.surface,
        confidence=match.get("confidence", 0.5) * 0.85,
        rationale=f"candidate_entity={match['entity_id']}",
    ))
```

The resolver **records** the best candidate in evidence but **does not assign** `ref.entity_id`. The `known_entities` list is built from the current turn's referents only — no prior salience scores are passed in.

`EntitySalienceTracker` at line 37 accepts `prior_salience` but `AnaphoraResolver` never receives it. The runtime creates `EntitySalienceTracker` but doesn't pass its output to the anaphora resolver.

**Gap:** Third-person pronouns remain unresolved. Cross-turn entity salience data exists but is not fed to the anaphora resolver.

### Culprit 12: SemanticAttentionController — Doesn't Process AffordancePredictions

**File:** `cemm/kernel/semantic_attention_controller.py`
**Lines:** 102-111 (Tier 8)

Current Tier 8 at line 102:
```python
# Tier 8: Self/action affordance requirements (priority = 8)
for atom in graph.atoms.values():
    if atom.kind in ("self", "action") and atom.id not in seen_atom_ids:
        focus_items.append(SemanticFocus(
            atom_id=atom.id,
            reason=f"affordance:{atom.kind}",
            priority=8,
            confidence=atom.confidence,
        ))
```

This tier matches `self`/`action` **atom kinds** — it does not process `AffordancePrediction` objects from `graph.affordance_predictions`. The tier name says "affordance" but the implementation is atom-kind-based.

**Gap:** `AffordancePrediction` objects are never converted to `SemanticFocus` items. Atoms triggered by affordance predictions don't receive attention priority.

## 4. Implementation Plan — 7 Phases

Each phase is self-contained and testable. Phases must be implemented in order
because later phases depend on earlier ones (e.g. affordance rules need
`evaluates` edges to exist before they can trigger).

---

### Phase 1: Wire Affect Update (Culprit 6)

**Goal:** Make `kernel.user.affect` update during turns, not just restore from session.

**Files to modify:**
- `cemm/kernel/semantic_kernel_runtime.py` — call `update_user_affect` after perception
- `cemm/kernel/pragmatic_interpreter.py` — add `affect_markers_to_semantics` helper

**Step 1a: Convert affect_markers to ObservationSemantics**

`MeaningPerceptPacket.affect_markers` is a `list[dict[str, Any]]` populated by `LanguageAdapter.detect_affect()`. The `update_user_affect` function needs an `ObservationSemantics` with an `affect` dict. Add a helper in `pragmatic_interpreter.py`:

```python
def affect_markers_to_semantics(
    affect_markers: list[dict[str, Any]],
    signal_id: str = "",
) -> ObservationSemantics:
    affect = {"valence": 0.0, "arousal": 0.0, "frustration": 0.0,
              "hostility": 0.0, "playfulness": 0.0}
    for marker in affect_markers:
        marker_type = marker.get("type", "")
        valence = marker.get("valence", 0.0)
        if marker_type in ("frustration", "hostility", "playfulness"):
            affect[marker_type] = max(affect[marker_type], abs(valence))
        if valence > 0:
            affect["valence"] = max(affect["valence"], valence)
            affect["arousal"] = max(affect["arousal"], abs(valence))
    return ObservationSemantics(
        speech_act="statement",
        affect=affect,
        confidence=0.6,
    )
```

**Step 1b: Call update_user_affect in run_turn()**

After `self._cpu.perceptor.perceive(signal, kernel)` in `run_turn()`:

```python
from .pragmatic_interpreter import update_user_affect, affect_markers_to_semantics
if packet.affect_markers:
    semantics = affect_markers_to_semantics(packet.affect_markers, signal.id)
    kernel.user.affect = update_user_affect(
        kernel.user.affect, semantics, kernel, signal.id,
    )
```

**Verification:**
- Run "I love him so much" through the pipeline
- Assert `kernel.user.affect.current_stance != "cooperative"` (should shift)
- Assert `kernel.user.affect.last_updated_signal_id == signal.id`
- Assert `SessionStore` persists the updated affect

**Drift risk:** Low. This wires existing functions together. No new types, no new modules.

---

### Phase 2: Create `evaluates` Edges (Culprits 1, 2)

**Goal:** Emotional predicates produce `evaluates` edges in the working graph.

**Files to modify:**
- `cemm/kernel/meaning_graph_builder.py` — add `_add_emotional_evaluations` method
- `cemm/kernel/construction_matcher.py` — enrich `graph_patch_templates` for emotional constructions

**Step 2a: Add `_add_emotional_evaluations` to MeaningGraphBuilder**

Add a new method called after `_add_actions` (line 153) in the `build()` method:

```python
self._add_emotional_evaluations(graph, packet, packet.meaning_groups)
```

The method scans action atoms for emotional verbs and creates `evaluates` edges:

```python
_EMOTIONAL_VERB_TO_RELATION: dict[str, str] = {
    "like": "likes", "likes": "likes", "love": "likes", "loves": "likes",
    "prefer": "likes", "prefers": "likes", "enjoy": "likes", "enjoys": "likes",
    "hate": "dislikes", "hates": "dislikes",
    "dislike": "dislikes", "dislikes": "dislikes",
}

def _add_emotional_evaluations(
    self, graph: UOLGraph, packet: MeaningPerceptPacket,
    groups: Iterable[MeaningGroup],
) -> None:
    for action in packet.actions:
        verb = (action.action_key or action.surface or "").lower()
        relation_key = self._EMOTIONAL_VERB_TO_RELATION.get(verb)
        if not relation_key:
            continue
        # Find the action atom in the graph
        action_atoms = [
            atom for atom in graph.atoms.values()
            if atom.kind == "action" and atom.group_id == action.group_id
            and atom.key == action.action_key
        ]
        if not action_atoms:
            continue
        action_atom = action_atoms[0]
        # Find subject (actor) and object via has_role edges
        subject_atom = self._find_role_atom(graph, action_atom, "actor")
        object_atom = self._find_role_atom(graph, action_atom, "object")
        if subject_atom is None or object_atom is None:
            continue
        valence = "positive" if relation_key == "likes" else "negative"
        graph.add_edge(
            "evaluates",
            subject_atom.id,
            object_atom.id,
            group_id=action.group_id,
            confidence=action.confidence,
            features={
                "valence": valence,
                "predicate": relation_key,
                "emotional_verb": verb,
            },
        )
```

`_find_role_atom` is a helper that traverses `has_role` edges:
```python
def _find_role_atom(self, graph: UOLGraph, atom: UOLAtom, role: str) -> UOLAtom | None:
    for edge in graph.edges:
        if edge.source_id == atom.id and edge.edge_type == "has_role":
            if edge.features.get("role") == role:
                target = graph.atoms.get(edge.target_id)
                if target:
                    return target
    return None
```

**Step 2b: Enrich ConstructionMatcher graph_patch_templates**

In `_seed_from_uol_semantics`, when the canonical_key is `state_preference`, add a relation patch template:

```python
if canonical_key == "state_preference":
    # Add emotional relation patch template
    for alias in aliases:
        verb = alias.lower()
        relation = _EMOTIONAL_VERB_TO_RELATION.get(verb, "likes")
        construction_id = f"{canonical_key}::{alias}"
        self._lattice.upsert(ConstructionAtom(
            construction_id=construction_id,
            form_signature=FormSignature(surface_pattern=alias),
            port_constraints=[PortConstraint(port_key="subject"), PortConstraint(port_key="object")],
            pragmatic_signature=PragmaticPattern(expected_acts=["preference_assertion"]),
            graph_patch_templates=[{
                "target": "concept_lattice",
                "operation": "upsert_relation_candidate",
                "relation_key": relation,
                "edge_type": "evaluates",
            }],
            confidence=intensity,
        ))
```

**Verification:**
- Run "I love Donald Trump" through the pipeline
- Assert graph contains an `evaluates` edge with `features.valence == "positive"` and `features.predicate == "likes"`
- Assert the edge connects the user entity atom to the target entity atom
- Assert `graph.trace["edge_count"]` increased

**Drift risk:** Medium. New method in graph builder, new edge creation. Must ensure `evaluates` edges are not confused with discourse `evaluates` edges (concession/contrast). The `features` dict distinguishes them via `emotional_verb` and `predicate` keys.

---

### Phase 3: Add Affordance Rules and Wire Predictions (Culprits 3, 4, 12)

**Goal:** `evaluates` edges trigger `evaluation_shift` predictions, and those predictions reach the obligation scheduler and attention controller.

**Files to modify:**
- `cemm/kernel/affordance_predictor.py` — add `evaluation_shift` seed rules
- `cemm/kernel/semantic_attention_controller.py` — add affordance prediction tier
- `cemm/kernel/semantic_obligation_scheduler.py` — accept `affordance_predictions` parameter
- `cemm/kernel/semantic_kernel_runtime.py` — pass predictions to scheduler

**Step 3a: Add evaluation_shift affordance rules**

In `AffordancePredictor._seed_rules()`, add two new rules:

```python
CausalAffordance(
    affordance_id="user_positive_evaluation",
    trigger_pattern=GraphPattern(atom_patterns=[
        {"kind": "relation", "key": "likes"},
    ]),
    effect_type="evaluation_shift",
    predicted_effect=GraphPatchTemplate(operations=[
        {"key": "affect_shift", "value": "positive_stance"},
    ]),
    confidence=0.7,
),
CausalAffordance(
    affordance_id="user_negative_evaluation",
    trigger_pattern=GraphPattern(atom_patterns=[
        {"kind": "relation", "key": "dislikes"},
    ]),
    effect_type="evaluation_shift",
    predicted_effect=GraphPatchTemplate(operations=[
        {"key": "affect_shift", "value": "negative_stance"},
    ]),
    confidence=0.7,
),
```

Note: The `predict()` method at line 19 iterates `graph.atoms.values()`. The emotional relation must appear as a **relation atom** with `key == "likes"` or `key == "dislikes"`. The graph builder's `_add_emotional_evaluations` (Phase 2) creates `evaluates` **edges**, not relation atoms. So we also need to add a relation atom for the emotional predicate:

In `_add_emotional_evaluations`, after creating the `evaluates` edge, also add a relation atom:
```python
relation_atom = graph.add_atom(
    "relation",
    relation_key,
    surface=verb,
    group_id=action.group_id,
    confidence=action.confidence,
    source="emotional_predicate",
    features={"valence": valence, "predicate": relation_key},
)
graph.add_edge("evaluates", subject_atom.id, object_atom.id, ...)
graph.add_edge("has_role", relation_atom.id, subject_atom.id, features={"role": "subject"})
graph.add_edge("has_role", relation_atom.id, object_atom.id, features={"role": "object"})
```

This gives the affordance predictor a relation atom to match against.

**Step 3b: Add affordance prediction tier to attention controller**

In `SemanticAttentionController.attend()`, after Tier 8 (line 111), add:

```python
# Tier 8b: Affordance prediction triggers (priority = 8)
for pred in graph.affordance_predictions:
    for atom_id in pred.trigger_atom_ids:
        if atom_id not in seen_atom_ids:
            focus_items.append(SemanticFocus(
                atom_id=atom_id,
                reason=f"affordance_prediction:{pred.affordance_key}",
                priority=8,
                confidence=pred.confidence,
            ))
            seen_atom_ids.add(atom_id)
```

**Step 3c: Pass affordance_predictions to scheduler**

Modify `SemanticObligationScheduler.schedule()` signature:

```python
def schedule(
    self,
    program: SemanticProgram,
    working_set: Any | None = None,
    kernel: Any | None = None,
    uol_graph: Any | None = None,
    affordance_predictions: list[Any] | None = None,
) -> ObligationFrame:
```

Store predictions on the ObligationFrame for downstream use:

```python
return ObligationFrame(
    ...
    # Add field to ObligationFrame type
    context={"affordance_predictions": affordance_predictions or []},
)
```

In `SemanticKernelRuntime.run_turn()`, pass the predictions:

```python
affordance_predictions = uol_graph.affordance_predictions
obligation_frame = self._obligation_scheduler.schedule(
    semantic_program, working_set, kernel, uol_graph,
    affordance_predictions=affordance_predictions,
)
```

**Verification:**
- Run "I love X" through the pipeline
- Assert `uol_graph.affordance_predictions` contains a prediction with `effect_type == "evaluation_shift"`
- Assert `obligation_frame.context["affordance_predictions"]` is non-empty
- Assert attention working set contains focus items with `reason` starting with `affordance_prediction:`

**Drift risk:** Medium. New parameter on `schedule()`. Must update all callers (only `SemanticKernelRuntime`). `ObligationFrame` type needs a `context` field — check if it already has one or add it.

---

### Phase 4: Expand Patch Extraction and Projection (Culprits 7, 8)

**Goal:** `likes`/`dislikes`/`evaluates` relations produce durable patch candidates and are answerable in query results.

**Files to modify:**
- `cemm/kernel/meaning_graph_builder.py` — expand patch extraction filter
- `cemm/kernel/relation_frame_compiler.py` — change `evaluates` projection policy

**Step 4a: Expand patch extraction filter**

In `_extract_graph_patches` at line 1174, change:

```python
# BEFORE:
if edge.edge_type in {"is_a", "same_as", "has_property", "used_for", "part_of"}

# AFTER:
if edge.edge_type in {"is_a", "same_as", "has_property", "used_for", "part_of",
                       "likes", "dislikes", "evaluates"}
```

Also add `_EDGE_TYPE_TO_RELATION_FAMILY` entries for the new types:

```python
"likes": "preference",
"dislikes": "preference",
"evaluates": "evaluation",
```

**Step 4b: Change evaluates projection policy**

In `RelationFrameCompiler._EDGE_PROJECTION_POLICY` at line 110, change:

```python
# BEFORE:
"evaluates": "none",

# AFTER:
"evaluates": "object",
```

Also remove `evaluates` from `_STRUCTURAL_EDGE_TYPES` at line 97 if present, so it's treated as a content edge.

**Caveat:** Discourse `evaluates` edges (concession/contrast) should remain structural. Distinguish by checking `features` for `emotional_verb` key. If the edge has `features.emotional_verb`, it's an emotional evaluation — project it. If not, it's a discourse edge — keep `projection_policy: "none"`.

Implementation: In `_compile_edge`, check features:
```python
if edge.edge_type == "evaluates":
    is_emotional = "emotional_verb" in (edge.features or {})
    projection_policy = "object" if is_emotional else "none"
    is_structural = not is_emotional
else:
    projection_policy = self._EDGE_PROJECTION_POLICY.get(edge.edge_type, "object")
    is_structural = edge.edge_type in self._STRUCTURAL_EDGE_TYPES
```

**Verification:**
- Run "I love X" through the pipeline
- Assert `graph.patch_candidates` contains a `GraphPatch` with `operation == "upsert_relation_candidate"` and `fields.relation_key == "likes"`
- Assert the compiled `RelationFrame` for the `evaluates` edge has `is_structural == False`
- Assert the frame is not filtered out by the query engine

**Drift risk:** Medium. Must not break discourse `evaluates` handling. The feature-based distinction is critical.

---

### Phase 5: Add Emotional Obligation and Realization (Culprits 9, 10)

**Goal:** Emotional predicates route to `acknowledge_emotional_context` obligation with empathetic realization templates.

**Files to modify:**
- `cemm/kernel/semantic_obligation_scheduler.py` — add emotional obligation routing
- `cemm/data/response_templates.json` — add emotional templates
- `cemm/kernel/semantic_query_engine.py` — pass affordance context to `build_contract`

**Step 5a: Add emotional obligation routing**

In `_refine_obligation()`, after the existing refinements, add:

```python
# Check for evaluation_shift affordance predictions
if affordance_predictions and base == "store_patch":
    has_evaluation_shift = any(
        p.get("effect_type") == "evaluation_shift"
        for p in affordance_predictions
    )
    if has_evaluation_shift:
        return "acknowledge_emotional_context"
```

Add to `_RESPONSE_MODE`:
```python
"acknowledge_emotional_context": "emotional_response",
```

Add to `_WRITE_POLICY`:
```python
"acknowledge_emotional_context": "patch_only",
```

Add to `_EVIDENCE_POLICY`:
```python
"acknowledge_emotional_context": "speaker_asserted",
```

Add to `_OBLIGATION_PRIORITY`:
```python
"acknowledge_emotional_context": 3,  # same priority as teaching
```

**Step 5b: Add realization templates**

In `response_templates.json`, add:

```json
"emotional_response": "I can see you feel strongly about {answer}. Tell me more about that.",
"emotional_acknowledgment": "Got it — {answer}. That's helpful to know."
```

**Step 5c: Build contract with emotional context**

In `SemanticQueryEngine.build_contract()`, when `obligation.obligation_kind == "acknowledge_emotional_context"`:

- Extract the object surface from the `evaluates` edge or relation atom
- Fill the `answer` slot with the object surface
- Use `emotional_response` template

The existing `build_contract` at line 367 handles `store_patch` by extracting `entry.surface`. For `acknowledge_emotional_context`, extract the object of the `evaluates` edge from the graph:

```python
elif obligation.obligation_kind == "acknowledge_emotional_context" and uol_graph is not None:
    # Find the evaluates edge with emotional_verb feature
    for edge in uol_graph.edges:
        if edge.edge_type == "evaluates" and "emotional_verb" in (edge.features or {}):
            target = uol_graph.atoms.get(edge.target_id)
            if target:
                slots["answer"] = RealizationSlot(
                    slot_key="answer",
                    slot_kind="entity",
                    value=target.surface,
                    confidence=edge.confidence,
                )
                break
```

**Verification:**
- Run "I love him so much" through the pipeline
- Assert `obligation_frame.obligation_kind == "acknowledge_emotional_context"`
- Assert `obligation_frame.response_mode == "emotional_response"`
- Assert realized output contains the target entity surface, not "Got it. I've learned that..."
- Assert output is empathetic, not a bare store confirmation

**Drift risk:** High. New obligation kind, new template, new contract logic. Must ensure the emotional obligation doesn't suppress legitimate questions (priority must be lower than `question`). Must ensure patch extraction still happens (write_policy = `patch_only`).

---

### Phase 6: Cross-Turn Pronoun Resolution (Culprit 11)

**Goal:** Third-person pronouns resolve to entities from prior turns using `EntitySalienceTracker`.

**Files to modify:**
- `cemm/kernel/anaphora_resolver.py` — accept and use prior salience
- `cemm/kernel/semantic_kernel_runtime.py` — pass salience to resolver
- `cemm/kernel/session_store.py` — persist salience map

**Step 6a: Pass prior_salience to AnaphoraResolver**

Modify `AnaphoraResolver.resolve()` to accept `prior_salience: dict[str, float] | None = None`:

```python
def resolve(
    self,
    referents: list[ReferentAtom],
    groups: list[MeaningGroup],
    entities: list[dict[str, Any]] | None = None,
    prior_salience: dict[str, float] | None = None,
) -> list[ReferentAtom]:
```

**Step 6b: Assign entity_id for third-person pronouns**

At line 117, after finding the best match, **assign** `entity_id` instead of just recording evidence:

```python
if match is not None:
    # Assign entity_id for cross-turn resolution
    ref.entity_id = match["entity_id"]
    ref.evidence.append(AtomEvidence(
        source="anaphora_candidate",
        surface=ref.surface,
        confidence=match.get("confidence", 0.5) * 0.85,
        rationale=f"cross_turn_salience_match={match['entity_id']}",
    ))
```

Also merge prior_salience entities into `known_entities`:

```python
if prior_salience:
    for entity_id, score in prior_salience.items():
        if score > 0.3:  # threshold
            entry = {
                "text": entity_id,
                "entity_id": entity_id,
                "entity_type": "unknown",
                "role": "topic",
                "confidence": min(score, 1.0),
            }
            if entry not in known_entities:
                known_entities.append(entry)
```

**Step 6c: Persist and restore salience in SessionStore**

In `SessionStore.persist()`, add:
```python
"entity_salience": copy.deepcopy(kernel.conversation.entity_salience)
```

In `SessionStore.restore()`, add:
```python
conv.entity_salience = prior.get("entity_salience", {})
```

**Step 6d: Wire in SemanticKernelRuntime**

In `run_turn()`, before calling `perceptor.perceive()`:

```python
prior_salience = getattr(kernel.conversation, "entity_salience", {})
```

Pass to perceptor or directly to anaphora resolver. The perceptor calls `self._anaphora_resolver.resolve()` at line ~230 of `meaning_perceptor.py`. Add `prior_salience` parameter to that call.

After perception, update salience:
```python
from .entity_salience_tracker import EntitySalienceTracker
ranked, updated_salience = EntitySalienceTracker().score(
    packet.referents, packet.meaning_groups, prior_salience,
)
kernel.conversation.entity_salience = updated_salience
```

**Verification:**
- Turn 1: "I love Donald Trump" → entity `donald_trump` gets high salience
- Turn 2: "Tell me more about him" → `him` resolves to `entity_id == "donald_trump"`
- Assert `ref.entity_id` is set, not just evidence
- Assert salience map persists via SessionStore

**Drift risk:** Medium. New parameter on `resolve()`. Must update all callers. Must handle gender/number constraints (he→male, she→female, they→plural). For now, accept best match regardless of gender — gender constraints can be added later.

---

### Phase 7: Wire CausalInference (Culprit 5)

**Goal:** `CausalInference` produces predictions from `DurableSemanticStore` relation frames, fed into the obligation scheduler.

**Files to create:**
- `cemm/kernel/causal_bridge.py` — adapter between `DurableSemanticStore` and `CausalInference`

**Files to modify:**
- `cemm/kernel/semantic_kernel_runtime.py` — call causal bridge after relation compilation
- `cemm/causal/inference.py` — add `predict_from_frames()` method

**Step 7a: Create CausalBridge adapter**

```python
# cemm/kernel/causal_bridge.py
from ..causal.inference import CausalInference
from ..memory.durable_semantic_store import DurableSemanticStore
from ..types.context_kernel import ContextKernel
from ..types.packets import InferencePacket


class CausalBridge:
    """Adapter: DurableSemanticStore RelationFrames → CausalInference predictions."""

    def __init__(
        self,
        durable_store: DurableSemanticStore,
        causal_inference: CausalInference | None = None,
    ) -> None:
        self._durable_store = durable_store
        self._causal = causal_inference  # may be None if no Store

    def predict_from_graph(
        self,
        graph: Any,
        kernel: ContextKernel,
        relation_frames: list[Any] | None = None,
    ) -> dict[str, Any]:
        """Produce causal predictions from the current graph + durable frames."""
        # Extract predicates from graph atoms
        predicates: list[str] = []
        entity_ids: list[str] = []
        for atom in graph.atoms.values():
            if atom.kind in ("process", "state", "relation"):
                predicates.append(atom.key)
            if atom.kind == "entity":
                entity_ids.append(atom.key)

        # Query durable store for related relations
        relevant_frames = []
        if relation_frames:
            relevant_frames = relation_frames
        else:
            for eid in entity_ids:
                relevant_frames.extend(
                    self._durable_store.query_relations(entity_id=eid)
                )

        # Build lightweight predictions without old Store/Claim system
        predictions: list[dict] = []
        for frame in relevant_frames:
            if frame.relation_key in ("likes", "dislikes"):
                predictions.append({
                    "predicate": frame.relation_key,
                    "confidence": frame.confidence,
                    "risk": 0.0,
                    "source": "durable_relation",
                    "subject": frame.subject.entity_id or frame.subject.surface,
                    "object": frame.object.entity_id or frame.object.surface,
                })

        return {
            "predictions": predictions,
            "predicates": predicates,
            "entity_ids": entity_ids,
        }
```

**Step 7b: Call CausalBridge in run_turn()**

After relation frame compilation and durable query (line ~290):

```python
from .causal_bridge import CausalBridge
causal_result = CausalBridge(self._durable_store).predict_from_graph(
    uol_graph, kernel, relation_frames=turn_frames + durable_frames,
)
```

Store in diagnostics:
```python
diagnostics["causal_predictions"] = causal_result["predictions"]
```

**Verification:**
- After committing a `likes` relation (Phase 4), run a second turn mentioning the same entity
- Assert `diagnostics["causal_predictions"]` contains a prediction with `predicate == "likes"`
- Assert predictions are available to the obligation scheduler

**Drift risk:** Low. New module, no changes to existing modules except runtime. The bridge is a read-only adapter — it doesn't mutate the graph or durable store. Can be added without touching `CausalInference` internals.

**Note:** Full `CausalInference.predict()` integration (with `Store`/`Claim`/`Model`) is deferred. The bridge provides graph-native causal predictions without requiring the old storage system. When `CausalInference` is migrated to use `DurableSemanticStore`, the bridge can be removed.

## 5. Acceptance Criteria

The fix is complete only when **all 10 criteria** pass:

1. "I love him so much" produces an `evaluates` edge in the working graph
2. The edge triggers an `evaluation_shift` affordance prediction
3. The affordance prediction reaches the obligation scheduler
4. The obligation is `acknowledge_emotional_context`, not `store_patch`
5. The realized output is empathetic, not a bare confirmation
6. The `likes` relation is extracted as a graph patch and committed to durable store
7. On the next turn, "Tell me more about him" resolves "him" to the prior entity
8. `kernel.user.affect` is updated during the turn, not just restored
9. `CausalBridge` predictions appear in runtime diagnostics
10. No domain-specific code (no "Trump", no "love" hardcoded in Python logic — only in data files)

### Regression Guards

- Existing golden tests must still pass (role labels, teaching persistence, self-identity, social suppression)
- Fuzz tests must not crash
- Multiturn integration tests must still pass (greetings, self-query, teaching)
- The `social_response` template "Hello!" must still work for genuine greetings ("hi", "hello")

## 6. What Not To Build

- **No** sentiment analysis model
- **No** emotion classifier
- **No** hardcoded emotional response strings in Python (templates in JSON only)
- **No** domain-specific entity handlers
- **No** bypass of the graph patch flow for emotional relations
- **No** storage of emotional state as raw text
- **No** new storage systems (use existing `DurableSemanticStore`)
- **No** new graph types (use existing `UOLGraph`)
- **No** separate emotional processing pipeline (everything flows through the existing 11-step `run_turn()`)

## 7. Testing Strategy

### New Golden Tests (in `tests/golden/`)

**`test_golden_emotional_predicate_persistence.py`**
- Teach "I love X" (no "remember" prefix)
- Assert `graph.patch_candidates` contains `upsert_relation_candidate` with `relation_key == "likes"`
- Assert `DurableSemanticStore.query_relations()` returns the `likes` relation after commit
- Assert the relation survives a second turn

**`test_golden_cross_turn_pronoun_resolution.py`**
- Turn 1: "I love Donald Trump"
- Turn 2: "Tell me more about him"
- Assert turn 2's `packet.referents` has `entity_id == "donald_trump"` for the "him" referent
- Assert the graph contains a `refers_to` edge linking the pronoun to the entity

**`test_golden_affect_update_during_turn.py`**
- Run "I love him so much" through the pipeline
- Assert `kernel.user.affect.last_updated_signal_id == signal.id`
- Assert `kernel.user.affect.current_stance` is not the default `"cooperative"`
- Assert `SessionStore` persists the updated affect

**`test_golden_affordance_prediction_reaches_scheduler.py`**
- Run "I love X" through the pipeline
- Assert `uol_graph.affordance_predictions` contains a prediction with `effect_type == "evaluation_shift"`
- Assert `obligation_frame` carries the predictions (via `context` or equivalent)

**`test_golden_empathetic_response.py`**
- Run "I love him so much" through the pipeline
- Assert `obligation_frame.obligation_kind == "acknowledge_emotional_context"`
- Assert `result.realized_output` does not contain "Got it. I've learned that"
- Assert `result.realized_output` contains the target entity surface
- Assert the response is empathetic in tone

### Test Already Deleted

- `test_golden_social_phatic_checkin.py` — asserted `realized_output == "Hello!"` for "how are you", locking in broken phatic checkin behavior. Moved to `docs/archive/newarch_superseded/`.

### Property Tests (add to `tests/test_randomized_fuzz.py`)

- For any emotional predicate (like/love/hate/prefer + object), graph must contain `evaluates` edge with `emotional_verb` feature
- For any `evaluates` edge with `emotional_verb` feature, affordance predictor must produce `evaluation_shift` prediction
- For any `evaluation_shift` prediction, obligation scheduler must route to `acknowledge_emotional_context`
- For any committed `likes`/`dislikes` relation, durable store must retrieve it on subsequent turns
- For any turn with affect markers, `kernel.user.affect.last_updated_signal_id` must equal the signal ID

### Verification Commands

```bash
# Run all golden tests
python -m pytest cemm/tests/golden/ -v

# Run multiturn integration tests
python -m pytest cemm/tests/test_multiturn_integration.py -v

# Run fuzz tests (should not crash)
python -m pytest cemm/tests/test_randomized_fuzz.py -v

# Run specific emotional predicate test
python -m pytest cemm/tests/golden/test_golden_emotional_predicate_persistence.py -v
```

## 8. Phase Dependency Graph

```
Phase 1 (Affect Update)     ──────────────────────┐
                                                    │
Phase 2 (evaluates Edges)   ────────────┐           │
                                          │           │
Phase 3 (Affordance Rules)  ─── depends on 2        │
                                          │           │
Phase 4 (Patch Extraction)  ─── depends on 2        │
                                          │           │
Phase 5 (Obligation+Realize)── depends on 3, 4      │
                                          │           │
Phase 6 (Pronoun Resolution)──────────────┼───────────┘
                                          │
Phase 7 (CausalInference)   ─── depends on 4 (needs committed relations)
```

Phases 1 and 6 can be done in parallel with Phase 2.
Phase 7 can be done last — it's the lowest priority since the core chain
(Phases 2-5) delivers the primary user-visible fix.

## 9. Data Flow After Fix

```
User: "I love him so much"

1. Perception
   → affect_markers: [{type: "positive", valence: 0.7, surface: "love"}]
   → actions: [ActionAtom(key="love", actor="user", object="him")]
   → referents: [ReferentAtom(surface="him", entity_type="person")]
   → AnaphoraResolver: "him" → entity_id="donald_trump" (from prior salience)

2. Affect Update (Phase 1)
   → affect_markers_to_semantics → ObservationSemantics(affect={valence: 0.7, ...})
   → update_user_affect → kernel.user.affect.current_stance = "cooperative" (positive)
   → SessionStore will persist updated affect

3. Graph Building (Phase 2)
   → _add_actions: action(love) atom with has_role(actor=user, object=donald_trump)
   → _add_emotional_evaluations: evaluates(user, donald_trump) with features={valence: "positive", predicate: "likes", emotional_verb: "love"}
   → relation(likes) atom with has_role(subject=user, object=donald_trump)

4. Affordance Prediction (Phase 3)
   → AffordancePredictor matches relation(likes) → evaluation_shift prediction
   → graph.affordance_predictions = [AffordancePrediction(effect_type="evaluation_shift", ...)]

5. Attention (Phase 3)
   → Tier 8b: affordance prediction atoms get priority 8
   → Working set includes emotional evaluation atoms

6. Obligation Scheduling (Phase 5)
   → _refine_obligation: base="store_patch", but evaluation_shift detected
   → Returns "acknowledge_emotional_context"
   → response_mode = "emotional_response"

7. Relation Frame Compilation (Phase 4)
   → evaluates edge with emotional_verb → is_structural=False, projection_policy="object"
   → RelationFrame(subject=user, relation=likes, object=donald_trump) is answerable

8. Query + Realization (Phase 5)
   → build_contract: finds evaluates edge, extracts "donald_trump" as answer slot
   → Template: "I can see you feel strongly about Donald Trump. Tell me more about that."

9. Patch Extraction (Phase 4)
   → _extract_graph_patches: evaluates edge in allowed set
   → GraphPatch(operation="upsert_relation_candidate", relation_key="likes", ...)

10. Patch Validation + Commit
    → PatchValidator validates the patch
    → PatchCommitter commits to DurableSemanticStore

11. Session Persistence
    → SessionStore persists: user_affect (updated), entity_salience (updated), conversation state

12. Causal Bridge (Phase 7)
    → CausalBridge reads durable relations for entity "donald_trump"
    → Finds likes(user, donald_trump) → prediction available for next turn
```

## 10. Files Touched Summary

| File | Phase | Change |
|------|-------|--------|
| `cemm/kernel/semantic_kernel_runtime.py` | 1,3,5,6,7 | Wire affect update, pass predictions, call causal bridge |
| `cemm/kernel/pragmatic_interpreter.py` | 1 | Add `affect_markers_to_semantics` helper |
| `cemm/kernel/meaning_graph_builder.py` | 2,4 | Add `_add_emotional_evaluations`, expand patch filter |
| `cemm/kernel/construction_matcher.py` | 2 | Enrich `graph_patch_templates` for emotional constructions |
| `cemm/kernel/affordance_predictor.py` | 3 | Add `evaluation_shift` seed rules |
| `cemm/kernel/semantic_attention_controller.py` | 3 | Add affordance prediction tier |
| `cemm/kernel/semantic_obligation_scheduler.py` | 3,5 | Accept predictions, add emotional obligation routing |
| `cemm/kernel/relation_frame_compiler.py` | 4 | Feature-based projection for `evaluates` |
| `cemm/kernel/semantic_query_engine.py` | 5 | Emotional context in `build_contract` |
| `cemm/data/response_templates.json` | 5 | Add `emotional_response` template |
| `cemm/kernel/anaphora_resolver.py` | 6 | Accept prior_salience, assign entity_id |
| `cemm/kernel/session_store.py` | 6 | Persist/restore entity_salience |
| `cemm/kernel/causal_bridge.py` | 7 | **New file** — adapter for causal predictions |
| `cemm/types/obligation_frame.py` | 3 | Add `context` field (if not present) |
| `cemm/types/context_kernel.py` | 6 | Add `entity_salience` to ConversationState (if not present) |

**Total: 14 files modified, 1 file created, 0 files deleted.**
