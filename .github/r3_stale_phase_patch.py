from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

test_path = ROOT / "hybrid_mvp" / "tests" / "test_r3_no_program_as_meaning.py"
text = test_path.read_text(encoding="utf-8")
node_id = "tests/test_r3_no_program_as_meaning.py::test_program_to_evaluate_raises_type_error"
metadata = '''    "tests/test_r3_no_program_as_meaning.py::test_program_to_evaluate_raises_type_error": {\n        "activation_phase": "R3",\n        "assertion_ref": "assertion:r3-program-to-evaluate-raises-type-error",\n        "diagnostic_role": "phase",\n        "introduced_by_task": "R3-Task-1",\n        "source_ast_sha256": "a5ca7d3465d7aa989e0285d1a64c010cb2da0d4297152132eac78693c9b6b812",\n    },\n'''
if text.count(metadata) != 1:
    raise SystemExit("obsolete R3 metadata block differs from reviewed source")
text = text.replace(metadata, "", 1)
marker = '''\n\ndef test_program_to_evaluate_raises_type_error() -> None:\n'''
if text.count(marker) != 1:
    raise SystemExit("obsolete R3 test function differs from reviewed source")
text = text.split(marker, 1)[0].rstrip() + "\n"
if "pytest." not in text:
    text = text.replace("\nimport pytest\n", "\n", 1)
test_path.write_text(text, encoding="utf-8")

config_path = ROOT / "hybrid_mvp" / "configs" / "validation_gates.json"
config = json.loads(config_path.read_text(encoding="utf-8"))
nodes = config["steps"]["r3_phase_tests"]["exact_nodes"]
if nodes.count(node_id) != 1:
    raise SystemExit("obsolete R3 node is not present exactly once in generated selector")
config["steps"]["r3_phase_tests"]["exact_nodes"] = [node for node in nodes if node != node_id]
config_path.write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")
