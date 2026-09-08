"""Bounded admitted designation reads within the gateway-owned trusted store.

Publication authenticates the grant. Reads reconstruct the committed lineage;
they require neither its HMAC key nor a still-open publication window. These
checks are not protection against an offline attacker fabricating a whole DB.
No consumer is wired to this owner until the separate integration increment.
"""
from collections import OrderedDict
from contextlib import contextmanager
from dataclasses import dataclass

from .authority import DesignationFact, LinkedAuthority
from .canonical import stable_ref
from .dialogue import DialogueObligation
from .gaps import BudgetExhausted
from .persistence import RevisionPin, SemanticStores
from .r3_codec import exact_fields, exact_int, exact_text, thaw_json
from .r3_persistence import EffectJournalEntry, EffectJournalState, effect_journal_get


@dataclass(frozen=True)
class DesignationEvidence:
    """Semantic designation identity and its actual, separate evidence owner."""
    designation: DesignationFact
    world_fact_ref: str | None
    authority_designation_ref: str | None
    provenance_refs: tuple[str, ...]


def _nonfuture(pin, current):
    """Allow proposer changes, not foreign authority or future revisions."""
    if (pin.authority_generation != current.authority_generation
            or any(getattr(pin, key) > getattr(current, key) for key in
                ("world_revision", "session_revision", "episode_revision", "effect_revision"))):
        raise ValueError("designation lineage has a future or foreign revision pin")


def _admitted_fact(stores, authority, fact, binding, current):
    """Reconstruct the exact committed chain using existing publication owners."""
    from .r3_effects import R3EffectGateway, _predicted_pin
    from .r3_learning import AliasReviewVerifier, publication_proposal_lineage

    if "publication_key" not in fact.proof:
        return None
    key = exact_text(fact.proof["publication_key"], "publication locator")
    stored = effect_journal_get(stores, key)
    if stored is None or stored.entry.state is not EffectJournalState.COMMITTED:
        raise ValueError("claimed alias publication has no committed journal")
    request = thaw_json(stored.entry.request_payload)
    if request.get("kind") != "learning_publication":
        raise ValueError("claimed alias locator is not a publication")
    review = exact_fields(request["review"], {"grant", "signature"}, "retained alias review")
    grant = exact_fields(review["grant"], AliasReviewVerifier._GRANT_FIELDS, "retained alias grant")
    for name in AliasReviewVerifier._GRANT_FIELDS - {"expires_at_turn"}:
        exact_text(grant[name], name)
    exact_int(grant["expires_at_turn"], "review expiry", minimum=1)
    signature = exact_text(review["signature"], "retained signature")
    if len(signature) != 64 or any(c not in "0123456789abcdef" for c in signature):
        raise ValueError("noncanonical retained alias signature")
    if binding is None or grant["store_binding"] != binding:
        raise ValueError("admitted alias belongs to a different trusted store")
    proposal = effect_journal_get(stores, grant["proposal_key"])
    if proposal is None or proposal.as_dict() != request["proposal"]:
        raise ValueError("admitted alias original proposal changed")
    _meaning, evaluation, plan, source, contract = publication_proposal_lineage(stores, authority, proposal, grant)
    pin = RevisionPin.from_dict(request["publication_pin"])
    proposal_output_pin = RevisionPin.from_dict(thaw_json(proposal.receipt_payload)["output_revision_pin"])
    # The answer and its publication must agree with each other;
    # today's proposer identity is not the identity of admitted world knowledge.
    if any(historical.model_identity != pin.model_identity for historical in
            (plan.revision_pin, proposal_output_pin)):
        raise ValueError("admitted alias historical publication model lineage mismatch")
    _nonfuture(plan.revision_pin, pin)
    _nonfuture(source.revision_pin, pin)
    _nonfuture(pin, current)
    _nonfuture(proposal_output_pin, pin)
    session = request["publication_session"]
    session_material = {k: v for k, v in session.items() if k != "snapshot_ref"}
    signature = authority.by_event_signature(contract.source_event_ref)
    if (session.get("snapshot_ref") != stable_ref("r3_session_snapshot", session_material)
            or session.get("session_ref") != source.session_ref
            or session.get("store_revision") != pin.session_revision
            or session.get("session_phase_ref") not in signature.valid_session_phases
            or not source.created_turn_index < evaluation.situation.turn_index <= session["turn_index"]
                < grant["expires_at_turn"] <= source.expires_turn_index):
        raise ValueError("admitted alias publication-time session is invalid")
    obligation_revision = exact_int(request["publication_obligation_revision"], "publication obligation revision")
    snapshot_material = {"session_ref": source.session_ref, "obligation_refs": [source.obligation_ref],
        "obligation_store_revision": obligation_revision}
    if request["publication_obligation_snapshot"] != {
            "snapshot_ref": stable_ref("r3_obligation_snapshot", snapshot_material), **snapshot_material}:
        raise ValueError("admitted alias original pending snapshot mismatch")
    _delta, observation = R3EffectGateway._publication_observation(request)
    origin = stable_ref("effect_journal_origin", {"kind": "learning_publication", "plan_ref": plan.plan_ref})
    expected_key = R3EffectGateway._effect_key(plan.decision_ref, plan.plan_ref, "learning_publication")
    parent = None
    for offset, state in enumerate((EffectJournalState.PLANNED, EffectJournalState.AUTHORIZED,
            EffectJournalState.OBSERVED), 1):
        parent = EffectJournalEntry.create(idempotency_key=expected_key, state=state, attempt_index=0,
            intent_ref=origin, decision_ref=plan.decision_ref, request_payload=request,
            observation_payload=observation if state is EffectJournalState.OBSERVED else None,
            outcome_ref=None, blocker_refs=(), parent_journal_ref=None if parent is None else parent.journal_ref,
            effect_revision=pin.effect_revision + offset)
    expected_observation, expected_fact, receipt = R3EffectGateway._publication_commit_material(
        parent, _predicted_pin(pin, effects=3))
    terminal = EffectJournalEntry.create(idempotency_key=expected_key, state=EffectJournalState.COMMITTED,
        attempt_index=0, intent_ref=origin, decision_ref=plan.decision_ref, request_payload=request,
        observation_payload=expected_observation, outcome_ref=receipt.receipt_ref, blocker_refs=(),
        parent_journal_ref=parent.journal_ref, effect_revision=pin.effect_revision + 4)
    _nonfuture(receipt.output_revision_pin, current)
    if (key != expected_key or fact != expected_fact or stored.entry != terminal
            or thaw_json(stored.receipt_payload) != receipt.as_dict()):
        raise ValueError("admitted alias fact/receipt/committed chain mismatch")
    completed = DialogueObligation.create(kind=source.kind, session_ref=source.session_ref,
        source_query_ref=source.source_query_ref, expected_answer_contract_ref=source.expected_answer_contract_ref,
        created_turn_index=source.created_turn_index, expires_turn_index=source.expires_turn_index,
        source_decision_ref=source.source_decision_ref, completion_receipt_ref=receipt.receipt_ref,
        revision_pin=source.revision_pin)
    for expected in (source, completed):
        actual = stores.r3_resolved_dialogue_obligation(expected.obligation_ref, commit_revision=obligation_revision + 1)
        if actual != expected:
            raise ValueError("admitted alias completed obligation mismatch")
    original = thaw_json(proposal.entry.request_payload)
    source_receipt = original["learning_source_journal"]["receipt"]
    proofs = tuple(dict.fromkeys((fact.fact_ref, receipt.receipt_ref, stored.entry.journal_ref,
        receipt.journal_preterminal_ref, receipt.operation_receipt_ref, grant["reviewer_ref"], grant["policy_ref"],
        plan.plan_ref, source.obligation_ref, completed.obligation_ref, source.source_query_ref,
        proposal.entry.journal_ref, grant["proposal_receipt_ref"], grant["source_journal_ref"],
        source_receipt["receipt_ref"], source_receipt["journal_preterminal_ref"], *receipt.proof_refs)))
    return DesignationEvidence(DesignationFact.create(surface=grant["surface"], target_ref=grant["target_ref"],
        language=grant["language"]), fact.fact_ref, None, proofs)


class AdmittedDesignationReader:
    """Shared bounded merged lookup; caches include misses, never static authority mutation."""
    def __init__(self, authority, stores, *, memory_review_binding=None):
        if type(authority) is not LinkedAuthority or type(stores) is not SemanticStores:
            raise TypeError("designation reader requires linked authority and semantic stores")
        if memory_review_binding is not None:
            exact_text(memory_review_binding, "trusted memory binding")
            if stores.learning_store_binding is not None:
                raise ValueError("cannot override a named SQLite store binding")
        self.authority, self.stores = authority, stores
        self.binding = stores.learning_store_binding or memory_review_binding
        self._cache = OrderedDict()

    @contextmanager
    def batch(self, expected_pin: RevisionPin):
        with self.stores.r3_read_snapshot(expected_pin):
            if expected_pin.authority_generation != self.authority.generation:
                raise ValueError("designation reader authority generation mismatch")
            batch = _DesignationBatch(self, expected_pin, self.stores.r3_obligation_revision())
            try:
                yield batch
            finally:
                batch.active = False


class _DesignationBatch:
    def __init__(self, reader, pin, obligation_revision):
        self.reader, self.pin, self.obligation_revision = reader, pin, obligation_revision
        self.active = True

    def _check(self):
        if not self.active:
            raise ValueError("designation read batch is closed")
        self.reader.stores.r3_assert_read_pin(self.pin)
        if self.reader.stores.r3_obligation_revision() != self.obligation_revision:
            from .persistence import StaleRevisionError
            raise StaleRevisionError("designation batch obligation revision changed")

    def _cached(self, mode, key, language, maximum, compute):
        self._check()
        reader = self.reader
        cache_key = (reader.authority.generation, reader.authority.content_hash, self.pin,
            self.obligation_revision, mode, key, language, maximum)
        if cache_key not in reader._cache:
            value = compute()
            self._check()
            reader._cache[cache_key] = value
            if len(reader._cache) > 256:
                reader._cache.popitem(last=False)
        reader._cache.move_to_end(cache_key)
        return reader._cache[cache_key]

    def _lookup(self, mode, key, language, maximum):
        exact_text(key, "designation key")
        if language is not None:
            exact_text(language, "designation language")
        exact_int(maximum, "designation maximum", minimum=1, maximum=16)
        def compute():
            authority, stores = self.reader.authority, self.reader.stores
            static = authority.designations.bounded_facts(mode, key, language, maximum=maximum)
            raw = stores.r3_designation_facts(mode, key, language, maximum=maximum)
            if len(static) > maximum or len(raw) > maximum:
                raise BudgetExhausted("admitted_designations", maximum)
            rows = [DesignationEvidence(fact, None, fact.designation_fact_ref,
                (fact.designation_fact_ref, authority.generation, authority.content_hash)) for fact in static]
            for fact in raw:
                evidence = self.resolve_world_fact(fact.fact_ref)
                if evidence is not None:
                    rows.append(evidence)
            if len(rows) > maximum:
                raise BudgetExhausted("admitted_designations", maximum)
            return tuple(sorted(rows, key=lambda r: (r.designation.surface, r.designation.language,
                r.designation.target_ref, r.world_fact_ref or r.authority_designation_ref)))
        return self._cached(mode, key, language, maximum, compute)

    def for_surface(self, surface, language, *, maximum=8):
        exact_text(language, "designation language")
        exact_int(maximum, "grounding designation maximum", minimum=1, maximum=8)
        exact = self._lookup("exact", surface, language, maximum)
        return exact or self._lookup("folded", surface, language, maximum)

    def exact_surface(self, surface, *, maximum=16):
        return self._lookup("exact", surface, None, maximum)

    def for_target(self, target_ref, language, *, maximum=16):
        return self._lookup("target", target_ref, language, maximum)

    def canonical_surface_for_target(self, target_ref, language, observed_surface, *, maximum=16):
        exact_text(observed_surface, "observed designation surface")
        rows = self.for_target(target_ref, language, maximum=maximum)
        exact = tuple(row for row in rows if row.designation.surface == observed_surface)
        return exact or tuple(row for row in rows if row.designation.surface.casefold() == observed_surface.casefold())

    def resolve_world_fact(self, fact_ref):
        exact_text(fact_ref, "world fact ref")
        def compute():
            fact = self.reader.stores.world.get(fact_ref)
            if fact is None:
                return None
            return _admitted_fact(self.reader.stores, self.reader.authority, fact, self.reader.binding, self.pin)
        return self._cached("world_fact", fact_ref, None, 1, compute)
