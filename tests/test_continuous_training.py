"""Integration test: continuous training loop end-to-end."""
import sys, os, json, tempfile
sys.path.insert(0, r'C:\dev\cemm\cemm')
from pathlib import Path
from cemm_runtime_router import (
    connect, handle_turn, _RUNTIME_CONFIG, RuntimeConfig,
    set_training_queue, emit_training_example, build_context,
    save_model, find_models, RUNTIME_SCHEMA,
)
from cemm.synthesis_verifier import verify_neural_response


def test_models_table():
    conn = connect(Path(tempfile.mktemp(suffix=".db")))
    models = find_models(conn)
    assert models == [], f"expected empty models, got {len(models)}"
    mid = save_model(conn, "operator", "test_op", registry_key="test", confidence=0.9, status="active")
    found = find_models(conn, kind="operator")
    assert len(found) == 1
    assert found[0]["registry_key"] == "test"
    conn.close()


def test_emit_training_example():
    queue_path = Path(tempfile.mktemp(suffix=".jsonl"))
    qdb = Path(tempfile.mktemp(suffix=".db"))
    conn = connect(qdb)
    set_training_queue(queue_path)
    ctx = build_context(conn, "t1")
    from cemm_runtime_router import RouteDecision
    decision = RouteDecision("answer", 0.5, "test", [], [], [])
    emit_training_example(conn, "test input", "test response", ctx, {}, {}, decision, {"strategy": "llm"})
    with queue_path.open() as f:
        lines = [json.loads(l) for l in f if l.strip()]
    assert len(lines) == 6  # 6 task types
    assert all(l["source"] == "runtime_continuous" for l in lines)
    assert all(l["task_type"] in {"context_inference", "uol_mapping", "operator_selection",
                                   "pragmatic_interpretation", "synthesis_verification",
                                   "self_state_update"} for l in lines)
    conn.close()
    queue_path.unlink()
    qdb.unlink()


def test_verifier():
    r = verify_neural_response("A good joke", "tell me a joke")
    assert r["supported"]
    assert not r["should_fallback"]
    r = verify_neural_response("hello", "hello")
    assert r["should_fallback"], "echo should fail"
    r = verify_neural_response("", "test")
    assert r["should_fallback"], "empty should fail"


def test_deploy_models_ingest():
    """Test that models can be saved and found by kind."""
    conn = connect(Path(tempfile.mktemp(suffix=".db")))
    save_model(conn, "operator", "weather_operator", registry_key="weather", status="active", confidence=0.85)
    save_model(conn, "uol_semantic", "process:greet", registry_key="process:greet", status="active", confidence=0.9)
    ops = find_models(conn, kind="operator")
    assert len(ops) == 1
    assert ops[0]["name"] == "weather_operator"
    conn.close()
