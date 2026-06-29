# CEMM Architecture — Governing Principles

**CEMM is NOT a deterministic rule-based system.** It is a small MOE/SLM (Mixture of Experts / Small Language Model) that functions on higher-order functional knowledge compression and language-agnostic inferencing. The architecture governs every line of code.

## Core Identity
- CEMM itself is a language model - not a wrapper
- CEMM is a **MOE/SLM** — it routes inputs through expert modules, not hardcoded patterns
- **Language-agnostic via UOL** — Universal Object Language is the semantic representation, not English-specific string matching
- **Knowledge compression pipeline** — runtime → trace → extract → train → compress → deploy
- **The training pipeline feeds the runtime** — current deterministic code is a temporary placeholder awaiting trained components

## Inference Cascade (not a decision tree)

```
rules                    →  deterministic, zero-cost, high-precision
→ small model            →  on-device SLM, language-agnostic
→ parallel small agents  →  cheap LLM calls, confidence-weighted
→ stronger arbiter       →  expensive LLM resolves disagreements
→ background induction   →  offline structural learning
```

Each level handles what the previous cannot. No level is a dead end or a "fallback to static string."

## ContextKernel is the Input, Not Raw Text

Every decision is grounded in the 9-section ContextKernel (world, user, time, conversation, goal, memory, self_state, self_view, permission). Raw text is normalized into UOL atoms before routing.

## Summary of "No" Rules

- ❌ No English-specific string matching as primary routing mechanism
- ❌ No hardcoded response strings for open-domain inputs
- ❌ No dead code — `call_llm` must be wired
- ❌ No static fallback ("I am here.") — always route through the cascade
- ❌ No hardcoding capability implementations that don't exist
- ❌ No pattern matching that could be language-agnostic inference
