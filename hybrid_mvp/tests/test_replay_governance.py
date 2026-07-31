from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

GOVERNING_DOCUMENTS = (
    "AGENTS.md",
    "docs/superpowers/specs/2026-07-31-hybrid-mvp-corrective-replay-admission-design.md",
    "docs/superpowers/plans/2026-07-31-hybrid-mvp-corrective-replay-master-plan.md",
    "docs/superpowers/plans/2026-07-31-hybrid-mvp-g0-r1-implementation-plan.md",
    "docs/ARCHITECTURE.md",
    "docs/ABI_REGISTRY.md",
)

SUPERSEDED_EXECUTION_CLAIMS = (
    "docs/superpowers/specs/2026-07-29-authoritative-mvp-completion-design.md",
    "docs/superpowers/plans/2026-07-29-authoritative-mvp-master-roadmap.md",
    "docs/superpowers/plans/2026-07-29-m1-six-phase-kernel.md",
    "docs/superpowers/plans/2026-07-29-m2-hybrid-proposal-verifier.md",
    "docs/superpowers/plans/2026-07-29-m3-cognition-learning-realization.md",
    "docs/superpowers/plans/2026-07-29-m4-training-failure-competitive-evaluation.md",
    "docs/superpowers/plans/2026-07-29-m5-surfaces-reliable-cutover.md",
    "docs/superpowers/plans/2026-07-30-corrective-replay-plan.md",
)

HISTORICAL_EVIDENCE = (
    "docs/EVALUATION_REPORT.md",
    "docs/NEURAL_MODEL.md",
    "docs/COMPARISON.md",
    "docs/RUNTIME_TRACES.md",
    "docs/WORKTREE_INTEGRATION.md",
    "artifacts/",
)

ACTIVE_POINTERS = (
    "AGENTS.md",
    "README.md",
    "INTEGRATION.md",
    "docs/IMPLEMENTATION_PLAN.md",
    "docs/ABI_REGISTRY.md",
    "docs/superpowers/specs/2026-07-31-hybrid-mvp-corrective-replay-admission-design.md",
)


def _authority() -> dict[str, object]:
    return json.loads(
        (ROOT / "docs/DOCUMENT_AUTHORITY.json").read_text(encoding="utf-8")
    )


def test_document_authority_is_scoped_and_classifications_are_exact() -> None:
    authority = _authority()

    assert authority["schema"] == "cemm-hybrid-document-authority-v1"
    assert authority["scope"] == "hybrid_mvp/"
    assert authority["path_base"] == "hybrid_mvp/"
    assert authority["root_runtime_authority"] == "../AGENTS.md"
    assert authority["governing_documents"] == list(GOVERNING_DOCUMENTS)
    assert authority["superseded_execution_claims"] == list(
        SUPERSEDED_EXECUTION_CLAIMS
    )
    assert authority["historical_evidence"] == list(HISTORICAL_EVIDENCE)
    assert authority["generated_artifacts_are_authority"] is False
    assert authority["root_adoption_requires_separate_review"] is True

    classifications = (
        set(GOVERNING_DOCUMENTS),
        set(SUPERSEDED_EXECUTION_CLAIMS),
        set(HISTORICAL_EVIDENCE),
    )
    for index, current in enumerate(classifications):
        for other in classifications[index + 1 :]:
            assert current.isdisjoint(other)

    for relative in (
        *GOVERNING_DOCUMENTS,
        *SUPERSEDED_EXECUTION_CLAIMS,
        *HISTORICAL_EVIDENCE,
    ):
        assert (ROOT / relative.rstrip("/")).exists(), relative

    root_authority = (ROOT / str(authority["root_runtime_authority"])).resolve()
    assert root_authority == (ROOT.parent / "AGENTS.md").resolve()
    assert root_authority.is_file()


def test_governing_pointers_make_no_old_admission_claim() -> None:
    obsolete_claims = (
        re.compile(r"\bM1\s*[-–]\s*M3\s+are\s+complete\b", re.IGNORECASE),
        re.compile(
            r"\bM4\s+Tasks?\s+(?:1\s*[-–]\s*)?4\s+"
            r"(?:is|are)\s+(?:complete|implemented)\b",
            re.IGNORECASE,
        ),
    )

    for relative in ACTIVE_POINTERS:
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "proposed for user review" not in text.casefold()
        for pattern in obsolete_claims:
            assert pattern.search(text) is None, relative
