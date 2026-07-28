"""Fail-closed runtime activation attestation for the native semantic spine."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping
import hashlib
import os
import sys

from cemm import atomic_graph, form_algebra, semantic_coverage
from cemm import semantic_contributions, learning_plans, propositions
from cemm import composition, semantic_description, proof
from cemm.model import stable

EXPECTED_COVERAGE_ABI = 7
EXPECTED_FEATURE_ALGEBRA = 7
EXPECTED_CONTRIBUTION_ABI = 1
EXPECTED_LEARNING_PLAN_ABI = 1
EXPECTED_PROPOSITION_ABI = 2
EXPECTED_ATOMIC_COMPOSITION_ABI = 1
EXPECTED_DESCRIPTION_ABI = 1
EXPECTED_PROOF_ABI = 1


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _record(module: Any, package_root: Path) -> dict[str, Any]:
    raw = getattr(module, "__file__", None)
    path = Path(raw).resolve() if raw else None
    inside = bool(path and (path == package_root or package_root in path.parents))
    return {
        "module": str(getattr(module, "__name__", "")),
        "path": str(path) if path else None,
        "sha256": _sha256(path) if path and path.is_file() else None,
        "inside_package_root": inside,
    }


def _contains_key(value: Any, key: str) -> bool:
    if isinstance(value, Mapping):
        return key in value or any(_contains_key(item, key) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains_key(item, key) for item in value)
    return False


def activation_attestation(form_pack: Any, store: Any | None = None) -> dict[str, Any]:
    package_root = Path(__file__).resolve().parent
    modules = (
        atomic_graph,
        form_algebra,
        semantic_coverage,
        semantic_contributions,
        learning_plans,
        propositions,
        composition,
        semantic_description,
        proof,
    )
    records = tuple(_record(item, package_root) for item in modules)
    data = dict(getattr(form_pack, "data", {}) or {})
    receipt = dict(data.get("training_receipt", {}) or {})
    coverage_abi = int(getattr(semantic_coverage, "COVERAGE_ABI_VERSION", -1))
    feature_algebra = int(data.get("feature_algebra_version", -1))
    receipt_version = int(receipt.get("receipt_version", -1))
    contribution_abi = int(getattr(semantic_contributions, "SEMANTIC_CONTRIBUTION_ABI", -1))
    learning_plan_abi = int(getattr(learning_plans, "LEARNING_PLAN_ABI", -1))
    proposition_abi = int(getattr(propositions, "PROPOSITION_GRAPH_ABI", -1))
    atomic_composition_abi = int(getattr(propositions, "ATOMIC_COMPOSITION_ABI", -1))
    description_abi = int(getattr(semantic_description, "DESCRIPTION_ABI", -1))
    proof_abi = int(getattr(proof, "PROOF_BUNDLE_ABI", -1))

    errors: list[str] = []
    expected = {
        "coverage_abi": (coverage_abi, EXPECTED_COVERAGE_ABI),
        "feature_algebra": (feature_algebra, EXPECTED_FEATURE_ALGEBRA),
        "receipt_version": (receipt_version, EXPECTED_FEATURE_ALGEBRA),
        "semantic_contribution_abi": (contribution_abi, EXPECTED_CONTRIBUTION_ABI),
        "learning_plan_abi": (learning_plan_abi, EXPECTED_LEARNING_PLAN_ABI),
        "proposition_graph_abi": (proposition_abi, EXPECTED_PROPOSITION_ABI),
        "atomic_composition_abi": (atomic_composition_abi, EXPECTED_ATOMIC_COMPOSITION_ABI),
        "description_abi": (description_abi, EXPECTED_DESCRIPTION_ABI),
        "proof_bundle_abi": (proof_abi, EXPECTED_PROOF_ABI),
    }
    for label, (actual, required) in expected.items():
        if actual != required:
            errors.append(f"{label}:{actual}:expected:{required}")
    if int(receipt.get("feature_algebra_version", -1)) != EXPECTED_FEATURE_ALGEBRA:
        errors.append("receipt_feature_algebra_mismatch")
    if not receipt.get("graph_matcher") or receipt.get("total_order_matcher") is not False:
        errors.append("graph_matcher_receipt_missing")
    if _contains_key(data, "learning_operation"):
        errors.append("legacy_learning_operation_present_in_form_pack")
    if _contains_key(data, "semantic_port"):
        errors.append("legacy_semantic_port_present_in_form_pack")
    open_class_records = [
        record
        for record in data.get("lexemes", ())
        if bool(dict(record.get("features", {})).get("open_class"))
    ]
    open_class_forms = {
        str(form).casefold()
        for record in open_class_records
        for form in record.get("forms", ())
    }
    forbidden_open_class_features = {
        "semantic_target_hint", "semantic_ref", "semantic_kind", "relation_ref",
        "property_ref", "capability_ref", "state_dimension_ref",
        "contribution_kind", "affordance_ref", "ports_provided", "ports_required",
    }
    leaked_identity = sorted({
        key
        for record in open_class_records
        for key in dict(record.get("features", {}))
        if key in forbidden_open_class_features
    })
    if leaked_identity:
        errors.append(
            "open_class_semantic_identity_in_form_pack:" + ",".join(leaked_identity)
        )
    function_forms = {str(form).casefold() for form in data.get("function_forms", ())}
    leaked_open_class = sorted(open_class_forms & function_forms)
    if leaked_open_class:
        errors.append(
            "open_class_forms_in_function_forms:" + ",".join(leaked_open_class[:12])
        )
    for item in records:
        if not item["inside_package_root"]:
            errors.append(f"module_outside_package:{item['module']}")
        if not item["sha256"]:
            errors.append(f"module_digest_missing:{item['module']}")

    authority: dict[str, Any] = {}
    if store is not None:
        required_refs = {
            "rel:has_semantic_frame": "relation_type",
            "rel:licenses_learning_contract": "relation_type",
            "event:learn": "event_type",
            "frame:event-learn": "semantic_frame",
            "event:know": "event_type",
            "frame:event-know": "semantic_frame",
            "event:greeting": "event_type",
            "frame:event-greeting-discourse": "semantic_frame",
            "contract:designation_learning": "concept",
            "contract:designation_target_answer": "concept",
            "goal:acquire_designation": "goal",
            "cap:learn": "capability",
            "op:designation": "operator",
        }
        for ref, kind in required_refs.items():
            atom = (
                store.authority_atom(ref, upto_generation=getattr(store, "generation", None))
                if hasattr(store, "authority_atom")
                else store.atom(ref)
            )
            actual = str(atom["kind"]) if atom is not None else None
            authority[ref] = actual
            if actual != kind:
                errors.append(f"authority_ref:{ref}:{actual}:expected:{kind}")
        try:
            learning_plans.LearningContractRegistry(
                store, getattr(store, "generation", None)
            ).get(learning_plans.DESIGNATION_LEARNING_CONTRACT)
        except Exception as exc:
            errors.append(f"learning_contract_invalid:{type(exc).__name__}:{exc}")
        try:
            profiles = semantic_contributions.SemanticAffordanceIndex(
                store, getattr(store, "generation", None), max_profiles_per_target=4
            ).profiles_for("event:learn")
            if not any(item.profile_ref == "frame:event-learn" for item in profiles):
                errors.append("learning_frame_not_active")
            know_profiles = semantic_contributions.SemanticAffordanceIndex(
                store, getattr(store, "generation", None), max_profiles_per_target=4
            ).profiles_for("event:know")
            if not any(
                item.profile_ref == "frame:event-know"
                and item.metadata.get("proposition_taking")
                and any("app" in role.filler_kinds for role in item.roles)
                for item in know_profiles
            ):
                errors.append("knowledge_proposition_frame_not_active")
            greeting_profiles = semantic_contributions.SemanticAffordanceIndex(
                store, getattr(store, "generation", None), max_profiles_per_target=4
            ).profiles_for("event:greeting")
            if not any(
                item.profile_ref == "frame:event-greeting-discourse"
                and item.metadata.get("standalone_licensed")
                for item in greeting_profiles
            ):
                errors.append("standalone_greeting_frame_not_active")
        except Exception as exc:
            errors.append(f"learning_frame_invalid:{type(exc).__name__}:{exc}")

    material = {
        "coverage_abi": coverage_abi,
        "feature_algebra_version": feature_algebra,
        "receipt_version": receipt_version,
        "semantic_contribution_abi": contribution_abi,
        "learning_plan_abi": learning_plan_abi,
        "proposition_graph_abi": proposition_abi,
        "atomic_composition_abi": atomic_composition_abi,
        "description_abi": description_abi,
        "proof_bundle_abi": proof_abi,
        "form_pack_hash": str(getattr(form_pack, "hash", "")),
        "modules": list(records),
        "authority": authority,
        "python_executable": str(Path(sys.executable).resolve()),
        "working_directory": str(Path.cwd().resolve()),
        "process_id": os.getpid(),
    }
    return {
        "activation_ref": stable("native-semantic-spine-activation", material),
        "ok": not errors,
        **material,
        "errors": errors,
        "source_changes_require_process_restart": True,
        "authority_reload_reloads_python_source": False,
    }


def assert_native_semantic_activation(form_pack: Any, store: Any | None = None) -> dict[str, Any]:
    attestation = activation_attestation(form_pack, store)
    if not attestation["ok"]:
        raise RuntimeError("native semantic activation failed: " + ", ".join(attestation["errors"]))
    return attestation

