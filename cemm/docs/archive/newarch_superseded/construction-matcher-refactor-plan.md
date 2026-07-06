# ConstructionMatcher Refactor Plan

## Problem

`MeaningPerceptor` (1400 lines) fuses three architecturally distinct steps —
**Segment**, **ConstructionMatch**, and **Atomize** — into one monolithic
English-specific class.  It uses ~15 hardcoded Python sets/dicts for intent
detection (`_QUESTION_STARTERS`, `_COMMAND_CUES`, `_SOCIAL_PHRASE_ALIASES`,
`_EXIT_CUES`, `_greeting_forms`, etc.) that duplicate data already in
`uol_semantics.json`.

The architecture (§5, §8, §18, §19.4) requires:
- A separate **ConstructionMatch** step using `ConstructionAtom` operators
- Constructions that propose graph patches, not regex rules
- A `cemm/kernel/construction_matcher.py` module (listed in §18, never built)
- Linguistic data in JSON, loaded dynamically — not hardcoded in Python

## Root Cause

`ConstructionLattice._seed()` has 6 crude entries that match on `group_type`
strings ("teaching", "question", "command").  No real surface-pattern matching
exists.  `MeaningPerceptor` compensates by doing English-specific intent
classification itself, bypassing the construction lattice entirely.

Meanwhile `uol_semantics.json` already has 40+ frame entries with aliases
(e.g. `self_identity_query` → `["who are you", "what are you", ...]`), but
these are only used by `ConversationActClassifier` for fuzzy matching —
**not** by the perceptor that actually determines intent.

## Solution: 4 Phases

### Phase 1 — `ConstructionMatcher` module (new file)

**File:** `cemm/kernel/construction_matcher.py`

**Purpose:** Match `ConstructionAtom` form-signatures against surface text
and meaning groups.  This is the missing §5.3 ConstructionMatch step.

**Design:**

```python
class ConstructionMatcher:
    """Match construction form-signatures against surface text.

    Seeded from uol_semantics.json frame aliases.  Each frame entry
    becomes a ConstructionAtom whose form_signature.surface_pattern
    is an alias phrase.  Matching is token-based n-gram, not regex.
    """
    def __init__(self, construction_lattice: ConstructionLattice) -> None:
        self._lattice = construction_lattice
        self._seed_from_uol_semantics()

    def _seed_from_uol_semantics(self) -> None:
        """Load frame aliases from uol_semantics.json and register them
        as ConstructionAtom entries in the lattice."""
        # For each entry in FRAME_ALIASES:
        #   Skip entries with cue_type (grammatical_* entries are cue sets,
        #     not constructions)
        #   Create ConstructionAtom with:
        #     construction_id = canonical_key
        #     form_signature.surface_pattern = each alias
        #     pragmatic_signature.expected_acts = [act_type]
        #     port_constraints derived from act_type
        #     confidence = intensity
        #   Register in lattice

    def match_group(self, group: MeaningGroup, packet: MeaningPerceptPacket) -> ConstructionMatch | None:
        """Find the best construction match for a meaning group.

        1. Normalize group surface to tokens
        2. For each construction in the lattice:
           a. Check if construction's surface_pattern tokens appear as
              a contiguous subsequence in the group tokens
           b. Score by coverage (matched_tokens / group_tokens)
              and construction confidence
        3. Return highest-scoring match above threshold
        """
```

**Key principles:**
- **No regex** — matching is token n-gram containment
- **No hardcoded English** — all patterns come from JSON
- **Multilingual** — Japanese/Igbo frame entries would work the same way
- **Constructions propose, perceptor disposes** — the matcher returns
  `ConstructionMatch` objects with `pragmatic_hints` and
  `graph_patch_templates`; the perceptor uses these to set `group_type`
  and `intent_key` instead of its own hardcoded logic

### Phase 2 — Enrich `ConstructionLattice` seeds

**File:** `cemm/memory/construction_lattice.py`

**Changes:**
- Replace the 6 crude `_seed()` entries with proper `ConstructionAtom`s
  that have real surface patterns
- Add a `match_surface(tokens: list[str]) -> ConstructionMatch | None`
  method that does token n-gram matching against form signatures
- Keep existing `match(packet, graph)` for graph-level matching
- Add `match_group(group, packet)` delegate that calls `match_surface`

**New seed constructions (from uol_semantics.json frame entries):**

| canonical_key | aliases | intent_key (current hardcoded) |
|---|---|---|
| `greeting` | hello, hi, hey, ... | `greeting` |
| `session_exit` | bye, goodbye, ... | `session_exit` |
| `self_identity_query` | who are you, what are you, ... | `self_identity_query` |
| `self_capability_query` | what can you do, ... | `capability_query` |
| `self_knowledge_query` | what do you know about yourself, ... | `self_knowledge_query` |
| `phatic_checkin` | how are you, how's it going, ... | `phatic_checkin` |
| `reciprocal_phatic` | what about you, and you, ... | `reciprocal_phatic` |
| `concept_query` | what is a, what does, define, ... | `question` / `fresh_world_query` |
| `command_remember` | remember, save, store, ... | `command` |
| `request_clarification` | huh, what do you mean, ... | `repair` |
| `acknowledgment` | ok, sure, yeah, ... | `acknowledgment` |
| `teaching_offer` | let me tell you about, ... | `teaching` |
| `user_state_report` | i'm good, i'm fine, ... | `user_state_report` |
| `self_category_query` | are you a robot, ... | (new) |
| `memory_query` | do you remember, ... | (new) |

**Cue-type entries (grammatical_*) stay as cue sets**, not constructions.
They're used by `_initial_group_type` for segmentation, not intent detection.
The `uol_metadata.py` module already loads these into `CUE_SETS`.

### Phase 3 — Refactor `MeaningPerceptor`

**File:** `cemm/kernel/meaning_perceptor.py`

**Changes in order of risk:**

1. **Accept `ConstructionMatcher` as a dependency:**
   ```python
   def __init__(self, ..., construction_matcher: ConstructionMatcher | None = None):
       self._construction_matcher = construction_matcher
   ```

2. **Replace `_intent_key_for_group` with construction delegation:**
   - Before: 15 hardcoded set lookups + special-case methods
   - After: call `self._construction_matcher.match_group(group, packet)`
     - If match found: use `match.construction_key` as intent key
     - If no match: fall through to minimal heuristic (group_type + punctuation)

3. **Replace `_is_self_identity_query`, `_is_capability_query`,
   `_is_self_knowledge_query` with construction matches:**
   - These are already frame entries in JSON with aliases
   - Construction matcher handles them automatically

4. **Replace `_is_teaching_group` with construction match:**
   - `teaching_offer` frame entry covers "let me tell you about", etc.
   - `concept_query` covers "X is Y" teaching patterns
   - Add `teaching_definition` frame entry for "X means Y", "X is called Y"

5. **Replace `_is_repair_group` with construction match:**
   - `request_clarification` and `confusion_repair` frame entries cover this

6. **Replace `_initial_group_type` to use `CUE_SETS` from `uol_metadata`:**
   - `cue_set("question_starter")` instead of `_QUESTION_STARTERS`
   - `cue_set("command_cue")` instead of `_COMMAND_CUES`
   - `cue_set("teaching_cue")` instead of `_TEACHING_CUES`
   - `cue_set("negation")` instead of `_NEGATIONS`
   - `frame_alias_set("acknowledgment")` instead of hardcoded answer set

7. **Replace `_looks_predicative` to use `CUE_SETS`:**
   - `cue_set("question_starter")`, `cue_set("command_cue")`,
     `cue_set("predicate_verb")` instead of hardcoded sets

8. **Replace modal/time/place emission to use `CUE_SETS`:**
   - `cue_set("modal")` for modal detection
   - `cue_set("temporal_reference")` for time cues
   - `cue_set("place_reference")` for place cues
   - Load `modal_types` from `uol_metadata` for modality classification

9. **Remove `_SOCIAL_PHRASE_ALIASES`:**
   - `phatic_checkin` and `reciprocal_phatic` frame entries cover this
   - Construction matcher handles phrase matching

10. **Remove `_FRESH_WORLD_CUES`:**
    - `cue_set("fresh_world_marker")` covers this

11. **Remove `_EXIT_CUES`:**
    - `frame_alias_set("session_exit")` covers this

12. **Remove `_greeting_forms` (both the line 1034 inline set
    and the line 1036 duplicate):**
    - `frame_alias_set("greeting")` covers this
    - Fixes the existing bug of duplicated `_greeting_forms`

13. **Remove `_AMBIGUOUS_LEXEMES`:**
    - This is a tiny seed lexicon (only "bank").  It should be loaded
      from JSON or removed entirely.  For now, move to a JSON entry
      `ambiguous_lexemes` in `uol_semantics.json`.

14. **Remove `_CONJUNCTION_MAP`:**
    - Load from `uol_metadata` or a `conjunction_map` JSON section.
    - This is used for clause splitting, not intent detection.

15. **Remove `_COMMON_PREDICATE_VERBS`:**
    - `cue_set("predicate_verb")` covers this

16. **Remove `_PRONOUNS`:**
    - Already handled by `self._language.map_pronouns()`
    - The hardcoded set is redundant

**Net effect:** ~15 hardcoded sets/dicts removed, ~200 lines of
English-specific intent detection replaced by construction matcher
delegation.  `MeaningPerceptor` shrinks from ~1400 to ~1100 lines.

### Phase 4 — Wiring

**File:** `cemm/kernel/semantic_cpu.py`

```python
self.construction_matcher = ConstructionMatcher(self.construction_lattice)
self.perceptor = MeaningPerceptor(
    construction_matcher=self.construction_matcher,
)
```

**File:** `cemm/kernel/semantic_kernel_runtime.py`
- Expose `construction_matcher` as a property
- No other changes needed (already delegates to SemanticCPU)

**File:** `cemm/kernel/pipeline.py`
- No changes needed (already delegates to runtime)

### Phase 5 — Data additions to `uol_semantics.json`

Already done:
- Added `grammatical_command_expanded` (cue_type: `command_cue`)
- Added `grammatical_teaching_cue` (cue_type: `teaching_cue`)
- Added `grammatical_predicate_verb` (cue_type: `predicate_verb`)
- Added `grammatical_place_reference` (cue_type: `place_reference`)
- Added `modal_types` map
- Added `reciprocal_phatic` frame entry

Still needed:
- Add `teaching_definition` frame entry for "X means Y", "X is called Y"
  (aliases: ["means", "called", "refers to", "is defined as", "equals"])
- Add `ambiguous_lexemes` section (or remove `_AMBIGUOUS_LEXEMES` entirely)
- Add `conjunction_map` section (or load from separate JSON)

### Phase 6 — Cleanup (separate from this refactor)

- Fix 4 silent `except Exception: pass` in `semantic_kernel_runtime.py`
- Replace `_identity_predicates`/`_capability_predicates` in `structural.py`
  with `PredicateSchemaStore` lookups
- Clean up stale operator loading in `__main__.py`

## Testing Strategy

1. **Before any code changes:** Run existing tests, capture baseline
2. **After Phase 1-2:** Unit test `ConstructionMatcher.match_group()` with
   known inputs ("who are you", "how are you", "remember that", etc.)
3. **After Phase 3:** Run existing tests, verify no regressions
4. **New tests:**
   - `test_construction_matcher.py` — test each frame entry matches its aliases
   - `test_multiturn_integration.py` — verify end-to-end behavior unchanged
   - `test_multilingual_constructions.py` — verify non-English frame entries
     work when added to JSON
5. **Property test:** For any text, `intent_key_for_group` should return
   the same result before and after refactor (golden file comparison)

## Risk Mitigation

- **Fallback:** If `ConstructionMatcher` returns no match, perceptor falls
  back to minimal heuristic (group_type + punctuation).  This prevents
  regressions for inputs not covered by frame entries.
- **Gradual:** Phases 1-2 are additive (new module + enriched seeds).
  Phase 3 is the only destructive change.  Can verify Phase 1-2 work
  before starting Phase 3.
- **Golden tests:** Capture current intent detection outputs for a set of
  inputs before refactor, verify same outputs after.

## What This Does NOT Change

- `MeaningGraphBuilder` — still builds UOLGraph from percept
- `SemanticKernelRuntime.run_turn()` — still the single authority
- `ConversationActClassifier` — already uses JSON, now shares `uol_metadata`
- `SemanticRealizer` — already data-driven from `response_templates.json`
- `PredicateSchemaStore` — already data-driven
- `LanguageAdapter` — still handles pronouns, actions, states, needs, affect
  (these are atom-level mappings, not intent detection)

## Architectural Compliance

After this refactor:
- §5.3 ConstructionMatch: **Implemented** (was missing)
- §8 Construction Lattice: **Properly seeded** from JSON (was 6 crude entries)
- §18 Module Boundaries: `construction_matcher.py` **exists** (was missing)
- §19.4 Construction As Regex: **Fixed** (was violating with hardcoded sets)
- §3.6 Constructions Are Operators: **Enforced** (intent detection via
  construction operators, not Python sets)
- Multilingual: Adding a new language = adding JSON frame entries, not
  changing Python code
