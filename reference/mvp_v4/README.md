# CEMM Minimal Semantic Brain MVP v4

v4 is an executable proof of the CEMM architecture with:

- exact data/CSIR-like semantic authority;
- open compositional Transformer structured prediction;
- N-best exact candidate settling;
- identity/designation separation;
- bounded semantic workspace and self state;
- anti-bloat ephemeral inference;
- learnable provisional/promoted semantic graph rules;
- explicit authority activation boundaries;
- reviewed new-vocabulary acquisition;
- multilingual shared semantics;
- semantic-pointer NLG with grounded response concepts.

Start with [`MVP_ARCHITECTURE.md`](MVP_ARCHITECTURE.md).

## Run tests

```bash
python -m unittest tests/test_mvp.py -v
```

## Rebuild language packs

```bash
python trainer.py training/en_seed.json language_packs/en.json \
  --knowledge knowledge/base.json \
  --knowledge knowledge/family_knowledge.json
```

## Key demo sequence

```text
teach: A mother in-law is the mother of a partner.
teach: A mother-in-law is the mother of a partner.
reload authority
learn: My mother in-law arrived today.
ask:   Am I married?
→ Yes.
```

The family-specific decomposition rule is not seeded in `family_knowledge.json`; it is induced, promoted, then explicitly activated.
