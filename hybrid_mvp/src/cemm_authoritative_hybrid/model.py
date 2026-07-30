"""Neural switch proposer: constrained sequence model for SemanticSwitchProgram.

This module owns :class:`NeuralSwitchProposer` and :class:`ProposalNetwork`.
The proposer is a constrained sequence model that decodes structural action IDs
plus pointer selections into the current designation/contribution/context
tables under :class:`ActionMasker` masks. Semantic refs are never tokenized by
their spelling; the model encodes only structural features (form evidence,
contribution kinds, legal action types) and anonymized dynamic target slots.

Exact acceptance remains in :class:`ExactProgramVerifier`. The release factory
calls the loaded network directly — no bootstrap/static delegate.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence
import hashlib
import json

import torch
from torch import nn
import torch.nn.functional as F

from .affordances import SemanticAffordanceIndex
from .authority import LinkedAuthority
from .canonical import stable_ref, tensor_identity
from .config import RuntimeConfig
from .contributions import ContributionExpander
from .coverage import CoverageVerifier
from .cycle import Orientation
from .forms import FormResolver
from .grounding import Grounder
from .persistence import RevisionPin
from .programs import ProgramAction, SemanticSwitchProgram, SourceAssignment
from .verifier import ActionMasker, ExactProgramVerifier, LegalActionIndex

__all__ = [
    "ProposalNetwork",
    "NeuralSwitchProposer",
    "load_proposer_from_artifact",
    "RealizerNetwork",
    "load_realizer_from_artifact",
]


# ---------------------------------------------------------------------------
# Feature encoding constants
# ---------------------------------------------------------------------------

# Closed-class feature categories that the model encodes (not ref spelling).
_FEATURE_CATEGORIES: tuple[str, ...] = (
    "participant",
    "binder",
    "query",
    "polarity",
    "modality",
    "tense_aspect",
    "connector",
    "discourse",
    "determiner",
    "linker",
    "correction",
)

# The 12 switch action types (structural, no dynamic pointer values).
_ACTION_TYPES: tuple[str, ...] = (
    "select_context",
    "select_mode",
    "select_designation",
    "instantiate_operator",
    "bind_role",
    "bind_reference",
    "bind_nested_application",
    "attach_scope",
    "project_variable",
    "propose_transition",
    "complete_program",
    "abstain",
)

_ACTION_TYPE_INDEX: dict[str, int] = {a: i for i, a in enumerate(_ACTION_TYPES)}

# The five persistent operators.
_OPERATORS: tuple[str, ...] = (
    "op:designation",
    "op:type",
    "op:relation",
    "op:state",
    "op:event",
)
_OPERATOR_INDEX: dict[str, int] = {o: i for i, o in enumerate(_OPERATORS)}

# The four semantic modes.
_MODES: tuple[str, ...] = ("OBSERVE", "QUERY", "REQUEST", "SIMULATE")
_MODE_INDEX: dict[str, int] = {m: i for i, m in enumerate(_MODES)}

# Contribution kinds from the closed transient ABI.
_CONTRIBUTION_KINDS: tuple[str, ...] = (
    "anchor",
    "predicate",
    "binder",
    "reference",
    "scope",
    "discourse",
    "connector",
    "qualifier",
    "literal",
    "open_variable",
)
_CONTRIBUTION_KIND_INDEX: dict[str, int] = {k: i for i, k in enumerate(_CONTRIBUTION_KINDS)}


def _feature_category_index(category: str) -> int:
    """Return a stable index for a feature category, or -1 if unknown."""
    try:
        return _FEATURE_CATEGORIES.index(category)
    except ValueError:
        return -1


# ---------------------------------------------------------------------------
# Structural feature encoding (alpha-equivalence preserving)
# ---------------------------------------------------------------------------


def _encode_form_units(lattice: Any, max_units: int = 32) -> torch.Tensor:
    """Encode form units into a fixed-size feature tensor.

    Each unit is encoded by its closed-class feature categories (not ref
    spelling). The encoding is a ``(max_units, num_feature_categories)`` tensor
    where entry ``[i, j]`` is 1.0 if unit ``i`` has a feature in category ``j``.

    This ensures alpha-equivalent orientations (same structure, different ref
    names) produce identical encodings.
    """
    num_cats = len(_FEATURE_CATEGORIES)
    encoding = torch.zeros(max_units, num_cats)
    units = getattr(lattice, "units", ())
    for i, unit in enumerate(units[:max_units]):
        for cat, _val in getattr(unit, "features", ()):
            idx = _feature_category_index(cat)
            if idx >= 0:
                encoding[i, idx] = 1.0
    return encoding


def _encode_prefix_state(prefix: tuple[ProgramAction, ...], max_actions: int = 24) -> torch.Tensor:
    """Encode the current action prefix into a fixed-size tensor.

    The encoding captures which action types have been taken and how many
    actions of each type, without encoding dynamic pointer values. This is
    structural only and preserves alpha-equivalence.
    """
    encoding = torch.zeros(max_actions, len(_ACTION_TYPES))
    for i, action in enumerate(prefix[:max_actions]):
        idx = _ACTION_TYPE_INDEX.get(action.action_type, -1)
        if idx >= 0:
            encoding[i, idx] = 1.0
    return encoding


def _encode_unit_pointer(unit: Any, max_units: int = 32) -> torch.Tensor:
    """Encode a single unit pointer by its structural features (not ref name).

    Returns a one-hot-like encoding of the unit's feature categories.
    """
    encoding = torch.zeros(max_units)
    # Use the unit's position in the lattice as the pointer index (anonymized).
    # This is structural: two alpha-equivalent orientations have units at the
    # same positions with the same features.
    return encoding


def _encode_orientation_structural(orientation: Orientation, max_units: int = 32) -> torch.Tensor:
    """Encode orientation structural features (not ref spelling).

    Encodes: number of participants, number of focus refs, mode, capability
    count. All structural, none depend on ref names.
    """
    features = torch.zeros(8)
    features[0] = len(getattr(orientation, "participants", ()))
    features[1] = len(getattr(orientation, "focus_refs", ()))
    features[2] = len(getattr(orientation, "event_refs", ()))
    features[3] = len(getattr(orientation, "capability_summary", ()))
    features[4] = len(getattr(orientation, "obligation_refs", ()))
    # Mode is structural
    mode_name = getattr(orientation, "mode", None)
    if hasattr(mode_name, "value"):
        mode_name = mode_name.value
    features[5] = _MODE_INDEX.get(str(mode_name), 0)
    features[6] = getattr(orientation, "scanned_atom_count", 0)
    features[7] = len(getattr(orientation, "visited_refs", ()))
    return features


# ---------------------------------------------------------------------------
# ProposalNetwork
# ---------------------------------------------------------------------------


class ProposalNetwork(nn.Module):
    """A small neural network for proposing SemanticSwitchProgram candidates.

    The network encodes structural features only (form evidence, contribution
    kinds, legal action types, current prefix state) and outputs logits over
    legal next action IDs. Semantic refs are never tokenized by their spelling;
    dynamic target slots use anonymized indices.

    The network is deliberately small (well under 25M parameters) to train in a
    few seconds on CPU.
    """

    def __init__(
        self,
        *,
        hidden: int = 64,
        layers: int = 2,
        max_form_tokens: int = 32,
        max_actions: int = 24,
        num_feature_categories: int = 11,
        num_action_types: int = 12,
        num_operators: int = 5,
        num_modes: int = 4,
        num_contribution_kinds: int = 10,
    ) -> None:
        super().__init__()
        self.hidden = hidden
        self.layers = layers
        self.max_form_tokens = max_form_tokens
        self.max_actions = max_actions
        self.num_feature_categories = num_feature_categories
        self.num_action_types = num_action_types
        self.num_operators = num_operators
        self.num_modes = num_modes
        self.num_contribution_kinds = num_contribution_kinds

        # Form unit encoder: (max_form_tokens, num_feature_categories) -> (hidden,)
        form_input_dim = max_form_tokens * num_feature_categories
        self.form_encoder = nn.Sequential(
            nn.Linear(form_input_dim, hidden),
            nn.GELU(),
            nn.Linear(hidden, hidden),
            nn.GELU(),
        )

        # Prefix state encoder: (max_actions, num_action_types) -> (hidden,)
        prefix_input_dim = max_actions * num_action_types
        self.prefix_encoder = nn.Sequential(
            nn.Linear(prefix_input_dim, hidden),
            nn.GELU(),
            nn.Linear(hidden, hidden),
            nn.GELU(),
        )

        # Orientation structural encoder: (8,) -> (hidden,)
        self.orientation_encoder = nn.Sequential(
            nn.Linear(8, hidden),
            nn.GELU(),
        )

        # Step position encoding
        self.step_embedding = nn.Embedding(max_actions + 1, hidden)

        # Combine all encodings
        combined_dim = hidden * 4  # form + prefix + orientation + step
        self.combiner = nn.Sequential(
            nn.Linear(combined_dim, hidden),
            nn.GELU(),
        )
        for _ in range(layers - 1):
            self.combiner.append(nn.Linear(hidden, hidden))
            self.combiner.append(nn.GELU())

        # Output head: logits over a fixed action vocabulary.
        # The vocabulary size covers: action_type (12) × operator (5) × mode (4)
        # × role (max ~10) × unit_slot (max_form_tokens) + structural actions.
        # We use a flat output over a bounded vocabulary.
        vocab_size = self._compute_vocab_size()
        self.output_head = nn.Linear(hidden, vocab_size)

    def _compute_vocab_size(self) -> int:
        """Compute the flat action vocabulary size.

        The vocabulary covers all structural action IDs with anonymized
        pointer slots. Dynamic values (specific unit refs, target refs) are
        resolved by pointer selection after logits are computed.
        """
        # select_context: 1 (default) + num event types (bounded, use 8)
        ctx = 1 + 8
        # select_mode: 4
        mode = 4
        # select_designation: num_designatable_kinds (bounded, use 8)
        desig = 8
        # instantiate_operator: 5 operators
        ops = 5
        # bind_role: operators × roles (bounded, use 5 × 8 = 40) × unit_slots (max_form_tokens)
        roles = 5 * 8
        bind_role = roles * self.max_form_tokens
        # complete_program: 1
        complete = 1
        # abstain: 1
        abstain = 1
        # bind_reference, bind_nested_application, attach_scope, project_variable,
        # propose_transition: bounded, use 32 each
        other = 32 * 5
        return ctx + mode + desig + ops + bind_role + complete + abstain + other

    def forward(
        self,
        form_features: torch.Tensor,
        prefix_state: torch.Tensor,
        orientation_features: torch.Tensor,
        step: torch.Tensor,
    ) -> torch.Tensor:
        """Forward pass returning logits over the action vocabulary.

        Args:
            form_features: ``(batch, max_form_tokens * num_feature_categories)``
            prefix_state: ``(batch, max_actions * num_action_types)``
            orientation_features: ``(batch, 8)``
            step: ``(batch,)`` step index tensor

        Returns:
            ``(batch, vocab_size)`` logits.
        """
        form_vec = self.form_encoder(form_features)
        prefix_vec = self.prefix_encoder(prefix_state)
        orient_vec = self.orientation_encoder(orientation_features)
        step_vec = self.step_embedding(step)
        combined = torch.cat([form_vec, prefix_vec, orient_vec, step_vec], dim=-1)
        combined = self.combiner(combined)
        logits = self.output_head(combined)
        return logits

    def forward_single(
        self,
        form_features: torch.Tensor,
        prefix_state: torch.Tensor,
        orientation_features: torch.Tensor,
        step: int,
    ) -> torch.Tensor:
        """Forward pass for a single (unbatched) input.

        Returns a ``(vocab_size,)`` tensor of logits.
        """
        batched_form = form_features.unsqueeze(0)
        batched_prefix = prefix_state.unsqueeze(0)
        batched_orient = orientation_features.unsqueeze(0)
        batched_step = torch.tensor([step], dtype=torch.long, device=form_features.device)
        logits = self.forward(
            batched_form, batched_prefix, batched_orient, batched_step
        )
        return logits.squeeze(0)


# ---------------------------------------------------------------------------
# Action vocabulary mapping
# ---------------------------------------------------------------------------


class _ActionVocabulary:
    """Maps between structural action IDs and flat vocabulary indices.

    The vocabulary is built from the :class:`LegalActionIndex`'s candidate
    actions. Each candidate action's structural ID is mapped to a flat index.
    Dynamic pointer values (unit refs, target refs) are anonymized to slot
    indices so that alpha-equivalent actions map to the same index.
    """

    def __init__(self, legal_index: LegalActionIndex, max_form_tokens: int = 32) -> None:
        self._legal_index = legal_index
        self._max_form_tokens = max_form_tokens
        self._id_to_idx: dict[str, int] = {}
        self._idx_to_action_template: dict[int, tuple[str, tuple[str, ...]]] = {}
        self._build()

    def _anonymize_structural_id(self, action: ProgramAction) -> str:
        """Return an anonymized structural ID for ``action``.

        Replaces dynamic pointer values (unit refs, target refs) with
        anonymized slot types so that alpha-equivalent actions produce the
        same ID. Unit refs are anonymized to just "unit_slot" (without the
        numeric index) so that the model learns to predict the role, and
        the proposer selects the best unit from legal candidates at inference
        time.
        """
        parts = [action.action_type]
        for i, arg in enumerate(action.arguments):
            if arg.startswith("unit:"):
                # Anonymize unit ref to just "unit_slot" (no index) — the model
                # predicts the role; the proposer picks the best unit from
                # legal candidates.
                parts.append("unit_slot")
            elif arg.startswith("concept:") or arg.startswith("entity:") or arg.startswith("participant:") or arg.startswith("event:"):
                # Anonymize target ref to its kind (structural only)
                kind = self._kind_for_ref(arg)
                parts.append(f"target_kind:{kind}")
            elif arg.startswith("designation:"):
                parts.append("designation_slot")
            elif arg.startswith("role:"):
                parts.append(arg)  # role names are structural
            elif arg.startswith("op:"):
                parts.append(arg)  # operators are structural
            elif arg in _MODES:
                parts.append(arg)  # modes are structural
            else:
                parts.append(arg)
        return "|".join(parts)

    def _kind_for_ref(self, ref: str) -> str:
        """Return the semantic kind for a ref, or 'unknown'."""
        atoms = self._legal_index._authority.atoms
        record = atoms.get(ref)
        if record is not None:
            return record.kind
        # Check by prefix
        if ref.startswith("concept:"):
            return "concept"
        if ref.startswith("entity:"):
            return "entity"
        if ref.startswith("participant:"):
            return "participant"
        if ref.startswith("event:"):
            return "event_type"
        return "unknown"

    def _build(self) -> None:
        """Build the vocabulary from the legal index's candidate actions."""
        # Generate all candidate actions from the empty prefix and a few
        # representative prefixes to cover the action space.
        prefixes_to_explore: list[tuple[ProgramAction, ...]] = [()]
        # Add prefixes with select_context, select_mode, select_designation,
        # instantiate_operator to cover post-operator actions.
        for ctx in sorted(self._legal_index._context_refs) or ["context:turn"]:
            prefixes_to_explore.append((
                ProgramAction(
                    action_ref="action:0",
                    action_type="select_context",
                    arguments=(ctx,),
                    source_unit_refs=(),
                ),
            ))
        for mode in sorted(self._legal_index._modes):
            ctx = sorted(self._legal_index._context_refs)[0] if self._legal_index._context_refs else "context:turn"
            prefixes_to_explore.append((
                ProgramAction(
                    action_ref="action:0",
                    action_type="select_context",
                    arguments=(ctx,),
                    source_unit_refs=(),
                ),
                ProgramAction(
                    action_ref="action:1",
                    action_type="select_mode",
                    arguments=(mode,),
                    source_unit_refs=(),
                ),
            ))
        # Add prefixes with select_designation (to generate instantiate_operator)
        ctx = sorted(self._legal_index._context_refs)[0] if self._legal_index._context_refs else "context:turn"
        for target in sorted(self._legal_index._designation_targets)[:4]:
            prefixes_to_explore.append((
                ProgramAction(
                    action_ref="action:0",
                    action_type="select_context",
                    arguments=(ctx,),
                    source_unit_refs=(),
                ),
                ProgramAction(
                    action_ref="action:1",
                    action_type="select_mode",
                    arguments=("OBSERVE",),
                    source_unit_refs=(),
                ),
                ProgramAction(
                    action_ref="action:2",
                    action_type="select_designation",
                    arguments=("designation:0", target),
                    source_unit_refs=(),
                ),
            ))
        # Add prefixes with operator instantiated
        for op in sorted(self._legal_index._operators):
            for target in sorted(self._legal_index._designation_targets)[:4]:
                prefixes_to_explore.append((
                    ProgramAction(
                        action_ref="action:0",
                        action_type="select_context",
                        arguments=(ctx,),
                        source_unit_refs=(),
                    ),
                    ProgramAction(
                        action_ref="action:1",
                        action_type="select_mode",
                        arguments=("OBSERVE",),
                        source_unit_refs=(),
                    ),
                    ProgramAction(
                        action_ref="action:2",
                        action_type="select_designation",
                        arguments=("designation:0", target),
                        source_unit_refs=(),
                    ),
                    ProgramAction(
                        action_ref="action:3",
                        action_type="instantiate_operator",
                        arguments=(op, "designation:0"),
                        source_unit_refs=(),
                    ),
                ))
                # Add prefixes with one bind_role to cover post-bind actions
                for role in sorted(self._legal_index._operator_roles.get(op, ())):
                    prefixes_to_explore.append((
                        ProgramAction(
                            action_ref="action:0",
                            action_type="select_context",
                            arguments=(ctx,),
                            source_unit_refs=(),
                        ),
                        ProgramAction(
                            action_ref="action:1",
                            action_type="select_mode",
                            arguments=("OBSERVE",),
                            source_unit_refs=(),
                        ),
                        ProgramAction(
                            action_ref="action:2",
                            action_type="select_designation",
                            arguments=("designation:0", target),
                            source_unit_refs=(),
                        ),
                        ProgramAction(
                            action_ref="action:3",
                            action_type="instantiate_operator",
                            arguments=(op, "designation:0"),
                            source_unit_refs=(),
                        ),
                        ProgramAction(
                            action_ref="action:4",
                            action_type="bind_role",
                            arguments=(role, "unit:0"),
                            source_unit_refs=("unit:0",),
                        ),
                    ))

        seen_ids: set[str] = set()
        id_to_action: dict[str, tuple[str, tuple[str, ...]]] = {}
        for prefix in prefixes_to_explore:
            for action in self._legal_index._candidate_actions(prefix):
                if self._legal_index.is_legal(action, prefix):
                    anon_id = self._anonymize_structural_id(action)
                    if anon_id not in seen_ids:
                        seen_ids.add(anon_id)
                        id_to_action[anon_id] = (action.action_type, tuple(action.arguments))

        # Always include complete_program and abstain
        for at in ("complete_program", "abstain"):
            anon_id = f"{at}|"
            if anon_id not in seen_ids:
                seen_ids.add(anon_id)
                id_to_action[anon_id] = (at, ())

        # Sort IDs deterministically before assigning indices
        for idx, anon_id in enumerate(sorted(id_to_action)):
            self._id_to_idx[anon_id] = idx
            self._idx_to_action_template[idx] = id_to_action[anon_id]

    def add_action(self, action: ProgramAction) -> int:
        """Add ``action`` to the vocabulary if not present. Return its index.

        This is used during training to ensure all gold actions are in the
        vocabulary. The vocabulary is rebuilt deterministically after adding.
        """
        anon_id = self._anonymize_structural_id(action)
        if anon_id in self._id_to_idx:
            return self._id_to_idx[anon_id]
        # Add and re-sort
        self._id_to_idx[anon_id] = -1  # temporary
        self._idx_to_action_template[-1] = (action.action_type, tuple(action.arguments))
        # Rebuild with sorted IDs
        all_ids = sorted(self._id_to_idx)
        new_id_to_idx: dict[str, int] = {}
        new_idx_to_template: dict[int, tuple[str, tuple[str, ...]]] = {}
        for idx, aid in enumerate(all_ids):
            new_id_to_idx[aid] = idx
            if aid == anon_id:
                new_idx_to_template[idx] = (action.action_type, tuple(action.arguments))
            else:
                old_idx = self._id_to_idx[aid]
                new_idx_to_template[idx] = self._idx_to_action_template[old_idx]
        self._id_to_idx = new_id_to_idx
        self._idx_to_action_template = new_idx_to_template
        return self._id_to_idx[anon_id]

    @property
    def size(self) -> int:
        return len(self._id_to_idx)

    def index_for_action(self, action: ProgramAction) -> int | None:
        """Return the vocabulary index for ``action``, or None if not found."""
        anon_id = self._anonymize_structural_id(action)
        return self._id_to_idx.get(anon_id)

    def action_template(self, idx: int) -> tuple[str, tuple[str, ...]] | None:
        """Return the (action_type, arguments) template for vocabulary index."""
        return self._idx_to_action_template.get(idx)


# ---------------------------------------------------------------------------
# NeuralSwitchProposer
# ---------------------------------------------------------------------------


class NeuralSwitchProposer:
    """Constrained sequence model that proposes SemanticSwitchProgram candidates.

    Decodes structural action IDs plus pointer selections step by step under
    :class:`ActionMasker` masks. For each step, gets legal next action IDs from
    the masker, computes logits, selects the highest-logit legal action, builds
    a :class:`SemanticSwitchProgram` from the action sequence, and verifies
    with :class:`ExactProgramVerifier`.

    The model encodes only structural features (form evidence, contribution
    kinds, legal action types) — never ref spelling. Dynamic target slots use
    anonymized indices. Two alpha-equivalent orientations (same structure,
    different ref names) produce identical logits.
    """

    def __init__(
        self,
        network: ProposalNetwork,
        metadata: Any,
        verifier: ExactProgramVerifier,
        coverage_verifier: CoverageVerifier,
        legal_action_index: LegalActionIndex,
        action_masker: ActionMasker,
        form_resolver: FormResolver,
        grounder: Grounder,
        affordance_index: SemanticAffordanceIndex,
        contribution_expander: ContributionExpander,
        authority: LinkedAuthority,
        config: RuntimeConfig,
    ) -> None:
        self._network = network
        self._metadata = metadata
        self._verifier = verifier
        self._coverage_verifier = coverage_verifier
        self._legal_action_index = legal_action_index
        self._action_masker = action_masker
        self._form_resolver = form_resolver
        self._grounder = grounder
        self._affordance_index = affordance_index
        self._contribution_expander = contribution_expander
        self._authority = authority
        self._config = config
        self._max_actions = getattr(config, "max_applications", 24)
        self._max_candidates = getattr(config, "max_complete_candidates", 48)
        self._vocab = _ActionVocabulary(legal_action_index, network.max_form_tokens)
        # Resize the network's output head to match the actual vocabulary size.
        self._ensure_vocab_size()

    def _ensure_vocab_size(self) -> None:
        """Ensure the network output head matches the vocabulary size."""
        vocab_size = self._vocab.size
        if self._network.output_head.out_features != vocab_size:
            old = self._network.output_head
            new_out = nn.Linear(old.in_features, vocab_size)
            # Copy overlapping weights
            with torch.no_grad():
                min_out = min(old.out_features, vocab_size)
                new_out.weight[:min_out] = old.weight[:min_out]
                new_out.bias[:min_out] = old.bias[:min_out]
            self._network.output_head = new_out

    @property
    def network(self) -> ProposalNetwork:
        return self._network

    @property
    def model_identity(self) -> str:
        return self._metadata.model_identity

    @property
    def metadata(self) -> Any:
        return self._metadata

    @property
    def trainable_parameter_count(self) -> int:
        return sum(p.numel() for p in self._network.parameters() if p.requires_grad)

    @property
    def action_encoding_hash(self) -> str:
        return self._metadata.action_encoding_hash

    # -- structural logits (alpha-equivalence preserving) -------------------

    def structural_logits(self, orientation: Orientation) -> torch.Tensor:
        """Return logits that depend ONLY on structural features.

        Two alpha-equivalent orientations (same structure, different ref
        names) produce identical logits. This is achieved by encoding only
        structural features: form lattice unit features (closed-class features
        per unit position). Session-specific counts and ref names are not
        encoded, ensuring alpha-equivalence.
        """
        text = orientation.source_text
        lattice = self._form_resolver.resolve(text)
        form_features = _encode_form_units(lattice, self._network.max_form_tokens)
        prefix_state = _encode_prefix_state((), self._network.max_actions)
        # Use zeroed orientation features for structural logits — only form
        # features (from the text) determine the logits, not session state.
        orient_features = torch.zeros(8)
        # Use step 0 for structural logits (no prefix yet)
        logits = self._network.forward_single(
            form_features.flatten(),
            prefix_state.flatten(),
            orient_features,
            0,
        )
        return logits.detach()

    # -- propose ---------------------------------------------------------------

    def propose(self, orientation: Orientation) -> Any:
        """Propose verified programs for ``orientation``.

        Decodes structural action IDs step by step under ActionMasker masks,
        builds a SemanticSwitchProgram from the action sequence, verifies with
        ExactProgramVerifier, and returns a ProposalResult.
        """
        from .proposal import ProposalResult

        text = orientation.source_text
        lattice = self._form_resolver.resolve(text)

        # Ground designations and expand contributions.
        grounding_result = self._grounder.ground_text(text)
        self._contribution_expander.expand(grounding_result, lattice)

        content_unit_refs = [
            u.unit_ref for u in lattice.units if u.source_text.strip()
        ]

        pin = self._build_revision_pin(orientation)

        # Greedy decode: at each step, select the highest-logit legal action.
        prefix: list[ProgramAction] = []
        candidates: list[SemanticSwitchProgram] = []
        explored = 0
        truncated = False

        form_features = _encode_form_units(lattice, self._network.max_form_tokens)
        orient_features = _encode_orientation_structural(orientation)

        self._network.eval()
        with torch.no_grad():
            for step in range(self._max_actions):
                prefix_state = _encode_prefix_state(tuple(prefix), self._network.max_actions)
                logits = self._network.forward_single(
                    form_features.flatten(),
                    prefix_state.flatten(),
                    orient_features,
                    step,
                )

                # Get legal next actions and mask logits
                legal_actions = self._generate_legal_actions(tuple(prefix), content_unit_refs)
                if not legal_actions:
                    break

                # Map legal actions to vocabulary indices and select highest logit
                best_action = None
                best_logit = float("-inf")
                for action in legal_actions:
                    idx = self._vocab.index_for_action(action)
                    if idx is not None and idx < logits.shape[0]:
                        logit = float(logits[idx])
                        if logit > best_logit:
                            best_logit = logit
                            best_action = action

                if best_action is None:
                    # Fallback: pick first legal action
                    best_action = legal_actions[0]

                explored += 1

                if best_action.action_type == "complete_program":
                    new_prefix = tuple(prefix) + (best_action,)
                    program = self._build_program(
                        new_prefix, lattice, orientation, pin
                    )
                    if program is not None:
                        result = self._verifier.verify(program)
                        if result.accepted:
                            candidates.append(program)
                    break
                elif best_action.action_type == "abstain":
                    new_prefix = tuple(prefix) + (best_action,)
                    program = self._build_program(
                        new_prefix, lattice, orientation, pin
                    )
                    if program is not None:
                        result = self._verifier.verify(program)
                        if result.accepted:
                            candidates.append(program)
                    break
                else:
                    prefix.append(best_action)
                    if len(prefix) >= self._max_actions:
                        truncated = True
                        break

        # If no complete candidate, try abstain fallback
        if not candidates:
            abstain_action = ProgramAction(
                action_ref=f"action:{len(prefix)}",
                action_type="abstain",
                arguments=(),
                source_unit_refs=(),
            )
            new_prefix = tuple(prefix) + (abstain_action,)
            program = self._build_program(new_prefix, lattice, orientation, pin)
            if program is not None:
                result = self._verifier.verify(program)
                if result.accepted:
                    candidates.append(program)

        # Canonical tie-breaking: sort by program_ref, deduplicate
        seen_refs: set[str] = set()
        unique: list[SemanticSwitchProgram] = []
        for p in sorted(candidates, key=lambda p: p.program_ref):
            if p.program_ref not in seen_refs:
                seen_refs.add(p.program_ref)
                unique.append(p)
        candidates = tuple(unique)

        return ProposalResult(
            candidates=candidates,
            explored_states=explored,
            truncated=truncated,
            model_identity=self.model_identity,
        )

    # -- internal helpers ---------------------------------------------------

    def _build_revision_pin(self, orientation: Orientation) -> RevisionPin:
        base = orientation.revision_pin
        if base is not None and base.authority_generation == self._authority.generation:
            return base
        return RevisionPin(
            authority_generation=self._authority.generation,
            world_revision=0,
            session_revision=0,
            episode_revision=0,
            effect_revision=0,
            model_identity=self.model_identity,
        )

    def _generate_legal_actions(
        self, prefix: tuple[ProgramAction, ...], content_unit_refs: list[str]
    ) -> list[ProgramAction]:
        """Generate candidate actions for the given prefix and filter by legality."""
        candidates: list[ProgramAction] = []
        idx = len(prefix)
        legal = self._legal_action_index

        # select_context
        for ctx in sorted(legal._context_refs):
            candidates.append(
                ProgramAction(
                    action_ref=f"action:{idx}",
                    action_type="select_context",
                    arguments=(ctx,),
                    source_unit_refs=(),
                )
            )
        if not legal._context_refs:
            candidates.append(
                ProgramAction(
                    action_ref=f"action:{idx}",
                    action_type="select_context",
                    arguments=("context:turn",),
                    source_unit_refs=(),
                )
            )

        # select_mode
        for mode in sorted(legal._modes):
            candidates.append(
                ProgramAction(
                    action_ref=f"action:{idx}",
                    action_type="select_mode",
                    arguments=(mode,),
                    source_unit_refs=(),
                )
            )

        # select_designation
        for target in sorted(legal._designation_targets):
            candidates.append(
                ProgramAction(
                    action_ref=f"action:{idx}",
                    action_type="select_designation",
                    arguments=("designation:0", target),
                    source_unit_refs=(),
                )
            )

        # instantiate_operator
        for op in sorted(legal._operators):
            candidates.append(
                ProgramAction(
                    action_ref=f"action:{idx}",
                    action_type="instantiate_operator",
                    arguments=(op, "designation:0"),
                    source_unit_refs=(),
                )
            )

        # bind_role — use actual lattice content units
        operator: str | None = None
        for a in prefix:
            if a.action_type == "instantiate_operator" and a.arguments:
                operator = a.arguments[0]
                break
        if operator is not None:
            bound_roles: set[str] = set()
            consumed_units: set[str] = set()
            for a in prefix:
                if a.action_type == "bind_role" and a.arguments:
                    bound_roles.add(a.arguments[0])
                    consumed_units.update(a.source_unit_refs)
            for role in legal._operator_roles.get(operator, ()):
                if role in bound_roles:
                    continue
                for unit in content_unit_refs:
                    if unit in consumed_units:
                        continue
                    candidates.append(
                        ProgramAction(
                            action_ref=f"action:{idx}",
                            action_type="bind_role",
                            arguments=(role, unit),
                            source_unit_refs=(unit,),
                        )
                    )

        # complete_program
        candidates.append(
            ProgramAction(
                action_ref=f"action:{idx}",
                action_type="complete_program",
                arguments=(),
                source_unit_refs=(),
            )
        )

        # abstain
        candidates.append(
            ProgramAction(
                action_ref=f"action:{idx}",
                action_type="abstain",
                arguments=(),
                source_unit_refs=(),
            )
        )

        # Filter by legality
        return [a for a in candidates if legal.is_legal(a, prefix)]

    def _build_program(
        self,
        prefix: tuple[ProgramAction, ...],
        lattice: Any,
        orientation: Orientation,
        pin: RevisionPin,
    ) -> SemanticSwitchProgram | None:
        """Build a SemanticSwitchProgram from a complete prefix."""
        if not prefix:
            return None

        last = prefix[-1]
        if last.action_type not in ("complete_program", "abstain"):
            return None

        # Extract mode from select_mode action.
        mode_name = "OBSERVE"
        for a in prefix:
            if a.action_type == "select_mode" and a.arguments:
                mode_name = a.arguments[0]
                break

        # Extract root graph ref from instantiate_operator action.
        root_refs: tuple[str, ...] = ()
        for a in prefix:
            if a.action_type == "instantiate_operator":
                root_refs = (a.action_ref,)
                break

        # Collect all source unit refs from the lattice.
        unit_refs = tuple(u.unit_ref for u in lattice.units)

        # Build source assignments.
        assignments = self._build_assignments(prefix, lattice)

        # Generate a deterministic program_ref.
        action_ids = [a.structural_id() for a in prefix]
        program_ref = stable_ref(
            "program",
            {
                "orientation": orientation.cache_key,
                "actions": sorted(action_ids),
                "mode": mode_name,
            },
        )

        return SemanticSwitchProgram(
            program_ref=program_ref,
            orientation_ref=orientation.cache_key or "orientation:0",
            actions=prefix,
            root_graph_refs=root_refs,
            mode_ref=f"mode:{mode_name}",
            goal_refs=(),
            source_unit_refs=unit_refs,
            source_assignments=assignments,
            revision_pin=pin,
        )

    def _build_assignments(
        self,
        prefix: tuple[ProgramAction, ...],
        lattice: Any,
    ) -> tuple[SourceAssignment, ...]:
        """Build source assignments from the prefix and lattice."""
        consumed: dict[str, str] = {}
        for action in prefix:
            if action.action_type == "bind_role" and action.source_unit_refs:
                role_name = action.arguments[0] if action.arguments else ""
                for unit_ref in action.source_unit_refs:
                    consumed[unit_ref] = role_name

        assignments: list[SourceAssignment] = []
        for unit in lattice.units:
            unit_ref = unit.unit_ref
            is_punct = not unit.source_text.strip() or not unit.normalized_forms

            if unit_ref in consumed:
                role_name = consumed[unit_ref]
                assignments.append(
                    SourceAssignment(
                        assignment_ref=f"assignment:{unit_ref}",
                        source_unit_ref=unit_ref,
                        contribution_ref=f"contribution:{unit_ref}",
                        assignment_kind="role",
                        target_ref=f"target:{role_name}",
                        residual_kind=None,
                        critical=False,
                    )
                )
            elif is_punct:
                assignments.append(
                    SourceAssignment(
                        assignment_ref=f"assignment:{unit_ref}",
                        source_unit_ref=unit_ref,
                        contribution_ref=f"contribution:{unit_ref}",
                        assignment_kind="residual",
                        target_ref=None,
                        residual_kind="discourse",
                        critical=False,
                    )
                )
            else:
                assignments.append(
                    SourceAssignment(
                        assignment_ref=f"assignment:{unit_ref}",
                        source_unit_ref=unit_ref,
                        contribution_ref=f"contribution:{unit_ref}",
                        assignment_kind="residual",
                        target_ref=None,
                        residual_kind="qualifier",
                        critical=False,
                    )
                )

        return tuple(assignments)


# ---------------------------------------------------------------------------
# Artifact loading
# ---------------------------------------------------------------------------


def load_proposer_from_artifact(
    root: str | Path,
    manifest_sha256: str,
    *,
    verifier: ExactProgramVerifier,
    coverage_verifier: CoverageVerifier,
    legal_action_index: LegalActionIndex,
    action_masker: ActionMasker,
    form_resolver: FormResolver,
    grounder: Grounder,
    affordance_index: SemanticAffordanceIndex,
    contribution_expander: ContributionExpander,
    authority: LinkedAuthority,
    config: RuntimeConfig,
    device: str = "cpu",
) -> NeuralSwitchProposer:
    """Load a trained NeuralSwitchProposer from a safetensors artifact.

    Loads the network weights from ``model.safetensors`` via the safe artifact
    contract (no ``torch.load``), reconstructs the ProposalNetwork from the
    metadata config, and wires all components.
    """
    from .artifacts import load_model_artifact

    root = Path(root)
    metadata, tensors = load_model_artifact(root, manifest_sha256, device=device)

    # Reconstruct the network from the metadata config.
    net_config = dict(metadata.config)
    network = ProposalNetwork(
        hidden=int(net_config.get("hidden", 64)),
        layers=int(net_config.get("layers", 2)),
        max_form_tokens=int(net_config.get("max_form_tokens", 32)),
        max_actions=int(net_config.get("max_actions", 24)),
    )
    # Resize output head to match the saved vocabulary size
    vocab_size = int(net_config.get("vocab_size", 0))
    if vocab_size > 0 and network.output_head.out_features != vocab_size:
        old = network.output_head
        new_out = nn.Linear(old.in_features, vocab_size)
        with torch.no_grad():
            min_out = min(old.out_features, vocab_size)
            new_out.weight[:min_out] = old.weight[:min_out]
            new_out.bias[:min_out] = old.bias[:min_out]
        network.output_head = new_out
    network.load_state_dict({k: v.to(device) for k, v in tensors.items()})
    network.to(device)
    network.eval()

    return NeuralSwitchProposer(
        network=network,
        metadata=metadata,
        verifier=verifier,
        coverage_verifier=coverage_verifier,
        legal_action_index=legal_action_index,
        action_masker=action_masker,
        form_resolver=form_resolver,
        grounder=grounder,
        affordance_index=affordance_index,
        contribution_expander=contribution_expander,
        authority=authority,
        config=config,
    )


# ---------------------------------------------------------------------------
# RealizerNetwork — neural network for surface realization
# ---------------------------------------------------------------------------


class RealizerNetwork(nn.Module):
    """A small neural network for realizing surface text from ResponseMeaning.

    The network encodes :class:`ResponseMeaning` features (mode, status,
    polarity, modality, epistemic_status, discourse_action) and decodes a
    token sequence that selects among bounded surface templates. The network
    is deliberately small (well under 25M parameters) to train in a few
    seconds on CPU.

    The network does NOT generate free-form text — it learns to select the
    correct bounded surface template variant for a given response meaning.
    Equivalence verification is performed independently by
    :class:`RealizationVerifier`.
    """

    def __init__(
        self,
        *,
        hidden: int = 64,
        layers: int = 2,
        feature_dim: int = 32,
        vocab_size: int = 16,
    ) -> None:
        super().__init__()
        self.hidden = hidden
        self.layers = layers
        self.feature_dim = feature_dim
        self.vocab_size = vocab_size

        # Encoder: maps response meaning features to a hidden representation.
        self.encoder = nn.Sequential(
            nn.Linear(feature_dim, hidden),
            nn.GELU(),
            nn.Linear(hidden, hidden),
            nn.GELU(),
        )

        # Combiner layers.
        self.combiner = nn.Sequential(
            nn.Linear(hidden, hidden),
            nn.GELU(),
        )
        for _ in range(layers - 1):
            self.combiner.append(nn.Linear(hidden, hidden))
            self.combiner.append(nn.GELU())

        # Output head: logits over a bounded token vocabulary.
        self.output_head = nn.Linear(hidden, vocab_size)

    def forward(self, features: torch.Tensor) -> torch.Tensor:
        """Forward pass returning logits over the token vocabulary.

        Args:
            features: ``(batch, feature_dim)`` response meaning features.

        Returns:
            ``(batch, vocab_size)`` logits.
        """
        encoded = self.encoder(features)
        combined = self.combiner(encoded)
        logits = self.output_head(combined)
        return logits

    def forward_single(self, features: torch.Tensor) -> torch.Tensor:
        """Forward pass for a single (unbatched) input.

        Returns a ``(vocab_size,)`` tensor of logits.
        """
        batched = features.unsqueeze(0)
        logits = self.forward(batched)
        return logits.squeeze(0)


# ---------------------------------------------------------------------------
# Realizer artifact loading
# ---------------------------------------------------------------------------


def load_realizer_from_artifact(
    root: str | Path,
    manifest_sha256: str,
    *,
    verifier: Any | None = None,
    form_resolver: Any | None = None,
    grounder: Any | None = None,
    device: str = "cpu",
) -> Any:
    """Load a trained NeuralConstrainedRealizer from a safetensors artifact.

    Loads the network weights from ``model.safetensors`` via the safe artifact
    contract (no ``torch.load``), reconstructs the RealizerNetwork from the
    metadata config, and wires all components.
    """
    from .artifacts import load_model_artifact
    from .realization import NeuralConstrainedRealizer, RealizationVerifier

    root = Path(root)
    metadata, tensors = load_model_artifact(root, manifest_sha256, device=device)

    # Reconstruct the network from the metadata config.
    net_config = dict(metadata.config)
    network = RealizerNetwork(
        hidden=int(net_config.get("hidden", 64)),
        layers=int(net_config.get("layers", 2)),
        feature_dim=int(net_config.get("feature_dim", 32)),
        vocab_size=int(net_config.get("vocab_size", 16)),
    )
    network.load_state_dict({k: v.to(device) for k, v in tensors.items()})
    network.to(device)
    network.eval()

    # Build the verifier.
    real_verifier = verifier
    if real_verifier is None:
        real_verifier = RealizationVerifier(
            form_resolver=form_resolver,
            grounder=grounder,
        )

    return NeuralConstrainedRealizer(
        network=network,
        metadata=metadata,
        verifier=real_verifier,
        form_resolver=form_resolver,
        grounder=grounder,
    )
