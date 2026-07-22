"""Web demo handler tests for the canonical v3.5.1 runtime."""
from __future__ import annotations


def test_web_demo_chat_handler_uses_canonical_v350_runtime_trace() -> None:
    from cemm.web_demo import handle_chat
    from cemm.v350.runtime import build_runtime

    class TestAuthorityGuard:
        def require_service_authority(self) -> None:
            return None

        def require_stage_adapter(self, **_kwargs) -> None:
            return None

    runtime = build_runtime(authority_guard=TestAuthorityGuard())
    try:
        payload = handle_chat(runtime, {
            "text": "how are you",
            "context_id": "web-demo-test",
            "include_trace": True,
        })
        assert payload["ok"] is True
        assert payload["emission_authorized"] is False
        assert payload["output_text"] is None
        assert payload["errors"] == []
        assert len(payload["trace"]["stages"]) == 23
        assert payload["trace"]["stages"][0] == "ORIENT_AND_PIN_SEMANTIC_BRAIN"
        assert payload["trace"]["stages"][-1] == "CONSOLIDATE_INVALIDATE_REPLAY_AND_FINALIZE"
        assert "CONSTRUCT_RESPONSE_CSIR" in payload["trace"]["stages"]
        assert "VERIFY_SEMANTIC_EQUIVALENCE_AND_AUTHORIZE_EMISSION" in payload["trace"]["stages"]
        assert payload["frontier_refs"]
    finally:
        runtime.close()
