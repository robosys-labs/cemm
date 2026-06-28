import pytest
from cemm.registry import Registry, RegistryEntry


class TestRegistry:
    def test_register_predicate(self):
        reg = Registry()
        entry = RegistryEntry(
            model_id="m1", canonical_key="favorite_database",
            kind="predicate", aliases=["fav_db", "preferred_db"],
        )
        reg.register(entry)
        resolved = reg.resolve_predicate("fav_db")
        assert resolved == "favorite_database"
        assert reg.resolve_predicate("favorite_database") == "favorite_database"

    def test_register_operator(self):
        reg = Registry()
        entry = RegistryEntry(
            model_id="m2", canonical_key="answer_op",
            kind="operator", required_slots=["answer_text"],
        )
        reg.register(entry)
        op = reg.resolve_operator("answer_op")
        assert op is not None
        assert "answer_text" in op.required_slots

    def test_canonicalize_predicate(self):
        reg = Registry()
        entry = RegistryEntry(
            model_id="m3", canonical_key="likes",
            kind="predicate", aliases=["enjoys", "favors"],
        )
        reg.register(entry)
        assert reg.canonicalize_predicate("LIKES") == "likes"
        assert reg.canonicalize_predicate("enjoys") == "likes"
        assert reg.canonicalize_predicate("unknown") == "unknown"

    def test_json_round_trip(self, tmp_path):
        reg = Registry()
        reg.register(RegistryEntry(
            model_id="m1", canonical_key="likes", kind="predicate", aliases=["enjoys"],
        ))
        path = tmp_path / "registry.json"
        reg.to_json(str(path))
        loaded = Registry.from_json(str(path))
        assert loaded.resolve_predicate("enjoys") == "likes"
