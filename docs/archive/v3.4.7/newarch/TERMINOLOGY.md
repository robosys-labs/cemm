# CEMM v3.5 Canonical Terminology

**Status:** binding terminology contract  
**Purpose:** prevent semantic drift caused by overloaded or interchangeable words.

---

## 1. Identity and type terms

### Referent

An identity-bearing semantic target that can be mentioned, bound, tracked, queried, or reasoned about.

### Storage kind

A small serialization discriminator for specialized referent identity payloads. It is not the semantic ontology.

### Referent type

A data-driven semantic classification represented by a `ReferentTypeSchema`. Types support multiple inheritance and facet entitlements.

### Type assertion

A context-, time-, source-, and confidence-qualified assertion that a referent instantiates a type.

### Identity facet

An anchor or criterion used to resolve whether mentions denote the same referent.

### Alias

A language- and scope-qualified surface form associated with a referent. An alias does not define the referent's type.

---

## 2. Knowledge-structure terms

### Facet

A foundational family of possible knowledge about a referent, such as state, localization, capability, or role.

### Facet entitlement

A type-level contract specifying whether a facet is required, optional, conditional, prohibited, or inherited.

### Referent knowledge view

A pinned derived projection of the currently accessible knowledge, state, capabilities, relations, and conflicts concerning a referent. It is not a truth store.

### Property

A relatively stable or identity-descriptive semantic relation. Properties can still vary by context and time.

### Attribute

Avoid as a canonical executable term because it ambiguously means property, state, type feature, parser feature, or database field. Use the specific term.

### State dimension

A typed axis along which a referent can hold time-indexed state values.

### State value

A referent/schema value belonging to a state dimension's domain.

### State assignment

A supported, time/context-qualified statement that a holder has a value on a state dimension.

### State occurrence

An optional reified referent representing a state interval or episode. It points to defining state applications.

### Default

A defeasible expectation rule. A default is not an active fact.

### Latent

Applicable and structurally present, but not currently active or instantiated.

### Active

Currently supported and applicable in the selected context/time.

### Blocked

An otherwise available state, disposition, or capability prevented by a current condition.

### Terminated

A previously active interval has ended. Termination does not erase historical truth.

### Inapplicable

The referent's active type/facet contracts do not license the requested knowledge dimension.

### Unknown

The dimension applies, but CEMM has insufficient admissible information about its value.

---

## 3. Action and ability terms

### Event

A temporally situated occurrence or change. An event may be intentional or non-intentional.

### Action

An event schema with an intentional, controlling, or operation-bearing participant.

### Event schema

The reusable definition of participant ports, occurrence constraints, transition contracts, and effects for an event class.

### Event occurrence

An identity-bearing instance of an event schema.

### Affordance

A type- or referent-level statement that an action is structurally meaningful or possible in principle.

### Disposition

A latent ability activated when conditions hold.

### Capability

A referent-level assessment that an action can currently be instantiated under declared conditions.

### Permission

A normative authorization to perform an action or access information.

### Competence

An assessment of reliability or quality for performing an action.

### Intention

A referent's represented commitment or plan to perform an action.

### Function

The intended, selected, designed, or institutional contribution of a referent/component. A function can remain when capability is unavailable.

### Operation

An executable implementation contract for an action schema.

### Goal

A desired semantic condition or obligation that directs planning or communication.

---

## 4. Proposition, claim, and knowledge terms

### Proposition

Truth-evaluable semantic content.

### Claim

A source's act of presenting a proposition with some commitment.

### Claim occurrence

The event of making a claim.

### Claim record

A durable source-attributed record linking the claim occurrence and proposition.

### Observation

A source-aligned occurrence delivered through a modality/channel.

### Evidence

A record that supports analysis, grounding, epistemic assessment, learning, or inference. Evidence is not truth.

### Knowledge record

CEMM's epistemic stance toward a proposition in a context/time, including support/opposition and provenance.

### Fact

Avoid as a raw storage term. In prose, “fact” means a proposition sufficiently supported for the specified context and use. Canonical storage remains `KnowledgeRecord`.

### Truth status

Open-world status:

```text
supported
opposed
both
undetermined
```

### Correction

A discourse/epistemic act that opposes, supersedes, or refines prior content. Correction does not erase history.

### Retraction

Withdrawal of a source's support for a claim/proposition.

---

## 5. Change and evaluation terms

### Change

A semantic transition between before and after conditions.

### State delta

A proof-bearing change candidate over a state dimension.

### Gain

A transition from absent/unavailable/lower possession to present/available possession.

### Loss

A transition ending possession, availability, relation, component membership, or state. Loss is not automatically harmful to all stakeholders.

### Increase/decrease

Scalar direction along an ordered dimension.

### Activation/deactivation

Change in operational availability of a state, disposition, capability, or process.

### Creation/destruction

Beginning or ending identity/existence in a context. Do not use these for ordinary state changes.

### Polarity

Logical assertion or negation of proposition content.

### Valence

Stakeholder- and goal-relative beneficial/harmful/mixed/neutral evaluation.

### Impact

An assessment of how an event/state change affects a referent or stakeholder.

### Importance

A contextual assessment of priority or significance to a stakeholder/goal.

### Salience

Current attention or discourse prominence. Salience is evidence for relevance but is not durable importance.

### Urgency

Time-sensitive priority for action or response.

### Risk

Expected possibility and severity of an undesirable outcome.

### Value

Use carefully:

- **semantic value**: a property/state/quantity filler;
- **evaluative value**: worth/desirability, represented through an assessment.

Never use one untyped `value` field to mean both.

---

## 6. Logical and modal terms

### Modality

A scoped operator such as possible, capable, permitted, necessary, intended, or desired.

### Normativity

Permission, obligation, prohibition, recommendation, or discouragement.

### Applicability

Whether a facet/operator/schema can meaningfully apply.

### Context

A world or discourse frame in which propositions and events are evaluated.

### Actual context

The runtime's current actual-world model, still subject to epistemic uncertainty.

### Reported context

A context containing source-attributed reported content.

### Hypothetical context

A possible scenario used for reasoning without actual-world commitment.

### Fictional/simulated context

A represented world whose state changes do not automatically affect actual context.

### Counterfactual

A context explicitly contrary to an assumed/known condition.

---

## 7. UOL terms

### Meaning schema

A reusable executable semantic definition.

### Semantic application

An instance of a meaning schema with local port bindings.

### Port

A schema-owned semantic participant/value position.

### Semantic variable

A typed open role/value used in questions, learning, rules, or partial meaning.

### UOL graph

Cycle-local graph of candidate/selected semantic applications, referents, variables, scopes, propositions, events, and discourse acts.

### Meaning hypothesis

One internally coherent candidate interpretation.

### Meaning bundle

A compatible set of selected hypotheses for a whole turn/observation set.

### GraphPatch

The only authorized proposal for durable semantic mutation.

---

## 8. Learning terms

### Learning contribution

One proposed reusable addition or correction to semantic/lexical/realization knowledge.

### Learning package

A dependency-tracked collection of contributions concerning a referent, type, event, relation, rule, lexical sense, or policy.

### Grounding frontier

The exact unresolved dependencies preventing a learning package from a requested use.

### Competence case

An independently sourced test proving a schema can perform a use.

### Use profile

The operations for which a schema revision is authorized:

```text
mention
ground
compose
query
infer
transition
impact
plan
execute
realize
```

### Promotion

Lifecycle movement toward broader/stronger use authorization.

### Counterexample

Evidence against an overgeneralized rule or schema condition. It is not merely a failed test.

---

## 9. Prohibited substitutions

Do not substitute:

```text
entity          for all referents
attribute       for property/state/type indiscriminately
negative        for polarity/loss/harm/decrease/prohibition
fact            for claim or observation
capability      for affordance/function/permission/intention
state           for property
role            for predicate port
event           for proposition
importance      for salience
default         for current state
template        for semantic rule
```
