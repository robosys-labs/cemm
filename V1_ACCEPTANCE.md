# CEMM v1 Acceptance Contract

> **Status (v3.1.3):** Items marked `[x]` are verified by the passing
> semantic-operational contract suite (`tests/test_semantic_operational_contract.py`,
> 88 tests) and/or the phrase regression suite
> (`tests/test_semantic_phrase_regressions.py`, 9 tests). Items marked `[ ]`
> remain active work or are not yet covered by an executable gate. Do not
> re-implement a checked item without first confirming the existing test no
> longer covers it — that is a regression risk.

## A. Authority and ABI

- [x] Exactly five foundational operator shapes remain executable.
- [ ] New test domains require only atoms/facts/rules, not code/schema changes.
- [x] Final language packs are self-contained and hash-valid.
- [ ] No `.v1.json` sidecars are loaded or present.
- [ ] Populated pre-final databases fail with an explicit rebuild message.
- [x] Pack-local `CONST*` sources resolve only to authority-scoped atoms visible to the pinned generation.
- [x] Generic concept predication compiles to subtype/definition structure, never concept-as-instance typing.

## B. Participant/deixis

- [x] First person binds to frame speaker.
- [x] Second person binds to frame addressee.
- [x] Output-frame inversion changes bindings without lexical data changes.
- [ ] No `USER` or `SYSTEM` codec source classes exist.

## C. Pure cognition

- [ ] `observe()` and `compose()` perform no writes.
- [x] Unknown forms create evidence/frontiers, not atoms.
- [x] Stable clauses survive adjacent unknown clauses.
- [x] No unresolved target changes global self state.

## D. State

- [ ] Every state training application has an explicit dimension source.
- [ ] Implied lexical dimensions use `DIM_OF_A*` plus reviewed `rel:value_of_dimension`; no compiler fill exists.

### State inheritance

- [ ] Recursive subtype/facet closure grants dimensions/capabilities/resources.
- [ ] A dimension not entitled to a referent is not projected.
- [ ] Continuous, categorical, and set-valued timelines preserve native domains.
- [ ] Defaults do not appear as active values.
- [ ] Concepts do not inherit instance state.

## E. Query/discourse/epistemics

- [x] Bare application queries are rejected.
- [ ] Dimension and value variables can be projected together.
- [x] Query bindings contain proof refs and coverage.
- [ ] Support+deny yields conflict before answered/supported.
- [x] Runtime mode cannot change discourse force.
- [x] Claims are stored first as attributed occurrences and placements.
- [x] Non-admitted claims do not enter world belief.
- [ ] Retractions require an explicit owned occurrence.

## F. Events/transitions

- [ ] Causal rules bind named roles, never positions.
- [ ] Transition previews include pre-state, post-delta, confidence, and proof.
- [ ] Queries and plain state descriptions produce NO transition preview.
- [ ] Predicted deltas are not committed as observations.
- [ ] Returned operation observations create prediction-error evidence.

## G. Self/capability

- [x] `value:ready` is absent from final authority.
- [x] Digital self exposes recursively inherited operational capabilities.
- [x] Response capability is derivable from runtime/resource evidence.
- [x] “How are you?” can be answered without a lexical ready fact.
- [x] Missing capability dependencies lower/unknown the assessment rather than default positive.

## H. Goals/actions/effects

- [ ] No directive executes without reviewed `rel:handled_by_adapter` routing, a registered adapter, and permission scope.
- [ ] Missing adapter returns a decline, not fake success.
- [ ] Effect journal is idempotent.
- [ ] Operation output is evidence and is not auto-admitted.
- [ ] Re-entry is bounded.

## I. Response and common ground

- [x] Response CSIR names the actual query/frontier/capability/operation target.
- [x] Semantic atom, evidence literal, and number placeholders retain provenance.
- [x] Placeholder ordering is deterministic across serialization order.
- [x] Unverified or leaking surfaces are empty and not committed.
- [x] Verified common ground commits the original Response CSIR, not reparsed text.

## J. Runtime ordering and persistence

- [ ] Stage trace is exactly ordered 0 through 22.
- [ ] Durable writes occur only at 13, 16, 17, and 21.
- [ ] `read_only` leaves all revisions and durable table counts unchanged.
- [ ] Stage-13 world CAS rejects stale writers.
- [ ] Stage-21 discourse CAS rejects stale writers.

## K. Performance

- [ ] Normal commits do not call `snapshot_hash()`.
- [ ] Runtime query does not call `base_facts()`.
- [ ] Indexed pattern retrieval independently returns correct facts.
- [ ] Relevant rule expansion respects fact/rule/depth limits.
- [ ] Workspace hard-required slots are bounded.
- [ ] Salience decay does not update every discourse row.
- [ ] World writes do not retrain language/workspace models.

## L. Training

- [ ] Every SemanticEpisode includes PRE, INPUT evidence, stable CSIR, act, placement, transition/NO_TRANSITION, and Response CSIR.
- [ ] At least one explicit NO_TRANSITION episode exists.
- [ ] Train and holdout families are disjoint.
- [ ] Held-out tests split by construction family, not random paraphrase.
- [ ] System output is supervised from original Response CSIR/frame.

## M. Reviewed lexical acquisition

- [x] Unknown parsing remains side-effect-free and never invokes acquisition.
- [x] Every newly created lexical identity has an explicit reviewed semantic kind.
- [x] `AutonomousAcquirer` and default-to-`concept` paths are absent.
- [x] Designation indexing is incremental for ordinary acquisition.
- [x] The runtime is explicitly re-pinned after reviewed authority publication.

The final test suite must run against a freshly created schema-v2 store and canonical migrated authority.

## N. Authority bundle and document integrity

- [x] All canonical data files are linked before the first durable import write.
- [x] A missing cross-file atom/rule constant fails with zero database delta.
- [x] Generic meta-relations and generic rules exist only in foundational authority.
- [ ] `rel:state_dimension` and `rel:state_value` are declared foundational relation atoms.
- [ ] Every implied state specification binds exactly one dimension and one value.
- [x] Concept hierarchy facts use `rel:subtype_of`, never concept-as-instance `op:type`.
- [x] Reviewed source corpora and compiled packs pass the same semantic integrity release gate.
- [x] Trainer and runtime use identical deterministic pointer ordering.

## O. Multi-resolution form and grounding

- [x] Surface normalization is reversible and isolated outside semantic authority.
- [x] Multiple form/span/designation/referent candidates survive into semantic composition.
- [x] No core-loop regex, keyword, punctuation or exact phrase branch decides meaning.
- [ ] Ambiguous labels do not silently merge identities or select a winner before settling.
- [ ] State/type/context factors change candidate energy or clamp invalid candidates before Stage 10.
- [x] An unknown span preserves grounded structure inside the same clause.
- [ ] Embedded/mixed discourse acts retain scope rather than being flattened.

## P. Designation and chained-property competence

- [x] `label:name` is a foundational designation family.
- [x] Full names and aliases are subtypes of `label:name`.
- [x] A name query is represented as designation QueryCSIR and returns literal bindings with proof.
- [x] The same query machinery handles aliases, titles, identifiers and localized labels.
- [ ] Chained property/dimension queries preserve every graph edge, context, time and proof.
- [x] No phrase-specific name/property handler exists.

