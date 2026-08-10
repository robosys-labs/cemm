from pathlib import Path

path = Path(__file__).resolve().parents[1] / "hybrid_mvp" / "src" / "cemm_authoritative_hybrid" / "r3_cognition.py"
text = path.read_text(encoding="utf-8")
old = '''        else:\n            contribution = DecisionContribution(\n                status=DecisionStatus.UNKNOWN, action=DecisionAction.NO_OP,\n                proof_refs=(transition.transition_evaluation_ref, capability.capability_evaluation_ref),\n                blocker_refs=transition.blocker_refs,\n                policy_refs=("policy:simulation_no_effect:v2",),\n            )\n'''
new = '''        else:\n            contribution = DecisionContribution(\n                status=DecisionStatus.UNKNOWN, action=DecisionAction.NO_OP,\n                transition_preview_refs=(transition.transition_evaluation_ref,),\n                proof_refs=(transition.transition_evaluation_ref, capability.capability_evaluation_ref),\n                blocker_refs=transition.blocker_refs,\n                policy_refs=("policy:simulation_no_effect:v2",),\n            )\n'''
if text.count(old) != 1:
    raise SystemExit(f"simulation unknown branch differs from reviewed source: count={text.count(old)}")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
