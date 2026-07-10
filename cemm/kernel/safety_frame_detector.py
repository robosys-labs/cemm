"""SafetyFrameDetector — meaning-based safety derivation from state transmutations.

Safety is a property of state transmutations, not of input text or graph atoms.
The detector consumes StateTransmutationFrames — the authority units that
describe resolved state transitions with prior state, proposed state, direction,
authority, and persistence policy.

Derivation rules:
    self_harm              = vital.* harmful direction on entity kind "self", kind=commanded/desired
    interpersonal_violence = vital.* harmful direction on entity kind "person", permission_policy=restricted
    illegal_activity       = permission_policy == "restricted" (any state family)
    medical_risk           = vital.* harmful direction, permission_policy == "normal", risk == "high"

Priority: self_harm > interpersonal_violence > illegal_activity > medical_risk

Severity is assessed from:
    - Schema risk level
    - Magnitude of change (direction + prior_value from StateOccupancyFrame)
    - Number of harmful vital dimensions affected simultaneously
    - Transmutation kind (commanded > desired > reported > inferred)

Harmful direction is data-driven via ``harmful_polarity`` in
``state_dimension_schemas.json``.
"""

from __future__ import annotations

from typing import Any

from ..types.meaning_percept import SafetyFrame, OutcomeAtom, SituationFrame
from ..types.state_transmutation import StateOccupancyFrame, StateTransmutationFrame
from .semantic_schema_kernel import SemanticSchemaKernel, get_kernel

# Safety category priority (highest first)
_PRIORITY_ORDER = [
    "self_harm",
    "interpersonal_violence",
    "illegal_activity",
    "medical_risk",
]

_RISK_TO_SEVERITY: dict[str, str] = {
    "critical": "high",
    "high": "high",
    "medium": "medium",
    "low": "low",
}

_MUST_NOT_DO: dict[str, list[str]] = {
    "self_harm": ["encourage", "provide_methods", "minimize"],
    "interpersonal_violence": ["encourage", "agree", "provide_methods", "minimize_risk"],
    "illegal_activity": ["encourage", "assist", "provide_methods"],
    "medical_risk": ["diagnose", "prescribe", "dismiss"],
}

_RESPONSE_MODE: dict[str, str] = {
    "self_harm": "deescalate",
    "interpersonal_violence": "deescalate",
    "illegal_activity": "refuse",
    "medical_risk": "safe_info",
}


class SafetyFrameDetector:
    """Detects safety-relevant frames from state transmutations.

    Safety is derived from StateTransmutationFrames — the authority units that
    describe resolved state transitions. The detector inspects each transmutation's
    state family, dimension, direction, target entity, transmutation kind, and
    prior value to classify and assess safety severity.
    """

    def __init__(self, schema_kernel: SemanticSchemaKernel | None = None) -> None:
        self._kernel = schema_kernel or get_kernel()

    def detect(
        self,
        transmutations: list[StateTransmutationFrame] | None = None,
        occupancy_frames: list[StateOccupancyFrame] | None = None,
        situation: SituationFrame | None = None,
        uol_graph: Any | None = None,
        valences: list[Any] | None = None,
    ) -> SafetyFrame | None:
        """Analyze state transmutations for safety concerns.

        Primary detection path: inspect StateTransmutationFrames for harmful
        state changes on safety-relevant dimensions.

        Fallback path: if no transmutations are available but a UOL graph is,
        inspect graph state delta atoms directly (backward compatibility).

        Returns a SafetyFrame if a safety concern is detected, None otherwise.
        """
        candidates: list[SafetyFrame] = []

        # Primary: Transmutation-based detection
        if transmutations:
            occupancy_index = self._index_occupancy(occupancy_frames or [])
            candidates.extend(self._detect_from_transmutations(transmutations, occupancy_index))

        # Fallback: Graph-based detection (for backward compatibility when
        # transmutations are not yet compiled — e.g., early in pipeline or tests)
        if not candidates and uol_graph is not None:
            candidates.extend(self._detect_from_graph(uol_graph))

        # Fallback: Situation frame outcome-based detection
        if not candidates and situation is not None:
            candidates.extend(self._detect_from_situation(situation))

        if not candidates:
            return None

        # Return highest-priority candidate
        candidates.sort(key=lambda sf: _PRIORITY_ORDER.index(sf.category) if sf.category in _PRIORITY_ORDER else 99)
        return candidates[0]

    # ── Primary: Transmutation-based detection ─────────────────────

    def _detect_from_transmutations(
        self,
        transmutations: list[StateTransmutationFrame],
        occupancy_index: dict[str, StateOccupancyFrame],
    ) -> list[SafetyFrame]:
        """Inspect StateTransmutationFrames for harmful state changes."""
        results: list[SafetyFrame] = []
        state_dims = self._kernel.state_dimensions
        action_ops = self._kernel.action_operators

        # Group harmful transmutations by action_key for multi-delta severity assessment
        harmful_by_action: dict[str, list[StateTransmutationFrame]] = {}

        for stm in transmutations:
            state_family = stm.state_family
            dim_name = stm.dimension
            direction = stm.direction

            # Check if this dimension is safety-relevant and direction is harmful
            if not state_dims.is_safety_relevant(state_family, dim_name):
                continue
            if not state_dims.is_harmful_direction(state_family, dim_name, direction):
                continue

            action_key = stm.features.get("action_key", "")
            target_ref = stm.target_ref

            # Determine target entity kind from target_ref
            target_kind = self._entity_kind_from_ref(target_ref)

            # Get schema properties
            permission_policy = action_ops.permission_policy_for(action_key) if action_key else stm.features.get("permission_policy", "normal")
            risk = action_ops.risk_for(action_key) if action_key else stm.features.get("risk", "medium")

            category = self._classify_safety(
                state_family, target_kind, permission_policy, risk,
                stm.transmutation_kind,
            )
            if category is None:
                continue

            harmful_by_action.setdefault(action_key or target_ref, []).append(stm)

            # Assess severity from prior state, risk, and transmutation kind
            severity = self._assess_severity(
                risk, stm, occupancy_index, state_family, dim_name,
            )

            # Build harmful outcomes from the transmutation
            harmful_outcome = OutcomeAtom(
                affected_entity_role=stm.features.get("target_role", "target"),
                changed_dimension=f"{state_family}.{dim_name}",
                direction=direction,
                event_key=action_key,
                confidence=stm.confidence,
            )

            results.append(SafetyFrame(
                category=category,
                severity=severity,
                requested_action=action_key or f"{state_family}.{dim_name}",
                target_entity_id=target_kind,
                harmful_outcomes=[harmful_outcome],
                allowed_response_mode=_RESPONSE_MODE.get(category, "refuse"),
                must_not_do=_MUST_NOT_DO.get(category, ["encourage"]),
                confidence=stm.confidence,
            ))

        # Also check for restricted permission_policy actions without vital deltas
        existing_keys = {sf.requested_action for sf in results}
        for stm in transmutations:
            action_key = stm.features.get("action_key", "")
            if not action_key or action_key in existing_keys:
                continue
            permission_policy = action_ops.permission_policy_for(action_key)
            if permission_policy == "restricted":
                risk = action_ops.risk_for(action_key)
                category = "illegal_activity"
                severity = _RISK_TO_SEVERITY.get(risk, "medium")
                results.append(SafetyFrame(
                    category=category,
                    severity=severity,
                    requested_action=action_key,
                    allowed_response_mode=_RESPONSE_MODE.get(category, "refuse"),
                    must_not_do=_MUST_NOT_DO.get(category, ["encourage"]),
                    confidence=stm.confidence,
                ))
                existing_keys.add(action_key)

        # Upgrade severity when multiple vital dimensions are affected by same action
        for action_key, stms in harmful_by_action.items():
            vital_count = sum(1 for s in stms if s.state_family == "vital")
            if vital_count > 1:
                for sf in results:
                    if sf.requested_action == action_key and sf.severity != "high":
                        sf.severity = "high"

        return results

    @staticmethod
    def _index_occupancy(
        occupancy_frames: list[StateOccupancyFrame],
    ) -> dict[str, StateOccupancyFrame]:
        index: dict[str, StateOccupancyFrame] = {}
        for occ in occupancy_frames:
            key = f"{occ.target_ref}:{occ.state_family}.{occ.dimension}"
            index[key] = occ
        return index

    @staticmethod
    def _entity_kind_from_ref(target_ref: str) -> str:
        """Extract entity kind from a target_ref string like 'entity:user' or 'self'."""
        if not target_ref:
            return ""
        if "self" in target_ref:
            return "self"
        if "user" in target_ref:
            return "person"
        if "person" in target_ref:
            return "person"
        if "animal" in target_ref:
            return "animal"
        if target_ref.startswith("role:"):
            role = target_ref[5:]
            if role in ("self", "actor"):
                return "self"
            return "person"
        return ""

    def _assess_severity(
        self,
        risk: str,
        stm: StateTransmutationFrame,
        occupancy_index: dict[str, StateOccupancyFrame],
        state_family: str,
        dim_name: str,
    ) -> str:
        """Assess severity from risk level, prior state, and transmutation kind."""
        base_severity = _RISK_TO_SEVERITY.get(risk, "medium")

        # Assess magnitude from prior state if available
        occ_key = f"{stm.target_ref}:{state_family}.{dim_name}"
        prior = occupancy_index.get(occ_key)
        if prior is not None and prior.current_value is not None:
            try:
                prior_val = float(prior.current_value)
                # If prior state is already near harmful polarity, upgrade severity
                harmful_polarity = self._get_harmful_polarity(state_family, dim_name)
                if harmful_polarity == "negative" and prior_val < 0.3:
                    base_severity = "high"
                elif harmful_polarity == "positive" and prior_val > 0.7:
                    base_severity = "high"
            except (ValueError, TypeError):
                pass

        # Transmutation kind affects severity: commanded/desired > reported > inferred
        if stm.transmutation_kind in ("commanded", "desired") and base_severity == "medium":
            base_severity = "high"

        return base_severity

    def _get_harmful_polarity(self, state_family: str, dim_name: str) -> str:
        """Get the harmful_polarity for a dimension from the schema."""
        schema = self._kernel.state_dimensions.get(state_family)
        if schema is None:
            return ""
        dim_def = schema.dimensions.get(dim_name, {})
        return dim_def.get("harmful_polarity", "")

    # ── Fallback: Graph-based detection (backward compatibility) ────

    def _detect_from_graph(self, graph: Any) -> list[SafetyFrame]:
        """Inspect state delta atoms and causes edges in the UOL graph."""
        results: list[SafetyFrame] = []
        state_dims = self._kernel.state_dimensions
        action_ops = self._kernel.action_operators

        for atom in graph.atoms.values():
            if atom.kind != "state" or atom.source != "schema_state_delta":
                continue

            dimension = atom.features.get("dimension", "")
            direction = atom.features.get("direction", "")
            target_role = atom.features.get("target_role", "actor")
            action_key = atom.features.get("action_key", "")

            if not dimension or not direction:
                continue

            parts = dimension.split(".", 1)
            if len(parts) != 2:
                continue
            state_family, dim_name = parts

            if not state_dims.is_safety_relevant(state_family, dim_name):
                continue
            if not state_dims.is_harmful_direction(state_family, dim_name, direction):
                continue

            action_atom = self._find_causing_action(graph, atom.id)
            if action_atom is None:
                continue

            target_kind = self._entity_kind_for_role(graph, action_atom, target_role)

            permission_policy = action_ops.permission_policy_for(action_key)
            risk = action_ops.risk_for(action_key)

            category = self._classify_safety(
                state_family, target_kind, permission_policy, risk,
            )
            if category is None:
                continue

            severity = _RISK_TO_SEVERITY.get(risk, "medium")
            results.append(SafetyFrame(
                category=category,
                severity=severity,
                requested_action=action_key,
                target_entity_id=target_kind,
                allowed_response_mode=_RESPONSE_MODE.get(category, "refuse"),
                must_not_do=_MUST_NOT_DO.get(category, ["encourage"]),
                confidence=atom.confidence,
            ))

        # Also check for restricted permission_policy without vital state deltas
        existing_keys = {sf.requested_action for sf in results}
        for atom in graph.atoms.values():
            if atom.kind != "action":
                continue
            action_key = atom.key
            if action_key in existing_keys:
                continue
            permission_policy = action_ops.permission_policy_for(action_key)
            if permission_policy == "restricted":
                risk = action_ops.risk_for(action_key)
                category = "illegal_activity"
                severity = _RISK_TO_SEVERITY.get(risk, "medium")
                results.append(SafetyFrame(
                    category=category,
                    severity=severity,
                    requested_action=action_key,
                    allowed_response_mode=_RESPONSE_MODE.get(category, "refuse"),
                    must_not_do=_MUST_NOT_DO.get(category, ["encourage"]),
                    confidence=atom.confidence,
                ))
                existing_keys.add(action_key)

        return results

    @staticmethod
    def _find_causing_action(graph: Any, state_atom_id: str) -> Any | None:
        """Find the action atom that causes a given state atom via causes edge."""
        for edge in graph.incoming(state_atom_id, "causes"):
            source = graph.atoms.get(edge.source_id)
            if source is not None and source.kind == "action":
                return source
        return None

    @staticmethod
    def _entity_kind_for_role(graph: Any, action_atom: Any, role: str) -> str:
        """Determine entity kind for a role via has_role edges."""
        for edge in graph.outgoing(action_atom.id, "has_role"):
            if edge.features.get("role") == role:
                return edge.features.get("entity_kind", "")
        return ""

    # ── Fallback: Situation frame outcome-based detection ───────────

    def _detect_from_situation(self, situation: SituationFrame) -> list[SafetyFrame]:
        """Use expected_outcomes from SituationFrame for safety classification."""
        results: list[SafetyFrame] = []
        if not situation.expected_outcomes:
            return results

        action_ops = self._kernel.action_operators
        state_dims = self._kernel.state_dimensions

        for outcome in situation.expected_outcomes:
            dimension = outcome.changed_dimension or ""
            direction = outcome.direction or ""
            target_role = outcome.affected_entity_role or "target"

            parts = dimension.split(".", 1)
            if len(parts) != 2:
                continue
            state_family, dim_name = parts

            if not state_dims.is_safety_relevant(state_family, dim_name):
                continue
            if not state_dims.is_harmful_direction(state_family, dim_name, direction):
                continue

            target_kind = self._infer_target_kind(situation, target_role)

            action_key = ""
            if situation.action:
                action_key = situation.action.action_key or ""

            permission_policy = action_ops.permission_policy_for(action_key) if action_key else "normal"
            risk = action_ops.risk_for(action_key) if action_key else "low"

            category = self._classify_safety(
                state_family, target_kind, permission_policy, risk,
            )
            if category is None:
                continue

            severity = _RISK_TO_SEVERITY.get(risk, "medium")
            results.append(SafetyFrame(
                category=category,
                severity=severity,
                requested_action=action_key or outcome.changed_dimension,
                target_entity_id=target_kind,
                allowed_response_mode=_RESPONSE_MODE.get(category, "refuse"),
                must_not_do=_MUST_NOT_DO.get(category, ["encourage"]),
                confidence=outcome.confidence if hasattr(outcome, "confidence") else 0.7,
            ))

        # Also check for restricted permission_policy from situation action
        if situation.action and situation.action.action_key:
            action_key = situation.action.action_key
            existing_keys = {sf.requested_action for sf in results}
            if action_key not in existing_keys:
                permission_policy = action_ops.permission_policy_for(action_key)
                if permission_policy == "restricted":
                    risk = action_ops.risk_for(action_key)
                    category = "illegal_activity"
                    severity = _RISK_TO_SEVERITY.get(risk, "medium")
                    results.append(SafetyFrame(
                        category=category,
                        severity=severity,
                        requested_action=action_key,
                        allowed_response_mode=_RESPONSE_MODE.get(category, "refuse"),
                        must_not_do=_MUST_NOT_DO.get(category, ["encourage"]),
                        confidence=0.7,
                    ))

        return results

    @staticmethod
    def _infer_target_kind(situation: SituationFrame, target_role: str) -> str:
        """Infer entity kind from situation frame roles."""
        if target_role in ("self", "actor"):
            return "self"
        if target_role in ("target", "object", "recipient"):
            if situation.action:
                target_role_val = getattr(situation.action, "target_role", "")
                if target_role_val in ("self", "myself"):
                    return "self"
            return "person"
        return "person"

    # ── Classification logic ────────────────────────────────────────

    @staticmethod
    def _classify_safety(
        state_family: str,
        target_kind: str,
        permission_policy: str,
        risk: str,
        transmutation_kind: str = "",
    ) -> str | None:
        """Classify safety category from compositional primitives.

        Args:
            state_family: e.g. "vital", "permission"
            target_kind: entity kind of the target (e.g. "self", "person")
            permission_policy: "normal" or "restricted"
            risk: "low", "medium", "high", "critical"
            transmutation_kind: "commanded", "desired", "reported", "inferred"

        Returns:
            Safety category string or None if not safety-relevant.
        """
        if state_family == "vital":
            if target_kind == "self":
                return "self_harm"
            if target_kind in ("person", "animal"):
                if permission_policy == "restricted":
                    return "interpersonal_violence"
                return "medical_risk"
            if permission_policy == "restricted":
                return "interpersonal_violence"
            return None

        if permission_policy == "restricted":
            return "illegal_activity"

        return None
