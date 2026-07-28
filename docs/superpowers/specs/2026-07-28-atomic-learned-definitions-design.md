# Atomic Learned Definitions Design

## Goal

Make a reviewed learned semantic definition a graph of ordinary five-operator
applications.  The graph, rather than a surface phrase or an independently
maintained rule list, is the authority from which CEMM composes, queries and
derives bounded consequences.

## Authority model

A learned designation continues to identify one semantic target.  When that
target is composite, its reviewed authority must additionally contain a
definition graph linked to the target.  The graph uses explicit typed ports,
variables and, where needed, bounded existential referents.  Internal target
refs and the spelling of a designation never create this decomposition.

For example, the semantic target `rel:mother_in_law` is independently
addressable, but its definition graph can state:

```text
mother_in_law(?mother, ?person)
  <=> mother_of(?mother, ?partner)
      AND partner(?partner, ?person)
```

The relation has a person-facing object port.  Possessive reference supplies
`?person = participant:user`; composition creates a cycle-local existential
referent for `?mother`, which can then fill the actor port of an arrival event.
No semantic atom is minted by this transient binding.

## Runtime model

Stage 5 composes only form contributions, dynamic semantic affordance ports,
and reviewed definition graph ports.  It adds three generic paths:

1. state predicates lower to `op:state` claims or queries according to force;
2. possessive relation evidence binds the relation's participant-facing port
   and introduces a typed transient referent for the remaining entity port;
3. an adjacent compatible event frame may consume that referent as a normal
   actor/participant filler.

The Stage-4 state projection may affect candidate ranking, but it may not
discard a semantically valid state query solely because the queried dimension
has no observation for the participant.  That absence is answered as unknown
unless a derived or observed fact supports or denies it.

## Derivation model

At reviewed activation, a definition graph may be lowered into a bounded,
typed rule projection for sparse closure.  Each projected rule retains the
definition graph ref and exact application mapping.  The definition graph is
the only semantic authority; a projection is a replaceable execution index.
Definitions that cannot be lowered safely remain describable but do not gain
an executable inference path.

The proof for a derived marital state must include the input relation fact,
the definition graph ref, and any projected-rule receipts.

## Acceptance

The test fixture publishes a reviewed composite relation definition and its
ordinary designations, then verifies that:

1. `My <composite relation> arrived today.` resolves to an event whose actor
   is the transient relation subject and whose relation object is the speaker;
2. `Am I married?` composes as an `op:state` query even before a participant
   state projection exists;
3. bounded inference derives the marital state from the definition graph and
   returns a proof path;
4. a newly acquired alias for the same relation succeeds without form-pack
   regeneration;
5. designation alone, with no reviewed definition graph, cannot produce the
   marital conclusion;
6. no active source uses a literal mother-in-law, marriage, or alias branch to
   choose composition or inference behavior.
