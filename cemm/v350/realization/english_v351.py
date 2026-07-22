"""Reviewed English realization authority and deterministic Phase-12 realizer.

English wording lives only in this projection layer.  The semantic kernel never switches
on English words.  Rules are content-addressed and must be present in the pinned authority
snapshot before they can realize a Response CSIR decision.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Mapping

from ..csir.authority_v351 import AuthoritySnapshotV351, UseAuthorization
from ..csir.canonical_v351 import exact_fingerprint, semantic_fingerprint
from ..csir.model import CSIRGraph, CSIRNodeKind, CSIRRef, ExactAuthorityPin, TermKind
from ..response.csir_v351 import ResponseAuthorityMapV351, ResponseDecision, ResponseFamily
from ..runtime_abi import RealizationPlanArtifact, SurfaceCandidateArtifact, artifact_ref
from .proof_v351 import (
    ExactRealizationProofBuilder, ExactRealizationTransformStep,
    required_qualification_refs, required_semantic_coverage,
)


@dataclass(frozen=True, slots=True)
class EnglishRealizationRuleV351:
    family: ResponseFamily
    rule_pin: ExactAuthorityPin
    lexical_pins: tuple[ExactAuthorityPin, ...]
    morphology_pin: ExactAuthorityPin
    linearization_pin: ExactAuthorityPin
    mode: str
    prefix_tokens: tuple[str, ...] = ()
    suffix_tokens: tuple[str, ...] = (".",)
    competence_case_pin: ExactAuthorityPin | None = None


@dataclass(frozen=True, slots=True)
class LexicalRealizationBindingV351:
    """Exact output lexicalization for one exact semantic pin."""

    semantic_pin: ExactAuthorityPin
    lexical_pin: ExactAuthorityPin
    surface: str
    lexical_category: str = ""

    def __post_init__(self) -> None:
        if not self.surface.strip():
            raise ValueError("lexical realization binding requires non-empty surface")


@dataclass(frozen=True, slots=True)
class LiteralRealizationBindingV351:
    """Exact language projection for a non-identity literal transformation."""

    literal_type: str
    literal_key: str
    lexical_pin: ExactAuthorityPin
    surface: str

    def __post_init__(self) -> None:
        if not self.literal_type.strip() or not self.literal_key.strip() or not self.surface.strip():
            raise ValueError("literal realization binding requires type, key and surface")


@dataclass(frozen=True, slots=True)
class ApplicationFrameSegmentV351:
    kind: str  # predicate | port
    port_pin: ExactAuthorityPin | None = None

    def __post_init__(self) -> None:
        if self.kind not in {"predicate", "port"}:
            raise ValueError("application realization segment kind must be predicate or port")
        if self.kind == "port" and self.port_pin is None:
            raise ValueError("port realization segment requires exact port pin")
        if self.kind == "predicate" and self.port_pin is not None:
            raise ValueError("predicate realization segment cannot carry port pin")


@dataclass(frozen=True, slots=True)
class ApplicationRealizationFrameV351:
    definition_pin: ExactAuthorityPin
    frame_pin: ExactAuthorityPin
    segments: tuple[ApplicationFrameSegmentV351, ...]

    def __post_init__(self) -> None:
        if not self.segments:
            raise ValueError("application realization frame requires ordered segments")
        ports = tuple(segment.port_pin.key for segment in self.segments if segment.port_pin is not None)
        if len(ports) != len(set(ports)):
            raise ValueError("application realization frame cannot repeat an exact port")
        if sum(segment.kind == "predicate" for segment in self.segments) != 1:
            raise ValueError("application realization frame requires exactly one predicate segment")


@dataclass(frozen=True, slots=True)
class EnglishRealizationPackageV351:
    package_pin: ExactAuthorityPin
    rules: tuple[EnglishRealizationRuleV351, ...]
    use_authorizations: tuple[UseAuthorization, ...] = ()
    lexicalizations: tuple[LexicalRealizationBindingV351, ...] = ()
    literal_bindings: tuple[LiteralRealizationBindingV351, ...] = ()
    application_frames: tuple[ApplicationRealizationFrameV351, ...] = ()
    language_tag: str = "en"

    def __post_init__(self) -> None:
        if not self.language_tag.strip():
            raise ValueError("realization package language tag is required")
        descriptor = self.content_descriptor()
        if (
            self.package_pin.kind != "language_realization_package"
            or self.package_pin.ref != f"language-pack:{self.language_tag}:realization"
            or self.package_pin.revision < 1
            or self.package_pin.content_hash != _hash(descriptor)
        ):
            raise ValueError("English realization package pin does not exactly address package content")

    def content_descriptor(self):
        return _package_descriptor(
            self.language_tag, self.rules, self.use_authorizations,
            self.lexicalizations, self.literal_bindings, self.application_frames,
        )

    @property
    def exact_pins(self) -> tuple[ExactAuthorityPin, ...]:
        values = {self.package_pin.key: self.package_pin}
        for rule in self.rules:
            for pin in (rule.rule_pin, *rule.lexical_pins, rule.morphology_pin, rule.linearization_pin):
                values[pin.key] = pin
            if rule.competence_case_pin is not None:
                values[rule.competence_case_pin.key] = rule.competence_case_pin
        for binding in self.lexicalizations:
            values[binding.lexical_pin.key] = binding.lexical_pin
        for binding in self.literal_bindings:
            values[binding.lexical_pin.key] = binding.lexical_pin
        for frame in self.application_frames:
            values[frame.frame_pin.key] = frame.frame_pin
        return tuple(values[key] for key in sorted(values))

    def validate(self, snapshot: AuthoritySnapshotV351) -> None:
        for pin in self.exact_pins:
            snapshot.require_known_pin(pin)
        expected_auth = {item.authorization_pin.key: item for item in self.use_authorizations}
        observed_auth = {item.authorization_pin.key: item for item in snapshot.use_authorizations}
        missing_auth = set(expected_auth).difference(observed_auth)
        if missing_auth:
            raise ValueError(f"English realization use authorization missing from exact snapshot:{sorted(missing_auth)}")
        for key, expected in expected_auth.items():
            observed = observed_auth[key]
            if (
                observed.target_pin.key != expected.target_pin.key
                or observed.operation != expected.operation
                or observed.decision != expected.decision
                or tuple(observed.context_scopes) != tuple(expected.context_scopes)
                or tuple(observed.permission_scopes) != tuple(expected.permission_scopes)
            ):
                raise ValueError("English realization use authorization payload differs from content-addressed package")
        families = tuple(item.family for item in self.rules)
        if len(families) != len(set(families)):
            raise ValueError("English realization package has duplicate family rule")
        lexical_semantics = tuple(item.semantic_pin.key for item in self.lexicalizations)
        if len(lexical_semantics) != len(set(lexical_semantics)):
            raise ValueError("English output lexicalization must be singular per exact semantic pin")
        literal_keys = tuple((item.literal_type, item.literal_key) for item in self.literal_bindings)
        if len(literal_keys) != len(set(literal_keys)):
            raise ValueError("English literal realization must be singular per typed literal key")
        frame_semantics = tuple(item.definition_pin.key for item in self.application_frames)
        if len(frame_semantics) != len(set(frame_semantics)):
            raise ValueError("English application frame must be singular per exact semantic definition")
        for binding in self.lexicalizations:
            snapshot.require_known_pin(binding.semantic_pin)
            snapshot.require_known_pin(binding.lexical_pin)
        for frame in self.application_frames:
            definition = snapshot.require_definition(frame.definition_pin)
            snapshot.require_known_pin(frame.frame_pin)
            formal = {item.port_pin.key for item in definition.formal_ports}
            for segment in frame.segments:
                if segment.port_pin is not None and segment.port_pin.key not in formal:
                    raise ValueError("English realization frame references a non-formal exact port")

    def require_rule(self, family: ResponseFamily) -> EnglishRealizationRuleV351:
        values = tuple(item for item in self.rules if item.family is family)
        if len(values) != 1:
            raise ValueError(f"exactly one reviewed English realization rule required:{family.value}")
        return values[0]

    def lexical_binding(
        self, semantic_pins: tuple[ExactAuthorityPin, ...],
    ) -> LexicalRealizationBindingV351 | None:
        keys = {pin.key for pin in semantic_pins}
        values = tuple(item for item in self.lexicalizations if item.semantic_pin.key in keys)
        if not values:
            return None
        if len(values) != 1:
            raise ValueError("ambiguous exact English lexicalization for semantic node")
        return values[0]

    def lexical_surface(self, semantic_pins: tuple[ExactAuthorityPin, ...]) -> str | None:
        binding = self.lexical_binding(semantic_pins)
        return None if binding is None else binding.surface

    def literal_binding(self, value) -> LiteralRealizationBindingV351 | None:
        key = (type(value).__name__, repr(value))
        values = tuple(
            item for item in self.literal_bindings
            if (item.literal_type, item.literal_key) == key
        )
        if not values:
            return None
        if len(values) != 1:
            raise ValueError("ambiguous exact English literal realization")
        return values[0]

    def application_frame(self, definition_pin: ExactAuthorityPin) -> ApplicationRealizationFrameV351 | None:
        values = tuple(item for item in self.application_frames if item.definition_pin.key == definition_pin.key)
        if not values:
            return None
        if len(values) != 1:
            raise ValueError("ambiguous exact English application realization frame")
        return values[0]


def _hash(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _pin(kind: str, ref: str, payload, *, revision: int = 1) -> ExactAuthorityPin:
    if revision < 1:
        raise ValueError("exact realization authority revision must be positive")
    return ExactAuthorityPin(kind, "cemm:v351:realization:en", ref, revision, _hash(payload), "global")


def _package_descriptor(language_tag, rules, use_authorizations, lexicalizations, literal_bindings, application_frames):
    return {
        "language_tag": language_tag,
        "rules": tuple(
            (
                item.family.value, item.rule_pin.key, tuple(pin.key for pin in item.lexical_pins),
                item.morphology_pin.key, item.linearization_pin.key, item.mode,
                item.prefix_tokens, item.suffix_tokens,
                None if item.competence_case_pin is None else item.competence_case_pin.key,
            )
            for item in rules
        ),
        "use_authorizations": tuple(
            (item.authorization_pin.key, item.target_pin.key, item.operation, item.decision)
            for item in use_authorizations
        ),
        "lexicalizations": tuple(
            (item.semantic_pin.key, item.lexical_pin.key, item.surface, item.lexical_category)
            for item in lexicalizations
        ),
        "literal_bindings": tuple(
            (item.literal_type, item.literal_key, item.lexical_pin.key, item.surface)
            for item in literal_bindings
        ),
        "application_frames": tuple(
            (
                item.definition_pin.key, item.frame_pin.key,
                tuple((segment.kind, None if segment.port_pin is None else segment.port_pin.key) for segment in item.segments),
            )
            for item in application_frames
        ),
    }


def compile_minimum_english_realization_package() -> EnglishRealizationPackageV351:
    # Fixed tokens here are realization data, never response-policy branches.  Semantically
    # loaded content is inserted only through the mode declared by the exact rule.
    specs = (
        (ResponseFamily.ANSWER_QUERY, "content_fragment", (), (".",)),
        (ResponseFamily.REPORT_STATE, "content_fragment", (), (".",)),
        (ResponseFamily.REPORT_RELATION, "content_fragment", (), (".",)),
        (ResponseFamily.REPORT_EVENT, "content_fragment", (), (".",)),
        (ResponseFamily.REPORT_CAPABILITY, "content_fragment", (), (".",)),
        # English projection only: semantic causality is already represented by exact
        # cause/effect ports in Response CSIR. The connector is content-addressed language data.
        (ResponseFamily.PROVIDE_CAUSAL_EXPLANATION, "causal_explanation", ("because",), (".",)),
        (ResponseFamily.ACKNOWLEDGE_TARGETED_CLAIM, "fixed_discourse", ("Noted",), (".",)),
        (ResponseFamily.REQUEST_CLARIFICATION, "fixed_discourse", ("Could", "you", "clarify"), ("?",)),
        (ResponseFamily.CORRECT_PRIOR_OUTPUT, "content_fragment", ("Actually,",), (".",)),
        (ResponseFamily.QUALIFY_UNCERTAINTY, "fixed_discourse", ("I", "do", "not", "know"), (".",)),
        (ResponseFamily.ASK_LEARNING_QUESTION, "fixed_discourse", ("Could", "you", "explain", "that"), ("?",)),
    )
    package_payload = {"language": "en", "revision": 1, "rules": [(f.value, m, p, s) for f, m, p, s in specs]}
    morphology = _pin("morphology_rule", "realize:en:identity-morphology", (package_payload, "identity-morphology"))
    linearizations = {}
    rules = []
    use_authorizations = []
    for family, mode, prefix, suffix in specs:
        payload = (package_payload, family.value, mode, prefix, suffix)
        rule_pin = _pin("realization_rule", f"realize:en:{family.value}", payload)
        lexical = tuple(
            _pin("realization_lexeme", f"realize:en:lexeme:{family.value}:{i}:{token.casefold()}", (payload, i, token))
            for i, token in enumerate((*prefix, *suffix)) if token.strip()
        )
        lin_key = (mode, suffix)
        linearization = linearizations.get(lin_key)
        if linearization is None:
            linearization = _pin("linearization_rule", f"realize:en:linearize:{_hash(lin_key)[:16]}", (package_payload, lin_key))
            linearizations[lin_key] = linearization
        competence_pin = _pin(
            "competence_case", f"competence:realization:en:{family.value}",
            (payload, "competence", "semantic-preservation"),
        )
        rules.append(EnglishRealizationRuleV351(
            family=family, rule_pin=rule_pin, lexical_pins=lexical or (
                _pin("realization_lexeme", f"realize:en:lexeme:{family.value}:semantic-content", (payload, "semantic-content")),
            ),
            morphology_pin=morphology, linearization_pin=linearization,
            mode=mode, prefix_tokens=prefix, suffix_tokens=suffix,
            competence_case_pin=competence_pin,
        ))
        auth_pin = _pin("use_authorization", f"realize:en:authorization:{family.value}", (payload, "realize", "allow"))
        use_authorizations.append(UseAuthorization(
            authorization_pin=auth_pin, target_pin=rule_pin, operation="realize", decision="allow",
            context_scopes=(), permission_scopes=(),
            evidence_refs=(competence_pin.ref,),
        ))
    literal_bindings = tuple(
        LiteralRealizationBindingV351(
            literal_type="bool", literal_key=repr(value),
            lexical_pin=_pin(
                "realization_lexeme", f"realize:en:literal:bool:{str(value).casefold()}",
                (package_payload, "literal", "bool", repr(value), surface),
            ),
            surface=surface,
        )
        for value, surface in ((True, "Yes"), (False, "No"))
    )
    # Package identity binds the fully expanded rule/projection inventory, not merely a
    # symbolic language name.  This makes later vocabulary/frame extensions exact ABI changes.
    descriptor = _package_descriptor(
        "en", tuple(rules), tuple(use_authorizations), (), literal_bindings, (),
    )
    package_pin = _pin(
        "language_realization_package", "language-pack:en:realization", descriptor,
        revision=1,
    )
    return EnglishRealizationPackageV351(
        package_pin=package_pin, rules=tuple(rules), use_authorizations=tuple(use_authorizations),
        literal_bindings=literal_bindings,
    )


def compile_english_lexicalization_binding(
    semantic_pin: ExactAuthorityPin, surface: str, *, lexical_category: str = "",
) -> LexicalRealizationBindingV351:
    payload = (semantic_pin.key, surface, lexical_category, "en")
    lexical_pin = _pin(
        "realization_lexeme",
        f"realize:en:semantic:{semantic_pin.ref}:{_hash(payload)[:16]}", payload,
    )
    return LexicalRealizationBindingV351(
        semantic_pin=semantic_pin, lexical_pin=lexical_pin, surface=surface,
        lexical_category=lexical_category,
    )


def compile_english_application_frame(
    definition_pin: ExactAuthorityPin, segments: tuple[ApplicationFrameSegmentV351, ...],
) -> ApplicationRealizationFrameV351:
    payload = (
        definition_pin.key,
        tuple((segment.kind, None if segment.port_pin is None else segment.port_pin.key) for segment in segments),
        "en",
    )
    frame_pin = _pin(
        "realization_frame",
        f"realize:en:frame:{definition_pin.ref}:{_hash(payload)[:16]}", payload,
    )
    return ApplicationRealizationFrameV351(definition_pin, frame_pin, segments)


def extend_english_realization_package(
    package: EnglishRealizationPackageV351, *,
    lexicalizations: tuple[LexicalRealizationBindingV351, ...] = (),
    application_frames: tuple[ApplicationRealizationFrameV351, ...] = (),
) -> EnglishRealizationPackageV351:
    """Create a new content-addressed projection bundle with a new exact revision.

    Vocabulary/frame changes advance the package revision and content hash. Activation still
    requires the new exact pins to be published in a new immutable AuthorityGeneration.
    """
    lex = tuple((*package.lexicalizations, *lexicalizations))
    frames = tuple((*package.application_frames, *application_frames))
    descriptor = _package_descriptor(
        package.language_tag, package.rules, package.use_authorizations,
        lex, package.literal_bindings, frames,
    )
    package_pin = _pin(
        "language_realization_package", f"language-pack:{package.language_tag}:realization",
        descriptor, revision=package.package_pin.revision + 1,
    )
    return EnglishRealizationPackageV351(
        package_pin=package_pin, rules=package.rules, use_authorizations=package.use_authorizations,
        lexicalizations=lex, literal_bindings=package.literal_bindings,
        application_frames=frames, language_tag=package.language_tag,
    )


class EnglishCSIRRealizerV351:
    RUNTIME_ABI = "v351"
    SERVICE_KIND = "english_csir_realizer"

    def __init__(
        self,
        *,
        package: EnglishRealizationPackageV351,
        response_authority_map: ResponseAuthorityMapV351,
        session_memory=None,
    ) -> None:
        self.package = package
        self.response_authority_map = response_authority_map
        self.session_memory = session_memory
        self.proofs = ExactRealizationProofBuilder()

    def _content_node(self, decision: ResponseDecision):
        authority = self.response_authority_map.require(decision.family)
        if authority.content_port_pin is None:
            return None
        root_apps = [
            app for app in decision.graph.applications
            if app.predicate_pin.key == authority.definition_pin.key
        ]
        if len(root_apps) != 1:
            return None
        bindings = [
            item for item in decision.graph.bindings_for(root_apps[0].application_ref)
            if item.port_pin.key == authority.content_port_pin.key
        ]
        if len(bindings) != 1 or len(bindings[0].fillers) != 1:
            return None
        return decision.graph.node(bindings[0].fillers[0])

    def _port_node(self, decision: ResponseDecision, port_pin: ExactAuthorityPin | None):
        if port_pin is None:
            return None
        authority = self.response_authority_map.require(decision.family)
        root_apps = [
            app for app in decision.graph.applications
            if app.predicate_pin.key == authority.definition_pin.key
        ]
        if len(root_apps) != 1:
            return None
        bindings = [
            item for item in decision.graph.bindings_for(root_apps[0].application_ref)
            if item.port_pin.key == port_pin.key
        ]
        if len(bindings) != 1 or len(bindings[0].fillers) != 1:
            return None
        return decision.graph.node(bindings[0].fillers[0])

    def _response_wrapper_coverage(self, decision: ResponseDecision) -> set[str]:
        """Coverage contributed by the exact response-family projection rule itself."""
        authority = self.response_authority_map.require(decision.family)
        values: set[str] = {
            f"root:{root.kind.value}:{root.ref}" for root in decision.graph.root_refs
        }
        for app in decision.graph.applications:
            if app.predicate_pin.key != authority.definition_pin.key:
                continue
            values.add(app.application_ref)
            values.update(binding.binding_ref for binding in decision.graph.bindings_for(app.application_ref))
        return values

    def _surface_for_ref(
        self, graph: CSIRGraph, ref: CSIRRef, *, cycle,
        used_lexical: dict | None = None, used_frames: dict | None = None,
        source_bindings: Mapping[str, object] | None = None, covered_semantics: set[str] | None = None,
        used_reference_evidence: set[str] | None = None,
        depth: int = 0, maximum_depth: int = 16,
    ) -> str | None:
        used_lexical = {} if used_lexical is None else used_lexical
        used_frames = {} if used_frames is None else used_frames
        source_bindings = {} if source_bindings is None else source_bindings
        covered_semantics = set() if covered_semantics is None else covered_semantics
        used_reference_evidence = set() if used_reference_evidence is None else used_reference_evidence
        if depth > maximum_depth:
            return None
        node = graph.node(ref)
        if node is None:
            return None
        if ref.kind is CSIRNodeKind.TERM:
            covered_semantics.add(node.term_ref)
            if getattr(node, "term_kind", None) is TermKind.LITERAL:
                value = node.literal_value
                if isinstance(value, bool):
                    literal = self.package.literal_binding(value)
                    if literal is None:
                        return None
                    used_lexical[literal.lexical_pin.key] = literal.lexical_pin
                    return literal.surface
                return str(value)
            identity = str(getattr(node, "identity_ref", None) or "")
            if getattr(node, "term_kind", None) is TermKind.REFERENT:
                if identity and self.session_memory is not None:
                    entry = self.session_memory.reference_surface_entry(
                        cycle.context_ref, cycle.permission_ref, identity, language_tag=(cycle.target_language or "en"),
                    )
                    if entry is not None:
                        used_reference_evidence.add(entry.reference_ref)
                        used_reference_evidence.update(entry.evidence_refs)
                        return entry.surface
                # Never leak internal referent IDs. Fall through to exact semantic lexicalization.
            elif getattr(node, "term_kind", None) is TermKind.OTHER and identity and self.session_memory is not None:
                source_graph = self.session_memory.semantic_graph(
                    cycle.context_ref, cycle.permission_ref, identity,
                )
                binding = source_bindings.get(identity)
                if source_graph is not None and binding is not None:
                    if (
                        getattr(binding, "semantic_fingerprint", "") != semantic_fingerprint(source_graph)
                        or getattr(binding, "exact_fingerprint", "") != exact_fingerprint(source_graph)
                    ):
                        return None
                if source_graph is not None and binding is not None and len(source_graph.root_refs) == 1:
                    surface = self._surface_for_ref(
                        source_graph, source_graph.root_refs[0], cycle=cycle,
                        used_lexical=used_lexical, used_frames=used_frames, source_bindings=source_bindings,
                        covered_semantics=set(), used_reference_evidence=used_reference_evidence,
                        depth=depth + 1, maximum_depth=maximum_depth,
                    )
                    if surface:
                        return surface
            exact_pins = tuple((*getattr(node, "authority_pins", ()), *getattr(node, "type_pins", ())))
            lexical = self.package.lexical_binding(exact_pins)
            if lexical is None:
                return None
            used_lexical[lexical.lexical_pin.key] = lexical.lexical_pin
            return lexical.surface
        if ref.kind is CSIRNodeKind.APPLICATION:
            covered_semantics.add(node.application_ref)
            frame = self.package.application_frame(node.predicate_pin)
            lexical = self.package.lexical_binding((node.predicate_pin,))
            if frame is None or lexical is None:
                return None
            used_frames[frame.frame_pin.key] = frame.frame_pin
            used_lexical[lexical.lexical_pin.key] = lexical.lexical_pin
            predicate = lexical.surface
            parts = []
            for segment in frame.segments:
                if segment.kind == "predicate":
                    parts.append(predicate)
                    continue
                bindings = tuple(
                    item for item in graph.bindings_for(node.application_ref)
                    if item.port_pin.key == segment.port_pin.key
                )
                if len(bindings) != 1 or len(bindings[0].fillers) != 1:
                    return None
                covered_semantics.add(bindings[0].binding_ref)
                surface = self._surface_for_ref(
                    graph, bindings[0].fillers[0], cycle=cycle, used_lexical=used_lexical,
                    used_frames=used_frames, source_bindings=source_bindings,
                    covered_semantics=covered_semantics, used_reference_evidence=used_reference_evidence,
                    depth=depth + 1, maximum_depth=maximum_depth,
                )
                if not surface:
                    return None
                parts.append(surface)
            return " ".join(parts)
        # Coordination/scope require their own exact projection authority.  Do not invent
        # universal conjunction or scope word order in kernel/runtime code.
        return None

    def _surface_for_node(
        self, node, *, cycle, graph: CSIRGraph | None = None,
        used_lexical: dict | None = None, used_frames: dict | None = None,
        source_bindings: Mapping[str, object] | None = None, covered_semantics: set[str] | None = None,
        used_reference_evidence: set[str] | None = None,
    ) -> str | None:
        used_lexical = {} if used_lexical is None else used_lexical
        used_frames = {} if used_frames is None else used_frames
        source_bindings = {} if source_bindings is None else source_bindings
        covered_semantics = set() if covered_semantics is None else covered_semantics
        used_reference_evidence = set() if used_reference_evidence is None else used_reference_evidence
        if node is None:
            return None
        if graph is not None and hasattr(node, "node_ref"):
            return self._surface_for_ref(
                graph, node.node_ref, cycle=cycle, used_lexical=used_lexical, used_frames=used_frames,
                source_bindings=source_bindings, covered_semantics=covered_semantics,
                used_reference_evidence=used_reference_evidence,
            )
        if hasattr(node, "term_ref"):
            covered_semantics.add(node.term_ref)
        if getattr(node, "term_kind", None) is TermKind.LITERAL:
            value = node.literal_value
            if isinstance(value, bool):
                literal = self.package.literal_binding(value)
                if literal is None:
                    return None
                used_lexical[literal.lexical_pin.key] = literal.lexical_pin
                return literal.surface
            return str(value)
        if getattr(node, "term_kind", None) is TermKind.REFERENT:
            identity = str(node.identity_ref or "")
            if identity and self.session_memory is not None:
                entry = self.session_memory.reference_surface_entry(
                    cycle.context_ref, cycle.permission_ref, identity, language_tag=(cycle.target_language or "en"),
                )
                if entry is not None:
                    used_reference_evidence.add(entry.reference_ref)
                    used_reference_evidence.update(entry.evidence_refs)
                    return entry.surface
        lexical = self.package.lexical_binding(
            tuple((*getattr(node, "authority_pins", ()), *getattr(node, "type_pins", ())))
        )
        if lexical is None:
            return None
        used_lexical[lexical.lexical_pin.key] = lexical.lexical_pin
        return lexical.surface

    @staticmethod
    def _join(prefix: tuple[str, ...], content: str | None, suffix: tuple[str, ...]) -> str:
        tokens = [*prefix]
        if content:
            tokens.append(content)
        surface = " ".join(token for token in tokens if token)
        if suffix:
            punct = "".join(suffix)
            if punct and surface:
                surface += punct
        return surface.strip()

    def realize(self, *, cycle, capability, store, effect_store, semantic_capabilities):
        del store, effect_store, semantic_capabilities
        decision = cycle.artifacts.get("response_decision")
        if not isinstance(decision, ResponseDecision):
            raise TypeError("Stage 19 English realizer requires ResponseDecision")
        if decision.family is ResponseFamily.NO_RESPONSE_REQUIRED:
            return {
                "realization_plan": RealizationPlanArtifact(
                    plan_ref=artifact_ref("realization-plan:no-response", decision.decision_ref),
                    selected_candidate_ref="",
                ),
                "surface_candidates": (), "realization_proofs": (),
                "no_response_required": True,
            }
        target_language = cycle.target_language or "en"
        if target_language != self.package.language_tag:
            return {
                "realization_plan": None, "surface_candidates": (), "realization_proofs": (),
                "frontier_refs": (f"frontier:realization:language-package:{target_language}",),
            }
        semantic_authority = cycle.artifacts["semantic_authority_snapshot_v351"]
        if not isinstance(semantic_authority, AuthoritySnapshotV351):
            raise TypeError("Stage 19 requires pinned AuthoritySnapshotV351")
        if (semantic_authority.generation, semantic_authority.authority_fingerprint) != (
            capability.authority_generation, capability.authority_fingerprint,
        ):
            raise ValueError("realizer semantic authority differs from cycle-pinned generation")
        try:
            self.package.validate(semantic_authority)
            # Realization authority is selected-family scoped.  An unrelated inactive
            # response family must not become a global output gate.
            response_authority = self.response_authority_map.validate_family(
                semantic_authority, decision.family
            )
            response_profile = semantic_authority.select_operational_profile(
                response_authority.definition_pin, operation="realize", permission_ref=cycle.permission_ref,
            )
            semantic_authority.select_use_authorizations(
                definition_pin=response_authority.definition_pin, profile_pin=response_profile.profile_pin,
                operation="realize", context_ref=cycle.context_ref, permission_ref=cycle.permission_ref,
            )
            rule = self.package.require_rule(decision.family)
        except Exception as exc:
            return {
                "realization_plan": None, "surface_candidates": (), "realization_proofs": (),
                "frontier_refs": (
                    "frontier:realization:exact-projection-authority-not-active:"
                    + artifact_ref("authority-gap", str(exc)).split(":", 1)[-1],
                ),
            }
        matching_auth = tuple(
            item for item in semantic_authority.use_authorizations
            if item.target_pin.key == rule.rule_pin.key and item.operation == "realize"
            and (not item.context_scopes or cycle.context_ref in item.context_scopes or "global" in item.context_scopes)
            and (not item.permission_scopes or cycle.permission_ref in item.permission_scopes or "global" in item.permission_scopes)
        )
        if any(item.decision.casefold() == "deny" for item in matching_auth) or not any(
            item.decision.casefold() == "allow" for item in matching_auth
        ):
            return {
                "realization_plan": None, "surface_candidates": (), "realization_proofs": (),
                "frontier_refs": ("frontier:realization:exact-use-authorization",),
            }
        content = None
        used_lexical = {}
        used_frames = {}
        used_reference_evidence: set[str] = set()
        covered_semantics = self._response_wrapper_coverage(decision)
        if rule.mode == "content_fragment":
            content = self._surface_for_node(
                self._content_node(decision), cycle=cycle, graph=decision.graph,
                used_lexical=used_lexical, used_frames=used_frames,
                source_bindings={item.semantic_ref: item for item in decision.source_bindings},
                covered_semantics=covered_semantics,
                used_reference_evidence=used_reference_evidence,
            )
            if not content:
                return {
                    "realization_plan": None, "surface_candidates": (), "realization_proofs": (),
                    "frontier_refs": ("frontier:realization:reference-or-lexicalization-gap",),
                }
        elif rule.mode == "causal_explanation":
            authority = self.response_authority_map.require(decision.family)
            cause = self._surface_for_node(
                self._port_node(decision, authority.cause_port_pin), cycle=cycle, graph=decision.graph,
                used_lexical=used_lexical, used_frames=used_frames,
                source_bindings={item.semantic_ref: item for item in decision.source_bindings},
                covered_semantics=covered_semantics, used_reference_evidence=used_reference_evidence,
            )
            effect = self._surface_for_node(
                self._port_node(decision, authority.effect_port_pin), cycle=cycle, graph=decision.graph,
                used_lexical=used_lexical, used_frames=used_frames,
                source_bindings={item.semantic_ref: item for item in decision.source_bindings},
                covered_semantics=covered_semantics, used_reference_evidence=used_reference_evidence,
            )
            if not cause or not effect or len(rule.prefix_tokens) != 1:
                return {
                    "realization_plan": None, "surface_candidates": (), "realization_proofs": (),
                    "frontier_refs": ("frontier:realization:causal-explanation-projection-gap",),
                }
            content = f"{effect} {rule.prefix_tokens[0]} {cause}"
        surface = self._join(() if rule.mode == "causal_explanation" else rule.prefix_tokens, content, rule.suffix_tokens)
        if not surface:
            return {
                "realization_plan": None, "surface_candidates": (), "realization_proofs": (),
                "frontier_refs": ("frontier:realization:empty-surface",),
            }
        candidate_ref = artifact_ref(
            "surface-candidate-v351", decision.decision_ref, target_language, surface,
        )
        coverage = tuple(sorted(covered_semantics))
        qualifications = required_qualification_refs(decision)
        step = ExactRealizationTransformStep(
            step_ref=artifact_ref("realization-step-v351", candidate_ref, rule.rule_pin.key),
            transform_kind=f"english:{rule.mode}",
            input_refs=(decision.decision_ref,), output_refs=(candidate_ref,),
            rule_pins=(
                self.package.package_pin, rule.rule_pin,
                *tuple(used_frames[key] for key in sorted(used_frames)),
            ),
            lexical_pins=tuple({
                pin.key: pin for pin in (*rule.lexical_pins, *tuple(used_lexical.values()))
            }[key] for key in sorted({
                pin.key: pin for pin in (*rule.lexical_pins, *tuple(used_lexical.values()))
            })),
            morphology_pins=(rule.morphology_pin,),
            linearization_pins=(rule.linearization_pin,),
            coverage_refs=coverage,
            preserved_qualification_refs=qualifications,
        )
        proof = self.proofs.build(
            semantic_input=decision, surface_candidate_ref=candidate_ref, surface=surface,
            authority_snapshot=semantic_authority, permission_ref=cycle.permission_ref,
            audience_refs=tuple(cycle.audience_refs), language_tag=target_language,
            steps=(step,), coverage_refs=coverage,
            proof_refs=tuple((*decision.proof_refs, *sorted(used_reference_evidence))),
        )
        candidate = SurfaceCandidateArtifact(
            candidate_ref=candidate_ref, surface=surface, language_tag=target_language,
            proof_ref=proof.proof_ref,
            metadata={
                "response_family": decision.family.value,
                "realization_rule_pin": rule.rule_pin.key,
                "semantic_input_ref": decision.decision_ref,
            },
        )
        plan = RealizationPlanArtifact(
            plan_ref=artifact_ref("realization-plan-v351", candidate_ref, rule.rule_pin.key),
            selected_candidate_ref=candidate_ref,
            novelty=False, risk_refs=(), audit_required=False,
            release_competence=False, unreviewed_transform=False,
            channel_metadata={"language_tag": target_language, "package_pin": self.package.package_pin.key},
        )
        return {
            "realization_plan": plan,
            "surface_candidates": (candidate,),
            "realization_proofs": (proof,),
        }


__all__ = [
    "ApplicationFrameSegmentV351", "ApplicationRealizationFrameV351",
    "EnglishCSIRRealizerV351", "EnglishRealizationPackageV351", "EnglishRealizationRuleV351",
    "LexicalRealizationBindingV351", "LiteralRealizationBindingV351",
    "compile_english_application_frame",
    "compile_english_lexicalization_binding", "compile_minimum_english_realization_package",
    "extend_english_realization_package",
]
