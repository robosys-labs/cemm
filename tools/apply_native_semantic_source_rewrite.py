#!/usr/bin/env python3
"""Apply the native semantic spine to source files, fail-closed and idempotently.

This is a source-of-truth rewrite. Generated JSON is handled by the dedicated
asset migrations and generators. The rewrite contains no semantic surface
routing; text matching here is installer preimage validation only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
from typing import Callable

BUNDLE = Path(__file__).resolve().parents[1]
SOURCE_REWRITE_VERSION = 1


def payload_path(relative: str, *, replacement: bool = False) -> Path:
    """Resolve payload bytes from delivery-bundle or installed-repo layout.

    The delivery bundle keeps replacement files under ``replacement/``. After
    installation the validated target file itself is the canonical payload, so
    the checked-in rewriter falls back to the ordinary repository path.
    """
    rel = Path(relative)
    candidates = ([BUNDLE / "replacement" / rel] if replacement else []) + [BUNDLE / rel]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise RuntimeError(f"native semantic source payload is missing: {relative}")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_once_or_present(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one source preimage, found {count}")
    return text.replace(old, new, 1)


def rewrite(path: Path, transform: Callable[[str], str]) -> dict[str, object]:
    before = path.read_text(encoding="utf-8")
    after = transform(before)
    if after != before:
        path.write_text(after, encoding="utf-8")
    return {
        "path": str(path),
        "changed": after != before,
        "before_sha256": hashlib.sha256(before.encode()).hexdigest(),
        "after_sha256": hashlib.sha256(after.encode()).hexdigest(),
    }


def copy_exact(source: Path, target: Path) -> dict[str, object]:
    target.parent.mkdir(parents=True, exist_ok=True)
    before = sha256(target) if target.exists() else None
    payload = source.read_bytes()
    if not target.exists() or target.read_bytes() != payload:
        target.write_bytes(payload)
    return {
        "path": str(target),
        "changed": before != hashlib.sha256(payload).hexdigest(),
        "before_sha256": before,
        "after_sha256": hashlib.sha256(payload).hexdigest(),
    }


def patch_forms(text: str) -> str:
    text = replace_once_or_present(
        text,
        "from cemm.form_algebra import AtomicConstructionAssembler, AtomicSchemaMatcher\n",
        "from cemm.form_algebra import AtomicConstructionAssembler, AtomicSchemaMatcher\n"
        "from cemm.semantic_contributions import SemanticAffordanceIndex\n",
        "forms semantic affordance import",
    )
    text = replace_once_or_present(
        text,
        "        self.pack = form_pack\n        self.max_input_chars = int(max_input_chars)\n",
        "        self.pack = form_pack\n"
        "        self.affordances = SemanticAffordanceIndex(\n"
        "            store, authority_generation, max_profiles_per_target=4\n"
        "        )\n"
        "        self.max_input_chars = int(max_input_chars)\n",
        "forms semantic affordance index",
    )
    text = replace_once_or_present(
        text,
        '''            if record["source_kind"] == "designation":\n                context_ref = record.get("context_ref")\n                if context_ref and participant_frame and context_ref != participant_frame.conversation_ref:\n                    continue\n                semantic_candidates = [\n                    (\n                        str(record["semantic_ref"]),\n                        float(record.get("weight", 1.0)),\n                        {"label_type": record.get("label_type"), "label_ref": record.get("label_ref")},\n                    )\n                ]\n            else:\n                semantic_candidates = self._reference_candidates(record, participant_frame)\n''',
        '''            if record["source_kind"] == "designation":\n                context_ref = record.get("context_ref")\n                if context_ref and participant_frame and context_ref != participant_frame.conversation_ref:\n                    continue\n                semantic_ref = str(record["semantic_ref"])\n                base_features = {\n                    "label_type": record.get("label_type"),\n                    "label_ref": record.get("label_ref"),\n                }\n                semantic_candidates = [\n                    (\n                        semantic_ref,\n                        float(record.get("weight", 1.0)) + float(profile.score),\n                        {**base_features, **profile.as_features()},\n                    )\n                    for profile in self.affordances.profiles_for(semantic_ref)\n                ]\n            else:\n                semantic_candidates = self._reference_candidates(record, participant_frame)\n''',
        "forms designation to semantic contribution expansion",
    )
    text = replace_once_or_present(
        text,
        '''        elif normalized in self.function_forms or alternatives:\n            alternatives = alternatives or ({},)\n            kind = "function"\n''',
        '''        elif alternatives and all(\n            bool(dict(item).get("open_class")) for item in alternatives\n        ):\n            # Morphology without a designation is evidence, not semantic identity.\n            # Keep the unit open/critical until a designation target contributes\n            # one or more semantic affordance profiles.\n            kind = "unknown"\n        elif normalized in self.function_forms or alternatives:\n            alternatives = alternatives or ({},)\n            kind = "function"\n''',
        "forms open-class unresolved boundary",
    )
    text = replace_once_or_present(
        text,
        '''        if current_revision != self._index_world_revision:\n            self.index = SurfaceIndex(\n                self.store, self.language, self.authority_generation, current_revision\n            )\n            self._index_world_revision = current_revision\n''',
        '''        if current_revision != self._index_world_revision:\n            self.index = SurfaceIndex(\n                self.store, self.language, self.authority_generation, current_revision\n            )\n            self.affordances = SemanticAffordanceIndex(\n                self.store, self.authority_generation, max_profiles_per_target=4\n            )\n            self._index_world_revision = current_revision\n''',
        "forms revision-pinned affordance refresh",
    )
    text = replace_once_or_present(
        text,
        '''        "qualifiers": {
            "learning_operation": "resolve_designation",
            "surface_evidence": surface,
        },\n''',
        '''        "qualifiers": {
            "learning_contract_ref": "contract:designation_learning",
            "surface_evidence": surface,
        },\n''',
        "forms typed learning contract qualifier",
    )
    if "learning_operation" in text or "resolve_designation" in text:
        raise RuntimeError("forms retains legacy learning_operation")
    return text


def patch_interpreter(text: str) -> str:
    text = replace_once_or_present(
        text,
        '''            function_forms=(\n                pack.data.get("function_forms")\n                or pack.data.get("grammar_tokens", [])\n            ),\n''',
        '''            # Realization grammar is output authority only. Pre-core form\n            # classification is owned exclusively by the generated form pack.\n            function_forms=(),\n''',
        "interpreter realization vocabulary isolation",
    )
    text = replace_once_or_present(
        text,
        '''        qualifiers = dict(packet.get("qualifiers", {})) if packet else {}\n        operation = qualifiers.get("learning_operation")\n        if not operation:\n            return ()\n''',
        '''        qualifiers = dict(packet.get("qualifiers", {})) if packet else {}\n        contract_ref = qualifiers.get("learning_contract_ref")\n        if not contract_ref:\n            return ()\n''',
        "interpreter learning contract trigger",
    )
    text = replace_once_or_present(
        text,
        '''                "learning_operation": str(operation),\n                "probe_query": dict(query) if query else None,\n                "known_bindings": dict(qualifiers.get("known_bindings", {})),\n                "expected_answer_shape": {\n                    "operation": str(operation),\n                    "surface_cardinality": "one",\n                },\n''',
        '''                "learning_contract_ref": str(contract_ref),\n                "probe_query": dict(query) if query else None,\n                "known_bindings": dict(qualifiers.get("known_bindings", {})),\n                "expected_answer_shape": {\n                    "learning_contract_ref": str(contract_ref),\n                    "surface_cardinality": "one",\n                },\n''',
        "interpreter typed learning probe",
    )
    text = text.replace(
        '                            "knowledge_binding"\n                            if item.get("learning_operation")\n',
        '                            "knowledge_binding"\n                            if item.get("learning_contract_ref")\n',
        1,
    )
    if 'item.get("learning_operation")' in text or 'qualifiers.get("learning_operation")' in text:
        raise RuntimeError("interpreter retains legacy learning_operation")
    if 'pack.data.get("grammar_tokens")' in text or 'pack.data.get("function_forms")' in text:
        raise RuntimeError("interpreter still feeds realization vocabulary into cognition")
    return text


def patch_goals(text: str) -> str:
    text = replace_once_or_present(
        text,
        '''                    if item.get("query_ref") == query_result.query_ref\n                    and item.get("learning_operation")\n                    and str(item.get("surface") or "").strip()\n''',
        '''                    if item.get("query_ref") == query_result.query_ref\n                    and isinstance(item.get("learning_plan"), Mapping)\n                    and str(item.get("surface") or "").strip()\n''',
        "goals typed learning probe eligibility",
    )
    text = replace_once_or_present(
        text,
        '''                            probe.get("surface"),\n                            probe.get("learning_operation"),\n''',
        '''                            probe.get("surface"),\n                            dict(probe.get("learning_plan", {})).get("plan_ref"),\n''',
        "goals learning plan identity",
    )
    if "learning_operation" in text:
        raise RuntimeError("goals retains legacy learning_operation")
    return text


def patch_runtime(text: str) -> str:
    text = replace_once_or_present(
        text,
        "from cemm.model import AmbiguousReferent, canonical, now, stable\n",
        "from cemm.model import AmbiguousReferent, canonical, now, stable\n"
        "from cemm.learning_plans import (\n"
        "    LearningContractRegistry,\n"
        "    LearningPlan,\n"
        "    validate_learning_commit_packet,\n"
        ")\n",
        "runtime learning imports",
    )
    text = replace_once_or_present(
        text,
        "        self.i = Interpreter(self.s, self.pack, generation, self.config)\n",
        "        self.i = Interpreter(self.s, self.pack, generation, self.config)\n"
        "        self.learning_contracts = LearningContractRegistry(self.s, generation)\n",
        "runtime learning contract registry",
    )
    text = replace_once_or_present(
        text,
        '''    def reload_authority(self):
        generation = self.s.generation
        self.runtime_attestation["authority_generation"] = generation
        self.runtime_attestation["authority_generation_hash"] = self.s.authority_hash(generation)
        self._bind_authority()
        return dict(self.runtime_attestation)
''',
        '''    def reload_authority(self):
        invalidated = self.dialogue_state.invalidate_pending_on_authority_reload()
        generation = self.s.generation
        self.runtime_attestation["authority_generation"] = generation
        self.runtime_attestation["authority_generation_hash"] = self.s.authority_hash(generation)
        self._bind_authority()
        return {
            **dict(self.runtime_attestation),
            "invalidated_pending_learning_plan_ref": (
                invalidated.plan.plan_ref if invalidated is not None else None
            ),
        }
''',
        "runtime authority reload invalidates stale learning plan",
    )
    text = replace_once_or_present(
        text,
        '''                learning_probe.append({\n                    **probe,\n                    "query_ref": query_result.query_ref,\n                    "probe_query": exact_query,\n                })\n''',
        '''                contract_ref = str(probe.get("learning_contract_ref") or "")\n                query_kind = str(dict(query_result.qualifiers or {}).get("query_kind") or "")\n                contract = self.learning_contracts.license_query(contract_ref, query_kind)\n                candidate_target_kinds = tuple(sorted(\n                    set(map(str, probe.get("semantic_kind_candidates", ())))\n                    & set(contract.expected_target_kinds)\n                ))\n                if not candidate_target_kinds:\n                    raise RuntimeError(\n                        "learning probe has no target kind licensed by its contract"\n                    )\n                plan = LearningPlan.create(\n                    contract=contract,\n                    source_query_ref=query_result.query_ref,\n                    source_query_kind=query_kind,\n                    source_query=exact_query,\n                    authority_generation=int(\n                        self.runtime_attestation["authority_generation"]\n                    ),\n                    surface_literal=str(probe.get("surface") or ""),\n                    language=self.lang,\n                    expected_target_kinds=candidate_target_kinds,\n                    known_bindings=dict(probe.get("known_bindings", {})),\n                    target_ref=probe.get("target_ref"),\n                    original_candidate_ref=probe.get("original_candidate_ref"),\n                    unresolved_span_ref=probe.get("unresolved_span_ref"),\n                    created_turn=self._cycle_counter,\n                    expires_after_turn=self.dialogue_state.expiry_turns,\n                )\n                plan.validate_authority(\n                    self.s, authority_generation=int(\n                        self.runtime_attestation["authority_generation"]\n                    )\n                )\n                learning_probe.append({\n                    **probe,\n                    "query_ref": query_result.query_ref,\n                    "probe_query": exact_query,\n                    "learning_plan": plan.as_dict(),\n                })\n''',
        "runtime bind exact typed learning plan",
    )
    text = replace_once_or_present(
        text,
        '''            if packet_qualifiers.get("consumes_pending_learning"):\n                self.dialogue_state.require(\n                    packet_qualifiers.get("pending_learning_obligation_ref")\n                )\n''',
        '''            if packet_qualifiers.get("consumes_pending_learning"):\n                pending_learning = self.dialogue_state.require(\n                    packet_qualifiers.get("pending_learning_obligation_ref")\n                )\n                validate_learning_commit_packet(\n                    packet,\n                    pending_learning,\n                    self.s,\n                    authority_generation=int(\n                        self.runtime_attestation["authority_generation"]\n                    ),\n                )\n''',
        "runtime validate learning commit before Stage 13",
    )
    if "learning_operation" in text:
        raise RuntimeError("runtime retains legacy learning_operation")
    return text


def patch_response(text: str) -> str:
    text = replace_once_or_present(
        text,
        "from cemm.model import Fact, canonical, stable\n",
        "from cemm.model import Fact, canonical, stable\n"
        "from cemm.learning_plans import LearningPlan\n",
        "response learning import",
    )
    text = replace_once_or_present(
        text,
        '        reason = goal_decision.reason if goal_decision else "no_goal"\n        obligation_ref = goal.goal_ref if goal else None\n',
        '        reason = goal_decision.reason if goal_decision else "no_goal"\n'
        '        obligation_ref = goal.goal_ref if goal else None\n'
        '        precomputed_response_ref = None\n',
        "response precomputed ref initialization",
    )
    text = replace_once_or_present(
        text,
        '            common = {\n                **query_qualifiers,\n                "query_status": query_result.status,\n                "coverage": query_result.coverage,\n                "unresolved_variables": list(query_result.unresolved_variables),\n                "query_ref": query_result.query_ref,\n            }\n            if query_qualifiers.get("query_kind") == "operational_condition_query":\n',
        '            common = {\n                **query_qualifiers,\n                "query_status": query_result.status,\n                "coverage": query_result.coverage,\n                "unresolved_variables": list(query_result.unresolved_variables),\n                "query_ref": query_result.query_ref,\n            }\n            if query_qualifiers.get("query_kind") == "capability_inventory_query":\n                target_ref = query_qualifiers.get("target_ref")\n            if query_qualifiers.get("query_kind") == "operational_condition_query":\n',
        "response capability inventory target binding",
    )
    if 'operation = str(payload.get("learning_operation") or "")' in text:
        start = text.index('            operation = str(payload.get("learning_operation") or "")')
        marker = '            reason = "unanswered_learning_query"\n'
        end = text.index(marker, start) + len(marker)
        replacement = '''            raw_plan = payload.get("learning_plan")\n            if not isinstance(raw_plan, Mapping):\n                raise ValueError("learning request requires typed learning plan")\n            plan = LearningPlan.from_dict(raw_plan)\n            surface = str(payload.get("surface") or "").strip()\n            query_kind = str(dict(query_result.qualifiers or {}).get("query_kind") or "")\n            if not surface or not query_kind:\n                raise ValueError("learning request requires surface and query kind")\n            if plan.source_query_ref != query_result.query_ref:\n                raise ValueError("learning plan is not bound to executed query")\n            if plan.source_query_kind != query_kind:\n                raise ValueError("learning plan query kind differs from QueryResult")\n            probe_query = payload.get("probe_query")\n            if not isinstance(probe_query, Mapping):\n                raise ValueError("learning request lacks exact probe query")\n            if canonical(plan.source_query) != canonical(dict(probe_query)):\n                raise ValueError("learning plan source query differs from goal probe query")\n            if plan.surface_literal != surface:\n                raise ValueError("learning plan surface differs from probe")\n            action = "request_learning_evidence"\n            target_ref = plan.target_ref\n            literals = (surface,)\n            qualifiers = {\n                "query_ref": query_result.query_ref,\n                "query_kind": query_kind,\n                "learning_query": payload.get("probe_query"),\n                "expected_semantic_kinds": list(plan.expected_target_kinds),\n                "known_bindings": dict(plan.known_bindings),\n                "expected_answer_shape": {\n                    "answer_contract_ref": plan.answer_contract_ref,\n                    "surface_cardinality": "one",\n                },\n                "original_candidate_ref": plan.original_candidate_ref,\n                "unresolved_span_ref": plan.unresolved_span_ref,\n            }\n            precomputed_response_ref = stable("response-csir", (\n                action, audience_ref, target_ref, [], (), qualifiers,\n                literals, "unanswered_learning_query", obligation_ref,\n            ))\n            plan = plan.bind_response(\n                response_ref=precomputed_response_ref,\n                goal_ref=obligation_ref,\n            )\n            qualifiers["learning_plan"] = plan.as_dict()\n            qualifiers["learning_plan_ref"] = plan.plan_ref\n            qualifiers["learning_contract_ref"] = plan.contract_ref\n            reason = "unanswered_learning_query"\n'''
        text = text[:start] + replacement + text[end:]
    text = replace_once_or_present(
        text,
        '''            learning_operation = evidence.get("learning_operation")\n            action = "request_learning_evidence" if learning_operation else "request_targeted_clarification"\n            target_ref = frontier.target_ref\n            surface = evidence.get("surface") or evidence.get("normalized")\n            literals = (str(surface),) if surface else ()\n''',
        '''            raw_learning_plan = evidence.get("learning_plan")\n            surface = evidence.get("surface") or evidence.get("normalized")\n            if isinstance(raw_learning_plan, Mapping):\n                action = "request_learning_evidence"\n            elif surface or frontier.target_ref:\n                action = "request_targeted_clarification"\n            else:\n                action = "request_generic_clarification"\n            target_ref = frontier.target_ref\n            literals = (str(surface),) if surface else ()\n''',
        "response generic clarification and typed learning selection",
    )
    legacy = '''            if learning_operation:\n                qualifiers.update(\n                    {\n                        "learning_operation": str(learning_operation),\n                        "learning_query": evidence.get("probe_query"),\n                        "known_bindings": dict(evidence.get("known_bindings", {})),\n                        "expected_answer_shape": dict(\n                            evidence.get("expected_answer_shape", {})\n                            or {\n                                "operation": str(learning_operation),\n                                "surface_cardinality": "one",\n                            }\n                        ),\n                    }\n                )\n'''
    typed = '''            if isinstance(raw_learning_plan, Mapping):\n                plan = LearningPlan.from_dict(raw_learning_plan)\n                qualifiers.update(\n                    {\n                        "learning_plan": plan.as_dict(),\n                        "learning_plan_ref": plan.plan_ref,\n                        "learning_contract_ref": plan.contract_ref,\n                        "query_ref": plan.source_query_ref,\n                        "query_kind": plan.source_query_kind,\n                        "learning_query": evidence.get("probe_query"),\n                        "known_bindings": dict(plan.known_bindings),\n                        "expected_answer_shape": {\n                            "answer_contract_ref": plan.answer_contract_ref,\n                            "surface_cardinality": "one",\n                        },\n                    }\n                )\n'''
    text = replace_once_or_present(text, legacy, typed, "response typed frontier learning plan")
    text = replace_once_or_present(
        text,
        '''    learning_operation = response.qualifiers.get("learning_operation")\n    if learning_operation:\n        parts += ["LEARNING", str(learning_operation)]\n''',
        '''    learning_plan_ref = response.qualifiers.get("learning_plan_ref")\n    if learning_plan_ref:\n        parts += [\n            "LEARNING_PLAN",\n            table.literal(\n                {"literal": {"type": "text", "value": str(learning_plan_ref)}},\n                "response:learning_plan_ref",\n            ),\n        ]\n''',
        "response pointerized typed learning plan",
    )
    text = replace_once_or_present(
        text,
        '''        for frontier in frontiers:
            for item in frontier.evidence:
                if item.get("learning_operation"):
                    qualifiers.setdefault("learning_operation", item["learning_operation"])
                    if item.get("surface"):
                        literals.append(str(item["surface"]))
''',
        '''        for frontier in frontiers:
            for item in frontier.evidence:
                if item.get("learning_plan_ref"):
                    qualifiers.setdefault("learning_plan_ref", item["learning_plan_ref"])
                    if item.get("surface"):
                        literals.append(str(item["surface"]))
''',
        "response answer metadata typed learning plan",
    )
    text = replace_once_or_present(
        text,
        '''        return ResponseCSIR(
            stable("response-csir", payload),
            action,
            audience_ref,
            target_ref,
            facts,
            bindings,
            qualifiers,
            literals,
            reason,
            obligation_ref,
        )''',
        '''        return ResponseCSIR(
            precomputed_response_ref or stable("response-csir", payload),
            action,
            audience_ref,
            target_ref,
            facts,
            bindings,
            qualifiers,
            literals,
            reason,
            obligation_ref,
        )''',
        "response precomputed ref usage",
    )
    if "learning_operation" in text:
        raise RuntimeError("response retains legacy learning_operation")
    return text


def patch_reference(text: str) -> str:
    text = replace_once_or_present(
        text,
        '''        if action == "request_learning_evidence":\n            return frozenset({"evidence", "learning_operation", "frontier_ref"})\n        if action == "request_targeted_clarification":\n            return frozenset({"evidence", "frontier_ref"})\n''',
        '''        if action == "request_learning_evidence":\n            return frozenset({\n                "evidence", "learning_plan_ref", "query_ref", "query_kind"\n            })\n        if action == "request_targeted_clarification":\n            return frozenset({"evidence", "frontier_ref"})\n        if action == "request_generic_clarification":\n            return frozenset({"frontier_ref"})\n        if action in {"answer_bindings", "report_multiple_bindings"} and query_kind == "capability_inventory_query":\n            return frozenset(base | {"binding_values", "target_ref"})\n        if action == "report_target_uncertainty" and query_kind == "capability_inventory_query":\n            return frozenset(base | {"target_ref"})\n''',
        "reference response semantic contracts",
    )
    if "learning_operation" in text:
        raise RuntimeError("reference realizer retains legacy learning_operation")
    return text


def patch_cli(text: str) -> str:
    text = replace_once_or_present(
        text,
        "from cemm.authority import load_documents, validate_documents, validate_pack_constants\n",
        "from cemm.authority import load_documents, validate_documents, validate_pack_constants\n"
        "from cemm.activation import assert_native_semantic_activation\n",
        "cli activation import",
    )
    text = replace_once_or_present(
        text,
        "def runtime(args): return Runtime(Store(args.db), args.pack)\n",
        "def runtime(args):\n"
        "    instance = Runtime(Store(args.db), args.pack)\n"
        "    assert_native_semantic_activation(instance.i.form_pack, instance.s)\n"
        "    return instance\n",
        "cli fail-closed native semantic activation",
    )
    return text


def patch_authority(text: str) -> str:
    text = replace_once_or_present(
        text,
        "from typing import Any, Iterable, Mapping, Sequence\n",
        "from typing import Any, Iterable, Mapping, Sequence\n\n"
        "from cemm.native_semantic_validation import validate_native_semantic_authority\n",
        "authority native validator import",
    )
    text = replace_once_or_present(
        text,
        '''    if require_foundations:\n        missing_relations = sorted(ref for ref in FOUNDATIONAL_META_RELATIONS if atom_kinds.get(ref) != "relation_type")\n''',
        '''    issues.extend(validate_native_semantic_authority(\n        atom_defs=atom_defs,\n        role_defs=role_defs,\n        facts=facts,\n    ))\n\n    if require_foundations:\n        missing_relations = sorted(ref for ref in FOUNDATIONAL_META_RELATIONS if atom_kinds.get(ref) != "relation_type")\n''',
        "authority native semantic graph validation",
    )
    return text


def patch_activation_callsite(text: str) -> str:
    # Older activation call sites passed only module/pack. The v1 spine validates
    # contract/frame authority too, so pass the runtime store when present.
    text = text.replace(
        "assert_atomic_graph_activation(runtime=self._runtime)",
        "assert_native_semantic_activation(runtime=self._runtime, store=self._store)",
    )
    return text



def patch_runtime_contract(text: str) -> str:
    text = text.replace("**Coverage/Form ABI:** 5", "**Coverage/Form ABI:** 6", 1)
    text = text.replace(
        "`designation_learning` is an immutable query kind licensed only for the\nexisting exact `resolve_designation` learning operation.",
        "`designation_learning` is an immutable query kind licensed only by the\nauthority-backed `contract:designation_learning` typed learning contract.",
        1,
    )
    marker = "## 21. Native semantic spine ABI 1"
    if marker not in text:
        text = text.rstrip() + """

## 21. Native semantic spine ABI 1

A designation resolves possible semantic identity. A generation-pinned semantic
affordance index derives bounded compositional candidates from the target's
semantic kind and reviewed `rel:has_semantic_frame` links. Language packs may
provide morphology and closed-class structure but do not own open-class semantic
identity. A learned designation must become compositionally usable without form
pack regeneration.

Runtime learning continuation is represented by `LearningPlan` ABI 1. It is
bound to one executed QueryStructure/QueryResult, one pinned authority generation,
one reviewed contract, one capability, one five-operator commit effect, one answer
contract and one pending dialogue obligation. `learning_operation` strings are forbidden in active source,
training authority, generated packs and Response CSIR.

Nested propositions remain rooted graphs of the five fixed operators. Event
complements use explicit event refs in reviewed roles; no proposition operator or
phrase-intent kernel is introduced.

Activation must attest Coverage/Form ABI 6, Semantic Contribution ABI 1,
LearningPlan ABI 1, PropositionGraph ABI 1, module provenance, generated pack
receipts and the linked frame/contract authority graph before serving input.
"""
    return text


def patch_core_loop_doc(text: str) -> str:
    marker = "## 13. Native semantic contribution and learning handoff"
    if marker in text:
        return text
    return text.rstrip() + """

## 13. Native semantic contribution and learning handoff

Between Stage 3 grounding and Stage 5 compilation, every designation candidate
is expanded through a generation-pinned `SemanticAffordanceIndex`. The resulting
transient contribution carries semantic identity, contribution kind, typed ports,
frame roles and provenance. This does not create or commit an atom.

Stage 5 consumes schema-declared and contribution-provided ports together. A
grounded predicate contribution left unassigned is critical. A morphology-only
open-class form with no designation remains a typed unknown and cannot cross the
Stage-7 executable boundary.

For unanswered exact designation/meaning queries, Stage 15 may receive one
`LearningPlan` only after Stage 10 has produced the matching QueryResult. The plan
identity includes the exact QueryStructure and pinned authority generation. Stage
18 preserves that plan in Response CSIR; Stage 21 may open one pending
obligation only after verified realization. A continuation can consume the
obligation only when Stage 13 validates and commits the exact licensed
`op:designation` effect and produces its receipt.

Proposition embedding uses bounded graphs of ordinary five-operator
applications. Shared event refs and explicit roles encode event complements; no
new proposition or intent operator is permitted.
"""

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    args = parser.parse_args()
    repo = args.repo.resolve()
    if not (repo / "cemm" / "runtime.py").exists():
        raise SystemExit(f"not a CEMM checkout: {repo}")

    changes: list[dict[str, object]] = []
    copies = (
        (payload_path("cemm/semantic_contributions.py"), repo / "cemm" / "semantic_contributions.py"),
        (payload_path("cemm/learning_plans.py"), repo / "cemm" / "learning_plans.py"),
        (payload_path("cemm/propositions.py"), repo / "cemm" / "propositions.py"),
        (payload_path("cemm/native_semantic_validation.py"), repo / "cemm" / "native_semantic_validation.py"),
        (payload_path("cemm/activation.py"), repo / "cemm" / "activation.py"),
        (payload_path("cemm/atomic_graph.py", replacement=True), repo / "cemm" / "atomic_graph.py"),
        (payload_path("cemm/form_algebra.py", replacement=True), repo / "cemm" / "form_algebra.py"),
        (payload_path("cemm/dialogue.py", replacement=True), repo / "cemm" / "dialogue.py"),
        (payload_path("cemm/web_demo.py", replacement=True), repo / "cemm" / "web_demo.py"),
    )
    for source, target in copies:
        changes.append(copy_exact(source, target))

    transforms = (
        ("cemm/forms.py", patch_forms),
        ("cemm/interpreter.py", patch_interpreter),
        ("cemm/goals.py", patch_goals),
        ("cemm/runtime.py", patch_runtime),
        ("cemm/response.py", patch_response),
        ("cemm/reference.py", patch_reference),
        ("cemm/cli.py", patch_cli),
        ("cemm/authority.py", patch_authority),
        ("CEMM_RUNTIME_IMPLEMENTATION_CONTRACT.md", patch_runtime_contract),
        ("runtime-core-loop.md", patch_core_loop_doc),
    )
    for relative, transform in transforms:
        changes.append(rewrite(repo / relative, transform))

    forbidden = {}
    for relative in (
        "cemm/interpreter.py", "cemm/goals.py", "cemm/runtime.py",
        "cemm/response.py", "cemm/reference.py", "cemm/dialogue.py",
    ):
        payload = (repo / relative).read_text(encoding="utf-8")
        if "learning_operation" in payload:
            forbidden[relative] = "learning_operation"
    if forbidden:
        raise RuntimeError(f"legacy learning protocol survived rewrite: {forbidden}")

    print(json.dumps({
        "source_rewrite_version": SOURCE_REWRITE_VERSION,
        "changes": changes,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
