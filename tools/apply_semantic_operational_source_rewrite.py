#!/usr/bin/env python3
"""Exact integration rewrite for the reviewed CEMM v1 branch preimage.

Principal semantic modules are overlaid as complete files.  This script owns
only branch-local integration points in runtime/config/cognition/compiler/
transitions/AGENTS.  Every edit is exact-count checked and idempotent.  There is
no drift mode and no best-effort rewrite.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import re
import shutil
import tempfile
from pathlib import Path


class RewriteError(RuntimeError):
    pass


REWRITE_VERSION = "3.1.3"
REWRITE_MARKERS = {
    "AGENTS.md": "<!-- CEMM_SOURCE_REWRITE:AGENTS:v3.1.3 -->",
    "cemm/config.py": "# CEMM_SOURCE_REWRITE:config:v3.1.3",
    "cemm/runtime.py": "# CEMM_SOURCE_REWRITE:runtime:v3.1.3",
    "cemm/cognition.py": "# CEMM_SOURCE_REWRITE:cognition:v3.1.3",
    "cemm/compiler.py": "# CEMM_SOURCE_REWRITE:compiler:v3.1.3",
    "cemm/transitions.py": "# CEMM_SOURCE_REWRITE:transitions:v3.1.3",
}


def _begin_file_rewrite(text: str, marker: str, *, label: str) -> str | None:
    """Return source for a first rewrite, or ``None`` for an already sealed file.

    A marker is written only after every transformation for that file succeeds.
    Therefore a sealed file is the exact output of one complete rewrite pass and
    must never be sent through the anchor engine again.  Duplicate markers are an
    integrity fault rather than an idempotency shortcut.
    """
    count = text.count(marker)
    if count == 1:
        return None
    if count != 0:
        raise RewriteError(f"{label}: expected zero or one rewrite seal, found {count}")
    return text


def _seal_file_rewrite(text: str, marker: str) -> str:
    if marker in text:
        raise RewriteError("rewrite seal appeared before file transformation completed")
    return text.rstrip() + "\n\n" + marker + "\n"


def replace_once(text: str, old: str, new: str, *, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RewriteError(f"{label}: expected one source anchor, found {count}")
    return text.replace(old, new, 1)


def replace_count(text: str, old: str, new: str, *, count: int, label: str) -> str:
    found = text.count(old)
    if found != count:
        raise RewriteError(f"{label}: expected {count} source anchors, found {found}")
    return text.replace(old, new)


def insert_after_once(text: str, anchor: str, insertion: str, *, label: str) -> str:
    count = text.count(anchor)
    if count != 1:
        raise RewriteError(f"{label}: expected one insertion anchor, found {count}")
    return text.replace(anchor, anchor + insertion, 1)


def regex_replace_once(text: str, pattern: str, replacement: str, *, label: str) -> str:
    compiled = re.compile(pattern, re.MULTILINE | re.DOTALL)
    matches = list(compiled.finditer(text))
    if len(matches) != 1:
        raise RewriteError(f"{label}: expected one regex anchor, found {len(matches)}")
    return compiled.sub(replacement, text, count=1)


def patch_config(path: Path) -> None:
    marker = REWRITE_MARKERS["cemm/config.py"]
    text = path.read_text(encoding="utf-8")
    source = _begin_file_rewrite(text, marker, label="config rewrite seal")
    if source is None:
        return
    text = source
    text = replace_once(
        text,
        "    capability_unknown_score: float = 0.0\n",
        "",
        label="remove numeric unknown capability policy",
    )
    path.write_text(_seal_file_rewrite(text, marker), encoding="utf-8")


def patch_runtime(path: Path) -> None:
    marker = REWRITE_MARKERS["cemm/runtime.py"]
    text = path.read_text(encoding="utf-8")
    source = _begin_file_rewrite(text, marker, label="runtime rewrite seal")
    if source is None:
        return
    text = source
    text = insert_after_once(
        text,
        "import json\n",
        "import sqlite3\n",
        label="runtime sqlite probe import",
    )
    text = insert_after_once(
        text,
        "from cemm.config import Config\n",
        "from cemm.dialogue import DialogueState\n",
        label="runtime dialogue import",
    )
    text = insert_after_once(
        text,
        "from cemm.model import AmbiguousReferent, canonical, now, stable\n",
        "from cemm.operational import (\n"
        "    CANONICAL_RUNTIME_RESOURCES,\n"
        "    OperationalInvariantChecker,\n"
        "    OperationalProviderContractError,\n"
        "    OperationalUsageLedger,\n"
        "    RuntimeServiceRegistry,\n"
        "    declared_operation_resources,\n"
        ")\n",
        label="runtime operational imports",
    )
    text = insert_after_once(
        text,
        "        self.epistemic_policy = EpistemicPolicy(store)\n",
        "        self.dialogue_state = DialogueState()\n",
        label="runtime dialogue state",
    )
    text = replace_once(
        text,
        '''        self.capability_evaluator = CapabilityEvaluator(
            self.s,
            self.config.capability_dependency_max_depth,
            self.config.capability_unknown_score,
        )
''',
        '''        self.capability_evaluator = CapabilityEvaluator(
            self.s,
            self.config.capability_dependency_max_depth,
        )
''',
        label="runtime capability evaluator ABI",
    )
    registry = '''        def semantic_runtime_probe():
            required = (
                "i",
                "inf",
                "retriever",
                "state_projector",
                "transition_engine",
                "capability_evaluator",
                "workspace",
            )
            missing = [name for name in required if not hasattr(self, name)]
            if missing:
                raise OperationalProviderContractError(
                    "semantic runtime registration is incomplete: " + ",".join(missing)
                )
            unavailable = [name for name in required if getattr(self, name) is None]
            if unavailable:
                return {
                    "state": "unavailable",
                    "score": 0.0,
                    "unavailable_components": unavailable,
                }
            return {
                "state": "available",
                "score": 1.0,
                "components": list(required),
            }

        def designation_index_probe():
            interpreter = getattr(self, "i", None)
            public_status = getattr(interpreter, "designation_index_status", None)
            if callable(public_status):
                status = public_status()
                if not isinstance(status, Mapping):
                    raise OperationalProviderContractError(
                        "designation-index status must be a mapping"
                    )
                return dict(status)

            # The resource is a semantic-store index, not a private interpreter
            # implementation detail. Reduced interpreters may omit the optional
            # diagnostic surface, so prove the persistent index directly from
            # the store before falling back to unknown evidence.
            db = getattr(self.s, "db", None)
            if db is None:
                return {
                    "state": "unknown",
                    "score": None,
                    "reason": "designation_index_store_handle_unavailable",
                }
            try:
                present = db.execute(
                    "SELECT 1 FROM sqlite_master "
                    "WHERE type='table' AND name='designation_index'"
                ).fetchone()
                if present is None:
                    return {
                        "state": "unavailable",
                        "score": 0.0,
                        "present": False,
                        "reason": "designation_index_table_missing",
                    }
                count = int(
                    db.execute("SELECT count(*) FROM designation_index").fetchone()[0]
                )
            except sqlite3.Error as exc:
                return {
                    "state": "unavailable",
                    "score": 0.0,
                    "present": False,
                    "error_type": type(exc).__name__,
                }
            return {
                "state": "available",
                "score": 1.0,
                "present": True,
                "entry_count": count,
                "evidence_source": "semantic_store_table",
            }

        def semantic_store_probe():
            if not hasattr(self.s, "db"):
                raise OperationalProviderContractError(
                    "semantic store provider lacks database handle"
                )
            return (
                self.s.db.execute("SELECT 1").fetchone() is not None,
                {"database_open": True},
            )

        self.service_registry = RuntimeServiceRegistry()
        self.service_registry.register("resource:runtime_process", lambda: True)
        self.service_registry.register(
            "resource:semantic_runtime", semantic_runtime_probe
        )
        self.service_registry.register_object(
            "resource:language_realizer", self, "realizer"
        )
        self.service_registry.register("resource:output_channel", lambda: True)
        self.service_registry.register_object(
            "resource:inference_engine", self, "inf"
        )
        self.service_registry.register(
            "resource:designation_index", designation_index_probe
        )
        self.service_registry.register(
            "resource:semantic_store", semantic_store_probe
        )
        self.service_registry.register_object(
            "resource:common_ground", self.s, "commit_common_ground"
        )
        self.service_registry.validate_resources()
'''
    text = insert_after_once(
        text,
        "        self.realizer = PointerRealizer(self.s, self.pack, self.cache)\n",
        registry,
        label="runtime service registry",
    )

    old_cycle = '''    def _new_cycle(self, participant_frame=None, source="user", channel="text"):
        self._cycle_counter += 1
        revisions = self.s.revisions()
        frame = participant_frame or self.session.input_frame(source=source, channel=channel)
        cycle_ref = stable("cycle", self.session.session_ref, self._cycle_counter, now())
        view = SelfRuntimeView(
            self.session.self_ref,
            int(self.runtime_attestation["authority_generation"]),
            revisions["world_revision"],
            revisions["discourse_revision"],
            revisions["observation_revision"],
            process_available=True,
            language_realizer_support=1.0,
            semantic_runtime_support=1.0,
            critical_blockers=(),
        )
        cycle = CycleState(
            cycle_ref,
            stable("pass", cycle_ref, 0),
            int(self.runtime_attestation["authority_generation"]),
            revisions["world_revision"],
            revisions["discourse_revision"],
            revisions["observation_revision"],
            frame,
            ContextStack(),
            TemporalFrame(),
            view,
        )
        return cycle
'''
    new_cycle = '''    def _new_cycle(self, participant_frame=None, source="user", channel="text"):
        self._cycle_counter += 1
        revisions = self.s.revisions()
        frame = participant_frame or self.session.input_frame(
            source=source,
            channel=channel,
            dialogue_context=self.dialogue_state.context(self._cycle_counter),
        )
        cycle_ref = stable("cycle", self.session.session_ref, self._cycle_counter, now())
        snapshot = self.service_registry.capture(
            self_ref=self.session.self_ref,
            cycle_ref=cycle_ref,
            authority_generation=int(self.runtime_attestation["authority_generation"]),
            world_revision=revisions["world_revision"],
        )
        view = SelfRuntimeView(
            self.session.self_ref,
            int(self.runtime_attestation["authority_generation"]),
            revisions["world_revision"],
            revisions["discourse_revision"],
            revisions["observation_revision"],
            snapshot,
        )
        cycle = CycleState(
            cycle_ref,
            stable("pass", cycle_ref, 0),
            int(self.runtime_attestation["authority_generation"]),
            revisions["world_revision"],
            revisions["discourse_revision"],
            revisions["observation_revision"],
            frame,
            ContextStack(),
            TemporalFrame(),
            view,
        )
        cycle.workspace.put(
            "operational_usage_ledger", OperationalUsageLedger(snapshot)
        )
        return cycle

    @staticmethod
    def _require_resources(cycle, stage, resources, *, allow_degraded=False):
        ledger = cycle.workspace.get("operational_usage_ledger")
        if ledger is None:
            raise RuntimeError("cycle lacks operational resource-use ledger")
        return OperationalInvariantChecker.check_stage_usage(
            cycle.self_runtime_view.operational_snapshot,
            resources,
            stage=int(stage),
            ledger=ledger,
            allow_degraded=allow_degraded,
        )

    def _interpreter_resources(self, operation):
        return declared_operation_resources(
            self.i,
            str(operation),
            baseline=("resource:semantic_runtime",),
            allowed_resources=CANONICAL_RUNTIME_RESOURCES,
        )
'''
    text = replace_once(text, old_cycle, new_cycle, label="runtime cycle snapshot/ledger")

    old_interpretation = '''    @staticmethod
    def _interpretation(trace, packet):
        raw = trace.get("interpretation_assessment", {})
        return InterpretationAssessment(
            raw.get("status") or ("resolved" if packet else "unresolved"),
            packet,
            tuple(raw.get("grounded_refs", trace.get("grounded_anchors", {}).values())),
            tuple(raw.get("open_variables", ())),
            tuple(raw.get("unresolved_evidence", trace.get("unknown_form_evidence", ()))),
            tuple(raw.get("blockers", (trace.get("reason"),) if trace.get("reason") else ())),
        )
'''
    new_interpretation = '''    @staticmethod
    def _interpretation(trace, packet):
        raw = trace.get("interpretation_assessment", {})
        return InterpretationAssessment(
            raw.get("status") or ("resolved" if packet else "unresolved"),
            packet,
            tuple(raw.get("grounded_refs", trace.get("grounded_anchors", {}).values())),
            tuple(raw.get("open_variables", ())),
            tuple(raw.get("unresolved_evidence", trace.get("unknown_form_evidence", ()))),
            tuple(raw.get("blockers", (trace.get("reason"),) if trace.get("reason") else ())),
            dict(raw.get("coverage", trace.get("interpretation_coverage", {})) or {}),
            dict(raw.get("partial_structure", trace.get("partial_packet", {})) or {}),
        )
'''
    text = replace_once(
        text, old_interpretation, new_interpretation,
        label="runtime interpretation coverage/partial structure",
    )

    frontiers_pattern = r'''    @staticmethod\n    def _frontiers\(trace, cycle_ref\):\n.*?        return tuple\(output\)\n\n'''
    frontiers_replacement = '''    @staticmethod
    def _frontiers(trace, cycle_ref):
        output = []
        for item in trace.get("unknown_form_evidence", ()):
            residual_class = str(item.get("residual_class") or "unknown_form")
            output.append(
                LearningFrontier.create(
                    residual_class,
                    (dict(item),),
                    target_ref=item.get("target_ref"),
                    blocks=("interpretation", "answer"),
                    cycle_ref=cycle_ref,
                )
            )
        for skipped in trace.get("skipped_clauses", ()):
            if skipped.get("reason") == "unknown_form":
                continue
            output.append(
                LearningFrontier.create(
                    skipped.get("reason", "unresolved_clause"),
                    (dict(skipped),),
                    blocks=("interpretation", "answer"),
                    cycle_ref=cycle_ref,
                )
            )
        if not output and trace.get("reason"):
            output.append(
                LearningFrontier.create(
                    trace["reason"],
                    ({
                        "reason": trace["reason"],
                        "coverage": trace.get("interpretation_coverage"),
                        "partial_structure": trace.get("partial_packet"),
                    },),
                    blocks=("interpretation", "answer"),
                    cycle_ref=cycle_ref,
                )
            )
        return tuple(output)

'''
    text = regex_replace_once(
        text, frontiers_pattern, frontiers_replacement,
        label="runtime typed frontier projection",
    )

    text = replace_once(
        text,
        '''            result = self.rulelearner.teach(
''',
        '''            self._require_resources(
                cycle,
                Stage.ENCODE,
                self._interpreter_resources("delex_for_rule"),
            )
            self._require_resources(
                cycle, Stage.COMMIT, ("resource:semantic_store",)
            )
            result = self.rulelearner.teach(
''',
        label="reviewed-teach resource receipts",
    )
    text = replace_once(
        text,
        '''        try:
            lattice = self.i.observe(text, cycle.participant_frame)
''',
        '''        try:
            self._require_resources(
                cycle,
                Stage.ENCODE,
                self._interpreter_resources("observe"),
            )
            lattice = self.i.observe(text, cycle.participant_frame)
''',
        label="normal interpretation resource receipts",
    )
    text = replace_once(
        text,
        '''        except AmbiguousReferent as exc:
            packet, news, uses = None, [], []
            trace = {"reason": "ambiguous_referent", "candidates": exc.candidates, "unknown_form_evidence": ({"surface": exc.surface},)}
        except Exception as exc:
            packet, news, uses = None, [], []
            trace = {"reason": "interpretation_error", "error": str(exc)}
''',
        '''        except AmbiguousReferent as exc:
            packet, news, uses = None, [], []
            trace = {
                "reason": "ambiguous_referent",
                "candidates": exc.candidates,
                "unknown_form_evidence": ({
                    "surface": exc.surface,
                    "residual_class": "argument_critical",
                    "semantic_kind_candidates": ["referent"],
                },),
            }
''',
        label="do not hide interpreter integrity failures",
    )
    text = replace_once(
        text,
        '''        interpretation = self._interpretation(trace, packet)
        frontiers = self._frontiers(trace, cycle.cycle_ref)
        cycle.workspace.put("interpretation_assessment", interpretation)
        cycle.workspace.put("frontier_graph", FrontierGraph(frontiers))
        stages.add(Stage.STABILIZE, counts={"stable": int(packet is not None), "frontiers": len(frontiers)})
''',
        '''        interpretation = self._interpretation(trace, packet)
        frontiers = self._frontiers(trace, cycle.cycle_ref)
        if packet is not None and interpretation.status != "resolved":
            raise RuntimeError(
                "partial interpretation attempted to cross the Stage-7 authority boundary"
            )
        cycle.workspace.put("interpretation_assessment", interpretation)
        cycle.workspace.put("frontier_graph", FrontierGraph(frontiers))
        stages.add(
            Stage.STABILIZE,
            counts={
                "stable": int(packet is not None and interpretation.status == "resolved"),
                "frontiers": len(frontiers),
            },
        )
''',
        label="Stage-7 interpretation invariant",
    )
    text = replace_once(
        text,
        "        runtime_facts = RuntimeObservationProvider.semantic_facts(cycle.self_runtime_view)\n",
        "        runtime_facts = cycle.self_runtime_view.operational_snapshot.semantic_facts()\n",
        label="cycle-local operational facts",
    )
    text = insert_after_once(
        text,
        "        if act and act.force == FORCE_QUERY and act.query:\n",
        '''            self._require_resources(
                cycle,
                Stage.QUERY_EXPLAIN,
                ("resource:inference_engine", "resource:semantic_store"),
            )
''',
        label="query resource receipts",
    )
    text = replace_once(
        text,
        '''        if should_commit:
            with self.s.db:
''',
        '''        if should_commit:
            packet_qualifiers = dict((packet or {}).get("qualifiers", {}))
            if packet_qualifiers.get("consumes_pending_learning"):
                self.dialogue_state.require(
                    packet_qualifiers.get("pending_learning_obligation_ref")
                )
            commit_resources = {"resource:semantic_store"}
            if any(
                app.get("operator") == "op:designation"
                for app in self._packet_applications(packet)
            ):
                commit_resources.add("resource:designation_index")
            self._require_resources(cycle, Stage.COMMIT, commit_resources)
            with self.s.db:
''',
        label="commit resource/obligation precondition",
    )
    text = replace_once(
        text,
        '''            if commit.get("act") is not None:
                act = commit["act"]
            stages.add(Stage.COMMIT, counts={"applications": len(commit["committed_apps"]), "frontiers": len(commit["frontier_refs"])}, refs=(commit["receipt"]["receipt_ref"],), durable_write=True)
''',
        '''            if commit.get("act") is not None:
                act = commit["act"]
            committed_packet = commit.get("packet") or {}
            committed_qualifiers = dict(committed_packet.get("qualifiers", {}))
            if (
                commit.get("committed_apps")
                and committed_qualifiers.get("consumes_pending_learning")
            ):
                consumed_obligation = self.dialogue_state.consume_after_commit(
                    committed_qualifiers.get("pending_learning_obligation_ref"),
                    commit_receipt_ref=commit["receipt"]["receipt_ref"],
                )
                cycle.workspace.put(
                    "consumed_learning_obligation",
                    consumed_obligation.as_dict(),
                )
            stages.add(Stage.COMMIT, counts={"applications": len(commit["committed_apps"]), "frontiers": len(commit["frontier_refs"])}, refs=(commit["receipt"]["receipt_ref"],), durable_write=True)
''',
        label="consume pending learning only after commit",
    )
    text = replace_once(
        text,
        '''            if mode == MODE_NORMAL:
                operation_result = self.adapters.execute(operation_plan)
                with self.s.db:
''',
        '''            if mode == MODE_NORMAL:
                self._require_resources(
                    cycle, Stage.PLAN_EXECUTE, ("resource:semantic_store",)
                )
                operation_result = self.adapters.execute(operation_plan)
                with self.s.db:
''',
        label="pre-effect journal resource receipt",
    )
    text = replace_once(
        text,
        '''                except Exception:
                    continue
''',
        '''                except (KeyError, TypeError, ValueError):
                    continue
''',
        label="operation observation validation uses precise failures",
    )

    text = replace_once(
        text,
        '''            if mode == MODE_NORMAL:
                current_world = self.s.revisions()["world_revision"]
                with self.s.db:
''',
        '''            if mode == MODE_NORMAL:
                current_world = self.s.revisions()["world_revision"]
                self._require_resources(
                    cycle, Stage.ASSIMILATE_OPERATION, ("resource:semantic_store",)
                )
                with self.s.db:
''',
        label="operation observation resource receipt",
    )

    text = replace_once(
        text,
        """        required_capability_refs = self._required_capabilities(act)
        candidates = list(self.goal_arbiter.candidates(
            act=act,
            query_result=query_result,
            frontiers=frontiers,
            transition_previews=transition_previews,
            capability_assessments=capability_assessments,
            required_capability_refs=required_capability_refs,
        ))
""",
        """        required_capability_refs = self._required_capabilities(act)
        learning_probe = []
        if query_result is not None and trace.get("pending_learning_probe"):
            if act is None or act.query is None:
                raise RuntimeError("learning probe survived without an exact query")
            exact_query = act.query.as_dict()
            exact_material = {
                key: exact_query.get(key)
                for key in ("restrictions", "variables", "projection", "qualifiers")
            }
            for raw_probe in trace.get("pending_learning_probe", ()):
                probe = dict(raw_probe)
                raw_query = dict(probe.get("probe_query") or {})
                raw_material = {
                    key: raw_query.get(key, [] if key != "qualifiers" else {})
                    for key in ("restrictions", "variables", "projection", "qualifiers")
                }
                if canonical(raw_material) != canonical(exact_material):
                    raise RuntimeError(
                        "learning probe query differs from the executed QueryStructure"
                    )
                learning_probe.append({
                    **probe,
                    "query_ref": query_result.query_ref,
                    "probe_query": exact_query,
                })
        candidates = list(self.goal_arbiter.candidates(
            act=act,
            query_result=query_result,
            frontiers=frontiers,
            transition_previews=transition_previews,
            capability_assessments=capability_assessments,
            required_capability_refs=required_capability_refs,
            learning_probe=tuple(learning_probe),
        ))
""",
        label="query-bound post-query learning handoff",
    )

    text = replace_once(
        text,
        '''            operation_result=operation_result,
            epistemic_placement=placement,
        )
        stages.add(Stage.RESPONSE_CSIR, counts={"responses": 1}, refs=(response_csir.response_ref,))
''',
        '''            operation_result=operation_result,
            epistemic_placement=placement,
            operational_snapshot=cycle.self_runtime_view.operational_snapshot,
            discourse_act=act,
            dialogue_context=cycle.participant_frame.dialogue_context,
        )
        stages.add(Stage.RESPONSE_CSIR, counts={"responses": 1}, refs=(response_csir.response_ref,))
''',
        label="response context bindings",
    )

    # Every realization uses an output participant frame and emits Stage-19/20
    # resource-use receipts. Dialogue state is updated only after Stage-21 common
    # ground commit, never immediately after string generation.
    realizer_pattern = re.compile(
        r"(?P<i>^[ ]*)response, realization_proof = self\.realizer\.response\(response_csir\)$",
        re.MULTILINE,
    )
    matches = list(realizer_pattern.finditer(text))
    if matches:
        def rewrite_realizer(match: re.Match[str]) -> str:
            indent = match.group("i")
            return (
                f"{indent}self._require_resources(\n"
                f"{indent}    cycle, Stage.REALIZE, (\"resource:language_realizer\",)\n"
                f"{indent})\n"
                f"{indent}self._require_resources(\n"
                f"{indent}    cycle, Stage.VERIFY, (\"resource:output_channel\",)\n"
                f"{indent})\n"
                f"{indent}response, realization_proof = self.realizer.response(\n"
                f"{indent}    response_csir,\n"
                f"{indent}    self.session.output_frame(\n"
                f"{indent}        addressee_ref=cycle.participant_frame.speaker_ref,\n"
                f"{indent}        channel=cycle.participant_frame.channel,\n"
                f"{indent}        dialogue_context=self.dialogue_state.context(self._cycle_counter),\n"
                f"{indent}    ),\n"
                f"{indent})"
            )
        text = realizer_pattern.sub(rewrite_realizer, text)
    elif "self.realizer.response(response_csir)" in text:
        raise RewriteError("runtime realizer calls remained unpatched")
    if text.count("self.realizer.response(\n") < 3:
        raise RewriteError("runtime expected three participant-aware realization sites")

    provenance = '''{
                        "response_csir": response_csir.as_dict(),
                        "surface_decision": realization_proof.get("surface_decision"),
                        "response_equivalence": realization_proof.get("response_equivalence"),
                        "obligation_ref": response_csir.obligation_ref,
                        "pending_learning": (
                            self.dialogue_state.pending.as_dict()
                            if self.dialogue_state.pending
                            else None
                        ),
                    }'''
    # The reviewed-teach call is on one line; the normal call uses a dedicated
    # third argument line. Replace both exact forms separately.
    text = replace_once(
        text,
        "cycle.participant_frame.conversation_ref, response_csir.response_ref, response_csir.as_dict(),\n",
        "cycle.participant_frame.conversation_ref, response_csir.response_ref, " + provenance + ",\n",
        label="reviewed-teach common-ground provenance",
    )
    text = replace_once(
        text,
        '''                    response_csir.as_dict(),
                    expected_discourse_revision=cycle.discourse_revision,
''',
        '''                    {
                        "response_csir": response_csir.as_dict(),
                        "surface_decision": realization_proof.get("surface_decision"),
                        "response_equivalence": realization_proof.get("response_equivalence"),
                        "obligation_ref": response_csir.obligation_ref,
                        "pending_learning": (
                            self.dialogue_state.pending.as_dict()
                            if self.dialogue_state.pending
                            else None
                        ),
                    },
                    expected_discourse_revision=cycle.discourse_revision,
''',
        label="normal common-ground provenance",
    )

    text = replace_once(
        text,
        '''            if response and realization_proof.get("verified"):
                with self.s.db:
''',
        '''            if response and realization_proof.get("verified"):
                self._require_resources(
                    cycle,
                    Stage.COMMON_GROUND,
                    ("resource:common_ground", "resource:semantic_store"),
                )
                with self.s.db:
''',
        label="reviewed-teach common-ground resource receipts",
    )
    text = replace_once(
        text,
        '''                stages.add(Stage.COMMON_GROUND, counts={"entries": 1}, refs=(common_ground["entry_ref"],), durable_write=True)
            else:
''',
        '''                self.dialogue_state.observe_response(
                    response_csir,
                    realization_proof,
                    cycle_ref=cycle.cycle_ref,
                    turn_index=self._cycle_counter,
                )
                stages.add(Stage.COMMON_GROUND, counts={"entries": 1}, refs=(common_ground["entry_ref"],), durable_write=True)
            else:
''',
        label="reviewed-teach dialogue update after common-ground commit",
    )
    text = replace_once(
        text,
        '''        if mode == MODE_NORMAL and verified and self.config.persist_common_ground:
            with self.s.db:
''',
        '''        if mode == MODE_NORMAL and verified and self.config.persist_common_ground:
            self._require_resources(
                cycle,
                Stage.COMMON_GROUND,
                ("resource:common_ground", "resource:semantic_store"),
            )
            with self.s.db:
''',
        label="normal common-ground resource receipts",
    )
    text = replace_once(
        text,
        '''            stages.add(Stage.COMMON_GROUND, counts={"entries": 1}, refs=(common_ground["entry_ref"],), durable_write=True)
        else:
''',
        '''            self.dialogue_state.observe_response(
                response_csir,
                realization_proof,
                cycle_ref=cycle.cycle_ref,
                turn_index=self._cycle_counter,
            )
            stages.add(Stage.COMMON_GROUND, counts={"entries": 1}, refs=(common_ground["entry_ref"],), durable_write=True)
        else:
''',
        label="normal dialogue update after common-ground commit",
    )

    # The early AmbiguousReferent path also passes through verified Stage 21 in
    # normal mode, rather than producing an untracked surface decision.
    text = replace_once(
        text,
        '''            stages.add(Stage.VERIFY, counts={"verified": int(bool(realization_proof.get("verified")))})
            stages.add(Stage.COMMON_GROUND, counts={"entries": 0})
            stages.add(Stage.FINALIZE, counts={"model_cache": len(self.cache), "workspace_slots": 0})
''',
        '''            verified = bool(response and realization_proof.get("verified"))
            stages.add(Stage.VERIFY, counts={"verified": int(verified)})
            common_ground = None
            if mode == MODE_NORMAL and verified and self.config.persist_common_ground:
                self._require_resources(
                    cycle,
                    Stage.COMMON_GROUND,
                    ("resource:common_ground", "resource:semantic_store"),
                )
                with self.s.db:
                    common_ground = self.s.commit_common_ground(
                        cycle.participant_frame.conversation_ref,
                        response_csir.response_ref,
                        {
                            "response_csir": response_csir.as_dict(),
                            "surface_decision": realization_proof.get("surface_decision"),
                            "response_equivalence": realization_proof.get("response_equivalence"),
                            "obligation_ref": response_csir.obligation_ref,
                            "pending_learning": None,
                        },
                        expected_discourse_revision=cycle.discourse_revision,
                    )
                self.dialogue_state.observe_response(
                    response_csir,
                    realization_proof,
                    cycle_ref=cycle.cycle_ref,
                    turn_index=self._cycle_counter,
                )
                stages.add(Stage.COMMON_GROUND, counts={"entries": 1}, refs=(common_ground["entry_ref"],), durable_write=True)
            else:
                stages.add(Stage.COMMON_GROUND, counts={"entries": 0})
            stages.add(Stage.FINALIZE, counts={"model_cache": len(self.cache), "workspace_slots": 0})
''',
        label="ambiguous path Stage-21 provenance",
    )
    text = replace_once(
        text,
        '''                "realization_proof": realization_proof,
                "stage_trace": stages.as_dict(),
''',
        '''                "realization_proof": realization_proof,
                "common_ground": common_ground,
                "dialogue_state": self.dialogue_state.context(self._cycle_counter),
                "operational_usage": cycle.workspace.get("operational_usage_ledger").as_dict(),
                "stage_trace": stages.as_dict(),
''',
        label="ambiguous path receipts",
    )

    text = replace_once(
        text,
        '''            "side_effect_free": mode == MODE_READ_ONLY,
        }
        return result
''',
        '''            "side_effect_free": mode == MODE_READ_ONLY,
            "dialogue_state": self.dialogue_state.context(self._cycle_counter),
            "operational_usage": cycle.workspace.get("operational_usage_ledger").as_dict(),
            "runtime_invariants": {
                "critical_residuals_block_execution": not (
                    packet is not None and interpretation.status != "resolved"
                ),
                "operational_snapshot_ref": cycle.self_runtime_view.operational_snapshot.snapshot_ref,
                "registered_resources": list(self.service_registry.resources()),
                "response_equivalence_verified": bool(
                    response and realization_proof.get("verified")
                ),
                "surface_absent": not bool(response),
            },
        }
        return result
''',
        label="normal runtime invariant receipts",
    )

    path.write_text(_seal_file_rewrite(text, marker), encoding="utf-8")


def patch_cognition(path: Path) -> None:
    marker = REWRITE_MARKERS["cemm/cognition.py"]
    text = path.read_text(encoding="utf-8")
    source = _begin_file_rewrite(text, marker, label="cognition rewrite seal")
    if source is None:
        return
    text = source
    text = replace_once(
        text,
        '''        raw_variables = list(value.get("variables", ()))
        projection = tuple(value.get("projection", ()))
''',
        '''        raw_variables = list(value.get("variables", ()))
        raw_projection = value.get("projection")
        projection = tuple(raw_projection) if raw_projection is not None else ()
''',
        label="preserve explicit empty boolean projection",
    )
    text = replace_once(
        text,
        '''        if not projection:
            projection = tuple(sorted(inferred))
''',
        '''        if raw_projection is None:
            projection = tuple(sorted(inferred))
''',
        label="query projection default only when absent",
    )
    text = replace_once(
        text,
        '''    blockers: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
''',
        '''    blockers: tuple[str, ...] = ()
    coverage: Mapping[str, Any] = field(default_factory=dict)
    partial_structure: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
''',
        label="interpretation coverage ABI",
    )
    text = replace_once(
        text,
        '''            "blockers": list(self.blockers),
        }


@dataclass(frozen=True)
class LearningFrontier:
''',
        '''            "blockers": list(self.blockers),
            "coverage": dict(self.coverage),
            "partial_structure": dict(self.partial_structure),
        }


@dataclass(frozen=True)
class LearningFrontier:
''',
        label="interpretation coverage serialization",
    )
    path.write_text(_seal_file_rewrite(text, marker), encoding="utf-8")


def patch_compiler(path: Path) -> None:
    marker = REWRITE_MARKERS["cemm/compiler.py"]
    text = path.read_text(encoding="utf-8")
    source = _begin_file_rewrite(text, marker, label="compiler rewrite seal")
    if source is None:
        return
    text = source
    text = replace_once(
        text,
        '''        projection = tuple(raw.get("projection", ())) or tuple(sorted(explicit))
''',
        '''        raw_projection = raw.get("projection")
        projection = (
            tuple(raw_projection)
            if raw_projection is not None
            else tuple(sorted(explicit))
        )
''',
        label="compiler explicit boolean projection",
    )
    path.write_text(_seal_file_rewrite(text, marker), encoding="utf-8")


def patch_transitions(path: Path) -> None:
    marker = REWRITE_MARKERS["cemm/transitions.py"]
    text = path.read_text(encoding="utf-8")
    source = _begin_file_rewrite(text, marker, label="transitions rewrite seal")
    if source is None:
        return
    text = source
    text = replace_once(
        text,
        '''                            "causal_not_factual": True,
                            "committed": False,
''',
        '''                            "causal_not_factual": True,
                            "epistemic_mode": "simulated",
                            "committed": False,
''',
        label="transition preview epistemic mode",
    )
    path.write_text(_seal_file_rewrite(text, marker), encoding="utf-8")


def patch_agents(path: Path) -> None:
    seal = REWRITE_MARKERS["AGENTS.md"]
    text = path.read_text(encoding="utf-8")
    source = _begin_file_rewrite(text, seal, label="AGENTS rewrite seal")
    if source is None:
        return
    text = source
    contract_marker = "CEMM_RUNTIME_IMPLEMENTATION_CONTRACT.md"
    if contract_marker not in text:
        addition = '''
## Canonical Runtime Implementation Contract

For active runtime, form/training, operational-state, transition and response-realization implementation, follow `CEMM_RUNTIME_IMPLEMENTATION_CONTRACT.md`. Do not duplicate or reinterpret that contract in this file or other architecture/phase documents.
'''
        text = text.rstrip() + "\n" + addition
    path.write_text(_seal_file_rewrite(text, seal), encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _method(tree: ast.AST, class_name: str, method_name: str):
    cls = next(
        (node for node in ast.walk(tree) if isinstance(node, ast.ClassDef) and node.name == class_name),
        None,
    )
    if cls is None:
        raise RewriteError(f"postcondition: missing class {class_name}")
    method = next(
        (node for node in cls.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == method_name),
        None,
    )
    if method is None:
        raise RewriteError(f"postcondition: missing method {class_name}.{method_name}")
    return method


def _called_attributes(node: ast.AST):
    return [
        (item.func.attr, item)
        for item in ast.walk(node)
        if isinstance(item, ast.Call) and isinstance(item.func, ast.Attribute)
    ]


def validate_postconditions(repo: Path) -> None:
    py_paths = [
        repo / "cemm/config.py",
        repo / "cemm/runtime.py",
        repo / "cemm/cognition.py",
        repo / "cemm/compiler.py",
        repo / "cemm/transitions.py",
    ]
    trees = {}
    for path in py_paths:
        try:
            trees[path.name] = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            raise RewriteError(f"postcondition: syntax error in {path}: {exc}") from exc

    config_names = {node.id for node in ast.walk(trees["config.py"]) if isinstance(node, ast.Name)}
    if "capability_unknown_score" in config_names or "capability_unknown_score" in (repo / "cemm/config.py").read_text(encoding="utf-8"):
        raise RewriteError("postcondition: numeric unknown capability policy remains")

    runtime = trees["runtime.py"]
    init = _method(runtime, "Runtime", "__init__")
    bind = _method(runtime, "Runtime", "_bind_authority")
    cycle = _method(runtime, "Runtime", "_new_cycle")
    process = _method(runtime, "Runtime", "process")
    _method(runtime, "Runtime", "_require_resources")
    interpreter_resources = _method(runtime, "Runtime", "_interpreter_resources")
    init_attrs = {
        target.attr
        for node in ast.walk(init)
        if isinstance(node, (ast.Assign, ast.AnnAssign))
        for target in (node.targets if isinstance(node, ast.Assign) else (node.target,))
        if isinstance(target, ast.Attribute)
    }
    if "dialogue_state" not in init_attrs:
        raise RewriteError("postcondition: Runtime has no dialogue state")
    bind_calls = _called_attributes(bind)
    if not any(name == "validate_resources" for name, _ in bind_calls):
        raise RewriteError("postcondition: service registry is not startup-validated")
    constants = {node.value for node in ast.walk(runtime) if isinstance(node, ast.Constant) and isinstance(node.value, str)}
    expected_resources = {
        "resource:runtime_process", "resource:semantic_runtime",
        "resource:language_realizer", "resource:output_channel",
        "resource:inference_engine", "resource:designation_index",
        "resource:semantic_store", "resource:common_ground",
    }
    if not expected_resources.issubset(constants):
        raise RewriteError("postcondition: canonical runtime service registry is incomplete")
    runtime_source = (repo / "cemm/runtime.py").read_text(encoding="utf-8")
    for required_fragment in (
        "designation_index_status",
        "SELECT count(*) FROM designation_index",
        "designation_index_store_handle_unavailable",
    ):
        if required_fragment not in runtime_source:
            raise RewriteError(
                "postcondition: designation-index operational proof is incomplete: "
                + required_fragment
            )
    if "operational_usage_ledger" not in {node.value for node in ast.walk(cycle) if isinstance(node, ast.Constant) and isinstance(node.value, str)}:
        raise RewriteError("postcondition: cycle has no resource-use ledger")
    if any(
        isinstance(node, ast.ExceptHandler)
        and isinstance(node.type, ast.Name)
        and node.type.id in {"Exception", "BaseException"}
        for node in ast.walk(process)
    ):
        raise RewriteError("postcondition: Runtime.process hides integrity failures")
    process_calls = _called_attributes(process)
    if sum(name == "_require_resources" for name, _ in process_calls) < 6:
        raise RewriteError("postcondition: runtime stages lack resource-use gates")
    declaration_source = ast.unparse(interpreter_resources)
    if "CANONICAL_RUNTIME_RESOURCES" not in declaration_source:
        raise RewriteError(
            "postcondition: interpreter resource declarations are not ABI-validated"
        )
    observe_gates = [
        call
        for name, call in process_calls
        if name == "_require_resources"
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
    ]
    if len(observe_gates) != 1:
        raise RewriteError(
            "postcondition: Stage.ENCODE is not gated by the interpreter's declared resource use"
        )
    _forbidden_pair = (
        "resource:semantic_runtime",
        "resource:designation_index",
    )
    if any(
        isinstance(node, ast.Tuple)
        and tuple(
            item.value for item in node.elts
            if isinstance(item, ast.Constant) and isinstance(item.value, str)
        ) == _forbidden_pair
        for node in ast.walk(process)
    ):
        raise RewriteError(
            "postcondition: Stage.ENCODE still hardcodes a private interpreter dependency"
        )
    if not any(name == "consume_after_commit" for name, _ in process_calls):
        raise RewriteError("postcondition: dialogue obligation is not commit-bound")
    realization_calls = [call for name, call in process_calls if name == "response"]
    if len(realization_calls) != 3 or any(len(call.args) < 2 for call in realization_calls):
        raise RewriteError("postcondition: every realization must use an output frame")

    candidate_calls = [
        call
        for name, call in process_calls
        if name == "candidates"
        and isinstance(call.func.value, ast.Attribute)
        and call.func.value.attr == "goal_arbiter"
    ]
    if len(candidate_calls) != 1 or not any(
        keyword.arg == "learning_probe" for keyword in candidate_calls[0].keywords
    ):
        raise RewriteError(
            "postcondition: unanswered exact queries are not connected to learning goals"
        )

    adapter_execute_calls = [
        call
        for name, call in process_calls
        if name == "execute"
        and isinstance(call.func.value, ast.Attribute)
        and call.func.value.attr == "adapters"
    ]
    if len(adapter_execute_calls) != 1:
        raise RewriteError("postcondition: expected one adapter execution boundary")
    execute_line = adapter_execute_calls[0].lineno
    plan_gates = [
        call
        for name, call in process_calls
        if name == "_require_resources"
        and call.lineno < execute_line
        and "Stage.PLAN_EXECUTE" in ast.unparse(call)
        and "resource:semantic_store" in ast.unparse(call)
    ]
    if not plan_gates:
        raise RewriteError(
            "postcondition: semantic-store/effect-journal gate occurs after adapter execution"
        )

    cognition = trees["cognition.py"]
    query_from_dict = _method(cognition, "QueryStructure", "from_dict")
    if "raw_projection" not in {node.id for node in ast.walk(query_from_dict) if isinstance(node, ast.Name)}:
        raise RewriteError("postcondition: explicit empty query projection is not preserved")
    compiler = trees["compiler.py"]
    query_method = _method(compiler, "ExactStructuredCompiler", "_query")
    if "raw_projection" not in {node.id for node in ast.walk(query_method) if isinstance(node, ast.Name)}:
        raise RewriteError("postcondition: compiler loses explicit empty query projection")
    transition_constants = {node.value for node in ast.walk(trees["transitions.py"]) if isinstance(node, ast.Constant)}
    if "simulated" not in transition_constants:
        raise RewriteError("postcondition: transition previews lack simulated epistemic mode")
    if "CEMM_RUNTIME_IMPLEMENTATION_CONTRACT.md" not in (repo / "AGENTS.md").read_text(encoding="utf-8"):
        raise RewriteError("postcondition: AGENTS.md does not route to the canonical contract")




def validate_rewrite_seals(repo: Path) -> None:
    problems = []
    for relative, marker in REWRITE_MARKERS.items():
        path = repo / relative
        if not path.is_file():
            problems.append(f"missing sealed rewrite target: {relative}")
            continue
        count = path.read_text(encoding="utf-8").count(marker)
        if count != 1:
            problems.append(
                f"{relative}: expected exactly one rewrite seal {marker!r}, found {count}"
            )
    if problems:
        raise RewriteError("rewrite seal validation failed:\n" + "\n".join(problems))


def rewrite_seal_state(repo: Path) -> dict[str, bool]:
    state = {}
    for relative, marker in REWRITE_MARKERS.items():
        path = repo / relative
        if not path.is_file():
            raise RewriteError(f"missing rewrite target: {relative}")
        count = path.read_text(encoding="utf-8").count(marker)
        if count > 1:
            raise RewriteError(
                f"{relative}: expected at most one rewrite seal, found {count}"
            )
        state[relative] = count == 1
    return state


def _rewrite_targets(repo: Path) -> tuple[Path, ...]:
    return tuple(repo / relative for relative in REWRITE_MARKERS)


def _apply_all_rewrites(repo: Path) -> None:
    patch_config(repo / "cemm/config.py")
    patch_runtime(repo / "cemm/runtime.py")
    patch_cognition(repo / "cemm/cognition.py")
    patch_compiler(repo / "cemm/compiler.py")
    patch_transitions(repo / "cemm/transitions.py")
    patch_agents(repo / "AGENTS.md")


def prove_idempotence_on_isolated_copy(repo: Path) -> None:
    """Run the rewrite engine on sealed copies and prove a byte-for-byte no-op.

    This is intentionally isolated from the checkout under validation.  The
    previous v3.1.0 implementation reran mutating anchor replacements directly
    in ``--check`` mode, allowing later replacements to create new matches for
    earlier anchors.  A check pass must never mutate or depend on anchor order.
    """
    with tempfile.TemporaryDirectory(prefix="cemm-source-rewrite-check-") as tmp:
        copy_root = Path(tmp) / "repo"
        for relative in REWRITE_MARKERS:
            source = repo / relative
            destination = copy_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        before = {
            relative: _sha256(copy_root / relative)
            for relative in REWRITE_MARKERS
        }
        _apply_all_rewrites(copy_root)
        after = {
            relative: _sha256(copy_root / relative)
            for relative in REWRITE_MARKERS
        }
        if before != after:
            changed = sorted(relative for relative in before if before[relative] != after[relative])
            raise RewriteError(
                "sealed source rewrite is not idempotent on isolated copies: "
                + ", ".join(changed)
            )

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    parser.add_argument(
        "--check", action="store_true",
        help=(
            "validate sealed rewrite output and prove idempotence on isolated "
            "copies without mutating the checkout"
        ),
    )
    args = parser.parse_args()
    repo = Path(args.repo).resolve()
    targets = _rewrite_targets(repo)
    before = {str(path): _sha256(path) for path in targets}

    if args.check:
        # A check is a pure verifier. It must never run first-pass anchor
        # replacements against the checkout being validated.
        validate_rewrite_seals(repo)
        validate_postconditions(repo)
        prove_idempotence_on_isolated_copy(repo)
        after = {str(path): _sha256(path) for path in targets}
        if before != after:
            changed = sorted(path for path in before if before[path] != after[path])
            raise RewriteError(
                "source rewrite check mutated the checkout: " + ", ".join(changed)
            )
        print("source rewrite seals, postconditions, and isolated idempotence passed")
        return

    seal_state = rewrite_seal_state(repo)
    sealed = sorted(relative for relative, present in seal_state.items() if present)
    unsealed = sorted(relative for relative, present in seal_state.items() if not present)
    if sealed and unsealed:
        raise RewriteError(
            "source rewrite targets are in a mixed sealed/unsealed state: "
            f"sealed={sealed}, unsealed={unsealed}"
        )
    if sealed:
        validate_rewrite_seals(repo)
        validate_postconditions(repo)
        prove_idempotence_on_isolated_copy(repo)
        after = {str(path): _sha256(path) for path in targets}
        if before != after:
            raise RewriteError("sealed source rewrite unexpectedly changed files")
        print("source integration files were already sealed and verified")
        return

    _apply_all_rewrites(repo)
    validate_rewrite_seals(repo)
    validate_postconditions(repo)
    after = {str(path): _sha256(path) for path in targets}
    unchanged = sorted(path for path in before if before[path] == after[path])
    if unchanged:
        raise RewriteError(
            "first rewrite pass left target files unchanged: " + ", ".join(unchanged)
        )
    print("rewrote and sealed exact runtime integration sources")


if __name__ == "__main__":
    main()
