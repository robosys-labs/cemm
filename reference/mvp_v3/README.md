# CEMM Minimal Brain MVP v3

Executable proof of a hybrid CEMM architecture: exact semantic authority + bounded semantic workspace + Transformer ranking + trainable language packs + semantic-pointer NLG.

## Files

- `cemm_mvp.py` — exact store, grounding, inference, self state, workspace, language interpretation, response planning and semantic-pointer realization.
- `trainer.py` — language-generic compiler from structured text/meaning training corpora to versioned language packs.
- `knowledge/base.json` — foundational semantic/runtime meaning. No embedded language-example or realization-template section.
- `knowledge/family_knowledge.json` — reusable family/domain semantic knowledge and rules.
- `training/en_seed.json`, `training/es_seed.json` — structured language training corpora.
- `language_packs/en.json`, `language_packs/es.json` — generated versioned language artifacts.
- `MVP_ARCHITECTURE.md` — consolidated architecture and mapping to current canonical `ARCHITECTURE.md`, `CORE_LOOP.md`, and `RUNTIME_PLAN.md`.
- `tests/test_mvp.py` — regression contract.

## Install

Requires Python 3.11+ and PyTorch.

```bash
pip install -r requirements.txt
```

## Rebuild language packs

```bash
python trainer.py training/en_seed.json language_packs/en.json
python trainer.py training/es_seed.json language_packs/es.json
```

## Initialize and inspect

```bash
python cemm_mvp.py init \
  --db demo.sqlite \
  --data knowledge/base.json \
  --data knowledge/family_knowledge.json \
  --pack language_packs/en.json
```

## Chat

```bash
python cemm_mvp.py chat \
  --db demo.sqlite \
  --pack language_packs/en.json
```

Example:

```text
Hi.
What is evidence?
Am I married?
My mother in-law arrived today.
Am I married?
```

Expected semantic behavior:

```text
Hello.
Evidence is information.
Evidence is insufficient.
Meaning is stored.
Yes.
```

These are not literal response branches in Python. Response semantics are constructed from the meaning DB and realized through the generated language pack.

## Tests

```bash
PYTHONPATH=. python -m unittest -v tests.test_mvp
```

See `MVP_ARCHITECTURE.md` for what the MVP proves and what remains intentionally outside scope.
