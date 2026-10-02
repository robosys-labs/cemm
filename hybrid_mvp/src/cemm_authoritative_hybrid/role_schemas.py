"""Activation-pinned reviewed role orders over primitive, source-local evidence.

This is a construction constraint, not a parser or query engine. Candidate
witnesses identify a match; only the immutable activated index licenses it.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any, Mapping

from .canonical import canonical_bytes, stable_ref
from .forms import _FEATURE_CATEGORIES
from .gaps import BudgetExhausted
from .affordances import SemanticAffordanceIndex
from .contributions import ContributionExpander
from .authority import LinkedAuthority
from .config import RuntimeConfig


@dataclass(frozen=True)
class RoleSelector:
    kind: str
    role: str
    target_kind: str | None = None
    features: tuple[tuple[str, str], ...] = ()
    target_kinds: tuple[str, ...] = ()


@dataclass(frozen=True)
class ReviewedRoleSchema:
    schema_ref: str
    selectors: tuple[RoleSelector, ...]


@dataclass(frozen=True)
class ReviewedCommunicativeSchema:
    """Closed optional actor/event/addressee construction, not generic optionality."""
    schema_ref: str
    selectors: tuple[RoleSelector, ...]


def _communicative_schema(name, row, kinds):
    expected = {
        "construction": "communicative_event",
        "evidence_order": [
            {"kind": "referent", "role": "role:actor", "target_kinds": ["entity", "participant"], "cardinality": "optional"},
            {"kind": "designation", "role": "role:event", "target_kind": "event_type"},
            {"kind": "referent", "role": "role:addressee", "target_kinds": ["entity", "participant"], "cardinality": "optional"},
        ],
    }
    if type(row) is not dict or row != expected or not {"entity", "participant", "event_type"} <= kinds:
        raise ValueError("invalid reviewed communicative construction")
    # Equality alone would admit mutable list/dict subclasses.
    if (type(row["evidence_order"]) is not list
        or any(type(s) is not dict or ("target_kinds" in s and type(s["target_kinds"]) is not list)
               for s in row["evidence_order"])):
        raise ValueError("invalid reviewed communicative selector fields")
    return ReviewedCommunicativeSchema(stable_ref("reviewed_communicative_schema", {"name": name, "row": row}), (
        RoleSelector("referent", "role:actor", target_kinds=("entity", "participant")),
        RoleSelector("designation", "role:event", "event_type"),
        RoleSelector("referent", "role:addressee", target_kinds=("entity", "participant")),
    ))


@dataclass(frozen=True)
class QueryProjectionSelector:
    kind: str
    port: str
    features: tuple[tuple[str, str], ...] = ()
    target_kinds: tuple[str, ...] = ()
    optional: bool = False


@dataclass(frozen=True)
class ReviewedQueryProjectionSchema:
    schema_ref: str
    selectors: tuple[QueryProjectionSelector, ...]
    requested_contents: tuple[str, ...]


@dataclass(frozen=True)
class QueryProjectionBinding:
    """Transient construction port, never a persistent semantic role."""
    port: str
    contribution_slot_ref: str
    source_unit_refs: tuple[str, ...]


@dataclass(frozen=True)
class QueryProjectionMatch:
    index_ref: str
    schema_ref: str
    match_ref: str
    requested_content: str
    target_designation_slot_ref: str
    bindings: tuple[QueryProjectionBinding, ...]
    source_unit_spans: tuple[tuple[str, int, int], ...]
    orthographic_source_unit_refs: tuple[str, ...]


def _query_projection_schema(name, row, patterns, kinds):
    """Activate only the closed transient projection construction contract."""
    if type(row) is not dict or set(row) != {"evidence_order", "result"}:
        raise ValueError("invalid reviewed query projection schema fields")
    result = row["result"]
    if (type(result) is not dict or set(result) != {"kind", "target_port", "requested_contents"}
        or result["kind"] != "query_projection" or result["target_port"] != "target"):
        raise ValueError("invalid reviewed query projection result")
    contents = result["requested_contents"]
    if (type(contents) is not list or not 1 <= len(contents) <= 2
        or any(type(c) is not str or c not in {"description", "definition"} for c in contents)
        or len(set(contents)) != len(contents)):
        raise ValueError("invalid reviewed requested contents")
    raw = row["evidence_order"]
    if type(raw) is not list or len(raw) != 4:
        raise ValueError("query projection requires closed request/binder/determiner/target ports")
    selectors = []
    expected = (("request", "open_variable", (("query", "query"), ("interrogative", "content"))),
                ("binder", "binder", (("binder", "copula"),)),
                ("determiner", "qualifier", (("determiner", "determiner"), ("construction_role", "query_target_article"))))
    for selector, (port, kind, features) in zip(raw[:3], expected, strict=True):
        keys = {"kind", "port", "features"} | ({"cardinality"} if port == "determiner" else set())
        if (type(selector) is not dict or set(selector) != keys
            or selector["kind"] != "feature" or selector["port"] != port
            or selector["features"] != [list(pair) for pair in features]
            or (kind, features) not in patterns
            or (port == "determiner" and selector["cardinality"] != "optional")):
            raise ValueError("unreviewed query projection feature port")
        selectors.append(QueryProjectionSelector("feature", port, features, optional=port == "determiner"))
    target = raw[-1]
    if (type(target) is not dict or set(target) != {"kind", "port", "target_kinds"}
        or target["kind"] != "designation" or target["port"] != "target"):
        raise ValueError("invalid reviewed query projection target port")
    target_kinds = target["target_kinds"]
    if (type(target_kinds) is not list or not 1 <= len(target_kinds) <= 3
        or any(type(k) is not str or k not in {"concept", "entity", "participant"} or k not in kinds for k in target_kinds)
        or len(set(target_kinds)) != len(target_kinds)):
        raise ValueError("unreviewed query projection target kinds")
    selectors.append(QueryProjectionSelector("designation", "target", target_kinds=tuple(target_kinds)))
    return ReviewedQueryProjectionSchema(stable_ref("reviewed_query_projection_schema", {"name": name, "row": row}),
                                         tuple(selectors), tuple(contents))


def _relation_projection_schema(schema: ReviewedRoleSchema) -> bool:
    """Compatibility of the current relation consumer, not an order selector."""
    if type(schema) is not ReviewedRoleSchema:
        return False
    predicates = tuple(s for s in schema.selectors if s.kind == "designation" and s.target_kind == "relation_type")
    referents = tuple(s for s in schema.selectors if s.kind == "designation" and s.target_kind == "entity")
    queries = tuple(s for s in schema.selectors if s.kind == "feature")
    return (len(schema.selectors) == 3 and len(predicates) == len(referents) == len(queries) == 1
            and predicates[0].role == "role:relation"
            and {referents[0].role, queries[0].role} == {"role:subject", "role:object"}
            and queries[0].features == (("query", "query"), ("interrogative", "person")))


def _relation_declarative_schema(schema) -> bool:
    return (type(schema) is ReviewedRoleSchema and len(schema.selectors) == 3
        and tuple(s.role for s in schema.selectors) == ("role:subject", "role:relation", "role:object")
        and schema.selectors[1] == RoleSelector("designation", "role:relation", "relation_type")
        and all(schema.selectors[i] == RoleSelector("referent", role, target_kinds=("entity", "participant"))
                for i, role in ((0, "role:subject"), (2, "role:object"))))


@dataclass(frozen=True)
class SelectedRoleEvidence:
    role: str
    target_kind: str | None
    designation_slot_ref: str | None
    source_unit_refs: tuple[str, ...]
    target_ref: str | None = None


@dataclass(frozen=True)
class RoleSchemaMatch:
    index_ref: str
    schema_ref: str
    match_ref: str
    bindings: tuple[SelectedRoleEvidence, ...]

    @property
    def predicate_slot_ref(self):
        return next(b.designation_slot_ref for b in self.bindings if b.target_kind == "relation_type")

    @property
    def referent_slot_ref(self):
        return next(b.designation_slot_ref for b in self.bindings if b.designation_slot_ref is not None
                    and b.designation_slot_ref != self.predicate_slot_ref)

    @property
    def query_source_ref(self):
        return next(b.source_unit_refs[0] for b in self.bindings if b.designation_slot_ref is None)

    @property
    def query_role(self):
        return next(b.role for b in self.bindings if b.designation_slot_ref is None)

    @property
    def referent_role(self):
        return next(b.role for b in self.bindings if b.designation_slot_ref == self.referent_slot_ref)

    @property
    def witness(self) -> tuple[tuple[str, str], ...]:
        return (("role_schema_index", self.index_ref),
                ("role_schema", self.schema_ref),
                ("role_schema_match", self.match_ref),
                ("projection_source", self.query_source_ref),
                ("projection_role", self.query_role),
                ("referent_slot", self.referent_slot_ref),
                ("referent_role", self.referent_role))

    @property
    def provenance(self) -> tuple[str, ...]:
        return self.index_ref, self.schema_ref, self.match_ref


@dataclass(frozen=True)
class CommunicativeRoleMatch:
    """Authentic source geometry only; explicit actors do not establish force."""
    index_ref: str
    schema_ref: str
    match_ref: str
    predicate_slot_ref: str
    target_ref: str
    frame_ref: str
    control_ref: str
    bindings: tuple[SelectedRoleEvidence, ...]
    source_actor_explicit: bool

    @property
    def provenance(self):
        return self.index_ref, self.schema_ref, self.match_ref, self.control_ref


def role_match_evidence(matches):
    """A bounded complete match set, independently rematched by exact sinks.

    Predicate evidence is shared across referent alternatives; the variable
    selects one member and exact correspondence checks its referent separately.
    This neither chooses an alternative nor duplicates predicate affordances.
    """
    ordered = tuple(sorted(set(matches), key=lambda match: match.match_ref))
    if len(ordered) == 1:
        return ordered[0].witness, ordered[0].provenance
    if not ordered:
        return (), ()
    witness = (("role_schema_index", ordered[0].index_ref),
               ("role_schema_match_set", stable_ref("reviewed_role_match_set", [m.witness for m in ordered])))
    provenance = tuple(dict.fromkeys(ref for match in ordered for ref in match.provenance))
    return witness, provenance


@dataclass(frozen=True)
class ReviewedRoleSchemaIndex:
    authority_generation: str
    authority_content_hash: str
    form_pack_hash: str
    index_ref: str
    schemas: tuple[ReviewedRoleSchema | ReviewedQueryProjectionSchema | ReviewedCommunicativeSchema, ...]
    match_limit: int
    attempt_limit: int
    primitive_patterns: tuple[tuple[str, tuple[tuple[str, str], ...]], ...]
    _activation_identity: tuple[Any, ...]
    _activation_schemas: tuple[ReviewedRoleSchema | ReviewedQueryProjectionSchema | ReviewedCommunicativeSchema, ...]
    _activation_patterns: tuple[tuple[str, tuple[tuple[str, str], ...]], ...]
    _activation_authority: Any
    _activation_config: Any
    _activation_affordances: SemanticAffordanceIndex

    @classmethod
    def from_pack(cls, pack: Mapping[str, Any], authority: Any, config: Any):
        if type(authority) is not LinkedAuthority or type(config) is not RuntimeConfig:
            raise TypeError("reviewed role activation requires exact LinkedAuthority and RuntimeConfig")
        from .proposal_context import _primitive_form_signature
        orders = pack.get("application_role_orders", {})
        if not isinstance(orders, Mapping) or len(orders) > config.max_orientation_alternatives:
            raise ValueError("reviewed role schema bound exceeded")
        schemas = []
        kinds = {atom.kind for atom in authority.atoms.values() if atom.reviewed}
        roles = {role for operator_roles in authority.operator_roles.values() for role in operator_roles}
        patterns = {_primitive_form_signature("orthography", value) for value in ("whitespace", "punctuation")}
        for category, pack_key in _FEATURE_CATEGORIES:
            for info in pack.get(pack_key, {}).values():
                if type(info) is not dict:
                    continue
                value = info.get("kind", category)
                kind, constraints = _primitive_form_signature(category, value,
                    tuple((key, info[key]) for key in ("interrogative", "construction_role") if key in info))
                if kind is not None:
                    patterns.add((kind, constraints))
        patterns = tuple(sorted(patterns))
        known_features = {pair for _, constraints in patterns for pair in constraints}
        for name, row in sorted(orders.items()):
            if isinstance(row, Mapping) and "construction" in row:
                schemas.append(_communicative_schema(name, row, kinds))
                continue
            if not isinstance(row, Mapping) or "evidence_order" not in row:
                continue
            if "result" in row:
                schemas.append(_query_projection_schema(name, row, patterns, kinds))
                continue
            raw = row["evidence_order"]
            if type(raw) is not list or not raw or len(raw) > config.max_orientation_alternatives:
                raise ValueError("reviewed role selectors exceed the construction bound")
            selectors = []
            for selector in raw:
                if type(selector) is not dict:
                    raise ValueError("role selector must be a reviewed object")
                kind, role = selector.get("kind"), selector.get("role")
                if role not in roles:
                    raise ValueError("reviewed role is absent from authority")
                if kind == "designation" and set(selector) == {"kind", "role", "target_kind"}:
                    target_kind = selector["target_kind"]
                    if target_kind not in kinds:
                        raise ValueError("unsupported reviewed designation selector")
                    selectors.append(RoleSelector(kind, role, target_kind))
                elif kind == "feature" and set(selector) == {"kind", "role", "features"}:
                    features = selector["features"]
                    if (type(features) is not list or not features or len(features) > config.max_orientation_alternatives
                        or any(type(pair) is not list or len(pair) != 2 or tuple(pair) not in known_features for pair in features)):
                        raise ValueError("role selector has unreviewed primitive features")
                    selectors.append(RoleSelector(kind, role, features=tuple(map(tuple, features))))
                elif kind == "referent" and set(selector) == {"kind", "role", "target_kinds"}:
                    # Explicit reviewed filler alternatives, never a semantic
                    # kind coercion or a default based on a word/ref spelling.
                    if (role not in {"role:subject", "role:object"}
                        or type(selector["target_kinds"]) is not list
                        or any(type(k) is not str for k in selector["target_kinds"])
                        or selector["target_kinds"] != ["entity", "participant"]
                        or not {"entity", "participant"} <= kinds):
                        raise ValueError("unreviewed relation referent kinds or role")
                    selectors.append(RoleSelector(kind, role, target_kinds=tuple(selector["target_kinds"])))
                else:
                    raise ValueError("invalid reviewed role selector fields")
            if len({s.role for s in selectors}) != len(selectors):
                raise ValueError("reviewed selector roles must be unique")
            schema = ReviewedRoleSchema(stable_ref("reviewed_role_schema", {"name": name, "row": row}), tuple(selectors))
            if _relation_declarative_schema(schema):
                if (set(row) != {"target_kinds", "roles", "evidence_order"}
                    or row["target_kinds"] != ["entity", "relation_type", "entity"]
                    or row["roles"] != ["role:subject", "role:relation", "role:object"]):
                    raise ValueError("invalid reviewed declarative relation projection")
            else:
                grounded = tuple(s for s in selectors if s.kind == "designation")
                if row.get("target_kinds") != [s.target_kind for s in grounded] or row.get("roles") != [s.role for s in grounded]:
                    raise ValueError("reviewed role schema grounded projection disagrees")
            if any(s.target_kind == "relation_type" for s in selectors) and not (_relation_projection_schema(schema) or _relation_declarative_schema(schema)):
                raise ValueError("reviewed mixed relation schema is incompatible with its projection consumer")
            schemas.append(schema)
        pack_hash = "sha256:" + hashlib.sha256(canonical_bytes(pack)).hexdigest()
        if sum(type(s) is ReviewedCommunicativeSchema for s in schemas) > 1:
            raise ValueError("reviewed communicative construction must have one owner")
        identity = {"authority_generation": authority.generation,
                    "authority_content_hash": authority.content_hash,
                    "form_pack_hash": pack_hash,
                    "schemas": [s.schema_ref for s in schemas]}
        index_ref = stable_ref("reviewed_role_schema_index", identity)
        schemas = tuple(schemas)
        affordances = SemanticAffordanceIndex(authority, config)
        return cls(authority.generation, authority.content_hash, pack_hash,
                   index_ref, schemas, config.max_orientation_alternatives, config.max_beam_states,
                   patterns, (authority.generation, authority.content_hash, pack_hash, index_ref,
                              config.max_orientation_alternatives, config.max_beam_states,
                              config.max_affordances_per_target, authority, config, affordances), schemas, patterns,
                   authority, config, affordances)

    def validate_activation(self, authority, pack=None):
        if type(authority) is not LinkedAuthority:
            raise TypeError("reviewed role activation requires exact LinkedAuthority")
        if (authority is not self._activation_authority
            or not self.identity_is_current or self.authority_generation != authority.generation
            or self.authority_content_hash != authority.content_hash):
            raise ValueError("reviewed role schema index has stale authority or activation")
        if pack is not None and self.form_pack_hash != "sha256:" + hashlib.sha256(canonical_bytes(pack)).hexdigest():
            raise ValueError("reviewed role schema index differs from active form pack")

    @property
    def identity_is_current(self):
        return (type(self._activation_identity) is tuple and len(self._activation_identity) == 10
                and self._activation_identity[7] is self._activation_authority
                and self._activation_identity[8] is self._activation_config
                and self._activation_identity[9] is self._activation_affordances
                and self._activation_identity[:7] == (self.authority_generation, self.authority_content_hash,
                                             self.form_pack_hash, self.index_ref, self.match_limit, self.attempt_limit,
                                             self._activation_config.max_affordances_per_target)
                and self.schemas is self._activation_schemas
                and self.primitive_patterns is self._activation_patterns
                and self._activation_authority.generation == self.authority_generation
                and self._activation_authority.content_hash == self.authority_content_hash
                and self._activation_affordances.authority_generation == self.authority_generation
                and self._activation_affordances._authority is self._activation_authority
                and self._activation_affordances._config is self._activation_config
                and self._activation_affordances._max == self._activation_config.max_affordances_per_target)

    def matches(self, designations, contributions, source_spans) -> tuple[RoleSchemaMatch | QueryProjectionMatch | CommunicativeRoleMatch, ...]:
        from .proposal_context import _primitive_form_ref, _primitive_form_ports
        if not self.identity_is_current:
            raise ValueError("reviewed role schema index has stale activation")
        if (not source_spans or len(source_spans) > 64 or any(type(start) is not int or type(end) is not int or start < 0 or end <= start
                                  for _, start, end in source_spans)
            or any(left[2] > right[1] for left, right in zip(source_spans, source_spans[1:]))
            or len({ref for ref, _, _ in source_spans}) != len(source_spans)):
            raise ValueError("reviewed role source geometry is malformed")
        spans = {ref: (start, end) for ref, start, end in source_spans}
        features: dict[str, set[tuple[str, str]]] = {}
        primitives: dict[str, list[Any]] = {}
        for row in contributions:
            if len(row.source_unit_refs) != 1 or not row.constraints:
                continue
            ref = row.source_unit_refs[0]
            if (row.kind, row.constraints) not in self.primitive_patterns:
                continue
            category, value = row.constraints[0]
            if (ref not in spans or row.provenance_refs != (ref,)
                or row.contribution_ref != _primitive_form_ref(ref, category, value, row.target_ref)
                or (row.kind != "reference" and (row.input_ports, row.output_ports) != _primitive_form_ports(row.kind, category))
                or (row.kind == "reference" and (row.target_ref is None) != (row.target_kind is None))
                or (row.kind == "reference" and row.input_ports != _primitive_form_ports("reference")[0])
                or (row.kind != "reference" and (row.target_ref is not None or row.target_kind is not None))):
                raise ValueError("reviewed primitive contribution ownership is malformed")
            features.setdefault(ref, set()).update(row.constraints)
            primitives.setdefault(ref, []).append(row)
        profiles_by_target = {}
        anchors_by_designation = {}
        def authentic_anchor(contribution, designation):
            """Regenerate the selected anchor through the existing bounded owners."""
            target = self._activation_authority.atoms.get(designation.target_ref)
            if target is None or target.kind != designation.target_kind:
                return False
            if designation.target_ref not in profiles_by_target:
                profiles_by_target[designation.target_ref] = self._activation_affordances.for_target(designation.target_ref)
            if designation.slot_ref not in anchors_by_designation:
                anchors_by_designation[designation.slot_ref] = tuple(
                    ContributionExpander._make_contribution(kind="anchor",
                        source_unit_refs=designation.source_unit_refs, target_ref=designation.target_ref,
                        input_ports=profile.input_ports, output_ports=profile.output_ports, frame_ref=profile.frame_ref)
                    for profile in profiles_by_target[designation.target_ref] if "anchor" in profile.contribution_kinds)
            provenance = tuple(d.slot_ref for d in designations if d.target_ref == designation.target_ref)
            return contribution.provenance_refs == provenance and any(
                (contribution.contribution_ref, contribution.kind, contribution.source_unit_refs,
                    contribution.target_ref, contribution.input_ports, contribution.output_ports, contribution.constraints)
                == (expected.contribution_ref, expected.kind, expected.source_unit_refs,
                    expected.target_ref, expected.input_ports, expected.output_ports, expected.constraints)
                for expected in anchors_by_designation[designation.slot_ref])
        boundaries = sorted(spans[ref] for ref, pairs in features.items()
                            if ("orthography", "sentence_boundary") in pairs
                            or {("orthography", "punctuation"), ("discourse", "question")} <= pairs)
        matches = []
        regions = tuple(zip((0, *(end for _, end in boundaries)), (*(begin for begin, _ in boundaries), max(e for _, e in spans.values()))))
        attempts = 0
        def spend():
            nonlocal attempts
            attempts += 1
            if attempts > self.attempt_limit:
                raise BudgetExhausted("reviewed_role_match_attempts", self.attempt_limit)

        def retain(match):
            if match not in matches:
                matches.append(match)
            if len(matches) > self.match_limit:
                raise BudgetExhausted("reviewed_role_matches", self.match_limit)

        def communicative_predicate(designation):
            control = self._activation_authority.communicative_control_for_target(designation.target_ref)
            target = self._activation_authority.atoms.get(designation.target_ref)
            if control is None or target is None or target.kind != designation.target_kind or target.kind != "event_type":
                return None
            profiles = self._activation_affordances.for_target(designation.target_ref)
            provenance = tuple(d.slot_ref for d in designations if d.target_ref == designation.target_ref)
            for profile in profiles:
                if profile.frame_ref != control.source_frame_ref or "predicate" not in profile.contribution_kinds:
                    continue
                expected = ContributionExpander._make_contribution(kind="predicate",
                    source_unit_refs=designation.source_unit_refs, target_ref=designation.target_ref,
                    input_ports=profile.input_ports, output_ports=profile.output_ports, frame_ref=profile.frame_ref)
                if any(c.kind == "predicate" and c.target_kind == "event_type" and c.provenance_refs == provenance
                    and (c.contribution_ref, c.source_unit_refs, c.target_ref, c.input_ports, c.output_ports, c.constraints)
                    == (expected.contribution_ref, expected.source_unit_refs, expected.target_ref,
                        expected.input_ports, expected.output_ports, expected.constraints) for c in contributions):
                    return control
            return None

        for schema in self.schemas:
            projection = type(schema) is ReviewedQueryProjectionSchema
            communication = type(schema) is ReviewedCommunicativeSchema
            if communication and not any(d.target_kind == "event_type" and communicative_predicate(d) is not None for d in designations):
                continue
            for start, end in regions:
                if communication:
                    # Only one complete direct source. Reports, links, scopes,
                    # quotation and compound sources cannot acquire this match.
                    if len(boundaries) > 1 or (boundaries and boundaries[0][1] != max(e for _, e in spans.values())) or start != 0:
                        continue
                    if any(("discourse", "question") in pairs for pairs in features.values()):
                        continue
                local = tuple(ref for ref, begin, finish in source_spans if start <= begin and finish <= end
                              and ("orthography", "whitespace") not in features.get(ref, set()))
                # Missing closed evidence makes a schema ineligible before
                # grounded prefix alternatives spend any matching budget.
                if any(selector.kind == "feature" and not (projection and selector.optional) and not any(
                    set(selector.features) <= features.get(ref, set()) for ref in local
                ) for selector in schema.selectors):
                    continue
                def walk(position, cursor, selected, target_slot_ref=None):
                    if position == len(schema.selectors):
                        if cursor == len(local):
                            if communication:
                                predicate = next(b for b in selected if b.role == "role:event")
                                designation = next(d for d in designations if d.slot_ref == predicate.designation_slot_ref)
                                control = communicative_predicate(designation)
                                if control is None:
                                    return
                                material = {"index": self.index_ref, "schema": schema.schema_ref,
                                    "predicate": designation.slot_ref, "control": control.control_ref,
                                    "bindings": [(b.role, b.target_kind, b.designation_slot_ref, b.source_unit_refs, b.target_ref) for b in selected]}
                                retain(CommunicativeRoleMatch(self.index_ref, schema.schema_ref,
                                    stable_ref("reviewed_communicative_match", material), designation.slot_ref,
                                    designation.target_ref, control.source_frame_ref, control.control_ref, selected,
                                    any(b.role == control.actor_role_ref for b in selected)))
                                return
                            if projection:
                                # Retain the full clause and its terminal punctuation;
                                # orthography is evidence, not a semantic port.
                                clause = tuple(row for row in source_spans if start <= row[1] and row[2] <= end
                                    or row[1] == end and (row[1], row[2]) in boundaries)
                                orthographic = tuple(ref for ref, _, _ in clause if
                                    ("orthography", "whitespace") in features.get(ref, set())
                                    or ("orthography", "punctuation") in features.get(ref, set()))
                                for content in schema.requested_contents:
                                    spend()
                                    material = {"index": self.index_ref, "schema": schema.schema_ref,
                                        "requested_content": content, "target_designation_slot_ref": target_slot_ref,
                                        "bindings": [(b.port, b.contribution_slot_ref, b.source_unit_refs) for b in selected],
                                        "source_unit_spans": clause, "orthographic_source_unit_refs": orthographic}
                                    retain(QueryProjectionMatch(self.index_ref, schema.schema_ref,
                                        stable_ref("reviewed_query_projection_match", material), content,
                                        target_slot_ref, selected, clause, orthographic))
                                return
                            material = {"index": self.index_ref, "schema": schema.schema_ref,
                                        "bindings": [(b.role, b.target_kind, b.designation_slot_ref, b.source_unit_refs, b.target_ref) for b in selected]}
                            match = RoleSchemaMatch(self.index_ref, schema.schema_ref,
                                stable_ref("reviewed_role_match", material), selected)
                            retain(match)
                        return
                    selector = schema.selectors[position]
                    if (projection and selector.optional) or (communication and selector.kind == "referent"):
                        spend()
                        walk(position + 1, cursor, selected, target_slot_ref)
                    if cursor >= len(local):
                        return
                    if selector.kind == "feature":
                        if projection:
                            candidates = tuple((QueryProjectionBinding(selector.port, c.slot_ref, c.source_unit_refs), None)
                                for c in primitives.get(local[cursor], ()) if set(selector.features) <= set(c.constraints)
                                and not features[local[cursor]] - set(c.constraints))
                        else:
                            candidates = (SelectedRoleEvidence(selector.role, None, None, (local[cursor],)),) if set(selector.features) <= features.get(local[cursor], set()) else ()
                    elif projection:
                        candidates = tuple((QueryProjectionBinding("target", c.slot_ref, d.source_unit_refs), d.slot_ref)
                            for d in designations if d.target_kind in selector.target_kinds and d.source_unit_refs
                            and d.source_unit_refs[0] == local[cursor]
                            for c in contributions if c.kind == "anchor" and c.target_ref == d.target_ref
                            and c.target_kind == d.target_kind and c.source_unit_refs == d.source_unit_refs
                            and authentic_anchor(c, d))
                    elif selector.kind == "referent":
                        candidates = tuple(SelectedRoleEvidence(selector.role, d.target_kind, d.slot_ref, d.source_unit_refs, d.target_ref)
                            for d in designations if d.target_kind in selector.target_kinds and d.source_unit_refs
                            and d.source_unit_refs[0] == local[cursor]
                            and self._activation_authority.atoms.get(d.target_ref) is not None
                            and self._activation_authority.atoms[d.target_ref].kind == d.target_kind)
                        candidates += tuple(SelectedRoleEvidence(selector.role, c.target_kind, None, c.source_unit_refs, c.target_ref)
                            for c in primitives.get(local[cursor], ()) if c.kind == "reference"
                            and c.target_kind in selector.target_kinds and c.target_ref is not None
                            and self._activation_authority.atoms.get(c.target_ref) is not None
                            and self._activation_authority.atoms[c.target_ref].kind == c.target_kind)
                    else:
                        candidates = tuple(SelectedRoleEvidence(selector.role, d.target_kind, d.slot_ref, d.source_unit_refs)
                            for d in designations if d.target_kind == selector.target_kind and d.source_unit_refs
                            and d.source_unit_refs[0] == local[cursor]
                            and (not communication or communicative_predicate(d) is not None))
                    for choice in candidates:
                        spend()
                        candidate, selected_target = choice if projection else (choice, None)
                        if any(ref not in spans for ref in candidate.source_unit_refs):
                            raise ValueError("reviewed role designation source is missing")
                        # This bounded mixed relation construction has no
                        # reviewed lexical-overlap license. A designation may
                        # cover whitespace, but cannot swallow another closed
                        # contribution (scope, linker, punctuation, etc.).
                        # Other construction consumers retain their own policy.
                        designation_evidence = selector.kind == "designation" if projection else candidate.designation_slot_ref is not None
                        if designation_evidence and (communication or projection or _relation_projection_schema(schema) or _relation_declarative_schema(schema)) and (
                            any(features.get(ref, set()) - {("orthography", "whitespace")}
                                    for ref in candidate.source_unit_refs)):
                            continue
                        refs = tuple(ref for ref in candidate.source_unit_refs
                                     if ("orthography", "whitespace") not in features.get(ref, set()))
                        if refs and local[cursor:cursor + len(refs)] == refs:
                            walk(position + 1, cursor + len(refs), (*selected, candidate), selected_target or target_slot_ref)
                walk(0, 0, ())
        return tuple(matches)


def relation_projection_matches(index, matches):
    """Keep generic matches out of the current relation-only projection owner."""
    licensed = {s.schema_ref for s in index.schemas if _relation_projection_schema(s)}
    return tuple(match for match in matches if type(match) is RoleSchemaMatch and match.schema_ref in licensed)


def relation_declarative_matches(index, matches):
    licensed = {s.schema_ref for s in index.schemas if _relation_declarative_schema(s)}
    return tuple(match for match in matches if type(match) is RoleSchemaMatch and match.schema_ref in licensed)


def communicative_role_errors(context, program, index, *, authority=None):
    """Independent exact bindings over authentic construction evidence.

    Situated fillers are checked for context-relative role/provenance/kind only.
    Actual Orientation participant targets and performed force are separate owners.
    """
    from .proposal_context import ProposalContext, ContributionSlot, _primitive_form_ref, _primitive_form_ports
    if type(context) is not ProposalContext:
        return ()
    applications = tuple(a for a in program.actions if a.action_type == "instantiate_operator"
        and len(a.arguments) == 2 and context.frame(a.arguments[1]) is not None
        and context.frame(a.arguments[1]).operator_ref == "op:event"
        and context.frame(a.arguments[1]).predicate_kind == "event_type")
    if not applications:
        return ()
    if type(index) is not ReviewedRoleSchemaIndex:
        # Source-only nested/multi-application component fixtures retain their
        # existing scope/report contracts; none establishes performed force.
        direct = sum(a.action_type == "instantiate_operator" for a in program.actions) == 1 and not any(
            a.action_type in {"attach_scope", "bind_nested_application"} for a in program.actions)
        if direct and any(context.frame(a.arguments[1]).source_unit_refs
            and {"role:actor", "role:addressee"} <= set((*context.frame(a.arguments[1]).required_roles,
                                                        *context.frame(a.arguments[1]).optional_roles))
            and not context.frame(a.arguments[1]).proposition_roles for a in applications):
            return ("communicative_schema_index_missing",)
        return ()
    applications = tuple(a for a in applications
        if index._activation_authority.communicative_control_for_target(context.frame(a.arguments[1]).predicate_target_ref) is not None)
    if not applications:
        return ()
    if (not index.identity_is_current or index.authority_generation != context.revision_pin.authority_generation
        or (authority is not None and (authority is not index._activation_authority
            or index.authority_content_hash != authority.content_hash))):
        return ("communicative_schema_index_stale",)
    try:
        matches = tuple(m for m in index.matches(context.designation_slots, context.contribution_slots,
            context.source_unit_spans) if type(m) is CommunicativeRoleMatch)
    except BudgetExhausted:
        return ("communicative_match_budget_exhausted",)
    except (ValueError, KeyError, TypeError, StopIteration):
        return ("communicative_evidence_invalid",)
    errors = []
    assignments = {s.source_unit_ref: s for s in program.source_assignments}
    if len(assignments) != len(program.source_assignments):
        return ("communicative_duplicate_source_assignment",)

    def selected_role_is_authentic(contribution, wanted, role, target):
        """Regenerate the consumed record before dispatching binding actions."""
        if contribution.kind not in {"anchor", "reference"}:
            return False
        if wanted.designation_slot_ref is not None:
            referent = context.designation(wanted.designation_slot_ref)
            expected_reference = ContributionSlot.create(
                contribution_ref=stable_ref("designation_reference_contribution", {
                    "designation_slot_ref": referent.slot_ref, "target_ref": target,
                    "target_kind": wanted.target_kind, "source_unit_refs": list(wanted.source_unit_refs),
                    "compatible_roles": [role]}),
                kind="reference", source_unit_refs=wanted.source_unit_refs,
                target_ref=target, target_kind=wanted.target_kind, input_ports=(), output_ports=(role,),
                constraints=(("resolution_kind", "designation"),),
                provenance_refs=tuple(dict.fromkeys((referent.slot_ref,
                    referent.designation_fact_ref, *referent.provenance_refs))))
            if contribution == expected_reference:
                return True
            # A designation can also supply an exact activated target affordance.
            # Its existing owner must actually expose this role; a compatible
            # forged port or a retained authentic alternative grants nothing.
            provenance = tuple(d.slot_ref for d in context.designation_slots if d.target_ref == target)
            for profile in index._activation_affordances.for_target(target):
                if contribution.kind not in profile.contribution_kinds or role not in profile.output_ports:
                    continue
                semantic = ContributionExpander._make_contribution(kind=contribution.kind,
                    source_unit_refs=wanted.source_unit_refs, target_ref=target,
                    input_ports=profile.input_ports, output_ports=profile.output_ports, frame_ref=profile.frame_ref)
                expected = ContributionSlot.create(contribution_ref=semantic.contribution_ref, kind=semantic.kind,
                    source_unit_refs=semantic.source_unit_refs, target_ref=target, target_kind=wanted.target_kind,
                    input_ports=semantic.input_ports, output_ports=semantic.output_ports,
                    constraints=semantic.constraints, provenance_refs=provenance)
                if contribution == expected:
                    return True
            return False
        if contribution.kind != "reference" or ("reference", contribution.constraints) not in index.primitive_patterns:
            return False
        category, value = contribution.constraints[0]
        source = wanted.source_unit_refs[0]
        expected_reference = ContributionSlot.create(
            contribution_ref=_primitive_form_ref(source, category, value, target), kind="reference",
            source_unit_refs=(source,), target_ref=target, target_kind=wanted.target_kind,
            input_ports=_primitive_form_ports("reference")[0], output_ports=(role,),
            constraints=contribution.constraints, provenance_refs=(source,))
        return contribution == expected_reference

    for app in applications:
        frame = context.frame(app.arguments[1])
        local_matches = tuple(m for m in matches if m.predicate_slot_ref == frame.designation_slot_ref)
        # Scoped/reported/compound and other modes retain existing semantics.
        # This construction never authenticates direct force for those graphs.
        if not local_matches:
            mode = context.mode_slot(program.mode_slot_ref)
            direct = mode is not None and mode.mode == "OBSERVE" and sum(
                a.action_type == "instantiate_operator" for a in program.actions) == 1 and not any(
                a.action_type in {"attach_scope", "bind_nested_application"} for a in program.actions)
            direct = direct and not any(r.critical for r in context.residual_evidence) and not any(
                c.kind in {"scope", "connector", "binder", "open_variable"}
                or (c.kind == "discourse" and any(pair not in {
                    ("orthography", "whitespace"), ("orthography", "punctuation"),
                    ("orthography", "sentence_boundary")} for pair in c.constraints))
                for c in context.contribution_slots)
            if direct or any(ref.startswith("reviewed_communicative_match:") for ref in frame.provenance_refs):
                errors.append("communicative_schema_match_missing")
            continue
        mode = context.mode_slot(program.mode_slot_ref)
        if mode is None or mode.mode != "OBSERVE":
            errors.append("communicative_observe_mode_required")
            continue
        control = index._activation_authority.communicative_control_for_target(frame.predicate_target_ref)
        signature = index._activation_authority.by_event_signature(frame.predicate_target_ref)
        bindings = tuple(a for a in program.actions if a.action_type in {"bind_reference", "bind_role"}
                         and len(a.arguments) == 3 and a.arguments[0] == app.arguments[0])
        def corresponds(match):
            designation = context.designation(match.predicate_slot_ref)
            profiles = tuple(p for p in index._activation_affordances.for_target(match.target_ref)
                if p.frame_ref == match.frame_ref and "predicate" in p.contribution_kinds)
            if (control is None or signature is None or designation is None
                or (frame.predicate_target_ref, frame.predicate_kind, frame.affordance_frame_ref, frame.source_unit_refs)
                != (match.target_ref, "event_type", match.frame_ref, designation.source_unit_refs)
                or control.control_ref != match.control_ref or control.source_frame_ref != match.frame_ref
                or not set(match.provenance) <= set(frame.provenance_refs)
                or app.source_unit_refs != designation.source_unit_refs
                or len(bindings) != 2
                or set(frame.required_roles) | set(frame.optional_roles) != {control.actor_role_ref, control.addressee_role_ref}
                or frame.proposition_roles or frame.derived_role_targets):
                return False
            if (frame.required_roles != tuple(s.role for s in signature.roles if s.required)
                or frame.optional_roles != tuple(s.role for s in signature.roles if not s.required)
                or not any(p.output_ports and frame.structural_role_ref == p.output_ports[0] for p in profiles)):
                return False
            expected_predicates = tuple(ContributionExpander._make_contribution(kind="predicate",
                source_unit_refs=designation.source_unit_refs, target_ref=match.target_ref,
                input_ports=p.input_ports, output_ports=p.output_ports, frame_ref=p.frame_ref) for p in profiles)
            designation_provenance = tuple(d.slot_ref for d in context.designation_slots if d.target_ref == match.target_ref)
            predicates = tuple(c for c in context.contribution_slots if c.kind == "predicate"
                and c.target_kind == "event_type" and c.provenance_refs == designation_provenance and c.literal_value is None
                and any((c.contribution_ref, c.source_unit_refs, c.target_ref, c.input_ports, c.output_ports, c.constraints)
                    == (expected.contribution_ref, expected.source_unit_refs, expected.target_ref,
                        expected.input_ports, expected.output_ports, expected.constraints) for expected in expected_predicates))
            for source in designation.source_unit_refs:
                assignment = assignments.get(source)
                if (assignment is None or assignment.assignment_kind != "predicate"
                    or assignment.contribution_slot_ref not in {c.slot_ref for c in predicates}
                    or assignment.target_action_ref != app.action_ref or assignment.target_role_ref is not None):
                    return False
            for role in (control.actor_role_ref, control.addressee_role_ref):
                actions = tuple(a for a in bindings if a.arguments[1] == role)
                if len(actions) != 1:
                    return False
                action = actions[0]
                filler = context.reference(action.arguments[2]) if action.action_type == "bind_reference" else context.contribution(action.arguments[2])
                if filler is None:
                    return False
                spec = next((s for s in signature.roles if s.role == role), None)
                atom = index._activation_authority.atoms.get(filler.target_ref)
                if spec is None or atom is None or atom.kind != filler.target_kind or filler.target_kind not in spec.filler_kinds:
                    return False
                wanted = next((b for b in match.bindings if b.role == role), None)
                if wanted is None:
                    if (action.action_type != "bind_reference" or filler.resolution_kind != "situated_participant"
                        or filler.source_unit_refs or action.source_unit_refs or filler.target_kind != "participant"
                        or filler.compatible_roles != (role,) or filler.target_ref not in context.context_refs
                        or filler.provenance_refs != (context.orientation_ref, frame.slot_ref)):
                        return False
                    continue
                target = context.designation(wanted.designation_slot_ref).target_ref if wanted.designation_slot_ref else wanted.target_ref
                if ((filler.target_ref, filler.target_kind, filler.source_unit_refs) != (target, wanted.target_kind, wanted.source_unit_refs)
                    or action.source_unit_refs != wanted.source_unit_refs):
                    return False
                for source in wanted.source_unit_refs:
                    assignment = assignments.get(source)
                    contribution = context.contribution(assignment.contribution_slot_ref) if assignment else None
                    if (assignment is None or contribution is None or assignment.target_action_ref != action.action_ref
                        or assignment.target_role_ref != role or contribution.target_ref != target
                        or contribution.source_unit_refs != wanted.source_unit_refs):
                        return False
                    if not selected_role_is_authentic(contribution, wanted, role, target):
                        return False
                    if action.action_type == "bind_reference":
                        if (assignment.assignment_kind != "reference" or contribution.kind != "reference"
                            or frame.slot_ref not in filler.provenance_refs
                            or (wanted.designation_slot_ref is not None and (
                                filler.resolution_kind != "designation" or wanted.designation_slot_ref not in filler.provenance_refs
                                or contribution.slot_ref not in filler.provenance_refs))
                            or (wanted.designation_slot_ref is None and (
                                filler.resolution_kind != "participant_deixis" or source not in filler.provenance_refs))):
                            return False
                    elif assignment.assignment_kind != "role" or contribution.slot_ref != action.arguments[2]:
                        return False
            return True
        if not any(corresponds(m) for m in local_matches):
            errors.append("communicative_role_correspondence")
    return tuple(dict.fromkeys(errors))


def relation_declarative_errors(context, program, index, *, authority=None):
    """Rematch actual source evidence, never trust reference-role hints."""
    from .proposal_context import ProposalContext
    if type(context) is not ProposalContext:
        return ()
    applications = tuple(a for a in program.actions if a.action_type == "instantiate_operator"
        and context.frame(a.arguments[1]) is not None
        and context.frame(a.arguments[1]).operator_ref == "op:relation"
        and context.frame(a.arguments[1]).predicate_kind == "relation_type")
    # Query construction has its own independently reviewed matcher.
    projected = {a.arguments[0] for a in program.actions if a.action_type == "project_variable" and len(a.arguments) == 3}
    applications = tuple(a for a in applications if a.arguments[0] not in projected)
    if not applications:
        return ()
    if type(index) is not ReviewedRoleSchemaIndex:
        # Source-free semantic fixtures are not public interpretation evidence.
        if any(r.resolution_kind == "participant_deixis" for r in context.reference_slots):
            return ("relation_declarative_schema_index_missing",)
        return ()
    if not index.identity_is_current or index.authority_generation != context.revision_pin.authority_generation or (
        authority is not None and (index.authority_generation != authority.generation or index.authority_content_hash != authority.content_hash)):
        return ("relation_declarative_schema_index_stale",)
    try:
        matches = relation_declarative_matches(index, index.matches(context.designation_slots, context.contribution_slots, context.source_unit_spans))
    except BudgetExhausted:
        return ("relation_declarative_match_budget_exhausted",)
    except (ValueError, KeyError, TypeError, StopIteration):
        return ("relation_declarative_evidence_invalid",)
    errors = []
    assignments = {s.source_unit_ref: s for s in program.source_assignments}
    for application in applications:
        frame = context.frame(application.arguments[1])
        local_matches = tuple(m for m in matches if m.predicate_slot_ref == frame.designation_slot_ref)
        bindings = tuple(a for a in program.actions if a.action_type in {"bind_reference", "bind_role"} and a.arguments[0] == application.arguments[0])
        if not local_matches:
            if any((context.reference(a.arguments[2]) if a.action_type == "bind_reference" else context.contribution(a.arguments[2])).target_kind == "participant" for a in bindings
                if (context.reference(a.arguments[2]) if a.action_type == "bind_reference" else context.contribution(a.arguments[2])) is not None):
                errors.append("relation_declarative_schema_match_missing")
            continue
        def corresponds(match):
            expected = tuple(b for b in match.bindings if b.role != "role:relation")
            if len(bindings) != len(expected):
                return False
            for wanted in expected:
                designation = context.designation(wanted.designation_slot_ref) if wanted.designation_slot_ref else None
                target = designation.target_ref if designation is not None else wanted.target_ref
                actual = tuple(a for a in bindings if a.arguments[1] == wanted.role)
                if len(actual) != 1:
                    return False
                action = actual[0]
                filler = context.reference(action.arguments[2]) if action.action_type == "bind_reference" else context.contribution(action.arguments[2])
                if filler is None or (filler.target_ref, filler.target_kind, filler.source_unit_refs) != (target, wanted.target_kind, wanted.source_unit_refs) or action.source_unit_refs != wanted.source_unit_refs:
                    return False
                for source in wanted.source_unit_refs:
                    assignment = assignments.get(source)
                    if assignment is None or assignment.target_action_ref != action.action_ref or assignment.target_role_ref != wanted.role:
                        return False
            return True
        if not any(corresponds(match) for match in local_matches):
            errors.append("relation_declarative_role_correspondence")
    return tuple(dict.fromkeys(errors))


def relation_query_errors(context, program, index, *, authority=None) -> tuple[str, ...]:
    """Rederive relation projection independently of candidate role/witness hints."""
    from .proposal_context import ProposalContext
    if type(context) is not ProposalContext:
        # Semantic-only compiler fixtures have no ORIENT source envelope.
        # They are not accepted by the exact runtime/context boundary.
        return ()
    projections = []
    for action in program.actions:
        if action.action_type != "project_variable" or len(action.arguments) != 3:
            continue
        variable = context.variable(action.arguments[1])
        frame = context.frame(variable.application_frame_ref) if variable else None
        if frame is not None and frame.operator_ref == "op:relation":
            projections.append((action, variable, frame))
    if not projections:
        return ()
    if type(index) is not ReviewedRoleSchemaIndex:
        return ("relation_query_schema_index_missing",)
    if not index.identity_is_current or (
        index.authority_generation != context.revision_pin.authority_generation
    ) or (
        authority is not None and (index.authority_generation != authority.generation or index.authority_content_hash != authority.content_hash)
    ):
        return ("relation_query_schema_index_stale",)
    try:
        matches = relation_projection_matches(index, index.matches(
            context.designation_slots, context.contribution_slots, context.source_unit_spans))
    except BudgetExhausted:
        return ("relation_query_match_budget_exhausted",)
    except (ValueError, KeyError, TypeError, StopIteration):
        return ("relation_query_primitive_evidence_invalid",)
    errors = []
    for action, variable, frame in projections:
        match = next((m for m in matches if m.predicate_slot_ref == frame.designation_slot_ref
                      and variable.construction_ref == m.match_ref), None)
        if match is None:
            errors.append("relation_query_schema_match_missing")
            continue
        predicate = context.designation(match.predicate_slot_ref)
        referent = context.designation(match.referent_slot_ref)
        witness, provenance = role_match_evidence(tuple(m for m in matches
                                                       if m.predicate_slot_ref == frame.designation_slot_ref))
        if (variable.role_ref != match.query_role or variable.source_unit_refs != (match.query_source_ref,)
            or action.source_unit_refs != variable.source_unit_refs):
            errors.append("relation_query_variable_owner")
        if (frame.predicate_target_ref != predicate.target_ref or frame.predicate_kind != predicate.target_kind
            or frame.source_unit_refs != predicate.source_unit_refs
            or not set(provenance) <= set(frame.provenance_refs)):
            errors.append("relation_query_predicate_owner")
        evidence = tuple(c for c in context.contribution_slots if c.kind == "predicate"
                         and c.target_ref == predicate.target_ref and c.source_unit_refs == predicate.source_unit_refs)
        evidence = tuple(c for c in evidence
                         if tuple(pair for pair in c.constraints if pair[0] in {
                             "role_schema_index", "role_schema", "role_schema_match", "role_schema_match_set",
                             "projection_source", "projection_role", "referent_slot", "referent_role"}) == witness
                         and set(provenance) <= set(c.provenance_refs))
        if not evidence:
            errors.append("relation_query_witness_mismatch")
        applications = tuple(a for a in program.actions if a.action_type == "instantiate_operator"
                             and a.arguments[1] == frame.slot_ref)
        if len(applications) != 1:
            errors.append("relation_query_application_owner")
            continue
        app = applications[0]
        if app.source_unit_refs != frame.source_unit_refs:
            errors.append("relation_query_predicate_sources")
        bindings = tuple(a for a in program.actions if a.action_type in {"bind_reference", "bind_role"}
                         and a.arguments[0] == app.arguments[0])
        if len(bindings) != 1 or bindings[0].arguments[1] != match.referent_role:
            errors.append("relation_query_referent_role")
            continue
        binding = bindings[0]
        reference = context.reference(binding.arguments[2]) if binding.action_type == "bind_reference" else context.contribution(binding.arguments[2])
        if (reference is None or reference.target_ref != referent.target_ref
            or reference.source_unit_refs != referent.source_unit_refs
            or binding.source_unit_refs != referent.source_unit_refs):
            errors.append("relation_query_referent_owner")
        assignments = {a.source_unit_ref: a for a in program.source_assignments}
        if len(assignments) != len(program.source_assignments):
            errors.append("relation_query_duplicate_source_assignment")
        for ref in predicate.source_unit_refs:
            assignment = assignments.get(ref)
            if (assignment is None or assignment.assignment_kind != "predicate"
                or assignment.contribution_slot_ref not in {c.slot_ref for c in evidence}
                or assignment.target_action_ref != app.action_ref or assignment.target_role_ref is not None):
                errors.append("relation_query_predicate_assignment")
        for ref in referent.source_unit_refs:
            assignment = assignments.get(ref)
            contribution = context.contribution(assignment.contribution_slot_ref) if assignment else None
            if (assignment is None or assignment.target_action_ref != binding.action_ref
                or assignment.target_role_ref != match.referent_role
                or contribution is None or contribution.target_ref != referent.target_ref
                or contribution.source_unit_refs != referent.source_unit_refs
                or (binding.action_type == "bind_reference" and (
                    assignment.assignment_kind != "reference" or contribution.kind != "reference"
                    or reference is None or contribution.slot_ref not in reference.provenance_refs))
                or (binding.action_type == "bind_role" and (
                    assignment.assignment_kind != "role" or contribution.slot_ref != binding.arguments[2]))):
                errors.append("relation_query_referent_assignment")
        query = next((c for c in context.contribution_slots if c.kind == "open_variable"
                      and c.source_unit_refs == (match.query_source_ref,)
                      and ("query", "query") in c.constraints and ("interrogative", "person") in c.constraints), None)
        assignment = assignments.get(match.query_source_ref)
        if (query is None or assignment is None or assignment.contribution_slot_ref != query.slot_ref
            or assignment.target_action_ref != action.action_ref or assignment.assignment_kind != "role"
            or assignment.target_role_ref != match.query_role):
            errors.append("relation_query_source_assignment")
    return tuple(dict.fromkeys(errors))


def query_projection_errors(context, program, index, *, authority=None) -> tuple[str, ...]:
    """Rematch an exact selected request against current activated form evidence.

    Codecs establish structural identity only. Each exact consumer calls this
    law anew; no compiler expression or candidate match claim is authority.
    """
    from .proposal_context import ProposalContext, licensed_query_projection_slots
    projections = tuple(a for a in program.actions
        if a.action_type == "project_variable" and len(a.arguments) == 2)
    if not projections:
        return ()
    if type(context) is not ProposalContext or type(index) is not ReviewedRoleSchemaIndex:
        return ("query_projection_schema_index_missing",)
    if (not index.identity_is_current
        or index.authority_generation != context.revision_pin.authority_generation):
        return ("query_projection_schema_index_stale",)
    if authority is not None:
        try:
            index.validate_activation(authority)
        except (TypeError, ValueError):
            return ("query_projection_schema_index_stale",)
    try:
        licensed = licensed_query_projection_slots(index, context)
    except BudgetExhausted:
        return ("query_projection_match_budget_exhausted",)
    except (ValueError, KeyError, TypeError, StopIteration):
        return ("query_projection_primitive_evidence_invalid",)
    if len(projections) != 1:
        return ("query_projection_request_bound",)
    action = projections[0]
    slot = context.query_projection(action.arguments[1])
    if slot is None or slot not in licensed:
        return ("query_projection_schema_match_missing",)
    errors = []
    if (program.proposal_context_ref != context.context_ref
        or program.orientation_ref != context.orientation_ref
        or program.revision_pin != context.revision_pin):
        errors.append("query_projection_context_lineage")
    mode = context.mode_slot(program.mode_slot_ref)
    if mode is None or mode.mode != "QUERY":
        errors.append("query_projection_query_mode_required")
    if (program.root_refs != (action.arguments[0],)
        or any(a.action_type not in {"select_context", "select_mode", "select_designation",
            "project_variable", "complete_program"} for a in program.actions)
        or any(a.action_type == "project_variable" and len(a.arguments) != 2 for a in program.actions)
        or program.actions[-1].action_type != "complete_program"):
        errors.append("query_projection_pure_forest_required")
    selected = tuple(a.arguments[0] for a in program.actions if a.action_type == "select_designation")
    if selected != (slot.target_designation_slot_ref,):
        errors.append("query_projection_designation_selection")
    orthographic = set(slot.orthographic_source_unit_refs)
    ownership = {ref: b.contribution_slot_ref for b in slot.bindings
        for ref in b.source_unit_refs if ref not in orthographic}
    sources = tuple(ref for ref in slot.source_unit_refs if ref in ownership)
    if action.source_unit_refs != sources:
        errors.append("query_projection_action_sources")
    assignments = {a.source_unit_ref: a for a in program.source_assignments}
    if len(assignments) != len(program.source_assignments):
        errors.append("query_projection_duplicate_source_assignment")
    for ref, pointer in ownership.items():
        assignment = assignments.get(ref)
        contribution = context.contribution(pointer)
        if (assignment is None or contribution is None
            or assignment.assignment_kind != "projection"
            or assignment.contribution_slot_ref != pointer
            or assignment.target_action_ref != action.action_ref
            or assignment.target_role_ref is not None or assignment.residual_kind is not None
            or assignment.critical != (contribution.kind in {
                "anchor", "predicate", "binder", "reference", "scope", "connector", "literal", "open_variable"})):
            errors.append("query_projection_port_assignment")
    if any(a.target_action_ref == action.action_ref and a.source_unit_ref not in ownership
        for a in program.source_assignments):
        errors.append("query_projection_extra_source_assignment")
    return tuple(dict.fromkeys(errors))
