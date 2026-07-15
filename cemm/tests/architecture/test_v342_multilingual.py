from pathlib import Path

def test_language_packs_share_semantic_keys():
    from cemm.language.pack import LanguagePackRegistry
    registry = LanguagePackRegistry()
    registry.load_directory(Path("cemm/data/languages"))
    assert {"en", "fr"} <= set(registry.language_tags)
    assert registry.require("en").lexical_entry("greet")
    assert registry.require("fr").lexical_entry("greet")
