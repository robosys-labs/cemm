"""
Manual integration test for CEMM process_input.
Uses the real process_input from __main__.py for accurate results.
"""
from __future__ import annotations

import sys
import os
import time
import traceback

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "cemm")))

from cemm.store.store import Store
from cemm.registry import Registry
from cemm.kernel.pipeline import Pipeline
from cemm.learning.online import OnlineLearner
from cemm.learning.inductor import Inductor
from cemm.kernel.recursive_loop import RecursiveLoop
from cemm.operators.registry import OperatorRegistry
from cemm.operators.answer import AnswerOperator
from cemm.operators.abstain import AbstainOperator
from cemm.operators.ask import AskOperator
from cemm.operators.remember import RememberOperator
from cemm.operators.reflect import ReflectOperator
from cemm.operators.update_claim import UpdateClaimOperator
from cemm.operators.create_model import CreateModelOperator
from cemm.operators.retrieve_op import RetrieveOperator
from cemm.operators.simulate import SimulateOperator
from cemm.operators.synthesize import SynthesizeOperator
from cemm.operators.call_tool import CallToolOperator
from cemm.__main__ import process_input, seed_registry, seed_self_state


def setup():
    store = Store(":memory:")
    registry = Registry()
    op_registry = OperatorRegistry()
    pipeline = Pipeline(store, registry)
    online_learner = OnlineLearner(store.source_trust, store.self_store, store.claims, store.models)
    inductor = Inductor(store, registry=registry)
    recursive_loop = RecursiveLoop(pipeline, store, online_learner, inductor)

    seed_registry(registry)
    seed_self_state(store)

    for op in [
        AnswerOperator(), AbstainOperator(), AskOperator(), RememberOperator(),
        ReflectOperator(), UpdateClaimOperator(), CreateModelOperator(),
        RetrieveOperator(), SimulateOperator(), SynthesizeOperator(), CallToolOperator(),
    ]:
        op_registry.register(op)

    return store, registry, op_registry, pipeline, online_learner, recursive_loop


def run_tests():
    store, registry, op_registry, pipeline, online_learner, recursive_loop = setup()
    context_id = "test_session"
    turn_count = [0]

    test_cases = [
        ("hello", "Greeting"),
        ("hi there", "Greeting variant"),
        ("good morning", "Time-based greeting"),
        ("remember I like coffee", "Remember preference"),
        ("save my favorite database is Postgres", "Save with long text"),
        ("rember I like tea", "Misspelled 'remember'"),
        ("rember that I use Pyton", "Misspelled 'remember' and 'Python'"),
        ("What is my favorite database?", "Recall stored fact"),
        ("what do I like?", "Question about preferences"),
        ("what is my favrite database", "Misspelled 'favorite' in recall"),
        ("whats the wether?", "Misspelled 'weather'"),
        ("can you remembr things?", "Misspelled 'remember' in question"),
        ("I thnk this is cool", "Misspelled 'think'"),
        ("reflect on your state", "Explicit reflect"),
        ("think about what you know", "Think command"),
        ("retrieve claims about user", "Explicit retrieve"),
        ("search for coffee", "Search command"),
        ("hi", "Very short input"),
        ("ok", "Acknowledgment"),
        ("?", "Just a question mark"),
        ("", "Empty input"),
        ("   ", "Whitespace only"),
        ("rain causes flooding", "Causal statement"),
        ("I exercise because I want to be healthy", "Because clause"),
        ("exit", "Exit command"),
    ]

    results = []
    for text, desc in test_cases:
        try:
            output = process_input(
                text, store, registry, op_registry, pipeline,
                online_learner, recursive_loop, context_id, turn_count,
            )
            results.append({"input": text, "desc": desc, "output": output, "error": None})
        except Exception as e:
            results.append({"input": text, "desc": desc, "output": "", "error": str(e)})

    print("\n" + "=" * 100)
    print("CEMM MANUAL INTEGRATION TEST (via process_input)")
    print("=" * 100)

    gaps = []
    for r in results:
        status = "PASS" if not r["error"] else "FAIL"
        print(f"\n[{status}] {r['desc']}")
        print(f"  Input:   {repr(r['input'][:60])}")
        print(f"  Output:  {repr(r['output'][:70])}")
        if r["error"]:
            print(f"  ERROR:   {r['error'][:200]}")
            gaps.append(f"BUG: {r['desc']} - {r['error']}")
        if "insufficient" in r["output"].lower() and r["input"].strip():
            if any(m in r["desc"].lower() for m in ["misspell", "typo"]):
                gaps.append(f"GAP: {r['desc']} - Abstained on misspelled input")
        if "remember" in r["desc"].lower() and "misspell" in r["desc"].lower():
            if "remembered" not in r["output"].lower() and "rember" not in r["output"].lower():
                gaps.append(f"GAP: {r['desc']} - Not recognized as remember command")

    # Multi-turn recall
    print("\n" + "=" * 100)
    print("MULTI-TURN RECALL TEST")
    print("=" * 100)

    store2, reg2, ops2, pipe2, ol2, rl2 = setup()
    ctx2 = "mt_session"
    tc2 = [0]

    for text, desc in [
        ("remember I like coffee", "Store preference"),
        ("what do I like?", "Recall preference"),
        ("whaat do I likke?", "Recall with misspellings"),
    ]:
        output = process_input(text, store2, reg2, ops2, pipe2, ol2, rl2, ctx2, tc2)
        print(f"  {desc}: {repr(text)} -> {repr(output[:70])}")
        if "recall" in desc.lower() and "insufficient" in output.lower():
            gaps.append(f"GAP: Multi-turn {desc} - Could not recall stored fact")

    print("\n" + "=" * 100)
    print("IDENTIFIED GAPS / BUGS")
    print("=" * 100)

    if gaps:
        seen = set()
        for g in gaps:
            if g not in seen:
                seen.add(g)
                print(f"  {g}")
    else:
        print("  No gaps identified!")

    print(f"\n  Total: {len(results)} test cases, {len(set(gaps))} unique gaps")


if __name__ == "__main__":
    run_tests()
