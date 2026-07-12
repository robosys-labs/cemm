Audit verdict

You are right: the current system still recognizes many important words as surface cues without possessing their operational meaning.

The problem is not simply that know and learn are absent from a vocabulary. The deeper problem is that CEMM currently lacks a complete cognitive predicate algebra connecting:

surface form
→ predicate sense
→ semantic category
→ typed roles
→ proposition scope
→ state/relation effects
→ query semantics
→ learning obligations
→ durable knowledge

The existing 16 UOL atom kinds remain sufficient. We should not add KnowAtom, LearnAtom, or EngineerAtom. Instead, CEMM needs instances such as:

relation(key="knows")
process(key="learns")
action(key="teaches")
relation(key="means")
relation(key="has_occupation")

with grounded roles and explicit proposition modes.

The current governing AGENTS.md already says surface evidence must not select operational meaning and predicate activation must consume grounded predicate phrases. The implementation at 4fc18d7, however, still violates both laws.

What happened in the transcript
1. “Do you know my name?”

The answer was factually acceptable because the name had not yet been supplied. But CEMM did not understand this through a grounded knows proposition.

It recognized the complete phrase:

"do you know my name"

as a seeded user_name_query alias. Likewise, broad phrases such as do you know, what is, and tell me about are seeded as open-domain query patterns.

So this currently works approximately as:

phrase match
→ user_name_query
→ profile_dimension query

rather than:

queried knows(
    knower=self,
    content=queried has_property(
        owner=user,
        dimension=identity.name,
        value=OPEN
    )
)

That distinction becomes important for every query that is not already in the phrase catalogue.

2. “You sound like you don't know the meaning of the word ‘know’...”

This utterance contains at least three meanings:

assistant does-not-know meaning(lexeme "know")
lexeme "know" has a meaning
"know" is important

But the current pipeline cannot reliably preserve any of them.

Quoted lexical mention is lost

'know' should be represented as a lexical-form referent:

entity/virtual_object(
    semantic_type=lexical_form,
    surface="know",
    language=en
)

and connected through something like:

means(lexical_form, predicate_schema)
mentions(user_utterance, lexical_form)

Instead, punctuation and quotes are stripped in some normalization paths. TextNormalizer removes punctuation before creating its canonical form, while other code uses a separate tokenizer that preserves apostrophes.

There is therefore no single canonical token and morphological stream.

The assertion outranks the critique

The operational arbitration explicitly chooses writable frames before queries or social/feedback frames:

if writable:
    primary = ...
elif queries:
    ...
elif social:
    ...

So a secondary assertion such as “it is important” can dominate the main critique about the assistant’s understanding.

This is why the turn could become store_patch even though the communicative purpose was corrective/metalinguistic.

The correct arbitration unit must be a meaning group plus discourse relation, not simply the highest-priority frame type anywhere in the utterance.

3. “Otherwise you can't even answer questions or learn easily”

This turn was classified as social and produced a phatic response.

The exact reason is visible in the classifier. A non-question between five and eighteen words that contains you can be converted into assistant_evaluation:

if not acts and word_count > 4 and word_count <= 18:
    if "you" in text_tokens:
        acts.append(ConversationAct(
            act_type="assistant_evaluation",
        ))

That broad pragmatic heuristic erased the actual semantic structure:

otherwise(
    if not can(self, answer(question)),
    then not can(self, learn(content))
)

At minimum, the turn contains:

a discourse consequence or condition;
a negated capability proposition around answer;
a negated or constrained capability/process around learn.

The classifier should be allowed to add an evaluation alongside those propositions. It must not replace them.

4. “I’m an engineer”

This failure has an exact mechanical cause.

Tokenization destroys the contraction before expansion

The language adapter normalizes tokens by removing apostrophes:

"I'm" → "im"

But the contraction dictionary is keyed as:

"i'm" → "i am"
"don't" → "do not"
"can't" → "cannot"

RelationExtractor._expand_contractions() performs exact dictionary lookup on the already-normalized token. Consequently:

im ≠ i'm
dont ≠ don't
cant ≠ can't

Therefore, the extractor never sees:

i am an engineer

and cannot create:

is_a(user, engineer)

Only the unknown engineer concept candidate survives.

The write confirmation remains false

The patch extractor marks a relation operation as required only when such an operation exists.

When no relation operation exists, runtime fallback code treats all remaining patch operations as the requested write:

if not required and write_contract is not None:
    required.extend(all_patch_operation_target_ids)

Thus:

requested meaning:
    user is_a engineer

actual commit:
    concept candidate "engineer"

runtime conclusion:
    requested write succeeded

Your trace confirms this:

committed patches: 1
durable relations: still 22
response: "I've stored that."

This is the same auxiliary-write confirmation bug in a different path.

The fallback must be deleted. A relation_upsert contract with no matching relation operation is an unsatisfied write, regardless of whether auxiliary concepts were committed.

5. “What do I do?”

There is no canonical occupational dimension or predicate.

The person schema has:

identity.role
cognitive.knowledge
capability.can_learn

but no social.occupation, vocational.occupation, or equivalent.

The surface aliases job, role, and title are all collapsed into identity.role, and only work in possessive profile constructions such as my job.

Meanwhile, any unclassified question defaults to a concept-definition query.

So CEMM effectively interprets:

what do I do?

as something resembling:

define an unidentified concept

rather than:

queried has_occupation(
    person=user,
    occupation=OPEN
)
6. “Do you know what an engineer is?”

This requires nested propositions.

The correct structure is approximately:

outer:
    queried knows(
        knower=self,
        content=inner
    )

inner:
    queried definition/is_a(
        subject=concept:engineer,
        object=OPEN
    )

The current system flattens the entire utterance into concept_definition and hard-codes the query to taxonomy relations:

is_a
same_as
part_of
used_for

There is no outer epistemic proposition.

Even if is_a(user, engineer) had been stored, that would only mean the user belongs to the class engineer. It would not answer:

what is an engineer?

To answer that, CEMM needs something like:

is_a(engineer, occupation)
used_for(engineer, engineering_work)
has_definition(engineer, ...)

The logically correct response with current evidence would have been:

I remember that you said you’re an engineer, but I don’t yet have a definition of “engineer.”

That response requires CEMM to distinguish:

knowledge about the user
≠ definition of engineer
≠ knowledge that such a definition is available
The deepest architectural defects
1. “All verbs evoke action schemas” is wrong

The schema kernel currently declares:

Verbs evoke action schemas.
Nouns evoke entity-kind candidates.

This is too shallow for a meaning system.

Many verbs are not actions:

Surface predicate	Semantic category
know	stative epistemic relation
believe	stative epistemic relation
own	possession relation
resemble	comparison relation
understand	cognitive state/relation
learn	change-of-state process
teach	communicative action/process
answer	communicative event
mean	denotation relation

The canonical rule should instead be:

Predicative expressions evoke PredicateSchema candidates.

The selected PredicateSchema declares whether the meaning is:
relation, state, process, action, event, or operator.

ActionOperatorSchema should be one specialization of the broader predicate model, not the universal verb model.

2. know exists only as scaffolding

know is listed as a grammatical predicate_verb, but that metadata only signals that a clause may contain a predicate. It does not define a semantic predicate, roles, polarity behavior, query behavior, or persistence semantics.

There is a seeded knows_about record, but it is classified as a generic definition relation and is used primarily by self-knowledge queries. It has no language aliases, state semantics, truth projection, or relationship to learning and memory.

Its schema type is also too limited. PredicateSchemaRecord currently contains only roles, inverse predicates, inheritance, projection, freshness, and evidence policy. It cannot express predicate category, aspect, polarity behavior, effects, argument constraints, lexical senses, or query forms.

3. learn exists, but it loses what was learned

learn maps to an action named increase_capability. It has an optional topic and produces only:

cognitive.knowledge → increase

There is no relation delta connecting the learner to the learned content.

This means the system can theoretically represent:

knowledge increased

but not:

self learned the meaning of "know"
self now knows concept X

The same mistake appears in memory_write, provide_information, display_information, and transfer_knowledge: they mutate a generic knowledge dimension without preserving the content that changed.

teach also directly increases the recipient’s knowledge. That is too strong. Teaching provides evidence or a candidate representation; successful assimilation is what produces learned knowledge.

4. Schema-defined roles are ignored

The action schemas define important roles such as:

topic
recipient
source
destination
instrument

But both role inference and graph construction primarily iterate only:

actor
object
target
place

This makes the cognitive schemas unusable:

learn(learner, topic)
teach(teacher, recipient, topic)
ask(speaker, topic)
answer(responder, question, content)

cannot be grounded properly.

Role materialization must iterate over schema.slots, not a hard-coded tuple.

5. Effects are materialized before activation

MeaningGraphBuilder._add_actions() immediately compiles schema state deltas as soon as it sees an action alias.

That happens before final interpretation selection and effect authorization.

Therefore, a sentence such as:

you did not learn X

can create a candidate knowledge increase state before negation is respected.

At the same time, PredicateActivationResolver rejects negated predicates entirely and does not actually enforce required ports when called by runtime.

Runtime activation is constructed from broad branch frame types—not the actual predicate phrases—and passes an empty resolved-entity set.

The architecture needs two distinct decisions:

PropositionResolution
    Is the proposition semantically understood?
    Includes asserted, negated, queried, quoted, hypothetical.

EffectAuthorization
    May its effects execute or persist?

A negated proposition remains meaningful. It merely does not authorize the positive effect.

6. Semantic gaps do not inspect predicate completeness

SemanticGapDetector says it detects missing typed ports, but the implementation mainly checks:

unknown lexemes;
pre-existing gaps;
groups containing referents but no predicate.

It does not compare activated predicate candidates against their schema-required roles.

Because learn is a known action alias, it is not an unknown lexeme. Because it produces an action/process atom, the group appears to have a predicate. Therefore:

learn

can avoid gap detection even if its learner, content, scope, and effect are unresolved.

A known surface form must not mean “semantically complete.”

7. Learning does not materialize a learned artifact

The updated cross-turn episode persistence is an improvement. The runtime now consumes prior pending obligations before creating new questions.

But the actual acquisition path remains incomplete:

A learning episode is created.
No corresponding hypothesis is necessarily created.
The answer assimilator extracts a generic field such as semantic_type or description.
apply_answer_fields() can mark the episode minimally grounded.
No predicate schema, lexeme-sense binding, construction, relation schema, or state schema is necessarily produced.

SessionLearningOverlay can store lexeme, operator, entity, and state bindings, but the audited runtime chiefly restores and persists it; accepted learning fields are not materialized into it in the acquisition path shown.

So a learning episode may become administratively “grounded” without changing the interpretation of the next occurrence.

8. Construction and pragmatic matching still outrank composition

ConstructionMatcher scans aliases, scores their token overlap, and chooses a highest-scoring construction.

The giant uol_semantics.json mixes:

lexical cues;
grammatical cues;
whole-utterance templates;
conversation acts;
semantic-looking names;
response policy metadata.

For example, it contains explicit templates for names, capabilities, phatic replies, complaints, open-domain queries, and teaching queries.

This data should be split into four independent layers:

language lexicon:
    surface/morphology → sense candidates

predicate schemas:
    canonical meaning → roles, category, effects, queries

construction schemas:
    compositional form → predicate/role arrangement

pragmatic cues:
    interaction-level signals → social/repair/style candidates

A pragmatic cue may supplement content meaning. It may never replace grounded propositions.

Required cognitive UOL foundation

A minimal foundational cognitive algebra should include these canonical predicates.

Stative relations
knows(knower, content)
knows_about(knower, topic)
understands(understander, structure_or_concept)
believes(believer, proposition)
remembers(rememberer, content)
has_access_to(agent, memory_record)
means(lexical_form, semantic_ref)
Processes and actions
learns(learner, content, source?)
teaches(teacher, learner, content)
informs(source, recipient, content)
asks(speaker, addressee?, proposition)
answers(responder, question, answer_content)
retrieves(agent, content_or_record)
stores(agent, proposition_or_record)
forgets(agent, content)
Important distinctions
stored(content)
    does not automatically equal
knows(self, content)

knows_about(self, engineer)
    does not automatically equal
understands(self, engineer)

teaches(user, self, content)
    does not automatically equal
learned(self, content)

learns(self, content)
    may produce
knows(self, content)

Every one of these can use the existing generic atom kinds. No new domain atom kind is necessary.

The predicate schema must become richer

The canonical schema needs fields along these lines:

{
  "predicate_key": "knows",
  "predicate_kind": "relation",
  "relation_family": "epistemic",
  "aspect": "stative",
  "aliases": {
    "en": ["know", "knows"],
    "ig": []
  },
  "roles": {
    "knower": {
      "required": true,
      "accepted_entity_kinds": ["person", "self", "autonomous_agent"]
    },
    "content": {
      "required": true,
      "accepted_semantic_kinds": [
        "entity",
        "concept",
        "relation",
        "state",
        "process"
      ]
    }
  },
  "polarity_behavior": "preserve_proposition",
  "query_projections": {
    "yes_no": "truth_status",
    "open_content": "content"
  },
  "persistence": {
    "cardinality": "set",
    "evidence_policy": "required"
  }
}

For learns:

{
  "predicate_key": "learns",
  "predicate_kind": "process",
  "aspect": "change_of_state",
  "roles": {
    "learner": {"required": true},
    "content": {"required": true},
    "source": {"required": false}
  },
  "effects": [
    {
      "effect_kind": "relation_upsert",
      "predicate_key": "knows",
      "subject_from": "learner",
      "object_from": "content",
      "authorization": "after_successful_assimilation"
    }
  ]
}

This should replace the current content-free cognitive.knowledge: increase behavior.

Occupation must also be foundational

Add:

social.occupation

to person-like entity schemas, with set or optional-one cardinality depending policy.

And add a canonical relation:

has_occupation(person, occupation)

identity.role should remain available for contextual roles such as administrator, parent, customer, or team lead. Occupation is a different dimension.

For:

I'm an engineer

the pipeline should produce:

is_a(user, engineer)

and, when engineer is_a occupation is known:

has_occupation(user, engineer)

If the kind of engineer is not yet known, CEMM may still store the speaker-asserted classification while retaining an ontology gap.

Then:

what do I do?

can query has_occupation(user, OPEN).

Implementation order
P0 — repair the semantic substrate
Create one canonical token/morphology stream.
Preserve raw span, normalized form, lemma, contraction decomposition, negation and quote boundaries. Remove independent tokenization policies from TextNormalizer, LanguageAdapter, and text_match.
Introduce one comprehensive PredicateSchema authority.
It must support relations, states, processes and actions—not only action operators.
Seed the cognitive predicate algebra.
Add knows, understands, learns, teaches, asks, answers, means, remembers, stores, retrieves, and forgets.
Make role binding schema-generic.
Iterate every declared role, including topic, recipient, content, source, question, and answer.
Separate proposition resolution from effect authorization.
Do not discard negated or queried propositions. Do not materialize action effects in MeaningGraphBuilder.
Delete the WriteOutcome fallback.
A missing required relation operation must make the write unsatisfied.
P1 — make learning operational
Generate an explicit LearningHypothesis for every blocking gap.
Convert accepted answer fields into a provisional semantic artifact:
lexeme-sense binding;
predicate schema;
role schema;
construction schema;
relation orientation;
state dimension.
Install the artifact in SessionLearningOverlay.
Re-run or resume the blocked interpretation against that overlay.
Promote only after evidence, reuse and counterexample checks.
P2 — repair queries and discourse
Support nested propositions and complement clauses.
Add truth/existence query projection, not only object projection.
Add occupation queries and object-kind constraints.
Demote construction and conversation-act matching to candidate evidence.
Preserve multiple meanings in mixed turns instead of allowing one writable or social frame to suppress the rest.
Required acceptance transcript

After implementation, the following should be true.

User: I'm an engineer.

Expected substrates:

relation: is_a
subject: user
object: concept:engineer
mode: asserted
required write: relation target
auxiliary write: concept candidate

Response only after relation commit:

Got it—you’re an engineer.

Then:

User: What do I do?
Assistant: You’re an engineer.

Then:

User: Do you know what an engineer is?

If no definition exists:

Assistant:
I remember that you said you’re an engineer,
but I don’t yet have a definition of “engineer.”

For negation:

User: You don't know what engineer means.

Expected graph:

relation: knows
knower: self
content: definition(engineer, OPEN)
mode: negated

No positive knowledge effect and no memory write.

For learning:

Assistant: What kind of meaning does “know” express?
User: It describes a relation between someone and information they possess.

Expected result:

LearningHypothesis:
  target = predicate_schema:knows
  predicate_kind = relation
  candidate_roles = [knower, content]

SessionLearningOverlay:
  "know" → predicate_schema:knows

next occurrence:
  interpreted through provisional predicate schema

Not merely:

resolved_fields["semantic_type"] = "relation"
episode.status = minimally_grounded
Bottom line

The earlier patch fixed several important integrity problems—open query ports, relation identity, public IDs, cross-turn episode persistence, and relation-frame handling—but it did not yet replace the underlying surface-act router with a compositional semantic CPU.

The next implementation should not be “add know, learn, engineer, and more phrases to JSON.” That would deepen the baggage.

It should establish:

one token/morphology substrate
+ one predicate-schema substrate
+ one proposition/scope algebra
+ one generic role resolver
+ one operational acquisition path

That is the minimum foundation on which CEMM can genuinely learn rather than merely remember patterns.