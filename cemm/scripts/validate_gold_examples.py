"""Validate gold examples against packet schemas."""

import sys, os; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import json
from cemm.legacy.v3_3.packet_validator import validate_packet

with open("generated/gold_examples.jsonl") as f:
    lines = f.readlines()

task_to_packet = {
    "semantic_event_graph": "semantic_event_graph",
    "semantic_answer_graph": "semantic_answer_graph",
    "grounded_graph": "grounded_graph",
    "memory_packet": "memory_packet",
    "inference_packet": "inference_packet",
    "decision_packet": "decision_packet",
}

ok = 0
fail = 0
for i, line in enumerate(lines):
    ex = json.loads(line)
    task = ex["task_type"]
    pkt = ex["payload"]["packet"]
    schema_type = task_to_packet.get(task)
    if not schema_type:
        continue
    errs = validate_packet(pkt, schema_type)
    if errs:
        label = ex["payload"].get("label", "no-label")
        print(f"FAIL line {i} ({label}): {'; '.join(errs)}")
        fail += 1
    else:
        ok += 1

print(f"Validated: {ok} passed, {fail} failed")
if fail:
    sys.exit(1)
