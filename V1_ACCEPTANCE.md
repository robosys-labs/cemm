# CEMM v1 Acceptance Contract

## A. Authority and ABI

- [ ] Exactly five foundational operator shapes remain executable.
- [ ] New test domains require only atoms/facts/rules, not code/schema changes.
- [ ] Final language packs are self-contained and hash-valid.
- [ ] No `.v1.json` sidecars are loaded or present.
- [ ] Populated pre-final databases fail with an explicit rebuild message.
- [ ] Pack-local `CONST*` sources resolve only to authority-scoped atoms visible to the pinned generation.
- [ ] Generic concept predication compiles to subtype/definition structure, never concept-as-instance typing.

## B. Participant/deixis

- [ ] First person binds to frame speaker.
- [ ] Second person binds to frame addressee.
- [ ] Output-frame inversion changes bindings without lexical data changes.
- [ ] No `USER` or `SYSTEM` codec source classes exist.

## C. Pure cognition

- [ ] `observe()` and `compose()` perform no writes.
- [ ] Unknown forms create evidence/frontiers, not atoms.
- [ ] Stable clauses survive adjacent unknown clauses.
- [ ] No unresolved target changes global self state.

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

- [ ] Bare application queries are rejected.
- [ ] Dimension and value variables can be projected together.
- [ ] Query bindings contain proof refs and coverage.
- [ ] Support+deny yields conflict before answered/supported.
- [ ] Runtime mode cannot change discourse force.
- [ ] Claims are stored first as attributed occurrences and placements.
- [ ] Non-admitted claims do not enter world belief.
- [ ] Retractions require an explicit owned occurrence.

## F. Events/transitions

- [ ] Causal rules bind named roles, never positions.
- [ ] Transition previews include pre-state, post-delta, confidence, and proof.
- [ ] Queries and plain state descriptions produce NO transition preview.
- [ ] Predicted deltas are not committed as observations.
- [ ] Returned operation observations create prediction-error evidence.

## G. Self/capability

- [ ] `value:ready` is absent from final authority.
- [ ] Digital self exposes recursively inherited operational capabilities.
- [ ] Response capability is derivable from runtime/resource evidence.
- [ ] “How are you?” can be answered without a lexical ready fact.
- [ ] Missing capability dependencies lower/unknown the assessment rather than default positive.

## H. Goals/actions/effects

- [ ] No directive executes without reviewed `rel:handled_by_adapter` routing, a registered adapter, and permission scope.
- [ ] Missing adapter returns a decline, not fake success.
- [ ] Effect journal is idempotent.
- [ ] Operation output is evidence and is not auto-admitted.
- [ ] Re-entry is bounded.

## I. Response and common ground

- [ ] Response CSIR names the actual query/frontier/capability/operation target.
- [ ] Semantic atom, evidence literal, and number placeholders retain provenance.
- [ ] Placeholder ordering is deterministic across serialization order.
- [ ] Unverified or leaking surfaces are empty and not committed.
- [ ] Verified common ground commits the original Response CSIR, not reparsed text.

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

- [ ] Unknown parsing remains side-effect-free and never invokes acquisition.
- [ ] Every newly created lexical identity has an explicit reviewed semantic kind.
- [ ] `AutonomousAcquirer` and default-to-`concept` paths are absent.
- [ ] Designation indexing is incremental for ordinary acquisition.
- [ ] The runtime is explicitly re-pinned after reviewed authority publication.

The final test suite must run against a freshly created schema-v2 store and canonical migrated authority.
