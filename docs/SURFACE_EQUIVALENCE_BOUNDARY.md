# Reference surface-equivalence boundary — NOT R5 activation

The foundation now includes a bounded **candidate checker** for positive,
actual, proof-supported QUERY answers. It does not train or generate language,
activate the historical neural model or claim general English competence.
`HybridRuntime` remains the single owner of semantic interpretation.

## Exact verification

1. Accept a canonical, persisted `FoundationTurn` produced by the existing
   ORIENT → PROPOSE → VERIFY → EVALUATE → EFFECT path.
2. Require its verified `ResponseMeaning` to be a supported, positive,
   actual, scope-free, proof-bearing `answer`. Reject unknown, contested,
   simulated, denied, partial or attributed-only response meanings.
3. Verify the original authority/model identities and current world revision.
   A response against stale evidence cannot be reused.
4. Re-interpret externally supplied candidate text in a **read-only** call
   through exactly the existing ORIENT → PROPOSE → VERIFY owners. The
   candidate must be a declarative OBSERVE surface, never a question or
   attempted operation.
5. Require one unambiguous, selected canonical `SemanticExpression` whose
   `expression_ref` is identical to the evaluated bound answer expression.
6. Recheck all world/session/effect revision pins; all calls must leave
   persistent state exactly unchanged. No EVALUATE/EFFECT runs for candidates.

This approach compares *meaning*, not keyword markers, response family,
internal semantic-ref spellings, normalized input hashes or canned templates.

## Supported and intentionally unsupported

The admitted reference fragment is currently binary, grounded relation
propositions such as a reviewed relation between `entity:alice` and
`entity:book`. Its source query may be expressed with a subject variable,
and its candidate answer must compile to the same grounded expression.
Review-approved lexical synonyms can express the exact same meaning using
independently verified derivations. Source proof remains on the original
structured `ResponseMeaning`.

This is **not** a complete realizer: it does not produce sentences, support
scope-rich statements, pronoun perspective, attribution qualifiers, multiple
bindings, temporal predicates, quantified grammar, negation, explanatory
argumentation or other general discourse acts. Those remain separate
acceptance contracts. Current R3 `CycleResult` continues to record the
unadmitted `contract:r5:realize_surface` gap.

## Evidence and limitations

- `test_foundation_surface_equivalence.py` checks exact matching,
  wrong referents/relations, direction, unlicensed quantification, multiple
  statements, discourse-act mismatch, unknown answers and stale world state.
- `test_foundation_surface_learning_integration.py` checks that a new
  reviewer-approved synonym can be represented both as the new surface and
  as the previously reviewed synonym, and independently reparsed as the
  identical fact after process restart.
- `SemanticSurfaceOracle` has zero write authority and uses
  `HybridRuntime.verify_surface_read_only`; production resource ceilings and
  realized-surface auditing still require explicit budgets and review.
- Since its verifier uses the same form/contribution/proposal machinery as
  the original input, **shared parser defects could yield false equivalence**.
  Independent human-reviewed semantic gold, adversarial evaluation and
  systematic parser-differential testing remain mandatory before R5 admission.

Do not replace the R5 completion gate with this checker or with a fixed set
of English templates. This is a testable dependency for future grounded
generation, not a production generative feature.
