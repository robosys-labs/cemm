"""Learned semantic interpretation over a bounded reversible form lattice.

Surface normalization and span matching are isolated in :mod:`cemm.forms`.
Those stages propose evidence and N-best grounding hypotheses only.  Reviewed
construction records and the neural codec propose exact semantic packets;
``ExactStructuredCompiler`` and ``SemanticSettler`` remain semantic authority.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from cemm.codec import Candidate, StructuredSemanticCodec
from cemm.compiler import ExactStructuredCompiler
from cemm.config import Config
from cemm.context import ParticipantFrame
from cemm.evidence import EvidenceEnvelope, EvidenceLattice
from cemm.forms import (
    ConstructionCandidateGenerator,
    FormPack,
    FormProcessor,
    GroundingHypothesis,
    ResolvedFormLattice,
    generic_designation_learning_packet,
)
from cemm.model import AmbiguousReferent, norm_text, surface, toks
from cemm.settler import SemanticSettler

try:
    import torch
    from torch import nn
except Exception as exc:  # pragma: no cover - import contract
    raise SystemExit("pip install torch") from exc


torch.set_num_threads(1)
MODEL_CACHE: dict[tuple[str, str], "SurfaceCodec"] = {}


class TransformerClassifier(nn.Module):
    def __init__(self, vocab, classes, d=48):
        super().__init__()
        self.emb = nn.Embedding(vocab, d, padding_idx=0)
        self.pos = nn.Embedding(128, d)
        layer = nn.TransformerEncoderLayer(d, 4, 96, dropout=0, batch_first=True)
        self.enc = nn.TransformerEncoder(layer, 1)
        self.out = nn.Linear(d, classes)

    def forward(self, values):
        positions = torch.arange(values.size(1), device=values.device)[None, :]
        hidden = self.enc(
            self.emb(values) + self.pos(positions),
            src_key_padding_mask=values.eq(0),
        )
        mask = values.ne(0).float().unsqueeze(-1)
        return self.out((hidden * mask).sum(1) / mask.sum(1).clamp_min(1))


def train_classifier(examples, key, label_key, seed=11, epochs=120):
    labels = sorted({example[label_key] for example in examples})
    label_index = {value: index for index, value in enumerate(labels)}
    vocabulary = ["<pad>", "<unk>"] + sorted(
        {token.casefold() for example in examples for token in toks(example[key])}
    )
    vocabulary_index = {value: index for index, value in enumerate(vocabulary)}
    sequences = [
        [vocabulary_index.get(token.casefold(), 1) for token in toks(example[key])]
        for example in examples
    ]
    maximum = max(map(len, sequences))
    values = torch.tensor(
        [sequence + [0] * (maximum - len(sequence)) for sequence in sequences]
    )
    targets = torch.tensor([label_index[example[label_key]] for example in examples])
    torch.manual_seed(seed)
    net = TransformerClassifier(len(vocabulary), len(labels))
    optimizer = torch.optim.AdamW(net.parameters(), lr=0.01)
    for _ in range(epochs):
        optimizer.zero_grad()
        loss = nn.functional.cross_entropy(net(values), targets)
        loss.backward()
        optimizer.step()
    net.eval()
    return {"labels": labels, "vi": vocabulary_index}, net


def predict_classifier(meta, net, text):
    sequence = [meta["vi"].get(token.casefold(), 1) for token in toks(text)]
    known = sum(index != 1 for index in sequence) / max(1, len(sequence))
    values = torch.tensor([sequence or [1]])
    with torch.no_grad():
        probabilities = torch.softmax(net(values), -1)[0]
        scores, indexes = torch.topk(probabilities, min(2, len(probabilities)))
    label = meta["labels"][int(indexes[0])]
    margin = float(scores[0] - (scores[1] if len(scores) > 1 else 0))
    return label, float(scores[0]), margin, known


class SurfaceCodec:
    def __init__(self, pack):
        examples = pack.data.get("realization_examples", [])
        self.meta, self.net = train_classifier(
            examples, "semantic", "surface_plan", 23, 110
        )
        self.allowed = {}
        for example in examples:
            self.allowed.setdefault(norm_text(example["semantic"]), set()).add(
                norm_text(example["surface_plan"])
            )

    @classmethod
    def get(cls, pack, cache=None):
        key = (pack.hash, "surface-v6-form-lattice")
        if cache is not None:
            existing = cache.get(key)
            if existing is not None:
                return existing
            value = cls(pack)
            cache.put(key, value)
            return value
        if key not in MODEL_CACHE:
            MODEL_CACHE[key] = cls(pack)
        return MODEL_CACHE[key]

    def realize(self, semantic):
        plan, confidence, margin, known = predict_classifier(
            self.meta, self.net, semantic
        )
        return plan, {
            "semantic": semantic,
            "surface_plan": plan,
            "confidence": confidence,
            "margin": margin,
            "known_token_ratio": known,
            "authorized_transform": norm_text(plan)
            in self.allowed.get(norm_text(semantic), set()),
        }


def _default_form_pack_path(language: str) -> Path:
    return Path(__file__).resolve().parent / "form_packs" / f"{language}.json"


class Delexer:
    """Compatibility facade over the new N-best form processor.

    ``run`` returns the best diagnostic delexicalization for rule-learning and
    older callers.  The ordinary runtime uses :meth:`resolve`, preserving all
    bounded alternatives until semantic settling.
    """

    def __init__(
        self,
        store,
        language,
        authority_generation=None,
        *,
        form_pack: FormPack | None = None,
        function_forms=(),
        config: Config | None = None,
    ):
        self.s = store
        self.lang = language
        self.authority_generation = authority_generation
        self.config = config or Config()
        self.form_pack = form_pack or FormPack(_default_form_pack_path(language))
        self.processor = FormProcessor(
            store,
            language,
            authority_generation,
            self.form_pack,
            semantic_function_forms=function_forms,
            max_input_chars=getattr(self.config, "form_max_input_chars", 8192),
            max_normalizations=getattr(self.config, "form_max_normalizations", 8),
            max_grounding_hypotheses=getattr(
                self.config, "form_max_grounding_hypotheses", 16
            ),
            max_span_candidates=getattr(
                self.config, "form_max_span_candidates", 128
            ),
        )

    def resolve(self, text, participant_frame: ParticipantFrame | None = None):
        return self.processor.resolve(text, participant_frame)

    @staticmethod
    def render_hypothesis(hypothesis: GroundingHypothesis):
        ref_to_placeholder: dict[str, str] = {}
        anchors: dict[str, str] = {}
        uses: list[tuple[str, str]] = []
        rendered: list[str] = []
        for unit in hypothesis.units:
            if unit.kind == "anchor" and unit.semantic_ref:
                placeholder = ref_to_placeholder.setdefault(
                    unit.semantic_ref, f"@A{len(ref_to_placeholder)}"
                )
                anchors[placeholder] = unit.semantic_ref
                rendered.append(f"{placeholder}<{unit.atom_kind or 'atom'}>")
                if unit.source_kind == "designation":
                    uses.append((unit.surface, unit.semantic_ref))
            else:
                rendered.append(unit.surface)
        return surface(rendered), anchors, uses

    def run(self, text, participant_frame: ParticipantFrame | None = None):
        lattice = self.resolve(text, participant_frame)
        if not lattice.grounding_hypotheses:
            return text, {}, []
        return self.render_hypothesis(lattice.grounding_hypotheses[0])

    def reference(self, surface_value, participant_frame=None):
        lattice = self.resolve(str(surface_value), participant_frame)
        candidates = []
        for hypothesis in lattice.grounding_hypotheses:
            if len(hypothesis.units) != 1:
                continue
            unit = hypothesis.units[0]
            if unit.kind == "anchor" and unit.semantic_ref:
                candidates.append((hypothesis.score, unit.semantic_ref))
        unique = []
        for score, ref in sorted(candidates, reverse=True):
            if ref not in [item[1] for item in unique]:
                unique.append((score, ref))
        if len(unique) > 1 and unique[0][0] - unique[1][0] < 0.25:
            raise AmbiguousReferent(
                surface_value,
                [{"ref": ref, "score": score} for score, ref in unique[:5]],
            )
        return unique[0][1] if unique else None


class Interpreter:
    def __init__(self, store, pack, authority_generation=None, config=None):
        self.s = store
        self.pack = pack
        self.authority_generation = authority_generation
        self.config = config or Config()
        self.lang = pack.language
        self.codec = StructuredSemanticCodec(pack, self.config)
        self.codec.authority_generation = authority_generation
        self.compiler = ExactStructuredCompiler(store)
        self.settler = SemanticSettler(store, self.compiler, self.config)
        configured = pack.data.get("form_pack")
        if configured:
            path = Path(pack.path).parent / str(configured)
        else:
            path = _default_form_pack_path(self.lang)
        self.form_pack = FormPack(path)
        expected_form_hash = pack.data.get("form_pack_hash")
        if expected_form_hash and str(expected_form_hash) != self.form_pack.hash:
            raise ValueError(
                f"language/form pack hash mismatch: {expected_form_hash} != {self.form_pack.hash}"
            )
        self.delexer = Delexer(
            store,
            self.lang,
            authority_generation,
            form_pack=self.form_pack,
            function_forms=(
                pack.data.get("function_forms")
                or pack.data.get("grammar_tokens", [])
            ),
            config=self.config,
        )
        self.constructions = ConstructionCandidateGenerator(
            self.form_pack,
            max_matches=getattr(self.config, "form_max_construction_matches", 32),
        )
        self._candidate_unknown_kinds_cache = self._candidate_unknown_kinds()

    def _candidate_unknown_kinds(self):
        kinds = set()
        for operator in self.pack.data.get("operators", []):
            for spec in self.s.roles(operator).values():
                expected = spec["filler_kind"]
                if expected == "state_value":
                    kinds.add("value")
                elif (
                    expected
                    and expected not in {"atom", "app"}
                    and not str(expected).startswith("literal:")
                ):
                    kinds.add(str(expected))
        # Reviewed acquisition may create identities of these existing semantic
        # kinds even when a particular language model does not currently emit
        # the corresponding operator role.
        kinds.update({"concept", "entity", "event_type", "relation_type", "time", "value"})
        return tuple(sorted(kinds))

    def _unknown_evidence(self, hypothesis: GroundingHypothesis):
        return tuple(
            {
                "surface": unit.surface,
                "normalized": unit.normalized,
                "char_start": unit.char_start,
                "char_end": unit.char_end,
                "unit_ref": unit.unit_ref,
                "semantic_kind_candidates": list(
                    self._candidate_unknown_kinds_cache
                ),
            }
            for unit in hypothesis.units
            if unit.kind == "unknown"
        )

    @staticmethod
    def _grounded_refs(hypothesis: GroundingHypothesis):
        return tuple(
            sorted(
                {
                    unit.semantic_ref
                    for unit in hypothesis.units
                    if unit.kind == "anchor" and unit.semantic_ref
                }
            )
        )

    def observe(self, text, participant_frame: ParticipantFrame):
        envelope = EvidenceEnvelope.text(
            text,
            participant_frame.speaker_ref,
            language=self.lang,
            channel=participant_frame.channel,
            permission_scope=None,
        )
        resolved = self.delexer.resolve(text, participant_frame)
        top = resolved.grounding_hypotheses[0] if resolved.grounding_hypotheses else None
        if top:
            delex, placeholders, uses = Delexer.render_hypothesis(top)
            unknown = self._unknown_evidence(top)
        else:
            delex, placeholders, uses, unknown = text, {}, [], ()
        clauses = tuple(
            clause.strip()
            for clause in re.split(r"(?<=[.!?])\s+", delex.strip())
            if clause.strip()
        ) or (delex,)
        return EvidenceLattice(
            (envelope,),
            {
                "delexicalized": delex,
                "grounded_anchors": dict(placeholders),
                "clauses": list(clauses),
                "uses": list(uses),
                "form_lattice_ref": resolved.lattice_ref,
                "form_hypothesis_count": len(resolved.grounding_hypotheses),
                "normalization_count": len(resolved.normalization_candidates),
                "form_bounds": dict(resolved.bounded),
                "safety_flags": list(resolved.safety_flags),
            },
            unknown,
            resolved,
        )

    def _construction_candidates(self, resolved, participant_frame):
        by_ref = {
            item.evidence_ref: item
            for item in self.constructions.evidence(resolved, participant_frame)
        }
        candidates = []
        for evidence in by_ref.values():
            try:
                packet = self.constructions.instantiate(
                    evidence, participant_frame, self.lang
                )
            except Exception:
                continue
            candidates.append(
                Candidate(
                    packet,
                    evidence.score,
                    {
                        "source": "reviewed_construction",
                        "construction_ref": evidence.construction_ref,
                        "construction_evidence_ref": evidence.evidence_ref,
                        "hypothesis_ref": evidence.hypothesis_ref,
                        "captures": dict(evidence.captures),
                        "remaining_unknowns": list(evidence.remaining_unknowns),
                    },
                )
            )
        return candidates, by_ref

    def _neural_candidates(self, resolved, participant_frame, state_projections):
        candidates = []
        hypothesis_budget = min(
            len(resolved.grounding_hypotheses),
            getattr(self.config, "form_max_semantic_hypotheses", 8),
        )
        for hypothesis in resolved.grounding_hypotheses[:hypothesis_budget]:
            text, anchors, _uses = Delexer.render_hypothesis(hypothesis)
            predicted = self.codec.predict(
                text,
                anchors,
                self.s,
                top_k=self.config.settler_top_k,
                participant_frame=participant_frame,
            )
            for candidate in predicted:
                candidate.score += hypothesis.score
                candidate.trace["source"] = "neural_structured_codec"
                candidate.trace["hypothesis_ref"] = hypothesis.hypothesis_ref
                candidate.trace["input"] = text
                candidate.trace["state_projection_refs"] = sorted(
                    (state_projections or {}).keys()
                )
                candidates.append(candidate)
        return candidates

    @staticmethod
    def _selected_neural_trace(settle_trace):
        candidates = settle_trace.get("candidates", ()) if settle_trace else ()
        return dict(candidates[0].get("neural", {})) if candidates else {}

    def _learning_frontier_for_packet(self, packet, selected_trace):
        qualifiers = dict(packet.get("qualifiers", {})) if packet else {}
        operation = qualifiers.get("learning_operation")
        if not operation:
            return ()
        captures = selected_trace.get("captures", {})
        literal = captures.get("surface") or qualifiers.get("surface_evidence")
        if isinstance(literal, dict) and "literal" in literal:
            literal = literal["literal"].get("value")
        if not literal:
            return ()
        query = packet.get("query")
        return (
            {
                "surface": str(literal),
                "normalized": norm_text(literal),
                "semantic_kind_candidates": list(
                    self._candidate_unknown_kinds_cache
                ),
                "learning_operation": str(operation),
                "probe_query": dict(query) if query else None,
                "blocks": ["knowledge_binding"],
                "priority": 2.0,
            },
        )

    @staticmethod
    def _best_unknown(items):
        # Structural information-gain proxy: prefer longer spans and later
        # content-bearing positions.  Nonblocking discourse units have already
        # been classified separately and are never included here.
        if not items:
            return None
        return max(
            items,
            key=lambda item: (
                len(str(item.get("surface", ""))),
                int(item.get("char_start", 0)),
                str(item.get("normalized", "")),
            ),
        )

    def compose(
        self,
        lattice: EvidenceLattice,
        participant_frame: ParticipantFrame,
        state_projections=None,
    ):
        resolved: ResolvedFormLattice | None = lattice.resolved_form_lattice
        if resolved is None:
            resolved = self.delexer.resolve(
                str(lattice.envelopes[0].payload.get("text", "")), participant_frame
            )
        construction_candidates, construction_by_ref = self._construction_candidates(
            resolved, participant_frame
        )
        neural_candidates = self._neural_candidates(
            resolved, participant_frame, state_projections
        )
        candidate_budget = max(
            self.config.settler_top_k,
            getattr(self.config, "form_max_semantic_candidates", 48),
        )
        candidates = sorted(
            construction_candidates + neural_candidates,
            key=lambda item: item.score,
            reverse=True,
        )[:candidate_budget]
        settled, settle_trace = self.settler.settle(candidates, "F0")
        selected_trace = self._selected_neural_trace(settle_trace)

        top_hypothesis = (
            resolved.grounding_hypotheses[0]
            if resolved.grounding_hypotheses
            else None
        )
        uses = []
        grounded_refs = ()
        top_unknown = ()
        delex = str(lattice.form_evidence.get("delexicalized", ""))
        if top_hypothesis:
            delex, anchors, uses = Delexer.render_hypothesis(top_hypothesis)
            grounded_refs = self._grounded_refs(top_hypothesis)
            top_unknown = self._unknown_evidence(top_hypothesis)
        else:
            anchors = {}

        if settled:
            packet, news = settled
            remaining_unknowns = tuple(selected_trace.get("remaining_unknowns", ()))
            learning_frontier = self._learning_frontier_for_packet(
                packet, selected_trace
            )
            unresolved = tuple(remaining_unknowns) + tuple(learning_frontier)
            status = "partial" if unresolved else "resolved"
            trace = {
                "structured_prediction": True,
                "clauses": [settle_trace],
                "n_best": True,
                "resolved_form_lattice": resolved.as_dict(),
                "delexicalized": delex,
                "grounded_anchors": anchors,
                "unknown_form_evidence": list(unresolved),
                "skipped_clauses": [],
                "interpretation_assessment": {
                    "status": status,
                    "grounded_refs": list(grounded_refs),
                    "open_variables": sorted(
                        {
                            value
                            for application in (
                                list(packet.get("apps", ()))
                                + list((packet.get("query") or {}).get("restrictions", ()))
                            )
                            for value in application.get("args", {}).values()
                            if isinstance(value, str) and value.startswith("?")
                        }
                    ),
                    "unresolved_evidence": list(unresolved),
                    "blockers": sorted(
                        {
                            "knowledge_binding"
                            if item.get("learning_operation")
                            else "unknown_form"
                            for item in unresolved
                        }
                    ),
                },
                "state_projection_refs": sorted(
                    (state_projections or {}).keys()
                ),
                "side_effect_free": True,
                "selected_candidate": selected_trace,
                "candidate_count": len(candidates),
            }
            return packet, news, uses, trace

        # If no exact semantic candidate settled, turn the highest-value open
        # form into an exact designation query.  Stage 10 searches learned data
        # before Stage 15 is allowed to ask the user for evidence.
        target = self._best_unknown(top_unknown)
        if target:
            packet = generic_designation_learning_packet(
                str(target["surface"]), self.lang
            )
            direct = Candidate(
                packet,
                1.0,
                {
                    "source": "generic_learning_operation",
                    "captures": {"surface": target["surface"]},
                    "remaining_unknowns": [
                        item for item in top_unknown if item is not target
                    ],
                },
            )
            fallback, fallback_trace = self.settler.settle([direct], "L0")
            if fallback:
                packet, news = fallback
                evidence = {
                    **dict(target),
                    "learning_operation": "resolve_designation",
                    "probe_query": dict(packet["query"]),
                    "blocks": ["knowledge_binding"],
                    "priority": 1.0,
                }
                trace = {
                    "structured_prediction": True,
                    "clauses": [settle_trace, fallback_trace],
                    "n_best": True,
                    "resolved_form_lattice": resolved.as_dict(),
                    "delexicalized": delex,
                    "grounded_anchors": anchors,
                    "unknown_form_evidence": [evidence],
                    "skipped_clauses": [],
                    "interpretation_assessment": {
                        "status": "partial",
                        "grounded_refs": list(grounded_refs),
                        "open_variables": ["?q0", "?q1"],
                        "unresolved_evidence": [evidence],
                        "blockers": ["knowledge_binding"],
                    },
                    "state_projection_refs": sorted(
                        (state_projections or {}).keys()
                    ),
                    "side_effect_free": True,
                    "selected_candidate": {
                        "source": "generic_learning_operation",
                        "surface": target["surface"],
                    },
                    "candidate_count": len(candidates) + 1,
                }
                return packet, news, uses, trace

        trace = {
            "reason": "semantic_graph_unsettled",
            "structured_prediction": False,
            "clauses": [settle_trace],
            "n_best": True,
            "resolved_form_lattice": resolved.as_dict(),
            "delexicalized": delex,
            "grounded_anchors": anchors,
            "unknown_form_evidence": list(top_unknown),
            "skipped_clauses": [],
            "interpretation_assessment": {
                "status": "unresolved",
                "grounded_refs": list(grounded_refs),
                "open_variables": [],
                "unresolved_evidence": list(top_unknown),
                "blockers": ["semantic_graph_unsettled"],
            },
            "state_projection_refs": sorted((state_projections or {}).keys()),
            "side_effect_free": True,
            "candidate_count": len(candidates),
        }
        return None, [], uses, trace

    def parse(self, text, participant_frame: ParticipantFrame | None = None):
        """Pure diagnostic helper. Runtime uses observe then compose around Stage 4."""
        if participant_frame is None:
            raise ValueError("ParticipantFrame is required")
        lattice = self.observe(text, participant_frame)
        return self.compose(lattice, participant_frame, state_projections={})

    def delex_for_rule(self, text, participant_frame: ParticipantFrame | None = None):
        delex, placeholders, uses = self.delexer.run(text, participant_frame)
        # Rule induction expects local placeholders. The best hypothesis already
        # uses first-occurrence local numbering.
        return delex, placeholders, uses
