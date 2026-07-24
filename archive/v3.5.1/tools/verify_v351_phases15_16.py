#!/usr/bin/env python3
from __future__ import annotations

import argparse, ast, json, subprocess
from pathlib import Path

BASELINE = "d20377430213b83ba6c4f104b989ea991cb73def"

REQUIRED = (
    "cemm/v350/state/model_v351.py",
    "cemm/v350/state/algebra_v351.py",
    "cemm/v350/state/entitlement_v351.py",
    "cemm/v350/state/transition_v351.py",
    "cemm/v350/state/capability_v351.py",
    "cemm/v350/state/codec_v351.py",
    "cemm/v350/causal/model_v351.py",
    "cemm/v350/causal/authority_v351.py",
    "cemm/v350/causal/authority_projection_v351.py",
    "cemm/v350/causal/engine_v351.py",
    "cemm/v350/causal/explanation_v351.py",
    "cemm/v350/causal/codec_v351.py",
    "cemm/v350/causal/commit_v351.py",
    "cemm/v350/causal/query_v351.py",
    "cemm/v350/causal/response_v351.py",
    "cemm/v350/causal/impact_v351.py",
    "cemm/v350/causal/goals_v351.py",
    "cemm/v350/causal/research_v351.py",
    "cemm/v350/causal/planning_v351.py",
    "cemm/v350/causal/runtime_v351.py",
)

FORBIDDEN_PATTERNS = (
    "if token ==", "if word ==", "if phrase ==", "event_name ==", "subject_role",
    "object_role", "zorb", "because the user said", "effect_store.base_store",
    "from ..uol", "from cemm.v347", "import cemm.v347",
)


def fail(msg):
    print("FAIL:", msg)
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo", nargs="?", default=None)
    ap.add_argument("--require-baseline", action="store_true")
    args = ap.parse_args()
    repo = (Path(args.repo).resolve() if args.repo else Path(__file__).resolve().parents[1])
    ok = True

    if args.require_baseline:
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
        ok &= head == BASELINE or fail(f"expected pre-apply baseline {BASELINE}, got {head}")

    for rel in REQUIRED:
        p = repo / rel
        if not p.is_file():
            ok &= fail(f"missing {rel}")
            continue
        try:
            ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
        except SyntaxError as exc:
            ok &= fail(f"syntax {rel}: {exc}")

    corpus = "\n".join(
        (repo / rel).read_text(encoding="utf-8")
        for rel in REQUIRED if (repo / rel).is_file()
    ).casefold()
    for pattern in FORBIDDEN_PATTERNS:
        if pattern.casefold() in corpus:
            ok &= fail(f"forbidden static shortcut found: {pattern}")

    runtime_text = (repo / "cemm/v350/causal/runtime_v351.py").read_text(encoding="utf-8").casefold()
    commit_text = (repo / "cemm/v350/causal/commit_v351.py").read_text(encoding="utf-8").casefold()
    explain_text = (repo / "cemm/v350/causal/explanation_v351.py").read_text(encoding="utf-8").casefold()
    state_text = (repo / "cemm/v350/state/model_v351.py").read_text(encoding="utf-8").casefold()
    transition_text = (repo / "cemm/v350/state/transition_v351.py").read_text(encoding="utf-8").casefold()
    entitlement_text = (repo / "cemm/v350/state/entitlement_v351.py").read_text(encoding="utf-8").casefold()
    authority_projection_text = (repo / "cemm/v350/causal/authority_projection_v351.py").read_text(encoding="utf-8").casefold()
    impact_text = (repo / "cemm/v350/causal/impact_v351.py").read_text(encoding="utf-8").casefold()
    goals_text = (repo / "cemm/v350/causal/goals_v351.py").read_text(encoding="utf-8").casefold()
    engine_text = (repo / "cemm/v350/causal/engine_v351.py").read_text(encoding="utf-8").casefold()
    package_text = (repo / "cemm/v350/state/__init__.py").read_text(encoding="utf-8").casefold()
    apply_text = (repo / "apply_phases15_16.py").read_text(encoding="utf-8").casefold()

    checks = {
        "8 state domains": all(x in corpus for x in (
            "categorical", "ordered", "continuous", "vector", "relational", "set", "process", "probabilistic"
        )),
        "typed probability support": "class probabilitypointv351" in state_text and "support_value:" in state_text and "probability support must be a typed state-value" in corpus,
        "explicit transition use authority": "authorized_use_operations" in state_text and "use_authority_explicit" in state_text and "useoperation.transition" in state_text,
        "do intervention cut": "cut_target_keys" in corpus and "intervention-cut" in corpus,
        "typed counterfactual abduction": "exogenousassumptionv351" in corpus and "counterfactual-abduction-unresolved" in corpus,
        "probability unresolved mass": "unresolved_probability_mass" in corpus,
        "competing writes fail closed": "aggregation_contract_pin" in corpus and "aggregation_selection_evaluators" in corpus,
        "exact stochastic independence": "stochastic_independence_pin" in corpus,
        "causal proof reuse": "causallearningevidencev351" in corpus and "causalproofv351" in corpus,
        "durable proof commit": "recordkind.transition_proof" in commit_text and "causal_transition_proof" in commit_text,
        "directional causal query": "extract_effect_of" in explain_text and "query_kind == \"effect_of\"" in explain_text,
        "simulation context matching": "item.intervention_ref == request.intervention.context_ref" in runtime_text,
        "nonactual impacts isolated": "causal_simulated_impact_vectors" in runtime_text and "contextsemantics.actual" in runtime_text,
        "planning remains pre-authorization": "authorized_operations" in runtime_text and "effect_authorizations" in runtime_text,
        "state identity excludes evidence lineage": "def semantic_document" in state_text and "semantic_document()" in state_text,
        "causal depth distinct from time horizon": "causal_depth" in corpus and "maximum_time_step" in corpus,
        "structural intervention cuts persist across time": "structural_key" in corpus and "cut_target_keys" in corpus,
        "factual queries never fall back to nonactual simulations": "no-matching-simulation-context" in runtime_text and "if simulation is none and candidates" not in runtime_text,
        "ambiguous causal proofs stay partial": "multiple-warranted-proof-paths" in explain_text,
        "query impact goal plan use axes are exact-authorized": all(x in corpus for x in (
            'operation="query"', 'operation="impact"', 'operation="response_policy"', 'operation="plan"'
        )),
        "impact role ambiguity is not dictionary overwrite": "ambiguous-root-role" in runtime_text,
        "utility must be finite": "utility evaluator must return a finite value" in corpus,
        "relational state roles are explicit": "class relationstaterolebindingv351" in state_text and "relation_role_pins" in state_text and "relation_bindings" in state_text,
        "minimum confidence budget is enforced": "minimum-confidence-pruned" in corpus and "minimum_confidence" in corpus,
        "why-not compares factual and contrast simulations": "def answer_why_not" in explain_text and "contrast_simulation_ref" in explain_text and "requires-factual-and-contrast-simulations" in explain_text,
        "causal proof steps preserve exact role bindings": "role_bindings: tuple[participantrolebinding" in corpus and "step.role_bindings" in corpus,
        "planner checks per-action exact plan authority": "action-exact-plan-use-authority-required" in runtime_text and "action.action_schema_pin" in runtime_text,
        "planner exact utility policy is runtime-wired": "utility_policy_pin=self.services.causal_utility_policy_pin" in apply_text,
        "stage0 projects only promoted state causal authority": "project_state_causal_authority(self.store, semantic_authority)" in apply_text and "_active_rich_records" in authority_projection_text,
        "authority projection excludes invalidated revisions": "store.is_invalidated" in authority_projection_text and 'getattr(payload, "executable", false)' in authority_projection_text,
        "authority projection is generation-pinned": "authority generation changed during state/causal authority projection" in authority_projection_text and "projection generation differs from pinned cycle" in authority_projection_text,
        "mechanism semantic identity excludes operational scope": '"context_scopes"' not in state_text[state_text.find("def authority_pin"):state_text.find("@property\n    def executable", state_text.find("def authority_pin"))],
        "unknown defeaters fail closed": "defeater-branch-required" in transition_text and "unknown possible defeater under block" in transition_text,
        "world isolation copies only declared source context": "source_context_ref" in engine_text and 'key.context_ref not in {"global", source_context_ref}' in engine_text,
        "unresolved impacts cannot create ordinary goals": "or not impact.resolved" in goals_text and "resolved=branch.resolved" in impact_text,
        "rich state assignment document is identity checked": "rich state assignment content identity differs from value_document" in entitlement_text and "rich categorical assignment ref/revision differs" in entitlement_text,
        "stage13 independently revalidates transition use": 'require_exact_use(' in commit_text and 'operation="transition"' in commit_text and "semantic_authority_snapshot_v351" in commit_text,
        "actual commit context cannot be smuggled": "item.context_ref == cycle.context_ref" in commit_text and "delta.context_ref != cycle.context_ref" in commit_text,
        "state package import closure has no misplaced causal projection": "authority_projection_v351" not in package_text,
        "isolated behavioral verifier is shipped": (repo / "tools/run_isolated_v351_phases15_16_checks.py").is_file(),
    }
    for label, value in checks.items():
        if not value:
            ok &= fail(label)

    print(json.dumps({"baseline": BASELINE, "checks": checks, "ok": bool(ok)}, indent=2, sort_keys=True))
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
