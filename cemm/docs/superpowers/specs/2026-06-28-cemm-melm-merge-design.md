# CEMM ↔ MELM Merge: CEMM as MELM's Extraction & Training Backend

**Date:** 2026-06-28  
**Status:** Draft  
**Design goal:** Merge MELM's assistant capabilities (router, synthesis, memory calibration, device actions) with CEMM's training pipeline (LLM extraction agents, causal inference, structured claim store) so that CEMM provides trained extraction quality to MELM conversations, targeting 300-turn coherent sessions.

## Architecture

```
User utterance
    │
    ▼
MELM OnDeviceAssistantCli._process_user_input()
    │
    ├── 1. parse_uol()                 ─── keyword-based UOL parsing
    ├── 2. HOOK: bridge.extract(text)  ─── CEMM enhanced extraction
    ├── 3. interpret()                 ─── semantic interpretation (+ bridge claims)
    ├── 4. route()                     ─── match contract (100+ contracts)
    ├── 5. HOOK: bridge.infer_causal() ─── causal evidence for synthesis
    ├── 6. synthesize()                ─── bounded response with citations
    ├── 7. HOOK: bridge.record_turn()  ─── persist to CEMM conversation store
    │
    ▼
 Assistant response
```

## Components

### 1. CemmBridge (`cemm/bridge.py`)

Public API that MELM imports. Zero MELM dependencies.

```python
class CemmBridge:
    def __init__(self, store_path: str = "cemm.db")
    def extract(self, text: str, context: list[dict] = None) -> ExtractionResult
    def extract_entities(self, text: str) -> list[Entity]
    def extract_claims(self, text: str) -> list[Claim]
    def infer_causal(self, claim_ids: list[str]) -> list[CausalLink]
    def record_turn(self, user_msg: str, assistant_msg: str, turn_num: int)
    def get_conversation_state(self) -> dict
    def close()
```

`ExtractionResult` contains: `entities: list[Entity]`, `claims: list[Claim]`, `predicates: list[str]`, `temporal: str | None`, `confidence: float`.

`context` is an optional list of prior turns as `{"role": "user"|"assistant", "content": str}` — same format as LLM chat messages. When provided, extraction uses conversation history for anaphora resolution.

All methods are **soft-fail** — if CEMM store is unavailable, they return empty results and log a warning.

### 2. MELM Integration (3 hooks)

Hook locations in `melm/cli.py` `OnDeviceAssistantCli._process_user_input()`:

| # | Hook | After Step | What It Does |
|---|------|-----------|--------------|
| 1 | **Enrich** | `parse_uol()` | Calls `bridge.extract(text)`, merges entities & claims into MELM's parse result |
| 2 | **Reason** | `route()` | Calls `bridge.infer_causal(claim_ids)`, attaches causal links to synthesis context |
| 3 | **Remember** | `synthesize()` | Calls `bridge.record_turn(user_msg, response, turn_num)` |

Feature-flagged via `CEMM_ENABLED` env var (default: `0`). When disabled, MELM runs indentically to current behavior.

### 3. Conversation Store Tables

New tables in `cemm/store/schema.py`:

```sql
CREATE TABLE conversations (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    turns_goal INTEGER NOT NULL DEFAULT 300,
    tags TEXT DEFAULT '[]'  -- JSON array: ["device_assistant", "complex", "anaphora_heavy"]
);

CREATE TABLE conversation_turns (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(id),
    turn_num INTEGER NOT NULL,
    user_msg TEXT NOT NULL,
    assistant_msg TEXT NOT NULL,
    entities_json TEXT DEFAULT '[]',
    claims_json TEXT DEFAULT '[]',
    is_elided INTEGER DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE turn_causal_links (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    source_turn_id TEXT NOT NULL,
    target_turn_id TEXT NOT NULL,
    claim_id TEXT,
    link_type TEXT NOT NULL DEFAULT 'reference'
);
```

### 4. Training Scale-Up

**Seed expansion:** `docs/superpowers/seeds/device_assistant_examples.jsonl` from 36 → 200+ examples covering all 9 task types (alarm, call, email, media, message, query, reminder, search, timer).

**Training run:** `python -m cemm.cemm_trainer ingest <file> && python -m cemm.cemm_trainer run --workers 4`

## Phases

### Phase 1: Bridge (`cemm/bridge.py`)
- Implement `CemmBridge` with full API surface
- Wire to existing `SqliteStore`, `OnlineLearner`, `Pipeline`
- Tests: unit tests for each method, integration test against in-memory store

### Phase 2: MELM Hooks
- Insert 3 hooks in `melm/cli.py` with CEMM_ENABLED guard
- Verify: MELM tests pass with CEMM_ENABLED=0, bridge calls fire with CEMM_ENABLED=1

### Phase 3a: Seed Expansion
- Write 170+ additional examples covering edge cases (fragments, redirections, multi-intent, anaphora, compound predicates)
- Format: JSONL matching existing schema

### Phase 3b: Conversation Store
- Add `sqlite_schema` entries for 3 new tables
- Implement `ConversationStore` class with `create_conversation()`, `add_turn()`, `get_history()`, `elide_old_turns()`
- Implement causal link tracking across turns
- Tests: 300-turn insert + retrieval, elision at 300, cross-turn query

### Phase 3c: Training Scale
- `ingest` all 200+ examples
- `run --workers 4` to generate labels
- Validate: extraction quality on held-out examples

## Exit Criteria

- [ ] `CemmBridge.extract()` returns correct entities/claims on device-assistant utterances
- [ ] MELM runs without CEMM — same behavior as today
- [ ] MELM with CEMM_ENABLED=1 — hooks fire, extraction enriches conversation
- [ ] 200+ seed examples ingested and labeled
- [ ] `ConversationStore` records 300 turns without degradation
- [ ] All CEMM tests pass
- [ ] All MELM tests pass
- [ ] Verification: 300-turn simulated session completes without error, entity accuracy >90%, contradictory responses <5%
