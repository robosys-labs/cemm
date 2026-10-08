#!/usr/bin/env python3
"""Observe actual text -> pending learning obligation ownership without bypasses."""
from pathlib import Path
import json
import sys
import tempfile
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from cemm_authoritative_hybrid.foundation import load_foundation

CANDIDATES=(
    "yoz means hello",
    "learn yoz means hello",
    "please learn yoz means hello",
    "call hello yoz",
    "learn that yoz means hello",
    "teach yoz means hello",
    "learn happy means hello",
)

def main():
    with tempfile.TemporaryDirectory() as d:
        runtime=load_foundation(ROOT,store_path=Path(d)/"learning")
        try:
            for i,text in enumerate(CANDIDATES):
                try:
                    result=runtime.process("session:learning-probe:"+str(i),text)
                    cycle=result.cycle
                    response=cycle.response_meaning
                    plan=None if response is None else response.learning_plan
                    print(json.dumps({
                        "text":text, "status":cycle.status.value,
                        "verification":cycle.verification.status,
                        "decision_action":None if cycle.evaluation is None else cycle.evaluation.decision.action.value,
                        "mode":None if response is None else response.mode.value,
                        "plan_ref":None if plan is None else plan.plan_ref,
                        "surface":None if plan is None else plan.surface_literal,
                        "target":None if plan is None else plan.target_ref,
                        "obligation":None if response is None else response.obligation_ref,
                        "turn_expiry":None if plan is None else plan.expires_at_turn,
                    },sort_keys=True))
                except Exception as e:
                    print(json.dumps({"text":text,"error":type(e).__name__,"message":str(e)[:200]}))
        finally:
            runtime.close()
if __name__=="__main__": main()
