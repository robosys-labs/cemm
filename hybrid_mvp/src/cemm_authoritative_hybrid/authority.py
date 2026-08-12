"""Linked semantic authority: reviewed source records, bounded indexes, hashes.

This module owns :class:`AuthorityBundle`, :class:`LinkedAuthority`, and
:class:`AuthorityLinker`. The linker validates owner, kind, five-operator
role schemas, refs, designations, rules, frames, transition signatures,
capabilities, permissions, policies, adapters, and explicit designations
before returning a :class:`LinkedAuthority`. It builds bounded indexes for
surface/language, target designations, kind, frame, rule signature, state
dimension, event signature, and transition. It emits both a full
content/generation hash and a model-compatibility hash over only the
contribution ABI, semantic kinds/ports, structural action ABI, and model
feature encoding. Compatible reviewed identities, designations, facts, and
rules change the full generation without invalidating weights; any structural
encoding change changes the compatibility hash and blocks model activation
until retraining.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from .canonical import sha256_governed_text, stable_ref

__all__ = [
    "AuthorityLinkError",
    "AuthorityStore",
    "AuthorityBundle",
    "DesignationIndex",
    "LinkedAuthority",
    "AuthorityLinker",
    "AtomRecord",
    "RoleSpec",
    "EventSignature",
    "RuleRecord",
]

FIXED_OPERATORS = frozenset({
    "op:designation", "op:type", "op:relation", "op:state", "op:event",
})


# ---------------------------------------------------------------------------
# Authority record types (owned here)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AtomRecord:
    ref: str
    kind: str
    reviewed: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RoleSpec:
    role: str
    filler_kinds: tuple[str, ...]
    required: bool = True
    proposition_valued: bool = False


@dataclass(frozen=True)
class EventSignature:
    event_type: str
    roles: tuple[RoleSpec, ...]
    valid_session_phases: tuple[str, ...] = ("opening", "active")
    required_capabilities: tuple[str, ...] = ()
    required_permissions: tuple[str, ...] = ()
    adapter_ref: str | None = None
    effect_schema: tuple[Mapping[str, Any], ...] = ()

    @property
    def required_roles(self) -> frozenset[str]:
        return frozenset(item.role for item in self.roles if item.required)


@dataclass(frozen=True)
class RuleRecord:
    rule_ref: str
    antecedent: tuple[Mapping[str, Any], ...]
    consequent: tuple[Mapping[str, Any], ...]
    confidence: float = 1.0
    reviewed: bool = True
    source_ref: str | None = None


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class AuthorityLinkError(Exception):
    """Raised when authority linking fails validation."""


# ---------------------------------------------------------------------------
# AuthorityStore — tracks the active generation
# ---------------------------------------------------------------------------


class AuthorityStore:
    """Holds raw authority data and tracks the active generation.

    ``active_generation`` is set to the generation string on a successful
    link and remains ``None`` on failure.
    """

    __slots__ = ("active_generation",)

    def __init__(self) -> None:
        self.active_generation: str | None = None


# ---------------------------------------------------------------------------
# AuthorityBundle — raw source records + manifest + store
# ---------------------------------------------------------------------------


class AuthorityBundle:
    """Holds raw source records from owner files with a manifest and store.

    The ``manifest`` property returns the manifest dict augmented with a
    ``_store`` key so the linker can set ``active_generation`` on success.
    """

    def __init__(self, manifest_data: Mapping[str, Any], store: AuthorityStore) -> None:
        self._manifest_data = dict(manifest_data)
        self._store = store

    @property
    def manifest(self) -> Mapping[str, Any]:
        """Return manifest dict with store reference for generation tracking."""
        return {**self._manifest_data, "_store": self._store}

    @property
    def store(self) -> AuthorityStore:
        return self._store


# ---------------------------------------------------------------------------
# DesignationIndex — bounded surface/target lookup
# ---------------------------------------------------------------------------


class DesignationIndex:
    """Bounded index for surface→target and target→surface designations.

    Only explicit designations in the source data create entries. Internal
    refs are never automatically lexicalized into surfaces.
    """

    __slots__ = ("_by_surface", "_by_folded_surface", "_by_target")

    def __init__(
        self,
        by_surface: Mapping[tuple[str, str], tuple[str, ...]],
        by_target: Mapping[tuple[str, str], tuple[str, ...]],
    ) -> None:
        self._by_surface = dict(by_surface)
        self._by_target = dict(by_target)
        folded: dict[tuple[str, str], list[str]] = {}
        for (surface, language), targets in self._by_surface.items():
            bucket = folded.setdefault((surface.casefold(), language), [])
            for target in targets:
                if target not in bucket:
                    bucket.append(target)
        self._by_folded_surface = {
            key: tuple(targets) for key, targets in folded.items()
        }

    def for_surface(self, surface: str, language: str) -> tuple[str, ...]:
        """Return target refs designated by ``surface`` in ``language``.

        Exact reviewed identity wins.  A bounded Unicode case-folded lookup is
        used only when the exact surface is absent; collisions remain explicit
        alternatives rather than being resolved by spelling heuristics.
        """
        exact = self._by_surface.get((surface, language), ())
        if exact:
            return exact
        return self._by_folded_surface.get((surface.casefold(), language), ())

    def for_target(self, target: str, language: str) -> tuple[str, ...]:
        """Return surfaces that designate ``target`` in ``language``."""
        return self._by_target.get((target, language), ())

    def canonical_surface_for_target(
        self,
        surface: str,
        target: str,
        language: str,
    ) -> str | None:
        """Return the linked surface identity matching one target.

        Exact target-linked surfaces are preserved.  Case-folded recovery is
        admitted only when it identifies one canonical reviewed surface for
        the target; ambiguous folded spellings fail closed.
        """
        exact_targets = self._by_surface.get((surface, language), ())
        if target in exact_targets:
            return surface
        matches = tuple(
            candidate
            for candidate in self._by_target.get((target, language), ())
            if candidate.casefold() == surface.casefold()
        )
        return matches[0] if len(matches) == 1 else None


# ---------------------------------------------------------------------------
# LinkedAuthority — validated, indexed result of linking
# ---------------------------------------------------------------------------


class LinkedAuthority:
    """The validated, indexed result of linking one authority generation.

    Attributes:
        content_hash: full generation hash over all content.
        model_compatibility_hash: hash over structural encoding only.
        generation: the authority generation string.
        designations: :class:`DesignationIndex` for surface/target lookup.
        atoms: dict of ref → :class:`AtomRecord`.
        event_signatures: dict of event_type → :class:`EventSignature`.
        rules: dict of rule_ref → :class:`RuleRecord`.
        capabilities: dict of participant → list of capability refs.
        permissions: tuple of (participant, permission, event) triples.
        adapters: tuple of adapter refs.
        operator_roles: dict of operator → list of role names.
        value_dimensions: dict of value ref → dimension ref.
    """

    __slots__ = (
        "content_hash",
        "model_compatibility_hash",
        "generation",
        "designations",
        "atoms",
        "event_signatures",
        "rules",
        "capabilities",
        "permissions",
        "adapters",
        "operator_roles",
        "value_dimensions",
        "definition_targets",
        "_by_kind",
        "_by_frame",
        "_by_rule_signature",
        "_by_state_dimension",
        "_by_event_signature",
        "_by_transition",
        "_by_transition_signature",
    )

    def __init__(
        self,
        content_hash: str,
        model_compatibility_hash: str,
        generation: str,
        designations: DesignationIndex,
        atoms: dict[str, AtomRecord],
        event_signatures: dict[str, EventSignature],
        rules: dict[str, RuleRecord],
        capabilities: dict[str, list[str]],
        permissions: tuple[tuple[str, str, str], ...],
        adapters: tuple[str, ...],
        operator_roles: dict[str, list[str]],
        value_dimensions: dict[str, str],
        definition_targets: dict[str, str],
        by_kind: dict[str, frozenset[str]],
        by_frame: dict[str, frozenset[str]],
        by_rule_signature: dict[str, dict[str, Any]],
        by_state_dimension: dict[str, frozenset[str]],
        by_event_signature: dict[str, EventSignature],
        by_transition: dict[str, dict[str, Any]],
        by_transition_signature: dict[tuple[str, str, str], dict[str, Any]],
    ) -> None:
        self.content_hash = content_hash
        self.model_compatibility_hash = model_compatibility_hash
        self.generation = generation
        self.designations = designations
        self.atoms = atoms
        self.event_signatures = event_signatures
        self.rules = rules
        self.capabilities = capabilities
        self.permissions = permissions
        self.adapters = adapters
        self.operator_roles = operator_roles
        self.value_dimensions = value_dimensions
        self.definition_targets = definition_targets
        self._by_kind = by_kind
        self._by_frame = by_frame
        self._by_rule_signature = by_rule_signature
        self._by_state_dimension = by_state_dimension
        self._by_event_signature = by_event_signature
        self._by_transition = by_transition
        self._by_transition_signature = by_transition_signature

    def by_kind(self, kind: str) -> frozenset[str]:
        """Return all atom refs of the given kind."""
        return self._by_kind.get(kind, frozenset())

    def by_frame(self, frame: str) -> frozenset[str]:
        """Return all atom refs in the given frame."""
        return self._by_frame.get(frame, frozenset())

    def by_rule_signature(self, rule_ref: str) -> dict[str, Any] | None:
        """Return the raw rule data for ``rule_ref``."""
        return self._by_rule_signature.get(rule_ref)

    def by_state_dimension(self, dimension: str) -> frozenset[str]:
        """Return all value refs for the given state dimension."""
        return self._by_state_dimension.get(dimension, frozenset())

    def by_event_signature(self, event_type: str) -> EventSignature | None:
        """Return the event signature for ``event_type``."""
        return self._by_event_signature.get(event_type)

    def by_transition(self, key: str) -> dict[str, Any] | None:
        """Return the transition for ``key``."""
        return self._by_transition.get(key)

    def transition_for(
        self, event_type: str, dimension: str, to_value: str
    ) -> dict[str, Any] | None:
        """Return the exact reviewed transition matching an application."""
        return self._by_transition_signature.get((event_type, dimension, to_value))


# ---------------------------------------------------------------------------
# AuthorityLinker — validates and links authority source records
# ---------------------------------------------------------------------------


class AuthorityLinker:
    """Validates owner files and returns a :class:`LinkedAuthority`.

    ``link`` accepts either a manifest file path or a manifest dict (which may
    carry a ``_store`` key for generation tracking). ``link_path`` accepts a
    path to a manifest JSON file.
    """

    def link(self, manifest: Any) -> LinkedAuthority:
        if isinstance(manifest, (str, Path)):
            return self._link_from_path(Path(manifest))
        if isinstance(manifest, Mapping):
            return self._link_from_dict(manifest)
        raise AuthorityLinkError(f"unsupported manifest type: {type(manifest)}")

    def link_path(self, path: str | Path) -> LinkedAuthority:
        return self._link_from_path(Path(path))

    # -- internal ----------------------------------------------------------

    def _link_from_path(self, path: Path) -> LinkedAuthority:
        path = path.resolve()
        if not path.exists():
            raise AuthorityLinkError(f"manifest not found: {path}")
        manifest_data = json.loads(path.read_text(encoding="utf-8-sig"))
        return self._link_manifest(manifest_data, base_dir=path.parent, store=None)

    def _link_from_dict(self, manifest_dict: Mapping[str, Any]) -> LinkedAuthority:
        store = manifest_dict.get("_store")
        return self._link_manifest(manifest_dict, base_dir=None, store=store)

    def _link_manifest(
        self,
        manifest_data: Mapping[str, Any],
        base_dir: Path | None,
        store: AuthorityStore | None,
    ) -> LinkedAuthority:
        generation = manifest_data.get("generation")
        if not generation:
            raise AuthorityLinkError("manifest missing generation")
        abi_version = manifest_data.get("abi_version", 1)
        owners_meta = manifest_data.get("owners", [])
        if not owners_meta:
            raise AuthorityLinkError("manifest has no owners")

        # Accumulators for merged data across all owners
        all_atoms: dict[str, tuple[AtomRecord, str]] = {}
        all_designations: list[dict[str, Any]] = []
        all_event_signatures: list[dict[str, Any]] = []
        all_rules: list[dict[str, Any]] = []
        all_capabilities: dict[str, list[str]] = {}
        all_permissions: list[list[str]] = []
        all_adapters: list[str] = []
        all_operator_roles: dict[str, list[str]] = {}
        all_value_dimensions: dict[str, str] = {}
        all_definition_targets: dict[str, str] = {}
        all_transitions: list[dict[str, Any]] = []

        # Load and validate each owner file
        for owner_meta in owners_meta:
            owner_name = owner_meta["name"]
            owner_path = Path(owner_meta["path"])
            if not owner_path.is_absolute():
                if base_dir is None:
                    raise AuthorityLinkError(
                        f"cannot resolve relative path without base dir: {owner_path}"
                    )
                owner_path = base_dir / owner_path

            # Verify file hash
            actual_hash = sha256_governed_text(owner_path)
            if actual_hash != owner_meta["sha256"]:
                raise AuthorityLinkError(
                    f"owner {owner_name} hash mismatch"
                )

            owner_data = json.loads(owner_path.read_text(encoding="utf-8-sig"))

            # Validate and collect atoms
            for atom_data in owner_data.get("atoms", []):
                ref = atom_data["ref"]
                kind = atom_data["kind"]
                reviewed = atom_data.get("reviewed", True)
                if not reviewed:
                    raise AuthorityLinkError(f"unreviewed atom: {ref}")
                if ref in all_atoms:
                    raise AuthorityLinkError(
                        f"duplicate owner for atom {ref}: "
                        f"{all_atoms[ref][1]} and {owner_name}"
                    )
                all_atoms[ref] = (
                    AtomRecord(ref=ref, kind=kind, reviewed=reviewed),
                    owner_name,
                )

            all_designations.extend(owner_data.get("designations", []))
            all_event_signatures.extend(owner_data.get("event_signatures", []))
            all_rules.extend(owner_data.get("rules", []))

            for participant, caps in owner_data.get("capabilities", {}).items():
                existing = all_capabilities.setdefault(participant, [])
                existing.extend(caps)

            all_permissions.extend(owner_data.get("permissions", []))
            all_adapters.extend(owner_data.get("adapters", []))

            for op, roles in owner_data.get("operator_roles", {}).items():
                all_operator_roles[op] = list(roles)

            for value, dim in owner_data.get("value_dimensions", {}).items():
                all_value_dimensions[value] = dim

            for source, target in owner_data.get("definition_targets", {}).items():
                if source in all_definition_targets:
                    raise AuthorityLinkError(
                        f"duplicate definition target owner: {source}"
                    )
                all_definition_targets[source] = target

            all_transitions.extend(owner_data.get("transitions", []))

        # -- Validate designations (targets must exist) --------------------
        for desig in all_designations:
            target = desig["target"]
            if target not in all_atoms:
                raise AuthorityLinkError(f"missing target: {target}")

        # -- Validate operator role schemas --------------------------------
        for op in FIXED_OPERATORS:
            if op not in all_operator_roles:
                raise AuthorityLinkError(f"missing operator role schema: {op}")

        # -- Validate event signatures -------------------------------------
        for es in all_event_signatures:
            event_type = es["event_type"]
            if event_type not in all_atoms:
                raise AuthorityLinkError(
                    f"event signature references unknown event: {event_type}"
                )
            for cap in es.get("required_capabilities", []):
                if cap not in all_atoms:
                    raise AuthorityLinkError(f"missing capability: {cap}")
            for perm in es.get("required_permissions", []):
                if perm not in all_atoms:
                    raise AuthorityLinkError(f"missing permission: {perm}")
            adapter = es.get("adapter_ref")
            if adapter and adapter not in all_atoms:
                raise AuthorityLinkError(f"missing adapter: {adapter}")

        # -- Validate capabilities -----------------------------------------
        for participant, caps in all_capabilities.items():
            if participant not in all_atoms:
                raise AuthorityLinkError(f"missing participant: {participant}")
            for cap in caps:
                if cap not in all_atoms:
                    raise AuthorityLinkError(f"missing capability atom: {cap}")

        # -- Validate permissions ------------------------------------------
        for perm in all_permissions:
            participant, perm_ref, event_ref = perm[0], perm[1], perm[2]
            if participant not in all_atoms:
                raise AuthorityLinkError(f"missing participant: {participant}")
            if perm_ref not in all_atoms:
                raise AuthorityLinkError(f"missing permission atom: {perm_ref}")
            if event_ref not in all_atoms:
                raise AuthorityLinkError(f"missing event atom: {event_ref}")

        # -- Validate adapters ---------------------------------------------
        for adapter in all_adapters:
            if adapter not in all_atoms:
                raise AuthorityLinkError(f"missing adapter atom: {adapter}")

        # -- Validate value dimensions -------------------------------------
        for value, dim in all_value_dimensions.items():
            if value not in all_atoms:
                raise AuthorityLinkError(f"missing value atom: {value}")
            if dim not in all_atoms:
                raise AuthorityLinkError(f"missing dimension atom: {dim}")

        # -- Validate reviewed transitions ---------------------------------
        transition_signatures: set[tuple[str, str, str]] = set()
        transition_refs: set[str] = set()
        for transition in all_transitions:
            required = ("transition_ref", "event_type", "dimension", "to_value")
            if any(
                type(transition.get(field)) is not str or not transition.get(field)
                for field in required
            ):
                raise AuthorityLinkError("transition record is structurally incomplete")
            transition_ref = transition["transition_ref"]
            if transition_ref in transition_refs:
                raise AuthorityLinkError(f"duplicate transition ref: {transition_ref}")
            transition_refs.add(transition_ref)
            event_type = transition["event_type"]
            dimension = transition["dimension"]
            to_value = transition["to_value"]
            from_value = transition.get("from_value")
            if event_type not in all_atoms or all_atoms[event_type][0].kind != "event_type":
                raise AuthorityLinkError(f"transition event is invalid: {event_type}")
            if dimension not in all_atoms or all_atoms[dimension][0].kind != "state_dimension":
                raise AuthorityLinkError(f"transition dimension is invalid: {dimension}")
            if to_value not in all_atoms or all_value_dimensions.get(to_value) != dimension:
                raise AuthorityLinkError(f"transition target value is invalid: {to_value}")
            if from_value is not None and (
                type(from_value) is not str
                or all_value_dimensions.get(from_value) != dimension
            ):
                raise AuthorityLinkError(f"transition source value is invalid: {from_value}")
            adapter = transition.get("adapter_ref")
            if adapter is not None and adapter not in all_adapters:
                raise AuthorityLinkError(f"transition adapter is invalid: {adapter}")
            signature = (event_type, dimension, to_value)
            if signature in transition_signatures:
                raise AuthorityLinkError(
                    "duplicate event/dimension/value transition signature"
                )
            transition_signatures.add(signature)

        for source, target in all_definition_targets.items():
            if source not in all_atoms:
                raise AuthorityLinkError(f"missing definition source atom: {source}")
            if target not in all_atoms:
                raise AuthorityLinkError(f"missing definition target atom: {target}")
            if all_atoms[target][0].kind != "concept":
                raise AuthorityLinkError(
                    f"definition target must be a concept: {target}"
                )

        # -- Build indexes -------------------------------------------------
        atoms_dict = {ref: record for ref, (record, _owner) in all_atoms.items()}

        # Designation index (bounded, explicit only)
        by_surface: dict[tuple[str, str], list[str]] = {}
        by_target: dict[tuple[str, str], list[str]] = {}
        for desig in all_designations:
            surface = desig["surface"]
            target = desig["target"]
            language = desig["language"]
            by_surface.setdefault((surface, language), []).append(target)
            by_target.setdefault((target, language), []).append(surface)
        designations = DesignationIndex(
            {k: tuple(v) for k, v in by_surface.items()},
            {k: tuple(v) for k, v in by_target.items()},
        )

        # Kind index
        kind_index: dict[str, set[str]] = {}
        for ref, (record, _owner) in all_atoms.items():
            kind_index.setdefault(record.kind, set()).add(ref)
        by_kind = {k: frozenset(v) for k, v in kind_index.items()}

        # Event signature objects and index
        event_sigs: dict[str, EventSignature] = {}
        for es_data in all_event_signatures:
            roles = tuple(
                RoleSpec(
                    role=r["role"],
                    filler_kinds=tuple(r["filler_kinds"]),
                    required=r.get("required", True),
                    proposition_valued=r.get("proposition_valued", False),
                )
                for r in es_data.get("roles", [])
            )
            sig = EventSignature(
                event_type=es_data["event_type"],
                roles=roles,
                valid_session_phases=tuple(
                    es_data.get("valid_session_phases", ("opening", "active"))
                ),
                required_capabilities=tuple(es_data.get("required_capabilities", [])),
                required_permissions=tuple(es_data.get("required_permissions", [])),
                adapter_ref=es_data.get("adapter_ref"),
                effect_schema=tuple(es_data.get("effect_schema", [])),
            )
            event_sigs[es_data["event_type"]] = sig

        # Rule objects and signature index
        rules: dict[str, RuleRecord] = {}
        by_rule_sig: dict[str, dict[str, Any]] = {}
        for rule_data in all_rules:
            ref = rule_data["rule_ref"]
            rules[ref] = RuleRecord(
                rule_ref=ref,
                antecedent=tuple(rule_data.get("antecedent", [])),
                consequent=tuple(rule_data.get("consequent", [])),
                confidence=rule_data.get("confidence", 1.0),
                reviewed=rule_data.get("reviewed", True),
                source_ref=rule_data.get("source_ref"),
            )
            by_rule_sig[ref] = rule_data

        # State dimension index
        state_dim_index: dict[str, set[str]] = {}
        for value, dim in all_value_dimensions.items():
            state_dim_index.setdefault(dim, set()).add(value)
        by_state_dim = {k: frozenset(v) for k, v in state_dim_index.items()}

        # Transition index
        by_transition: dict[str, dict[str, Any]] = {}
        by_transition_signature: dict[tuple[str, str, str], dict[str, Any]] = {}
        for trans in all_transitions:
            key = trans.get("transition_ref", f"trans:{len(by_transition)}")
            by_transition[key] = trans
            by_transition_signature[
                (trans["event_type"], trans["dimension"], trans["to_value"])
            ] = trans

        # -- Compute hashes ------------------------------------------------
        full_payload = {
            "abi_version": abi_version,
            "generation": generation,
            "atoms": {
                ref: {"ref": r.ref, "kind": r.kind, "reviewed": r.reviewed}
                for ref, r in atoms_dict.items()
            },
            "designations": sorted(
                all_designations, key=lambda d: (d["surface"], d["language"], d["target"])
            ),
            "event_signatures": sorted(all_event_signatures, key=lambda e: e["event_type"]),
            "rules": sorted(all_rules, key=lambda r: r["rule_ref"]),
            "capabilities": all_capabilities,
            "permissions": sorted(all_permissions, key=lambda p: (p[0], p[1], p[2])),
            "adapters": sorted(all_adapters),
            "operator_roles": all_operator_roles,
            "value_dimensions": all_value_dimensions,
            "definition_targets": all_definition_targets,
            "transitions": sorted(
                all_transitions, key=lambda t: json.dumps(t, sort_keys=True)
            ),
        }
        content_hash = stable_ref("authority-content", full_payload)

        # Structural / compatibility payload: only encoding-relevant parts
        structural_payload = {
            "abi_version": abi_version,
            "operator_roles": all_operator_roles,
            "kinds": sorted({r.kind for r in atoms_dict.values()}),
            "event_signatures": [
                {
                    "event_type": es["event_type"],
                    "roles": es.get("roles", []),
                }
                for es in sorted(all_event_signatures, key=lambda e: e["event_type"])
            ],
            "value_dimensions": all_value_dimensions,
            "definition_targets": all_definition_targets,
        }
        model_compatibility_hash = stable_ref("authority-compat", structural_payload)

        # -- Set active generation on store --------------------------------
        if store is not None:
            store.active_generation = generation

        return LinkedAuthority(
            content_hash=content_hash,
            model_compatibility_hash=model_compatibility_hash,
            generation=generation,
            designations=designations,
            atoms=atoms_dict,
            event_signatures=event_sigs,
            rules=rules,
            capabilities=all_capabilities,
            permissions=tuple(tuple(p) for p in all_permissions),
            adapters=tuple(all_adapters),
            operator_roles=all_operator_roles,
            value_dimensions=all_value_dimensions,
            definition_targets=all_definition_targets,
            by_kind=by_kind,
            by_frame={},
            by_rule_signature=by_rule_sig,
            by_state_dimension=by_state_dim,
            by_event_signature=event_sigs,
            by_transition=by_transition,
            by_transition_signature=by_transition_signature,
        )
