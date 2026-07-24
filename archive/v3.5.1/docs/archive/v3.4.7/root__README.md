# CEMM — Contextual Event Memory Model

CEMM is an experimental **grounded semantic kernel**: a small multilingual system intended to build meaning from evidence, referents, predicates, and typed operational ports; learn new semantic structure; reason under bounded rules; plan actions; and generate only responses it can semantically justify.

> **Current status:** this delivery contains the bounded v3.4.7 reference implementation and makes `cemm.v347` the canonical semantic authority. The complete architecture-conformance gate passes with zero findings and the combined acceptance/metamorphic suite contains 58 passing tests. This is a working baby-CEMM substrate, not a claim of general intelligence or unlimited language/world competence.

---

## The central idea

CEMM does not treat a complete sentence pattern as meaning.

```text
Observation
  → language/multimodal evidence lattice
  → Referent candidates
  → active predicates and local operational ports
  → UOL meaning hypotheses
  → compatible MeaningBundle
  → knowledge, learning, inference, goals, or operations
  → response-goal candidates
  → UOL response plan
  → target-language realization
```

Language analyzers, NER systems, parsers, databases, embeddings, vision models, and optional statistical/LLM components may propose evidence. The semantic kernel alone selects meaning.

---

## One term for semantic objects: Referent

A **Referent** is any identity-bearing thing CEMM can point to, track, mention, bind to a predicate port, remember, or reason about.

Referents include:

- self, people, animals, organizations, physical and digital objects;
- places;
- events, actions, and processes;
- propositions;
- states;
- quantities and units;
- times and intervals;
- collections, contexts, information objects, and schema concepts when discussed.

They remain distinct through `ReferentKind`, type schemas, identity rules, and specialized payloads. They are not flattened into one undifferentiated object type.

Predicates connect referents through **local typed ports**. For example, the `named` predicate owns ports such as `named.holder` and `named.name`; an operation such as `move` owns ports such as `move.object` and `move.destination`.

---

## UOL

UOL is CEMM’s **Universal Operational Language**.

A cycle-local `UOLGraph` holds multiple candidate referents, predications, propositions, scopes, discourse relations, open ports, and assumptions. The graph is a temporary workbench, not a permanent sentence graph.

The selected compatible subgraph is a `MeaningBundle`. Durable changes are proposed through a `GraphPatch`, which carries provenance, scope, permissions, expected revisions, validation requirements, and rollback information.

Outbound communication is first built as a `UOLResponsePlan`; only then is it realized in the target language.

---

## What “understands” means

CEMM may assert a clause only when it has an explicit semantic proof:

- the relevant user meaning or system goal was selected;
- the response exists as UOL;
- predicate and realization schemas are active;
- required ports are filled;
- referents are grounded or deliberately mentioned/quoted;
- epistemic policy permits the context, certainty, and attribution;
- any inference has an admissible proof and consequence status;
- the target-language realization covers the full semantic contribution.

Fluent output is not treated as evidence of understanding.

---

## Why v3.4.7 is a breaking cutover

The audited v3.4.6 path still relies heavily on declarative ordered construction matches to produce predications. Later “forest,” context, and response layers enrich or rank candidates that the construction path already made available.

v3.4.7 replaces that authority with:

- N-best language and structural analysis;
- mention and Referent candidate resolution;
- predicate activation from lexical, structural, type, context, and multimodal evidence;
- local port projection and bounded binding;
- joint referent/port resolution;
- compatible multi-proposition bundle selection;
- typed gaps and error attribution;
- GraphPatch-controlled learning and knowledge;
- rule-class-aware bounded inference;
- semantic goal, operation, and response planning.

The construction matcher remains useful only as a language-specific evidence provider for grammar, idioms, and argument realization.

---

## Canonical documents

Read these in order:

1. [`AGENTS.md`](AGENTS.md) — binding implementation and review rules.
2. [`architecture.md`](architecture.md) — canonical semantic architecture and terminology.
3. [`coreloop.md`](coreloop.md) — end-to-end runtime authority and stage contract.
4. [`3.4.7-upgrade-fixes-plan.md`](3.4.7-upgrade-fixes-plan.md) — migration phases, tests, and release gates.

Older plans and architecture documents are historical unless explicitly incorporated into these files.

---

## Working baby CEMM target

The first authentic release is intentionally small but must be real. It must be able to:

- analyze and realize at least two typologically different languages through the same semantic contracts;
- answer its name and the expansion of CEMM from seeded knowledge;
- learn and remember a user’s full name and age;
- understand conjunctions and answer multi-part queries;
- resolve references to people, objects, places, events, propositions, states, and time;
- distinguish an unknown word from an unresolved reference;
- conduct a bounded multi-turn teaching dialogue;
- learn a scoped concept, relationship, predicate, or rule grounded in existing foundations;
- distinguish strict, causal, enabling, default, statistical, and sensitive rules;
- produce proof-bearing bounded inferences;
- plan one safe operation with bound semantic ports;
- use session multimodal state in reference resolution;
- generate and rank multiple response goals;
- block any output clause that is not fully authorized.

Passing one exact chat transcript is not sufficient. Paraphrase, structural mutation, minimal-pair, cross-language, and discourse tests are release requirements.

---

## Foundation data

A teachable CEMM requires a small but operationally complete seed package covering:

- ReferentKinds and identity;
- predicate families and local ports;
- state and transition;
- quantities, units, conversions, and time;
- place, event participation, and relationships;
- causal/conditional and relation algebra;
- epistemic, discourse, learning, goal, capability, permission, and operation concepts;
- self identity, `CEMM`, and `Contextual Event Memory Model`;
- response-goal and realization competence schemas.

Reviewed foundation and language source packages may be JSON/YAML. Runtime and learned records live behind durable indexed storage interfaces.

---

## Learning and inference

CEMM learns semantic contributions rather than memorizing sentences.

New learning begins in narrow scope and must connect to known Referents or exact typed frontier dependencies. A learning transaction may recursively ask what kind of thing a term denotes, what ports a predicate has, what relation class applies, what exceptions exist, or how the concept is expressed in a language.

Recursive learning and inference are bounded by time, depth, record, firing, existential, interaction, and sensitivity budgets.

The system distinguishes:

- identity and constitutive structure;
- strict implication;
- prerequisite and enablement;
- causation;
- defaults and typicality;
- statistical association;
- pragmatic and normative rules.

For example, a president is better represented as an institutional role occupied by a person/agent in a jurisdiction and valid interval—not simply as a child kind of person. “Usually in the capital” is a default, not a location fact. Relationship status likewise must not silently imply co-residence or sensitive personal activity.

---

## Repository status vocabulary

Project reports use five separate terms:

- **specified** — required by the active architecture;
- **implemented** — code/data exists;
- **wired** — the canonical runtime invokes it;
- **authoritative** — no competing path can make the same decision;
- **verified** — end-to-end and metamorphic tests prove it.

A component is not complete merely because its class exists or a demo phrase passes.

---

## Development setup

The current project metadata targets Python 3.11+.

```bash
python -m venv .venv

# Linux/macOS
source .venv/bin/activate

# Windows PowerShell
# .venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Run the available test suite:

```bash
pytest -q
```

Run the command-line interface:

```bash
python -m cemm --chat
```

Run one turn:

```bash
python -m cemm --once "What is your name?"
```

Run the semantic architecture audit:

```bash
python -m cemm.v347.audit --eval "What is your name?"
```

Run the complete release checks:

```bash
python -m compileall -q cemm
python -m cemm.v347.conformance
pytest -q
```

Where the web demo module is present:

```bash
python -m cemm.web_demo --debug
```

The CLI uses the canonical `cemm.v347.runtime.Runtime`. Use the semantic audit command below to inspect selected meaning, gaps, truth assessments, patch commits, and emission proof.

---

## Contribution rules

Before implementing a fix, identify the authority that owns the failure:

- evidence/form analysis;
- Referent grounding;
- schema activation;
- port binding and composition;
- MeaningBundle selection;
- gap/error attribution;
- knowledge/epistemics;
- learning;
- inference;
- goals/operations;
- response selection;
- UOL planning;
- realization/emission.

Do not add an exact sentence, fallback response, English kernel regex, direct store write, or special response branch to hide a lower-level problem.

Every semantic fix should include:

- semantic trace assertions;
- nearby paraphrases and structural variants;
- a negative/minimal-pair test;
- cross-language coverage where applicable;
- architecture lint/import checks;
- honest status reporting.

See [`AGENTS.md`](AGENTS.md) for the binding contract.

---

## v3.4.7 completion profile

The canonical implementation now includes the full architectural spine:

1. one universal Referent family, UOL graphs, bundles, and GraphPatch commits;
2. durable schema/rule lifecycle, use profiles, dependency invalidation, truth maintenance, and temporal validity;
3. multilingual and multimodal evidence lattices with lineage-preserving analyzer fusion;
4. discourse/session-world tracking and bounded joint Referent/port resolution;
5. generalized grounded schema/rule learning and ordinary-path promotion/hydration;
6. strict, defeasible, causal, enabling, probabilistic, sensitive, inverse, symmetric, and transitive reasoning contracts;
7. semantic goals, live capability evidence, operation authorization, effect reconciliation, and ledgers;
8. response-goal selection, UOL response planning, semantic reference/tone planning, round-trip checking, and emission proof;
9. executable conformance, restart, cross-language, multimodal, metamorphic, determinism, safety, and release tests.

Expansion after v3.4.7 should add reviewed schemas, languages, analyzers, adapters, competence cases, and domain data through these contracts. It must not create a parallel interpreter, sentence-level authority, direct persistence path, or surface-language kernel branch.

---

## License and project maturity

CEMM is research-oriented, early-stage software. Its architecture uses cognitive terminology to describe software records and processes; it does not claim subjective consciousness or human-equivalent understanding.
