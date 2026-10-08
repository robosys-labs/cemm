# Reviewed learning in the canonical CEMM foundation

**Scope:** externally authorized lexical designation of an **existing reviewed
semantic atom**. This implements a narrowly bounded learning capability, not
autonomous ontology growth or general linguistic realization.

## Exact runtime path

```text
"learn yoz means hello"
  ORIENT → PROPOSE → VERIFY → EVALUATE
  → Decision.CREATE_LEARNING_OBLIGATION
  → R3 EFFECT commits pending DialogueObligation + NoEffectReceipt
  → ResponseMeaning contains exact LearningPlan and obligation proof

[separate human review service with authenticated reviewer session]
  → issues ReviewApproval bound to plan, obligation, session,
    original NoEffectReceipt, reviewer, policy, nonce and short expiry
  → FoundationRuntime.approve_reviewed_learning(...)
  → R3EffectGateway.commit_reviewed_learning(...)
  → SQLite single BEGIN IMMEDIATE / COMMIT
     - consumes the plan and 192-bit nonce exactly once
     - inserts one indexed reviewed designation + canonical world Fact
     - resolves the original pending obligation
     - stores full signed reviewer decision in the effect journal
     - advances world/obligation/effect revisions
  → Grounder looks up the revised world designation index
  → subsequent turns reuse the reviewed identity (including after restart)
```

The existing authority generation is not rewritten by an alias commit. The
reviewed *target atom* remains immutable; the new lexical link belongs to
revision-pinned, locally reviewed world knowledge. A new target/concept requires
a separately reviewed authority-generation publication.

## Security boundary

`ReviewerIssuer` belongs **only** inside a reviewer-facing service that has
already authenticated its human reviewer and verified role/policy authority.
The issuer's HMAC key is a server-side secret from a trusted key-management
system. It must never be sent to a user, put into a prompt, surfaced through
the app API, or embedded in the repository.

`ReviewerVerifier` receives allowlisted reviewer keys through trusted
server configuration **at foundation runtime construction**, never per
approval call. A foundation started without a trusted verifier rejects every
review-completion request. Verification establishes that a trusted signer approved
**the exact learning effect**, not that the source sentence was true, nor
that the human review interface was properly authenticated. Human identity,
MFA, reviewer roles, key rotation and external audit are integration duties,
not capabilities this Python module claims to provide.

Each signature covers policy, reviewer, plan, obligation, original effect,
session, nonce, issuance and expiry. The 192-bit nonce and plan are globally
unique in the SQLite store; replay across processes or new approvals fails.
Approvals last at most one hour (default five minutes) and plans have a
four-turn active window. Only one unexpired learning obligation can be active
per session.

Neither raw `op:designation` facts, ordinary statements, unreviewed source
content nor dummy marker strings are accepted by the dynamic designation
index. The reviewer cannot change the selected semantic target or create an
authority atom; the gateway checks the exact original R3 proof, existing
target kind, source receipt, and persisted pending obligation.

## Crash and concurrency behavior

The approval mutation uses **one SQLite transaction**. A fault after
nonce/index insertion must roll back the alias, obligation resolution, fact,
journal and revisions together; the same signed approval can then be retried.
Successful approvals are recorded in the effect journal and remain non-replayable.

A review service can store `FoundationTurn.to_wire()` securely before
acknowledging the initial learning request. On restart, it can reconstruct a
strictly validated handoff using `FoundationTurn.from_wire(...)`. Rehydrating
the handoff never grants reviewer authority: the original NoEffectReceipt must
still exist in SQLite and the separate reviewer signature must still verify.

Concurrent approval attempts on different SQLite connections use revision
checks under `BEGIN IMMEDIATE`. Only one can commit. The reference design
does not claim distributed multi-database or multi-region transactions.

## Reference integration

1. Use `load_foundation` and call `process(session, text)`; verify the
   returned `ResponseMeaning.learning_plan` exists.
2. Securely persist the turn's `to_wire()` output in the review service.
3. Authenticate the reviewer independently; render the complete canonical
   proposed surface/target, confidence/evidence and original semantic proof.
4. Issue an approval with `ReviewerIssuer` in the trusted review backend.
5. Configure the trusted `ReviewerVerifier` once in `load_foundation(...,
   reviewer_verifier=trusted_verifier)` from protected server configuration,
   then pass ONLY the signed decision to
   `FoundationRuntime.approve_reviewed_learning(..., now=server_epoch)`.
6. Check the resulting committed `EffectReceipt`, and execute the next
   language turn against the updated world revision.

Never trust a caller-provided clock, reviewer name, policy, target, plan or
nonce in place of verifying the signed payload and persisted source proof.
The reference API accepts `now` for deterministic testing; a production
service MUST supply time from its trusted server clock.

## Release qualification still required

- Authenticated reviewer UI, roles and segregation of duties
- Alias retraction, correction and historical provenance-preserving supersession
- Key rotation, security monitoring and review evidence retention policy
- Bounded cleanup/archival of expired obligations
- Indexed, policy-aware large-corpus aliases and concurrent multi-node scale
- A learned, semantically round-trip-verified surface realizer
- Independent compositional/temporal/attributed/quantified meaning coverage

`tests/test_foundation_reviewed_learning_effect.py` proves the implemented
subset through public requests, independent signatures, forgery/replay/expiry
denial, persistence, changed names inside semantic queries, crash recovery
and cross-connection contention. It does not prove open-domain cognition.
