# CEMM Minimal Semantic Brain MVP

This bundle is an executable architectural proof for a small, non-bloated CEMM core.

The invariant kernel is under 500 Python lines and contains no family, office, medical, or other domain concepts. Domain knowledge grows through atoms, exact semantic applications, reusable rules, designations, evidence, and language-training data — not new Python classes or predicate schemas.

## Core invariant

```text
CODE KNOWS                     DATA KNOWS
---------------------------    ------------------------------------------
5 universal operators          entities / concepts / relation types
fixed universal roles          state dimensions / values / event types
exact validation               multilingual designations
content identity               learned definitions and entailments
bounded rule execution         causal/default rules
referent ranking               language evidence/examples
Transformer codec              realization examples
```

The five operator shapes are:

```text
op:designation
op:type
op:relation
op:state
op:event
```

Importing an entirely new domain does not add operators or operator-role schema.

## Family inference demonstration

Learned knowledge is supplied in `knowledge/family_knowledge.json`.

Input:

```text
My mother in-law arrived today.
```

Question:

```text
Am I married?
```

The runtime answers:

```text
Yes.
```

The proof is composed generically:

```text
mother_in_law_of(M, user)
  -> exists P: mother_of(M, P) AND partner_of(P, user)
  -> partner_of(P, user)
  -> spouse_of(P, user)                   [generic subrelation rule]
  -> marital_state(user) = married        [generic relation-state rule]
```

The same closure also derives:

```text
mother_of(M, P)
  -> female(M)                             [generic participant-type rule]
  -> human(M)                              [generic type transitivity]
  -> living_entity(M)                      [generic type transitivity]
```

None of those derived facts are persisted merely because they were queried.

## Anti-bloat rules

1. **No concept-specific schema.** `mother_in_law`, `wife`, `spouse`, `president`, `temperature`, etc. are atoms/data.
2. **Only irreducible compositional meanings need domain rules.** Repeated patterns use reusable meta-relations and generic rules.
3. **Derived closure is ephemeral by default.** Queries do not materialize every inferred consequence.
4. **Applications are content-addressed.** Reasserting the same exact semantic application does not duplicate it.
5. **Rules are semantically deduplicated.** The same antecedent/consequent cannot be stored repeatedly under different names.
6. **Causal rules are not ordinary truth entailments.** They are stored in the same rule substrate but excluded from actual-world closure.
7. **Dynamic ranking is not authority.** Label-use counts and discourse salience affect resolution but are excluded from the semantic snapshot hash.
8. **Language models cannot invent structural kinds freely.** Only data-declared creatable structural kinds may be instantiated.

## Multilinguality

Exact meaning is shared across languages. The bundle demonstrates:

```text
English observation:
  My mother in-law arrived today.

Spanish question over the same stored meaning:
  ¿Estoy casado?

Answer:
  Sí.
```

Labels/designations are semantic facts. Multiple language-specific surfaces may point to one exact atom.

## Run

Requires Python and PyTorch.

```bash
python cemm_mvp.py init \
  --db demo.sqlite \
  --data knowledge/base.json \
  --data knowledge/family_knowledge.json

python cemm_mvp.py learn --db demo.sqlite "My mother in-law arrived today."
python cemm_mvp.py ask   --db demo.sqlite "Am I married?"
python cemm_mvp.py ask   --db demo.sqlite "Is she a human?"
python cemm_mvp.py ask   --db demo.sqlite --language es "¿Estoy casado?"
```

## Tests

```bash
python -m unittest discover -s tests -v
```

The regression suite covers schema non-growth, family inference/proof, non-persistent closure, causal isolation, type-lattice reuse, multilingual reuse, semantic coreference, same-name ambiguity, rule deduplication, state supersession, replay stability, unknown-vs-false, and language-program hardcoding checks.

## Important scope boundary

`family_knowledge.json` represents **already learned semantic knowledge** compiled from teaching. This MVP proves that once those meanings are learned, they compose and infer generically. It does not claim to induce arbitrary logical rules directly from unrestricted teaching sentences yet.
