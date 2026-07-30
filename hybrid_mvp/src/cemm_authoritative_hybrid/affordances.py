"""Kind-derived semantic affordances: proof-bearing admissibility profiles.

This module owns :class:`AffordanceProfile` and
:class:`SemanticAffordanceIndex`.

Default affordances are derived **only** from semantic kind — never from
surface text or ref-name spelling.  Reviewed frame atoms may refine or
replace defaults, but only when generation-pinned (linked to the authority
generation) and the target is a linked atom.  The index is bounded by
``RuntimeConfig.max_affordances_per_target``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .contributions import ContributionKind

__all__ = [
    "AffordanceProfile",
    "SemanticAffordanceIndex",
]


# ---------------------------------------------------------------------------
# AffordanceProfile
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AffordanceProfile:
    """A kind-derived admissibility profile for one semantic target.

    Attributes:
        target_ref: the semantic target ref (e.g. ``"event:greeting"``).
        contribution_kinds: tuple of :class:`ContributionKind` values.
        input_ports: tuple of input port names (e.g. ``("role:actor",)``).
        output_ports: tuple of output port names (e.g. ``("role:event",)``).
        role_candidates: tuple of candidate role names.
        frame_ref: the reviewed frame ref that refined this profile, or None
            when the profile is a kind-derived default.
    """

    target_ref: str
    contribution_kinds: tuple[ContributionKind, ...]
    input_ports: tuple[str, ...]
    output_ports: tuple[str, ...]
    role_candidates: tuple[str, ...]
    frame_ref: str | None


# ---------------------------------------------------------------------------
# Default affordance derivation by semantic kind
# ---------------------------------------------------------------------------

# Each kind maps to a tuple of default AffordanceProfile templates (without
# target_ref, which is filled in at lookup time).  The templates use
# ContributionKind values and typed ports.
#
# These defaults follow governing spec section 7:
#   event_type      → event-predicate + event-type-anchor
#   relation_type   → relation-predicate + relation-type-anchor
#   state_dimension → state-property + dimension-anchor
#   state_value     → value-anchor + state-value-predicate
#   label_type      → designation-property + label-anchor
#   concept         → nominal-anchor + type-predicate
#   entity         → referent-anchor
#   participant     → referent-anchor + participant-reference
#   capability     → capability-target + capability-predicate
#   permission     → permission-predicate
#   adapter        → adapter-reference


def _profile(
    target_ref: str,
    kinds: tuple[ContributionKind, ...],
    inputs: tuple[str, ...] = (),
    outputs: tuple[str, ...] = (),
    roles: tuple[str, ...] = (),
    frame_ref: str | None = None,
) -> AffordanceProfile:
    return AffordanceProfile(
        target_ref=target_ref,
        contribution_kinds=kinds,
        input_ports=inputs,
        output_ports=outputs,
        role_candidates=roles,
        frame_ref=frame_ref,
    )


def _default_profiles(target_ref: str, kind: str) -> tuple[AffordanceProfile, ...]:
    """Derive default affordance profiles from the target's semantic kind."""

    if kind == "event_type":
        return (
            _profile(
                target_ref,
                ("predicate",),
                inputs=("role:actor", "role:type"),
                outputs=("role:event",),
                roles=("role:actor", "role:type"),
            ),
            _profile(
                target_ref,
                ("anchor",),
                outputs=("role:event",),
                roles=("role:event",),
            ),
        )

    if kind == "relation_type":
        return (
            _profile(
                target_ref,
                ("predicate",),
                inputs=("role:subject", "role:object"),
                outputs=("role:relation",),
                roles=("role:subject", "role:object"),
            ),
            _profile(
                target_ref,
                ("anchor",),
                outputs=("role:relation",),
                roles=("role:relation",),
            ),
        )

    if kind == "state_dimension":
        return (
            _profile(
                target_ref,
                ("predicate",),
                inputs=("role:subject", "role:value"),
                outputs=("role:dimension",),
                roles=("role:subject", "role:value"),
            ),
            _profile(
                target_ref,
                ("anchor",),
                outputs=("role:dimension",),
                roles=("role:dimension",),
            ),
        )

    if kind == "state_value":
        return (
            _profile(
                target_ref,
                ("anchor",),
                outputs=("role:value",),
                roles=("role:value",),
            ),
            _profile(
                target_ref,
                ("predicate",),
                inputs=("role:subject", "role:dimension"),
                outputs=("role:value",),
                roles=("role:value",),
            ),
        )

    if kind == "label_type":
        return (
            _profile(
                target_ref,
                ("predicate",),
                inputs=("role:target", "role:surface"),
                outputs=("role:label_type",),
                roles=("role:target", "role:surface"),
            ),
            _profile(
                target_ref,
                ("anchor",),
                outputs=("role:label_type",),
                roles=("role:label_type",),
            ),
        )

    if kind == "concept":
        return (
            _profile(
                target_ref,
                ("anchor",),
                outputs=("role:instance",),
                roles=("role:instance",),
            ),
            _profile(
                target_ref,
                ("predicate",),
                inputs=("role:instance",),
                outputs=("role:class",),
                roles=("role:instance", "role:class"),
            ),
        )

    if kind == "entity":
        return (
            _profile(
                target_ref,
                ("anchor",),
                outputs=("role:target",),
                roles=("role:target",),
            ),
        )

    if kind == "participant":
        return (
            _profile(
                target_ref,
                ("anchor",),
                outputs=("role:actor",),
                roles=("role:actor",),
            ),
            _profile(
                target_ref,
                ("reference",),
                outputs=("role:participant",),
                roles=("role:participant",),
            ),
        )

    if kind == "capability":
        return (
            _profile(
                target_ref,
                ("reference",),
                outputs=("role:capability",),
                roles=("role:capability",),
            ),
            _profile(
                target_ref,
                ("predicate",),
                inputs=("role:participant",),
                outputs=("role:capability",),
                roles=("role:participant", "role:capability"),
            ),
        )

    if kind == "permission":
        return (
            _profile(
                target_ref,
                ("predicate",),
                inputs=("role:participant", "role:event"),
                outputs=("role:permission",),
                roles=("role:permission",),
            ),
        )

    if kind == "adapter":
        return (
            _profile(
                target_ref,
                ("reference",),
                outputs=("role:adapter",),
                roles=("role:adapter",),
            ),
        )

    # Unknown kind: no default affordances.
    return ()


# ---------------------------------------------------------------------------
# SemanticAffordanceIndex
# ---------------------------------------------------------------------------


class SemanticAffordanceIndex:
    """Bounded index of kind-derived affordance profiles.

    Affordances are derived only from the target's semantic kind.  Reviewed
    frame atoms may refine defaults when generation-pinned and linked.
    Ref-name spelling alone never creates affordances.

    Args:
        authority: the :class:`LinkedAuthority` with atoms and designations.
        config: the :class:`RuntimeConfig` with bounds.
    """

    def __init__(self, authority: Any, config: Any) -> None:
        self._authority = authority
        self._config = config
        self._max = getattr(config, "max_affordances_per_target", 4)
        self._frames = self._load_frames()

    # -- frame loading -------------------------------------------------------

    def _load_frames(self) -> dict[str, list[dict[str, Any]]]:
        """Load reviewed frame data from the frames directory.

        Frames are keyed by target_ref.  Only frames whose generation matches
        the authority generation are accepted (generation-pinned).
        """
        frames: dict[str, list[dict[str, Any]]] = {}
        # Try to load from data/authority/frames/semantic_affordances.json
        # relative to the authority manifest's directory.
        frames_path = self._find_frames_path()
        if frames_path is None:
            return frames
        try:
            data = json.loads(Path(frames_path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return frames

        generation = data.get("generation", "")
        if generation != self._authority.generation:
            # Generation mismatch: frames are not pinned to this authority.
            return frames

        for frame in data.get("frames", []):
            target_ref = frame.get("target_ref", "")
            if target_ref:
                frames.setdefault(target_ref, []).append(frame)
        return frames

    def _find_frames_path(self) -> Path | None:
        """Locate the semantic_affordances.json file."""
        # Try the standard location relative to the project root.
        candidates = [
            Path(__file__).resolve().parents[2] / "data" / "authority" / "frames" / "semantic_affordances.json",
        ]
        for p in candidates:
            if p.exists():
                return p
        return None

    # -- public API -----------------------------------------------------------

    def for_target(self, target_ref: str) -> tuple[AffordanceProfile, ...]:
        """Return affordance profiles for ``target_ref``.

        Derives defaults from the target's semantic kind.  Reviewed frame
        atoms may refine defaults when generation-pinned and linked.
        Bounded by ``max_affordances_per_target``.
        """
        atom = self._authority.atoms.get(target_ref)
        if atom is None:
            return ()

        kind = atom.kind
        defaults = _default_profiles(target_ref, kind)

        # Apply reviewed frame refinements.
        frame_list = self._frames.get(target_ref, [])
        refined = list(defaults)
        for frame in frame_list:
            profile = self._frame_to_profile(target_ref, frame)
            if profile is not None:
                # Frame refines: replace the first default with the frame
                # profile, or append if fewer defaults than frames.
                if len(refined) < len(defaults):
                    refined[len(refined)] = profile
                else:
                    refined.append(profile)

        return tuple(refined[: self._max])

    def for_designation(self, surface: str) -> tuple[AffordanceProfile, ...]:
        """Return affordances for the target(s) designated by ``surface``.

        A synonym inherits the target's affordances because the designation
        links the surface to the same semantic target.
        """
        targets = self._authority.designations.for_surface(surface, "en")
        if not targets:
            return ()
        result: list[AffordanceProfile] = []
        for target in targets:
            result.extend(self.for_target(target))
        return tuple(result[: self._max])

    def for_unlinked_ref(self, ref: str) -> tuple[AffordanceProfile, ...]:
        """Return affordances for ``ref`` only if it is a linked atom.

        Ref-name spelling alone cannot create affordances.  If ``ref`` is
        not in the authority's atoms, return ().
        """
        if ref not in self._authority.atoms:
            return ()
        return self.for_target(ref)

    # -- internal ------------------------------------------------------------

    @staticmethod
    def _frame_to_profile(
        target_ref: str, frame: Mapping[str, Any]
    ) -> AffordanceProfile | None:
        """Convert a reviewed frame dict to an AffordanceProfile."""
        kinds = tuple(frame.get("contribution_kinds", ()))
        if not kinds:
            return None
        return AffordanceProfile(
            target_ref=target_ref,
            contribution_kinds=kinds,
            input_ports=tuple(frame.get("input_ports", ())),
            output_ports=tuple(frame.get("output_ports", ())),
            role_candidates=tuple(frame.get("role_candidates", ())),
            frame_ref=frame.get("frame_ref"),
        )
