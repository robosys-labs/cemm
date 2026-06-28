import math


def log_odds(p: float) -> float:
    if p <= 0.0:
        return -float("inf")
    if p >= 1.0:
        return float("inf")
    return math.log(p / (1.0 - p))


def probability(log_odds_val: float) -> float:
    if log_odds_val == float("inf"):
        return 1.0
    if log_odds_val == -float("inf"):
        return 0.0
    return 1.0 / (1.0 + math.exp(-log_odds_val))


def prior_log_odds(base_rate: float = 0.5) -> float:
    return log_odds(base_rate)


def source_evidence_weight(source_trust: float, evidence_count: int) -> float:
    return source_trust * math.log(evidence_count + 1.0)


def direct_confirmation_weight(confirmations: int, total_observations: int) -> float:
    if total_observations == 0:
        return 0.0
    ratio = confirmations / total_observations
    return math.log(confirmations + 1.0) * (ratio - 0.5) * 2.0


def frame_validity_weight(frame_confidence: float, temporal_overlap: float = 1.0) -> float:
    return frame_confidence * temporal_overlap * 0.5


def contradiction_weight(contradiction_strength: float) -> float:
    return -abs(contradiction_strength) * 2.0


def staleness_weight(age_ms: float, half_life_ms: float = 86400000.0) -> float:
    decay = -math.log(2.0) * (age_ms / half_life_ms)
    return decay * 0.3


def update_log_odds(
    current_log_odds: float,
    source_trust: float = 0.5,
    evidence_count: int = 0,
    confirmations: int = 0,
    total_observations: int = 0,
    frame_confidence: float = 0.5,
    temporal_overlap: float = 1.0,
    contradiction_strength: float = 0.0,
    age_ms: float = 0.0,
    half_life_ms: float = 86400000.0,
    base_rate: float = 0.5,
) -> float:
    total = current_log_odds
    total += prior_log_odds(base_rate)
    total += source_evidence_weight(source_trust, evidence_count)
    total += direct_confirmation_weight(confirmations, total_observations)
    total += frame_validity_weight(frame_confidence, temporal_overlap)
    total += contradiction_weight(contradiction_strength)
    total += staleness_weight(age_ms, half_life_ms)
    return total
