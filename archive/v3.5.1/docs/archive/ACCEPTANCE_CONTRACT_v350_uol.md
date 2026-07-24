# CEMM v3.5.1 Acceptance Contract

**Status:** canonical executable competence/release contract  
**Purpose:** prove that CEMM is a working learning-first semantic system rather than a larger set of rules, gates, templates, or release artifacts.

Tests must primarily assert semantic structures, bindings, state effects, frontiers, proofs and authority—not exact wording.

---

# Gate A0 — Documentation and authority integrity

Must prove:

```text
one active implementation roadmap
one canonical core loop
one runtime plan
CORE_ISSUES exists
superseded plans are archived/non-authoritative
no broken canonical references
```

---

# Gate A1 — Stabilized runtime substrate

Required:

```text
0 release hashes per normal turn
0 boot hashes per normal turn
0 full overlay scan for O(1) write
no RecordKind-wide hot lookup
no global lock across semantic solve
no per-turn full learning promotion scan
stable runtime observation does not persist per request
authority generation separate from mutable world/discourse revisions
concurrent reads overlap
typed final completion status
```

---

# Gate A2 — Architectural prohibition tests

CI fails if public kernel/runtime contains:

- transcript-specific phrase routing;
- language-specific semantic word branches;
- direct `who/what/where/why/how` → completed response intent mapping;
- predicate-specific answer sentences;
- generic targetless acknowledgement as success;
- event-specific state mutators;
- subject/object universal effect rules;
- source-code type additions required for learned domain types;
- defaults inserted as active state;
- claims automatically treated as actual facts;
- hidden legacy semantic fallback;
- floating executable semantic dependencies.

---

# Gate A3 — CSIR exactness

Required property tests:

```text
canonical labeling independent of insertion order
serialization round trip
alpha-renaming invariance
graph-isomorphism identity
scope distinction
context distinction
time/aspect distinction
polarity/modality distinction
role-binding distinction
proof-lineage stability
exact closure reconstruction
```

Equivalent meaning normalizes equivalently under the same authority generation.

Distinct meaning does not collapse.

---

# Gate A4 — Participant grounding and reference

Prove:

```text
speaker/addressee from ParticipantFrame
pronouns contribute discourse-role requirements
synthetic renamed pronouns preserve same grounding behavior
proper names/aliases do not become kernel branches
pronoun/coreference can remain ambiguous
```

Required conversation:

```text
I have a box.
It is blue.
What color is it?
```

Answer binding must resolve the box color through discourse-compatible reference.

---

# Gate A5 — English compositional semantic kernel

Minimum reviewed English package must support:

```text
identity/classification
property/state predication
possession
simple relation
simple event
negation
modality/capability
WH query
yes/no query
correction
definition/teaching
greeting
request/imperative
```

### Synthetic rename test

Rename content vocabulary while preserving language/construction authority.

Expected:
- equivalent CSIR;
- no new kernel code;
- no phrase-specific patch.

---

# Gate A6 — Query separation

Keep separate:

```text
information gap
variable
restriction graph
answer projection
discourse act
response obligation
```

Embedded interrogatives must not automatically become top-level ask acts.

Internal role labels must never be returned as answers.

---

# Gate A7 — Conversational memory and epistemic admission

### Case A — participant fact

```text
My name is Chibu.
What's my name?
```

Expected:
- claim occurrence;
- speaker referent grounding;
- scoped admission under participant-fact policy;
- answer `Chibu` semantically;
- no `target`/`holder`/`possessor` leakage.

### Case B — correction

```text
My name is Chibu.
No, my name is Chibueze.
What's my name?
```

Expected:
- prior claim retained in history;
- new current belief selected;
- answer reflects correction.

### Case C — high-risk assertion

A high-impact world claim remains attributed/corroboration-required unless policy admits it.

---

# Gate A8 — Definition/teaching without concept-specific code

Teach:

```text
A zorb is a toy.
The zorb is blue.
```

Then ask:

```text
What is a zorb?
What color is the zorb?
```

Expected:
- generic definitional/classification semantics;
- reusable learned/scoped structure;
- no `zorb` source-code branch;
- restart behavior according to promotion/retention policy.

---

# Gate A9 — Partial cognition

Unknown material around known meaning must not erase grounded structure.

Example:

```text
My zorb is florp.
```

When `my`, possession and `zorb` are known but `florp` is not:

Expected:

```text
known participant/possession structure preserved
unknown semantic frontier for florp
clarification/learning possible
no fabricated property meaning
```

---

# Gate A10 — Discourse and common ground

Required follow-ups:

```text
Why?
For what?
What did you mean?
Understood what?
What happened to it?
Can it still move?
```

Tests assert that the correct prior semantic target is selected by discourse/type/context compatibility.

No exact transcript sequence handler.

---

# Gate A11 — Self/runtime capability honesty

Queries such as:

```text
How are you?
What can you do?
```

must use actual self/runtime state and active capabilities.

Expected:
- no invented human emotions;
- unavailable adapter means unavailable/unknown capability, not a fabricated positive claim;
- capability, permission and competence remain distinct.

---

# Gate A12 — Learning end-to-end

A learning test is valid only when it proves:

```text
unknown/frontier
→ candidate induction
→ exact dependency closure
→ supporting/opposing evidence
→ competence
→ promotion decision
→ immutable new authority generation
→ restart
→ unseen compositional reuse
```

### New type

Teach a previously unknown type and compatible properties/capabilities.

After promotion/restart:
- type inheritance works;
- mention grounds;
- entitled state dimensions apply;
- no source-code type addition.

### New lexicalization

Teach a new surface for an existing semantic definition.

After promotion/restart:
- new surface resolves to existing semantics;
- synthetic rename behaves equivalently.

### Counterexample

Teach an exception and prove a default is defeated without deleting the reusable schema.

---

# Gate A13 — Recurrent semantic dynamics

Required:

```text
deterministic baseline oracle
typed relation-specific messages
hard constraint mask
bounded iterations
convergence assessment
partial output on budget exhaustion
calibrated probabilities only where calibration exists
```

Reference cases must converge to the same canonical semantic class as the exact baseline or document valid ambiguity.

---

# Gate A14 — State entitlement

Examples:

- living animal: biological health applicable;
- proposition: biological health inapplicable;
- digital agent: runtime/capability dimensions may apply;
- room: temperature applies, mood does not;
- server: thermal state may affect processing capability through a mechanism.

Defaults do not create active state assignments.

---

# Gate A15 — Claims/context safety

Required contrasts:

```text
John says the fox died.
I saw the fox die.
The fox did not die.
The fox may die.
The fox almost died.
The fox died in the story.
```

Expected:
- correct proposition/claim/context/polarity/modality;
- no inappropriate actual-world transition.

---

# Gate A16 — Role-sensitive event/transition

Equivalent active/passive forms produce equivalent role-bound CSIR and transition candidates.

Effects target semantic roles, not grammatical positions.

Cross-type polysemy must not force one event effect universally.

---

# Gate A17 — Causal reasoning

Prove separation of:

```text
temporal order
correlation
default expectation
causal mechanism
intervention
counterfactual
```

Required:
- defeater test;
- context isolation;
- recursive propagation cycle bound;
- proof-bearing explanation path.

---

# Gate A18 — Response CSIR and realization

One realization grammar family must handle arbitrary compatible content for:

```text
identity/property/state
relation
query answer
negative modality
past/completed event
uncertainty qualification
clarification
capability report
```

Adding a new learned concept/property/value must not require a new whole-sentence template.

Realization cannot invent missing semantics.

---

# Gate A19 — Semantic preservation and emission

Every emission requires:

```text
valid response semantics
realization proof
qualification preservation
privacy/safety/audience/channel checks
emission authorization
journal/idempotency where required
observed boundary result
```

Full independent round trip is required for:
- release competence;
- novelty/risk/policy cases;
- configured audit sampling.

No verifier bypass.

---

# Gate A20 — Restart, versioning, invalidation, replay

Required:

```text
historical record rehydrates under original authority
promoted learned artifact rehydrates exactly
authority generation change invalidates only dependencies
world/discourse writes do not redefine semantic meaning
replay requirements are explicit
no floating latest resolution
```

---

# Gate A21 — Performance/concurrency

Set concrete numeric budgets from Phase-0 baseline, but structural rules are mandatory:

```text
steady state = O(semantic work + bounded indexed reads)
not O(release size + boot size + overlay history + all record kinds)
```

Required:
- 1/4/16/64 request concurrency tests;
- 1k/10k/100k overlay scale tests;
- solver candidate/iteration budgets;
- no hidden global serialization.

---

# Gate A22 — Legacy isolation/cutover

Release rejected if:

```text
public runtime imports legacy semantic authority
CSIR failure falls back to UOL
legacy store is lazily queried for meaning
signed artifact contains unapproved legacy adapter
migration and runtime authority are combined
```

Migration tooling may remain offline/read-only.

---

# Final release gate

CEMM v3.5.1 is releasable only when:

```text
A0–A22 pass
+
critical/high CORE_ISSUES are VERIFIED or migration-only with zero public authority
+
English Conversational Kernel passes
+
learning→promotion→restart passes
+
performance/concurrency gates pass
+
signed release artifacts are regenerated deterministically after behavior is proven
```
