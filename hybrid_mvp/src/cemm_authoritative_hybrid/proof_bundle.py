"""Proof Bundle ABI 2: transient request-first evidence, not write authority.

Factories and decoders check structure only. QueryDecisionOwner authenticates
store lineage inside its pinned read; a decoded bundle is not authenticated.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .canonical import stable_ref
from .descriptions import (
    DESCRIPTION_MAX_REFS, DescriptionCompleteness, DescriptionResult,
    _pin, _ref, _refs, _wire_refs,
)
from .expressions import ApplicationFiller, SemanticApplication, SemanticExpression
from .persistence import RevisionPin, _normalized_application_payload
from .r3_codec import exact_fields, freeze_json

PROOF_BUNDLE_ABI_VERSION = 2


def _require_exact_wire_json(value: object) -> None:
    """Check existing JSON bounds, then disallow wire container coercion.

    The shared checker bounds depth, per-container rows and scalar text without
    imposing an unrelated aggregate-node cap on maximum-cardinality bundles.
    It permits immutable mappings/tuples for internal artifacts; wire records
    instead require exact JSON dicts/lists before nested codecs normalize them.
    """
    freeze_json(value)
    pending = [value]
    while pending:
        item = pending.pop()
        if type(item) is dict:
            pending.extend(item.values())
        elif type(item) is list:
            pending.extend(item)
        elif item is not None and type(item) not in {str, bool, int, float}:
            raise TypeError("proof wire values must be exact JSON types")


@dataclass(frozen=True, init=False)
class ClaimEvidence:
    claim_ref: str
    application_ref: str
    stance: str
    fact_ref: str
    source_ref: str
    decision_ref: str
    occurrence_ref: str
    placement: str
    placement_ref: str
    proof_refs: tuple[str, ...]
    authority_generation: str
    confidence_micros: int
    asserted_world_revision: int
    commit_transaction_ref: str

    _FIELDS = frozenset(__annotations__)

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise TypeError("use ClaimEvidence.create")

    @classmethod
    def create(cls, *, claim_ref: str, application_ref: str, stance: str,
               fact_ref: str, source_ref: str, decision_ref: str, occurrence_ref: str,
               placement: str, placement_ref: str, proof_refs: tuple[str, ...],
               authority_generation: str, confidence_micros: int,
               asserted_world_revision: int, commit_transaction_ref: str) -> "ClaimEvidence":
        if cls is not ClaimEvidence:
            raise TypeError("ClaimEvidence factory requires exact class")
        values = dict(application_ref=application_ref, stance=stance, fact_ref=fact_ref,
                      source_ref=source_ref, decision_ref=decision_ref,
                      occurrence_ref=occurrence_ref, placement=placement,
                      placement_ref=placement_ref, proof_refs=proof_refs,
                      authority_generation=authority_generation,
                      confidence_micros=confidence_micros,
                      asserted_world_revision=asserted_world_revision,
                      commit_transaction_ref=commit_transaction_ref)
        for name in ("application_ref", "fact_ref", "source_ref", "decision_ref",
                     "occurrence_ref", "placement_ref",
                     "commit_transaction_ref"):
            _ref(values[name], name)
        if (type(authority_generation) is not str or not authority_generation
                or len(authority_generation) > RevisionPin._MAX_TEXT_LENGTH):
            raise ValueError("authority_generation must be exact bounded generation identity")
        if not application_ref.startswith("semantic_application:") or not fact_ref.startswith("fact:"):
            raise ValueError("claim application/fact namespace mismatch")
        if type(stance) is not str or stance not in {"support", "deny"}:
            raise ValueError("claim stance must be exact support or deny")
        if type(placement) is not str or placement != "reviewed":
            raise ValueError("description evidence must have reviewed placement")
        if type(proof_refs) is not tuple:
            raise TypeError("proof_refs must be exact tuple")
        if len(proof_refs) > DESCRIPTION_MAX_REFS:
            raise ValueError("proof_refs exceeds Proof Bundle ABI bound")
        for proof_ref in proof_refs:
            _ref(proof_ref, "proof_refs item")
        if not proof_refs:
            raise ValueError("claim evidence requires proof_refs")
        if type(confidence_micros) is not int or not 0 <= confidence_micros <= 1_000_000:
            raise ValueError("confidence_micros must be exact bounded int")
        if type(asserted_world_revision) is not int or asserted_world_revision < 1:
            raise ValueError("asserted_world_revision must be exact positive int")
        material = {**values, "proof_refs": list(proof_refs)}
        if type(claim_ref) is not str or stable_ref("semantic_claim", material) != claim_ref:
            raise ValueError("claim_ref mismatch")
        result = object.__new__(cls)
        for name, value in {"claim_ref": claim_ref, **values}.items():
            object.__setattr__(result, name, value)
        return result

    def as_dict(self) -> dict[str, Any]:
        return {name: list(self.proof_refs) if name == "proof_refs" else getattr(self, name)
                for name in sorted(self._FIELDS)}

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ClaimEvidence":
        row = exact_fields(value, cls._FIELDS, "ClaimEvidence")
        if type(row["proof_refs"]) is not list:
            raise TypeError("proof_refs must be exact list")
        rebuilt = cls.create(**{**row, "proof_refs": tuple(row["proof_refs"])})
        if rebuilt.as_dict() != row:
            raise ValueError("non-canonical ClaimEvidence")
        return rebuilt


@dataclass(frozen=True, init=False)
class ProofBundle:
    abi_version: int
    proof_bundle_ref: str
    description: DescriptionResult
    application_refs: tuple[str, ...]
    claims: tuple[ClaimEvidence, ...]
    revision_pin: RevisionPin

    _FIELDS = frozenset(__annotations__)

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise TypeError("use ProofBundle.create")

    @property
    def source_expression_ref(self) -> str:
        return self.description.request.source_expression_ref

    @property
    def answer_expression_ref(self) -> str | None:
        answer = self.description.answer_expression
        return None if answer is None else answer.expression_ref

    @property
    def completeness(self) -> DescriptionCompleteness:
        return self.description.completeness

    @property
    def applications(self) -> tuple[SemanticApplication, ...]:
        answer = self.description.answer_expression
        if answer is None:
            return ()
        if answer.query_projections:
            raise ValueError("proof answer cannot contain a query projection")
        mapping = dict(zip((app.application_ref for app in answer.applications), self.application_refs, strict=True))

        def binding(row):
            filler = row.filler
            if type(filler) is ApplicationFiller:
                filler = ApplicationFiller(mapping[filler.node_ref])
            return type(row)(row.role_ref, filler)

        return tuple(SemanticApplication(mapping[app.application_ref], app.operator,
                        app.predicate_ref, tuple(binding(row) for row in app.roles),
                        tuple(binding(row) for row in app.qualifiers))
                     for app in answer.applications)

    @classmethod
    def create(cls, *, description: DescriptionResult, application_refs: tuple[str, ...],
               claims: tuple[ClaimEvidence, ...], revision_pin: RevisionPin) -> "ProofBundle":
        if cls is not ProofBundle:
            raise TypeError("ProofBundle factory requires exact class")
        if type(description) is not DescriptionResult or DescriptionResult.from_dict(description.as_dict()) != description:
            raise TypeError("description must be exact canonical DescriptionResult")
        pin = _pin(revision_pin)
        if description.revision_pin != pin:
            raise ValueError("proof bundle revision pins differ")
        _refs(application_refs, "application_refs")
        if type(claims) is not tuple or len(claims) > DESCRIPTION_MAX_REFS:
            raise TypeError("claims must be exact bounded tuple")
        for claim in claims:
            if type(claim) is not ClaimEvidence or ClaimEvidence.from_dict(claim.as_dict()) != claim:
                raise TypeError("claims must be exact canonical ClaimEvidence")
            if claim.authority_generation != pin.authority_generation or claim.asserted_world_revision > pin.world_revision:
                raise ValueError("claim evidence revision pin mismatch")
        if tuple(claim.claim_ref for claim in claims) != tuple(sorted({claim.claim_ref for claim in claims})):
            raise ValueError("claim evidence must be unique and sorted")
        if len({claim.fact_ref for claim in claims}) != len(claims):
            raise ValueError("claim facts must be independently owned")
        answer = description.answer_expression
        if answer is None:
            if application_refs or claims or any((description.fact_refs, description.definition_refs,
                                                 description.claim_refs, description.source_refs, description.proof_refs)):
                raise ValueError("terminal proof bundle cannot carry evidence")
        else:
            if (answer.scope_operators or answer.expression_links or answer.binders
                    or len(application_refs) != len(answer.applications)):
                raise ValueError("proof application correspondence mismatch")
            aggregate = {
                "fact_refs": tuple(sorted({claim.fact_ref for claim in claims})),
                "definition_refs": tuple(sorted({claim.application_ref for claim in claims})),
                "claim_refs": tuple(claim.claim_ref for claim in claims),
                "source_refs": tuple(sorted({claim.source_ref for claim in claims})),
                "proof_refs": tuple(sorted({ref for claim in claims for ref in claim.proof_refs})),
            }
            if any(getattr(description, name) != refs for name, refs in aggregate.items()):
                raise ValueError("proof evidence aggregate mismatch")
            root_mapping = dict(zip((app.application_ref for app in answer.applications), application_refs, strict=True))
            if tuple(sorted(root_mapping[ref] for ref in answer.root_refs)) != description.definition_refs:
                raise ValueError("proof root correspondence mismatch")
            signs: dict[str, set[str]] = {}
            for claim in claims:
                signs.setdefault(claim.application_ref, set()).add(claim.stance)
            conflict = any(stances == {"support", "deny"} for stances in signs.values())
            if conflict != (description.completeness is DescriptionCompleteness.CONFLICT):
                raise ValueError("proof signed completeness mismatch")
        values = dict(abi_version=PROOF_BUNDLE_ABI_VERSION, description=description,
                      application_refs=application_refs, claims=claims, revision_pin=pin)
        result = object.__new__(cls)
        for name, value in values.items():
            object.__setattr__(result, name, value)
        for app in result.applications:
            if stable_ref("semantic_application", _normalized_application_payload(app)) != app.application_ref:
                raise ValueError("proof application content identity mismatch")
        material = result._material()
        object.__setattr__(result, "proof_bundle_ref", stable_ref("proof_bundle", material))
        return result

    def _material(self) -> dict[str, Any]:
        return dict(abi_version=self.abi_version,
                    description=self.description.as_dict(), application_refs=list(self.application_refs),
                    claims=[claim.as_dict() for claim in self.claims], revision_pin=self.revision_pin.as_dict())

    def as_dict(self) -> dict[str, Any]:
        return {"proof_bundle_ref": self.proof_bundle_ref, **self._material()}

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ProofBundle":
        row = exact_fields(value, cls._FIELDS, "ProofBundle")
        _ref(row["proof_bundle_ref"], "proof_bundle_ref")
        _require_exact_wire_json(row)
        if type(row["abi_version"]) is not int or row["abi_version"] != PROOF_BUNDLE_ABI_VERSION:
            raise ValueError("unsupported Proof Bundle ABI")
        if type(row["claims"]) is not list or len(row["claims"]) > DESCRIPTION_MAX_REFS:
            raise TypeError("claims must be exact bounded list")
        for name in ("description", "revision_pin"):
            if type(row[name]) is not dict:
                raise TypeError(f"{name} must be exact dict")
        rebuilt = cls.create(description=DescriptionResult.from_dict(row["description"]),
                application_refs=_wire_refs(row["application_refs"], "application_refs"),
                claims=tuple(ClaimEvidence.from_dict(claim) for claim in row["claims"]),
                revision_pin=RevisionPin.from_dict(row["revision_pin"]))
        if rebuilt.as_dict() != row:
            raise ValueError("proof_bundle_ref mismatch or non-canonical ProofBundle")
        return rebuilt


def _bundle_for_description(description: DescriptionResult, claims: tuple[Any, ...]) -> ProofBundle:
    evidence = tuple(ClaimEvidence.create(
        claim_ref=claim.claim_ref,
        **{name: getattr(claim, name) for name in ClaimEvidence._FIELDS - {"claim_ref"}},
    ) for claim in sorted(claims, key=lambda claim: claim.claim_ref))
    applications = {app.application_ref: app for claim in claims for app in claim.applications}
    application_refs: tuple[str, ...] = ()
    if description.answer_expression is not None:
        rebuilt, ref_map = SemanticExpression._create_with_ref_map(
            applications=tuple(applications[ref] for ref in sorted(applications)),
            root_refs=description.definition_refs,
        )
        if rebuilt != description.answer_expression:
            raise ValueError("description proof answer correspondence mismatch")
        reverse = {local: persistent for persistent, local in ref_map.items()}
        application_refs = tuple(reverse[app.application_ref] for app in rebuilt.applications)
    return ProofBundle.create(description=description,
        application_refs=application_refs, claims=evidence, revision_pin=description.revision_pin)
