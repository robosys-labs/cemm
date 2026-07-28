"""Bounded epistemic proof bundles and verified semantic dialogue focus."""
from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Any, Iterable, Mapping

from cemm.model import canonical, stable

PROOF_BUNDLE_ABI = 1
_VALID_COMPLETENESS = frozenset({"unsupported", "partial", "complete", "conflict", "stale"})


def _refs(values: Iterable[Any], limit: int = 512) -> tuple[str, ...]:
    result = tuple(dict.fromkeys(str(item) for item in values if str(item)))
    if len(result) > limit:
        raise ValueError("proof reference set exceeds bound")
    return result


@dataclass(frozen=True)
class ProofBundle:
    proof_ref: str
    target_kind: str
    target_ref: str
    fact_refs: tuple[str, ...] = ()
    claim_refs: tuple[str, ...] = ()
    claim_occurrence_refs: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    inference_receipt_refs: tuple[str, ...] = ()
    commit_receipt_refs: tuple[str, ...] = ()
    operational_snapshot_refs: tuple[str, ...] = ()
    authority_generation: int = 0
    world_revision: int = 0
    completeness: str = "unsupported"
    support_count: int = 0
    opposition_count: int = 0
    provenance: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.proof_ref or not self.target_kind or not self.target_ref:
            raise ValueError("proof bundle requires identity and target")
        if self.completeness not in _VALID_COMPLETENESS:
            raise ValueError("unsupported proof completeness")
        if min(self.authority_generation, self.world_revision, self.support_count, self.opposition_count) < 0:
            raise ValueError("proof counters cannot be negative")

    @classmethod
    def create(cls, target_kind: str, target_ref: str, **kwargs):
        normalized = {
            key: _refs(kwargs.get(key, ()))
            for key in (
                "fact_refs", "claim_refs", "claim_occurrence_refs", "source_refs",
                "evidence_refs", "inference_receipt_refs", "commit_receipt_refs",
                "operational_snapshot_refs",
            )
        }
        body = {
            "target_kind": str(target_kind),
            "target_ref": str(target_ref),
            **{key: list(value) for key, value in normalized.items()},
            "authority_generation": int(kwargs.get("authority_generation", 0)),
            "world_revision": int(kwargs.get("world_revision", 0)),
            "completeness": str(kwargs.get("completeness", "unsupported")),
            "support_count": int(kwargs.get("support_count", 0)),
            "opposition_count": int(kwargs.get("opposition_count", 0)),
            "provenance": dict(kwargs.get("provenance", {})),
        }
        return cls(
            stable("proof-bundle-v1", body), str(target_kind), str(target_ref),
            **normalized,
            authority_generation=body["authority_generation"],
            world_revision=body["world_revision"],
            completeness=body["completeness"],
            support_count=body["support_count"],
            opposition_count=body["opposition_count"],
            provenance=body["provenance"],
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ProofBundle":
        if int(value.get("proof_bundle_abi", -1)) != PROOF_BUNDLE_ABI:
            raise ValueError("unsupported proof bundle ABI")
        created = cls.create(
            str(value["target_kind"]), str(value["target_ref"]),
            fact_refs=value.get("fact_refs", ()),
            claim_refs=value.get("claim_refs", ()),
            claim_occurrence_refs=value.get("claim_occurrence_refs", ()),
            source_refs=value.get("source_refs", ()),
            evidence_refs=value.get("evidence_refs", ()),
            inference_receipt_refs=value.get("inference_receipt_refs", ()),
            commit_receipt_refs=value.get("commit_receipt_refs", ()),
            operational_snapshot_refs=value.get("operational_snapshot_refs", ()),
            authority_generation=int(value.get("authority_generation", 0)),
            world_revision=int(value.get("world_revision", 0)),
            completeness=str(value.get("completeness", "unsupported")),
            support_count=int(value.get("support_count", 0)),
            opposition_count=int(value.get("opposition_count", 0)),
            provenance=dict(value.get("provenance", {})),
        )
        if created.proof_ref != str(value.get("proof_ref")):
            raise ValueError("proof bundle identity mismatch")
        return created

    def as_dict(self) -> dict[str, Any]:
        return {
            "proof_bundle_abi": PROOF_BUNDLE_ABI,
            "proof_ref": self.proof_ref,
            "target_kind": self.target_kind,
            "target_ref": self.target_ref,
            "fact_refs": list(self.fact_refs),
            "claim_refs": list(self.claim_refs),
            "claim_occurrence_refs": list(self.claim_occurrence_refs),
            "source_refs": list(self.source_refs),
            "evidence_refs": list(self.evidence_refs),
            "inference_receipt_refs": list(self.inference_receipt_refs),
            "commit_receipt_refs": list(self.commit_receipt_refs),
            "operational_snapshot_refs": list(self.operational_snapshot_refs),
            "authority_generation": self.authority_generation,
            "world_revision": self.world_revision,
            "completeness": self.completeness,
            "support_count": self.support_count,
            "opposition_count": self.opposition_count,
            "provenance": dict(self.provenance),
        }


@dataclass(frozen=True)
class VerifiedSemanticFocus:
    focus_ref: str
    focus_kind: str
    proposition_ref: str | None
    query_ref: str | None
    response_ref: str
    target_refs: tuple[str, ...]
    binding_signature: str
    proof_ref: str | None
    recorded_turn: int
    authority_generation: int
    world_revision: int

    @classmethod
    def create(
        cls, *, focus_kind: str, response_ref: str,
        target_refs: Iterable[str] = (), proposition_ref: str | None = None,
        query_ref: str | None = None, bindings: Iterable[Mapping[str, Any]] = (),
        proof_ref: str | None = None, recorded_turn: int = 0,
        authority_generation: int = 0, world_revision: int = 0,
    ) -> "VerifiedSemanticFocus":
        targets = _refs(target_refs, 64)
        signature = canonical(tuple(dict(item) for item in bindings))
        body = (
            str(focus_kind), proposition_ref, query_ref, str(response_ref), targets,
            signature, proof_ref, int(recorded_turn), int(authority_generation),
            int(world_revision),
        )
        return cls(
            stable("verified-semantic-focus-v1", body), str(focus_kind),
            proposition_ref, query_ref, str(response_ref), targets, signature,
            proof_ref, int(recorded_turn), int(authority_generation),
            int(world_revision),
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "VerifiedSemanticFocus":
        created = cls(
            str(value["focus_ref"]), str(value["focus_kind"]),
            value.get("proposition_ref"), value.get("query_ref"),
            str(value["response_ref"]),
            tuple(map(str, value.get("target_refs", ()))),
            str(value.get("binding_signature", "")), value.get("proof_ref"),
            int(value.get("recorded_turn", 0)),
            int(value.get("authority_generation", 0)),
            int(value.get("world_revision", 0)),
        )
        expected = stable(
            "verified-semantic-focus-v1",
            (
                created.focus_kind, created.proposition_ref, created.query_ref,
                created.response_ref, created.target_refs, created.binding_signature,
                created.proof_ref, created.recorded_turn,
                created.authority_generation, created.world_revision,
            ),
        )
        if created.focus_ref != expected:
            raise ValueError("verified semantic focus identity mismatch")
        return created

    def as_dict(self) -> dict[str, Any]:
        return {
            "focus_ref": self.focus_ref,
            "focus_kind": self.focus_kind,
            "proposition_ref": self.proposition_ref,
            "query_ref": self.query_ref,
            "response_ref": self.response_ref,
            "target_refs": list(self.target_refs),
            "binding_signature": self.binding_signature,
            "proof_ref": self.proof_ref,
            "recorded_turn": self.recorded_turn,
            "authority_generation": self.authority_generation,
            "world_revision": self.world_revision,
        }


class ProofEngine:
    def __init__(self, store: Any, config: Any, authority_generation: int) -> None:
        self.store = store
        self.authority_generation = int(authority_generation)
        self.max_nodes = int(getattr(config, "proof_max_nodes", 96))
        self.max_sources = int(getattr(config, "proof_max_sources", 16))
        if not 1 <= self.max_nodes <= 512 or not 1 <= self.max_sources <= 64:
            raise ValueError("proof bounds are invalid")

    def _records_for_facts(self, fact_refs: Iterable[str]):
        refs = _refs(fact_refs, self.max_nodes)
        if not refs:
            return (), (), (), (), (), (), ()
        marks = ",".join("?" for _ in refs)
        claims = self.store.db.execute(
            f"SELECT c.claim_ref,c.app_ref,c.observation_ref,c.stance,"
            f"c.authority_status,c.generation,o.source_ref "
            f"FROM claims c JOIN observations o "
            f"ON o.observation_ref=c.observation_ref "
            f"WHERE c.app_ref IN({marks}) AND c.valid_to IS NULL "
            f"ORDER BY c.generation DESC,c.claim_ref LIMIT ?",
            (*refs, self.max_nodes),
        ).fetchall()
        claim_refs = _refs((row["claim_ref"] for row in claims), self.max_nodes)
        observations = _refs((row["observation_ref"] for row in claims), self.max_nodes)
        sources = _refs((row["source_ref"] for row in claims), self.max_sources)
        occurrence_refs: tuple[str, ...] = ()
        if observations:
            obs_marks = ",".join("?" for _ in observations)
            rows = self.store.db.execute(
                f"SELECT occurrence_ref FROM claim_occurrences "
                f"WHERE observation_ref IN({obs_marks}) "
                f"ORDER BY created_at DESC,occurrence_ref LIMIT ?",
                (*observations, self.max_nodes),
            ).fetchall()
            occurrence_refs = _refs((row[0] for row in rows), self.max_nodes)

        subjects = _refs((*refs, *claim_refs), self.max_nodes * 2)
        proof_refs: list[str] = []
        parent_refs: list[str] = []
        if subjects:
            subject_marks = ",".join("?" for _ in subjects)
            rows = self.store.db.execute(
                f"SELECT proof_ref,parent_refs FROM proof_links "
                f"WHERE subject_ref IN({subject_marks}) "
                f"ORDER BY proof_ref LIMIT ?",
                (*subjects, self.max_nodes),
            ).fetchall()
            for row in rows:
                proof_refs.append(str(row["proof_ref"]))
                try:
                    parent_refs.extend(map(str, json.loads(row["parent_refs"] or "[]")))
                except (TypeError, ValueError, json.JSONDecodeError):
                    continue

        generations = tuple(dict.fromkeys(int(row["generation"]) for row in claims))
        commit_refs: tuple[str, ...] = ()
        if generations:
            gen_marks = ",".join("?" for _ in generations)
            rows = self.store.db.execute(
                f"SELECT receipt_ref FROM commit_receipts "
                f"WHERE generation IN({gen_marks}) "
                f"ORDER BY generation DESC,receipt_ref LIMIT ?",
                (*generations, self.max_nodes),
            ).fetchall()
            commit_refs = _refs((row[0] for row in rows), self.max_nodes)
        authority = tuple(str(row["authority_status"]) for row in claims)
        stances = tuple(str(row["stance"]) for row in claims)
        evidence = _refs((*proof_refs, *parent_refs), self.max_nodes)
        return (
            claim_refs, occurrence_refs, sources, evidence, commit_refs,
            authority, stances,
        )

    def for_query_result(
        self, query_result: Any, *, operational_snapshot_ref: str | None = None
    ) -> ProofBundle:
        fact_refs = _refs(
            (
                ref
                for binding in tuple(getattr(query_result, "bindings", ()))
                for ref in tuple(getattr(binding, "proof_refs", ()))
            ),
            self.max_nodes,
        )
        claims, occurrences, sources, evidence, commits, authority, stances = (
            self._records_for_facts(fact_refs)
        )
        inference = tuple(
            ref for ref in evidence
            if ref.startswith(("inference", "rule", "proof"))
        )
        snapshots = (str(operational_snapshot_ref),) if operational_snapshot_ref else ()
        opposition = (
            sum(1 for stance in stances if stance in {"deny", "oppose"})
            or int(getattr(query_result, "opposition_count", 0))
        )
        support = (
            sum(1 for stance in stances if stance == "support")
            or int(getattr(query_result, "support_count", 0))
        )
        if opposition and support:
            completeness = "conflict"
        elif not fact_refs and not snapshots:
            completeness = "unsupported"
        elif claims or snapshots:
            completeness = "complete"
        else:
            completeness = "partial"
        return ProofBundle.create(
            "query_result", str(query_result.query_ref),
            fact_refs=fact_refs, claim_refs=claims,
            claim_occurrence_refs=occurrences, source_refs=sources,
            evidence_refs=evidence, inference_receipt_refs=inference,
            commit_receipt_refs=commits, operational_snapshot_refs=snapshots,
            authority_generation=self.authority_generation,
            world_revision=int(self.store.revisions()["world_revision"]),
            completeness=completeness, support_count=support,
            opposition_count=opposition,
            provenance={
                "query_status": str(query_result.status),
                "authority_statuses": list(authority),
            },
        )

    def explain_focus(
        self, focus: VerifiedSemanticFocus,
        *, proof_lookup: Mapping[str, Any] | None = None,
    ) -> ProofBundle:
        current_world = int(self.store.revisions()["world_revision"])
        if (
            focus.authority_generation != self.authority_generation
            or focus.world_revision != current_world
        ):
            return ProofBundle.create(
                focus.focus_kind, focus.focus_ref,
                authority_generation=self.authority_generation,
                world_revision=current_world, completeness="stale",
                provenance={
                    "stale_focus_ref": focus.focus_ref,
                    "focus_authority_generation": focus.authority_generation,
                    "focus_world_revision": focus.world_revision,
                    "current_authority_generation": self.authority_generation,
                    "current_world_revision": current_world,
                },
            )
        if proof_lookup and focus.proof_ref in proof_lookup:
            value = proof_lookup[focus.proof_ref]
            if isinstance(value, Mapping):
                value = ProofBundle.from_dict(value)
            if isinstance(value, ProofBundle):
                if (
                    value.authority_generation == self.authority_generation
                    and value.world_revision == current_world
                    and value.proof_ref == focus.proof_ref
                ):
                    return value
                return ProofBundle.create(
                    focus.focus_kind, focus.focus_ref,
                    authority_generation=self.authority_generation,
                    world_revision=current_world, completeness="stale",
                    provenance={"stale_proof_ref": value.proof_ref},
                )
        return ProofBundle.create(
            focus.focus_kind, focus.focus_ref,
            authority_generation=self.authority_generation,
            world_revision=current_world,
            completeness="partial" if focus.proof_ref else "unsupported",
            provenance={"focus": focus.as_dict()},
        )
