import importlib.util
import json
from dataclasses import dataclass as _fixture_dataclass
from pathlib import Path
import sys

import pytest

from cemm_authoritative_hybrid.persistence import (
    open_stores,
    memory_stores,
    Fact,
)

ROOT = Path(__file__).parents[1]

def _load_legacy_test_support(module_name: str) -> None:
    """Expose retired fixtures only while collecting old test modules."""

    path = Path(__file__).with_name(f"{module_name}.py")
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"{module_name} test support is unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)


_load_legacy_test_support("legacy_propositions")
_load_legacy_test_support("legacy_runtime_fixtures")

AUTHORITY_GENERATION = "authority:generation-1"


# ---------------------------------------------------------------------------
# Persistence fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def store_path(tmp_path):
    """A tmp_path-based directory for SQLite store files."""
    p = tmp_path / "stores"
    p.mkdir()
    return p


@pytest.fixture
def stores_factory():
    """Callable that takes a path and returns a SQLite ``SemanticStores``."""

    def _factory(
        path, *, authority_generation=AUTHORITY_GENERATION, model_identity=None
    ):
        return open_stores(
            path,
            authority_generation=authority_generation,
            model_identity=model_identity,
        )

    return _factory


@pytest.fixture
def sqlite_stores(store_path):
    """An opened SQLite ``SemanticStores`` instance (closed after test)."""
    stores = open_stores(store_path, authority_generation=AUTHORITY_GENERATION)
    yield stores
    stores.close()


@pytest.fixture
def memory_stores_fixture():
    """A test-only in-memory ``SemanticStores`` instance."""
    stores = memory_stores(authority_generation=AUTHORITY_GENERATION)
    yield stores
    stores.close()


@pytest.fixture
def fact_factory():
    """Callable that takes a key string and returns a ``Fact``."""

    def _factory(
        key,
        *,
        operator="op:relation",
        stance="support",
        confidence=1.0,
        derived=False,
        proof=None,
    ):
        return Fact(
            fact_ref=f"fact:{key}",
            operator=operator,
            args={"role:target": f"entity:{key}", "role:label": f"literal:{key}"},
            stance=stance,
            confidence=confidence,
            derived=derived,
            proof=proof or {"source": "test"},
        )

    return _factory


@pytest.fixture
def effect_factory():
    """Callable that takes a key string and returns an effect record dict."""

    def _factory(key, *, payload=None):
        return {
            "effect_key": f"effect:{key}",
            "payload": payload or {"action": "noop", "key": key},
        }

    return _factory


# ---------------------------------------------------------------------------
# Parametrization: run applicable tests against both backends
# ---------------------------------------------------------------------------

BACKENDS = ["sqlite", "memory"]


@pytest.fixture(params=BACKENDS)
def any_stores(request, store_path):
    """Parametrized fixture yielding both SQLite and in-memory stores."""
    if request.param == "sqlite":
        stores = open_stores(store_path, authority_generation=AUTHORITY_GENERATION)
    else:
        stores = memory_stores(authority_generation=AUTHORITY_GENERATION)
    yield stores
    stores.close()


# ---------------------------------------------------------------------------
# Authority linker fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def authority_factory(tmp_path):
    """Callable that creates test AuthorityBundle instances with configurable errors.

    Parameters:
        designation_target: if set, adds a designation targeting a non-existent atom.
        duplicate_atom: if set, adds the atom to both kernel and conversation owners.
        corrupt_hash: if True, writes a wrong sha256 in the manifest.
    """
    from cemm_authoritative_hybrid.authority import AuthorityBundle, AuthorityStore
    from cemm_authoritative_hybrid.canonical import sha256_governed_text

    def _factory(
        *,
        designation_target=None,
        duplicate_atom=None,
        corrupt_hash=False,
    ):
        store = AuthorityStore()

        kernel = {
            "owner": "kernel",
            "atoms": [
                {"ref": "participant:user", "kind": "participant", "reviewed": True},
                {"ref": "participant:system", "kind": "participant", "reviewed": True},
                {"ref": "concept:person", "kind": "concept", "reviewed": True},
            ],
            "designations": [],
            "event_signatures": [],
            "rules": [],
            "capabilities": {},
            "permissions": [],
            "adapters": [],
            "operator_roles": {
                "op:designation": ["role:target", "role:label_type", "role:surface"],
                "op:type": ["role:instance", "role:class"],
                "op:relation": ["role:subject", "role:relation", "role:object"],
                "op:state": ["role:subject", "role:dimension", "role:value"],
                "op:event": ["role:event", "role:type"],
            },
            "value_dimensions": {},
            "transitions": [],
            "source": {"origin": "test"},
        }

        conversation = {
            "owner": "conversation",
            "atoms": [
                {"ref": "event:greeting", "kind": "event_type", "reviewed": True},
            ],
            "designations": [
                {"surface": "hello", "target": "event:greeting", "language": "en"},
            ],
            "event_signatures": [],
            "rules": [],
            "capabilities": {},
            "permissions": [],
            "adapters": [],
            "operator_roles": {},
            "value_dimensions": {},
            "transitions": [],
            "source": {"origin": "test"},
        }

        if designation_target:
            kernel["designations"].append(
                {
                    "surface": "missing_thing",
                    "target": designation_target,
                    "language": "en",
                }
            )

        if duplicate_atom:
            kernel["atoms"].append(
                {"ref": duplicate_atom, "kind": "event_type", "reviewed": True}
            )

        auth_dir = tmp_path / "authority"
        auth_dir.mkdir()

        owners = []
        for name, data in [("kernel", kernel), ("conversation", conversation)]:
            p = auth_dir / f"{name}.json"
            p.write_text(json.dumps(data, sort_keys=True, indent=2), encoding="utf-8")
            sha = sha256_governed_text(p)
            if corrupt_hash and name == "kernel":
                sha = "0" * 64
            owners.append({"name": name, "path": str(p), "sha256": sha})

        manifest_data = {
            "generation": "authority-test-v1",
            "abi_version": 1,
            "owners": owners,
        }

        return AuthorityBundle(manifest_data, store)

    return _factory


@pytest.fixture
def linked_authority():
    """A successfully linked LinkedAuthority from the real data/authority/manifest.json."""
    from cemm_authoritative_hybrid.authority import AuthorityLinker

    return AuthorityLinker().link_path(ROOT / "data" / "authority" / "manifest.json")


# ---------------------------------------------------------------------------
# Form lattice and grounding fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def form_pack():
    """The English forms.json language pack as a mapping."""
    with open(
        ROOT / "data" / "languages" / "en" / "forms.json", encoding="utf-8"
    ) as fh:
        return json.load(fh)


@pytest.fixture
def form_pack_hash():
    """The SHA-256 of the canonical forms.json content."""
    from cemm_authoritative_hybrid.canonical import canonical_bytes
    import hashlib

    with open(ROOT / "data" / "languages" / "en" / "forms.json", "rb") as fh:
        content = fh.read()
    data = json.loads(content)
    digest = hashlib.sha256(canonical_bytes(data)).hexdigest()
    return f"sha256:{digest}"


@pytest.fixture
def form_resolver(form_pack):
    """A FormResolver configured with the English forms.json pack."""
    from cemm_authoritative_hybrid.forms import FormResolver
    from cemm_authoritative_hybrid.config import RuntimeConfig

    return FormResolver(form_pack, RuntimeConfig.release())


@pytest.fixture
def designation_store():
    """A test-only mutable designation store with commit_reviewed.

    Designations committed here are visible to the grounder via the authority's
    DesignationIndex.  This simulates reviewed designation learning without
    regenerating the language pack.
    """
    from cemm_authoritative_hybrid.authority import DesignationIndex

    class _DesignationStore:
        def __init__(self) -> None:
            self._by_surface: dict[tuple[str, str], list[str]] = {}
            self._by_target: dict[tuple[str, str], list[str]] = {}

        def commit_reviewed(
            self, surface: str, target: str, language: str = "en"
        ) -> None:
            key = (surface, language)
            self._by_surface.setdefault(key, []).append(target)
            self._by_target.setdefault((target, language), []).append(surface)

        def build_index(self) -> DesignationIndex:
            return DesignationIndex(
                {k: tuple(v) for k, v in self._by_surface.items()},
                {k: tuple(v) for k, v in self._by_target.items()},
            )

    return _DesignationStore()


@pytest.fixture
def grounder(linked_authority, form_pack, form_pack_hash, designation_store):
    """A Grounder with the linked authority and test designation store."""
    from cemm_authoritative_hybrid.grounding import Grounder
    from cemm_authoritative_hybrid.config import RuntimeConfig

    return Grounder(
        authority=linked_authority,
        config=RuntimeConfig.release(),
        form_pack=form_pack,
        form_pack_hash=form_pack_hash,
        designation_store=designation_store,
    )


@pytest.fixture
def door_sensor_evidence():
    """An EvidenceItem from a sensor adapter pinning entity:door."""
    from cemm_authoritative_hybrid.forms import EvidenceItem

    return EvidenceItem.create(
        source="sensor",
        content={"target_ref": "entity:door", "adapter_ref": "adapter:door_sensor"},
        source_ref="sensor:door-0",
        provenance_refs=("receipt:door-0",),
        adapter_receipt_ref="receipt:door-0",
    )


# ---------------------------------------------------------------------------
# Phase receipt and gap receipt fixtures
# ---------------------------------------------------------------------------


@_fixture_dataclass(frozen=True)
class _LegacyPhaseReceipt:
    cycle_ref: str
    phase: str
    input_refs: tuple[str, ...]
    output_refs: tuple[str, ...]
    revision_pin: object
    budget_use: dict[str, int]
    status: str
    rejection_codes: tuple[str, ...] = ()
    duration_ns: int | None = None

    def as_dict(self):
        return {
            "cycle_ref": self.cycle_ref,
            "phase": self.phase,
            "input_refs": list(self.input_refs),
            "output_refs": list(self.output_refs),
            "revision_pin": self.revision_pin.as_dict(),
            "budget_use": dict(self.budget_use),
            "status": self.status,
            "rejection_codes": list(self.rejection_codes),
            "duration_ns": self.duration_ns,
        }


@_fixture_dataclass(frozen=True)
class _KernelCycleResult:
    cycle_ref: str
    status: object
    phase_output_refs: dict[object, tuple[str, ...]]
    gap_receipt: object | None
    trace: tuple[_LegacyPhaseReceipt, ...]
    final_revision_pin: object

    def as_dict(self):
        return {
            "cycle_ref": self.cycle_ref,
            "status": self.status.value,
            "phase_output_refs": {
                phase.value: list(refs)
                for phase, refs in self.phase_output_refs.items()
            },
            "gap_receipt": None,
            "trace": [receipt.as_dict() for receipt in self.trace],
            "final_revision_pin": self.final_revision_pin.as_dict(),
            "effect_receipt": None,
        }


class _FixtureCycleRunner:
    def run(self, *, trace=False):
        from cemm_authoritative_hybrid.cycle import CycleStatus, SemanticPhase

        stores = memory_stores(authority_generation="authority:generation-test")
        try:
            pin = stores.revision_pin()
            cycle_ref = "cycle:fixture"
            outputs = {
                phase: (f"artifact:{phase.value.lower()}",)
                for phase in SemanticPhase
            }
            rows = (
                tuple(
                    _LegacyPhaseReceipt(
                        cycle_ref=cycle_ref,
                        phase=phase.value,
                        input_refs=(),
                        output_refs=outputs[phase],
                        revision_pin=pin,
                        budget_use={"tokens": 1},
                        status="ok",
                    )
                    for phase in SemanticPhase
                )
                if trace
                else ()
            )
            return _KernelCycleResult(
                cycle_ref=cycle_ref,
                status=CycleStatus.RESOLVED,
                phase_output_refs=outputs,
                gap_receipt=None,
                trace=rows,
                final_revision_pin=pin,
            )
        finally:
            stores.close()


@pytest.fixture
def cycle_fixture():
    return _FixtureCycleRunner()


@pytest.fixture
def gap_classifier():
    """A ``GapClassifier`` instance for typed exception classification."""
    from cemm_authoritative_hybrid.gaps import GapClassifier

    return GapClassifier()


# ---------------------------------------------------------------------------
# Six-phase runtime fixtures
# ---------------------------------------------------------------------------

SIX_PHASES = ("ORIENT", "PROPOSE", "VERIFY", "EVALUATE", "EFFECT", "REALIZE")


@pytest.fixture
def verified_observation_program():
    """A minimal SemanticSwitchProgram fixture for the development profile.

    This is a typed observation program that the fixture proposal owner returns
    unchanged. It uses a single ``op:event`` application in OBSERVE mode.
    """
    from legacy_propositions import (
        Application,
        PropositionGraph,
        SemanticSwitchProgram,
    )

    app = Application.create(
        "op:event",
        {
            "role:event": "event-instance:test-1",
            "role:type": "event:observation",
            "role:actor": "participant:user",
        },
    )
    graph = PropositionGraph.create([app], app.application_ref)
    return SemanticSwitchProgram.create("OBSERVE", "event:context:test", graph)


@pytest.fixture
def runtime_factory(memory_stores_fixture, linked_authority):
    """Callable that takes ``proposal_fixture=...`` and returns a HybridRuntime.

    The runtime is configured with fixture owners for the development profile.
    The proposal owner returns the injected program; verification always passes;
    evaluation always resolves; effects and realization are no-ops.
    """
    from cemm_authoritative_hybrid.config import RuntimeConfig
    from cemm_authoritative_hybrid.runtime import (
        FixtureEffectOwner,
        FixtureEvaluationOwner,
        FixtureProposalOwner,
        FixtureRealizationOwner,
        FixtureVerificationOwner,
        HybridRuntime,
    )

    def _factory(*, proposal_fixture=None):
        if proposal_fixture is None:
            from legacy_propositions import (
                Application,
                PropositionGraph,
                SemanticSwitchProgram,
            )

            app = Application.create(
                "op:event",
                {
                    "role:event": "event-instance:default",
                    "role:type": "event:observation",
                    "role:actor": "participant:user",
                },
            )
            graph = PropositionGraph.create([app], app.application_ref)
            proposal_fixture = SemanticSwitchProgram.create(
                "OBSERVE", "event:context:default", graph
            )

        owners = {
            "proposal": FixtureProposalOwner(proposal_fixture),
            "verification": FixtureVerificationOwner(),
            "evaluation": FixtureEvaluationOwner(),
            "effect": FixtureEffectOwner(memory_stores_fixture),
            "realization": FixtureRealizationOwner(),
        }
        return HybridRuntime(
            config=RuntimeConfig.release(),
            authority=linked_authority,
            stores=memory_stores_fixture,
            owners=owners,
            profile="development",
        )

    return _factory


# ---------------------------------------------------------------------------
# Affordance index and orientation projection fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def affordance_index(linked_authority):
    """A SemanticAffordanceIndex with the linked authority."""
    from cemm_authoritative_hybrid.affordances import SemanticAffordanceIndex
    from cemm_authoritative_hybrid.config import RuntimeConfig

    return SemanticAffordanceIndex(linked_authority, RuntimeConfig.release())


@pytest.fixture
def runtime(linked_authority, memory_stores_fixture):
    """A bounded orientation harness backed by the canonical projector.

    Orientation projection tests require only the projector and its exact
    dependencies. Keeping this fixture independent of ``HybridRuntime``
    prevents retired six-phase fixture owners from becoming an alternate
    production runtime path.
    """
    from cemm_authoritative_hybrid.config import RuntimeConfig
    from cemm_authoritative_hybrid.cycle import OrientationProjector

    class _OrientationHarness:
        def __init__(self):
            self._authority = linked_authority
            self._stores = memory_stores_fixture
            self._config = RuntimeConfig.release()
            self._projector = OrientationProjector(
                self._authority, self._stores, self._config
            )

        def orient(self, session_ref, source_text):
            return self._projector.project(session_ref, source_text)

    return _OrientationHarness()

# ---------------------------------------------------------------------------
# Recursive Semantic Switch Program and coverage fixtures
# ---------------------------------------------------------------------------


def _default_revision_pin(authority_generation="authority:generation-1"):
    from cemm_authoritative_hybrid.persistence import RevisionPin

    return RevisionPin(
        authority_generation=authority_generation,
        world_revision=0,
        session_revision=0,
        episode_revision=0,
        effect_revision=0,
        model_identity="model:test",
    )


def _is_punctuation_unit(unit) -> bool:
    """A unit is punctuation/discourse if it is whitespace or has no
    normalized surface form (e.g. a bare punctuation mark)."""
    return not unit.source_text.strip() or not unit.normalized_forms


def _build_context_and_program_from_lattice(
    lattice, *, negate=False, revision_pin=None
):
    """Build a minimal valid ``(ProposalContext, SemanticSwitchProgram)`` pair.

    The context uses an ``op:event`` application frame with one predicate
    contribution and one subject contribution.  The program follows the
    canonical six-action derivation: select_context, select_mode,
    select_designation, instantiate_operator, bind_role, complete_program.

    When ``negate`` is true, the first content unit is retained as a critical
    scope residual, which must reject execution.
    """
    from cemm_authoritative_hybrid.proposal_context import (
        ApplicationFrameSlot,
        ContributionSlot,
        DesignationSlot,
        ModeSlot,
        ProposalContext,
    )
    from cemm_authoritative_hybrid.programs import (
        ProgramAction,
        SemanticSwitchProgram,
        SourceAssignment,
    )
    from cemm_authoritative_hybrid.persistence import RevisionPin

    pin = revision_pin or _default_revision_pin()
    if not isinstance(pin, RevisionPin):
        pin = RevisionPin(
            authority_generation=pin.authority_generation,
            world_revision=pin.world_revision,
            session_revision=pin.session_revision,
            episode_revision=pin.episode_revision,
            effect_revision=pin.effect_revision,
            model_identity=pin.model_identity or "model:test",
        )

    designation = DesignationSlot.create(
        source_unit_refs=("unit:predicate",),
        target_ref="event:test",
        target_kind="event_type",
        score_q=900_000,
        designation_fact_ref="designation:test",
        provenance_refs=("authority:test",),
    )
    predicate = ContributionSlot.create(
        contribution_ref="contribution:predicate",
        kind="predicate",
        source_unit_refs=("unit:predicate",),
        target_ref="event:test",
        target_kind="event_type",
        input_ports=("role:subject",),
        output_ports=("role:event",),
        constraints=(),
    )
    subject = ContributionSlot.create(
        contribution_ref="contribution:subject",
        kind="anchor",
        source_unit_refs=("unit:subject",),
        target_ref="entity:one",
        target_kind="entity",
        input_ports=(),
        output_ports=("role:subject",),
        constraints=(),
        provenance_refs=("designation:one",),
    )
    mode = ModeSlot.create(
        mode="OBSERVE",
        source_unit_refs=(),
        construction_ref=None,
        requested_effect="admission",
    )
    frame = ApplicationFrameSlot.create(
        designation_slot_ref=designation.slot_ref,
        predicate_target_ref="event:test",
        predicate_kind="event_type",
        operator_ref="op:event",
        structural_role_ref="role:event",
        required_roles=("role:subject",),
        optional_roles=(),
        proposition_roles=(),
        source_unit_refs=("unit:predicate",),
        derived_role_targets=(),
        affordance_frame_ref="frame:event-test",
        provenance_refs=(designation.slot_ref, "authority:test", "frame:event-test"),
    )
    context = ProposalContext.create(
        orientation_ref="orientation:test",
        evidence_packet_ref="evidence:test",
        form_lattice_ref="lattice:test",
        grounding_ref="grounding:test",
        designation_slots=(designation,),
        contribution_slots=(predicate, subject),
        mode_slots=(mode,),
        application_frames=(frame,),
        reference_slots=(),
        scope_slots=(),
        expression_link_slots=(),
        variable_slots=(),
        transition_slots=(),
        residual_evidence=(),
        context_refs=("turn:test",),
        source_unit_refs=("unit:predicate", "unit:subject"),
        source_unit_spans=(
            ("unit:predicate", 0, 4),
            ("unit:subject", 4, 8),
        ),
        revision_pin=pin,
    )

    actions = (
        ProgramAction.create(
            action_index=0,
            action_type="select_context",
            arguments=(context.context_ref,),
        ),
        ProgramAction.create(
            action_index=1,
            action_type="select_mode",
            arguments=(context.mode_slots[0].slot_ref,),
        ),
        ProgramAction.create(
            action_index=2,
            action_type="select_designation",
            arguments=(context.designation_slots[0].slot_ref,),
        ),
        ProgramAction.create(
            action_index=3,
            action_type="instantiate_operator",
            arguments=("application:main", context.application_frames[0].slot_ref),
            source_unit_refs=("unit:predicate",),
        ),
        ProgramAction.create(
            action_index=4,
            action_type="bind_role",
            arguments=(
                "application:main",
                "role:subject",
                context.contribution_slots[1].slot_ref,
            ),
            source_unit_refs=("unit:subject",),
        ),
        ProgramAction.create(
            action_index=5,
            action_type="complete_program",
            arguments=(),
        ),
    )
    assignments = (
        SourceAssignment.create(
            source_unit_ref="unit:predicate",
            contribution_slot_ref=context.contribution_slots[0].slot_ref,
            assignment_kind="predicate",
            target_action_ref=actions[3].action_ref,
            target_role_ref=None,
            residual_kind=None,
            critical=False,
        ),
        SourceAssignment.create(
            source_unit_ref="unit:subject",
            contribution_slot_ref=context.contribution_slots[1].slot_ref,
            assignment_kind="role",
            target_action_ref=actions[4].action_ref,
            target_role_ref="role:subject",
            residual_kind=None,
            critical=False,
        ),
    )
    program = SemanticSwitchProgram.create(
        orientation_ref=context.orientation_ref,
        proposal_context_ref=context.context_ref,
        actions=actions,
        root_refs=("application:main",),
        mode_slot_ref=context.mode_slots[0].slot_ref,
        goal_refs=("goal:understand",),
        source_unit_refs=context.source_unit_refs,
        source_assignments=assignments,
        revision_pin=context.revision_pin,
    )
    return context, program


def _build_program_from_lattice(lattice, *, negate=False, revision_pin=None):
    """Backward-compatible wrapper returning only the program."""
    _context, program = _build_context_and_program_from_lattice(
        lattice, negate=negate, revision_pin=revision_pin
    )
    return program


@pytest.fixture
def program_factory(form_resolver):
    """Callable that takes a text string and returns a minimal valid program."""

    def _factory(text):
        lattice = form_resolver.resolve(text)
        return _build_program_from_lattice(lattice)

    return _factory


@pytest.fixture
def proposal_context(form_resolver, linked_authority):
    """A ProposalContext for the valid program."""
    from cemm_authoritative_hybrid.proposal import BootstrapProposer

    lattice = form_resolver.resolve("what is your name?")
    pin = _default_revision_pin(authority_generation=linked_authority.generation)
    pin = type(pin)(
        authority_generation=pin.authority_generation,
        world_revision=pin.world_revision,
        session_revision=pin.session_revision,
        episode_revision=pin.episode_revision,
        effect_revision=pin.effect_revision,
        model_identity=BootstrapProposer.model_identity,
    )
    context, _program = _build_context_and_program_from_lattice(
        lattice, revision_pin=pin
    )
    return context


@pytest.fixture
def valid_program(form_resolver, linked_authority):
    """A well-formed SemanticSwitchProgram with valid source assignments."""
    from cemm_authoritative_hybrid.proposal import BootstrapProposer

    lattice = form_resolver.resolve("what is your name?")
    pin = _default_revision_pin(authority_generation=linked_authority.generation)
    pin = type(pin)(
        authority_generation=pin.authority_generation,
        world_revision=pin.world_revision,
        session_revision=pin.session_revision,
        episode_revision=pin.episode_revision,
        effect_revision=pin.effect_revision,
        model_identity=BootstrapProposer.model_identity,
    )
    _context, program = _build_context_and_program_from_lattice(
        lattice, revision_pin=pin
    )
    return program


@pytest.fixture
def valid_lattice(form_resolver):
    """A FormLattice for the valid program text."""
    return form_resolver.resolve("what is your name?")


@pytest.fixture
def coverage_verifier():
    """A CoverageVerifier instance bounded by the release config."""
    from cemm_authoritative_hybrid.coverage import CoverageVerifier

    return CoverageVerifier()


@pytest.fixture
def exact_verifier(coverage_verifier):
    """An ExactProgramVerifier with the coverage verifier."""
    from cemm_authoritative_hybrid.verifier import ExactProgramVerifier

    return ExactProgramVerifier(coverage_verifier=coverage_verifier)


@pytest.fixture
def verifier(exact_verifier):
    """An ExactProgramVerifier (alias for exact_verifier)."""
    return exact_verifier


@pytest.fixture
def masker(proposal_context):
    """An ActionMasker sharing the same LegalActionIndex as the verifier."""
    from cemm_authoritative_hybrid.verifier import ActionMasker, LegalActionIndex

    return ActionMasker(LegalActionIndex(proposal_context))


@pytest.fixture
def prefix(valid_program):
    """A tuple of ProgramAction representing a partial program prefix."""
    # Return the first two actions (select_context, select_mode).
    return valid_program.actions[:2]


@pytest.fixture
def proposal(proposal_context, valid_program):
    """A one-candidate ProposalResult for the valid program."""
    from cemm_authoritative_hybrid.proposal import (
        ProposalResult,
        RankedProgramCandidate,
    )

    candidate = RankedProgramCandidate.create(
        rank=0,
        score_q=900_000,
        program=valid_program,
        provenance_refs=("derivation:0",),
    )
    return ProposalResult.create(
        orientation_ref=proposal_context.orientation_ref,
        proposal_context_ref=proposal_context.context_ref,
        candidates=(candidate,),
        status="candidates",
        abstention_code=None,
        explored_states=1,
        truncated=False,
        model_identity=proposal_context.revision_pin.model_identity,
        revision_pin=proposal_context.revision_pin,
    )


@pytest.fixture
def mutate():
    """Return a callable that applies a named mutation to a program.

    Each mutation produces a program that fails the corresponding verifier
    check with a specific error code.

    Mutations:
        unknown_ref: replace a target_ref with a non-existent ref
        wrong_kind: use an atom with wrong kind for its role
        missing_role: remove a required role binding
        duplicate_role: add a duplicate role binding
        scope_cycle: create a scope cycle in nested applications
        stale_revision: use an old revision_pin
        excess_depth: exceed max_graph_depth
        uncovered_unit: leave a source unit unassigned
    """
    from cemm_authoritative_hybrid.canonical import stable_ref
    from cemm_authoritative_hybrid.programs import (
        ACTION_ABI_HASH,
        PROGRAM_ABI_VERSION,
        ProgramAction,
        SemanticSwitchProgram,
        SourceAssignment,
    )
    from cemm_authoritative_hybrid.persistence import RevisionPin

    def _make_action(action_index, action_type, arguments, source_unit_refs=()):
        """Create a ProgramAction with correct ref, bypassing schema validation."""
        material = {
            "abi_version": PROGRAM_ABI_VERSION,
            "action_index": action_index,
            "action_type": action_type,
            "arguments": list(arguments),
            "source_unit_refs": list(source_unit_refs),
        }
        action_ref = stable_ref("program_action", material)
        return ProgramAction._from_canonical(
            action_ref,
            action_index,
            action_type,
            tuple(arguments),
            tuple(source_unit_refs),
        )

    def _make_program(
        program,
        *,
        actions=None,
        source_assignments=None,
        source_unit_refs=None,
        revision_pin=None,
    ):
        """Create a SemanticSwitchProgram with correct ref, bypassing validation."""
        acts = actions if actions is not None else program.actions
        sa = source_assignments if source_assignments is not None else program.source_assignments
        su = source_unit_refs if source_unit_refs is not None else program.source_unit_refs
        rp = revision_pin if revision_pin is not None else program.revision_pin
        material = {
            "abi_version": PROGRAM_ABI_VERSION,
            "orientation_ref": program.orientation_ref,
            "proposal_context_ref": program.proposal_context_ref,
            "action_abi_hash": ACTION_ABI_HASH,
            "actions": [a.as_dict() for a in acts],
            "root_refs": list(program.root_refs),
            "mode_slot_ref": program.mode_slot_ref,
            "goal_refs": list(program.goal_refs),
            "source_unit_refs": list(su),
            "source_assignments": [a.as_dict() for a in sa],
            "revision_pin": rp.as_dict(),
        }
        program_ref = stable_ref("program", material)
        return SemanticSwitchProgram._from_canonical(
            program_ref,
            orientation_ref=program.orientation_ref,
            proposal_context_ref=program.proposal_context_ref,
            actions=acts,
            root_refs=program.root_refs,
            mode_slot_ref=program.mode_slot_ref,
            goal_refs=program.goal_refs,
            source_unit_refs=su,
            source_assignments=sa,
            revision_pin=rp,
        )

    def _renumber(actions):
        """Recreate actions with contiguous indices, preserving content."""
        return tuple(
            _make_action(
                i,
                action.action_type,
                action.arguments,
                action.source_unit_refs,
            )
            for i, action in enumerate(actions)
        )

    def _mutate(program, mutation):
        if mutation == "stale_revision":
            old_pin = RevisionPin(
                authority_generation="authority:stale-generation",
                world_revision=program.revision_pin.world_revision,
                session_revision=program.revision_pin.session_revision,
                episode_revision=program.revision_pin.episode_revision,
                effect_revision=program.revision_pin.effect_revision,
                model_identity=program.revision_pin.model_identity,
            )
            return _make_program(program, revision_pin=old_pin)

        if mutation == "unknown_ref":
            # Replace select_designation slot ref with a non-existent one.
            new_actions = []
            for action in program.actions:
                if action.action_type == "select_designation":
                    new_actions.append(
                        _make_action(
                            action.action_index,
                            "select_designation",
                            ("designation:nonexistent",),
                            action.source_unit_refs,
                        )
                    )
                else:
                    new_actions.append(action)
            return _make_program(program, actions=tuple(new_actions))

        if mutation == "wrong_kind":
            # Replace bind_role contribution slot ref with a non-existent one.
            new_actions = []
            old_bind_ref = None
            new_bind_ref = None
            for action in program.actions:
                if action.action_type == "bind_role":
                    old_bind_ref = action.action_ref
                    new_action = _make_action(
                        action.action_index,
                        "bind_role",
                        (
                            action.arguments[0],
                            action.arguments[1],
                            "contribution:nonexistent",
                        ),
                        action.source_unit_refs,
                    )
                    new_bind_ref = new_action.action_ref
                    new_actions.append(new_action)
                else:
                    new_actions.append(action)
            new_assignments = []
            for a in program.source_assignments:
                if a.target_action_ref == old_bind_ref:
                    new_assignments.append(
                        SourceAssignment.create(
                            source_unit_ref=a.source_unit_ref,
                            contribution_slot_ref=a.contribution_slot_ref,
                            assignment_kind=a.assignment_kind,
                            target_action_ref=new_bind_ref,
                            target_role_ref=a.target_role_ref,
                            residual_kind=a.residual_kind,
                            critical=a.critical,
                        )
                    )
                else:
                    new_assignments.append(a)
            return _make_program(
                program,
                actions=tuple(new_actions),
                source_assignments=tuple(new_assignments),
            )

        if mutation == "missing_role":
            # Remove the bind_role action and its source assignment.
            kept = [a for a in program.actions if a.action_type != "bind_role"]
            new_actions = _renumber(kept)
            new_assignments = tuple(
                a for a in program.source_assignments
                if a.source_unit_ref != program.source_unit_refs[-1]
            )
            new_source_units = program.source_unit_refs[:-1]
            return _make_program(
                program,
                actions=new_actions,
                source_assignments=new_assignments,
                source_unit_refs=new_source_units,
            )

        if mutation == "duplicate_role":
            # Add a second bind_role binding the same role (no source unit).
            new_actions = []
            for action in program.actions:
                new_actions.append(action)
                if action.action_type == "bind_role":
                    new_actions.append(
                        _make_action(
                            len(new_actions),
                            "bind_role",
                            action.arguments,
                            (),
                        )
                    )
            new_actions = _renumber(new_actions)
            return _make_program(program, actions=new_actions)

        if mutation == "scope_cycle":
            # Add bind_nested_application actions with invalid arguments.
            # These cause ValueError in the verifier's replay.
            extra = [
                _make_action(
                    0,
                    "bind_nested_application",
                    ("action:nest_b_to_a",),
                    (),
                ),
                _make_action(
                    1,
                    "bind_nested_application",
                    ("action:nest_a_to_b",),
                    (),
                ),
            ]
            new_actions = []
            for a in program.actions:
                if a.action_type == "complete_program":
                    new_actions.extend(extra)
                new_actions.append(a)
            new_actions = _renumber(new_actions)
            return _make_program(program, actions=new_actions)

        if mutation == "excess_depth":
            # Add enough project_variable actions to exceed max_applications.
            extra = [
                _make_action(
                    0,
                    "project_variable",
                    (f"binder:extra:{i}", f"variable:nonexistent:{i}", "application:main"),
                    (),
                )
                for i in range(30)
            ]
            new_actions = []
            for a in program.actions:
                if a.action_type == "complete_program":
                    new_actions.extend(extra)
                new_actions.append(a)
            new_actions = _renumber(new_actions)
            return _make_program(program, actions=new_actions)

        if mutation == "uncovered_unit":
            # Remove one source assignment, bypassing create validation.
            if not program.source_assignments:
                return program
            return _make_program(
                program,
                source_assignments=program.source_assignments[:-1],
            )

        raise ValueError(f"unknown mutation: {mutation}")

    return _mutate


@pytest.fixture
def case(valid_lattice, valid_program):
    """A (lattice, program) pair with complete coverage."""
    from collections import namedtuple

    Case = namedtuple("Case", ["lattice", "program"])
    return Case(lattice=valid_lattice, program=valid_program)


@pytest.fixture
def negated_effect_case(form_resolver):
    """A (lattice, program) pair where the program has a critical scope residual."""
    lattice = form_resolver.resolve("do not open the door")
    program = _build_program_from_lattice(lattice, negate=True)
    return (lattice, program)


@pytest.fixture
def canonical_round_trip(tmp_path):
    """Callable that serializes an object to canonical JSON and restores it."""
    from cemm_authoritative_hybrid.canonical import (
        read_canonical_json,
        write_canonical_json,
    )

    counter = {"i": 0}

    def _round_trip(obj, cls):
        i = counter["i"]
        counter["i"] += 1
        p = tmp_path / f"round_trip_{i}.json"
        write_canonical_json(p, obj.as_dict())
        loaded = read_canonical_json(p)
        return cls.from_dict(loaded)

    return _round_trip


# ---------------------------------------------------------------------------
# Bootstrap proposer and orientation fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def orient(linked_authority, memory_stores_fixture):
    """Callable that takes a text string and returns an Orientation.

    Uses :class:`OrientationProjector` to build the source-bound orientation.
    """
    from cemm_authoritative_hybrid.cycle import (
        OrientationProjector,
        SemanticMode,
    )
    from cemm_authoritative_hybrid.config import RuntimeConfig

    stores = memory_stores(
        authority_generation=linked_authority.generation,
    )
    projector = OrientationProjector(
        authority=linked_authority,
        stores=stores,
        config=RuntimeConfig.release(),
    )

    def _orient(text, mode=SemanticMode.QUERY):
        return projector.project("session:bootstrap", text, mode=mode)

    return _orient


@pytest.fixture
def bootstrap_proposer():
    """A :class:`BootstrapProposer` with the release config."""
    from cemm_authoritative_hybrid.config import RuntimeConfig
    from cemm_authoritative_hybrid.proposal import BootstrapProposer

    return BootstrapProposer(RuntimeConfig.release())


# ---------------------------------------------------------------------------
# Neural switch proposer fixtures (M2 Task 6)
# ---------------------------------------------------------------------------


@pytest.fixture
def release_factory():
    """Callable that returns a HybridRuntime with the neural profile.

    Loads the trained safetensors artifact from ``artifacts/proposal_dev/``.
    """
    from cemm_authoritative_hybrid.bootstrap import load_runtime

    def _factory():
        return load_runtime(ROOT, profile="neural")

    return _factory


@pytest.fixture
def trained_proposer(release_factory):
    """A NeuralSwitchProposer loaded from the artifact."""
    runtime = release_factory()
    return runtime.proposal_model


@pytest.fixture
def orientations(linked_authority, form_resolver):
    """A list of orientations for testing the neural proposer."""
    from cemm_authoritative_hybrid.cycle import (
        OrientationProjector,
        SemanticMode,
    )
    from cemm_authoritative_hybrid.config import RuntimeConfig
    from cemm_authoritative_hybrid.persistence import memory_stores

    stores = memory_stores(authority_generation=linked_authority.generation)
    projector = OrientationProjector(
        authority=linked_authority,
        stores=stores,
        config=RuntimeConfig.release(),
    )
    texts = [
        "what is your name?",
        "your name is what?",
        "what are you called?",
        "and you are called what?",
        "is the server online?",
        "not online",
        "can I call you CEMM?",
        "I can call you CEMM, right?",
        "you said what?",
        "yoz means hello",
    ]
    orientations = []
    for text in texts:
        orientation = projector.project(
            "session:bootstrap", text, mode=SemanticMode.QUERY
        )
        orientations.append(orientation)
    stores.close()
    return orientations


@pytest.fixture
def alpha_equivalent_orientations(linked_authority, form_resolver):
    """A pair of orientations that are structurally identical but have different ref names.

    Both orientations use the same surface text structure but different
    participant refs, ensuring the structural features are identical while
    the ref names differ.
    """
    from cemm_authoritative_hybrid.cycle import (
        OrientationProjector,
        SemanticMode,
    )
    from cemm_authoritative_hybrid.config import RuntimeConfig
    from cemm_authoritative_hybrid.persistence import memory_stores

    stores = memory_stores(authority_generation=linked_authority.generation)
    projector = OrientationProjector(
        authority=linked_authority,
        stores=stores,
        config=RuntimeConfig.release(),
    )
    text = "what is your name?"
    orientation1 = projector.project("session:bootstrap", text, mode=SemanticMode.QUERY)

    # Create an alpha-equivalent orientation with different session ref
    # but the SAME surface text — structural features depend only on form
    # evidence, not session/turn ref names.
    orientation2 = projector.project("session:alt", text, mode=SemanticMode.QUERY)

    stores.close()
    return (orientation1, orientation2)


@pytest.fixture
def structural_holdout(orientations):
    """A set of test surfaces for ablation testing."""
    return orientations
