#!/usr/bin/env python3
"""Install the recursive native-semantic runtime into the pinned CEMM checkout.

The rewrite targets the reviewed main commit only.  It is byte-idempotent and
fails when the expected current architecture is absent.  Surface strings below
are installer preimages, never runtime cognition.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Callable

BUNDLE = Path(__file__).resolve().parents[1]
SOURCE_REWRITE_VERSION = 2


def payload(relative: str, replacement: bool = False) -> Path:
    rel = Path(relative)
    candidates = ([BUNDLE / "replacement" / rel] if replacement else []) + [BUNDLE / rel]
    for item in candidates:
        if item.is_file():
            return item
    raise RuntimeError(f"missing recursive semantic payload: {relative}")


def rewrite(path: Path, transform: Callable[[str], str]):
    before = path.read_text(encoding="utf-8")
    after = transform(before)
    if after != before:
        path.write_text(after, encoding="utf-8")
    return {
        "path": str(path), "changed": before != after,
        "before_sha256": hashlib.sha256(before.encode()).hexdigest(),
        "after_sha256": hashlib.sha256(after.encode()).hexdigest(),
    }


def copy_exact(source: Path, target: Path):
    target.parent.mkdir(parents=True, exist_ok=True)
    before = hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else None
    data = source.read_bytes()
    if not target.exists() or target.read_bytes() != data:
        target.write_bytes(data)
    return {"path": str(target), "changed": before != hashlib.sha256(data).hexdigest(),
            "before_sha256": before, "after_sha256": hashlib.sha256(data).hexdigest()}


def insert_once(text: str, marker: str, addition: str, label: str, *, after=True) -> str:
    if addition in text:
        return text
    if text.count(marker) != 1:
        raise RuntimeError(f"{label}: expected one insertion marker, found {text.count(marker)}")
    return text.replace(marker, marker + addition if after else addition + marker, 1)


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    if text.count(old) != 1:
        raise RuntimeError(f"{label}: expected one preimage, found {text.count(old)}")
    return text.replace(old, new, 1)


def replace_last_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    index = text.rfind(old)
    if index < 0:
        raise RuntimeError(f"{label}: expected a preimage")
    return text[:index] + new + text[index + len(old):]


def replace_region(text: str, start: str, end: str, replacement: str, label: str) -> str:
    if replacement in text:
        return text
    a = text.find(start)
    b = text.find(end, a + len(start)) if a >= 0 else -1
    if a < 0 or b < 0:
        raise RuntimeError(f"{label}: region markers not found")
    return text[:a] + replacement + text[b:]



def patch_forms(text: str) -> str:
    replacements = (
        ("algebra_version != 6", "algebra_version != 7"),
        ('receipt.get("receipt_version", -1)) != 6', 'receipt.get("receipt_version", -1)) != 7'),
        ("v6 graph matcher", "v7 recursive graph matcher"),
    )
    for before, after in replacements:
        if before in text:
            text = text.replace(before, after)
    required = (
        "algebra_version != 7",
        'receipt.get("receipt_version", -1)) != 7',
        "v7 recursive graph matcher",
    )
    if any(item not in text for item in required):
        raise RuntimeError("forms ABI-7 cutover did not reach every required gate")
    return text

def patch_interpreter(text: str) -> str:
    text = insert_once(
        text, "from cemm.semantic_coverage import (\n",
        "from cemm.composition import RecursiveCompositionChart\n",
        "interpreter recursive composition import", after=False,
    )
    marker = "        self._candidate_unknown_kinds_cache = self._candidate_unknown_kinds()\n"
    text = insert_once(
        text, marker,
        "        self.composition = RecursiveCompositionChart(self.constructions, self.config)\n"
        "        self._last_composition_result = None\n",
        "interpreter chart initialization", after=False,
    )
    start = "    def _construction_candidates(self, resolved, participant_frame):\n"
    end = "    @staticmethod\n    def _selected_candidate_trace"
    method = '''    def _construction_candidates(self, resolved, participant_frame):
        """Produce only complete candidates through the one recursive chart."""
        result = self.composition.compose(resolved, participant_frame, self.lang)
        self._last_composition_result = result
        return list(result.candidates), (), {}

'''
    text = replace_region(text, start, end, method, "interpreter construction cutover")
    old = '''        construction_candidates, partial_matches, construction_by_ref = self._construction_candidates(
            resolved, participant_frame
        )
'''
    new = '''        construction_candidates, partial_matches, construction_by_ref = self._construction_candidates(
            resolved, participant_frame
        )
        composition_result = self._last_composition_result
'''
    text = replace_once(text, old, new, "interpreter composition result binding")
    marker = '''        # A partial schema match preserves the best structural hypothesis and all
'''
    gap_branch = '''        if composition_result is not None and composition_result.gaps and not candidates:
            gap_evidence = []
            for gap in composition_result.gaps:
                item = gap.as_dict()
                coverage = dict(item.get("evidence", {}).get("coverage", {}) or {})
                residuals = list(coverage.get("critical_residuals", ()))
                residual = residuals[0] if residuals else {}
                unknown = bool(item.get("unknown_unit_refs")) and not item.get("known_unit_refs")
                gap_evidence.append({
                    "surface": residual.get("surface", ""),
                    "normalized": residual.get("normalized", ""),
                    "unit_refs": list(item.get("source_unit_refs", ())),
                    "residual_class": "unknown_form" if unknown else "known_form_unassigned",
                    "grounding_status": "unknown" if unknown else "lexically_known",
                    "semantic_ref": residual.get("semantic_ref"),
                    "role_hypotheses": list(item.get("candidate_roles", ())),
                    "composition_gap": item,
                    "priority": 2.0 if item.get("gap_kind") == "missing_proposition_link" else 1.0,
                })
            trace = {
                "reason": "recursive_semantic_graph_unsettled",
                "structured_prediction": True,
                "clauses": [settle_trace],
                "n_best": True,
                "resolved_form_lattice": resolved.as_dict(),
                "delexicalized": delex,
                "grounded_anchors": anchors,
                "unknown_form_evidence": gap_evidence,
                "background_learning_evidence": [],
                "pending_learning_probe": [],
                "skipped_clauses": [],
                "interpretation_coverage": None,
                "partial_packet": None,
                "interpretation_assessment": {
                    "status": "partial",
                    "grounded_refs": list(grounded_refs),
                    "open_variables": [],
                    "unresolved_evidence": gap_evidence,
                    "background_learning_evidence": [],
                    "coverage": {},
                    "blockers": sorted({item["composition_gap"]["gap_kind"] for item in gap_evidence}),
                },
                "composition": dict(composition_result.diagnostics),
                "composition_gaps": [gap.as_dict() for gap in composition_result.gaps],
                "state_projection_refs": sorted((state_projections or {}).keys()),
                "side_effect_free": True,
                "candidate_count": len(candidates),
            }
            return None, [], uses, trace

'''
    text = insert_once(text, marker, gap_branch, "interpreter graph-level gap branch", after=False)
    text = text.replace(
        '                "candidate_count": len(candidates),\n            }\n            return packet, news, uses, trace\n',
        '                "candidate_count": len(candidates),\n                "composition": dict(composition_result.diagnostics) if composition_result else {},\n            }\n            return packet, news, uses, trace\n',
        1,
    )
    text = replace_once(
        text,
        '                "learning_contract_ref": str(contract_ref),\n                "probe_query": dict(query) if query else None,\n',
        '                "learning_contract_ref": str(contract_ref),\n                "query_kind": str(dict(query.get("qualifiers", {}) if isinstance(query, dict) else {}).get("query_kind") or ""),\n                "probe_query": dict(query) if query else None,\n',
        "interpreter learning-probe query kind",
    )
    text = text.replace(
        "if composition_result is not None and composition_result.gaps:",
        "if composition_result is not None and composition_result.gaps and not candidates:",
    )
    return text


def patch_cognition(text: str) -> str:
    text = text.replace("    describe_target: str | None\n", "    describe_target: Any | None\n", 1)
    return text


def patch_store(text: str) -> str:
    text = insert_once(
        text, "from cemm.authority import load_documents, validate_documents\n",
        "from cemm.semantic_contributions import SemanticAffordanceIndex\n",
        "store semantic frame import", after=True,
    )
    marker = "    def validate_app(self, operator, args):\n"
    helpers = '''    @staticmethod
    def _application_predicate_ref(operator, args):
        role = {
            "op:event": "role:type",
            "op:relation": "role:relation",
            "op:state": "role:dimension",
            "op:type": "role:class",
        }.get(str(operator))
        value = args.get(role) if role else None
        return value if isinstance(value, str) and not value.startswith(("?", "!")) else None

    def _frame_allows_app(self, operator, role_ref, args):
        predicate = self._application_predicate_ref(operator, args)
        if not predicate:
            return False
        profiles = SemanticAffordanceIndex(
            self, self.generation, max_profiles_per_target=4
        ).profiles_for(predicate)
        return any(
            profile.metadata.get("kernel_operator_ref") == operator
            and profile.metadata.get("proposition_taking")
            and any(role.role_ref == role_ref and "app" in role.filler_kinds for role in profile.roles)
            for profile in profiles
        )

'''
    text = insert_once(text, marker, helpers, "store app-valued frame helpers", after=False)
    old = '''        for role, value in args.items():
            if role not in specs:
                raise ValueError(f"{operator} disallows {role}")
            self._validate_filler(role, value, specs[role])
'''
    new = '''        for role, value in args.items():
            if role not in specs:
                raise ValueError(f"{operator} disallows {role}")
            try:
                self._validate_filler(role, value, specs[role])
            except ValueError:
                if not (
                    isinstance(value, dict)
                    and set(value) == {"app"}
                    and self._frame_allows_app(operator, role, args)
                    and self.db.execute(
                        "SELECT 1 FROM applications WHERE app_ref=?", (str(value["app"]),)
                    ).fetchone()
                ):
                    raise
'''
    text = replace_once(text, old, new, "store reviewed app filler override")
    return text


def patch_runtime(text: str) -> str:
    text = insert_once(
        text, "from cemm.learning_plans import (\n",
        "from cemm.semantic_description import SemanticDescriptionEngine\n"
        "from cemm.proof import ProofEngine, VerifiedSemanticFocus\n",
        "runtime description/proof imports", after=False,
    )
    text = text.replace(
        "        self.dialogue_state = DialogueState()\n",
        "        self.dialogue_state = DialogueState(max_verified_focus=self.config.dialogue_max_verified_focus)\n",
        1,
    )
    marker = "        self.retriever = SemanticRetriever(self.s, self.config, generation)\n"
    text = insert_once(
        text, marker,
        "        self.description_engine = SemanticDescriptionEngine(\n"
        "            self.s, self.config, int(self.runtime_attestation[\"authority_generation\"])\n"
        "        )\n"
        "        self.proof_engine = ProofEngine(\n"
        "            self.s, self.config, int(self.runtime_attestation[\"authority_generation\"])\n"
        "        )\n",
        "runtime exact description/proof services", after=True,
    )
    # Graph-level frontier grouping, preserving lexical learning only for true unknowns.
    start = "    @staticmethod\n    def _frontiers(trace, cycle_ref):\n"
    end = "    def _materialize(self, packet, news, generation, seed):\n"
    method = '''    @staticmethod
    def _frontiers(trace, cycle_ref):
        output = []
        seen_gaps = set()
        for item in trace.get("unknown_form_evidence", ()):
            gap = item.get("composition_gap") if isinstance(item, dict) else None
            if isinstance(gap, dict):
                gap_ref = str(gap.get("gap_ref") or "")
                if gap_ref in seen_gaps:
                    continue
                seen_gaps.add(gap_ref)
                kind = str(gap.get("gap_kind") or "known_form_composition_gap")
                unknown_only = bool(gap.get("unknown_unit_refs")) and not gap.get("known_unit_refs")
                blocks = ("interpretation", "answer", "lexical_learning") if unknown_only else ("interpretation", "answer")
                output.append(LearningFrontier.create(
                    "unknown_form" if unknown_only else kind,
                    ({**dict(item), "composition_gap": dict(gap)},),
                    target_ref=item.get("semantic_ref"),
                    blocks=blocks,
                    cycle_ref=cycle_ref,
                ))
                continue
            residual_class = str(item.get("residual_class") or "unknown_form")
            grounding_status = str(item.get("grounding_status") or "unknown")
            semantic_ref = item.get("semantic_ref") or item.get("target_ref")
            if residual_class == "unknown_form":
                kind, blocks = "unknown_form", ("interpretation", "answer", "lexical_learning")
            elif grounding_status == "grounded" and semantic_ref:
                kind, blocks = "grounded_composition_gap", ("interpretation", "answer")
            else:
                kind, blocks = "known_form_composition_gap", ("interpretation", "answer")
            output.append(LearningFrontier.create(
                kind, (dict(item),), target_ref=str(semantic_ref) if semantic_ref else None,
                blocks=blocks, cycle_ref=cycle_ref,
            ))
        for skipped in trace.get("skipped_clauses", ()):
            if skipped.get("reason") != "unknown_form":
                output.append(LearningFrontier.create(
                    skipped.get("reason", "unresolved_clause"), (dict(skipped),),
                    blocks=("interpretation", "answer"), cycle_ref=cycle_ref,
                ))
        if not output and trace.get("reason"):
            output.append(LearningFrontier.create(
                trace["reason"], ({"reason": trace["reason"], "coverage": trace.get("interpretation_coverage"),
                                   "partial_structure": trace.get("partial_packet")},),
                blocks=("interpretation", "answer"), cycle_ref=cycle_ref,
            ))
        return tuple(output)

    def _resolve_candidate_application_refs(self, packet):
        applications = self._packet_applications(packet)
        if not applications:
            return packet
        by_local = {
            str(item.get("application_ref")): item
            for item in applications if item.get("application_ref")
        }
        if not by_local:
            return packet
        if len(by_local) != sum(1 for item in applications if item.get("application_ref")):
            raise ValueError("duplicate candidate-local application refs")
        resolved = {}
        pending = set(by_local)
        while pending:
            progressed = False
            for local_ref in tuple(sorted(pending)):
                application = by_local[local_ref]
                args = {}
                blocked = False
                for role, value in application.get("args", {}).items():
                    if isinstance(value, dict) and set(value) == {"app"}:
                        child = str(value["app"])
                        if child in by_local and child not in resolved:
                            blocked = True
                            break
                        args[role] = {"app": resolved.get(child, child)}
                    else:
                        args[role] = value
                if blocked:
                    continue
                resolved[local_ref] = self.s.app_signature(application["operator"], args)
                application["args"] = args
                application["application_ref"] = resolved[local_ref]
                pending.remove(local_ref)
                progressed = True
            if not progressed:
                raise ValueError("candidate-local application graph is cyclic or incomplete")
        # Parent app bindings now reference exact child app signatures. Child-first
        # order is required so store validation cannot observe a dangling app ref.
        ordered = []
        remaining = list(applications)
        inserted = set()
        while remaining:
            progress = False
            for item in tuple(remaining):
                children = {
                    str(value["app"]) for value in item.get("args", {}).values()
                    if isinstance(value, dict) and set(value) == {"app"}
                }
                local_children = {child for child in children if child in set(resolved.values())}
                external_children = children - local_children
                if all(self.s.db.execute(
                    "SELECT 1 FROM applications WHERE app_ref=?", (child,)
                ).fetchone() for child in external_children) and local_children.issubset(inserted):
                    ordered.append(item); inserted.add(str(item.get("application_ref")))
                    remaining.remove(item); progress = True
            if not progress:
                raise ValueError("materialized application graph is cyclic")
        if packet.get("query"):
            packet["query"]["restrictions"] = ordered
        elif packet.get("directive"):
            packet["directive"]["content"] = ordered
        else:
            packet["apps"] = ordered
        return packet

'''
    text = replace_region(text, start, end, method, "runtime frontier/materialization helpers")
    old = '''        for application in self._packet_applications(output):
            application["args"] = {role: convert(value) for role, value in application["args"].items()}
'''
    new = '''        for application in self._packet_applications(output):
            application["args"] = {role: convert(value) for role, value in application["args"].items()}
        output = self._resolve_candidate_application_refs(output)
'''
    text = replace_once(text, old, new, "runtime candidate app materialization")
    # Replace Stage-10 query/description block.
    start = "        runtime_facts = cycle.self_runtime_view.operational_snapshot.semantic_facts()\n"
    end = "        stages.add(Stage.QUERY_EXPLAIN, counts={"
    prefix = '''        runtime_facts = cycle.self_runtime_view.operational_snapshot.semantic_facts()
        query_result = None
        retrieval = None
        description_result = None
        proof_bundle = None
        facts = list(runtime_facts)
        by_ref = {fact.ref: fact for fact in facts}
        workspace_trace = {"selected": [], "top_k": self.config.workspace_top_k}
        scoped_epistemic = None
        describe_request = getattr(act, "describe_target", None) if act else None
        if act and act.force == FORCE_QUERY and act.query:
            query_kind = str(dict(act.query.qualifiers or {}).get("query_kind") or "")
            if (
                isinstance(describe_request, dict)
                or query_kind == "embedded_proposition_query"
            ):
                self._require_resources(
                    cycle, Stage.QUERY_EXPLAIN, ("resource:semantic_store",)
                )
            if isinstance(describe_request, dict) and describe_request.get("description_kind") == "semantic_target":
                request = self.description_engine.request(
                    str(describe_request["target_ref"]),
                    facets=tuple(describe_request.get("requested_facets", ())) or (),
                    provenance={"query_ref": act.query.query_ref, "act_ref": act.act_ref},
                )
                description_result = self.description_engine.describe(request)
                facts = list(description_result.facts) + list(runtime_facts)
                by_ref = {fact.ref: fact for fact in facts}
                binding = QueryBinding(
                    {"?description_target": request.target_ref},
                    tuple(fact.ref for fact in description_result.facts),
                )
                query_result = QueryResult(
                    act.query.query_ref,
                    "answered" if description_result.target_kind != "unknown" else "unknown",
                    (binding,) if description_result.target_kind != "unknown" else (),
                    1.0 if description_result.target_kind != "unknown" else 0.0,
                    len(description_result.facts), 0, (), (),
                    tuple(x.frontier_ref for x in frontiers),
                    {
                        **dict(act.query.qualifiers or {}),
                        "query_kind": "semantic_description",
                        "target_ref": request.target_ref,
                        "description_result": description_result.as_dict(),
                    },
                )
            elif isinstance(describe_request, dict) and describe_request.get("description_kind") == "epistemic_provenance":
                raw_focus = cycle.participant_frame.dialogue_context.get("verified_semantic_focus")
                focus = VerifiedSemanticFocus.from_dict(raw_focus) if isinstance(raw_focus, dict) else None
                if focus is not None:
                    proof_bundle = self.proof_engine.explain_focus(
                        focus,
                        proof_lookup={focus.proof_ref: self.dialogue_state.proof_bundle(focus.proof_ref)},
                    )
                else:
                    proof_bundle = self.proof_engine.explain_focus(VerifiedSemanticFocus.create(
                        focus_kind="unresolved", response_ref="response:none",
                        authority_generation=int(self.runtime_attestation["authority_generation"]),
                        world_revision=self.s.revisions()["world_revision"],
                    ))
                query_result = QueryResult(
                    act.query.query_ref,
                    "answered" if proof_bundle.completeness not in {"unsupported", "stale"} else "unknown",
                    (), 1.0 if proof_bundle.completeness not in {"unsupported", "stale"} else 0.0,
                    proof_bundle.support_count, proof_bundle.opposition_count, (), (),
                    tuple(x.frontier_ref for x in frontiers),
                    {
                        **dict(act.query.qualifiers or {}),
                        "query_kind": "epistemic_provenance",
                        "proof_bundle": proof_bundle.as_dict(),
                    },
                )
            elif query_kind == "embedded_proposition_query" and dict(act.query.qualifiers or {}).get("evaluation_kind") == "answerability":
                embedded = tuple(dict(act.query.qualifiers or {}).get("embedded_proposition_graphs", ()))
                descriptions = []
                for graph in embedded:
                    request_data = dict(graph.get("provenance", {}).get("describe_request", {}) or {})
                    if request_data.get("target_ref"):
                        req = self.description_engine.request(str(request_data["target_ref"]), provenance={"outer_query_ref": act.query.query_ref})
                        descriptions.append(self.description_engine.describe(req))
                answerable = bool(descriptions) and all(item.target_kind != "unknown" for item in descriptions)
                description_result = descriptions[0] if len(descriptions) == 1 else None
                proof_refs = tuple(fact.ref for item in descriptions for fact in item.facts)
                query_result = QueryResult(
                    act.query.query_ref, "supported" if answerable else "contradicted",
                    (), 1.0, int(answerable), int(not answerable), (), (),
                    tuple(x.frontier_ref for x in frontiers),
                    {**dict(act.query.qualifiers or {}), "answer_mode": "boolean"},
                )
                facts = [fact for item in descriptions for fact in item.facts] + list(runtime_facts)
                by_ref = {fact.ref: fact for fact in facts}
            else:
                self._require_resources(
                    cycle, Stage.QUERY_EXPLAIN,
                    ("resource:inference_engine", "resource:semantic_store"),
                )
                retrieval = self.retriever.retrieve(act.query.restrictions, salient_refs=grounded_refs)
                facts, by_ref = self.inf.closure(seed_facts=retrieval.facts, rules=retrieval.rules, extra=runtime_facts)
                query_result = self.inf.execute_query(
                    act.query, facts, by_ref,
                    blocking_frontiers=tuple(x.frontier_ref for x in frontiers),
                )
                proof_refs = sorted({ref for binding in query_result.bindings for ref in binding.proof_refs})
                _, workspace_trace = self.workspace.build(
                    facts, act.query.as_dict(), proof_refs, cycle_turn=self._cycle_counter,
                )
                scoped_epistemic = ScopedEpistemicAssessment(
                    query_result.query_ref, query_result.status, tuple(proof_refs), (),
                    query_result.unresolved_variables, query_result.coverage,
                )
        elif act and act.force == FORCE_DESCRIPTION and act.describe_target:
            self._require_resources(
                cycle, Stage.QUERY_EXPLAIN, ("resource:semantic_store",)
            )
            target = act.describe_target.get("target_ref") if isinstance(act.describe_target, dict) else act.describe_target
            request = self.description_engine.request(str(target), provenance={"act_ref": act.act_ref})
            description_result = self.description_engine.describe(request)
            facts = list(description_result.facts) + list(runtime_facts)
            by_ref = {fact.ref: fact for fact in facts}
            binding = QueryBinding({"?description_target": request.target_ref}, tuple(fact.ref for fact in description_result.facts))
            query_result = QueryResult(
                stable("description-query", request.target_ref),
                "answered" if description_result.target_kind != "unknown" else "unknown",
                (binding,) if description_result.target_kind != "unknown" else (),
                1.0 if description_result.target_kind != "unknown" else 0.0,
                len(description_result.facts), 0, (), (), tuple(x.frontier_ref for x in frontiers),
                {"query_kind": "semantic_description", "target_ref": request.target_ref,
                 "description_result": description_result.as_dict()},
            )
            scoped_epistemic = ScopedEpistemicAssessment(
                query_result.query_ref, query_result.status,
                tuple(fact.ref for fact in description_result.facts), (), (), query_result.coverage,
            )
'''
    text = replace_region(text, start, end, prefix, "runtime Stage-10 exact description/proof")
    # Record verified focus before common-ground persistence.
    marker = "        common_ground = None\n"
    focus = '''        if verified and query_result is not None:
            if proof_bundle is None:
                proof_bundle = self.proof_engine.for_query_result(
                    query_result,
                    operational_snapshot_ref=(
                        cycle.self_runtime_view.operational_snapshot.snapshot_ref
                        if dict(query_result.qualifiers or {}).get("query_kind") == "operational_condition_query"
                        else None
                    ),
                )
            focus_targets = {
                str(value) for binding in query_result.bindings
                for value in binding.values.values()
                if isinstance(value, str) and not value.startswith(("?", "!"))
            }
            focus_targets.update(str(ref) for ref in grounded_refs)
            verified_focus = VerifiedSemanticFocus.create(
                focus_kind="query_result",
                proposition_ref=dict((packet or {}).get("qualifiers", {})).get("proposition_ref"),
                query_ref=query_result.query_ref,
                response_ref=response_csir.response_ref,
                target_refs=tuple(sorted(focus_targets)),
                bindings=(binding.values for binding in query_result.bindings),
                proof_ref=proof_bundle.proof_ref,
                recorded_turn=self._cycle_counter,
                authority_generation=int(self.runtime_attestation["authority_generation"]),
                world_revision=self.s.revisions()["world_revision"],
            )
            self.dialogue_state.record_verified_focus(verified_focus, proof_bundle)
        else:
            verified_focus = None

'''
    # second occurrence is main flow; replace last by rsplit
    if focus not in text:
        idx = text.rfind(marker)
        if idx < 0: raise RuntimeError("runtime common-ground marker absent")
        text = text[:idx] + focus + text[idx:]
    # Include focus in common-ground payload and result.
    text = replace_last_once(
        text,
        '                        "obligation_ref": response_csir.obligation_ref,\n                        "pending_learning": (\n',
        '                        "obligation_ref": response_csir.obligation_ref,\n                        "verified_semantic_focus": verified_focus.as_dict() if verified_focus else None,\n                        "proof_bundle": proof_bundle.as_dict() if proof_bundle else None,\n                        "pending_learning": (\n',
        "runtime main common-ground proof payload",
    )
    text = replace_last_once(
        text,
        '            "query_result": query_result.as_dict() if query_result else None,\n',
        '            "query_result": query_result.as_dict() if query_result else None,\n'
        '            "description_result": description_result.as_dict() if description_result else None,\n'
        '            "proof_bundle": proof_bundle.as_dict() if proof_bundle else None,\n'
        '            "verified_semantic_focus": verified_focus.as_dict() if verified_focus else None,\n',
        "runtime result proof payload",
    )
    text = replace_once(
        text,
        '                query_kind = str(dict(query_result.qualifiers or {}).get("query_kind") or "")\n',
        '                query_kind = str(probe.get("query_kind") or dict(raw_query.get("qualifiers", {}) or {}).get("query_kind") or "")\n',
        "runtime learning-plan query-kind provenance",
    )
    return text


def patch_settler(text: str) -> str:
    """Calibrate evidence scores while preserving strict polysemy margins."""
    if "settler_score_temperature" in text:
        return text
    old = '        maximum = max(item["base"] for item in values)\n        for item in values:\n            item["energy"] = item["base"] - maximum + 0.35\n        for _ in range(self.config.settler_rounds):\n            normalizer = sum(math.exp(item["energy"]) for item in values)\n            probabilities = [math.exp(item["energy"]) / normalizer for item in values]\n            for index, item in enumerate(values):\n                item["energy"] = (\n                    item["base"] - maximum + 0.35\n                ) - 0.28 * (1 - probabilities[index])\n'
    new = '        maximum = max(item["base"] for item in values)\n        temperature = float(self.config.settler_score_temperature)\n        for item in values:\n            item["energy"] = (item["base"] - maximum) / temperature + 0.35\n        for _ in range(self.config.settler_rounds):\n            normalizer = sum(math.exp(item["energy"]) for item in values)\n            probabilities = [math.exp(item["energy"]) / normalizer for item in values]\n            for index, item in enumerate(values):\n                item["energy"] = (\n                    (item["base"] - maximum) / temperature + 0.35\n                ) - 0.28 * (1 - probabilities[index])\n'
    text = replace_once(text, old, new, "settler score calibration")
    old = '        margin = top["posterior"] - (\n            values[1]["posterior"] if len(values) > 1 else 0.0\n        )\n        settled = len(values) == 1 or (\n            top["posterior"] >= self.config.settler_posterior_threshold\n            and margin >= self.config.settler_margin_threshold\n        )\n'
    new = '        margin = top["posterior"] - (\n            values[1]["posterior"] if len(values) > 1 else 0.0\n        )\n        score_margin = top["base"] - (\n            values[1]["base"] if len(values) > 1 else 0.0\n        )\n        settled = len(values) == 1 or (\n            top["posterior"] >= self.config.settler_posterior_threshold\n            and margin >= self.config.settler_margin_threshold\n            and score_margin >= self.config.settler_score_margin_threshold\n        )\n'
    text = replace_once(text, old, new, "settler evidence margin")
    return replace_once(text, '            "margin": margin,\n            "selected_candidate_ref":', '            "margin": margin,\n            "score_margin": score_margin,\n            "selected_candidate_ref":', "settler score margin trace")


def patch_response(text: str) -> str:
    if 'query_qualifiers.get("query_kind") == "semantic_description"' not in text:
        text = text.replace(
            '            "report_operational_condition",\n',
            '            "report_operational_condition",\n            "describe_semantic_target",\n            "explain_evidence_provenance",\n',
            1,
        )
    marker = '''            if query_qualifiers.get("query_kind") == "operational_condition_query":
'''
    branch = '''            if query_qualifiers.get("query_kind") == "semantic_description":
                result = dict(query_qualifiers.get("description_result", {}) or {})
                action = "describe_semantic_target"
                target_ref = result.get("target_ref") or query_qualifiers.get("target_ref")
                facts = tuple(
                    facts_by_ref[ref]
                    for ref in sorted({item.get("ref") for item in result.get("facts", ()) if item.get("ref")})
                    if ref in facts_by_ref
                )
                facet_names = [key for key, refs in dict(result.get("fact_facets", {})).items() if refs]
                qualifiers = {
                    **common,
                    "description_result_ref": result.get("result_ref"),
                    "description_completeness": result.get("completeness"),
                    "target_kind": result.get("target_kind"),
                    "preferred_surface": result.get("preferred_surface"),
                    "description_summary": ", ".join(facet_names),
                    "description_fact_refs": [item.get("ref") for item in result.get("facts", ()) if item.get("ref")],
                    "description_source_refs": list(result.get("source_refs", ())),
                    "missing_facets": list(result.get("missing_facets", ())),
                }
                reason = "semantic_target_description"
            elif query_qualifiers.get("query_kind") == "epistemic_provenance":
                proof = dict(query_qualifiers.get("proof_bundle", {}) or {})
                action = "explain_evidence_provenance"
                target_ref = None
                sources = list(proof.get("source_refs", ()))
                authority = list(dict(proof.get("provenance", {})).get("authority_statuses", ()))
                if audience_ref in sources:
                    basis = "user_report"
                elif proof.get("operational_snapshot_refs"):
                    basis = "operational_observation"
                elif proof.get("inference_receipt_refs"):
                    basis = "inference"
                elif "reviewed" in authority or "promoted" in authority or "seed" in sources:
                    basis = "reviewed_authority"
                elif proof.get("fact_refs") or proof.get("claim_refs"):
                    basis = "stored_evidence"
                else:
                    basis = "unsupported"
                qualifiers = {
                    **common,
                    "proof_ref": proof.get("proof_ref"),
                    "proof_basis": basis,
                    "proof_completeness": proof.get("completeness"),
                    "proof_fact_refs": list(proof.get("fact_refs", ())),
                    "proof_claim_refs": list(proof.get("claim_refs", ())),
                    "proof_source_refs": sources,
                    "proof_inference_refs": list(proof.get("inference_receipt_refs", ())),
                    "proof_snapshot_refs": list(proof.get("operational_snapshot_refs", ())),
                }
                reason = "epistemic_provenance_explanation"
            elif query_qualifiers.get("query_kind") == "operational_condition_query":
'''
    if 'query_qualifiers.get("query_kind") == "semantic_description"' not in text:
        text = replace_once(text, marker, branch, "response semantic description/proof branches")
    # Structural composition gaps never become lexical teaching requests.
    old = '''            elif surface or frontier.target_ref:
                action = "request_targeted_clarification"
            else:
                action = "request_generic_clarification"
'''
    new = '''            elif evidence.get("composition_gap"):
                action = "report_structural_composition_gap"
            elif surface or frontier.target_ref:
                action = "request_targeted_clarification"
            else:
                action = "request_generic_clarification"
'''
    if 'action = "report_structural_composition_gap"' not in text:
        text = replace_once(text, old, new, "response structural gap action")
        text = text.replace(
            '                "frontier_ref": frontier.frontier_ref,\n',
            '                "frontier_ref": frontier.frontier_ref,\n'
            '                "composition_gap": dict(evidence.get("composition_gap", {}) or {}),\n'
            '                "gap_kind": dict(evidence.get("composition_gap", {}) or {}).get("gap_kind"),\n',
            1,
        )
    return text


def patch_reference(text: str) -> str:
    # Match arbitrary semantic qualifier conditions declared by response grammar.
    old = '''            required_qualifiers = dict(when.get("qualifiers", {}) or {})
            actual_qualifiers = dict(getattr(response, "qualifiers", {}) or {})
            if any(actual_qualifiers.get(key) != value for key, value in required_qualifiers.items()):
                continue
            specificity = sum(value is not None for key, value in when.items() if key != "qualifiers") + len(required_qualifiers)
'''
    new = '''            required_qualifiers = dict(when.get("qualifiers", {}) or {})
            actual_qualifiers = dict(getattr(response, "qualifiers", {}) or {})
            semantic_conditions = {
                key: value for key, value in when.items()
                if key not in {"action", "query_kind", "has_bindings", "has_facts", "qualifiers"}
            }
            def condition_matches(actual, expected):
                if isinstance(expected, Mapping) and "any_of" in expected:
                    return actual in set(expected["any_of"])
                if isinstance(expected, Mapping) and "not" in expected:
                    return actual != expected["not"]
                return actual == expected
            if any(not condition_matches(actual_qualifiers.get(key), value) for key, value in required_qualifiers.items()):
                continue
            if any(not condition_matches(actual_qualifiers.get(key), value) for key, value in semantic_conditions.items()):
                continue
            specificity = sum(value is not None for key, value in when.items() if key != "qualifiers") + len(required_qualifiers)
'''
    text = replace_once(text, old, new, "reference generic qualifier conditions")
    marker = '''        if action == "explain_surface_choice":
'''
    contracts = '''        if action == "describe_semantic_target":
            base = {
                "query_ref", "query_kind", "description_result_ref",
                "description_completeness",
            }
            completeness = qualifiers.get("description_completeness")
            if completeness == "identity_only":
                base.add("target_kind")
            elif completeness in {"partial_structure", "sufficient_structure"}:
                base.update({"target_kind", "description_summary"})
            elif completeness == "conflicting_structure":
                base.add("target_ref")
            return frozenset(base)
        if action == "explain_evidence_provenance":
            return frozenset({
                "query_ref", "query_kind", "proof_ref", "proof_basis",
                "proof_completeness",
            })
        if action == "report_structural_composition_gap":
            return frozenset({"frontier_ref", "gap_kind"})
'''
    text = insert_once(text, marker, contracts, "reference new response contracts", after=False)
    return text


def patch_semantic_coverage(text: str) -> str:
    replacements = (
        ("Fail-closed semantic coverage ABI v6.", "Fail-closed semantic coverage ABI v7."),
        ("V6 preserves grounding provenance", "V7 preserves grounding provenance"),
        ("COVERAGE_ABI_VERSION = 6", "COVERAGE_ABI_VERSION = 7"),
        ("residual-span-v6", "residual-span-v7"),
        ("coverage-diagnostic-match-seed-v6", "coverage-diagnostic-match-seed-v7"),
        ("coverage-hypothesis-v6", "coverage-hypothesis-v7"),
        ("coverage-match-seed-v6", "coverage-match-seed-v7"),
        ("coverage-seed-v6", "coverage-seed-v7"),
        ("interpretation-coverage-v6", "interpretation-coverage-v7"),
    )
    for before, after in replacements:
        if before in text:
            text = text.replace(before, after)
    if "COVERAGE_ABI_VERSION = 7" not in text:
        raise RuntimeError("semantic coverage ABI-7 constant is absent after rewrite")
    if any(token in text for token in (
        "residual-span-v6", "coverage-seed-v6", "interpretation-coverage-v6"
    )):
        raise RuntimeError("active semantic coverage still contains ABI-6 identities")
    return text


def patch_semantic_operational_validator(text: str) -> str:
    text = text.replace("generate_en_form_pack_v6", "generate_en_form_pack_v7")
    text = text.replace("ABI_VERSION = 6", "ABI_VERSION = 7")
    text = text.replace("v6 graph matcher", "v7 recursive graph matcher")
    text = text.replace('    "desire_knowledge_designation_query",\n', "")
    if "generate_en_form_pack_v6" in text:
        raise RuntimeError("semantic-operational validator still imports the retired v6 form generator")
    if "generate_en_form_pack_v7" not in text:
        raise RuntimeError("semantic-operational validator has no ABI-7 form generator import")
    if "ABI_VERSION = 7" not in text:
        raise RuntimeError("semantic-operational validator ABI was not migrated to 7")
    if "desire_knowledge_designation_query" in text:
        raise RuntimeError("semantic-operational validator still requires the retired sentence-shaped family")
    return text


def patch_web_demo(text: str) -> str:
    return text.replace("assert_atomic_graph_activation", "assert_native_semantic_activation")


def patch_docs(text: str) -> str:
    marker = "## Recursive Atomic Semantic Composition ABI"
    if marker in text:
        return text
    return text.rstrip() + '''

## Recursive Atomic Semantic Composition ABI

Stage 5 owns one bounded bottom-up composition chart. Form units may become
transient PropositionGraph ABI 2 units and compose into larger graphs. Graphlets
are never persisted and never create a sixth operator. Candidate-local app-valued
roles are admitted only by reviewed proposition-taking frames and are flattened
child-first before Stage 13.

Semantic description and epistemic explanation extend the exact Stage-10 query
path. Descriptions contain only indexed stored facts. Proof explanations contain
only exact application, claim, occurrence, source, inference, commit or runtime
snapshot refs. Stage 21 records bounded verified semantic focus after realization
verification; surface wording is never semantic authority.

Activation requires Coverage/Form ABI 7, Atomic Composition ABI 1,
PropositionGraph ABI 2, Description ABI 1 and Proof Bundle ABI 1. The obsolete
sentence-shaped embedded proposition family and one-pass Stage-5 fallback are
forbidden.
'''


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    args = parser.parse_args()
    repo = args.repo.resolve()
    if not (repo / "cemm/runtime.py").is_file():
        raise SystemExit(f"not a CEMM checkout: {repo}")
    changes = []
    copies = (
        ("cemm/semantic_contributions.py", False),
        ("cemm/learning_plans.py", False),
        ("cemm/propositions.py", False),
        ("cemm/composition.py", False),
        ("cemm/semantic_description.py", False),
        ("cemm/proof.py", False),
        ("cemm/native_semantic_validation.py", False),
        ("cemm/activation.py", False),
        ("cemm/atomic_graph.py", True),
        ("cemm/form_algebra.py", True),
        ("cemm/compiler.py", True),
        ("cemm/config.py", True),
        ("cemm/dialogue.py", True),
        ("cemm/web_demo.py", True),
    )
    for relative, replacement in copies:
        changes.append(copy_exact(payload(relative, replacement), repo / relative))
    transforms = (
        ("cemm/forms.py", patch_forms),
        ("cemm/interpreter.py", patch_interpreter),
        ("cemm/cognition.py", patch_cognition),
        ("cemm/store.py", patch_store),
        ("cemm/runtime.py", patch_runtime),
        ("cemm/settler.py", patch_settler),
        ("cemm/response.py", patch_response),
        ("cemm/reference.py", patch_reference),
        ("cemm/semantic_coverage.py", patch_semantic_coverage),
        ("tools/validate_semantic_operational_contract.py", patch_semantic_operational_validator),
        ("CEMM_RUNTIME_IMPLEMENTATION_CONTRACT.md", patch_docs),
        ("runtime-core-loop.md", patch_docs),
    )
    for relative, transform in transforms:
        changes.append(rewrite(repo / relative, transform))
    forbidden = []
    for relative in ("cemm/interpreter.py", "cemm/runtime.py", "cemm/response.py"):
        source = (repo / relative).read_text(encoding="utf-8")
        if "desire_knowledge_designation_query" in source or "assert_atomic_graph_activation" in source:
            forbidden.append(relative)
    if forbidden:
        raise RuntimeError(f"superseded semantic paths survived rewrite: {forbidden}")
    print(json.dumps({"source_rewrite_version": SOURCE_REWRITE_VERSION, "changes": changes}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
