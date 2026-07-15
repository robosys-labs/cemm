from pathlib import Path
import json

def test_foundations_exclude_chat_domain_concepts():
    text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in Path("cemm/data/foundations").glob("*.json")
    )
    for forbidden in ('"machine"', '"engineer"', '"president"', '"leader"'):
        assert forbidden not in text

def test_all_language_constructions_are_typed():
    for path in Path("cemm/data/languages").glob("*/pack.json"):
        pack = json.loads(path.read_text(encoding="utf-8"))
        for construction in pack["constructions"]:
            assert construction.get("terms")
            assert not isinstance(construction.get("pattern"), str)

def test_v341_contains_no_boot_vocabulary_tables():
    text = Path("cemm/kernel/boot/v341.py").read_text(encoding="utf-8")
    assert "_PREDICATES" not in text
    assert "_LEXEMES" not in text
    assert "_CONSTRUCTIONS" not in text
