"""Verified semantic focus, reference alternatives and persistent obligations."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from .canonical import stable_ref
from .persistence import RevisionPin, SemanticStores
from .r3_codec import exact_fields, exact_int, exact_pin, exact_refs, exact_text, optional_text, wire_refs

DIALOGUE_ABI_VERSION = 1

__all__ = [
    "DIALOGUE_ABI_VERSION", "ObligationKind", "VerifiedSemanticFocus",
    "FocusStore", "ReferenceConstraints", "ReferenceResolution",
    "ReferenceResolver", "DialogueObligation", "DialogueObligationManager",
    "GoalSelection", "GoalArbiter",
]


class ObligationKind(Enum):
    CLARIFICATION = "clarification"
    LEARNING_ANSWER = "learning_answer"
    EVIDENCE_REQUEST = "evidence_request"
    OPERATION_RESOLUTION = "operation_resolution"


@dataclass(frozen=True, init=False)
class VerifiedSemanticFocus:
    focus_ref: str
    expression_refs: tuple[str, ...]
    entity_refs: tuple[str, ...]
    event_refs: tuple[str, ...]
    salience_proof_refs: tuple[str, ...]
    participant_ref: str
    session_ref: str
    turn_ref: str
    revision_pin: RevisionPin

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise TypeError("use VerifiedSemanticFocus.create")

    @classmethod
    def create(cls, *, expression_refs: tuple[str, ...], entity_refs: tuple[str, ...], event_refs: tuple[str, ...], salience_proof_refs: tuple[str, ...], participant_ref: str, session_ref: str, turn_ref: str, revision_pin: RevisionPin) -> "VerifiedSemanticFocus":
        values = {
            "expression_refs": exact_refs(expression_refs, "expression_refs", nonempty=True),
            "entity_refs": exact_refs(entity_refs, "entity_refs"),
            "event_refs": exact_refs(event_refs, "event_refs"),
            "salience_proof_refs": exact_refs(salience_proof_refs, "salience_proof_refs"),
            "participant_ref": exact_text(participant_ref, "participant_ref"),
            "session_ref": exact_text(session_ref, "session_ref"),
            "turn_ref": exact_text(turn_ref, "turn_ref"),
            "revision_pin": exact_pin(revision_pin),
        }
        material = {"abi_version": DIALOGUE_ABI_VERSION, **{k: list(v) if type(v) is tuple else v.as_dict() if type(v) is RevisionPin else v for k, v in values.items()}}
        result = object.__new__(cls); object.__setattr__(result, "focus_ref", stable_ref("verified_focus", material))
        for key, item in values.items(): object.__setattr__(result, key, item)
        return result

    def as_dict(self) -> dict[str, Any]:
        return {"abi_version": DIALOGUE_ABI_VERSION, "focus_ref": self.focus_ref, "expression_refs": list(self.expression_refs), "entity_refs": list(self.entity_refs), "event_refs": list(self.event_refs), "salience_proof_refs": list(self.salience_proof_refs), "participant_ref": self.participant_ref, "session_ref": self.session_ref, "turn_ref": self.turn_ref, "revision_pin": self.revision_pin.as_dict()}

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "VerifiedSemanticFocus":
        fields = frozenset({"abi_version", "focus_ref", "expression_refs", "entity_refs", "event_refs", "salience_proof_refs", "participant_ref", "session_ref", "turn_ref", "revision_pin"})
        data = exact_fields(value, fields, "VerifiedSemanticFocus")
        if data["abi_version"] != DIALOGUE_ABI_VERSION or type(data["revision_pin"]) is not dict: raise ValueError("unsupported Focus ABI")
        rebuilt = cls.create(expression_refs=wire_refs(data["expression_refs"], "expression_refs", nonempty=True), entity_refs=wire_refs(data["entity_refs"], "entity_refs"), event_refs=wire_refs(data["event_refs"], "event_refs"), salience_proof_refs=wire_refs(data["salience_proof_refs"], "salience_proof_refs"), participant_ref=data["participant_ref"], session_ref=data["session_ref"], turn_ref=data["turn_ref"], revision_pin=RevisionPin.from_dict(data["revision_pin"]))
        if rebuilt.focus_ref != data["focus_ref"] or rebuilt.as_dict() != data: raise ValueError("non-canonical focus encoding")
        return rebuilt


class FocusStore:
    def __init__(self, stores: SemanticStores | None = None) -> None:
        self._stores = stores; self._entries: list[VerifiedSemanticFocus] = []

    def add(self, focus: VerifiedSemanticFocus) -> None:
        if type(focus) is not VerifiedSemanticFocus: raise TypeError("focus must be exact VerifiedSemanticFocus")
        if self._stores is not None:
            receipt = self._stores.focus.commit(focus.focus_ref, focus.session_ref, focus.as_dict(), expected_revision=self._stores.focus.revision)
            if receipt.new_revision <= receipt.parent_revision: raise ValueError("focus commit did not advance revision")
        self._entries.append(focus)

    @property
    def entries(self) -> tuple[VerifiedSemanticFocus, ...]: return tuple(self._entries)

    @property
    def refs(self) -> frozenset[str]:
        return frozenset(ref for row in self._entries for ref in (*row.expression_refs, *row.entity_refs, *row.event_refs))

    def recent_entries(self, n: int) -> tuple[VerifiedSemanticFocus, ...]:
        exact_int(n, "n", maximum=512); return tuple(self._entries[-n:]) if n else ()


@dataclass(frozen=True)
class ReferenceConstraints:
    person: str | None
    number: str | None
    kind: str | None
    recency: int
    scope_ref: str | None

    def __post_init__(self) -> None:
        for name in ("person", "number", "kind", "scope_ref"):
            value = getattr(self, name)
            if value is not None: exact_text(value, name)
        exact_int(self.recency, "recency", maximum=512)


@dataclass(frozen=True, init=False)
class ReferenceResolution:
    resolution_ref: str
    reference_ref: str
    selected_ref: str | None
    alternative_refs: tuple[str, ...]
    proof_refs: tuple[str, ...]

    def __init__(self, *_args: Any, **_kwargs: Any) -> None: raise TypeError("use ReferenceResolution.create")

    @classmethod
    def create(cls, *, reference_ref: str, selected_ref: str | None, alternative_refs: tuple[str, ...], proof_refs: tuple[str, ...]) -> "ReferenceResolution":
        reference_ref = exact_text(reference_ref, "reference_ref"); selected_ref = optional_text(selected_ref, "selected_ref"); alternatives = exact_refs(alternative_refs, "alternative_refs"); proofs = exact_refs(proof_refs, "proof_refs")
        if selected_ref is not None and selected_ref in alternatives: raise ValueError("selected ref cannot repeat as alternative")
        material = {"abi_version": DIALOGUE_ABI_VERSION, "reference_ref": reference_ref, "selected_ref": selected_ref, "alternative_refs": list(alternatives), "proof_refs": list(proofs)}
        result = object.__new__(cls); object.__setattr__(result, "resolution_ref", stable_ref("reference_resolution", material)); object.__setattr__(result, "reference_ref", reference_ref); object.__setattr__(result, "selected_ref", selected_ref); object.__setattr__(result, "alternative_refs", alternatives); object.__setattr__(result, "proof_refs", proofs); return result


class ReferenceResolver:
    """Resolve references only from verified focus under explicit constraints.

    Person and scope constraints are applied against structural focus metadata.
    Number constraints are applied when the linked authority carries a reviewed
    ``number`` metadata value for the candidate; absence of such metadata is
    treated as unknown rather than as evidence for rejection. Candidate refs
    are de-duplicated before ranking so repeated focus mentions cannot create
    non-canonical alternative lists.
    """

    _EXPRESSION_KINDS = frozenset({"proposition", "content", "claim", "expression"})

    def __init__(
        self,
        focus_store: FocusStore,
        authority: Any,
        *,
        margin_q: int = 300_000,
    ) -> None:
        if type(focus_store) is not FocusStore:
            raise TypeError("focus_store must be exact FocusStore")
        self._focus_store = focus_store
        self._authority = authority
        self._margin_q = exact_int(margin_q, "margin_q", maximum=1_000_000)

    @staticmethod
    def _participant_matches(row: VerifiedSemanticFocus, person: str | None) -> bool:
        if person is None or person == "third":
            return True
        if person == "first":
            return row.participant_ref == "participant:user"
        if person == "second":
            return row.participant_ref == "participant:system"
        return False

    @staticmethod
    def _scope_matches(row: VerifiedSemanticFocus, scope_ref: str | None) -> bool:
        return scope_ref is None or row.session_ref == scope_ref

    def _number_matches(self, ref: str, number: str | None) -> bool:
        if number is None:
            return True
        atoms = getattr(self._authority, "atoms", None)
        if not isinstance(atoms, Mapping):
            return True
        atom = atoms.get(ref)
        metadata = getattr(atom, "metadata", None)
        if not isinstance(metadata, Mapping):
            return True
        candidate_number = metadata.get("number")
        if candidate_number is None:
            return True
        return candidate_number == number

    @classmethod
    def _refs_for_kind(
        cls, row: VerifiedSemanticFocus, kind: str | None
    ) -> tuple[str, ...]:
        if kind in cls._EXPRESSION_KINDS:
            return row.expression_refs
        if kind == "entity":
            return row.entity_refs
        if kind == "event":
            return row.event_refs
        if kind is None:
            return (*row.expression_refs, *row.entity_refs, *row.event_refs)
        return ()

    def resolve(
        self,
        reference_ref: str,
        constraints: ReferenceConstraints,
        current_turn_ref: str,
    ) -> ReferenceResolution:
        exact_text(reference_ref, "reference_ref")
        exact_text(current_turn_ref, "current_turn_ref")
        if type(constraints) is not ReferenceConstraints:
            raise TypeError("constraints must be exact ReferenceConstraints")

        entries = tuple(
            row
            for row in self._focus_store.recent_entries(constraints.recency or 512)
            if row.turn_ref != current_turn_ref
            and self._participant_matches(row, constraints.person)
            and self._scope_matches(row, constraints.scope_ref)
        )
        # ref -> (score, proof_focus_ref). Repeated mentions retain the most
        # recent proof only and never duplicate a canonical alternative.
        candidates: dict[str, tuple[int, str]] = {}
        for recency, row in enumerate(reversed(entries)):
            score = 1_000_000 - recency * 100_000
            for ref in self._refs_for_kind(row, constraints.kind):
                if not self._number_matches(ref, constraints.number):
                    continue
                previous = candidates.get(ref)
                if previous is None or score > previous[0]:
                    candidates[ref] = (score, row.focus_ref)

        if not candidates:
            return ReferenceResolution.create(
                reference_ref=reference_ref,
                selected_ref=None,
                alternative_refs=(),
                proof_refs=(),
            )

        ranked = sorted(
            ((ref, score, proof) for ref, (score, proof) in candidates.items()),
            key=lambda row: (-row[1], row[0]),
        )
        selected, score, proof = ranked[0]
        alternatives = tuple(
            ref
            for ref, candidate_score, _ in ranked[1:]
            if score - candidate_score <= self._margin_q
        )
        return ReferenceResolution.create(
            reference_ref=reference_ref,
            selected_ref=selected,
            alternative_refs=alternatives,
            proof_refs=(proof,),
        )


@dataclass(frozen=True, init=False)
class DialogueObligation:
    obligation_ref: str
    kind: ObligationKind
    session_ref: str
    source_query_ref: str
    expected_answer_contract_ref: str
    created_turn_index: int
    expires_turn_index: int
    source_decision_ref: str
    completion_receipt_ref: str | None
    revision_pin: RevisionPin

    def __init__(self, *_args: Any, **_kwargs: Any) -> None: raise TypeError("use DialogueObligation.create")

    @classmethod
    def create(cls, *, kind: ObligationKind, session_ref: str, source_query_ref: str, expected_answer_contract_ref: str, created_turn_index: int, expires_turn_index: int, source_decision_ref: str, completion_receipt_ref: str | None, revision_pin: RevisionPin) -> "DialogueObligation":
        if type(kind) is not ObligationKind: raise TypeError("kind must be exact ObligationKind")
        values = {"kind": kind, "session_ref": exact_text(session_ref, "session_ref"), "source_query_ref": exact_text(source_query_ref, "source_query_ref"), "expected_answer_contract_ref": exact_text(expected_answer_contract_ref, "expected_answer_contract_ref"), "created_turn_index": exact_int(created_turn_index, "created_turn_index"), "expires_turn_index": exact_int(expires_turn_index, "expires_turn_index"), "source_decision_ref": exact_text(source_decision_ref, "source_decision_ref"), "completion_receipt_ref": optional_text(completion_receipt_ref, "completion_receipt_ref"), "revision_pin": exact_pin(revision_pin)}
        if values["expires_turn_index"] <= values["created_turn_index"]: raise ValueError("obligation expiry must follow creation")
        material = {"abi_version": DIALOGUE_ABI_VERSION, **{k: v.value if isinstance(v, ObligationKind) else v.as_dict() if type(v) is RevisionPin else v for k, v in values.items()}}
        result = object.__new__(cls); object.__setattr__(result, "obligation_ref", stable_ref("dialogue_obligation", material))
        for key, item in values.items(): object.__setattr__(result, key, item)
        return result

    def as_dict(self) -> dict[str, Any]:
        return {"abi_version": DIALOGUE_ABI_VERSION, "obligation_ref": self.obligation_ref, "kind": self.kind.value, "session_ref": self.session_ref, "source_query_ref": self.source_query_ref, "expected_answer_contract_ref": self.expected_answer_contract_ref, "created_turn_index": self.created_turn_index, "expires_turn_index": self.expires_turn_index, "source_decision_ref": self.source_decision_ref, "completion_receipt_ref": self.completion_receipt_ref, "revision_pin": self.revision_pin.as_dict()}


class DialogueObligationManager:
    """Own the lifecycle of typed dialogue obligations.

    Completion produces a new content-addressed obligation record and retains a
    bounded alias from the pending ref to the completed ref. This keeps the
    record immutable while allowing callers to retrieve the completed logical
    obligation through the ref they originally received.
    """

    def __init__(self, stores: SemanticStores | None = None) -> None:
        if stores is not None and type(stores) is not SemanticStores:
            raise TypeError("stores must be exact SemanticStores or None")
        self._stores = stores
        self._rows: dict[str, DialogueObligation] = {}
        self._aliases: dict[str, str] = {}

    def _resolve_ref(self, obligation_ref: str) -> str:
        exact_text(obligation_ref, "obligation_ref")
        seen: set[str] = set()
        current = obligation_ref
        while current in self._aliases:
            if current in seen:
                raise ValueError("obligation alias cycle")
            seen.add(current)
            current = self._aliases[current]
        return current

    def add(self, obligation: DialogueObligation) -> None:
        if type(obligation) is not DialogueObligation:
            raise TypeError("obligation must be exact DialogueObligation")
        if obligation.obligation_ref in self._rows or obligation.obligation_ref in self._aliases:
            raise ValueError("obligation ref already exists")
        if (
            obligation.kind is ObligationKind.LEARNING_ANSWER
            and self.has_learning_obligation()
        ):
            raise ValueError("only one learning obligation may be pending")
        if self._stores is not None:
            self._stores.obligations.commit(
                obligation.obligation_ref,
                obligation.session_ref,
                obligation.as_dict(),
                expected_revision=self._stores.obligations.revision,
                resolved=obligation.completion_receipt_ref is not None,
            )
        self._rows[obligation.obligation_ref] = obligation

    def get(self, obligation_ref: str) -> DialogueObligation | None:
        return self._rows.get(self._resolve_ref(obligation_ref))

    def fulfill(
        self, obligation_ref: str, completion_receipt_ref: str
    ) -> DialogueObligation:
        canonical_ref = self._resolve_ref(obligation_ref)
        current = self._rows.get(canonical_ref)
        if current is None:
            raise KeyError(obligation_ref)
        if current.completion_receipt_ref is not None:
            raise ValueError("obligation is already fulfilled")
        completion = exact_text(completion_receipt_ref, "completion_receipt_ref")
        completed = DialogueObligation.create(
            kind=current.kind,
            session_ref=current.session_ref,
            source_query_ref=current.source_query_ref,
            expected_answer_contract_ref=current.expected_answer_contract_ref,
            created_turn_index=current.created_turn_index,
            expires_turn_index=current.expires_turn_index,
            source_decision_ref=current.source_decision_ref,
            completion_receipt_ref=completion,
            revision_pin=current.revision_pin,
        )
        if self._stores is not None:
            self._stores.obligations.complete(
                canonical_ref,
                completed.obligation_ref,
                completed.session_ref,
                completed.as_dict(),
                expected_revision=self._stores.obligations.revision,
            )
        del self._rows[canonical_ref]
        self._rows[completed.obligation_ref] = completed
        self._aliases[canonical_ref] = completed.obligation_ref
        if obligation_ref != canonical_ref:
            self._aliases[obligation_ref] = completed.obligation_ref
        return completed

    def pending(
        self,
        *,
        kind: ObligationKind | None = None,
        turn_index: int | None = None,
    ) -> tuple[DialogueObligation, ...]:
        if kind is not None and type(kind) is not ObligationKind:
            raise TypeError("kind must be exact ObligationKind or None")
        if turn_index is not None:
            exact_int(turn_index, "turn_index")
        rows = tuple(
            row
            for row in self._rows.values()
            if row.completion_receipt_ref is None
            and (kind is None or row.kind is kind)
            and (turn_index is None or row.expires_turn_index > turn_index)
        )
        return tuple(
            sorted(rows, key=lambda row: (row.expires_turn_index, row.obligation_ref))
        )

    def has_learning_obligation(self, *, turn_index: int | None = None) -> bool:
        return bool(
            self.pending(kind=ObligationKind.LEARNING_ANSWER, turn_index=turn_index)
        )


@dataclass(frozen=True)
class GoalSelection:
    selected_goal_ref: str | None
    selected_obligation_ref: str | None
    policy_ref: str

    def __post_init__(self) -> None:
        optional_text(self.selected_goal_ref, "selected_goal_ref")
        optional_text(self.selected_obligation_ref, "selected_obligation_ref")
        exact_text(self.policy_ref, "policy_ref")
        if (
            self.selected_goal_ref is not None
            and self.selected_obligation_ref is not None
        ):
            raise ValueError("goal and obligation cannot both control a selection")

    @property
    def ui_intent_label(self) -> str:
        """Derived display label with no control authority."""
        if self.selected_obligation_ref is not None:
            return "obligation:fulfill"
        if self.selected_goal_ref is not None:
            return "goal:pursue"
        return "idle"


class GoalArbiter:
    """Select obligations before goals using an explicit structural policy."""

    POLICY_REF = "policy:obligation_first"

    def select(
        self,
        goals: tuple[str, ...],
        obligations: tuple[DialogueObligation, ...],
    ) -> GoalSelection:
        exact_refs(goals, "goals")
        if type(obligations) is not tuple or any(
            type(row) is not DialogueObligation for row in obligations
        ):
            raise TypeError("obligations must be an exact DialogueObligation tuple")
        pending = tuple(
            row for row in obligations if row.completion_receipt_ref is None
        )
        if pending:
            selected = min(
                pending,
                key=lambda row: (row.expires_turn_index, row.obligation_ref),
            )
            return GoalSelection(None, selected.obligation_ref, self.POLICY_REF)
        return GoalSelection(
            goals[0] if goals else None,
            None,
            self.POLICY_REF,
        )
