# CEMM

**A trainable event-centered memory model for context-aware agents.**

CEMM is a pure-Python implementation of a meaning-first language architecture (v3.1) — a lean, practical system for context, memory, self-state, causal reasoning, recursive reflection, structural learning, and action. CEMM operates on foundational meaning atoms/primitives instead of matrices, enabling native language understanding and online learning.

## Core Primitives

| Primitive | Meaning | Main Question |
|---|---|---|
| `Signal` | Something observed | What happened? |
| `Entity` | Something identified | What thing is this? |
| `Claim` | Something believed | What is asserted? |
| `Model` | A reusable structure or process | How does this work? |
| `Action` | Something done or considered | What should happen next? |
| `Self` | The system's persistent self-state | What am I, and how am I changing? |

### Meaning Atoms (v3.0+)

| Atom | Meaning |
|---|---|
| `ReferentAtom` | Entity detected in signal (NER, capitalization, pronoun) |
| `ActionAtom` | Event/action predicate |
| `StateAtom` | Reported state of an entity |
| `RelationAtom` | Relationship between entities |
| `NeedAtom` | Expressed need or goal |
| `OutcomeAtom` | Predicted state change from an event |
| `ValenceAtom` | Entity-relative favorability evaluation |

## Project Structure

```
cemm/
├── types/       # Foundational atoms + runtime packets (dataclasses)
├── store/       # SQLite persistence (10 tables, 16 indexes)
├── confidence/  # Log-odds math and scoring formulas
├── registry/    # Predicate/entity/operator canonicalization + act type policy
├── kernel/      # Pipeline runtime: MeaningPerceptor, FrameBinder, EntityFactExtractor,
│                #   SituationFrameBuilder, OutcomeEvaluator, SafetyFrameDetector,
│                #   ConversationActClassifier, RetrievalPlanner, RetrievalExecutor,
│                #   ActResolutionPlanner, DecisionRouter, OutputStateUpdater
├── retrieval/   # Structural retrieval + ranking + RetrievalExecutor
├── operators/   # 10 typed operators (answer..abstain)
├── synthesis/   # Template/extractive router + verifier
├── causal/      # Causal inference + simulation engine
├── learning/    # Online learning, NER, surface tagger
└── training/    # Training export + task decomposition
```

## Quick Start

```bash
cd C:\dev\cemm

# Run tests
python -m pytest cemm/tests -q

# Start interactive session
python -m cemm
```

## Running

```bash
python -m cemm                    # Interactive chat
python -m cemm --eval "What is my favorite database?"  # Single query
python -m cemm --db path/to/db.sqlite                   # Persistent store
python -m cemm.web_demo           # Browser demo at http://127.0.0.1:5000
```

## Architecture (v3.1 Pipeline)

```
Signal
  -> ContextInferenceEngine (context before interpretation)
  -> MeaningPerceptor (NER + unknown lexemes + POS-lite roles + pronouns/deixis + affect)
  -> SituationFrameBuilder -> FrameBinder (atom-based scored role binding)
  -> EntityFactExtractor (atom-first fact extraction with surface pattern fallback)
  -> OutcomeEvaluator (predicted outcomes + entity-relative valences)
  -> SafetyFrameDetector (harm prevention before decision)
  -> SemanticInterpreter (SemanticEventGraph + UOL atoms)
  -> ConversationActClassifier (multi-act packet classification)
  -> RetrievalPlanner (explicit mode-driven retrieval plan)
  -> RetrievalExecutor (plan-driven structural retrieval)
  -> Ranker (confidence * trust * recency scoring)
  -> CausalInference (precondition/effect matching)
  -> ActResolutionPlanner (reply obligations + memory update plans + answer tasks)
  -> DecisionRouter (action selection)
  -> Synthesis Router (template/extractive/neural/abstain)
  -> OutputStateUpdater (post-output conversation state)
  -> Trace emission + online learning
```

See `cemm/architecture.md` for the full v3.0 architecture and `cemm/cemm_v3_1_operational_meaning_spine.md` for the v3.1 operational spine.

## Tests

267 tests covering:
- ERCA invariants (drift-proof contract)
- Foundational fixes (social/phatic, memory write, context-first, safety)
- v3.1 operational spine (FrameBinder, EntityFactExtractor, ActResolutionPlanner, RetrievalExecutor)
- CapabilityClassifier (supported/unsupported capability detection)
- Store CRUD for all subsystems
- Confidence math (log-odds, scoring)
- Registry (canonicalization, JSON round-trip)
- Causal inference (prediction, simulation, closure)
- Pipeline (signal persistence, kernel construction, full end-to-end)
