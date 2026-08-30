"""Non-circular identity material for one accountable R4.1 review act."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ._r4_source_codec import (
    canonical_json_bytes,
    construct,
    exact_content_ref,
    exact_fields,
    exact_int,
    exact_ref,
    exact_reviewer_refs,
    exact_revision,
    exact_sha256,
    exact_text,
    strict_decode,
    wire_ref_tuple,
)
from .canonical import stable_ref


REVIEW_SCOPE = "r4_1_supervision_authoring"


@dataclass(frozen=True, init=False)
class ReviewContextMaterial:
    review_context_ref: str
    review_scope: str
    review_policy_ref: str
    review_policy_sha256: str
    reviewer_refs: tuple[str, ...]
    reviewed_base_revision: str
    authority_generation: str
    form_abi_version: int
    form_pack_sha256: str
    input_set_ref: str

    _FIELDS = frozenset(
        {
            "review_context_ref",
            "review_scope",
            "review_policy_ref",
            "review_policy_sha256",
            "reviewer_refs",
            "reviewed_base_revision",
            "authority_generation",
            "form_abi_version",
            "form_pack_sha256",
            "input_set_ref",
        }
    )

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("use ReviewContextMaterial.create")

    @classmethod
    def create(
        cls,
        *,
        review_policy_ref: str,
        review_policy_sha256: str,
        reviewer_refs: tuple[str, ...],
        reviewed_base_revision: str,
        authority_generation: str,
        form_abi_version: int,
        form_pack_sha256: str,
        input_set_ref: str,
    ) -> "ReviewContextMaterial":
        reviewers = exact_reviewer_refs(reviewer_refs)
        material = {
            "review_scope": REVIEW_SCOPE,
            "review_policy_ref": exact_ref(
                review_policy_ref, "review_policy_ref", prefix="review_policy:"
            ),
            "review_policy_sha256": exact_sha256(
                review_policy_sha256, "review_policy_sha256"
            ),
            "reviewer_refs": list(reviewers),
            "reviewed_base_revision": exact_revision(
                reviewed_base_revision, "reviewed_base_revision"
            ),
            "authority_generation": exact_text(
                authority_generation, "authority_generation", maximum=512
            ),
            "form_abi_version": exact_int(
                form_abi_version,
                "form_abi_version",
                minimum=7,
                maximum=7,
            ),
            "form_pack_sha256": exact_sha256(
                form_pack_sha256, "form_pack_sha256"
            ),
            "input_set_ref": exact_content_ref(
                input_set_ref,
                "input_set_ref",
                prefix="worksheet_input_set:",
            ),
        }
        return construct(
            cls,
            review_context_ref=stable_ref("source_review", material),
            reviewer_refs=reviewers,
            **{
                key: value
                for key, value in material.items()
                if key != "reviewer_refs"
            },
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "review_context_ref": self.review_context_ref,
            "review_scope": self.review_scope,
            "review_policy_ref": self.review_policy_ref,
            "review_policy_sha256": self.review_policy_sha256,
            "reviewer_refs": list(self.reviewer_refs),
            "reviewed_base_revision": self.reviewed_base_revision,
            "authority_generation": self.authority_generation,
            "form_abi_version": self.form_abi_version,
            "form_pack_sha256": self.form_pack_sha256,
            "input_set_ref": self.input_set_ref,
        }

    def to_json_bytes(self) -> bytes:
        return canonical_json_bytes(self.as_dict())

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ReviewContextMaterial":
        row = exact_fields(value, cls._FIELDS, "ReviewContextMaterial")
        if row["review_scope"] != REVIEW_SCOPE:
            raise ValueError("unsupported review scope")
        rebuilt = cls.create(
            review_policy_ref=row["review_policy_ref"],
            review_policy_sha256=row["review_policy_sha256"],
            reviewer_refs=wire_ref_tuple(
                row["reviewer_refs"], "reviewer_refs", nonempty=True
            ),
            reviewed_base_revision=row["reviewed_base_revision"],
            authority_generation=row["authority_generation"],
            form_abi_version=row["form_abi_version"],
            form_pack_sha256=row["form_pack_sha256"],
            input_set_ref=row["input_set_ref"],
        )
        if (
            rebuilt.review_context_ref != row["review_context_ref"]
            or rebuilt.as_dict() != dict(row)
        ):
            raise ValueError("non-canonical ReviewContextMaterial")
        return rebuilt

    @classmethod
    def from_json_bytes(cls, raw: object) -> "ReviewContextMaterial":
        return strict_decode(raw, cls.from_dict, owner="R4 review context")


__all__ = ["REVIEW_SCOPE", "ReviewContextMaterial"]
