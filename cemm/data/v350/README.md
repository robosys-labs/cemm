# CEMM v3.5 reviewed semantic source package

This tree is the modular, language-neutral input to the deterministic Phase-4
SQLite compiler. It is reviewed source, not Python ontology authority.

## Phase ownership

- **Phase 4** supplies manifest loading, typed decoding, whole-package validation,
  deterministic compilation, immutable boot storage, and writable overlays.
- **Phase 5** derives type closure, facet entitlements, defaults, states,
  capabilities, and referent knowledge views.
- **Phase 6** supplies the minimal structural foundation and independent
  competence gates in this directory.
- **Phase 7 and later** own lexical senses, language realization, transition
  contracts, causal rules, domain knowledge, and runtime cutover.

Empty later-phase modules are explicit boundaries. They are not silently
replaced by code defaults.

## Phase-6 seed layers

```text
6A  broad referent-type anchors and multiple inheritance
6B  universal facets and entitlement contracts
6C  native semantic axes and operators
6D  properties, state dimensions, values, measures, and relations
6E  generic action/event, claim, discourse, and response-policy schemas
6F  function/capability distinction and truthful self contracts
6G  identity/evidence fixtures and non-factual default expectations
6H  declarative competence cases and deterministic verification
```

The package deliberately does **not** seed domain concepts such as person,
animal, server, bank, fox, battery, pregnancy, fraud, marriage, or biological
death. Those remain learned or separately promoted domain knowledge.

## Critical invariants

- A storage kind is never a semantic ontology type.
- Defaults are rules and never boot-time active state assignments.
- A claim schema does not admit its content as actual-world knowledge.
- Event schemas in Phase 6 do not yet authorize transitions, causality, or impact; the UOL validator enforces exact transition-use authorization.
- Function persists independently of live capability.
- Only runtime-backed self capabilities are marked available.
- Language realization remains explicitly unavailable until its later phase.
- No sentence templates or language-specific lexical forms are foundation data.
- Truth support, epistemic basis, proposition polarity, change direction, and evaluative valence remain separate axes.
- Importance/valence are assessment vocabularies, and capability status is record-scoped; none is silently materialized as ordinary holder state.
- Exact record counts and a full source-record fingerprint are contract-pinned; the contract and competence files are SHA-256 pinned by the manifest.

## Verification

```bash
python tools/verify_v350_foundation.py
```

The verifier audits `foundation_contract.json`, compiles the package twice,
requires byte-identical SQLite output, opens the first artifact as an immutable
boot database, and executes `competence/foundation.jsonl` through the canonical
Phase-5 projectors.
