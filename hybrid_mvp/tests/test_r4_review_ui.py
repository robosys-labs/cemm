"""Static safety and accessibility contract for the R4.1 review UI."""
from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
UI_ROOT = ROOT / "scripts/r4_1_review_ui"


class _ShellParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.sections: set[str] = set()
        self.inline_handlers: list[str] = []
        self.scripts: list[dict[str, str | None]] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        values = dict(attrs)
        if values.get("id"):
            self.ids.add(values["id"])
        if values.get("data-section"):
            self.sections.add(values["data-section"])
        self.inline_handlers.extend(
            key for key in values if key.casefold().startswith("on")
        )
        if tag == "script":
            self.scripts.append(values)


def test_review_ui_has_semantic_accessible_shell() -> None:
    parser = _ShellParser()
    parser.feed((UI_ROOT / "index.html").read_text(encoding="utf-8"))

    assert {
        "status-header",
        "workspace",
        "impact-dialog",
        "impact-title",
        "impact-content",
        "confirm-impact",
        "toast",
    } <= parser.ids
    assert parser.sections == {
        "dashboard",
        "structural",
        "purpose",
        "recipe",
        "designation",
        "export",
    }
    assert parser.inline_handlers == []
    assert parser.scripts == [{"src": "/app.js", "defer": None}]


def test_review_ui_javascript_is_thin_and_avoids_unsafe_dom_paths() -> None:
    source = (UI_ROOT / "app.js").read_text(encoding="utf-8")
    for forbidden in (
        "innerHTML",
        "outerHTML",
        "insertAdjacentHTML",
        "eval(",
        "new Function",
        "localStorage",
        "sessionStorage",
        "document.cookie",
        "http://",
        "https://",
    ):
        assert forbidden not in source
    for required in (
        "function renderDashboard",
        "function renderItems",
        "function renderStructuralCard",
        "function renderPurposeCard",
        "function renderRecipeCard",
        "function renderDesignationCard",
        "function renderExport",
        "document.createElement",
        "textContent",
        'X-CEMM-Review-Token',
        "busyPreviousDisabled",
    ):
        assert required in source


@pytest.mark.parametrize(
    "contract",
    (
        ":focus-visible",
        "prefers-reduced-motion",
        "@media (max-width: 900px)",
        "min-height: 44px",
        "max-width: 1440px",
        "overflow-wrap: anywhere",
    ),
)
def test_review_ui_css_preserves_accessibility_contract(contract: str) -> None:
    source = (UI_ROOT / "styles.css").read_text(encoding="utf-8")
    assert contract in source
