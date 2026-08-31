# R4.1 Reviewer Identity Validation Repair

**Date:** 2026-08-31  
**Status:** approved design  
**Scope:** accountable-review presentation and loopback API only

## Problem

Guided Review accepts arbitrary text in the reviewer identity field and sends
it to the server. The canonical Python validator correctly rejects values that
are not typed reviewer references, but the browser displays its internal error:

```text
reviewer_refs item is not an admitted reference
```

The field's helper text is insufficient protection because neither the browser
nor the reviewer route translates the exact contract into actionable feedback.
This makes a valid security/authority boundary look like a broken workflow.

## Root cause

`exact_reviewer_refs` is the correct owner of reviewer-reference semantics. It
requires a nonempty, canonical set of references in the `reviewer:` namespace,
with no whitespace and a nonempty local identity. The UI has no corresponding
input check, while the generic HTTP error handler returns the validator's
low-level wording unchanged.

The repair must not broaden this validator, admit bare names or email
addresses, silently add `reviewer:`, normalize an identity, or select an
identity on the reviewer's behalf.

## Chosen design

Keep the full canonical reference as the explicit input. Add one small
browser-side predicate that mirrors the active reviewer-reference shape:

```text
reviewer:<nonempty identity with no whitespace>
```

The Guided Review identity form and Advanced Explorer reviewer form use that
predicate before making a request. Invalid input remains in the field, focus
returns to it, `aria-invalid` and an inline status message identify the exact
problem, and no request or state mutation occurs.

The reviewer API remains authoritative. At that route only, rejected reviewer
values are translated into stable public guidance:

```text
Reviewer ref must use reviewer:<identity> with no spaces.
```

All other validation failures retain their existing handling. A valid value is
still passed unchanged to `ReviewSession.set_reviewers`, which continues to use
`exact_reviewer_refs` and canonical ordering/deduplication.

## Data flow

```text
explicit browser input
→ local shape check
→ exact reviewer API request
→ canonical Python validation
→ atomic working-state commit
```

There is no authority lookup, semantic designation, identity creation, runtime
dependency, new endpoint, background validation or additional release gate.

## Error and recovery behavior

- Empty, bare, whitespace-containing or non-`reviewer:` input is rejected
  locally with the public format guidance.
- The entered invalid value remains visible and editable.
- The reviewer field receives focus and is marked invalid for assistive
  technology.
- Correcting the value clears the local error before submission.
- A malformed or bypassed request receives the same public guidance from the
  server and leaves working state unchanged.
- Stale revisions, authorization failures and journal warnings retain their
  existing behavior.

## Testing

Add regression coverage that proves:

1. the Guided and Advanced forms use one shared exact input predicate;
2. invalid input is stopped before `api("/api/reviewer")` and receives inline,
   accessible guidance without normalization;
3. the server returns public reviewer guidance for malformed reviewer refs and
   does not mutate state;
4. `reviewer:son` remains accepted unchanged;
5. existing UI safety, API authorization, session, export-equivalence and
   canonical-validator tests remain green.

## Non-goals

- creating or admitting reviewer identities in semantic authority;
- accepting display names, emails or bare local names;
- suggesting which person should own the review;
- changing reviewer provenance, export schemas or review ABIs;
- adding another validation process or performance gate.
