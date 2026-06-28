import math


def compute_relevance(
    claim_predicate: str,
    goal_keywords: list[str],
    entity_overlap: int = 0,
    total_goal_entities: int = 1,
) -> float:
    if not goal_keywords:
        return 0.5
    predicate_terms = set(claim_predicate.lower().split("_"))
    goal_terms = set(g.lower() for g in goal_keywords)
    term_overlap = len(predicate_terms & goal_terms)
    text_score = term_overlap / max(len(goal_terms), 1)
    entity_score = entity_overlap / max(total_goal_entities, 1)
    return min(1.0, (text_score * 0.6 + entity_score * 0.4) * 1.5)


def score_claim(
    relevance: float = 0.5,
    trust: float = 0.5,
    confidence: float = 0.5,
    salience: float = 0.0,
    recency: float = 1.0,
    permission_valid: bool = True,
    contradiction_penalty: float = 0.0,
) -> float:
    if not permission_valid:
        return 0.0
    effective_salience = max(salience, 0.1)
    return (
        relevance
        * trust
        * confidence
        * effective_salience
        * recency
    ) - contradiction_penalty


def score_model(
    applicability: float = 0.5,
    trust: float = 0.5,
    confidence: float = 0.5,
    utility: float = 0.0,
    permission_valid: bool = True,
    cost_penalty: float = 0.0,
    risk_penalty: float = 0.0,
) -> float:
    if not permission_valid:
        return 0.0
    return (
        applicability
        * trust
        * confidence
        * utility
    ) - cost_penalty - risk_penalty


def score_action(
    expected_user_value: float = 0.5,
    confidence: float = 0.5,
    permission_valid: bool = True,
    self_coherence: float = 1.0,
    latency_cost: float = 0.0,
    compute_cost: float = 0.0,
    risk_cost: float = 0.0,
    uncertainty_penalty: float = 0.0,
) -> float:
    if not permission_valid:
        return 0.0
    return (
        expected_user_value
        * confidence
        * self_coherence
    ) - latency_cost - compute_cost - risk_cost - uncertainty_penalty
