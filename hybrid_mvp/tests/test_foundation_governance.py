"""Foundation routing successors; historical assertions remain unchanged."""
from collections import Counter
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AMENDMENT = "docs/superpowers/specs/2026-09-07-foundation-proof-corrective-amendment.md"
PLAN = "docs/superpowers/plans/2026-09-07-foundation-proof-implementation-plan.md"
R4_AMENDMENT = "docs/superpowers/specs/2026-08-29-r4-1-data-supervision-corrective-amendment.md"
HISTORICAL_ROUTES = (
    "docs/superpowers/specs/2026-09-03-r4-closure-slice-anti-recursion-design.md",
    "docs/superpowers/specs/2026-09-03-unresolved-designation-and-research-handoff-design.md",
    "docs/superpowers/plans/2026-09-03-unresolved-designation-implementation-plan.md",
    "docs/superpowers/plans/2026-09-03-r4-closure-slice-implementation-plan.md",
)

__cemm_test_inventory__ = {
    "tests/test_foundation_governance.py::test_foundation_classifies_every_authority_document_once": {
        "source_ast_sha256": "05f180497b91cbd56189ecb73122dd6142bf9f21601dd9f9f2a03ddcbc91c50c",
        "activation_phase": "G0",
        "assertion_ref": "assertion:authority-cleanup-classifies-documents-exactly",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-1",
        "owner_ref": "governance",
    },
    "tests/test_foundation_governance.py::test_foundation_routes_current_work_without_promoting_admission": {
        "source_ast_sha256": "f136807893cb3334218a11e490920f10f5689fe86c396ac1e0ff829a509e6482",
        "activation_phase": "G0",
        "assertion_ref": "assertion:r4-closure-stop-routes-only-to-reviewed-representation-design",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Proof-Task-1",
        "owner_ref": "governance",
    },
}


def test_foundation_classifies_every_authority_document_once():
    authority = json.loads((ROOT / "docs/DOCUMENT_AUTHORITY.json").read_text())
    classes = tuple(authority[name] for name in (
        "governing_documents", "historical_evidence", "superseded_execution_claims",
    ))
    counts = Counter(path for paths in classes for path in paths)
    documents = {path.relative_to(ROOT).as_posix() for path in (ROOT / "docs").rglob("*.md")}
    assert documents | {"AGENTS.md", "README.md", "INTEGRATION.md"} <= counts.keys()
    assert all(count == 1 for count in counts.values())
    assert authority["governing_documents"][:4] == ["AGENTS.md", AMENDMENT, PLAN, R4_AMENDMENT]
    assert authority["scope"] == "hybrid_mvp/"
    assert authority["root_adoption_requires_separate_review"] is True
    assert authority["generated_artifacts_are_authority"] is False


def test_foundation_routes_current_work_without_promoting_admission():
    authority = json.loads((ROOT / "docs/DOCUMENT_AUTHORITY.json").read_text())
    assert set(HISTORICAL_ROUTES) <= set(authority["historical_evidence"])
    assert set(HISTORICAL_ROUTES).isdisjoint(authority["governing_documents"])
    for path in HISTORICAL_ROUTES:
        banner = "\n".join((ROOT / path).read_text(encoding="utf-8").splitlines()[:20]).casefold()
        assert "historical" in banner or "superseded" in banner
        assert Path(AMENDMENT).name in banner or Path(PLAN).name in banner
    for path in (
        "AGENTS.md", "README.md", "INTEGRATION.md", "docs/ARCHITECTURE.md",
        "docs/IMPLEMENTATION_PLAN.md", "docs/REPLAY_GOVERNANCE.md",
    ):
        text = " ".join((ROOT / path).read_text(encoding="utf-8").casefold().split())
        assert Path(AMENDMENT).name in text, path
        assert "task 4 requires a reviewed form-evidence amendment" not in text, path
    amendment = " ".join((ROOT / AMENDMENT).read_text(encoding="utf-8").split())
    assert "R5 training, selection, calibration, frozen evaluation and realization activation remain unavailable" in amendment
    assert "diagnostic" in amendment
    assert "no phase admission" in amendment
    assert "governance/replay_status.jsonl" in amendment
