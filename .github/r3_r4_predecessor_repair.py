from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "hybrid_mvp"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one source match, found {count}")
    return text.replace(old, new, 1)


def patch_proposal_context() -> None:
    path = PROJECT / "src/cemm_authoritative_hybrid/proposal_context.py"
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "        application_frames = self._application_frames(\n"
        "            designation_slots,\n"
        "            profiles_by_target,\n"
        "            predicate_targets,\n"
        "        )\n",
        "        application_frames, event_signatures = self._application_frames(\n"
        "            designation_slots,\n"
        "            profiles_by_target,\n"
        "            predicate_targets,\n"
        "        )\n",
        "application-frame call",
    )
    text = replace_once(
        text,
        "        designation_references = self._designation_references(\n"
        "            designation_slots,\n"
        "            profiles_by_target,\n"
        "            contribution_slots,\n"
        "        )\n"
        "        reference_slots = _bounded_unique_slots(\n"
        "            (*designation_references, *form_references),\n"
        "            self._config.max_orientation_alternatives,\n"
        "        )\n",
        "        reference_contributions, designation_references = (\n"
        "            self._designation_reference_evidence(\n"
        "                designation_slots,\n"
        "                application_frames,\n"
        "                event_signatures,\n"
        "                contribution_slots,\n"
        "            )\n"
        "        )\n"
        "        contribution_slots = _bounded_unique_contributions(\n"
        "            (*reference_contributions, *contribution_slots),\n"
        "            self._config,\n"
        "        )\n"
        "        situated_references = self._situated_participant_references(\n"
        "            orientation,\n"
        "            application_frames,\n"
        "            event_signatures,\n"
        "            (*designation_references, *form_references),\n"
        "        )\n"
        "        reference_slots = _bounded_unique_slots(\n"
        "            (*designation_references, *form_references, *situated_references),\n"
        "            self._config.max_orientation_alternatives,\n"
        "        )\n",
        "designation-reference build",
    )
    start = text.index("    def _designation_references(")
    end = text.index("\n    def _application_frames(", start)
    old_section = text[start:end]
    if "profiles_by_target" not in old_section or 'kind in {"anchor", "reference"}' not in old_section:
        raise SystemExit("designation-reference predecessor method drifted")
    new_section = '''    def _designation_reference_evidence(
        self,
        designations: tuple[DesignationSlot, ...],
        frames: tuple[ApplicationFrameSlot, ...],
        event_signatures: Mapping[str, EventSignature],
        existing_contributions: tuple[ContributionSlot, ...],
    ) -> tuple[tuple[ContributionSlot, ...], tuple[ReferenceSlot, ...]]:
        contributions: list[ContributionSlot] = []
        references: list[ReferenceSlot] = []
        for designation in designations:
            if designation.target_kind not in {"entity", "participant"}:
                continue
            roles = self._compatible_reference_roles(
                designation, frames, event_signatures
            )
            if not roles:
                continue
            existing_roles = tuple(
                dict.fromkeys(
                    role
                    for row in existing_contributions
                    if row.kind == "reference"
                    and row.target_ref == designation.target_ref
                    and row.source_unit_refs == designation.source_unit_refs
                    for role in row.output_ports
                )
            )
            if set(roles) <= set(existing_roles):
                contribution = next(
                    row
                    for row in existing_contributions
                    if row.kind == "reference"
                    and row.target_ref == designation.target_ref
                    and row.source_unit_refs == designation.source_unit_refs
                )
            else:
                contribution = ContributionSlot.create(
                    contribution_ref=stable_ref(
                        "designation_reference_contribution",
                        {
                            "designation_slot_ref": designation.slot_ref,
                            "target_ref": designation.target_ref,
                            "target_kind": designation.target_kind,
                            "source_unit_refs": list(designation.source_unit_refs),
                            "compatible_roles": list(roles),
                        },
                    ),
                    kind="reference",
                    source_unit_refs=designation.source_unit_refs,
                    target_ref=designation.target_ref,
                    target_kind=designation.target_kind,
                    input_ports=(),
                    output_ports=roles,
                    constraints=(("resolution_kind", "designation"),),
                    provenance_refs=tuple(
                        dict.fromkeys(
                            (
                                designation.slot_ref,
                                designation.designation_fact_ref,
                                *designation.provenance_refs,
                            )
                        )
                    ),
                )
            reference = ReferenceSlot.create(
                target_ref=designation.target_ref,
                target_kind=designation.target_kind,
                source_unit_refs=designation.source_unit_refs,
                resolution_kind="designation",
                compatible_roles=roles,
                score_q=designation.score_q,
                provenance_refs=(designation.slot_ref, contribution.slot_ref),
            )
            contributions.append(contribution)
            references.append(reference)
        return tuple(contributions), tuple(references)

    def _compatible_reference_roles(
        self,
        designation: DesignationSlot,
        frames: tuple[ApplicationFrameSlot, ...],
        event_signatures: Mapping[str, EventSignature],
    ) -> tuple[str, ...]:
        generic = _reference_roles(designation.target_kind)
        compatible: list[str] = []
        for frame in frames:
            legal_roles = (*frame.required_roles, *frame.optional_roles)
            if frame.predicate_kind == "event_type":
                signature = event_signatures.get(frame.predicate_target_ref)
                if not isinstance(signature, EventSignature):
                    continue
                specs = {row.role: row for row in signature.roles}
                for role in legal_roles:
                    spec = specs.get(role)
                    if spec is None or spec.proposition_valued:
                        continue
                    if not spec.filler_kinds or designation.target_kind in spec.filler_kinds:
                        compatible.append(role)
                continue
            compatible.extend(role for role in legal_roles if role in generic)
        return tuple(dict.fromkeys((*compatible, *generic)))

    def _situated_participant_references(
        self,
        orientation: Orientation,
        frames: tuple[ApplicationFrameSlot, ...],
        event_signatures: Mapping[str, EventSignature],
        explicit_references: tuple[ReferenceSlot, ...],
    ) -> tuple[ReferenceSlot, ...]:
        participant_refs = tuple(
            ref
            for ref in orientation.participants
            if isinstance(self._authority.atoms.get(ref), AtomRecord)
            and self._authority.atoms[ref].kind == "participant"
        )
        if not participant_refs:
            return ()
        speaker = (
            orientation.participant_frame
            if orientation.participant_frame in participant_refs
            else participant_refs[0]
        )
        others = tuple(ref for ref in participant_refs if ref != speaker)
        actor_roles = frozenset(
            {"role:actor", "role:subject", "role:speaker", "role:source", "role:participant"}
        )
        addressed_roles = frozenset(
            {"role:addressee", "role:target", "role:object", "role:recipient", "role:beneficiary"}
        )
        rows: list[ReferenceSlot] = []
        for frame in frames:
            if frame.predicate_kind != "event_type":
                continue
            signature = event_signatures.get(frame.predicate_target_ref)
            if not isinstance(signature, EventSignature):
                continue
            specs = {row.role: row for row in signature.roles}
            for role in frame.required_roles:
                spec = specs.get(role)
                if (
                    spec is None
                    or spec.proposition_valued
                    or (spec.filler_kinds and "participant" not in spec.filler_kinds)
                    or any(role in ref.compatible_roles for ref in explicit_references)
                ):
                    continue
                target = (
                    speaker
                    if role in actor_roles
                    else (others[0] if role in addressed_roles and others else None)
                )
                if target is None:
                    continue
                rows.append(
                    ReferenceSlot.create(
                        target_ref=target,
                        target_kind="participant",
                        source_unit_refs=(),
                        resolution_kind="situated_participant",
                        compatible_roles=(role,),
                        score_q=1_000_000,
                        provenance_refs=(orientation.orientation_ref, frame.slot_ref),
                    )
                )
        return tuple(rows)
'''
    text = text[:start] + new_section + text[end:]
    text = replace_once(
        text,
        "    ) -> tuple[ApplicationFrameSlot, ...]:\n        frames: list[ApplicationFrameSlot] = []\n",
        "    ) -> tuple[tuple[ApplicationFrameSlot, ...], Mapping[str, EventSignature]]:\n        frames: list[ApplicationFrameSlot] = []\n",
        "application-frame return type",
    )
    text = replace_once(
        text,
        "        return tuple(frames)\n\n    def _transition_slots(\n",
        "        return (\n"
        "            tuple(frames),\n"
        "            MappingProxyType(\n"
        "                {\n"
        "                    target: signature\n"
        "                    for target, signature in event_signature_by_target.items()\n"
        "                    if isinstance(signature, EventSignature)\n"
        "                }\n"
        "            ),\n"
        "        )\n\n"
        "    def _transition_slots(\n",
        "application-frame return",
    )
    path.write_text(text, encoding="utf-8")


def patch_runtime() -> None:
    path = PROJECT / "src/cemm_authoritative_hybrid/runtime.py"
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "        permissions = tuple(\n"
        "            row if type(row) is str else f\"{row[0]}:{row[1]}:{row[2]}\"\n"
        "            for row in self._authority.permissions\n"
        "        )\n",
        "        permissions = _unique(\n"
        "            tuple(\n"
        "                row if type(row) is str else f\"{row[0]}:{row[1]}:{row[2]}\"\n"
        "                for row in self._authority.permissions\n"
        "            )\n"
        "        )\n",
        "permission snapshot",
    )
    path.write_text(text, encoding="utf-8")


def patch_cycle() -> None:
    path = PROJECT / "src/cemm_authoritative_hybrid/cycle.py"
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "            fixed_dimensions = (\n"
        "                (\"authority_generation\", source.authority_generation, target.authority_generation),\n"
        "                (\"session_revision\", source.session_revision, target.session_revision),\n"
        "                (\"episode_revision\", source.episode_revision, target.episode_revision),\n"
        "                (\"model_identity\", source.model_identity, target.model_identity),\n"
        "            )\n",
        "            fixed_dimensions = (\n"
        "                (\"authority_generation\", source.authority_generation, target.authority_generation),\n"
        "                (\"episode_revision\", source.episode_revision, target.episode_revision),\n"
        "                (\"model_identity\", source.model_identity, target.model_identity),\n"
        "            )\n",
        "effect fixed dimensions",
    )
    text = replace_once(
        text,
        "            if (\n"
        "                target.world_revision < source.world_revision\n"
        "                or target.effect_revision < source.effect_revision\n"
        "            ):\n"
        "                raise ValueError(\"EFFECT revision changes must be monotonic\")\n"
        "            if (\n"
        "                target != source\n"
        "                and self.disposition is not PhaseDisposition.COMMITTED\n"
        "            ):\n"
        "                raise ValueError(\"only EFFECT with COMMITTED may change a revision pin\")\n"
        "            if self.disposition is PhaseDisposition.COMMITTED and target == source:\n",
        "            if (\n"
        "                target.world_revision < source.world_revision\n"
        "                or target.session_revision < source.session_revision\n"
        "                or target.effect_revision < source.effect_revision\n"
        "            ):\n"
        "                raise ValueError(\"EFFECT revision changes must be monotonic\")\n"
        "            if self.disposition is PhaseDisposition.NO_EFFECT:\n"
        "                if target.world_revision != source.world_revision:\n"
        "                    raise ValueError(\"EFFECT with NO_EFFECT may not change world revision\")\n"
        "                if target.effect_revision <= source.effect_revision:\n"
        "                    raise ValueError(\"persisted NO_EFFECT must advance effect revision\")\n"
        "            elif target != source and self.disposition is not PhaseDisposition.COMMITTED:\n"
        "                raise ValueError(\"only EFFECT with COMMITTED/NO_EFFECT may change a revision pin\")\n"
        "            if self.disposition is PhaseDisposition.COMMITTED and target == source:\n",
        "effect revision monotonicity",
    )
    path.write_text(text, encoding="utf-8")


def patch_r4_test_and_config() -> None:
    test_path = PROJECT / "tests/test_r4_authentic_episodes.py"
    text = test_path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        '    expected = ("ORIENT", "PROPOSE", "VERIFY", "EVALUATE", "EFFECT", "RESPOND")\n',
        '    expected = ("ORIENT", "PROPOSE", "VERIFY", "EVALUATE", "EFFECT", "REALIZE")\n',
        "R4 phase expectation",
    )
    test_path.write_text(text, encoding="utf-8")

    config_path = PROJECT / "configs/validation_gates.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    owner = config["steps"]["r3_situation_context_owner_tests"]["exact_nodes"]
    owner_nodes = (
        "tests/test_r3_r4_predecessor_regressions.py::test_designation_reference_slots_bind_exact_reference_contributions",
        "tests/test_r3_r4_predecessor_regressions.py::test_event_frames_receive_only_missing_situated_participant_roles",
        "tests/test_r3_r4_predecessor_regressions.py::test_orientation_permission_snapshot_is_set_like",
    )
    for node in owner_nodes:
        if node not in owner:
            owner.append(node)
    owner.sort()
    phase = config["steps"]["r3_phase_tests"]["exact_nodes"]
    phase_node = "tests/test_r3_r4_predecessor_regressions.py::test_public_greeting_completes_r3_and_persists_no_effect_without_world_mutation"
    if phase_node not in phase:
        phase.append(phase_node)
    phase.sort()
    for step_name in ("r3_situation_context_owner_tests", "r3_phase_tests"):
        inputs = config["steps"][step_name]["inputs"]
        test_file = "tests/test_r3_r4_predecessor_regressions.py"
        if test_file not in inputs:
            inputs.append(test_file)
        inputs.sort()
    config_path.write_text(
        json.dumps(config, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def refresh_governance() -> None:
    env = {**dict(__import__("os").environ), "PYTHONPATH": "src:scripts:."}
    subprocess.run(
        [sys.executable, "scripts/refresh_r3_r4_test_metadata.py"],
        cwd=PROJECT,
        env=env,
        check=True,
    )
    sys.path.insert(0, str(PROJECT / "src"))
    sys.path.insert(0, str(PROJECT / "scripts"))
    from cemm_authoritative_hybrid import process_control as process_control_module
    sys.modules["process_control"] = process_control_module
    from test_inventory_core import load_and_verify, verify_document_authority_pin
    from validation_gate import InventorySelector, _expected_g0_inventory_receipt, canonical_json_bytes

    inventory_path = PROJECT / "governance/test_inventory.json"
    inventory_sha = verify_document_authority_pin(PROJECT, inventory_path)
    inventory = load_and_verify(
        PROJECT,
        inventory_path,
        phase="G0",
        enforce_reviewed_counts=True,
        expected_sha256=inventory_sha,
    )
    selector = InventorySelector(
        phase="G0",
        inventory_ref=inventory.inventory_ref,
        literal_metadata_ref=inventory.literal_metadata_ref,
        active_node_set_ref=inventory.active_node_set_ref,
        active_node_ids=inventory.active_node_ids,
        collectable_node_set_ref=inventory.collectable_node_set_ref,
        collectable_node_ids=inventory.collectable_node_ids,
    )
    authority_raw = (PROJECT / "docs/DOCUMENT_AUTHORITY.json").read_bytes()
    receipt = _expected_g0_inventory_receipt(
        authority_sha256=hashlib.sha256(authority_raw).hexdigest(),
        inventory_sha256=inventory_sha,
        inventory=inventory,
        selector=selector,
    )
    (PROJECT / "artifacts/validation/TEST_INVENTORY_RECEIPT.json").write_bytes(
        canonical_json_bytes(receipt)
    )


def main() -> None:
    patch_proposal_context()
    patch_runtime()
    patch_cycle()
    patch_r4_test_and_config()
    refresh_governance()


if __name__ == "__main__":
    main()
