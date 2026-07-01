from __future__ import annotations

import json
import sys

# Add repo root to path
sys.path.insert(0, "C:/dev/cemm")

from cemm.cemm_trainer import PROMPTS, render_prompt


payload = json.dumps(
    {
        "context_kernel": {},
        "semantic_event_graph": {},
        "semantic_answer_graph": {},
        "memory_packet": {},
        "inference_packet": {},
        "output_text": "x",
        "selected_evidence": {},
        "self_state": {},
        "recent_event_graphs": [],
    },
    sort_keys=True,
)

missing = []
for task_type in PROMPTS:
    try:
        agent, system, user = render_prompt(task_type, payload)
        if not agent or not system or not user:
            missing.append(task_type)
    except Exception:
        missing.append(task_type)

print(missing)
