# Sentient NLG Pipeline Design

## Problem

Current NLG uses static templates (`response_templates.json`) filled by `SemanticRealizer.realize()` via `str.format()`. Limitations: not language-agnostic, not primitive-based, not sentient-aware, single-output, not learnable.

## Solution

Candidate generation + ranking + selection pipeline replacing templates entirely.

## Data Flow

```
RelationFrame + SlotFills + ObligationFrame
  -> ContentExtractor (agnostic) -> semantic_roles
  -> GoalFramer (agnostic) -> framing_roles + variants
  -> StyleAnnotator (agnostic) -> StyleProfile(4 axes)
  -> CandidateExpander (agnostic) -> 1..N NLGFrames
  -> [per candidate] PronounResolver -> PredicateSelector -> Morphologizer -> Linearizer (en)
  -> PatternInjector (en) -> adds learned pattern candidates
  -> Ranker (agnostic) -> scores all candidates
  -> Selector (agnostic) -> picks best + emits internal actions
  -> surface text + actions
```

## Stages (each a pure function)

1. **ContentExtractor**: RelationFrame + SlotFills -> semantic_roles {agent, patient, predicate, dimension, polarity}
2. **GoalFramer**: goal_type + roles -> framing_roles {speaker, listener, source, intent} + framing_variant (direct, echo, follow_up, hedge, minimal, deflect)
3. **StyleAnnotator**: user_state + self_state -> StyleProfile(terseness, formality, warmth, detail)
4. **CandidateExpander**: framing variants x constructions -> NLGFrame list (count controlled by style)
5. **PronounResolver** (en): framing_roles -> pronoun choices (I/you/he/she, my/your)
6. **PredicateSelector** (en): relation_key + goal + style -> verb form (is, has, causes, got it, can't)
7. **Morphologizer** (en): agreement, articles, plurals, contractions (terseness > 0.6 -> contract)
8. **Linearizer** (en): word order -> surface text + punctuation + capitalization
9. **PatternInjector** (en): retrieves learned patterns from chat history as additional candidates
10. **Ranker**: scores each candidate (style_match 0.3, context_fit 0.2, fluency 0.2, safety 0.2, learned_weight 0.1)
11. **Selector**: picks best by score, time_pressure sensitivity, tie-breaking randomness, emits internal actions

## Composable Goal Types

6 primitives: `assert`, `query`, `acknowledge`, `negate`, `refuse`, `instruct`

Complex goals = primitive + style override. E.g. emotional_acknowledge = acknowledge + warmth=0.8, terseness=0.3.

Obligation mapping: answer_* -> assert, store_patch -> acknowledge, ask_clarification -> query, abstain_policy -> negate, social_reply -> acknowledge, exit -> acknowledge (terseness=0.9).

## Core Types

```python
@dataclass
class StyleProfile:
    terseness: float = 0.5    # 0=verbose, 1=terse
    formality: float = 0.5    # 0=casual, 1=formal
    warmth: float = 0.5       # 0=cold, 1=warm
    detail: float = 0.5       # 0=minimal, 1=exhaustive

@dataclass
class NLGFrame:
    goal_type: str
    relation_key: str
    semantic_roles: dict[str, str]
    framing_roles: dict[str, str]
    framing_variant: str
    style: StyleProfile
    pronouns: dict[str, str]
    predicate_form: str
    tokens: list[str]
    text: str
    source: str = "grammar"  # or "learned_pattern"
    confidence: float = 0.5
    features: dict[str, Any] = field(default_factory=dict)

@dataclass
class NLGResult:
    text: str
    actions: list[dict[str, Any]]
    selected_frame: NLGFrame
    all_candidates: list[NLGFrame]
```

## Module Structure

```
cemm/nlg/
  __init__.py
  nlg_frame.py          # NLGFrame, StyleProfile, NLGResult
  nlg_pipeline.py       # NLGPipeline orchestrator
  goal_mapper.py        # obligation_to_goal()
  transformers/
    content_extractor.py
    goal_framer.py
    style_annotator.py
    candidate_expander.py
    pronoun_resolver.py
    predicate_selector.py
    morphologizer.py
    linearizer.py
    pattern_injector.py
    ranker.py
    selector.py
  languages/
    en_rules.py         # English grammar rules
  data/
    learned_patterns.json
```

## Integration

Replaces `SemanticRealizer.realize()` in `semantic_kernel_runtime.py`:

```python
nlg_result = self._nlg_pipeline.generate(
    goal_type=obligation_to_goal(obligation_frame),
    relation_frames=relation_frames,
    slot_fills=answer_binding.slot_fills,
    obligation=obligation_frame,
    user_state=self._session_store.user_state,
    self_state=self._session_store.self_state,
)
result.realized_output = nlg_result.text
result.internal_actions = nlg_result.actions
```

## Removed

- `cemm/kernel/semantic_realizer.py`
- `cemm/data/response_templates.json`
- `_template_for_obligation()` in `semantic_query_engine.py`
- `_TEMPLATE_SLOT_KINDS`, `_ABSTENTION_REASONS`, `_TEMPLATE_FALLBACK`
- `template_key` field on `RealizationContract`

## Sentient Adaptation

Style axes driven by:
- **User urgency** (abbreviations, short utterances) -> high terseness
- **User formality** (long structured sentences) -> high formality
- **Self temperature** (insulted twice) -> low warmth, high terseness until user warms up
- **Conversation context** (teaching) -> high formality + detail

Selector can emit internal actions (e.g. `set_language("fr")` when user says they're from France).

## Learned Patterns

Stored as `(goal_type, style_signature) -> [surface_patterns]`. Seeded initially, grows from successful interactions. Injected as additional candidates alongside grammar-composed ones.
