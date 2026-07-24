"""Generic exact ConstructionProgramRecord VM for deterministic Phase-10 composition."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Callable, Mapping

from ..csir.authority_v351 import (
    AuthoritySnapshotV351, ClosureProof, SemanticAuthorityError,
    SemanticDefinitionCompiler, semantic_structural_exact_fingerprint,
)
from ..csir.canonical_v351 import normalize, semantic_fingerprint
from ..csir.model import (
    CSIRGraph, CSIRNodeKind, CSIRRef, ExactAuthorityPin, Qualifier, QualifierKind,
    ScopeEmbedding, SemanticVariable,
)
from ..csir.operations import KernelOperationError, Substitution, bind, substitute, unify
from ..language.model import ConstructionProgramOperation
from ..schema.model import SchemaClass


class ProgramVMError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ProgramVMFrontier:
    frontier_ref: str
    missing_contract: str
    source_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ProgramVMResult:
    graph: CSIRGraph
    closure_proofs: tuple[ClosureProof, ...]
    projection_authority_pins: tuple[ExactAuthorityPin, ...]
    source_refs: tuple[str, ...]
    frontiers: tuple[ProgramVMFrontier, ...] = ()


@dataclass(slots=True)
class _Instance:
    definition_pin: ExactAuthorityPin
    root_ref: CSIRRef
    formals_by_ref: dict[str, CSIRRef]
    proof: ClosureProof


@dataclass(slots=True)
class _Branch:
    graph: CSIRGraph
    symbols: dict[str, CSIRRef]
    instances: dict[str, _Instance]
    proofs: dict[str, ClosureProof]
    projection_pins: dict[tuple[str, str, str, int, str, str], ExactAuthorityPin]
    frontiers: list[ProgramVMFrontier]

    def clone(self):
        return _Branch(
            self.graph,
            dict(self.symbols),
            dict(self.instances),
            dict(self.proofs),
            dict(self.projection_pins),
            list(self.frontiers),
        )


def _merge(left: CSIRGraph, right: CSIRGraph) -> CSIRGraph:
    return CSIRGraph(
        terms=(*left.terms, *right.terms),
        variables=(*left.variables, *right.variables),
        applications=(*left.applications, *right.applications),
        bindings=(*left.bindings, *right.bindings),
        qualifiers=(*left.qualifiers, *right.qualifiers),
        scope_embeddings=(*left.scope_embeddings, *right.scope_embeddings),
        coordinations=(*left.coordinations, *right.coordinations),
        proof_links=(*left.proof_links, *right.proof_links),
        root_refs=tuple(dict.fromkeys((*left.root_refs, *right.root_refs))),
        unresolved_refs=tuple(sorted(set((*left.unresolved_refs, *right.unresolved_refs)))),
    )


class DeterministicConstructionProgramVM:
    """Execute only generic VM operations under exact v3.5.1 authority."""

    def __init__(self, authority_snapshot: AuthoritySnapshotV351, *, maximum_branches: int = 256) -> None:
        self.snapshot = authority_snapshot
        self.maximum_branches = maximum_branches
        self.compiler = SemanticDefinitionCompiler(authority_snapshot)

    def _definition(self, ref: str, revision: int):
        values = tuple(
            item for item in self.snapshot.semantic_definitions
            if item.definition_pin.ref == ref and item.definition_pin.revision == revision
        )
        if len(values) != 1:
            raise ProgramVMError(f"exact definition resolution requires one match:{ref}@{revision}:{len(values)}")
        return values[0]

    def _pin(self, ref: str, revision: int | None = None) -> ExactAuthorityPin:
        inventory = [item.definition_pin for item in self.snapshot.semantic_definitions]
        inventory.extend(
            port.port_pin for definition in self.snapshot.semantic_definitions for port in definition.formal_ports
        )
        inventory.extend(item.profile_pin for item in self.snapshot.operational_profiles)
        inventory.extend(item.parameter_pin for item in self.snapshot.dynamics_parameters)
        inventory.extend(item.model_pin for item in self.snapshot.observation_models)
        inventory.extend(item.mechanism_pin for item in self.snapshot.causal_mechanisms)
        inventory.extend(item.authorization_pin for item in self.snapshot.use_authorizations)
        inventory.extend(self.snapshot.auxiliary_exact_pins)
        values = tuple(
            pin for pin in inventory
            if pin.ref == ref and (revision is None or pin.revision == revision)
        )
        if len(values) != 1:
            raise ProgramVMError(f"exact authority resolution requires one match:{ref}@{revision}:{len(values)}")
        return values[0]

    def _open_instance(self, definition, namespace: str) -> tuple[CSIRGraph, _Instance]:
        # `_expand` is the authority compiler's exact graph-instantiation primitive.  The
        # occurrence stays open until the construction VM binds formal ports.
        graph, formals, _local = self.compiler._expand(
            definition, (definition.definition_pin.ref, namespace)
        )
        if len(graph.root_refs) != 1:
            raise ProgramVMError(
                f"construction-program definition requires one semantic root:{definition.definition_pin.key}:{len(graph.root_refs)}"
            )
        closure = self.compiler.closure_resolver.resolve(definition.definition_pin)
        template = self.compiler.expanded_template(definition.definition_pin)
        template = normalize(template)
        template_fp = semantic_fingerprint(template)
        conservative = (
            definition.expected_semantic_fingerprint is None
            or definition.expected_semantic_fingerprint == template_fp
        )
        if definition.executable and not conservative:
            raise ProgramVMError("non-conservative semantic definition cannot execute")
        proof = ClosureProof(
            root_definition_pin=definition.definition_pin,
            authority_generation=self.snapshot.generation,
            authority_fingerprint=self.snapshot.authority_fingerprint,
            semantic_authority_snapshot_fingerprint=self.snapshot.snapshot_fingerprint,
            closure_pins=closure.pins,
            dependency_edges=closure.dependency_edges,
            constraint_pins=closure.constraint_pins,
            expanded_template_semantic_fingerprint=template_fp,
            compiled_semantic_fingerprint=template_fp,
            compiled_structural_exact_fingerprint=semantic_structural_exact_fingerprint(template),
            expected_semantic_fingerprint=definition.expected_semantic_fingerprint,
            conservative=conservative,
        )
        proof.verify_authority(self.snapshot)
        instance = _Instance(
            definition_pin=definition.definition_pin,
            root_ref=graph.root_refs[0],
            formals_by_ref={
                port.port_pin.ref: CSIRRef(CSIRNodeKind.VARIABLE, formals[port.port_pin.key])
                for port in definition.formal_ports
            },
            proof=proof,
        )
        return graph, instance

    @staticmethod
    def _rewrite_refs_after_bind(branch: _Branch, variable: CSIRRef, filler: CSIRRef) -> None:
        for key, value in tuple(branch.symbols.items()):
            if value == variable:
                branch.symbols[key] = filler
        for instance in branch.instances.values():
            for key, value in tuple(instance.formals_by_ref.items()):
                if value == variable:
                    instance.formals_by_ref[key] = filler

    def _bind_instance_port(self, branch: _Branch, instance_symbol: str, port_ref: str, filler: CSIRRef) -> None:
        instance = branch.instances.get(instance_symbol)
        if instance is None:
            raise ProgramVMError(f"unknown application symbol:{instance_symbol}")
        variable = instance.formals_by_ref.get(port_ref)
        if variable is None:
            raise ProgramVMError(
                f"exact construction port does not exist on definition:{instance.definition_pin.ref}:{port_ref}"
            )
        if variable.kind is not CSIRNodeKind.VARIABLE:
            if variable != filler:
                raise ProgramVMError("construction attempts to rebind an already-bound formal port")
            return
        branch.graph = bind(branch.graph, variable.ref, filler)
        self._rewrite_refs_after_bind(branch, variable, filler)

    def _instantiate_into(self, branch: _Branch, *, definition, result_ref: str, namespace: str) -> None:
        graph, instance = self._open_instance(definition, namespace)
        branch.graph = _merge(branch.graph, graph)
        branch.symbols[result_ref] = instance.root_ref
        branch.instances[result_ref] = instance
        branch.proofs[instance.proof.proof_ref] = instance.proof

    def execute(
        self,
        *,
        program,
        construction_candidate,
        initial_graph: CSIRGraph,
        slot_resolver: Callable[[str], CSIRRef | None],
        closure_candidates,
    ) -> tuple[ProgramVMResult, ...]:
        branches = [_Branch(initial_graph, {}, {}, {}, {}, [])]
        for index, step in enumerate(program.steps):
            next_branches: list[_Branch] = []
            for branch in branches:
                try:
                    op = step.operation
                    if op == ConstructionProgramOperation.INTRODUCE_VARIABLE:
                        kinds = frozenset(step.expected_filler_classes)
                        allowed = frozenset({CSIRNodeKind.TERM, CSIRNodeKind.APPLICATION, CSIRNodeKind.COORDINATION})
                        # Filler-class constraints are checked by exact definitions later;
                        # the kernel variable kind remains structural.
                        variable = SemanticVariable(
                            variable_ref=f"vm:{construction_candidate.candidate_ref}:{step.result_ref}",
                            allowed_kinds=allowed,
                            scope_ref="global",
                            open_purpose=(
                                "partial" if step.open_binding_purpose is None
                                else step.open_binding_purpose.value
                            ),
                        )
                        branch.graph = replace(
                            branch.graph,
                            variables=(*branch.graph.variables, variable),
                        )
                        branch.symbols[step.result_ref] = variable.node_ref
                        next_branches.append(branch)
                    elif op in {ConstructionProgramOperation.INSTANTIATE_SCHEMA, ConstructionProgramOperation.WRAP_DISCOURSE_ACT}:
                        definition = self._definition(step.schema_ref, int(step.schema_revision))
                        self._instantiate_into(
                            branch, definition=definition, result_ref=step.result_ref,
                            namespace=f"{construction_candidate.candidate_ref}:{index}:{step.result_ref}",
                        )
                        if op == ConstructionProgramOperation.WRAP_DISCOURSE_ACT:
                            if len(step.input_refs) != 1:
                                raise ProgramVMError("discourse wrapper requires one content symbol")
                            filler = branch.symbols.get(step.input_refs[0])
                            if filler is None:
                                raise ProgramVMError("discourse wrapper content symbol is missing")
                            self._bind_instance_port(branch, step.result_ref, step.port_ref, filler)
                        next_branches.append(branch)
                    elif op == ConstructionProgramOperation.ACTIVATE_SCHEMA_CLASS_CANDIDATES:
                        definitions = []
                        for candidate in closure_candidates:
                            if candidate.schema_class not in set(step.schema_classes):
                                continue
                            try:
                                definition = self._definition(candidate.schema_ref, candidate.schema_revision)
                            except ProgramVMError:
                                continue
                            definitions.append(definition)
                        definitions = sorted(
                            {item.definition_pin.key: item for item in definitions}.values(),
                            key=lambda item: item.definition_pin.key,
                        )
                        if not definitions:
                            branch.frontiers.append(ProgramVMFrontier(
                                frontier_ref=f"frontier:composition:no-schema-class-candidate:{construction_candidate.candidate_ref}:{index}",
                                missing_contract="exact semantic definition candidate for declared schema class",
                                source_refs=(program.program_ref, step.step_ref),
                            ))
                            next_branches.append(branch)
                            continue
                        for branch_index, definition in enumerate(definitions):
                            child = branch.clone()
                            self._instantiate_into(
                                child, definition=definition, result_ref=step.result_ref,
                                namespace=f"{construction_candidate.candidate_ref}:{index}:{branch_index}",
                            )
                            next_branches.append(child)
                    elif op == ConstructionProgramOperation.BIND_PORT_FROM_SLOT:
                        fillers = tuple(dict(construction_candidate.slot_fillers).get(step.slot_ref, ()))
                        if len(fillers) != 1:
                            raise ProgramVMError(
                                f"exact port binding requires one slot filler:{step.slot_ref}:{len(fillers)}"
                            )
                        filler = slot_resolver(fillers[0])
                        if filler is None:
                            raise ProgramVMError(f"slot filler is not semantically grounded:{step.slot_ref}")
                        self._bind_instance_port(branch, step.input_refs[0], step.port_ref, filler)
                        next_branches.append(branch)
                    elif op == ConstructionProgramOperation.BIND_PORT_FROM_SYMBOL:
                        app_symbol, source_symbol = step.input_refs
                        filler = branch.symbols.get(source_symbol)
                        if filler is None:
                            raise ProgramVMError(f"missing source symbol:{source_symbol}")
                        self._bind_instance_port(branch, app_symbol, step.port_ref, filler)
                        next_branches.append(branch)
                    elif op == ConstructionProgramOperation.UNIFY:
                        if len(step.input_refs) < 2:
                            next_branches.append(branch)
                            continue
                        left = branch.symbols.get(step.input_refs[0]); right = branch.symbols.get(step.input_refs[1])
                        if left is None or right is None:
                            raise ProgramVMError("unify references missing symbols")
                        if left.kind is CSIRNodeKind.VARIABLE:
                            try:
                                branch.graph = substitute(branch.graph, Substitution(((left.ref, right),)))
                                self._rewrite_refs_after_bind(branch, left, right)
                            except KernelOperationError:
                                if right.kind is not CSIRNodeKind.VARIABLE:
                                    raise
                                branch.graph = substitute(branch.graph, Substitution(((right.ref, left),)))
                                self._rewrite_refs_after_bind(branch, right, left)
                        elif right.kind is CSIRNodeKind.VARIABLE:
                            branch.graph = substitute(branch.graph, Substitution(((right.ref, left),)))
                            self._rewrite_refs_after_bind(branch, right, left)
                        else:
                            result = unify(branch.graph, left, branch.graph, right)
                            if not result.success:
                                raise ProgramVMError(";".join(result.reason_refs) or "unification failed")
                            branch.graph = substitute(branch.graph, result.substitution)
                        next_branches.append(branch)
                    elif op == ConstructionProgramOperation.SET_PROJECTION:
                        pin = self._pin(step.value_ref, step.value_revision)
                        branch.projection_pins[pin.key] = pin
                        next_branches.append(branch)
                    elif op in {ConstructionProgramOperation.ADD_SCOPE, ConstructionProgramOperation.ADD_MODALITY}:
                        target = branch.symbols.get(step.input_refs[0]) if step.input_refs else (
                            next(iter(branch.symbols.values())) if len(branch.symbols) == 1 else None
                        )
                        if target is None:
                            raise ProgramVMError("scope/modality operation requires an unambiguous target symbol")
                        pin = self._pin(step.value_ref, step.value_revision) if step.value_ref else None
                        if pin is None:
                            raise ProgramVMError("scope/modality operation requires exact value authority")
                        qualifier = Qualifier(
                            qualifier_ref=f"vm:q:{construction_candidate.candidate_ref}:{index}",
                            target=target,
                            qualifier_kind=(
                                QualifierKind.MODALITY
                                if op == ConstructionProgramOperation.ADD_MODALITY else QualifierKind.CONTEXT
                            ),
                            value_pin=pin,
                        )
                        branch.graph = replace(branch.graph, qualifiers=(*branch.graph.qualifiers, qualifier))
                        next_branches.append(branch)
                    elif op in {
                        ConstructionProgramOperation.ADD_RESTRICTION,
                        ConstructionProgramOperation.ADD_TIME_FEATURE,
                        ConstructionProgramOperation.ADD_ASPECT_FEATURE,
                        ConstructionProgramOperation.PRESERVE_GAP,
                    }:
                        # These operations constrain/search or preserve information; they do
                        # not license inventing semantic applications. Exact restrictions are
                        # already represented by variables/definitions and verified later.
                        next_branches.append(branch)
                    else:
                        raise ProgramVMError(f"unsupported generic construction VM operation:{op.value}")
                except (ProgramVMError, SemanticAuthorityError, ValueError) as exc:
                    branch.frontiers.append(
                        ProgramVMFrontier(
                            frontier_ref=f"frontier:composition:program:{construction_candidate.candidate_ref}:{index}",
                            missing_contract=str(exc),
                            source_refs=(program.program_ref, step.step_ref),
                        )
                    )
                    next_branches.append(branch)
            branches = next_branches[: self.maximum_branches]
            if len(next_branches) > self.maximum_branches:
                for branch in branches:
                    branch.frontiers.append(
                        ProgramVMFrontier(
                            "frontier:composition:program-branch-budget",
                            "bounded discrete construction-program branch budget",
                            (program.program_ref,),
                        )
                    )
                break

        results = []
        for branch in branches:
            roots = tuple(
                branch.symbols[ref] for ref in program.root_symbol_refs if ref in branch.symbols
            )
            graph = branch.graph if not roots else replace(branch.graph, root_refs=roots)
            results.append(
                ProgramVMResult(
                    graph=graph,
                    closure_proofs=tuple(branch.proofs[key] for key in sorted(branch.proofs)),
                    projection_authority_pins=tuple(
                        branch.projection_pins[key] for key in sorted(branch.projection_pins)
                    ),
                    source_refs=(construction_candidate.candidate_ref, program.program_ref),
                    frontiers=tuple(branch.frontiers),
                )
            )
        return tuple(results)


__all__ = [
    "DeterministicConstructionProgramVM", "ProgramVMError", "ProgramVMFrontier", "ProgramVMResult",
]
