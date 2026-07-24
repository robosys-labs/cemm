"""Final semantic-activation helpers.

Mechanism only: this module separates observation/form/language uncertainty.
It does not contain vocabulary, predicate names, language-specific grammar or
domain ontology branches.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections import defaultdict


@dataclass(frozen=True, slots=True)
class TurnLanguageDecision:
    language_tag: str | None
    confidence: float
    competing_tags: tuple[str, ...]
    positive_language_tags: tuple[str, ...]
    code_switching: bool


def decide_turn_language(observations, forms, hints=()) -> TurnLanguageDecision:
    """Derive turn language from positive form evidence, never script fallback.

    Span-level LanguageEvidence may retain weak script-compatible candidates.
    This decision intentionally ignores those weak candidates unless they also
    produced an actual reviewed form/morphology match.
    """
    semantic = tuple(
        item for item in observations
        if item.category not in {"whitespace", "punctuation", "symbol"}
    )
    by_observation = defaultdict(list)
    for form in forms:
        for observation_ref in form.observation_refs:
            by_observation[observation_ref].append(form)

    scores = defaultdict(float)
    unambiguous_span_tags = []
    for observation in semantic:
        candidates = tuple(by_observation.get(observation.observation_ref, ()))
        if not candidates:
            continue
        best_by_tag = {}
        for candidate in candidates:
            weight = float(candidate.confidence)
            # A multi-observation form contributes fractionally at each covered
            # observation so it does not outvote an equivalent atomic path merely
            # because it spans more tokens.
            weight /= max(1, len(candidate.observation_refs))
            best_by_tag[candidate.language_tag] = max(
                weight, best_by_tag.get(candidate.language_tag, 0.0)
            )
        if not best_by_tag:
            continue
        best = max(best_by_tag.values())
        winners = tuple(sorted(
            tag for tag, score in best_by_tag.items()
            if score >= best - 0.05
        ))
        for tag in winners:
            scores[tag] += best_by_tag[tag] / len(winners)
        if len(winners) == 1:
            unambiguous_span_tags.append(winners[0])

    hint_set = tuple(sorted(set(hints)))
    for tag in hint_set:
        scores[tag] += 1.0

    positive = tuple(sorted(scores))
    if not scores:
        return TurnLanguageDecision(
            hint_set[0] if len(hint_set) == 1 else None,
            1.0 if len(hint_set) == 1 else 0.0,
            (),
            hint_set,
            False,
        )

    ordered = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    best_tag, best_score = ordered[0]
    second = ordered[1][1] if len(ordered) > 1 else 0.0
    decisive = (
        len(hint_set) == 1
        or len(ordered) == 1
        or best_score - second >= 0.50
        or best_score >= max(1.0, second * 1.75)
    )
    competing = tuple(
        tag for tag, score in ordered[1:]
        if score >= best_score - 0.50
    )
    unique_span_tags = tuple(sorted(set(unambiguous_span_tags)))
    code_switching = len(unique_span_tags) > 1 and not (
        len(hint_set) == 1 and all(tag == hint_set[0] for tag in unique_span_tags)
    )
    total = sum(scores.values())
    confidence = 0.0 if total <= 0 else min(1.0, best_score / total)
    return TurnLanguageDecision(
        best_tag if decisive else None,
        confidence,
        competing if not decisive else (),
        positive,
        code_switching,
    )


@dataclass(frozen=True, slots=True)
class FormPathCandidate:
    path_ref: str
    selected_form_candidate_refs: tuple[str, ...]
    gap_observation_refs: tuple[str, ...]
    score: float
    evidence_refs: tuple[str, ...]


def enumerate_form_paths(observations, forms, *, maximum_paths: int = 64):
    """Enumerate bounded exact-coverage paths over semantic observations.

    Every semantic observation is explained once by a selected form candidate
    or by an explicit gap. Normalization/multiword candidates therefore compete
    as alternative explanations instead of becoming simultaneous semantics.
    """
    if maximum_paths < 1:
        raise ValueError("maximum_paths must be positive")
    semantic = tuple(
        item for item in observations
        if item.category not in {"whitespace", "punctuation", "symbol"}
    )
    refs = tuple(item.observation_ref for item in semantic)
    ref_index = {ref: index for index, ref in enumerate(refs)}
    starts = defaultdict(list)
    for form in forms:
        if not form.observation_refs:
            continue
        try:
            indices = tuple(ref_index[ref] for ref in form.observation_refs)
        except KeyError:
            continue
        if indices != tuple(range(indices[0], indices[0] + len(indices))):
            continue
        starts[indices[0]].append(form)
    for values in starts.values():
        values.sort(
            key=lambda item: (
                -len(item.observation_refs),
                -float(item.confidence),
                item.candidate_ref,
            )
        )

    paths = [(( ), ( ), 0.0, 0)]
    complete = []
    while paths and len(complete) < maximum_paths:
        selected, gaps, score, index = paths.pop(0)
        if index >= len(refs):
            complete.append((selected, gaps, score))
            continue
        options = starts.get(index, ())
        for form in options:
            paths.append((
                (*selected, form.candidate_ref),
                gaps,
                score + (float(form.confidence) - 0.5) * 2.0,
                index + len(form.observation_refs),
            ))
        # Partial understanding is always representable; the gap alternative is
        # lower-ranked than a reviewed form but never discarded.
        paths.append((
            selected,
            (*gaps, refs[index]),
            score - 1.25,
            index + 1,
        ))
        paths.sort(key=lambda item: (-item[2], len(item[1]), item[0], item[1]))
        paths = paths[:maximum_paths]

    from .schema.model import semantic_fingerprint
    result = []
    for selected, gaps, score in complete[:maximum_paths]:
        result.append(FormPathCandidate(
            path_ref="form-path:" + semantic_fingerprint(
                "form-path", (selected, gaps), 24
            ),
            selected_form_candidate_refs=tuple(selected),
            gap_observation_refs=tuple(gaps),
            score=score,
            evidence_refs=tuple(
                sorted({
                    ref
                    for form in forms
                    if form.candidate_ref in selected
                    for ref in form.evidence_refs
                })
            ) or tuple(refs),
        ))
    return tuple(result)
