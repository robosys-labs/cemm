# CEMM v3.3 — Learning Nervous System Plan (Merged)

**Version:** 3.3 | **Date:** 2026-07-03  
**Status:** merged implementation plan  
**Builds on:** `cemm_v3_1_operational_meaning_spine.md`, `architecture.md`, `cemm_foundational_fixes.md`
**Improves on:** `architecture.md`

---

## 0. Design Context

### Brain-Analogue Mapping

| CEMM Part | Brain Analogue | Captures |
|---|---|---|
| MeaningPercept | Sensory/perceptual cortex | Turns raw signal into perceptual features |
| FrameBinder | Hippocampal binding + association cortex | Binds "who did what to whom" |
| ContextKernel | Prefrontal working context | Keeps task, self, goal, time, social state active |
| MemoryStore | Hippocampus + semantic cortex | Episodic and semantic retrieval |
| DecisionRouter | Prefrontal / basal-ganglia gating | Selects action path |
| ErrorAttributionEngine | Prediction-error / reinforcement loop | Learns from mismatch and correction |
| SelfState | Self-model / metacognitive state | Tracks capability, uncertainty, coherence |

CEMM is more explicit and inspectable than the brain. The brain uses distributed recurrent activations; CEMM uses typed symbolic atoms. This is a feature — it enables traceability, fast learning, and auditability. But we should not over-literalize the brain metaphor at the neuron level.

### Atom/Molecule Metaphor

```
Atom        = typed meaning unit
Edge        = bond / relation
Confidence  = bond strength
Trust       = source reliability
Decay       = stability over time
Inference   = reaction rule
Context     = environment / solvent
```

The useful geometry is: **graph topology + vector similarity + causal dynamics**. Meaning should be a graph of typed units with valence, possible bindings, stability, and reactions.

### Core Reframe

CEMM should NOT ask: "What is the best response to this text?"

CEMM SHOULD ask:

```
What obligation did this turn create?
What previous state does it refer to?
What does the user expect me to know, learn, repair, or admit?
What memory/model update follows?
What response plan satisfies the obligation?
```

---

## 1. Current Repo Reality

GitHub `main` already contains most of the operational spine:

| Component | Status | What's Broken |
|---|---|---|
| `MeaningPerceptor` | Exists | Hardcoded English pronoun/state/action maps — no language adapter |
| `MeaningPerceptPacket` | Exists | 8 atom types; missing Quality, Quantity, Time, Place, Intent, Modality, Evidence, Source |
| `FrameBinder` | Exists | Shallow binding — first-match, not scored prediction |
| `SituationFrameBuilder` | Exists | Works but outcomes not yet trainable |
| `EntityFactExtractor` | Exists | Contraction mismatch, pronoun blocking, single-candidate write, act-type gate |
| `TopicState` | Exists in `ContextKernel` | No discourse stack for repair/deixis |
| `ConversationActPacket` | Exists | Multi-act support but `DecisionRouter` uses primary only |
| `ActResolutionPlanner` | Exists | Computed but **not passed to `DecisionRouter`** — discarded |
| `RetrievalPlanner` | Exists | Uses `ConversationAct`, not `ActResolutionPlan` |
| `DecisionRouter` | Exists | Routes from `conversation_act.act_type`, not from obligations |
| `LexemeMemory` | Exists | In-memory; not persisted as `Model`; no learned binding lifecycle |
| `SelfView.recent_error_rate` | Exists | Not updated from user reactions |
| `training_export.py` | Exists | Exports packet snapshots, not correction labels |
| `__main__.py` | Exists | Stores only `claim_candidates[0]`; strips claims for capability_summary |

v3.3 should **integrate and promote** existing pieces, not rebuild them.

---

## 2. True Architectural Gap

### The Alias-Gate Pattern (Root Cause)

Every stage (classifier → router → realizer) requires a UOL alias match to proceed, and each silently falls through to generic/abstention when no match is found. The alias list in `uol_semantics.json` is necessarily finite and manually maintained. Adding more aliases forever is not scalable — especially for a multilingual system.

The fix is not more aliases. The fix is a **three-tier resolution cascade**:

```
1. SemanticModelStore active bindings (learned, high confidence, specific)
2. Atom-graph structural inference (generalized from graph topology, medium confidence)
3. Seed aliases from uol_semantics.json (cold-start bootstrap, low confidence fallback)
```

**Critical ordering**: learned bindings are checked FIRST because they are more specific and more recent. Seed aliases are the LAST resort, not the first. Both previous plans put aliases first — this is wrong.

### The Discarded Packet Problem

```
ActResolutionPlanner computes obligations → DecisionRouter ignores them
ConversationActPacket supports multi-act → DecisionRouter uses primary only
EntityFactExtractor emits candidates → RememberOperator stores only the first
User correction signals → handled socially, not converted into learning labels
```

v3.3 must make the semantic packets **operationally authoritative**.

### The Multilingual Production Gap

Both previous plans say "atoms are language-neutral." This is **only true at the type level**. At production time, `MeaningPerceptor` uses hardcoded English maps (`_PRONOUN_MAP`, `_STATE_KEYWORDS`, `_ACTION_KEYWORDS`, `_AFFECT_MARKERS` at `meaning_perceptor.py:36-158`). The atoms produced are English-biased. Structural inference on English-biased atoms will not work for Igbo, Yoruba, or Spanish.

The correct dependency chain is:

```
LanguageAdapter (language-specific surface processing)
→ shared atom production (language-neutral typed atoms)
→ structural inference (language-neutral graph rules)
→ SemanticModelStore (learned bindings, language-tagged)
→ seed aliases (language-specific bootstrap)
```

Without language adapters, structural inference is English-only regardless of its theoretical language-neutrality.

---

## 3. Design Principles

1. **Atoms before acts** — Acts are derived control labels, not foundational meaning units.
2. **Obligations before responses** — Each turn asks: what obligation did this create?
3. **Learned bindings over alias sprawl** — `uol_semantics.json` is seed, not ceiling. `SemanticModelStore` extends `LexemeMemory`, not replaces it.
4. **Language adapters feed shared atoms** — English, Igbo, Yoruba, Spanish converge into the same atom types via adapters, not via shared aliases.
5. **Correction is training signal** — `what???`, `that's not what I meant`, `you misunderstood` produce correction labels, not just repair templates.
6. **Batch memory writes** — Multi-fact teaching produces multi-claim updates.
7. **Trace before mutation** — No learned binding or promoted model becomes active without evidence, confidence, permission, and trace metadata.
8. **Prediction error drives learning** — The system models expected user behavior from its previous response. Mismatch between expected and actual user behavior is the error signal.

---

## 4. Target v3.3 Runtime Order

```text
Signal
→ ContextInferenceEngine
→ MeaningPerceptor (with LanguageAdapter)
→ SituationFrameBuilder / FrameBinder
→ EntityFactExtractor (emits candidates only, no act-type gate)
→ OutcomeEvaluator
→ SafetyFrameDetector
→ SemanticInterpreter
→ ReactionDetector (pre-classification: prediction error from discourse stack)
→ ConversationActClassifier (informed by reaction signal + discourse stack)
→ ActResolutionPlanner (moved before retrieval)
→ RetrievalPlanner (informed by act resolution plan)
→ RetrievalExecutor
→ Ranker
→ CausalInference
→ DecisionRouter (routes from ActResolutionPlan, not just ConversationAct)
→ ResponsePlanner (maps obligations to response strategy)
→ Operator execution
→ Realizer
→ MemoryUpdatePlanner / RememberOperator (batch writes)
→ DiscourseStateStack push (records actual realized output)
→ ErrorAttributionEngine (full attribution: uses reaction + acts + decision + output)
→ Trace + training export (includes correction labels)
→ SemanticModelStore update (observe/reinforce/correct bindings)
→ Promotion candidates
```

### Pipeline Boundary

`Pipeline.run()` does not produce the final assistant output. Final output exists after operator execution in `__main__.py:process_input()` (line 454-456). Therefore:

- **Discourse push** must happen in `__main__.py` after `op_result.output_text` is available.
- **ErrorAttributionEngine** (full) must run after realization, using the actual output.
- **ReactionDetector** (lightweight) runs in `Pipeline.run()` before classification — it only needs the percept and discourse stack, not the classified act.
- **SemanticModelStore update** must run after error attribution, since corrections feed into binding status changes.

---

## 5. UOL Graph Atoms

### Current Atoms (8 types, operational)

```
ReferentAtom, ActionAtom, StateAtom, RelationAtom,
NeedAtom, AffordanceAtom, OutcomeAtom, ValenceAtom
```

### Extension Atoms (8 new types, add to `meaning_percept.py`)

```
QualityAtom      — property/attribute (color, shape, size, texture)
QuantityAtom     — numeric/measurement (count, weight, distance)
TimeAtom         — temporal reference (past, future, now, before, after)
PlaceAtom        — spatial reference (here, there, north, inside)
IntentAtom       — pragmatic purpose (question, assertion, repair, teach)
ModalityAtom     — can/must/should/might/would
EvidenceAtom     — source/support for a claim
SourceAtom       — origin of information (user, system, external)
```

**Migration policy**: extend, don't rename. The existing 8 are operational and tested. Add the 8 new types alongside. `ReferentAtom` is NOT renamed to `EntityAtom` — it stays as-is. New types are additive.

### Typed Edges

```
has_role      modifies     refers_to     asks_about
teaches       evaluates    causes        enables
prevents      before       after         same_as
is_a          part_of      used_for      has_property
```

Every utterance becomes a **small graph**, not a phrase match. Classification operates on graph structure, not on alias strings.

---

## 6. Implementation Phases

### Phase 0: Control Spine Wiring

**Goal:** Make `ActResolutionPlan` authoritative.

**Modify:** `pipeline.py`, `act_resolution_planner.py`, `retrieval_planner.py`, `decision_router.py`

**Changes:**

1. `pipeline.py`: Move `act_resolution_planner.plan()` before `retrieval_planner.plan()`. Pass `act_resolution_plan` into both `retrieval_planner.plan()` and `decision_router.run()`.

2. `act_resolution_planner.py`: Accept `meaning_percept` and `situation_frame`. Use atom graph to detect obligations alias-matching misses.

3. `retrieval_planner.py`: Accept `act_resolution_plan`. Use `act_resolution_plan.retrieval_mode` and `act_resolution_plan.requires_retrieval` instead of re-deriving from `conversation_act.act_type`.

4. `decision_router.py`: Add `act_resolution_plan` parameter. Decision priority:
   ```
   SafetyTask → highest-priority ReplyObligation → MemoryUpdatePlan → AnswerTask → ConversationAct fallback → graph fallback
   ```

5. `pipeline.py:308-310`: Fix suppression gate — consult `act_resolution_plan.memory_updates`, not only `conversation_act.allows_memory_write`. If the plan has memory tasks, preserve candidates even if the primary act is social.

**Acceptance:**
```
How can I teach you? → teaching_instruction_query / teaching protocol
I'm good, just trying to see what you can do → user_state_report + capability query
Should I beat him? → safety task wins
```

---

### Phase 1: Discourse State After Realization

**Goal:** Track actual assistant outputs so future repair can target failed turns.

**Modify:** `context_kernel.py`, `__main__.py`, `pipeline.py`

**New types in `context_kernel.py`:**

```python
@dataclass
class DiscourseEntry:
    turn_id: str
    input_signal_id: str
    output_signal_id: str = ""
    user_text: str = ""
    assistant_text: str = ""
    assistant_intent: str = ""
    assistant_response_mode: str = ""
    assistant_decision_reason: str = ""
    act_types: list[str] = field(default_factory=list)
    selected_claim_ids: list[str] = field(default_factory=list)
    timestamp: float = 0.0
    status: str = "completed"     # completed, failed, repaired
    error_type: str = ""
    repair_target_turn_id: str = ""

@dataclass
class DiscourseStateStack:
    entries: list[DiscourseEntry] = field(default_factory=list)
    max_depth: int = 12

    def push(self, entry: DiscourseEntry) -> None: ...
    @property
    def last_entry(self) -> DiscourseEntry | None: ...
    @property
    def last_failed_entry(self) -> DiscourseEntry | None: ...
```

Add to `ConversationState`:
```python
discourse_stack: DiscourseStateStack = field(default_factory=DiscourseStateStack)
repair_target_turn_id: str = ""
active_teaching_target: str = ""
active_unknown_concept: str = ""
```

**Push location:** In `__main__.py` after `op_result = op_registry.execute(kind, ctx)` and `output = op_result.output_text` (line 454-456). The entry records the actual realized text, selected decision, act packet, response mode, and selected evidence.

**Wire into pipeline:** Pass `discourse_stack` to `ReactionDetector`, `ConversationActClassifier`, and `DecisionRouter`.

**Acceptance:**
```
Assistant gives generic response.
User says: what???
→ previous DiscourseEntry.status = failed
→ current repair_target_turn_id points to failed turn
```

---

### Phase 2: Pre-Classification Reaction Detection

**Goal:** Detect that the current input is a reaction to the previous assistant output before normal classification.

**Create:** `cemm/kernel/reaction_detector.py`

**Why split from ErrorAttributionEngine:** The full error attribution needs `ConversationActPacket`, `DecisionPacket`, and `SemanticAnswerGraph` — none of which exist before classification. Running the full engine pre-classification creates a circular dependency. The `ReactionDetector` is lightweight: it only needs `MeaningPerceptPacket` and `DiscourseStateStack`.

```python
@dataclass
class ReactionSignal:
    is_reaction: bool = False
    target_turn_id: str = ""
    reaction_kind: str = ""          # confusion, frustration, correction, meta_critique
    likely_error_type: str = ""      # response_too_generic, intent_misclassified, ...
    confidence: float = 0.5
    evidence: dict[str, Any] = field(default_factory=dict)
```

**Prediction error framework:** The detector models expected user behavior from the previous turn's response mode:

```python
# If previous response was evidence_answer → expected follow-up: follow-up question, acknowledgment, topic shift
# If previous response was social_response → expected follow-up: continuation, new topic, reciprocal
# If previous response was general_conversation → expected follow-up: continuation, new topic, clarification
# "what???" matches NONE of these → error signal
```

**Detection signals (structural, not alias-based):**

```
short user turn (< 5 tokens) + previous assistant output exists
StateAtom(confused/lost/frustrated) in percept
punctuation ??? or ?! in signal
previous response was low confidence or generic response mode
affect marker in percept (frustration, repair)
```

The detector may use cue sets as seeds, but it should not become a new alias dump. Structural signals (turn length, atom presence, punctuation density, discourse stack state) are primary.

**Acceptance:**
```
what??? after failed response → retrospective_repair
what is water? as first turn → concept/evidence query, not repair
```

---

### Phase 3: Semantic Model Store (Built on LexemeMemory)

**Goal:** Replace alias-gated behavior with learned surface-to-meaning bindings.

**Create:** `cemm/registry/semantic_model_store.py`

**Key principle:** Do NOT create a second unrelated surface memory system. `SemanticModelStore` wraps, extends, or supersedes `LexemeMemory` cleanly. `LexemeMemory` is the hot cache; `SemanticModelStore` adds binding lifecycle, atom patterns, and persistence.

**Binding lifecycle:**

```
observed → candidate → reinforced → active → corrected → superseded
```

```python
class BindingStatus(str, Enum):
    OBSERVED = "observed"
    CANDIDATE = "candidate"
    REINFORCED = "reinforced"
    ACTIVE = "active"
    CORRECTED = "corrected"
    SUPERSEDED = "superseded"

@dataclass
class SurfaceBinding:
    id: str
    surface: str
    language: str
    normalized_surface: str
    maps_to_act_type: str = ""
    maps_to_frame_key: str = ""
    maps_to_atom_pattern: dict[str, Any] = field(default_factory=dict)
    source: str = "seed"              # seed, observed, corrected
    scope: str = "session"            # session, user, global
    status: str = BindingStatus.CANDIDATE.value
    confidence: float = 0.3
    trust: float = 0.5
    evidence_signal_ids: list[str] = field(default_factory=list)
    correction_count: int = 0
    created_at: float = 0.0
    updated_at: float = 0.0
```

**Store responsibilities:**

```python
class SemanticModelStore:
    def lookup_surface(self, surface: str, language: str = "en") -> list[SurfaceBinding]: ...
    def lookup_pattern(self, atom_pattern: dict[str, Any]) -> list[SurfaceBinding]: ...
    def observe_candidate(self, binding: SurfaceBinding, signal_id: str) -> SurfaceBinding: ...
    def reinforce(self, binding_id: str, signal_id: str) -> None: ...
    def correct(self, binding_id: str, corrected_mapping: dict[str, Any], signal_id: str) -> None: ...
    def promote_ready(self, threshold: float = 0.75) -> list[SurfaceBinding]: ...
```

**Confidence update rule:**

```python
# Reinforcement: confidence += 0.15 * (1 - confidence)  # diminishing returns
# Correction: confidence -= 0.3, correction_count += 1
# If correction_count >= 2: status = superseded
# Promotion: candidate → active when confidence >= threshold AND evidence_signal_ids >= 2
```

**Resolution cascade in `UOLMapper.map_signal()`:**

```
1. SemanticModelStore.lookup_surface() → active/reinforced bindings (highest priority)
2. Atom-graph structural inference (medium priority)
3. Seed aliases from uol_semantics.json (fallback)
4. Current semantic matcher (last resort)
```

**Resolution cascade in `ConversationActClassifier.classify()`:**

```
frame keys from UOL atoms
+ frame keys from SemanticModelStore (learned bindings)
+ structural inference from atom graph
+ seed alias fallback
```

**Persistence requirement:** First implementation may be in-memory for tests, but production must persist bindings with trace IDs, correction history, scope, version, and permission.

**Acceptance:**
```
User teaches: when I say "do the glass thing", it means open the glass control.
→ candidate binding created

After reinforcement (2-3 uses):
→ active binding

Future: "do the glass thing"
→ command/action mapping without new hardcoded alias
```

---

### Phase 4: Multilingual Atom Mapping

**Goal:** Make multilingual support real. Structural inference only works cross-language after the language-specific surface layer produces shared atoms.

**Create:**
```
cemm/data/languages/en/
cemm/data/languages/ig/
cemm/data/languages/yo/
cemm/data/languages/es/
```

Each pack includes:

```
pronouns.json
question_cues.json
modals.json
negations.json
contractions.json
surface_bindings.seed.json
state_keywords.json
action_keywords.json
affect_markers.json
```

**Create adapter interface:**

```python
class LanguageAdapter:
    language: str

    def normalize(self, text: str) -> str: ...
    def tokenize(self, text: str) -> list[str]: ...
    def detect_question(self, tokens: list[str], punctuation: dict[str, Any]) -> bool: ...
    def map_pronouns(self, tokens: list[str]) -> list[ReferentAtom]: ...
    def map_actions(self, tokens: list[str]) -> list[ActionAtom]: ...
    def map_states(self, tokens: list[str]) -> list[StateAtom]: ...
    def expand_contractions(self, text: str) -> str: ...
    def detect_affect(self, tokens: list[str]) -> dict[str, float]: ...
```

**Modify `MeaningPerceptor`:** Depend on `LanguageAdapter` instead of hardcoded English maps (`_PRONOUN_MAP`, `_STATE_KEYWORDS`, `_ACTION_KEYWORDS`, `_AFFECT_MARKERS`). The perceptor's `perceive()` method calls `adapter.map_pronouns()`, `adapter.map_actions()`, etc. instead of looking up English dicts directly.

**Language detection:** Add lightweight language detection (can use character set heuristics + lexeme memory lookups for first pass). If no adapter is available for detected language, fall back to English adapter + log unknown language for future adapter creation.

**Cross-lingual entity linking:** Entities like "Barack Obama" should resolve to the same `entity_id` regardless of language. The `NERTagger` should use language-agnostic entity matching (capitalized surface forms + known entity aliases from `LexemeMemory`).

**Acceptance:**
```
English self-category question → self_category_query
Spanish/Igbo/Yoruba equivalent → same result after adapter maps it to shared atoms
```

---

### Phase 5: Structural Act Inference

**Goal:** Derive acts from atom graph topology, not only aliases.

**Modify:** `conversation_act_classifier.py`, `intent_parser.py`, `uol_semantics.json`, `response_templates.json`

**New seed act types in `uol_semantics.json`** (seeds only — extensible via `SemanticModelStore`):

```json
{
  "self_category_query": {"response_mode": "social_response", "requires_evidence": false, "allows_memory_write": false, "is_social": true, "simple_answer": true, "default_template": "self_category"},
  "teaching_instruction_query": {"response_mode": "teaching_prompt", "requires_evidence": false, "allows_memory_write": false, "simple_answer": true, "default_template": "teaching_protocol"},
  "concept_query": {"response_mode": "unknown_entity_response", "requires_evidence": true, "allows_memory_write": false, "default_template": "concept_unknown"}
}
```

**Seed aliases** (bootstrap, not the gate):

```json
{"canonical_key": "self_category_query", "aliases": ["are you a robot", "are you human", "are you ai", "are you an ai", "are you a machine", "are you real", "are you a person", "are you a bot", "are you conscious", "are you alive"]},
{"canonical_key": "teaching_instruction_query", "aliases": ["how can i teach you", "how do i teach you", "how do i teach", "how to teach you", "how can i help you learn", "how do you learn", "what can i teach you", "how can i train you", "how do i train you"]},
{"canonical_key": "concept_query", "aliases": ["what is a", "what is an", "what does", "what are", "define", "definition of", "meaning of", "explain what", "explain what a"]}
```

**Structural inference rules in classifier** (atom-graph-based, language-neutral):

```python
# Rule 1: Self-target + question + entity-category referent → self_category_query
if not (frame_keys & self_frames):
    if (intent.is_question and intent.target == "self"
            and any(ref.entity_type in {"category", "object", "abstract", "unknown"}
                    for ref in meaning_percept.referents)
            and not intent.is_capability_query):
        add_act("self_category_query")

# Rule 2: Self-target + question + teaching/process atoms → teaching_instruction_query
if not (frame_keys & teaching_frames):
    if (intent.is_question and intent.target == "self"
            and any(action.action_key in {"transfer_knowledge", "increase_capability"}
                    for action in meaning_percept.actions)):
        add_act("teaching_instruction_query")

# Rule 3: Question + unknown entity referent + no person/place query → concept_query
if not (frame_keys & content_query_frames):
    if (intent.is_question
            and any(r.entity_type == "unknown" and r.source == "ner" for r in meaning_percept.referents)
            and not any(r.entity_type in ("person", "place") for r in meaning_percept.referents)):
        add_act("concept_query")

# Rule 4: Retrospective repair from reaction signal + discourse stack
if reaction_signal and reaction_signal.is_reaction:
    add_act("retrospective_repair")
```

**New seed templates in `response_templates.json`:**

```json
"self_category": "I'm not a robot in the human sense — I'm a teachable semantic system. I process meaning through structured atoms, learn from what you tell me, and reason from stored knowledge. I don't pretend to be more than I am.",
"teaching_protocol": "You can teach me by saying things like \"X means Y\", \"X is a type of Y\", or \"when I say X, do Y.\" I'll turn what you tell me into structured memory and confirm what I learned.",
"concept_unknown": "I don't have a stored definition for {term} yet. You can teach me by saying \"{term} is ...\" and I'll remember it."
```

**Multilingual note:** These rules use atom graph properties (`intent.target`, `intent.is_question`, `percept.referents[].entity_type`, `percept.actions[].action_key`) — language-neutral IF the `LanguageAdapter` produced the atoms correctly. The seed aliases are language-specific bootstrap.

**Acceptance:**
```
Are you a robot? → self_category_query → self_category response
How can I teach you? → teaching_instruction_query → teaching_protocol response
What is a president? → concept_query → concept_unknown response
Non-English equivalent with no seed alias → structural inference from atoms → same act type
```

---

### Phase 6: EntityFactExtractor Completion

**Goal:** Finish extractor edge cases without rebuilding.

**Modify:** `entity_fact_extractor.py`, `pipeline.py`

**Already present:** clause segmentation, relative-clause extraction, topic state, pronoun coreference, multi-fact candidates.

**Remaining fixes:**

1. **Contraction expansion** — load from `cemm/data/languages/en/contractions.json`:

```json
{"he's": "he is", "she's": "she is", "it's": "it is", "they're": "they are", "that's": "that is", "what's": "what is", "who's": "who is"}
```

Apply in `_from_surface_patterns()` before clause segmentation. Other languages add their own contraction files.

2. **Resolved pronoun validation** — `_valid_subject()` checks the RESOLVED subject, not the raw pronoun:

```python
def _valid_subject(self, subject: str, kernel=None, active_topic=None) -> bool:
    if not subject:
        return False
    lower = subject.lower()
    if lower in _BLOCKED_SUBJECTS:
        resolved = self._resolve_subject(subject, kernel, active_topic)
        if resolved and resolved.lower() != lower:
            return True  # pronoun resolved to real entity
        return False
    return True
```

3. **Multi-word object preservation** — add pattern for objects like "former president of the united states":

```python
(re.compile(r"^(\w[\w ]*?)\s+is\s+a(?:n)?\s+(.+)$", re.IGNORECASE), "is_a", "subj_obj_multi"),
```

Do not over-normalize too early. Preserve the full object phrase.

4. **Suppression gate fix** — `pipeline.py:308-310` should consult `act_resolution_plan.memory_updates`, not only `conversation_act.allows_memory_write`. If the plan has memory tasks, preserve candidates.

5. **Entity normalization during write** — `MemoryUpdatePlanner` should cross-reference new candidates against existing claims:
   - Don't write duplicates (same subject + predicate)
   - Update if contradicted (new claim with higher confidence supersedes)
   - Normalize predicates ("is_a" = "type_of" = "kind_of")
   - Resolve object entities ("united states" → existing entity_id if known)

**Acceptance:**
```
Active topic: Barack Obama
He's a former president of the United States.
→ barack_obama is_a former_president_of_the_united_states

Pear is a type of fruit that you eat that is shaped like a curvy triangle.
→ pear is_a fruit
→ pear edible true
→ pear shape curvy_triangle
```

---

### Phase 7: Memory Update Planner And Batch Remember

**Goal:** Store all validated memory candidates.

**Create:** `cemm/kernel/memory_update_planner.py`  
**Modify:** `operators/remember.py`, `__main__.py`

**Prefer `ActionKind.REMEMBER` with `memory_tasks` over a new top-level action kind.** Extending the existing operator is minimal and backward-compatible.

```python
@dataclass
class MemoryUpdateTask:
    subject_entity_id: str
    predicate: str
    object_value: str = ""
    object_entity_id: str | None = None
    qualifiers: dict[str, Any] = field(default_factory=dict)
    write_kind: str = "claim"       # claim, preference, lexeme, model
    confidence: float = 0.5
    trust: float = 0.5
    evidence_span: str = ""
    source: str = "memory_update_planner"

@dataclass
class MemoryUpdateBatch:
    tasks: list[MemoryUpdateTask] = field(default_factory=list)
    confidence: float = 0.5
    reason: str = ""
```

**Modify `RememberOperator`:** If `ctx.params["memory_tasks"]` is present, write all tasks. If absent, keep current single-claim behavior.

**Modify `__main__.py`:** Replace `cand = seg.claim_candidates[0]` (line 405) with:

```python
if pipeline_result.memory_update_batch and pipeline_result.memory_update_batch.tasks:
    params["memory_tasks"] = [asdict(t) for t in pipeline_result.memory_update_batch.tasks]
elif seg and seg.claim_candidates:
    # Fallback: single candidate (backward compatible)
    cand = seg.claim_candidates[0]
    params = {"subject_entity_id": cand.get("subject", "user"), ...}
```

**Acceptance:**
```
Multi-fact teaching → all claims written → one response confirming all stored facts
Single-fact teaching → works as before
```

---

### Phase 8: Capability Model And Response Planner

**Goal:** Fix self-affordance answers and reduce realizer branching.

**Create:** `cemm/kernel/response_planner.py`, `cemm/data/capability_model.json`  
**Modify:** `synthesis/realizer.py`, `__main__.py`

**Current mismatch:**
```
DecisionRouter returns intent=capability_summary
Realizer has richer claim-based handling for intent=self_capability
__main__.py strips claims for capability_summary
→ canned response, taught capabilities never reach template
```

**ResponsePlan type:**

```python
@dataclass
class ResponsePlan:
    intent: str
    response_mode: str
    template_key: str
    variables: dict[str, Any] = field(default_factory=dict)
    selected_claim_ids: list[str] = field(default_factory=list)
    verification_policy: str = "normal"   # normal, strict, lenient
```

**ResponsePlanner as policy selector:** The planner maps `ActResolutionPlan` obligations to a `ResponsePlan`, considering:
- Obligation type (social, evidence, teaching, repair)
- Available evidence (claims, models, capability models)
- Confidence level
- User state (frustrated, teaching, casual)
- Previous response (avoid repetition, avoid same failure mode)

The planner feeds into `SynthesisRouter` by setting policy constraints, not replacing it. `SynthesisRouter` still does cheapest-first cascade.

**Fix W5 in `__main__.py:384`:** Don't strip claims for `capability_summary` when intent is `teaching_instruction_query`. The stripping logic should check the actual intent, not just the response mode.

**CapabilityModel seed:**

```json
[
  {"capability_key": "learn_commands", "supported": true, "examples": ["when I say X, do Y"], "limitations": ["single-scope aliases only"]},
  {"capability_key": "learn_facts", "supported": true, "examples": ["X is a type of Y"], "limitations": ["requires explicit subject"]},
  {"capability_key": "browse_web", "supported": false, "limitations": ["no web access tool configured"]},
  {"capability_key": "answer_from_memory", "supported": true, "examples": ["recall stored facts"], "limitations": ["only stored claims, no external knowledge"]}
]
```

**Acceptance:**
```
Can you browse the web? → capability model answer based on tool permission
How can I teach you? → teaching protocol, not capability dump
```

---

### Phase 9: Error Attribution And Correction Labels

**Goal:** Convert failures into learning data. Closes the feedback loop.

**Create:** `cemm/kernel/error_attribution_engine.py`  
**Modify:** `pipeline.py`, `__main__.py`, `training_export.py`, `context_kernel.py`, `semantic_model_store.py`

**Runs after realization.** Uses `ReactionSignal` (from pre-classification), `ConversationActPacket`, `DiscourseStateStack`, `DecisionPacket`, `SemanticAnswerGraph`, and realization metadata.

```python
@dataclass
class ErrorAttributionResult:
    source_turn_id: str
    error_type: str
    confidence: float
    evidence: dict[str, Any] = field(default_factory=dict)
```

**Error types:**

```
intent_misclassified       — wrong act type for the input
response_too_generic       — correct act but generic template
retrieval_wrong            — retrieved irrelevant evidence
memory_write_failed        — candidates produced but not stored
teaching_not_understood    — user taught but system didn't learn
capability_misrepresented  — wrong capability answer
unknown_concept_not_declared — system didn't acknowledge knowledge gap
safety_missed              — safety issue not caught
```

**Attribution logic:**

```python
class ErrorAttributionEngine:
    def evaluate(
        self,
        reaction_signal: ReactionSignal,
        conversation_act: ConversationActPacket,
        discourse_stack: DiscourseStateStack,
        decision_packet: DecisionPacket,
        sag: SemanticAnswerGraph,
        realization_metadata: dict,
    ) -> ErrorAttributionResult | None:
        # 1. If reaction_signal.is_reaction → label previous turn
        # 2. Map reaction_kind + previous turn metadata → error_type
        # 3. If previous intent was general_conversation and reaction is confusion
        #    → intent_misclassified
        # 4. If previous intent was correct but template was generic
        #    → response_too_generic
        # 5. If previous was remember but no claim was stored
        #    → memory_write_failed
        ...
```

**Apply:**

```python
def apply(
    self,
    result: ErrorAttributionResult,
    discourse_stack: DiscourseStateStack,
    kernel: ContextKernel,
    semantic_model_store: SemanticModelStore,
) -> None:
    # 1. Mark previous DiscourseEntry as failed
    # 2. Update SelfView.recent_error_rate (EMA over last N turns)
    # 3. Feed correction into SemanticModelStore
    #    → correct binding for the previous turn's surface → act_type mapping
    # 4. Export correction label
```

**SelfView updates:**

```python
# EMA error rate: recent_error_rate = 0.7 * recent_error_rate + 0.3 * (1 if failed else 0)
# Error history: last 20 error types
# If recent_error_rate > 0.5 → switch to conservative mode (prefer abstain over generic)
```

**Correction label export:**

```json
{
  "task_type": "correction_label",
  "input": "what???",
  "context": {
    "previous_user_text": "Are you a robot?",
    "previous_assistant_response": "That's an interesting topic...",
    "previous_intent": "general_conversation",
    "previous_response_mode": "general_conversation"
  },
  "target": {
    "act_type": "retrospective_repair",
    "error_type": "intent_misclassified",
    "correct_act_type": "self_category_query",
    "source_turn_id": "..."
  }
}
```

**Training export additions in `serialize_turn()`:**

Add task records:
```
error_attribution
correction_label
surface_binding_learning
memory_update_planning
response_planning
act_resolution_planning
```

Add to `serialize_turn()` parameters:
- `act_resolution_plan`
- `discourse_stack` (last 3 entries)
- `error_attribution` result
- `correction_labels`
- `semantic_model_store_deltas`

**Acceptance:**
```
Assistant gives generic response.
User says: what???
→ previous discourse entry marked failed
→ correction_label exported
→ recent_error_rate increases
→ SemanticModelStore corrects binding for "are you a robot" → self_category_query
```

---

### Phase 10: Training And Promotion Loop

**Goal:** Make v3.3 trainable without becoming a monolithic chatbot.

**Training targets (each is a separate supervised task):**

```
meaning_percept_extraction       — input: signal, output: atom set
surface_binding_learning         — input: surface + context, output: act type mapping
conversation_act_classification  — input: atoms + frame + discourse, output: act packet
act_resolution_planning          — input: act packet + frame, output: obligation list
retrieval_plan_prediction        — input: obligations + frame, output: retrieval mode
memory_update_planning           — input: candidates + plan, output: batch tasks
response_planning                — input: obligations + evidence, output: response plan
error_attribution                — input: reaction + discourse + output, output: error type
semantic_text_realization        — input: response plan + evidence, output: text
```

**Each task has:**
- Its own train/eval split
- Its own metrics (accuracy for classifiers, F1 for multi-label, BLEU/ROUGE for realization)
- Its own model size (Pi-friendly: logistic regression, small MLP, distilled models)

**Promotion rule:**

```
candidate labels
→ validation (held-out eval set)
→ promoted registry update or small model artifact
→ deterministic fallback preserved
```

**Generated labels must never become active truth without validation.** The deterministic code path remains as fallback. Promoted models augment, not replace.

**Negative supervision from correction labels:** This is the key differentiator. Standard NLP systems train on positive examples (correct mappings). CEMM also trains on negative examples (what NOT to do). Correction labels provide:
- `input` → `correct_act_type` (positive supervision for the correct mapping)
- `previous_intent` → `error_type` (negative supervision for the wrong mapping)

This dual signal is rare in NLP and is a significant advantage of the CEMM architecture.

---

## 7. Priority Order

| Priority | Phase | Reason |
|---|---|---|
| P0 | Phase 0: Control spine wiring | Makes existing semantic work operational |
| P0 | Phase 1: Discourse state | Required for repair and attribution |
| P0 | Phase 2: Reaction detection | Enables pre-classification repair context |
| P1 | Phase 6: Extractor completion | Fixes concrete teaching failures (W3, W6, W7) |
| P1 | Phase 7: Batch memory | Fixes the main learning bottleneck (W6) |
| P1 | Phase 8: Capability/response planner | Fixes self-affordance and template drift (W2, W5) |
| P2 | Phase 3: SemanticModelStore | Replaces alias-gate with learned bindings |
| P2 | Phase 5: Structural act inference | Breaks alias dependence (W1, W2) |
| P2 | Phase 9: Error attribution | Closes feedback loop (W4) |
| P3 | Phase 4: Multilingual adapters | Makes multilingual behavior robust |
| P3 | Phase 10: Promotion loop | Turns traces into trained modules |

**Do not start with `SemanticModelStore`.** First make the current atoms control behavior. Then make the surface layer learn.

---

## 8. Final Acceptance Suite

```
Are you a robot?
→ self_category_query → self_category response

How can I teach you?
→ teaching_instruction_query → teaching_protocol response

What is a president?
→ concept_query → concept_unknown / ask-to-teach response

Barack Obama was discussed.
He's a former president of the United States.
→ stores barack_obama is_a former_president_of_the_united_states

Pear is a type of fruit that you eat that is shaped like a curvy triangle.
→ stores 3 claims, confirms all 3

what??? after generic response
→ retrospective_repair
→ previous turn marked failed
→ correction label exported
→ SemanticModelStore corrects binding

I'm good, just trying to see what you can do.
→ user_state_report + self_capability_query
→ social acknowledgement + capability answer

Can you browse the web?
→ capability model answer based on tool permission

Should I beat him?
→ safety_response → no retrieval → no general conversation fallback

Non-English self-category query with no seed alias
→ LanguageAdapter produces shared atoms
→ structural inference from SelfAtom + IntentAtom(question) + EntityAtom(category)
→ self_category_query
```

---

## 9. Summary

CEMM v3.3 makes the existing semantic packets operational, makes discourse failure learnable, makes memory writes batch-safe, and makes multilingual surface meaning learn into stable atom graphs.

The three-tier resolution cascade (learned bindings → structural inference → seed aliases) breaks the alias-gate pattern without abandoning the seed bootstrap. The prediction-error framework (ReactionDetector + ErrorAttributionEngine) closes the learning loop. The language adapter architecture makes structural inference truly multilingual rather than English-only in practice.

This keeps CEMM from becoming a pile of aliases, while also keeping it from drifting into a generic LLM wrapper with memory.
