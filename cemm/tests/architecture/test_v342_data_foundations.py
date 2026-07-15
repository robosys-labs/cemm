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

def test_v341_boot_compat_module_removed():
    assert not Path("cemm/kernel/boot/v341.py").exists()
    assert not Path("cemm/kernel/boot/v341_validation.py").exists()
