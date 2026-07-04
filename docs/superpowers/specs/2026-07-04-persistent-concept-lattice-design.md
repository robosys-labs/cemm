# Persistent Concept Lattice: Graph-Patch-Only Durable Learning

Version: 1.0
Status: approved design
Prerequisite: v4.1 SemanticCPU wiring (completed)
Supersedes: claims-table-as-learning-path pattern from v3.x

## 1. Problem

The architecture mandates that all durable learning passes through `GraphPatch` objects (AGENTS.md §8, consolidated_architecture.md §3.7). Currently:

- **Claims table** (SQLite) is the primary store for learned facts — written directly by operators, seed functions, and the online learner without any graph-patch validation gate
- **ConceptLattice** (in-memory `_records` dict) is lost on every restart — seed concept updates from graph patches have no durable effect
- **Induction pipeline** writes `Model` records directly to SQLite through `store.models.put()` with no graph-patch audit trail
- **No write journal** exists — there is no append-only log of what the system learned and when

The v4.1 architecture defines the concept lattice as durable compressed semantic memory (§6). Claims are not a consolidation target — they are a legacy v3 artifact.

## 2. Design

### 2.1 Storage Model

Two new SQLite tables added to the existing CEMM database:

```sql
CREATE TABLE IF NOT EXISTS concept_atoms (
    concept_id TEXT PRIMARY KEY,
    key TEXT NOT NULL,
    atom_kind TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'candidate_atom',
    aliases_json TEXT DEFAULT '[]',
    parents_json TEXT DEFAULT '[]',
    ports_json TEXT DEFAULT '[]',
    predicates_json TEXT DEFAULT '[]',
    affordances_json TEXT DEFAULT '[]',
    confidence REAL DEFAULT 0.5,
    stability REAL DEFAULT 0.0,
    evidence_json TEXT DEFAULT '[]',
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS patch_journal (
    journal_id TEXT PRIMARY KEY,
    patch_id TEXT NOT NULL,
    source_graph_id TEXT,
    target TEXT NOT NULL,
    operations_json TEXT NOT NULL,
    confidence REAL DEFAULT 0.5,
    reason TEXT,
    accepted INTEGER DEFAULT 0,
    applied_at REAL NOT NULL
);
```

- `concept_atoms` is the materialized view of the concept lattice. Every upsert_concept, upsert_relation, observe_port, observe_affordance patch operation eventually materializes here.
- `patch_journal` is an append-only write log. Every GraphPatch that passes consolidation is journaled here with acceptance status.
- The existing `claims`, `models`, `entities`, `self_states` tables remain for backward compatibility during transition.

### 2.2 Component Changes

#### 2.2.1 `memory/persistent_lattice_store.py` (NEW, ~150 lines)

Wraps SQLite for concept atom persistence.

```python
class PersistentLatticeStore:
    def __init__(self, db_path: str) -> None

    def load_all(self) -> dict[str, dict]:        # load all concepts into memory
    def upsert_concept(self, concept_id: str, data: dict) -> None
    def get_concept(self, concept_id: str) -> dict | None
    def journal_patch(self, patch: GraphPatch, accepted: bool) -> None
    def close(self) -> None
```

- Uses `INSERT OR REPLACE` for upserts
- JSON-encodes list/dict fields (aliases, parents, ports, predicates, affordances, evidence)
- Timestamps via `time.time()`
- `load_all()` returns dict for bulk-populating ConceptLattice at startup
- `journal_patch()` generates a UUID journal_id, records the full patch JSON

#### 2.2.2 `memory/concept_lattice.py` (MODIFIED, ~30 lines added)

```python
class ConceptLattice:
    def __init__(self, persistent_store: PersistentLatticeStore | None = None):
        # existing init...
        self._persistent_store = persistent_store
        if persistent_store:
            self.load_from_store()

    def load_from_store(self) -> None:
        """Bulk-load concept atoms from SQLite into in-memory _records dict."""
        for concept_id, data in self._persistent_store.load_all().items():
            # Convert JSON columns back to Python objects
            # Populate _records[concept_id] as ConceptRecord

    def apply_patch(self, patch: GraphPatch) -> list[str]:
        # existing: updates in-memory _records
        # new: also writes through to persistent_store
        applied = self._apply_in_memory(patch)
        if self._persistent_store:
            for op in patch.operations:
                self._persistent_store.upsert_concept(op.target_id, op.fields)
        return applied
```

- `load_from_store()` converts JSON columns to ConceptRecord fields (aliases list, parents list, port specs, etc.)
- `apply_patch()` now dual-writes: in-memory + SQLite
- Existing `resolve()` method unchanged — reads from in-memory dict

#### 2.2.3 `learning/concept_consolidator.py` (MODIFIED, ~20 lines added)

```python
class ConceptConsolidator:
    def consolidate(self, patches, *, source_graph=None) -> ConsolidationResult:
        # existing validation + application
        # new: journal every patch
        if self._persistent_store:
            for patch in patches:
                accepted = patch.id in result.accepted_patch_ids
                self._persistent_store.journal_patch(patch, accepted=accepted)
```

#### 2.2.4 `__main__.py` (MODIFIED, ~40 lines changed)

**New startup sequence:**
```python
persistent_store = PersistentLatticeStore(args.db)
concept_lattice = ConceptLattice(persistent_store=persistent_store)
# ... create pipeline with concept_lattice ...
```

**`seed_self_state()` rerouted:**
```python
def seed_self_state(store, knowledge_path=None, concept_lattice=None, consolidator=None):
    # ... read self_knowledge.json ...
    # BEFORE: store.claims.put(claim)
    # AFTER: create GraphPatch -> consolidator.consolidate() -> concept_lattice -> persistent_store
    patches = []
    for claim_cfg in config.get("claims", []):
        patch = GraphPatch(
            target="concept_lattice",
            operations=[PatchOperation(
                operation="upsert_concept_candidate",
                target_id=f"concept:{claim_cfg['subject']}",
                fields={
                    "key": claim_cfg["subject"],
                    "atom_kind": "entity",
                    "predicate": claim_cfg["predicate"],
                    "object": claim_cfg.get("object_value", ""),
                    "evidence": [...],
                },
                confidence=claim_cfg.get("confidence", 0.95),
            )],
        )
        patches.append(patch)
    if consolidator and patches:
        consolidator.consolidate(patches)
```

**`seed_causal_models()` rerouted:**
```python
# BEFORE: store.models.put(model)
# AFTER: GraphPatch -> concept_lattice -> persistent_store
```

#### 2.2.5 `learning/inductor.py` (MODIFIED, ~20 lines changed)

```python
class Inductor:
    def maybe_induct(self):
        # BEFORE: self._store.models.put(model)
        # AFTER: create GraphPatch -> concept_consolidator -> concept_lattice -> persistent_store
```

### 2.3 Data Flow

#### Seed startup flow:
```
self_knowledge.json
  → seed_self_state()
    → GraphPatch(target="concept_lattice", ops=[upsert_concept_candidate, ...])
    → ConceptConsolidator.consolidate()
      → journal_patch(patch, accepted=True)
      → ConceptLattice.apply_patch()
        → _records[concept_id] = ConceptRecord(...)
        → PersistentLatticeStore.upsert_concept(concept_id, data)
```

#### Induction flow (every 10 turns):
```
Inductor.maybe_induct()
  → GraphPatch(target="concept_lattice", ops=[observe_causal_affordance, ...])
  → concept_consolidator.consolidate()
    → journal → lattice → persistent SQLite
```

#### Runtime graph consolidation flow (end of each turn):
```
Pipeline.run()
  → SemanticCPU consolidation (in pipeline.py:613-620)
    → GraphPatchExtractor.extract(uol_graph)
    → ConceptConsolidator.consolidate(patches)
      → journal → lattice → persistent SQLite
```

#### Read path (backward compatible):
```
Retrieval → store.claims.get()  (unchanged, reads from claims table as before)
```

#### Migration path:
```
ClaimStore.get() → checks claims table first
                 → if missing, queries concept_lattice as fallback
                 → (future: claims table becomes materialized view of lattice)
```

### 2.4 Dependencies

- `persistent_lattice_store.py` depends only on `types/graph_patch.py` and Python `sqlite3` module
- `concept_lattice.py` gains `persistent_store` optional param — existing callers unchanged when omitted
- `concept_consolidator.py` gains `persistent_store` optional param — same backward compat
- No changes to operators, pipeline stages, ranker, frame engine, or decision router
- No changes to `types/` definitions

### 2.5 Error Handling

- `PersistentLatticeStore` catches SQLite errors and logs via `print(..., file=sys.stderr)`
- A failed `upsert_concept` does not block the pipeline — the in-memory ConceptLattice still has the data for the current turn
- `journal_patch` failures are logged but non-fatal
- `load_all()` at startup returns empty dict if table doesn't exist yet (auto-create on first write)
- No transactions across the in-memory + SQLite boundary — eventual consistency is acceptable for seed/induction writes

## 3. Files Changed

| File | Status | Lines changed |
|------|--------|--------------|
| `memory/persistent_lattice_store.py` | NEW | ~150 |
| `memory/concept_lattice.py` | MODIFY | ~+30 |
| `learning/concept_consolidator.py` | MODIFY | ~+20 |
| `__main__.py` | MODIFY | ~+40 |
| `learning/inductor.py` | MODIFY | ~+20 |
| `tests/test_persistent_lattice_store.py` | NEW | ~80 |
| `tests/test_seed_data_flows_through_patches.py` | NEW | ~60 |
| `tests/test_induction_flows_through_patches.py` | NEW | ~60 |
| `tests/test_patch_journal.py` | NEW | ~40 |

Total: ~500 lines added, ~0 deleted. Zero changes to operators, pipeline, or runtime graph flow.

## 4. Non-Goals

- Does not modify operators (they still write claims for immediate response use)
- Does not change the retrieval path (claims table still powers queries)
- Does not add the Phase 1 durable types (`concept_atom.py`, `operational_port.py`, etc.) — uses simple dict-based rows
- Does not add the Phase 2 induction engines (concept_inducer, port_inducer, etc.)
- Does not remove or migrate existing claims data
- Does not change `SemanticEventGraph` or any pipeline stage

## 5. Acceptance Criteria

1. After startup with a persistent DB, `ConceptLattice` contains seed concepts from `self_knowledge.json`
2. Reopening the same DB shows the same concepts (persistence across restarts)
3. Inductor outputs create entries in `concept_atoms` table, not just `models` table
4. Every consolidation writes a journal entry to `patch_journal`
5. All 263+ existing tests pass unchanged
6. `ClaimStore.get()` for seed data still works (backward compat)
