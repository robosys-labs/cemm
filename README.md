# CEMM v1 — Modular semantic cognition kernel

CEMM keeps one exact semantic substrate while using neural models for open
compositional interpretation, semantic workspace dynamics, learnable
definitions, and grounded language realization — without domain-schema or
phrase-program explosion. v1 is built from the frozen v4 MVP kernel.

## Thesis

```text
Exact semantics are authority.
Neural computation proposes, ranks, composes and realizes semantics.
Neural latent state never becomes a second semantic ontology.
```

There is no closed semantic-program catalogue. Surface text plus grounded
mention evidence flows through a shared Transformer to intent, application-slot
presence, per-slot operators, role→grounded-source pointers, an N-best graph of
candidates, exact compile/clamp, recurrent candidate settling, and finally a
stable or unresolved CSIR-like graph.

## Architecture

```text
┌──────────────────────────────────────────────────────────────────────┐
│ IMMUTABLE SEMANTIC AUTHORITY                                         │
│                                                                      │
│ Kernel Semantic ABI · CSIR constructors · exact operators/roles      │
│ semantic definitions · promoted rules · language/model artifacts     │
│ operational profiles · causal mechanisms · authorizations            │
└─────────────────────────────────┬────────────────────────────────────┘
                                  │ exact pins
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│ MUTABLE GROUNDED WORLD / DISCOURSE                                   │
│                                                                      │
│ referents · claims · state timelines · events · evidence · discourse │
│ world revision · discourse revision · observation revision           │
└─────────────────────────────────┬────────────────────────────────────┘
                                  │ bounded indexed retrieval
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│ CYCLE WORKSPACE / ACTIVE SEMANTIC WORKSPACE                          │
│                                                                      │
│ evidence lattice · referent candidates · CSIR candidates             │
│ relevant exact/derived facts · self/world state · runtime view       │
│ query restrictions · proof dependencies · frontiers · goals          │
└─────────────────────────────────┬────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│ NEURAL SEMANTIC DYNAMICS                                              │
│                                                                      │
│ structured graph prediction · relevance ranking · attention          │
│ N-best candidate scoring · language realization-plan selection       │
└─────────────────────────────────┬────────────────────────────────────┘
                                  │ exact compiler / hard constraints
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│ EXACT SEMANTIC COGNITION                                              │
│                                                                      │
│ settle · query · infer · learn candidate · simulate · choose goal     │
│ commit only at explicit boundaries                                   │
└───────────────┬──────────────────────────────┬───────────────────────┘
                │                              │
                ▼                              ▼
       RESPONSE SEMANTICS               LEARNING FRONTIERS
                │                              │
                ▼                              ▼
       semantic-pointer NLG         provisional candidate authority
                │                              │
                ▼                              ▼
       cheap proof verification       competence / evidence / review
                │                              │
                ▼                              ▼
       authorized emission             new authority generation
                │                              │
                └───────────────► next-cycle activation ◄─────────────┘
```

## Quick start

```bash
pip install -e .
python -m cemm.cli init --db demo.sqlite \
  --data cemm/data/base.json \
  --data cemm/data/family_knowledge.json \
  --pack cemm/language_packs/en.json
python -m cemm.cli ask --db demo.sqlite \
  --pack cemm/language_packs/en.json "What is evidence?"
```

## Concrete example

A short session showing ask, teach (provisional→promoted), reload, learn, and
inference:

```text
$ python -m cemm.cli ask --db demo.sqlite --pack cemm/language_packs/en.json "What is evidence?"
"Evidence is information."

$ python -m cemm.cli teach --db demo.sqlite --pack cemm/language_packs/en.json "A mother in-law is the mother of a partner."
→ provisional rule recorded (generation pending promotion)

$ python -m cemm.cli teach --db demo.sqlite --pack cemm/language_packs/en.json "A mother in-law is the mother of a partner."
→ rule promoted to authority

$ python -m cemm.cli reload --db demo.sqlite --pack cemm/language_packs/en.json
→ Authority reloaded to generation N.

$ python -m cemm.cli learn --db demo.sqlite --pack cemm/language_packs/en.json "My mother in-law arrived today."
→ grounded claim recorded (mother_in-law referent bound)

$ python -m cemm.cli ask --db demo.sqlite --pack cemm/language_packs/en.json "Am I married?"
"Yes."
```

The final answer is derived by forward-chaining inference over the promoted
rule (mother_in-law ⇒ mother of partner) plus the learned grounded claim
(speaker has a mother in-law), yielding an inferred partner and therefore a
married state.

## CLI commands

| Command   | Purpose                                                        |
|-----------|---------------------------------------------------------------|
| `init`    | Create a database and import data + language pack.            |
| `chat`    | Read lines from stdin, print responses.                       |
| `learn`   | Process text in learn mode (record grounded claims).          |
| `teach`   | Process text in teach mode (propose/promote rules).           |
| `ask`     | Process text in ask mode (query, no side effects).            |
| `inspect` | Print table counts and snapshot hash for a database.          |
| `reload`  | Reload authority into the runtime (promote pending generation).|
| `acquire` | Run explicit reviewed acquisition; ordinary unknown forms open typed learning frontiers without parser writes. |

## Module structure

| Module           | Responsibility                                                        |
|------------------|-----------------------------------------------------------------------|
| `constants.py`   | Database DDL, tokenizer regex, shared constants.                      |
| `config.py`      | Configurable thresholds for the runtime.                              |
| `model.py`       | Core model types and helper functions.                                |
| `context.py`     | Session/cycle participant, temporal, and workspace grounding artifacts.|
| `store.py`       | Semantic meaning database; authority/world atom separation.           |
| `state.py`       | Recursive state entitlement and generic state-timeline projection.    |
| `codec.py`       | Open compositional semantic codec (CSIR construction).                |
| `compiler.py`    | Exact structured compiler (compile/clamp candidates).                 |
| `settler.py`     | Semantic settler (recurrent candidate settling).                      |
| `workspace.py`   | Bounded active semantic workspace.                                    |
| `selfstate.py`   | Session self-state and state transitions.                             |
| `inference.py`   | Forward-chaining inference engine.                                    |
| `rules.py`       | Rule learner (provisional→promoted lifecycle).                        |
| `interpreter.py` | Interpreter, SurfaceCodec, and Delexer.                               |
| `trainer.py`     | Language-pack trainer (train-at-startup proof models).                |
| `realizer.py`    | Pointer realizer and language pack.                                   |
| `response.py`    | Response planning and pointerization.                                 |
| `acquisition.py` | Reviewed and autonomous vocabulary acquisition.                       |
| `runtime.py`     | Runtime orchestrator (cycle coordination, authority reload).          |
| `cli.py`         | Command-line interface (8 subcommands).                               |

## Current status

Architecture proof, under active verification. The executable test suite—not a
hard-coded README pass count—is the acceptance source of truth. Bundled
Transformers are tiny train-at-startup proof models, not performance
benchmarks. The kernel demonstrates the core invariant — exact semantics as
authority, neural computation as proposal — end to end across ask, teach,
learn, reload, and acquire.

## References

- `ARCHITECTURE.md` — full v1 architecture and runtime contracts.
- `v1-fixes.md` — dependency-ordered defect/fix plan and acceptance gates.
- `runtime-core-loop.md` — concrete lean runtime/core-loop implementation contract.
- `reference/mvp_v4/` — frozen MVP v4 demo (read-only permanent reference).
  Run it with:
  ```bash
  cd reference/mvp_v4
  PYTHONPATH=. python -m unittest -v tests.test_mvp
  ```
- `cemm/data/` — base and family-knowledge semantic data.
- `cemm/language_packs/` — English (`en.json`) and Spanish (`es.json`) packs.
- `cemm/training/` — seed corpora for language-pack training.
