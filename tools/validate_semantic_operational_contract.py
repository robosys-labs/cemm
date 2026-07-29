#!/usr/bin/env python3
"""Behavioral and structural release gate for the CEMM semantic runtime.

The gate intentionally avoids implementation-spelling assertions.  It validates
serialized ABIs, recomputes generated artifacts, executes the critical semantic
contracts, and inspects Python ASTs for forbidden second-authority paths.
"""
from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterable, Mapping

try:
    from tools.authority_ownership import AuthorityOwnershipError, validate_repository_authority
except ImportError:
    from authority_ownership import AuthorityOwnershipError, validate_repository_authority

ABI_VERSION = 7
BASE_OWNED_REFS = frozenset({
    "value:unknown",
    "dim:runtime_process_support",
    "dim:semantic_runtime_support",
    "dim:language_realizer_support",
    "dim:critical_blocker_count",
    "rel:subtype_of",
    "rel:value_of_dimension",
})
CONVERSATION_OWNED_REFS = frozenset({
    "rel:knows",
    "resource:inference_engine",
    "resource:designation_index",
    "resource:semantic_store",
    "resource:common_ground",
})
REJECTED_REFS = frozenset({
    "dim:operational_condition",
    "dim:runtime_support",
    "value:operating_normally",
    "value:degraded",
    "rel:attributed_property",
    "concept:surface_pattern_matching",
})
TRANSIENT_SELF_DIMENSIONS = frozenset({
    "dim:availability",
    "dim:communication_status",
    "dim:emotional_state",
    "dim:runtime_process_support",
    "dim:semantic_runtime_support",
    "dim:language_realizer_support",
    "dim:critical_blocker_count",
    "dim:operational_condition",
    "dim:runtime_support",
})
CANONICAL_RESOURCES = frozenset({
    "resource:runtime_process",
    "resource:semantic_runtime",
    "resource:language_realizer",
    "resource:output_channel",
    "resource:inference_engine",
    "resource:designation_index",
    "resource:semantic_store",
    "resource:common_ground",
})
REQUIRED_FAMILIES = frozenset({
    "attributed_open_predication_claim",
    "designation_claim",
    "designation_confirmation",
    "designation_query",
    "meaning_query",
    "contextual_meaning_query",
    "operational_condition_query",
    "relation_surface_query",
    "surface_choice_explanation_query",
    "type_query",
    "capability_inventory_query",
    "definition_designation_claim",
    "designation_learning_answer",
    "generic_state_value_predication",
    "generic_type_predication",
    "semantic_discourse_reaction",
})
QUERY_RESPONSE_ACTIONS = frozenset({
    "answer_bindings",
    "report_multiple_bindings",
    "confirm",
    "deny",
    "report_conflict",
    "report_target_uncertainty",
    "report_operational_condition",
})


class ContractError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractError(message)


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def purge_cemm_modules() -> None:
    for name in tuple(sys.modules):
        if name == "cemm" or name.startswith("cemm.") or name.startswith("tools.generate_en_form_pack") or name.startswith("tools.migrate_semantic_operational_assets"):
            sys.modules.pop(name, None)


def import_repo(repo: Path) -> None:
    purge_cemm_modules()
    value = str(repo)
    if value in sys.path:
        sys.path.remove(value)
    sys.path.insert(0, value)


def validate_authority(repo: Path) -> dict[str, Any]:
    try:
        index = validate_repository_authority(repo)
    except (AuthorityOwnershipError, ValueError) as exc:
        raise ContractError(f"authority graph invalid: {exc}") from exc
    base = str((repo / "cemm/data/base.json").resolve())
    conversation_path = repo / "cemm/data/conversation_foundation.json"
    conversation = str(conversation_path.resolve())
    for ref in BASE_OWNED_REFS:
        require(index.atom_owner.get(ref) == base, f"base ownership lost for {ref}")
        require(ref not in index.document_atoms.get(conversation, ()), f"conversation redefines base atom {ref}")
    for ref in CONVERSATION_OWNED_REFS:
        require(index.atom_owner.get(ref) == conversation, f"conversation ownership lost for {ref}")
    require(not REJECTED_REFS.intersection(index.atom_owner), "rejected first-bundle atoms remain")
    conversation_data = load_json(conversation_path)
    migration = dict(conversation_data.get("semantic_operational_migration", {}) or {})
    require(migration.get("authority_change") == "removal_only", "authority migration is not removal-only")
    require(migration.get("added_atom_count") == 0, "authority migration added atoms")
    require(migration.get("modified_atom_count") == 0, "authority migration modified atoms")
    for path in sorted((repo / "cemm/data").glob("*.json")):
        for fact in load_json(path).get("facts", ()):
            args = dict(fact.get("args", {}) or {})
            timeless = (
                fact.get("operator") == "op:state"
                and args.get("role:subject") == "participant:system"
                and args.get("role:dimension") in TRANSIENT_SELF_DIMENSIONS
                and fact.get("authority_status", "reviewed") == "reviewed"
            )
            require(not timeless, f"timeless reviewed operational fact remains in {path.name}: {fact.get('fact_ref')}")
    return {"atom_count": len(index.atom_owner), "document_count": len(index.document_atoms)}


def validate_form_artifact(repo: Path) -> dict[str, Any]:
    import_repo(repo)
    from cemm.form_algebra import AtomicSchemaMatcher
    from cemm.semantic_coverage import COVERAGE_ABI_VERSION
    try:
        from tools.generate_en_form_pack_v7 import build_pack
    except ImportError:
        from generate_en_form_pack_v7 import build_pack

    seed_path = repo / "cemm/training/en_form_schema_seed.json"
    pack_path = repo / "cemm/form_packs/en.json"
    pack = load_json(pack_path)
    require(COVERAGE_ABI_VERSION == ABI_VERSION, "runtime coverage ABI mismatch")
    require(pack.get("feature_algebra_version") == ABI_VERSION, "form artifact ABI mismatch")
    material = {key: value for key, value in pack.items() if key != "pack_hash"}
    require(pack.get("pack_hash") == hashlib.sha256(canonical(material).encode()).hexdigest(), "form-pack hash mismatch")
    schemas = tuple(pack.get("schemas", ()))
    AtomicSchemaMatcher(schemas, max_matches=128)
    families = {str(item.get("family")) for item in schemas}
    require(families == REQUIRED_FAMILIES, f"form families differ: missing={sorted(REQUIRED_FAMILIES-families)}, extra={sorted(families-REQUIRED_FAMILIES)}")
    require(not pack.get("constructions"), "phrase constructions remain active")
    computed = build_pack(seed_path)
    require(computed == pack, "checked-in form pack is not the deterministic generator output")
    receipt = dict(pack.get("training_receipt", {}) or {})
    require(receipt.get("receipt_version") == ABI_VERSION, "training receipt ABI mismatch")
    require(receipt.get("feature_algebra_version") == ABI_VERSION, "training receipt algebra mismatch")
    require(receipt.get("example_count") == len(receipt.get("positive_replay", ())), "positive replay receipt count mismatch")
    require(receipt.get("family_count") == len(schemas), "family receipt count mismatch")
    require(receipt.get("annotated_replay_coverage") == 1.0, "positive replay is incomplete")
    require(receipt.get("surface_matcher_key_count") == 0, "surface matcher conditions remain")
    require(receipt.get("regex_condition_count") == 0, "regex semantic conditions remain")
    require(all(row.get("blocked") for row in receipt.get("critical_slot_mutations", ())), "a critical-slot mutation remains executable")
    require(all(row.get("blocked") for row in receipt.get("negative_probes", ())), "a reviewed negative probe remains executable")
    require(
        receipt.get("graph_matcher") is True,
        "form pack was not verified by the v7 recursive graph matcher",
    )
    require(
        receipt.get("total_order_matcher") is False,
        "form pack still claims total-order matcher",
    )
    require(
        all(
            row.get("intended_family") in row.get("executable_families", ())
            for row in receipt.get("cross_family_collision_matrix", ())
        ),
        "cross-family collision receipt failed: intended family missing",
    )
    require(
        all(
            row.get("mode") == "reviewed_singleton"
            or (
                row.get("mode") == "leave_one_out"
                and row.get("executable_match_count") >= 1
            )
            or row.get("mode") == "leave_one_out_partial"
            or row.get("mode") == "leave_one_out_full_schema"
            for row in receipt.get("family_holdouts", ())
        ),
        "family holdout receipt is incomplete or nonunique",
    )
    return {"pack_hash": pack["pack_hash"], "schema_count": len(schemas), "example_count": receipt["example_count"]}


def validate_migration_idempotence(repo: Path) -> dict[str, Any]:
    import_repo(repo)
    try:
        from tools.migrate_semantic_operational_assets import migrate_language_pack, migrate_seed
    except ImportError:
        from migrate_semantic_operational_assets import migrate_language_pack, migrate_seed
    with tempfile.TemporaryDirectory(prefix="cemm-migration-validation-") as tmp:
        root = Path(tmp)
        conversation = root / "conversation_foundation.json"
        language = root / "en.json"
        form = root / "form.json"
        shutil.copy2(repo / "cemm/data/conversation_foundation.json", conversation)
        shutil.copy2(repo / "cemm/language_packs/en.json", language)
        shutil.copy2(repo / "cemm/form_packs/en.json", form)
        before_atoms = {item["ref"]: canonical(item) for item in load_json(conversation).get("atoms", ())}
        migrate_seed(conversation)
        migrate_language_pack(language, form)
        first_seed = conversation.read_bytes()
        first_language = language.read_bytes()
        migrate_seed(conversation)
        migrate_language_pack(language, form)
        require(conversation.read_bytes() == first_seed, "seed migration is not byte-idempotent")
        require(language.read_bytes() == first_language, "language migration is not byte-idempotent")
        after_atoms = {item["ref"]: canonical(item) for item in load_json(conversation).get("atoms", ())}
        require(not (set(after_atoms) - set(before_atoms)), "migration added authority atoms")
        require(all(after_atoms[ref] == before_atoms[ref] for ref in after_atoms), "migration modified a surviving atom")
    return {"seed_byte_idempotent": True, "language_byte_idempotent": True}


def parse_sources(repo: Path) -> dict[str, ast.AST]:
    output: dict[str, ast.AST] = {}
    for root_name in ("cemm", "tools", "tests"):
        root = repo / root_name
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            relative = path.relative_to(repo).as_posix()
            try:
                output[relative] = ast.parse(path.read_text(encoding="utf-8"), filename=relative)
            except SyntaxError as exc:
                raise ContractError(f"syntax error in {relative}: {exc}") from exc
    return output


def function_node(tree: ast.AST, class_name: str | None, name: str) -> ast.FunctionDef | ast.AsyncFunctionDef:
    scope: Iterable[ast.AST] = ast.walk(tree)
    if class_name:
        cls = next((node for node in ast.walk(tree) if isinstance(node, ast.ClassDef) and node.name == class_name), None)
        require(cls is not None, f"missing class {class_name}")
        scope = cls.body
    node = next((item for item in scope if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == name), None)
    require(node is not None, f"missing function {class_name + '.' if class_name else ''}{name}")
    return node


def called_attributes(node: ast.AST) -> list[tuple[str, ast.Call]]:
    output = []
    for item in ast.walk(node):
        if isinstance(item, ast.Call) and isinstance(item.func, ast.Attribute):
            output.append((item.func.attr, item))
    return output


def string_constants(node: ast.AST) -> set[str]:
    return {item.value for item in ast.walk(node) if isinstance(item, ast.Constant) and isinstance(item.value, str)}


def validate_source_structure(repo: Path) -> dict[str, Any]:
    trees = parse_sources(repo)
    required = {
        "cemm/interpreter.py", "cemm/realizer.py", "cemm/retrieval.py", "cemm/runtime.py",
        "cemm/cognition.py", "cemm/compiler.py", "cemm/transitions.py", "cemm/semantic_coverage.py",
        "cemm/form_algebra.py", "cemm/forms.py", "cemm/settler.py", "cemm/response.py",
        "cemm/operational.py",
        "tools/apply_semantic_operational_source_rewrite.py",
    }
    require(required.issubset(trees), f"required implementation sources missing: {sorted(required-set(trees))}")

    interpreter = trees["cemm/interpreter.py"]
    imports = {alias.name for node in ast.walk(interpreter) if isinstance(node, (ast.Import, ast.ImportFrom)) for alias in node.names}
    class_names = {node.name for node in ast.walk(interpreter) if isinstance(node, ast.ClassDef)}
    require("torch" not in imports and "re" not in imports, "interpreter retains neural/regex semantic authority")
    require("StructuredSemanticCodec" not in class_names, "interpreter retains alternate semantic codec")
    compose = function_node(interpreter, "Interpreter", "compose")
    require(not any(isinstance(node, ast.ExceptHandler) and isinstance(node.type, ast.Name) and node.type.id in {"Exception", "BaseException"} for node in ast.walk(compose)), "Interpreter.compose hides integrity failures with a broad exception")
    compose_source = ast.unparse(compose)
    require("require_coverage=True" in compose_source.replace(" ", ""), "Interpreter.compose relaxed complete coverage")
    require("self.codec" not in compose_source, "diagnostic codec re-entered semantic compose")
    codec_property = function_node(interpreter, "Interpreter", "codec")
    require(any(
        isinstance(item, ast.Name) and item.id == "property"
        for decorator in codec_property.decorator_list
        for item in ast.walk(decorator)
    ), "legacy codec compatibility surface is not diagnostic-only property")
    require(function_node(interpreter, "Interpreter", "designation_index_status") is not None, "interpreter lacks public designation-index status")
    interpreter_resources = function_node(interpreter, "Interpreter", "operational_resources_for")
    interpreter_resource_source = ast.unparse(interpreter_resources)
    require("resource:designation_index" in interpreter_resource_source, "real interpreter does not declare designation-index use")
    require("unsupported interpreter operation" in interpreter_resource_source, "unknown interpreter operations do not fail closed")

    forms = trees.get("cemm/forms.py")
    require(forms is not None, "forms implementation is missing")
    name_like = function_node(forms, "HeuristicProperNameProvider", "_name_like")
    require("protected_forms" in ast.unparse(name_like), "named-entity proposal can shadow reviewed structural forms")
    resolve = function_node(forms, "FormProcessor", "resolve")
    resolve_source = ast.unparse(resolve)
    require("hypotheses_by_normalization" in resolve_source, "normalization hypotheses are globally starved before representation")
    require("structural_rank" in resolve_source, "structural lexical hypotheses can be crowded out by populated designation evidence")
    require("participant_anchors" in resolve_source, "participant-reference hypotheses lack ranking protection")

    settler = trees["cemm/settler.py"]
    settle = function_node(settler, "SemanticSettler", "settle")
    semantic_signature = function_node(settler, "SemanticSettler", "_semantic_signature")
    require("by_signature" in ast.unparse(settle), "provenance-equivalent interpretations split posterior mass")
    provenance_assignment = next(
        (
            node for node in ast.walk(settler)
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name)
                and target.id == "_PROVENANCE_ONLY_PACKET_QUALIFIERS"
                for target in node.targets
            )
        ),
        None,
    )
    require(provenance_assignment is not None, "settler lacks an explicit provenance-only qualifier contract")
    provenance_source = ast.unparse(provenance_assignment)
    require("construction_schema_ref" in provenance_source, "settler semantic signature does not remove construction provenance")
    require("query_kind" not in provenance_source, "settler strips meaning-bearing query qualifiers")
    require("qualifiers.pop" in ast.unparse(semantic_signature), "settler does not normalize provenance before semantic comparison")

    response_builder = trees["cemm/response.py"]
    response_build = function_node(response_builder, "ResponseBuilder", "build")
    require(
        "designation_learning" in string_constants(response_build)
        or "learning_plan_ref" in string_constants(response_build)
        or "learning_contract_ref" in string_constants(response_build),
        "contextual designation learning is not response-licensed",
    )

    operational = trees["cemm/operational.py"]
    declared_resources = function_node(operational, None, "declared_operation_resources")
    declared_source = ast.unparse(declared_resources)
    require("operational_resources_for" in declared_source, "operational use is not component-declared")
    require("CANONICAL_RUNTIME_RESOURCES" in declared_source, "declared operational use is not ABI-bounded")
    require("baseline" in declared_source, "declared operational use loses mandatory stage resources")

    realizer = trees["cemm/realizer.py"]
    response_fn = function_node(realizer, "PointerRealizer", "response")
    response_calls = called_attributes(response_fn)
    require(all(name not in {"pointerize_fact", "facts_mentioning"} for name, _ in response_calls), "response realization can fall back to supporting facts")
    require("torch" not in {alias.name for node in ast.walk(realizer) if isinstance(node, (ast.Import, ast.ImportFrom)) for alias in node.names}, "realizer retains neural runtime authority")

    retrieval = trees["cemm/retrieval.py"]
    retrieve_fn = function_node(retrieval, "SemanticRetriever", "retrieve")
    require(all(name != "facts_mentioning" for name, _ in called_attributes(retrieve_fn)), "retrieval broadens through facts_mentioning")

    runtime = trees["cemm/runtime.py"]
    runtime_process = function_node(runtime, "Runtime", "process")
    runtime_init = function_node(runtime, "Runtime", "__init__")
    runtime_bind = function_node(runtime, "Runtime", "_bind_authority")
    runtime_cycle = function_node(runtime, "Runtime", "_new_cycle")
    runtime_require = function_node(runtime, "Runtime", "_require_resources")
    runtime_interpreter_resources = function_node(runtime, "Runtime", "_interpreter_resources")
    del runtime_require
    require(not any(isinstance(node, ast.ExceptHandler) and isinstance(node.type, ast.Name) and node.type.id in {"Exception", "BaseException"} for node in ast.walk(runtime_process)), "Runtime.process hides semantic integrity failures with a broad exception")
    constants = string_constants(runtime)
    require(CANONICAL_RESOURCES.issubset(constants), "runtime does not register every canonical resource")
    require("operational_usage_ledger" in string_constants(runtime_cycle), "cycle does not own an operational use ledger")
    require(any(name == "consume_after_commit" for name, _ in called_attributes(runtime_process)), "pending learning is not commit-bound")
    realizer_calls = [call for name, call in called_attributes(runtime_process) if name == "response"]
    require(realizer_calls and all(len(call.args) >= 2 for call in realizer_calls), "runtime realization lacks an output participant frame")
    require(any(name == "validate_resources" for name, _ in called_attributes(runtime_bind)), "runtime service registry is not startup-validated")
    require(any(isinstance(node, ast.Assign) and any(isinstance(target, ast.Attribute) and target.attr == "dialogue_state" for target in node.targets) for node in ast.walk(runtime_init)), "runtime dialogue state is absent")
    require(sum(1 for name, _ in called_attributes(runtime_process) if name == "_require_resources") >= 6, "runtime stages lack operational use receipts")
    interpreter_resource_source = ast.unparse(runtime_interpreter_resources)
    require("CANONICAL_RUNTIME_RESOURCES" in interpreter_resource_source, "interpreter resource declarations bypass the runtime ABI")
    process_calls = called_attributes(runtime_process)
    require(any(
        name == "_require_resources"
        and "Stage.ENCODE" in ast.unparse(call)
        and any(
            isinstance(inner, ast.Call)
            and isinstance(inner.func, ast.Attribute)
            and inner.func.attr == "_interpreter_resources"
            and len(inner.args) == 1
            and isinstance(inner.args[0], ast.Constant)
            and inner.args[0].value == "observe"
            for inner in ast.walk(call)
        )
        for name, call in process_calls
    ), "Stage.ENCODE does not gate the interpreter's declared resource use")
    require(not any(
        isinstance(node, ast.Tuple)
        and tuple(
            item.value for item in node.elts
            if isinstance(item, ast.Constant) and isinstance(item.value, str)
        ) == ("resource:semantic_runtime", "resource:designation_index")
        for node in ast.walk(runtime_process)
    ), "Stage.ENCODE hardcodes a private interpreter dependency")
    runtime_source = (repo / "cemm/runtime.py").read_text(encoding="utf-8")
    require("SELECT count(*) FROM designation_index" in runtime_source, "designation-index probe cannot prove the persistent store index")
    require("designation_index_store_handle_unavailable" in runtime_source, "designation-index probe does not preserve unknown evidence")
    goal_calls = [
        call for name, call in process_calls
        if name == "candidates"
        and isinstance(call.func.value, ast.Attribute)
        and call.func.value.attr == "goal_arbiter"
    ]
    require(
        len(goal_calls) == 1
        and any(keyword.arg == "learning_probe" for keyword in goal_calls[0].keywords),
        "runtime does not connect unanswered exact queries to learning goals",
    )
    adapter_calls = [
        call for name, call in process_calls
        if name == "execute"
        and isinstance(call.func.value, ast.Attribute)
        and call.func.value.attr == "adapters"
    ]
    require(len(adapter_calls) == 1, "runtime has an unexpected adapter execution boundary")
    adapter_line = adapter_calls[0].lineno
    require(
        any(
            name == "_require_resources"
            and call.lineno < adapter_line
            and "Stage.PLAN_EXECUTE" in ast.unparse(call)
            and "resource:semantic_store" in ast.unparse(call)
            for name, call in process_calls
        ),
        "adapter execution precedes semantic-store/effect-journal resource gating",
    )

    cognition = trees["cemm/cognition.py"]
    from_dict = function_node(cognition, "QueryStructure", "from_dict")
    require("raw_projection" in {node.id for node in ast.walk(from_dict) if isinstance(node, ast.Name)}, "QueryStructure cannot distinguish absent from explicit empty projection")
    compiler = trees["cemm/compiler.py"]
    query_fn = function_node(compiler, "ExactStructuredCompiler", "_query")
    require("raw_projection" in {node.id for node in ast.walk(query_fn) if isinstance(node, ast.Name)}, "compiler cannot preserve explicit empty projection")
    transitions = trees["cemm/transitions.py"]
    require("simulated" in string_constants(transitions), "transition preview lacks simulated epistemic mode")

    rewrite = trees["tools/apply_semantic_operational_source_rewrite.py"]
    require(function_node(rewrite, None, "validate_postconditions") is not None, "source rewrite lacks AST postconditions")
    require(function_node(rewrite, None, "validate_rewrite_seals") is not None, "source rewrite lacks seal validation")
    require(function_node(rewrite, None, "prove_idempotence_on_isolated_copy") is not None, "source rewrite lacks isolated idempotence proof")
    rewrite_constants = string_constants(rewrite)
    require("3.1.3" in rewrite_constants, "source rewrite protocol is not v3.1.3")
    main_fn = function_node(rewrite, None, "main")
    check_branches = [
        node for node in ast.walk(main_fn)
        if isinstance(node, ast.If) and "args.check" in ast.unparse(node.test)
    ]
    require(len(check_branches) == 1, "source rewrite check branch is missing or ambiguous")
    check_calls = {
        item.func.id if isinstance(item.func, ast.Name) else item.func.attr
        for item in ast.walk(check_branches[0])
        if isinstance(item, ast.Call)
        and isinstance(item.func, (ast.Name, ast.Attribute))
    }
    require(
        {"validate_rewrite_seals", "validate_postconditions", "prove_idempotence_on_isolated_copy"}.issubset(check_calls),
        "source rewrite --check does not perform the complete pure verification protocol",
    )
    require("_apply_all_rewrites" not in check_calls, "source rewrite --check re-enters the mutating anchor engine")
    return {
        "python_source_count": len(trees),
        "runtime_resource_gate_calls": sum(1 for name, _ in called_attributes(runtime_process) if name == "_require_resources"),
        "source_rewrite_check_pure": True,
    }


def validate_behavior(repo: Path) -> dict[str, Any]:
    import_repo(repo)
    from cemm.cognition import QueryResult, QueryStructure
    from cemm.goals import GoalArbiter, GoalCandidate, GoalDecision
    from cemm.operational import (
        OperationalInvariantChecker, OperationalInvariantError, OperationalSnapshot,
        RuntimeResourceObservation, RuntimeServiceRegistry,
    )
    from cemm.semantic_coverage import (
        CoverageIntegrityError, CoveragePolicy, InterpretationCoverage,
        coverage_from_dict,
    )
    from cemm.surface_plans import ExactSurfacePlanIndex
    from cemm.response import ResponseBuilder

    unit = SimpleNamespace(unit_ref="u0", kind="unknown", surface="know", normalized="know", token_start=0, token_end=1, char_start=0, char_end=4, features={"predicate": True})
    receipt = CoveragePolicy.build((unit,), (), required_semantic_roles=("predicate",))
    require(not receipt.executable and bool(receipt.critical_residual_refs) and receipt.residuals[0].unit_refs == ("u0",), "critical residual can execute")
    forged = receipt.as_dict()
    forged["complete"] = True
    try:
        coverage_from_dict(forged)
    except CoverageIntegrityError:
        pass
    else:
        raise ContractError("tampered coverage receipt was trusted")

    loaded_receipt = coverage_from_dict(receipt.as_dict())
    try:
        loaded_receipt.assert_provenance(
            schema_ref="schema:other",
            hypothesis_ref=loaded_receipt.hypothesis_ref,
            match_seed_ref=loaded_receipt.match_seed_ref,
        )
    except CoverageIntegrityError:
        pass
    else:
        raise ContractError("coverage receipt was reusable across semantic candidates")
    diagnostic = coverage_from_dict(InterpretationCoverage.unresolved(seed="validator").as_dict())
    require(diagnostic.diagnostic_only and not diagnostic.executable, "diagnostic coverage became executable")

    query = QueryStructure.from_dict({
        "restrictions": [{"operator": "op:relation", "args": {"role:subject": "participant:system", "role:relation": "rel:knows", "role:object": "entity:donald-trump"}}],
        "variables": [], "projection": [], "qualifiers": {"query_kind": "relation_query"},
    })
    require(query.projection == (), "explicit empty boolean projection was expanded")
    require(dict(query.qualifiers) == {"query_kind": "relation_query"}, "query qualifiers drifted")

    unknown_registry = RuntimeServiceRegistry()
    unavailable_registry = RuntimeServiceRegistry()
    for ref in sorted(CANONICAL_RESOURCES):
        unknown_registry.register(ref, lambda: None)
        unavailable_registry.register(
            ref,
            (lambda: False) if ref == "resource:inference_engine" else (lambda: True),
        )
    unknown = unknown_registry.capture(
        self_ref="participant:system", cycle_ref="cycle:unknown",
        authority_generation=1, world_revision=1,
    )
    unavailable = unavailable_registry.capture(
        self_ref="participant:system", cycle_ref="cycle:unavailable",
        authority_generation=1, world_revision=1,
    )
    require(unknown.score("resource:inference_engine") is None and unknown.assess().score is None, "unknown operational evidence became numeric")
    for snapshot in (unknown, unavailable):
        try:
            OperationalInvariantChecker.require_resource(snapshot, "resource:inference_engine", stage=10)
        except OperationalInvariantError:
            pass
        else:
            raise ContractError("unresolved/unavailable resource use was allowed")

    registry = RuntimeServiceRegistry()
    for ref in sorted(CANONICAL_RESOURCES):
        registry.register(ref, lambda: True)
    registry.validate_resources()
    captured = registry.capture(self_ref="participant:system", cycle_ref="cycle:registry", authority_generation=1, world_revision=1)
    require(captured.assess().status == "operating_normally", "healthy service registry is not assessed normally")

    blocked = GoalCandidate("goal:blocked", "answer_query", "query:x", 10.0, blockers=("critical_residual",))
    clarify = GoalCandidate("goal:clarify", "clarify", "frontier:x", 1.0)
    require(GoalArbiter.decide((blocked, clarify)).selected.goal_ref == "goal:clarify", "blocked answer outranked clarification")
    require(GoalArbiter.decide((blocked,)).selected is None, "all-blocked goal set still selected a goal")

    unanswered = QueryResult(
        "query:learning", "unknown", (), 0.0, 0, 0, (), (), (),
        {"query_kind": "meaning_query"},
    )
    learning_candidates = GoalArbiter().candidates(
        act=SimpleNamespace(force="query", evidence={}, act_ref="act:learning"),
        query_result=unanswered,
        learning_probe=({
            "query_ref": unanswered.query_ref,
            "surface": "Alpha",
            "learning_plan": {"plan_ref": "plan:validator-learning"},
        },),
    )
    learning_goals = [
        item for item in learning_candidates
        if item.kind == "request_learning_evidence"
    ]
    require(
        len(learning_goals) == 1,
        "unanswered exact query did not create one learning obligation",
    )
    # ResponseBuilder.build() for learning requires a full typed LearningPlan
    # with contract/authority state; that is exercised by the native semantic
    # spine test suite (tests/test_native_semantic_spine.py) rather than this
    # standalone structural validator.
    blocked_learning = QueryResult(
        "query:blocked-learning", "unknown", (), 0.0, 0, 0, (), (),
        ("frontier:critical",), {"query_kind": "meaning_query"},
    )
    blocked_candidates = GoalArbiter().candidates(
        act=SimpleNamespace(force="query", evidence={}, act_ref="act:blocked"),
        query_result=blocked_learning,
        learning_probe=({
            "query_ref": blocked_learning.query_ref,
            "surface": "Alpha",
            "learning_plan": {"plan_ref": "plan:validator-blocked"},
        },),
    )
    require(
        not any(
            item.kind == "request_learning_evidence"
            for item in blocked_candidates
        ),
        "critical query frontier was bypassed by a learning goal",
    )

    class Pack:
        language = "en"
        data = {"response_examples": [
            {"semantic": "RESPONSE greet", "surface_plan": "Hello."},
            {"semantic": "RESPONSE greet", "surface_plan": "Hi."},
        ]}
    try:
        ExactSurfacePlanIndex(Pack(), "response_examples")
    except ValueError:
        pass
    else:
        raise ContractError("conflicting exact surface supervision was accepted")
    return {
        "coverage_fail_closed": True,
        "coverage_provenance_bound": True,
        "operational_states_distinct": True,
        "blocked_goals_rejected": True,
        "post_query_learning_bound": True,
        "learning_frontiers_respected": True,
    }


def validate_language(repo: Path) -> dict[str, Any]:
    language = load_json(repo / "cemm/language_packs/en.json")
    form = load_json(repo / "cemm/form_packs/en.json")
    material = {key: value for key, value in language.items() if key != "pack_hash"}
    require(language.get("pack_hash") == hashlib.sha256(canonical(material).encode()).hexdigest(), "language-pack hash mismatch")
    require(language.get("form_pack_hash") == form.get("pack_hash"), "language pack does not pin form pack")
    contract = dict(language.get("semantic_operational_contract", {}) or {})
    require(contract.get("form_schema_algebra") == "atomic-feature-v7", "language pack pins the wrong form algebra")
    require(contract.get("response_fallback") == "same_response_csir_only", "language pack allows semantic fallback")
    require(contract.get("authority_atom_additions") == 0, "language migration claims authority additions")
    rules = tuple(language.get("response_grammar", ()))
    refs = [str(rule.get("ref") or "") for rule in rules]
    require(len(refs) == len(set(refs)) and all(refs), "response grammar refs are missing or duplicated")
    require("en:response:operational" not in refs, "legacy broad operational grammar remains")
    by_ref = {rule["ref"]: rule for rule in rules}
    required = {
        "en:response:designation", "en:response:type", "en:response:surface-choice",
        "en:response:attributed-claim", "en:response:relation-unknown",
        "en:response:operational-normal", "en:response:operational-degraded",
        "en:response:operational-unavailable", "en:response:operational-unknown",
    }
    require(required.issubset(by_ref), f"response grammar rules missing: {sorted(required-set(by_ref))}")
    for rule in rules:
        require(isinstance(rule.get("when"), Mapping), f"invalid response matcher {rule.get('ref')}")
        require(isinstance(rule.get("required_slots"), list), f"missing surface-slot ABI {rule.get('ref')}")
        require(isinstance(rule.get("semantic_slots"), list), f"missing semantic-slot ABI {rule.get('ref')}")
        action = rule.get("when", {}).get("action")
        if action in QUERY_RESPONSE_ACTIONS:
            require({"query_ref", "query_kind"}.issubset(rule["semantic_slots"]), f"query response rule is not obligation/query bound: {rule['ref']}")
    relation_slots = set(by_ref["en:response:relation-unknown"]["semantic_slots"])
    require({"subject_ref", "relation_ref", "object_surface"}.issubset(relation_slots), "relation uncertainty drops structured meaning")
    surface_slots = set(by_ref["en:response:surface-choice"]["semantic_slots"])
    require({"surface_decision_ref", "prior_response_ref", "prior_surface"}.issubset(surface_slots), "metalinguistic response lacks prior-surface provenance")
    return {"pack_hash": language["pack_hash"], "response_rule_count": len(rules)}


def validate_single_contract(repo: Path) -> None:
    contract = repo / "CEMM_RUNTIME_IMPLEMENTATION_CONTRACT.md"
    require(contract.exists(), "canonical implementation contract is missing")
    agents = (repo / "AGENTS.md").read_text(encoding="utf-8")
    require(contract.name in agents, "AGENTS.md does not route implementation authority to the canonical contract")


def validate(repo: Path) -> dict[str, Any]:
    require((repo / "cemm").is_dir(), f"not a CEMM repository: {repo}")
    report = {
        "authority": validate_authority(repo),
        "form_artifact": validate_form_artifact(repo),
        "migration": validate_migration_idempotence(repo),
        "source_structure": validate_source_structure(repo),
        "behavior": validate_behavior(repo),
        "language": validate_language(repo),
    }
    validate_single_contract(repo)
    return {"status": "semantic_operational_contract_valid", "abi_version": ABI_VERSION, **report}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    repo = Path(args.repo).resolve()
    try:
        report = validate(repo)
    except ContractError as exc:
        raise SystemExit(f"SEMANTIC-OPERATIONAL CONTRACT FAILED: {exc}") from exc
    print(json.dumps(report, indent=2) if args.json else "semantic-operational contract validation passed")


if __name__ == "__main__":
    main()
