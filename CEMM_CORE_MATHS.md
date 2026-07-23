# CEMM v3.5.1 Core Mathematics — Grounded Semantic Dynamics

**Status:** canonical mathematical contract  
**Purpose:** formalize exact semantic representation, recurrent neural-style meaning formation, multimodal grounding, world-state estimation, role-sensitive action dynamics, causal inference, recursive learning, impact, goals and response generation.

---

# 1. Global cognitive state

At cycle time \(t\):

\[
\mathcal C_t=(S_t,G_t,\alpha_t,B_t,\mathcal M_t,E_t,V_t,D_t,F_t,\Pi_t)
\]

- \(S_t\): exact authority snapshot;
- \(G_t\): working CSIR graph;
- \(\alpha_t\): activation state over graph candidates;
- \(B_t\): grounded belief over referent state variables;
- \(\mathcal M_t\): causal/dynamic mechanism graph;
- \(E_t\): epistemic support/opposition;
- \(V_t\): goals, values, impact and significance;
- \(D_t\): discourse/common ground;
- \(F_t\): typed learning and reasoning frontiers;
- \(\Pi_t\): evidence, proof and authority lineage.

The state is sparse, typed and context-indexed.

---

# 2. Exact authority snapshot

\[
S=(K,C,N,D,O,\Theta,U,L,M,P,A,B,\Omega)
\]

where:

- \(K\): Kernel Semantic ABI;
- \(C\): definition compiler ABI;
- \(N\): CSIR normalizer/equivalence ABI;
- \(D\): semantic definitions;
- \(O\): operational profiles;
- \(\Theta\): semantic-dynamics parameters;
- \(U\): use authorizations;
- \(L\): language and multimodal projection authority;
- \(M\): causal mechanism authority;
- \(P\): policy;
- \(A\): runtime adapters;
- \(B\): boot authority;
- \(\Omega\): ordered overlays.

Snapshot root:

\[
R_S=H(K\|C\|N\|R_D\|R_O\|R_\Theta\|R_U\|R_L\|R_M\|R_P\|R_A\|R_B\|R_\Omega)
\]

Every executable pin includes kind, namespace, ref, revision, content hash and scope.

No executable dependency may use `latest`, `maximum`, a semantic key, a revision range or a floating authoritative parent.

---

# 3. CSIR graph

A CSIR graph is:

\[
G=(T,V,A,B,Q,R,\Pi)
\]

- \(T\): grounded terms/referents/literals/times/contexts;
- \(V\): typed variables;
- \(A\): typed n-ary applications;
- \(B\): port bindings;
- \(Q\): context/time/polarity/modality/source/permission qualifiers;
- \(R\): scope, coordination, identity, ordering and dependency relations;
- \(\Pi\): proof/evidence/authority annotations.

Each application \(a\) pins an exact definition closure \(Cl_S(a)\).

---

# 4. Definition compilation and canonical meaning

A definition:

\[
D_\sigma=(P_\sigma,G_\sigma,C_\sigma,\Delta_\sigma)
\]

contains formal ports, a definition graph, constraints and exact dependencies.

Closure:

\[
Cl_S(p)=\mu X.\left(\{p\}\cup\bigcup_{q\in X}deps_S(q)\right)
\]

Compilation under substitution \(\theta\):

\[
Compile_S(p,\theta)=NF_S\left(\bigcup_{q\in Cl_S(p)}G_q\theta_q\right)
\]

Semantic equivalence:

\[
G_1\equiv_S G_2 \iff NF_S(G_1)=NF_S(G_2)
\]

A higher-order concept is valid only when its abstraction is conservative over its expansion.

---

# 5. Semantic neural state

For each candidate CSIR node/application/binding \(i\), maintain:

\[
h_i^{(k)}=(\alpha_i^{(k)},\mathbf e_i,\mathbf q_i,\Sigma_i)
\]

where:

- \(\alpha_i\) is activation/support mass;
- \(\mathbf e_i\) is a learned continuous representation used for similarity and message functions;
- \(\mathbf q_i\) contains exact type/context/role features;
- \(\Sigma_i\) represents uncertainty/calibration state.

The embedding \(\mathbf e_i\) is not semantic identity. Semantic identity remains the exact CSIR/authority pin.

---

# 6. Typed recurrent message passing

For typed edge/factor relation \(r\), message from \(i\) to \(j\):

\[
m_{i\to j}^{(k,r)}=
\psi_r(h_i^{(k)},h_j^{(k)},x_{ij},S)
\]

Node update:

\[
\tilde h_j^{(k+1)}=
\phi_j\left(h_j^{(k)},
\operatorname{AGG}_{r,i}m_{i\to j}^{(k,r)},
E,S\right)
\]

Hard semantic mask:

\[
h_j^{(k+1)}=
\begin{cases}
\tilde h_j^{(k+1)} & HardCompatible(j,S)=1\\
0 & otherwise
\end{cases}
\]

Relations use separate parameter families for:

```text
port-role compatibility
type entitlement
scope
context/world
time/aspect
identity/coreference
causal expectation
state dependency
discourse relation
construction evidence
multimodal alignment
```

No single undifferentiated attention matrix is semantic authority.

---

# 7. Energy and attractor meaning

Let \(x\) encode candidate senses, referents, roles, scopes, contexts and graph fragments.

\[
\mathcal E(x)=
\mathcal E_{obs}
+\mathcal E_{lex}
+\mathcal E_{bind}
+\mathcal E_{type}
+\mathcal E_{scope}
+\mathcal E_{time}
+\mathcal E_{context}
+\mathcal E_{causal}
+\mathcal E_{discourse}
+\mathcal E_{complexity}
\]

Hard violations have infinite energy.

Meaning formation seeks stable low-energy semantic-equivalence classes:

\[
[G^*]\approx\arg\min_{[G]\in\mathcal F_S}\mathcal E([G];E,S)
\]

Recurrent convergence criterion:

\[
\|\alpha^{(k+1)}-\alpha^{(k)}\|<\varepsilon
\quad\land\quad
NF(G^{(k+1)})=NF(G^{(k)})
\]

A stable partial graph with explicit variables/frontiers is a valid attractor.

---

# 8. Bottom-up and top-down coupling

Bottom-up message:

\[
m^{BU}=f_{obs}(o,span,track,calibration)
\]

Top-down prediction from candidate definition \(\sigma\):

\[
m^{TD}=f_{pred}(ports_\sigma,types_\sigma,scope_\sigma,state_\sigma)
\]

Combined update:

\[
\alpha_i^{k+1}=\sigma\left(
 b_i+m_i^{BU}+m_i^{TD}+m_i^{context}-m_i^{inhibition}
\right)
\]

Top-down prediction may open or rank expected roles. It may not fabricate grounded fillers.

---

# 9. Evidence calibration and dependence

Calibrated contribution:

\[
\phi_i(h,e_i)=\log\frac{P(e_i\mid h,S)}{P(e_i\mid\neg h,S)}
\]

Evidence with shared lineage is clustered and discounted. For lineage clusters \(L_j\):

\[
Score(h)=\sum_j JointEvidenceScore(h,L_j)
\]

not the naive sum of all derived signals.

Posterior is computed over normalized semantic classes, not derivations:

\[
P([G]\mid E,S)=
\frac{\sum_{h:NF(G_h)=NF(G)}e^{Score(h)}}
{\sum_{[G']}\sum_{h:NF(G_h)=NF(G')}e^{Score(h)}}
\]

---

# 10. Grounded state spaces

For referent \(r\), active state space:

\[
\mathcal Z_r(S,c,t)=\prod_{d\in Entitled(r,S,c,t)}\mathcal V_d
\]

State variable:

\[
Z_{r,d,t}\in\mathcal V_d
\]

State domains can be discrete, continuous, vector, relational, set-valued or process-valued.

Belief state:

\[
b_{r,d,t}(z)=P(Z_{r,d,t}=z\mid O_{\le t},K,S)
\]

---

# 11. Multimodal observation model

For observation \(o_t^m\) from modality \(m\):

\[
p(o_t^m\mid Z_{r,d,t}=z,\kappa_m)
\]

where \(\kappa_m\) is calibration authority.

Bayesian filtering form:

\[
b_t(z)\propto
p(o_t\mid z)\int p(z\mid z',a_{t-1},c)\,b_{t-1}(z')\,dz'
\]

For discrete spaces, replace the integral with a sum.

Identity uncertainty is jointly represented:

\[
P(r,z\mid o)\propto P(o\mid r,z)P(z\mid r)P(r)
\]

Modalities may fuse only when context/time/identity compatibility holds.

---

# 12. Temporal and geospatial semantics

State assignment:

\[
s=(r,d,v,[t_0,t_1),c,\pi)
\]

Current-state logic is at least three-valued: true, false, unknown.

Geospatial state includes position, orientation and qualitative relations:

\[
Pos_r(t)\in\mathbb R^n
\]

plus graph predicates such as inside, touching, supported-by, near, connected-to and reachable.

Spatial transitions use exact frame/reference authority. “Left,” “near,” and “above” are context/reference-frame qualified.

---

# 13. Event/action semantics

An event/action instance:

\[
e=(p_a,\beta,c,[t_0,t_1],q)
\]

where \(p_a\) is the exact event/action definition and \(\beta\) binds semantic roles to participants.

A mechanism:

\[
T_a^\theta:(\mathbf Z_{\beta,t},c)\to
P(\Delta\mathbf Z_{\beta},E_{secondary}\mid\mathbf Z_{\beta,t},c)
\]

Effects are role-addressed:

\[
\Delta Z_{\beta(role),d}
\]

not subject/object addressed.

---

# 14. Direct transition and graph rewrite

A deterministic mechanism is a graph rewrite:

\[
T=(P,N,\Delta^+,\Delta^-,W)
\]

Applicable iff:

\[
Match(P,e\cup K_t)\land\neg Match(N,e\cup K_t)
\land Auth_S(T,transition)
\]

Preview:

\[
K'=(K_t\setminus\Delta^-)\cup\Delta^+
\]

Probabilistic mechanism:

\[
P(K'\mid K_t,e,c,\theta_T)
\]

Commit still requires a specific authorized delta and exact pre-state CAS.

---

# 15. Cross-dimensional mechanisms

For dimensions \(d_i,d_j\):

\[
Z_{r,d_j,t+1}:=f_{ij}(Z_{r,d_i,t},Pa,c,U;\theta_{ij})
\]

Example thermal-to-affective mechanism:

\[
Comfort_{r,t+1}=
 f(Temperature_{r,t},ComfortRange_r,Exposure,Health,Context,U)
\]

This is not:

\[
Temperature \equiv Emotion
\]

Type entitlement and individual/context parameters determine applicability.

---

# 16. Structural causal model

For each endogenous semantic state variable \(X_i\):

\[
X_i(t+1):=f_i(Pa_i(t),A_t,C_t,U_i;\theta_i)
\]

Causal graph \(\mathcal M=(X,E_M,F,\Theta)\).

Observation:

\[
P(X\mid O=o)
\]

Intervention:

\[
P(X\mid do(A=a))
\]

Counterfactual:

\[
P(Y_{a'}\mid A=a,Y=y,O)
\]

Counterfactual worlds are context-isolated and never mutate actual state.

---

# 17. Recursive causal propagation

Let direct delta set be \(\Delta_0\).

Dependency propagation:

\[
\Delta_{k+1}=Propagate(\Delta_k,K_t,\mathcal M,S)
\]

Closure:

\[
\Delta^*=\mu X.(\Delta_0\cup Propagate(X))
\]

subject to:

```text
maximum depth
maximum generated events/deltas
cycle classification
confidence decay or probabilistic integration
context isolation
proof-size budget
```

Each derived delta contains its causal path.

---

# 18. Capability dynamics

\[
Capable(r,a,c,t)=
Afforded(r,a)
\land DependenciesSatisfied(r,a,c,t)
\land ResourcesAvailable(r,a,c,t)
\land AdapterAvailable(a,t)
\]

Capability status posterior can be derived from uncertain dependencies:

\[
P(Capable)=P(\bigwedge_j D_j\land R\land A)
\]

Permission and competence remain separate variables.

---

# 19. Epistemic semantics

For proposition \(p\), context \(c\), time \(t\):

\[
Truth(p,c,t)=(s,o)
\]

with support/opposition values, optionally weighted by source and evidence quality.

Admission:

\[
Admit(e,p,c,u,S)\in\{allow,deny,preserve\_only\}
\]

Inference uses admitted premises appropriate for its target context/use.

---

# 20. Query and explanation

Query:

\[
Q=(v,R(v),\pi,c,t,u)
\]

Answers:

\[
Ans(Q,K)=\{\theta(v)\mid K\models R\theta\land Visible(\theta,c,t,u)\}
\]

Causal explanation seeks a minimal warranted subgraph \(P\):

\[
P^*=\arg\min_P Cost(P)
\]

subject to:

\[
P\vdash target
\]

and proof, relevance and audience constraints.

---

# 21. Prediction error and recursive learning

Predicted next state/observation:

\[
\hat Z_{t+1}=E[Z_{t+1}\mid\mathcal C_t]
\]

\[
\hat O_{t+1}=E[O_{t+1}\mid\hat Z_{t+1}]
\]

Error:

\[
\epsilon_t=(O_t-\hat O_t,Z_t-\hat Z_t)
\]

Frontier classifier:

\[
F_t=ClassifyError(\epsilon_t,G_t,B_t,\mathcal M_t,S)
\]

Possible targets include lexical, grounding, state, causal, parameter, context, capability, impact and response competence.

---

# 22. Continuous parameter learning

For differentiable parameter authority \(\theta\):

\[
\theta' = \theta-\eta\nabla_\theta\mathcal L
\]

Typical loss:

\[
\mathcal L=
\lambda_o\mathcal L_{observation}
+\lambda_s\mathcal L_{semantic\ class}
+\lambda_p\mathcal L_{state\ prediction}
+\lambda_c\mathcal L_{causal\ prediction}
+\lambda_r\mathcal L_{roundtrip}
+\lambda_{cal}\mathcal L_{calibration}
\]

The update produces a candidate parameter artifact. Promotion requires replay, independent competence, calibration and use-specific risk gates.

Local Hebbian-like association may be used as a candidate signal:

\[
\Delta w_{ij}\propto \alpha_i\alpha_j
\]

but co-activation alone never proves semantic identity or causality.

---

# 23. Discrete definition and causal-structure learning

Candidate definition \(D\) is selected by fit, closure and compression:

\[
Score(D)=Fit(D;E)-\lambda Complexity(D)+\mu Reuse(D)-\rho Contradiction(D)
\]

Causal structure candidate \(\mathcal M'\):

\[
Score(\mathcal M')=
\log P(E\mid\mathcal M')
-\lambda |\mathcal M'|
+InterventionSupport
-CounterexamplePenalty
\]

Promotion remains per use and requires independent evidence.

---

# 24. Competence and authority promotion

For authority item \(a\), use \(u\):

\[
p_{a,u}\sim Beta(\alpha_{a,u},\beta_{a,u})
\]

or another calibrated family appropriate to the outcome type.

Promotion:

\[
Promote(a,u)\iff
Closed(a)
\land IndependentEvidence(a,u)
\land CounterexampleCoverage(a,u)
\land Calibration(a,u)
\land Permission(a,u)
\land P(p_{a,u}\ge q_u)\ge\gamma_u
\]

Structural closure and semantic conservativity are hard gates, not probabilities.

---

# 25. Impact mathematics

For transition from \(Z_t\) to \(Z_{t+1}\), stakeholder \(s\), goal set \(g\):

\[
I_{s,g}=\Phi_s(Z_{t+1}-Z_t,g,c,t)
\]

Impact is a vector:

\[
I=(direction,valence,magnitude,duration,reversibility,risk,uncertainty)
\]

Affective consequence for experiencer \(r\):

\[
P(Affect_{r,t+1}\mid\Delta Z,Traits_r,Context,History)
\]

must remain separate from the physical delta and from user-reported emotion.

---

# 26. Goal and action selection

For goal \(g\):

\[
U(g)=Benefit-Cost-Risk+Obligation+Urgency+InformationGain
\]

Select compatible set:

\[
\max_{x_i\in\{0,1\}}\sum_i U(g_i)x_i
\]

subject to conflict, permission, resource, safety and precedence constraints.

Planning uses causal simulation:

\[
\pi^*=\arg\max_\pi E[U(Z_T)\mid do(\pi),B_t,\mathcal M,S]
\]

---

# 27. Response generation

Candidate response semantic graph \(R\) is evaluated by:

\[
U_R(R)=
\lambda_q Coverage(R,Q)
+\lambda_t TruthPreservation(R)
+\lambda_i InformationGain(R)
+\lambda_s SocialAppropriateness(R)
+\lambda_e ImpactSensitivity(R)
-\lambda_r Risk(R)
-\lambda_c Cost(R)
\]

subject to:

```text
exact semantic authority
source and uncertainty preservation
permission/privacy/safety
fresh operation state
target-bearing discourse act
realizability
```

\[
R^*=\arg\max_{R\in\mathcal R_S}U_R(R)
\]

Surface generation:

\[
y^*=Realize_L(R^*)
\]

Round-trip:

\[
\exists G_y\in Analyze_S(y^*):G_y\equiv_S R^*
\]

Round-trip is necessary but not sufficient for emission.

---

# 28. Decisiveness and uncertainty

For best semantic class \(g^*\):

\[
Decisive_u(g^*)=
[P(g^*)\ge\tau_u]
\land[H(G\mid E)\le\eta_u]
\land[RequiredVars_u=\varnothing]
\land[Auth_S(g^*,u)]
\land[Risk\le\rho_u]
\]

Transition, action, causal assertion and high-impact response require stricter thresholds than mention or provisional composition.

---

# 29. Invalidation and replay

Dependency graph \(D=(N,E)\).

\[
Affected(X)=\mu Y.\left(X\cup\{v\mid\exists u\in Y:(u,v)\in E\}\right)
\]

A changed definition, parameter, calibration, causal mechanism, state premise or policy invalidates all dependent projections and decisions.

Historical records retain their original snapshot roots.

---

# 30. Required mathematical acceptance tests

1. exact definition closure is deterministic and content-addressed;
2. changing a dependency, dynamics parameter or calibration changes the authority root;
3. embeddings cannot make hard-incompatible graphs executable;
4. recurrent updates converge or return bounded incompleteness;
5. duplicate derivations do not inflate semantic-class confidence;
6. correlated multimodal evidence is not double counted;
7. subject/object changes do not alter role-bound effect semantics across active/passive paraphrases;
8. state effects are identical across languages when CSIR role bindings match;
9. temperature and affect remain distinct dimensions with explicit causal links;
10. type-conditioned mechanisms produce different consequences for animal, server and room;
11. recursive causal propagation is cycle-bounded and proof-bearing;
12. intervention and observation are not conflated;
13. hypothetical/counterfactual simulation cannot mutate actual state;
14. prediction errors create typed frontiers;
15. continuous parameter changes require new pinned artifacts;
16. learned causal edges require competence beyond temporal correlation;
17. capability deltas derive from dependencies;
18. response semantics preserve causal/epistemic qualification;
19. realization cannot invent unsupported meaning;
20. every committed state/action/response decision is replayable from exact snapshot and pre-state.

# Phase 15–16 causal/state mathematics completion

## Typed state domains
For exact dimension `d`, let its reviewed domain be `D_d` and runtime value `z_{r,d,t} in D_d`.
A transform is a partial typed function `T_m : D_1 x ... x D_k -> D_d`; it is undefined rather
than coerced when unit/frame/manifold/type constraints fail. Categorical assignment is equality;
ordered shift follows exact reviewed order; scalar affine transforms preserve units; vector
transforms preserve exact coordinate/manifold contracts; set/process/relation/distribution
operators preserve their own algebra. A probabilistic value is a normalized measure over typed
state values from the exact support domain, not over untyped string keys.

## Structural equations and interventions
For endogenous variable `X_i`:
`X_i := f_i(Pa_i, U_i ; theta_i)`.
Observation computes `P(Y | X=x, E)`. Intervention computes the mutilated model
`M_do(X=x)` by replacing `f_X` with constant `x` and removing all incoming edges to `X`.

Counterfactual:
1. `P(U | E=e)` (abduction),
2. build `M_do(X=x)`,
3. evaluate `Y_x(U)` while holding the abducted exogenous/background realization fixed.
Unidentified abduction is an information frontier, not a probability invented from absence.

## Bounded propagation and probability mass
Each branch b carries absolute probability `p_b` and confidence `c_b`. Exact-independent
stochastic mechanisms may compose by product; independence may never be inferred merely because
two branch sets are present. Pruning/budget exhaustion reports unresolved probability mass
`1 - sum_b p_b`; a surviving branch is never renormalized to false certainty.

## Competing mechanism aggregation
For simultaneous mechanisms `{m_j}` targeting the same variable/time, an explicit aggregation
operator `A` is required:
`Delta Z = A(Delta Z_1, ..., Delta Z_n | exact authority)`.
Absent an exact aggregation contract/evaluator, the transition is unresolved; mechanism order is
not used as a hidden conflict policy.

## Causal proof and explanation
A proof DAG step is `s=(M, X_src, E_src, Y, p, c, W, Parents)`. Explanation is a minimal
warranted reverse subgraph from target Y to root causes. Query, prediction, impact, planning and
learning must reuse this DAG. Causal candidate research scores explicit hypotheses using
lineage-discounted evidence plus complexity penalty and requires intervention/mechanism evidence;
association alone cannot activate an edge. `why/cause-of` explanation traverses this DAG toward
ancestors; `effect-of` traverses toward descendants. Direction is part of the semantic projection,
not inferred from language wording.

## Final v3.5.1 mathematical clarifications

This document is the canonical mathematical contract for v3.5.1. Inactive hard-masked semantic states are bottom/ineligible states, not ordinary zero-evidence states. Posterior/support aggregation is over evidence-dependence quotient classes rather than derivation count. Without an exact joint model, correlated transforms cannot multiply support. Multimodal fusion is conditioned on candidate identity hypotheses. Interventions use do-semantics rather than conditioning; feedback requires explicit equilibrium authority or time-unrolling. Operation results re-enter as observations under the same AuthorityGeneration with a bounded two-hop recurrence budget. Oscillation or budget exhaustion is typed partial cognition, never convergence.

