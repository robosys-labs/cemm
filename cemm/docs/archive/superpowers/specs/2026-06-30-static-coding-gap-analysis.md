# CEMM Static Coding Gap Analysis — 2026-06-30 (Session 2)

> **Context:** During gap fixing, static hardcoded logic was introduced into kernel components (`decision_router.py`, `semantic_interpreter.py`) that violates CEMM's model-driven, language-agnostic architecture. This document tracks those gaps and their fixes.

## Architectural Principle

CEMM is designed so that **all language understanding lives in the model layer** (Registry, UOL Mapper, trained artifacts). Kernel components (SemanticInterpreter, DecisionRouter) should only operate on typed semantic structures (UOL atoms, SEG, SAG), never on raw text patterns.

## Static Coding Gaps Introduced

### S1: Hardcoded greeting word list in DecisionRouter
- **Location:** `kernel/decision_router.py:32` — `_GREETINGS = {"hello", "hi", "hey", ...}`
- **Problem:** Greeting detection uses a hardcoded English word list with fuzzy matching directly in the DecisionRouter. This is language-specific, non-trainable, and bypasses the UOL mapper + SEG process detection.
- **Proper path:** The UOL mapper should detect greeting intent and emit a `ProcessUOLAtom(frame_key="greeting")`. The SEG should contain this process. The DecisionRouter should check `graph.processes` for `frame_key == "greeting"`, not parse raw text.

### S2: Hardcoded exit word list in DecisionRouter
- **Location:** `kernel/decision_router.py:33` — `_EXITS = {"exit", "quit", "bye", ...}`
- **Problem:** Same as S1 — language-specific exit detection in the kernel instead of the model layer.
- **Proper path:** UOL mapper should emit `ProcessUOLAtom(frame_key="session_exit")`. DecisionRouter checks graph processes.

### S3: Hardcoded command prefix list in DecisionRouter
- **Location:** `kernel/decision_router.py:34` — `_COMMAND_PREFIXES = ["remember", "save", "reflect", ...]`
- **Problem:** Command detection uses hardcoded English verb prefixes with fuzzy Levenshtein matching in the DecisionRouter. This bypasses the registry's operator entries and UOL semantic mapping.
- **Proper path:** UOL mapper should detect command intent and emit `ProcessUOLAtom(frame_key="command_remember")` etc. DecisionRouter maps process frame_keys to action kinds via the registry's operator entries.

### S4: Hardcoded claim candidate regex patterns in SemanticInterpreter
- **Location:** `kernel/semantic_interpreter.py:38-50` — `_CLAIM_CANDIDATE_PATTERNS`
- **Problem:** Claim extraction uses hardcoded English regex patterns (`"i like"`, `"i have"`, `"i am"`, etc.). This is language-specific and non-trainable. The patterns also hardcode subject resolution (`"i" -> "user"`).
- **Proper path:** Claim candidates should be derived from UOL process/state atoms + registry predicates. The UOL mapper identifies the semantic structure; the interpreter maps it to predicate keys via the registry.

### S5: Hardcoded temporal/causal regex patterns in SemanticInterpreter
- **Location:** `kernel/semantic_interpreter.py:15-36` — `_TEMPORAL_PATTERNS`, `_CAUSAL_PATTERNS`
- **Problem:** Temporal and causal edge extraction uses hardcoded English regex patterns. These should be UOL semantic mappings, not kernel-level regex.
- **Proper path:** UOL mapper should emit process atoms with temporal/causal frame_keys. The interpreter maps these to edges using registry entries, not regex.

### S6: Command prefix stripping in SemanticInterpreter
- **Location:** `kernel/semantic_interpreter.py:164-168` — strips `"remember "`, `"save "`, `"rember "`, `"store "`
- **Problem:** Hardcoded command prefix stripping including a misspelled variant (`"rember"`). This is a workaround for the UOL mapper not recognizing command intent.
- **Proper path:** UOL mapper should handle command detection and strip/normalize commands as part of mapping.

### S7: Hardcoded "user" default subject in SemanticInterpreter claim_refs
- **Location:** `kernel/semantic_interpreter.py:141-143` — searches by `"user"` as default subject
- **Problem:** Assumes first-person statements always have `"user"` as subject. This is an English-centric assumption.
- **Proper path:** Subject resolution should come from the UOL mapper's entity ref atoms, which should map first-person pronouns to the kernel's user entity.

## Fix Plan

1. **Extend UOLMapper** to detect greetings, exits, commands, temporal/causal language, and claim structures — all using registry entries for canonical keys
2. **Register UOL semantic entries** for `greeting`, `session_exit`, `command_remember`, `command_reflect`, `command_retrieve`, `temporal_before`, `temporal_after`, `causal_causes`, etc.
3. **Register predicate entries** for claim candidate patterns (`likes`, `is_a`, `has`, `used_for`, `belongs_to`, `favorite`, `prefers`)
4. **Remove all static coding** from DecisionRouter — rely entirely on SEG processes
5. **Remove all static regex** from SemanticInterpreter — rely on UOL atoms and registry resolution
6. **Keep Levenshtein** as a utility in the UOL mapper for fuzzy alias resolution against registry entries

## Remaining Gaps from Manual Testing

### R1: Multi-turn recall failure
- **Problem:** After storing "I like coffee" via `remember`, asking "what do I like?" does not retrieve the stored claim. The SEG has no claim_refs because the UOL mapper doesn't extract "what do I like?" as a query about the user's preferences.
- **Root cause:** UOL mapper doesn't detect question intent or map it to entity refs that would trigger claim lookup.

### R2: Misspelled input abstention
- **Problem:** Misspelled queries like "whats the wether?" abstain because the UOL mapper doesn't recognize them.
- **Root cause:** UOL mapper has no fuzzy matching against registry aliases. Fuzzy matching should be in the mapper, not the DecisionRouter.

### R3: Greeting response quality
- **Problem:** Greetings route to `answer` but produce "I don't have enough information to answer." because there are no claims to answer with.
- **Root cause:** Greeting should produce a conversational response, not a knowledge-base answer. This requires a `greeting` synthesis strategy or a dedicated greeting response path in the answer operator.
