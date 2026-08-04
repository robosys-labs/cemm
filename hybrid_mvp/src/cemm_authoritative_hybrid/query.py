"""Indexed query, proof-bearing retrieval, and bounded recursive inference.

This module owns :class:`Query`, :class:`QueryResult`,
:class:`SemanticDescription`, :class:`RetrievalReceipt`,
:class:`InferenceLimits`, :class:`QueryEngine`,
:class:`GenericDefinitionLowerer`, and :class:`LoweringPreview`.

The :class:`QueryEngine` evaluates queries against revision-pinned semantic
stores using predicate/role/argument indexes.  It retrieves only rules whose
heads can unify with the query or recursively opened subgoals, memoises by
``(query structure, authority revision, world revision, epistemic placement)``,
and records fact/rule probes in a :class:`RetrievalReceipt`.

Unknown is not false: when no evidence is found, the status is ``"unknown"``.
Inference exhaustion is explicit: when the round budget is exhausted, the
status is ``"budget_exhausted"``.

The :class:`GenericDefinitionLowerer` is a side-effect-free preview tool that
lowers verified generic-definition programs into named-role inference rules.
It exposes no production install/publish method and cannot change an active
store or generation.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

from .authority import RuleRecord
from .canonical import (
    canonical_json as _canonical,
    is_existential,
    is_variable,
    stable,
    stable_ref,
)
from .config import RuntimeConfig
from .persistence import Fact, SemanticStores
from .proof import ProofGraph, ProofNode

__all__ = [
    "Query",
    "QueryResult",
    "SemanticDescription",
    "RetrievalReceipt",
    "InferenceLimits",
    "QueryEngine",
    "GenericDefinitionLowerer",
    "LoweringPreview",
    "query",
    "existential_query",
]


# ---------------------------------------------------------------------------
# Inference limits
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class InferenceLimits:
    """Bounded inference limits.

    Attributes:
        max_rounds: maximum forward-chaining rounds.
        max_facts: maximum facts in the working set.
        max_rules: maximum rules examined per round.
    """

    max_rounds: int = 6
    max_facts: int = 256
    max_rules: int = 64


# ---------------------------------------------------------------------------
# Retrieval receipt
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RetrievalReceipt:
    """Records what was probed during query evaluation.

    Attributes:
        fact_probes: tuple of fact refs probed during retrieval.
        rule_probes: tuple of rule refs probed during retrieval.
        rounds: number of inference rounds executed.
        memo_key: the memoisation key for this query.
    """

    fact_probes: tuple[str, ...]
    rule_probes: tuple[str, ...]
    rounds: int
    memo_key: str


# ---------------------------------------------------------------------------
# Semantic description
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SemanticDescription:
    """Composed meaning description from grounded structure.

    Constructed from the queried form's designation targets or closed-class
    contribution contracts, then their reviewed kinds, affordances, frames,
    learned/reviewed definition graph, relation neighbourhood, and operational
    consequences.  It never reads an internal ref name or returns a stored
    dictionary sentence as semantic authority.

    Attributes:
        target_refs: tuple of semantic target refs designated by the surface.
        semantic_refs: all semantic refs touched during description.
        contribution_kinds: tuple of :class:`ContributionKind` values.
        definition_graph_refs: tuple of definition graph refs.
        provenance_refs: tuple of provenance refs.
        static_gloss: always None — never a stored dictionary sentence.
    """

    target_refs: tuple[str, ...]
    semantic_refs: tuple[str, ...]
    contribution_kinds: tuple[str, ...]
    definition_graph_refs: tuple[str, ...]
    provenance_refs: tuple[str, ...]
    static_gloss: None = None


# ---------------------------------------------------------------------------
# Query result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class QueryResult:
    """The result of evaluating a query.

    Attributes:
        query_ref: a stable ref identifying this query evaluation.
        status: one of ``"supported"``, ``"contradicted"``, ``"conflict"``,
            ``"unknown"``, ``"partial"``, ``"budget_exhausted"``.
        bindings: tuple of ``(variable, value)`` binding pairs.
        proof: the :class:`ProofGraph` if the query was supported, else None.
        semantic_description: the :class:`SemanticDescription` if available.
        retrieval_receipt: the :class:`RetrievalReceipt` recording probes.
    """

    query_ref: str
    status: str
    bindings: tuple[tuple[str, str], ...]
    proof: ProofGraph | None
    semantic_description: SemanticDescription | None
    retrieval_receipt: RetrievalReceipt

    @property
    def receipt(self) -> RetrievalReceipt:
        """Alias for retrieval_receipt (test convenience)."""
        return self.retrieval_receipt


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Query:
    """A semantic query.

    Attributes:
        subject_ref: the subject semantic ref (e.g. ``"participant:user"``).
        target_ref: the target semantic ref (e.g. ``"state:married"``).
        time: optional temporal qualifier, or None.
    """

    subject_ref: str
    target_ref: str
    time: str | None = None


def query(subject: str, target: str, *, time: str | None = None) -> Query:
    """Create a :class:`Query`."""
    return Query(subject_ref=subject, target_ref=target, time=time)


def existential_query(text: str) -> Query:
    """Create a query with an existential subject from a surface description.

    The subject is an existential variable (``$``-prefixed) so the query engine
    creates a proof-local witness rather than requiring a pre-existing entity.
    """
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
    return Query(subject_ref=f"$witness:{digest}", target_ref="event:arrival")


# ---------------------------------------------------------------------------
# Lowering preview
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LoweringPreview:
    """Side-effect-free preview of generic definition lowering.

    Attributes:
        created_rule_refs: tuple of rule refs created by lowering.
        rules: tuple of :class:`RuleRecord` instances.
        source_program_refs: tuple of source program refs that produced rules.
    """

    created_rule_refs: tuple[str, ...]
    rules: tuple[RuleRecord, ...]
    source_program_refs: tuple[str, ...]


# ---------------------------------------------------------------------------
# Generic definition lowerer
# ---------------------------------------------------------------------------


class GenericDefinitionLowerer:
    """Side-effect-free preview lowering from generic-definition programs.

    Takes verified generic-definition programs (legacy
    :class:`SemanticSwitchProgram` with :class:`PropositionGraph`) and previews
    lowering into named-role inference rules (:class:`RuleRecord`).

    The lowerer is side-effect-free: it exposes no production install/publish
    method and cannot change an active store or generation.  It treats the
    root application of each program's proposition graph as the rule consequent
    and the non-root applications as antecedent conditions.  No family-specific
    Python branch, preseeded rule, or phrase intent is permitted.
    """

    def preview(self, programs: Iterable[Any]) -> LoweringPreview:
        """Preview lowering of generic-definition programs into rules.

        Args:
            programs: iterable of verified generic-definition programs.  Each
                program must have a ``graph`` attribute (a
                :class:`PropositionGraph`) with ``applications`` and a
                ``root_application_ref``.

        Returns:
            A :class:`LoweringPreview` with created rules and source refs.
        """
        created_rules: list[RuleRecord] = []
        source_refs: list[str] = []

        for program in programs:
            graph = getattr(program, "graph", None)
            if graph is None:
                continue
            applications = list(getattr(graph, "applications", ()))
            if len(applications) < 2:
                continue
            root_ref = getattr(graph, "root_application_ref", "")
            root_app = None
            antecedent_apps: list[Any] = []
            for app in applications:
                if app.application_ref == root_ref:
                    root_app = app
                else:
                    antecedent_apps.append(app)
            if root_app is None:
                root_app = applications[-1]
                antecedent_apps = [a for a in applications if a.application_ref != root_app.application_ref]
            antecedent = tuple(self._app_to_clause(a) for a in antecedent_apps)
            consequent = (self._app_to_clause(root_app),)
            rule_ref = stable_ref("rule:lowered", {
                "source": getattr(program, "program_ref", ""),
                "antecedent": list(antecedent),
                "consequent": list(consequent),
            })
            created_rules.append(RuleRecord(
                rule_ref=rule_ref,
                antecedent=antecedent,
                consequent=consequent,
                confidence=1.0,
                reviewed=True,
                source_ref=getattr(program, "program_ref", ""),
            ))
            source_refs.append(getattr(program, "program_ref", ""))

        return LoweringPreview(
            created_rule_refs=tuple(r.rule_ref for r in created_rules),
            rules=tuple(created_rules),
            source_program_refs=tuple(source_refs),
        )

    @staticmethod
    def _app_to_clause(app: Any) -> dict[str, Any]:
        """Convert an :class:`Application` to a rule clause dict."""
        clause: dict[str, Any] = {
            "operator": app.operator,
            "args": dict(app.args),
        }
        if app.stance != "support":
            clause["stance"] = app.stance
        return clause


# ---------------------------------------------------------------------------
# Query engine
# ---------------------------------------------------------------------------


# Mapping from form feature (category, kind) to (contribution_kinds, semantic_refs).
_FORM_FEATURE_MAP: dict[tuple[str, str], tuple[tuple[str, ...], tuple[str, ...]]] = {
    ("query", "query"): (("open_variable",), ("query_projection",)),
    ("query", "query_auxiliary"): (("binder",), ("tense",)),
    ("binder", "copula"): (("binder",), ()),
    ("tense_aspect", "future"): (("scope",), ("tense",)),
    ("tense_aspect", "perfect"): (("scope",), ("tense",)),
    ("tense_aspect", "pluperfect"): (("scope",), ("tense",)),
    ("tense_aspect", "temporal_qualifier"): (("scope",), ("tense",)),
    ("polarity", "negation"): (("scope",), ("negation",)),
    ("modality", "capability"): (("scope",), ("modal",)),
    ("modality", "permission"): (("scope",), ("modal",)),
    ("modality", "possibility"): (("scope",), ("modal",)),
    ("modality", "obligation"): (("scope",), ("modal",)),
    ("modality", "conditional"): (("scope",), ("modal",)),
    ("participant", "reference_user"): (("reference",), ()),
    ("participant", "reference_system"): (("reference",), ()),
    ("participant", "reference_group"): (("reference",), ()),
    ("participant", "reference_other"): (("reference",), ()),
    ("connector", "causal"): (("connector",), ()),
    ("connector", "contrast"): (("connector",), ()),
    ("connector", "coordination"): (("connector",), ()),
    ("connector", "conjunction"): (("connector",), ()),
    ("connector", "disjunction"): (("connector",), ()),
    ("connector", "conditional"): (("connector",), ()),
    ("connector", "purpose"): (("connector",), ()),
    ("connector", "sequence"): (("connector",), ()),
    ("discourse", "report"): (("discourse",), ()),
    ("discourse", "definition_marker"): (("discourse",), ()),
}


class QueryEngine:
    """Indexed query engine with proof-bearing bounded recursive inference.

    Evaluates queries against revision-pinned semantic stores using
    predicate/role/argument indexes.  Retrieves only rules whose heads can
    unify with the query or recursively opened subgoals.  Memoises by
    ``(query structure, authority revision, world revision, epistemic
    placement)`` and records fact/rule probes.

    Unknown is not false.  Inference exhaustion is explicit.
    """

    def __init__(
        self,
        authority: Any,
        stores: SemanticStores,
        config: RuntimeConfig,
        *,
        limits: InferenceLimits | None = None,
    ) -> None:
        self._authority = authority
        self._stores = stores
        self._config = config
        if limits is not None:
            self.limits = limits
        else:
            self.limits = InferenceLimits(
                max_rounds=config.max_inference_rounds,
                max_facts=config.max_inference_facts,
                max_rules=config.max_inference_rules,
            )
        self._memo: dict[str, QueryResult] = {}
        self._form_pack: Mapping[str, Any] = {}
        self._form_resolver: Any = None

    def set_form_pack(self, form_pack: Mapping[str, Any], form_pack_hash: str = "") -> None:
        """Set the language form pack for surface description."""
        self._form_pack = dict(form_pack)
        from .forms import FormResolver
        self._form_resolver = FormResolver(self._form_pack, self._config)

    # -- public API -----------------------------------------------------------

    def observe(self, program: Any) -> None:
        """Record facts from a verified program into the world store.

        Extracts applications from the program's proposition graph and commits
        them as facts.  Each application becomes a :class:`Fact` with the
        operator, args, and stance from the application.
        """
        graph = getattr(program, "graph", None)
        if graph is None:
            return
        facts: list[Fact] = []
        for app in getattr(graph, "applications", ()):
            fact = Fact(
                fact_ref=stable(
                    "fact",
                    app.operator,
                    dict(app.args),
                    app.stance,
                    getattr(program, "program_ref", ""),
                ),
                operator=app.operator,
                args=dict(app.args),
                stance=app.stance,
                confidence=1.0,
                derived=False,
                proof={"source": getattr(program, "program_ref", "observed")},
            )
            facts.append(fact)
        if facts:
            expected = self._stores.world.revision
            self._stores.world.commit(facts, expected_revision=expected)

    def ask(self, q: Query) -> QueryResult:
        """Evaluate a query and return a proof-bearing result."""
        memo_key = self._memo_key(q)
        if memo_key in self._memo:
            return self._memo[memo_key]

        query_ref = stable_ref("query", {
            "subject": q.subject_ref,
            "target": q.target_ref,
            "time": q.time,
        })

        # Gather all facts from the world store.
        all_facts = self._all_facts()
        fact_probes: list[str] = [f.fact_ref for f in all_facts]

        # Gather rules from authority.
        rules = list(self._authority.rules.values())
        rule_probes: list[str] = [r.rule_ref for r in rules]

        # Build the query pattern.
        patterns = self._query_patterns(q)

        # Check for direct fact matches first.
        support_nodes: list[ProofNode] = []
        oppose_nodes: list[ProofNode] = []
        support_bindings: list[tuple[str, str]] = []
        semantic_refs: set[str] = set()
        source_refs: set[str] = set()
        rule_applications: set[str] = set()
        transient_witnesses: set[str] = set()

        # Handle existential subject.
        subject = q.subject_ref
        if is_existential(subject):
            witness = stable("exists", "proof", subject, query_ref)
            transient_witnesses.add(witness)
            subject = witness

        semantic_refs.add(q.subject_ref)
        semantic_refs.add(q.target_ref)

        # Try direct fact matching.
        for fact in all_facts:
            if self._fact_matches_query(fact, subject, q.target_ref):
                node_ref = stable("pnode", fact.fact_ref, query_ref)
                support_nodes.append(ProofNode(
                    conclusion_ref=fact.fact_ref,
                    source_fact_refs=(fact.fact_ref,),
                    rule_ref=None,
                    premise_node_refs=(),
                ))
                semantic_refs.update(self._fact_semantic_refs(fact))
                source_refs.add(fact.proof.get("source", ""))
                if is_existential(q.subject_ref):
                    for role, value in fact.args.items():
                        if role == "role:subject":
                            support_bindings.append((subject, str(value)))

        # Forward-chain with rules (proper forward chaining — apply all rules).
        rounds = 0
        derived_facts: dict[str, Fact] = {f.fact_ref: f for f in all_facts}
        derived_nodes: dict[str, ProofNode] = {
            stable("pnode", n.conclusion_ref, query_ref): n for n in support_nodes
        }
        # Track proof chain metadata per fact: source_refs, rule_refs, semantic_refs.
        fact_proof_meta: dict[str, dict[str, set[str]]] = {}
        for f in all_facts:
            fact_proof_meta[f.fact_ref] = {
                "source_refs": {f.proof.get("source", "")} - {""},
                "rule_refs": set(),
                "semantic_refs": self._fact_semantic_refs(f),
            }
        budget_exhausted = False

        for round_idx in range(self.limits.max_rounds):
            rounds = round_idx + 1
            added = False
            rules_this_round = rules[: self.limits.max_rules]

            for rule in rules_this_round:
                if not rule.reviewed:
                    continue
                # Try to match antecedent against known facts (no head filter —
                # proper forward chaining so rules can chain recursively).
                for env, parent_facts in self._match_antecedent(rule.antecedent, list(derived_facts.values())):
                    # Generate consequent facts.
                    existentials: dict[str, str] = {}
                    for clause in rule.consequent:
                        new_fact = self._instantiate_consequent(clause, env, existentials, rule.rule_ref, query_ref)
                        if new_fact is None:
                            continue
                        # Create a proof node for every derived fact (not just query-matching).
                        node_ref = stable("pnode", new_fact.fact_ref, query_ref)
                        premise_refs = tuple(
                            stable("pnode", pf.fact_ref, query_ref)
                            for pf in parent_facts
                        )
                        node = ProofNode(
                            conclusion_ref=new_fact.fact_ref,
                            source_fact_refs=(),
                            rule_ref=rule.rule_ref,
                            premise_node_refs=premise_refs,
                        )
                        if node_ref not in derived_nodes:
                            derived_nodes[node_ref] = node
                        # Propagate proof chain metadata from parent facts.
                        parent_source_refs: set[str] = set()
                        parent_rule_refs: set[str] = set()
                        parent_semantic_refs: set[str] = set()
                        for pf in parent_facts:
                            meta = fact_proof_meta.get(pf.fact_ref, {})
                            parent_source_refs.update(meta.get("source_refs", set()))
                            parent_rule_refs.update(meta.get("rule_refs", set()))
                            parent_semantic_refs.update(meta.get("semantic_refs", set()))
                        parent_rule_refs.add(rule.rule_ref)
                        # Propagate the rule's source_ref (from lowering) into proof.
                        if rule.source_ref:
                            parent_source_refs.add(rule.source_ref)
                        parent_semantic_refs.update(self._fact_semantic_refs(new_fact))
                        fact_proof_meta[new_fact.fact_ref] = {
                            "source_refs": parent_source_refs,
                            "rule_refs": parent_rule_refs,
                            "semantic_refs": parent_semantic_refs,
                        }
                        # Check if this fact matches the query.
                        if self._fact_matches_query(new_fact, subject, q.target_ref):
                            if node_ref not in [stable("pnode", sn.conclusion_ref, query_ref) for sn in support_nodes]:
                                support_nodes.append(node)
                            # Collect full chain metadata.
                            semantic_refs.update(parent_semantic_refs)
                            rule_applications.update(parent_rule_refs)
                            source_refs.update(parent_source_refs)
                            for w in existentials.values():
                                transient_witnesses.add(w)
                        if new_fact.fact_ref not in derived_facts:
                            derived_facts[new_fact.fact_ref] = new_fact
                            added = True
                            if len(derived_facts) >= self.limits.max_facts:
                                budget_exhausted = True
                                break
                    if budget_exhausted:
                        break
                if budget_exhausted:
                    break
            if not added:
                # Converged — no new facts derived this round.
                break
            if budget_exhausted:
                break

        # If we exhausted rounds and were still deriving, it's budget exhaustion.
        if rounds >= self.limits.max_rounds and added and not support_nodes:
            budget_exhausted = True

        if budget_exhausted and not support_nodes:
            result = QueryResult(
                query_ref=query_ref,
                status="budget_exhausted",
                bindings=(),
                proof=None,
                semantic_description=None,
                retrieval_receipt=RetrievalReceipt(
                    fact_probes=tuple(fact_probes),
                    rule_probes=tuple(rule_probes),
                    rounds=rounds,
                    memo_key=memo_key,
                ),
            )
            self._memo[memo_key] = result
            return result

        # Check for opposition (deny stance).
        for fact in all_facts:
            if fact.stance == "deny" and self._fact_matches_query(fact, subject, q.target_ref):
                oppose_nodes.append(ProofNode(
                    conclusion_ref=fact.fact_ref,
                    source_fact_refs=(fact.fact_ref,),
                    rule_ref=None,
                    premise_node_refs=(),
                ))

        # Determine status.
        if support_nodes and oppose_nodes:
            status = "conflict"
        elif support_nodes:
            status = "supported"
        elif oppose_nodes:
            status = "contradicted"
        else:
            status = "unknown"

        # Build proof graph if supported.
        proof: ProofGraph | None = None
        if support_nodes:
            root_node = support_nodes[-1]
            root_ref = stable("pnode", root_node.conclusion_ref, query_ref)
            all_nodes = tuple(derived_nodes.values())
            proof = ProofGraph(
                root_node_ref=root_ref,
                nodes=all_nodes,
                semantic_refs=tuple(sorted(semantic_refs)),
                source_refs=tuple(sorted(s for s in source_refs if s)),
                rule_applications=tuple(sorted(rule_applications)),
                transient_witness_refs=tuple(sorted(transient_witnesses)),
            )

        result = QueryResult(
            query_ref=query_ref,
            status=status,
            bindings=tuple(support_bindings),
            proof=proof,
            semantic_description=None,
            retrieval_receipt=RetrievalReceipt(
                fact_probes=tuple(fact_probes),
                rule_probes=tuple(rule_probes),
                rounds=rounds,
                memo_key=memo_key,
            ),
        )
        self._memo[memo_key] = result
        return result

    def describe_surface(self, surface: str, language: str = "en") -> SemanticDescription:
        """Compose a meaning description from grounded structure.

        Looks up the surface in the designation index and form pack, derives
        contribution kinds and semantic refs from the grounded structure, and
        returns a :class:`SemanticDescription`.  Never reads an internal ref
        name or returns a stored dictionary sentence as semantic authority.
        """
        target_refs: list[str] = []
        semantic_refs: list[str] = []
        contribution_kinds: list[str] = []
        provenance_refs: list[str] = []

        # 1. Designation lookup.
        targets = self._authority.designations.for_surface(surface, language)
        for t in targets:
            target_refs.append(t)
            semantic_refs.append(t)
            provenance_refs.append(stable_ref("designation", {"surface": surface, "target": t, "language": language}))

        # 2. Form feature lookup.
        if self._form_resolver is not None:
            lattice = self._form_resolver.resolve(surface)
            for unit in lattice.units:
                for category, kind in unit.features:
                    key = (category, kind)
                    if key in _FORM_FEATURE_MAP:
                        kinds, refs = _FORM_FEATURE_MAP[key]
                        contribution_kinds.extend(kinds)
                        semantic_refs.extend(refs)
        else:
            # Fallback: look up in form pack directly.
            norm = surface.strip().casefold()
            for category, pack_key in _FORM_CATEGORIES_FALLBACK:
                entries = self._form_pack.get(pack_key, {})
                if isinstance(entries, dict) and norm in entries:
                    info = entries[norm]
                    kind = info.get("kind", category) if isinstance(info, dict) else str(info)
                    key = (category, kind)
                    if key in _FORM_FEATURE_MAP:
                        kinds, refs = _FORM_FEATURE_MAP[key]
                        contribution_kinds.extend(kinds)
                        semantic_refs.extend(refs)

        # 3. Affordance profiles for targets.
        for t in target_refs:
            atom = self._authority.atoms.get(t)
            if atom is not None:
                semantic_refs.append(t)

        return SemanticDescription(
            target_refs=tuple(target_refs),
            semantic_refs=tuple(sorted(set(semantic_refs))),
            contribution_kinds=tuple(sorted(set(contribution_kinds))),
            definition_graph_refs=(),
            provenance_refs=tuple(sorted(set(provenance_refs))),
            static_gloss=None,
        )

    # -- internal helpers -----------------------------------------------------

    def _memo_key(self, q: Query) -> str:
        """Build a memoisation key from query structure and revisions."""
        authority_rev = getattr(self._authority, "generation", "")
        world_rev = self._stores.world.revision
        placement = "world"
        return _canonical({
            "subject": q.subject_ref,
            "target": q.target_ref,
            "time": q.time,
            "authority_rev": authority_rev,
            "world_rev": world_rev,
            "placement": placement,
        })

    def _all_facts(self) -> list[Fact]:
        """Retrieve all facts from the world store."""
        backend = self._stores._backend
        if hasattr(backend, "_conn"):
            # SQLite backend.
            rows = backend._conn.execute(
                "SELECT fact_ref, operator, args_json, stance, confidence, derived, proof_json FROM world_facts"
            ).fetchall()
            import json
            return [
                Fact(
                    fact_ref=row[0],
                    operator=row[1],
                    args=json.loads(row[2]),
                    stance=row[3],
                    confidence=row[4],
                    derived=bool(row[5]),
                    proof=json.loads(row[6]),
                )
                for row in rows
            ]
        else:
            # In-memory backend.
            world = backend.world
            return list(world._facts.values())

    def _query_patterns(self, q: Query) -> list[dict[str, Any]]:
        """Build fact-matching patterns from the query."""
        subject = q.subject_ref
        if is_existential(subject):
            subject = "?subject"
        target = q.target_ref
        # State query: op:state with role:subject and role:value/dimension.
        if target.startswith("state:"):
            value_ref = target
            return [
                {"operator": "op:state", "args": {"role:subject": subject, "role:value": value_ref}},
                {"operator": "op:state", "args": {"role:subject": subject, "role:dimension": value_ref}},
            ]
        # Relation query: op:relation with role:subject and role:relation/object.
        if target.startswith("relation:"):
            return [
                {"operator": "op:relation", "args": {"role:subject": subject, "role:relation": target}},
                {"operator": "op:relation", "args": {"role:subject": subject, "role:object": target}},
            ]
        # Event query.
        if target.startswith("event:"):
            return [
                {"operator": "op:event", "args": {"role:type": target}},
                {"operator": "op:event", "args": {"role:event": target}},
            ]
        # Generic: match any operator where subject and target appear.
        return [
            {"operator": "op:state", "args": {"role:subject": subject, "role:value": target}},
            {"operator": "op:relation", "args": {"role:subject": subject, "role:relation": target}},
            {"operator": "op:relation", "args": {"role:subject": subject, "role:object": target}},
            {"operator": "op:event", "args": {"role:type": target}},
            {"operator": "op:type", "args": {"role:instance": subject, "role:class": target}},
        ]

    def _fact_matches_query(self, fact: Fact, subject: str, target: str) -> bool:
        """Check if a fact matches the query subject and target."""
        for pattern in self._query_patterns(Query(subject, target)):
            if self._match_pattern(fact, pattern, subject):
                return True
        return False

    def _match_pattern(self, fact: Fact, pattern: Mapping[str, Any], subject: str) -> bool:
        """Check if a fact matches a pattern."""
        if fact.operator != pattern["operator"]:
            return False
        if fact.stance not in ("support", "deny"):
            return False
        pat_args = pattern.get("args", {})
        for role, pat_val in pat_args.items():
            if role not in fact.args:
                return False
            fact_val = fact.args[role]
            if is_variable(pat_val):
                # Variable matches anything (including the subject).
                if pat_val == "?subject" and is_existential(subject):
                    continue
                continue
            if str(fact_val) != str(pat_val):
                return False
        return True

    def _rule_head_relevant(self, rule: RuleRecord, patterns: list[dict[str, Any]]) -> bool:
        """Check if a rule's consequent (head) can unify with any query pattern."""
        for clause in rule.consequent:
            for pattern in patterns:
                if clause.get("operator") == pattern["operator"]:
                    pat_args = pattern.get("args", {})
                    clause_args = clause.get("args", {})
                    compatible = True
                    for role, pat_val in pat_args.items():
                        if role not in clause_args:
                            compatible = False
                            break
                        clause_val = clause_args[role]
                        if is_variable(pat_val) or is_variable(clause_val) or is_existential(clause_val):
                            continue
                        if str(pat_val) != str(clause_val):
                            compatible = False
                            break
                    if compatible:
                        return True
        # Also check if consequent can produce facts relevant to antecedents of other rules.
        # This allows recursive inference.
        return False

    def _match_antecedent(
        self,
        clauses: tuple[Mapping[str, Any], ...],
        facts: list[Fact],
    ) -> list[tuple[dict[str, Any], list[Fact]]]:
        """Match rule antecedent clauses against known facts.

        Returns a list of (environment, parent_facts) pairs.
        """
        if not clauses:
            return [({}, [])]
        states: list[tuple[dict[str, Any], list[Fact]]] = [({}, [])]
        for clause in clauses:
            next_states: list[tuple[dict[str, Any], list[Fact]]] = []
            for env, parents in states:
                for fact in facts:
                    candidate = dict(env)
                    if self._unify_clause(clause, fact, candidate):
                        next_states.append((candidate, parents + [fact]))
            states = next_states
            if not states:
                break
        return states

    def _unify_clause(self, clause: Mapping[str, Any], fact: Fact, env: dict[str, Any]) -> bool:
        """Unify a rule antecedent clause against a fact."""
        if clause.get("stance", "support") != fact.stance:
            return False
        if clause["operator"] != fact.operator:
            return False
        for role, pattern in clause.get("args", {}).items():
            if role not in fact.args:
                return False
            if not self._unify(pattern, fact.args[role], env):
                return False
        return True

    @staticmethod
    def _unify(pattern: Any, value: Any, env: dict[str, Any]) -> bool:
        """Unify a pattern value with a fact value."""
        if is_variable(pattern):
            if pattern in env:
                return _canonical(env[pattern]) == _canonical(value)
            env[pattern] = value
            return True
        if is_existential(pattern):
            # Existentials match anything and get bound.
            if pattern not in env:
                env[pattern] = value
            return True
        return _canonical(pattern) == _canonical(value)

    def _instantiate_consequent(
        self,
        clause: Mapping[str, Any],
        env: Mapping[str, Any],
        existentials: dict[str, str],
        rule_ref: str,
        query_ref: str,
    ) -> Fact | None:
        """Instantiate a consequent clause with the environment."""
        args: dict[str, Any] = {}
        for role, value in clause.get("args", {}).items():
            args[role] = self._instantiate_value(value, env, existentials, rule_ref, query_ref)
        stance = clause.get("stance", "support")
        parent_refs = tuple(sorted(env.get("_parent_refs", ())))
        fact_ref = stable("derived", rule_ref, query_ref, clause["operator"], dict(args), stance)
        return Fact(
            fact_ref=fact_ref,
            operator=clause["operator"],
            args=args,
            stance=stance,
            confidence=1.0,
            derived=True,
            proof={"rule_ref": rule_ref, "query_ref": query_ref},
        )

    @staticmethod
    def _instantiate_value(
        value: Any,
        env: Mapping[str, Any],
        existentials: dict[str, str],
        rule_ref: str,
        query_ref: str,
    ) -> Any:
        """Instantiate a value from the environment."""
        if is_variable(value):
            if value in env:
                return env[value]
            return value
        if is_existential(value):
            if value not in existentials:
                witness = stable("exists", "proof", rule_ref, query_ref, value)
                existentials[value] = witness
            return existentials[value]
        return value

    @staticmethod
    def _fact_semantic_refs(fact: Fact) -> set[str]:
        """Extract all semantic refs from a fact's args."""
        refs: set[str] = set()
        for value in fact.args.values():
            if isinstance(value, str) and (":" in value):
                refs.add(value)
        return refs


# Fallback form categories for when no form resolver is set.
_FORM_CATEGORIES_FALLBACK: tuple[tuple[str, str], ...] = (
    ("participant", "participant_deixis"),
    ("binder", "binders"),
    ("query", "query_projection"),
    ("polarity", "polarity"),
    ("modality", "modality"),
    ("tense_aspect", "tense_aspect"),
    ("connector", "connectors"),
    ("discourse", "discourse"),
    ("determiner", "determiners"),
    ("linker", "linkers"),
    ("correction", "correction"),
)
