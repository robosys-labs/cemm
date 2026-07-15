"""Combined reversible input/output language pack loader."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

from ..kernel.schema.construction import (
    ConstructionTerm,
    InputConstructionSchema,
    LexicalInputMapping,
    MatchKind,
    PostMatchConstraint,
    TokenConstraint,
)
from ..kernel.schema.lexicalization import LanguageRealizationPack


@dataclass(frozen=True, slots=True)
class SemanticLanguagePack:
    language_tag: str
    input_lexicon: tuple[LexicalInputMapping, ...]
    input_constructions: tuple[InputConstructionSchema, ...]
    realization: LanguageRealizationPack
    fingerprint: str

    @classmethod
    def load(cls, root: Path) -> "SemanticLanguagePack":
        input_path = root / "understanding.json"
        realization_path = root / "realization.json"
        raw = json.loads(input_path.read_text(encoding="utf-8"))
        realization = LanguageRealizationPack.load(realization_path)
        digest = hashlib.sha256(
            input_path.read_bytes() + realization_path.read_bytes()
        ).hexdigest()

        lexicon = tuple(
            LexicalInputMapping(
                mapping_id=item["mapping_id"],
                language_tag=raw["language_tag"],
                surface_forms=tuple(item["surface_forms"]),
                lemma_forms=tuple(item.get("lemma_forms", item["surface_forms"])),
                semantic_key=item["semantic_key"],
                part_of_speech=item.get("part_of_speech", ""),
                morphological_features=dict(item.get("morphological_features", {})),
                grounding_contract_ref=item.get("grounding_contract_ref", ""),
                competence_case_refs=tuple(item.get("competence_case_refs", ())),
                version=int(item.get("version", 1)),
            )
            for item in raw["lexicon"]
        )
        constructions = tuple(
            InputConstructionSchema(
                schema_id=item["schema_id"],
                language_tag=raw["language_tag"],
                terms=tuple(
                    ConstructionTerm(
                        term_id=term["term_id"],
                        constraints=tuple(
                            TokenConstraint(
                                kind=MatchKind(constraint["kind"]),
                                values=tuple(constraint.get("values", ())),
                                negate=bool(constraint.get("negate", False)),
                            )
                            for constraint in term["constraints"]
                        ),
                        capture_key=term.get("capture_key", ""),
                        minimum_occurs=int(term.get("minimum_occurs", 1)),
                        maximum_occurs=int(term.get("maximum_occurs", 1)),
                    )
                    for term in item["terms"]
                ),
                predicate_key=item["predicate_key"],
                role_capture_map=dict(item.get("role_capture_map", {})),
                open_role_keys=tuple(item.get("open_role_keys", ())),
                communicative_force=item.get("communicative_force", "assert"),
                polarity=item.get("polarity", "positive"),
                modality=item.get("modality", "actual"),
                output_kind=item.get("output_kind", "predication"),
                output_metadata=dict(item.get("output_metadata", {})),
                post_constraints=tuple(
                    PostMatchConstraint(
                        constraint_kind=constraint["constraint_kind"],
                        capture_key=constraint.get("capture_key", ""),
                        values=tuple(constraint.get("values", ())),
                        other_capture_key=constraint.get("other_capture_key", ""),
                        negate=bool(constraint.get("negate", False)),
                    )
                    for constraint in item.get("post_constraints", ())
                ),
                competence_case_refs=tuple(item.get("competence_case_refs", ())),
                round_trip_case_refs=tuple(item.get("round_trip_case_refs", ())),
                priority=int(item.get("priority", 0)),
                version=int(item.get("version", 1)),
            )
            for item in raw["constructions"]
        )
        pack = cls(
            language_tag=raw["language_tag"],
            input_lexicon=lexicon,
            input_constructions=constructions,
            realization=realization,
            fingerprint=digest,
        )
        failures = pack.validate()
        if failures:
            raise ValueError(
                f"invalid semantic language pack {root}: " + "; ".join(failures)
            )
        return pack

    def validate(self) -> tuple[str, ...]:
        failures: list[str] = []
        for mapping in self.input_lexicon:
            if not mapping.grounding_contract_ref:
                failures.append(f"{mapping.mapping_id}: no grounding contract")
            if not mapping.competence_case_refs:
                failures.append(f"{mapping.mapping_id}: no competence cases")
        for construction in self.input_constructions:
            if not construction.terms:
                failures.append(f"{construction.schema_id}: empty construction")
            if not construction.competence_case_refs:
                failures.append(f"{construction.schema_id}: no competence cases")
            if not construction.round_trip_case_refs:
                failures.append(f"{construction.schema_id}: no round-trip cases")
        failures.extend(self.realization.validate())
        return tuple(failures)
