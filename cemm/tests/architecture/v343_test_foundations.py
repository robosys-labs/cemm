from pathlib import Path

from cemm.kernel.boot.v343 import load_v343_package
from cemm.kernel.foundations.validator import validate_data_root


DATA_ROOT = Path("cemm/data")


def test_foundations_and_two_language_packs_validate():
    package = load_v343_package(DATA_ROOT)
    assert package.foundations.validate() == ()
    assert {"en", "fr"} <= set(package.language_packs)


def test_domain_concepts_are_not_foundation_primitives():
    assert validate_data_root(DATA_ROOT) == ()
    text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (DATA_ROOT / "foundations" / "v343").glob("*.json")
    )
    for key in ("machine", "leader", "president", "engineer"):
        assert f'"{key}"' not in text


def test_language_pack_has_no_content_literal_segments():
    package = load_v343_package(DATA_ROOT)
    for semantic_pack in package.language_packs.values():
        for construction in semantic_pack.realization.constructions:
            for segment in construction.segments:
                if segment.kind.value == "punctuation":
                    assert not any(ch.isalnum() for ch in segment.punctuation)
                if segment.kind.value == "space":
                    assert not segment.schema_ref
