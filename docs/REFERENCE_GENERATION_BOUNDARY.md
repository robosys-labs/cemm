# Reference generation boundary

## Admitted capability

`FoundationRuntime.generate_reference_english(turn)` can emit an English
sentence **only for a single factually supported, proof-bearing binary
relation query**, using reviewed source designations for both grounded
entities and the relation predicate.

The generation path is:

```text
Text question → canonical ORIENT / PROPOSE / VERIFY
  → exact R3 QUERY proof + single bound ResponseMeaning
  → generic English S–V–O reference production from reviewed lexical facts
  → read-only reparse via the SAME canonical interpreter
  → identical SemanticExpression + unchanged RevisionPin?
      yes: ReferenceGeneration(status="verified", surface=...)
      no:  ReferenceGeneration(status="unadmitted", surface=None)
```

No previous sentence template, keyword family, inferred unreviewed synonym,
internal semantic reference or free-form generative string is permitted. The
reference output is independent of surface-specific source code: changes
of subject, relation and object are driven entirely by exact reviewed
designations and typed roles. All returned positive candidates are gated by
exact canonical-expression equality and attached R3 proof identity.

## Deliberately excluded

This is **not** general linguistic realization or an admitted neural R5
decoder. It cannot currently express quantified or conditional statements,
logical scope, tense/aspect, negation, modal uncertainty, nested attribution,
multiple answer bindings, multiword lexical entries, contextual pronouns,
explanations, first/second-person inflection or multilingual output.

Unsupported expressions and vocabulary are not paraphrased. They produce
typed unadmitted results, and never publish a user-facing sentence.

## Safety and evaluation

- `tests/test_foundation_reference_generation.py` uses independently
  reviewed binary-relation world evidence and independently specified
  expected sentences for multiple entity/relation configurations.
- `SemanticSurfaceOracle` performs read-only exact graph reconstruction
  and refuses stale semantic, world, session and effect revisions.
- The generator does not install authority, accept teaching, train models,
  or run EVALUATE/EFFECT again.
- Shared-parser false equivalence remains possible. Before any general R5
  admission, add independent compositional semantic gold, adversarial
  grammatical transformations and blind parser-differential benchmarks.
- The old marker/template realizer stays unadmitted; no R5 completion
  receipt is forged by this reference generator.

This is a **bounded, executable end-to-end cognitive-and-language canary**,
not a claim of open-domain conversational intelligence.
