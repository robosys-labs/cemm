# R4 Closure Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce one truthful pass or stop outcome for the twelve fixed R4
closure cases while proving practical semantic behavior through existing
owners only.

**Architecture:** Extend the existing R3/R4 predecessor regression owner with
one bounded vertical matrix. Diagnose the earliest divergent artifact, repair
one existing owner at a time, and rerun the whole matrix after each repair. The
public runtime remains stopped at the unadmitted R5 realization boundary;
surface checks use only an existing independently reviewed offline compiler and
must stop if exact semantic round-trip authorization is unavailable.

**Tech Stack:** Python 3.12, pytest, the existing six-phase HybridRuntime,
Program ABI 2, Semantic Expression ABI 1, Response Meaning ABI 2, SQLite test
stores, and existing R4 realization-supervision/compiler code.

---

## Non-negotiable execution rules

**Scope exclusions:** no source package and no R5 activation.

- Keep one active blocker at a time.
- Permit a maximum three owner-level fixes and maximum three implementation
  commits.
- Add no ABI, phase, gate, service, runtime owner, review UI, source package,
  model, training run or generated corpus.
- Do not edit `data/scenarios/`, `artifacts/review_drafts/`, active selection
  files, purpose partitions or training artifacts.
- Do not use `RealizationVerifier`, `SafeRealizer` or
  `NeuralConstrainedRealizer` as proof of exact surface equivalence: their
  module contract explicitly says they are pre-R5 marker diagnostics.
- A commit is eligible only when it moves at least one named closure case
  through the earliest previously failing semantic boundary.
- After every eligible fix, run the entire fixed matrix. If the next failure is
  owned elsewhere, stop and classify it before editing anything else.

## Current observed baseline

The unmodified development runtime was probed on 2026-09-03 with an isolated
temporary SQLite store:

| Case | Current earliest result |
|---|---|
| What is CEMM? | reaches ResponseMeaning; R5 surface owner unavailable |
| What is zorbulate? | PROPOSE abstains: `proposal:critical_residual` |
| Can you learn aliases? | reaches ResponseMeaning; R5 surface owner unavailable |
| You said what? | PROPOSE abstains: `proposal:no_complete_candidate` |
| That you learn. with context | not yet proven with an exact context fixture |
| That you learn. without context | PROPOSE abstains: `proposal:no_complete_candidate` |
| Alice does not like the book. | PROPOSE abstains: `proposal:critical_residual` |
| The server is online and offline. | reaches conflict ResponseMeaning |
| If server online then lamp on. | VERIFY rejects all candidates |
| The server is offline. You said goodbye. | VERIFY rejects all candidates |
| Set the state without permission. | PROPOSE abstains: `proposal:critical_residual` |
| invalid Program ABI 2 mutation | existing direct-verifier rejection must be selected and reused |

This table is diagnostic evidence, not an expected-gold shortcut. Acceptance
tests below encode required meaning and practical behavior, never these failing
statuses.

### Task 1: Freeze the fixed vertical matrix in the existing test owner

**Files:**

- Modify: `tests/test_r3_r4_predecessor_regressions.py`
- Read: `tests/test_program_abi2.py`
- Read: `tests/test_r1_verification_batch.py`
- Read: `src/cemm_authoritative_hybrid/runtime.py`

- [ ] **Step 1: Add the exact case description type and fixed rows**

Add a frozen test-only value type and exactly twelve rows. The context row must
name its setup action explicitly; no row may infer expected behavior from the
runtime output.

```python
@dataclass(frozen=True)
class _ClosureCase:
    case_ref: str
    surface: str | None
    context_setup: str
    expected_mode: SemanticMode | None
    expected_action: str


_CLOSURE_CASES = (
    _ClosureCase("known_definition", "What is CEMM?", "fresh", SemanticMode.QUERY, "answer"),
    _ClosureCase("unknown_designation", "What is zorbulate?", "fresh", SemanticMode.QUERY, "unknown"),
    _ClosureCase("capability_query", "Can you learn aliases?", "fresh", SemanticMode.QUERY, "answer"),
    _ClosureCase("history_query", "You said what?", "record_system_goodbye", SemanticMode.QUERY, "answer"),
    _ClosureCase("fragment_resolved", "That you learn.", "open_meaning_question", SemanticMode.OBSERVE, "answer"),
    _ClosureCase("fragment_unresolved", "That you learn.", "fresh", SemanticMode.OBSERVE, "clarify"),
    _ClosureCase("negated_relation", "Alice does not like the book.", "fresh", SemanticMode.OBSERVE, "acknowledge_observation"),
    _ClosureCase("state_conflict", "The server is online and offline.", "fresh", SemanticMode.OBSERVE, "clarify"),
    _ClosureCase("linked_simulation", "If the server is online, then the lamp is on.", "fresh", SemanticMode.SIMULATE, "answer_simulation"),
    _ClosureCase("multiple_roots", "The server is offline. You said goodbye.", "fresh", SemanticMode.OBSERVE, "acknowledge_observation"),
    _ClosureCase("permission_denial", "Set the state without permission.", "remove_set_state_permission", SemanticMode.REQUEST, "deny"),
    _ClosureCase("invalid_program", None, "mutate_valid_program", None, "verification_rejected"),
)
```

Do not implement the named setup actions with phrase-specific branches. Use
the existing session/focus, permission and direct-verifier test seams already
exercised in `tests/test_discourse_reference.py`,
`tests/test_effect_gateway.py`, `tests/test_capability_derivation.py` and
`tests/test_program_abi2.py`. If one seam cannot represent the setup, record
that existing owner as the blocker instead of adding a fixture-only owner.

- [ ] **Step 2: Add one structural invariant helper**

```python
def _assert_selected_semantic_path(result) -> None:
    assert result.proposal.status == "candidates"
    assert result.verification.status == "selected"
    meaning = result.verification.selected_meaning
    assert meaning is not None
    assert meaning.expression.expression_ref
    assert result.evaluation is not None
    assert result.effect_receipt is not None
    assert result.response_meaning is not None
    assert result.response_meaning.response_expression.expression_ref
```

The invalid-program row instead calls the existing exact verifier directly and
asserts one typed rejection without invoking phrase processing.

- [ ] **Step 3: Write the first RED acceptance tests**

Start with three rows only: known definition, unknown designation and invalid
Program mutation. Assert the useful outcome, including that `zorbulate`
survives as a literal in the selected expression and that the unknown response
is not an acknowledgement.

```python
assert "zorbulate" in json.dumps(
    result.response_meaning.response_expression.as_dict(),
    sort_keys=True,
).casefold()
assert result.response_meaning.discourse_action == "unknown"
assert result.response_meaning.discourse_action != "acknowledge"
```

- [ ] **Step 4: Run the focused RED test**

Run:

```powershell
python -m pytest tests/test_r3_r4_predecessor_regressions.py -k "closure" -vv -p no:cacheprovider
```

Expected: known definition and the reused invalid-program rejection pass;
unknown designation fails first at PROPOSE with
`proposal:critical_residual`. Do not edit VERIFY, cognition or realization
while this is the earliest divergence.

### Task 2: Prove whether the unknown-designation query is representable

**Files:**

- Read: `src/cemm_authoritative_hybrid/proposal_context.py`
- Read: `src/cemm_authoritative_hybrid/recursive_composer.py`
- Test: `tests/test_r3_r4_predecessor_regressions.py`
- Test: `tests/test_proposal_context_builder.py`

- [ ] **Step 1: Add the narrow ProposalContext RED assertion**

For `What is zorbulate?`, assert that existing form evidence yields a bounded
designation-query application frame over the literal and open variable, while
creating no semantic atom or designation slot for `zorbulate`.

```python
assert not any(slot.target_ref.endswith(":zorbulate") for slot in context.designation_slots)
assert any(slot.kind == "literal" and slot.literal_value == "zorbulate" for slot in context.contribution_slots)
assert any(slot.kind == "open_variable" for slot in context.contribution_slots)
assert any(frame.operator_ref == "op:designation" for frame in context.application_frames)
```

- [ ] **Step 2: Audit the existing frame contract before changing code**

Confirm whether the active `ApplicationFrameSlot` can legally represent an
unresolved predicate without either a reviewed designation slot or an invented
semantic target. The present source requires both a nonempty
`designation_slot_ref` and `predicate_target_ref`, while this case correctly
has neither. Do not work around that constraint with a fake ref, literal-derived
atom, implicit `concept:zorbulate`, or an in-place ABI shape change.

The semantic evidence that must eventually compose is:

```text
binder(definition/predication) + literal(unknown span) + open_variable(query)
```

The literal must own `role:surface`; the open variable must own the queried
semantic target. If no active frame/schema can carry those ports without a
designation target, the closure slice has found a ProposalContext/composer
architecture blocker and must take the stop outcome. A new ABI may be proposed
only after this plan stops; it cannot be introduced inside the closure slice.

- [ ] **Step 3: Run context and vertical tests**

Run:

```powershell
python -m pytest tests/test_proposal_context_builder.py -k "unknown and designation and query" -vv -p no:cacheprovider
python -m pytest tests/test_r3_r4_predecessor_regressions.py -k "closure" -vv -p no:cacheprovider
```

Expected: the acceptance assertion is RED against the present implementation.
If the contract audit confirms there is no legal unresolved application frame,
do not modify production code: record the stop outcome with this exact evidence.
If an already-admitted schema can express it, use only that existing schema and
rerun the vertical case. A mere change from `critical_residual` to another
abstention is not completion.

- [ ] **Step 4: Commit only if the named case legally crosses the old boundary**

```powershell
git add hybrid_mvp/src/cemm_authoritative_hybrid/proposal_context.py hybrid_mvp/src/cemm_authoritative_hybrid/recursive_composer.py hybrid_mvp/tests/test_proposal_context_builder.py hybrid_mvp/tests/test_r3_r4_predecessor_regressions.py
git commit -m "fix(r4): compose unknown designation queries"
```

Omit unchanged paths from `git add`. This is owner-level fix 1 and
implementation commit 1 only if no ABI shape or fake semantic identity was
needed. Otherwise make no implementation commit and proceed directly to the
stop record in Task 4.

### Task 3: Classify the next blocker before a second fix

Execute this task only if Task 2 legally crossed the unknown-designation
boundary under the active ABI.

**Files:**

- Modify: `tests/test_r3_r4_predecessor_regressions.py`
- Modify only the single earliest owner selected by the trace
- Modify on stop: `docs/superpowers/specs/2026-09-03-r4-closure-slice-anti-recursion-design.md`

- [ ] **Step 1: Add the remaining surface rows without weakening them**

Add one test per remaining row. Every supported surface row calls
`_assert_selected_semantic_path`; unresolved context must still produce typed
ResponseMeaning rather than an untyped proposal abstention. Assert exact graph
properties instead of operator labels alone:

```python
assert len(result.verification.selected_meaning.expression.root_refs) == 2  # multiple_roots only
assert result.response_meaning.discourse_action == case.expected_action
assert result.response_meaning.blocker_refs  # denial/unresolved/conflict only
```

For the linked simulation, assert an expression link and two proposition roots
or one linked root according to the active Semantic Expression ABI contract;
do not accept an opaque literal in place of either proposition.

- [ ] **Step 2: Run with an exact phase trace**

Run:

```powershell
python -m pytest tests/test_r3_r4_predecessor_regressions.py -k "closure" -vv --tb=short -p no:cacheprovider
```

Classify the first failing row into exactly one existing owner:

```text
form evidence → designation → affordance → ProposalContext → composer
→ exact verifier/compiler → situation/evaluation → effect → ResponseMeaning
→ offline realization authorization
```

- [ ] **Step 3: Apply at most one owner-local repair**

Write a focused RED test beside that owner, implement the minimum semantic fix,
and rerun both its owner test and the complete closure matrix. Do not repair a
later row in the same commit. The implementation must be semantic-kind/frame
driven and must pass multilingual/unseen-synonym anti-bloat checks where the
owner is form, designation or affordance related.

- [ ] **Step 4: Commit or stop**

If the whole matrix advances and owner tests pass, commit only the owner,
existing closure test owner and exact metadata changes. This is owner-level
fix 2. Repeat Step 2 once for owner-level fix 3.

If the matrix would require a fourth owner, a new ABI/phase/gate, source
package publication, phrase dispatch, automatic lexicalization or R5
activation, take the stop outcome immediately. Do not spend all three fixes
merely because the cap exists.

### Task 4: Prove exact practical surfaces or take the realization stop outcome

**Files:**

- Test: `tests/test_r3_r4_predecessor_regressions.py`
- Read: `src/cemm_authoritative_hybrid/r4_realization_compiler.py`
- Read: `src/cemm_authoritative_hybrid/realization.py`
- Modify on pass/stop: `docs/superpowers/specs/2026-09-03-r4-closure-slice-anti-recursion-design.md`
- Modify on pass/stop:
  `docs/superpowers/progress/2026-08-29-r4-1-data-supervision-replay-progress.md`

- [ ] **Step 1: Attempt authorization through existing exact offline owners**

For each selected ResponseMeaning, require a nonblank surface whose reviewed
slots and alignments reconstruct the exact response expression, action,
participants, epistemic status, modality, polarity and required literals.
Explicitly reject `Acknowledged.`, source echo and `[no authorized surface]`.

- [ ] **Step 2: Refuse the marker-verifier shortcut**

If the only available proof is `RealizationVerifier.verify`, stop. Its source
contract says it does not establish canonical-expression equivalence. Do not
change that statement, broaden markers or call a marker receipt “authorized.”

- [ ] **Step 3: Record exactly one outcome**

Pass outcome: all twelve cases are green, no forbidden mechanism exists, and a
bounded receipt records case ref, Program ref, Expression ref, VerifiedMeaning
ref, Decision ref, Effect/NoEffect ref, ResponseMeaning ref and exact offline
authorization receipt ref.

Stop outcome: record the first unresolved owner, the exact failing case, its
earliest artifact/status and why another fix would exceed the three-owner or
architectural boundary. Keep R4 bulk authoring and R5 unavailable.

- [ ] **Step 4: Run bounded closeout verification**

Run:

```powershell
python -m pytest tests/test_r3_r4_predecessor_regressions.py -k "closure" -vv -p no:cacheprovider
python -m pytest tests/test_replay_governance.py -q -p no:cacheprovider
python -m compileall -q src/cemm_authoritative_hybrid tests/test_r3_r4_predecessor_regressions.py
git diff --check
```

Expected on pass: all commands succeed and every case is usable. Expected on
stop: the closure test remains RED and the governance tests succeed with the
explicit blocker record; no phase or admission status changes.

## Definition of done

This plan ends with exactly one of two states:

1. all twelve fixed cases traverse the required semantic path and exact offline
   surface authorization without R5 activation; or
2. the stop outcome names one earliest architecture blocker after no more than
   three owner-level fixes.

Neither state authorizes a source package, R4.1 admission, R5 training or root
adoption. Only a passing state permits a later mechanical R4.1 correction plan.
