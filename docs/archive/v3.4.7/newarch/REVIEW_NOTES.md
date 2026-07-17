# CEMM v3.5 Foundational Redesign Review

**Purpose:** record why the previous v3.5 draft and the current v3.4.7 contracts are not deep enough, and state the decisions that govern the replacement documents.

## 1. What the prior documents got right

The previous architecture and core-loop documents correctly established several non-negotiable foundations:

- `Referent` as the single identity-bearing semantic object family;
- analyzers as evidence providers rather than meaning authorities;
- local schema-owned ports;
- a cycle-local UOL workbench;
- compatible bundle selection instead of one top proposition;
- GraphPatch-only durable mutation;
- explicit provenance, lifecycle, inference limits, and emission proof;
- multilingual meaning shared below language-specific realization;
- bounded, grounded learning rather than sentence memorization.

These remain binding ideas.

## 2. Why they were still insufficient

The documents described a better semantic pipeline but did not fully define the *knowledge substrate* on which a learning-first system must operate.

The main omissions were:

1. **No universal referent knowledge envelope.**  
   Referents shared an identity record, but there was no complete architecture for what every referent can be known through: identity, existence, type, time, localization, composition, properties, state dimensions, relations, roles, functions, affordances, capabilities, significance, and event history.

2. **No explicit facet-entitlement model.**  
   The documents mentioned type profiles and admissible states, but did not define how a referent type grants, requires, prohibits, activates, defaults, or leaves latent a state/property/capability facet.

3. **No first-class claim architecture.**  
   Proposition content, the event of making a claim, evidence for the claim, and CEMM's own epistemic stance were not separated rigorously enough.

4. **No first-class event-effect algebra.**  
   Actions and events could have rules, but the architecture did not define a generic transition substrate for state activation, termination, gain, loss, increase, decrease, capability gating, creation, destruction, or temporal persistence.

5. **Semantic “gates” were underspecified.**  
   Truth negation, harmful valence, negative scalar change, loss, deactivation, prohibition, and low importance must never be represented by one generic negative flag.

6. **Importance and impact were absent from cognition.**  
   Response-goal selection needs a grounded, stakeholder-relative assessment of impact, importance, relationship, user stance, recurrence, and conversational history.

7. **Learning remained a downstream subsystem.**  
   A learning-first system needs learning metadata, frontier state, schema use profiles, competence, negative evidence, and revision dependencies throughout the architecture—not only after understanding succeeds.

8. **The broad referent-kind enum was still too ontology-like.**  
   A learning-first system should use a very small storage discriminator and a data-driven, multiple-inheritance referent type graph. New referent types must not require Python enum changes.

9. **Capabilities were still self-centric.**  
   Capabilities, functions, dispositions, and state-dependent affordances must be available for any referent whose type entitles them, including living, digital, social, institutional, and composite referents.

10. **The death/loss class of meanings was not modeled.**  
    Without transition contracts and capability dependencies, the system cannot derive that a supported death event disables life-dependent capabilities while preserving historical identity and externally caused motion.

## 3. Corrective architectural decisions

### 3.1 Referent remains canonical, but type becomes data-driven

`Referent` remains the only identity-bearing filler family.

`ReferentKind` becomes a minimal storage/serialization discriminator. Executable semantic typing is provided by versioned `ReferentTypeSchema` records with multiple inheritance.

### 3.2 Every referent has a common knowledge envelope

Every referent can participate in a common set of foundational knowledge facets. A type decides which facets are required, optional, latent, defaulted, prohibited, or inapplicable.

### 3.3 State is event-sourced and time/context qualified

Current state is a derived projection over observations, claims, admitted propositions, event effects, defaults, and defeaters. It is not a mutable property bag.

### 3.4 Events change state through transition contracts

An `EventSchema` declares participant ports and generic semantic effect rules. Event effects are compiled into `StateDelta` and `CapabilityDelta` candidates, then assessed and committed in the appropriate world/context.

### 3.5 Native UOL axes are orthogonal

At minimum, CEMM natively distinguishes:

- truth polarity;
- existence status;
- applicability;
- activation;
- capability availability;
- scalar direction;
- possession change;
- evaluative valence;
- importance;
- certainty;
- modality;
- normativity;
- temporal status;
- persistence and reversibility.

### 3.6 “Life” is not a bag of capabilities

Biological life is represented through lifecycle/process and state schemas. Life-dependent capabilities declare dependencies on living state. Death terminates the living interval and disables those capabilities. It does not erase their historical existence or conflate health, emotion, and motion.

### 3.7 Impact and response policy are semantic

Events can generate stakeholder-relative `ImpactAssessment` candidates. Response policies operate over selected meaning, epistemic certainty, impact, importance, relationship, discourse history, and user state. They do not match words or transcripts.

### 3.8 Learning packages are first-class

A learned concept may contribute types, facet entitlements, properties, states, actions, transition rules, lexicalizations, examples, counterexamples, defaults, impact rules, and competence cases as one dependency-tracked package.

## 4. Version decision

This is not a revision of the previous v3.5 draft. It is the canonical **v3.5 foundational redesign**.

The documents in this package replace the earlier generated v3.5 documents. They are intended to replace the repository's v3.4.7 architecture and core-loop contracts only after review and deliberate cutover.
