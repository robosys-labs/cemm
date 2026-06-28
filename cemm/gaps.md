Version: 2.0 Review – Critical Path to Implementation

This document consolidates all remaining foundational weaknesses discovered during deep architectural review. The ERCA is a brilliant cognitive chassis—but these gaps represent the structural engineering challenges that must be resolved before it can be safely implemented at scale.

Gaps are prioritized: Critical (blocks implementation), High (breaks invariants), Medium (causes ambiguity/scale issues), Low (cleanup).

Priority 1: Critical Gaps (Block Implementation)
Gap 1: The Inductor is a Black Box (Structural Learning Undefined)
Location: Section 23 (Background Induction)

Issue: The trigger conditions are correct, but the Inductor’s computation is completely unspecified. How does it detect a "repeated pattern"? What search space does it explore? How does it abstract specific observations into a candidate Model? The Inductor is load-bearing for the entire "truly learns" claim, but it has no body—this replicates the answer operator flaw from PTA v1.0.

Fix Required:
Define a Minimal Induction Contract:

Inputs: Set of active claims, feedback events, failed retrieval patterns, and Self.epistemic.coverage_gaps.

Output: Candidate Model records (kind: predicate, causal_rule, context_rule).

Algorithm Constraint (MVP): Restrict to three deterministic heuristics to avoid combinatorial explosion:

Synonym Aggregation: If two predicates share identical subject/object type pairs and co-occur > 5 times, propose canonical merge.
Sequential Pattern Mining: If Action A is consistently followed by Signal B within 5 seconds, propose causal_rule A → B with confidence = support / (support + failures).
Slot Completion: If a Goal has missing_slots and a specific claim fills it repeatedly, propose a context_rule to auto-populate it.
Explicitly forbid novel ontological class invention in MVP—that requires a separate safe exploration sandbox.
Gap 2: Neural Synthesis Verification is Asserted, Not Achievable
Location: Section 23 (Synthesis Validation)

Issue: The spec mandates that neural synthesis output must be verified to use only selected claim IDs. This is the hallucination attribution problem—a hard open research problem. The spec treats verification as a uniform structural gate, which means either the neural path will fail verification constantly (causing false abstains) or verification becomes nominal.

Fix Required:
Split verification strategy by synthesis path:

Template/Extractive → Hard Gate: Structural traceability is guaranteed; enforce strictly.

Neural → Soft Gate: Run a consistency check (does the output contradict any selected claim? Use an NLI model). If no contradiction is found, pass but flag verification_type: "soft" and downgrade the final response confidence by a factor (e.g., 0.85).

Add a Verifier Model: Treat verification as a Model(kind = "verifier") with its own confidence score. If verifier confidence < 0.7, force fallback to Extractive synthesis.

Gap 3: Frame Rules are Applied After Ranking (Invariant Violation)
Location: Section 21 (Runtime Pipeline) vs. Section 27 (Invariants)

Issue: The pipeline applies apply frame rules after rank_claims_and_models. This creates a window where a claim is ranked and selected, but then invalidated by a world-state update before execution. The action executes with a stale claim set—directly violating the invariant "claim is ranked outside its valid frame".

Fix Required:
Move apply frame rules to immediately after retrieve_claims_and_models and before filter_permissions and rank_claims.
New pipeline order:
retrieve -> apply frame rules -> filter_permissions -> rank_claims_and_models -> causal inference -> rank_actions.

Priority 2: High Gaps (Break Core Runtime Integrity)
Gap 4: Operator Executable Bodies are Metadata-Only
Location: Section 22 (Typed Operators)

Issue: Model(kind = "operator") records contain input/output schemas, preconditions, and effects—they are metadata. The spec defines how answer routes to the Synthesis Router, but simulate, reflect, call_tool, and create_model_candidate have no implementation mapping. What code runs when Action.kind == "simulate"?

Fix Required:
Define a Dispatch Contract mapping Action.kind to a concrete resolver:

text
answer            -> SynthesisRouter.route()
ask               -> ClarificationEngine.generate()
remember          -> MemoryStore.save()
update_claim      -> ClaimGraph.update()
create_model_candidate -> Inductor.propose()
synthesize        -> SynthesisRouter.route()
simulate          -> CausalEngine.simulate()
retrieve          -> RetrievalPipeline.run()
reflect           -> SelfReflectionEngine.run()
abstain           -> AbstainPolicy.evaluate()
Gap 5: Confidence Propagation in Causal Chains is Undefined
Location: Sections 16 & 20 (Causal Simulation & Confidence)

Issue: When the causal engine produces predicted_claims with a confidence field, or chains rules A→B→C, there is no formula for how these confidences combine. The log-odds formula covers evidence updates for stored claims—not forward inference through causal rule chains.

Fix Required:
Define a Forward Inference Confidence Rule:

For a single rule: inferred_conf = product(precondition_confidences) * rule.confidence.

For a chain (A→B→C): chain_conf = inferred_conf(A→B) * inferred_conf(B→C).

Cap at 0.99 to prevent overconfidence.

Add confidence_type: "simulated" to distinguish predicted claims from observed claims, so the system qualifies them (e.g., "I predict this would happen with 65% confidence...").

Gap 6: Recursive Budget is Not Consumed
Location: Section 21 (Recursive Runtime)

Issue: max_recursive_steps exists, but each recursion builds a fresh ContextKernel with a new Budget. A malicious or accidental loop could spawn 100 recursions at 50ms each, causing a 5-second timeout—and the parent has no control.

Fix Required:
Treat Budget as a mutable accumulator. On recursion:

text
new_budget.latency_target_ms = parent_budget.latency_target_ms - parent_action.cost_ms
new_budget.max_recursive_steps = parent_budget.max_recursive_steps - 1
If remaining budget <= 0 or steps <= 0, the recursive call immediately aborts and logs a system-level warning.

Priority 3: Medium Gaps (Ambiguity & Scalability)
Gap 7: Multi-User State (users: UserState[]) is Undefined
Location: Section 10 (ContextKernel)

Issue: users: UserState[] exists but is never referenced in pipeline steps, operators, permissions, or learning. When do multiple users exist? How do conflicting claims resolve? Whose permissions gate which claims?

Fix Required:
Explicitly document for MVP: Single-user only. Replace users: UserState[] with user: UserState. Add a note that multi-user support requires a separate conflict-resolution strategy (e.g., trust-weighted voting) and is deferred to v3.0.

Gap 8: The Frame Problem (Inertia) is Unhandled
Location: Section 16 (Causal World Model)

Issue: If the system updates is_at(Alice, Home) to is_at(Alice, Office), how does it know her hair color, name, and favorite database haven't changed? Without explicit inertia axioms (default assumption of persistence), the world model cannot reason about what stays the same.

Fix Required:
Add a persistence: boolean flag to WorldState. For all causal models, default to minimal change semantics: only the listed effects are updated; everything else remains as-is. This must be explicitly stated as the operational default.

Gap 9: PragmaticState is Ambiguously Overloaded
Location: Section 10 (UserState vs. ConversationState)

Issue: Both UserState.session_affect: PragmaticState and ConversationState.pragmatic_state: PragmaticState use the same type. session_affect tracks user emotional stance (target = assistant/self), while conversation tracks dynamics (repetition pressure). They share target_entity_id, which is directionally ambiguous.

Fix Required:
Split into explicit structures:

UserAffectState: tracks valence, hostility, playfulness, frustration (target is always the system/self).

ConversationDynamics: tracks repetition_pressure, active_repetition_group_ids, likely_cause_claim_ids (target is the topic/previous action).

Gap 10: Self Modes are Undefined & Unconnected
Location: Section 8 (Self.mode)

Issue: Modes (assistant, researcher, planner, etc.) exist but have no triggers, behavioral consequences, or trace requirements. A mode without behavioral effects is just a dead label.

Fix Required:
Define explicit triggers and effects:

Mode	Trigger	Behavioral Effect
researcher	Self.epistemic.coverage_gaps large or user asks deep question	Increase retrieval depth, allow slower latency.
planner	Active goal with missing slots	Prioritize simulate actions.
reflector	High uncertainty or contradiction detected	Pause external actions, emit reflection signals.
teacher	User asks explanation after correction	Switch to longer, pedagogical synthesis strategies.
Require an Action(kind = "reflect") to be emitted on any mode change to maintain traceability.		
Gap 11: current_constraints: string[] is Dead Weight
Location: Section 10 (WorldState)

Issue: This is a remnant from v1.0. It is superseded by active_frame_model_ids and active_context_rule_model_ids. The string list is unstructured and unused.

Fix Required: Remove it entirely. If constraints need runtime representation, they should be stored as active Claim or Model references, not free-text strings.

Priority 4: Low Gaps (Cleanup & Refinement)
Gap 12: Unstructured Machine-Readable Strings
Location: Self.metacognition.known_limits: string[] and failed_retrieval_patterns: string[]

Issue: These are free-text, which means they are useful for human debugging but useless for the system’s runtime behavior. The system cannot check "don't answer X" against an incoming query if X is a string in a list.

Fix Required:
Replace with references to structured Claim objects (e.g., Claim(predicate: "self_capability_limitation", object_value: "cannot_answer_medical")). This allows the system to retrieve and match them structurally during abstain or reflection.

Gap 13: Allen Temporal Relations Were Dropped
Location: Sections 5 vs. original v1.0

Issue: The original PTA v1.0 had Allen interval relations (precedes, overlaps). ERCA v2.0 downgraded to valid_from/valid_until, which only handles containment. Queries like "What was happening while I was in the meeting?" (overlap) are now computationally heavy or impossible to index.

Fix Required:
Re-introduce a lean temporal_relations index as a derived cache, not a stored primitive. When a claim with a temporal interval is stored, a background job computes Allen relations against the 5 most temporally proximate active claims and stores them as Claim objects with predicate "temporally_overlaps" or "precedes". This keeps retrieval structural and cheap.

Summary Table of Gaps
#	Priority	Gap Name	Core Issue	Status
1	Critical	Inductor Black Box	No algorithm defined for structural learning.	Unblocked
2	Critical	Neural Verification	Hard structural gate is unachievable for neural path.	Unblocked
3	Critical	Frame Ordering	Rank uses invalid claims due to post-hoc invalidation.	Unblocked
4	High	Operator Bodies	Metadata only; no dispatch mapping to executable code.	Unblocked
5	High	Causal Confidence	No formula for chained/forward inference confidence.	Unblocked
6	High	Recursive Budget	Budget not consumed; runaway recursion possible.	Unblocked
7	Medium	Multi-User	users:[] defined but never handled.	Document as Deferred
8	Medium	Inertia (Frame Problem)	No persistence axioms for unchanged state.	Unblocked
9	Medium	Pragmatic Ambiguity	Same type used for user affect vs. conversation dynamics.	Unblocked
10	Medium	Self Modes	Triggers/effects unspecified for mode changes.	Unblocked
11	Low	Dead Constraints	current_constraints: string[] is unused.	Remove
12	Low	Unstructured Limits	known_limits strings are not machine-checkable.	Unblocked
13	Low	Temporal Intervals	Lost Allen relations; overlap queries expensive.	Unblocked
