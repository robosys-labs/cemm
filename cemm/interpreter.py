"""Surface realization codec, contextual delexer and pure interpreter."""
from __future__ import annotations

import json
import re

from cemm.codec import StructuredSemanticCodec
from cemm.compiler import ExactStructuredCompiler
from cemm.config import Config
from cemm.context import ParticipantFrame
from cemm.model import AmbiguousReferent, norm_text, toks
from cemm.settler import SemanticSettler

try:
    import torch
    from torch import nn
except Exception as exc:
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
        hidden = self.enc(self.emb(values) + self.pos(positions), src_key_padding_mask=values.eq(0))
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
    values = torch.tensor([sequence + [0] * (maximum - len(sequence)) for sequence in sequences])
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
        self.meta, self.net = train_classifier(examples, "semantic", "surface_plan", 23, 110)
        self.allowed = {}
        for example in examples:
            self.allowed.setdefault(norm_text(example["semantic"]), set()).add(norm_text(example["surface_plan"]))

    @classmethod
    def get(cls, pack, cache=None):
        key = (pack.hash, "surface-v5")
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
        plan, confidence, margin, known = predict_classifier(self.meta, self.net, semantic)
        return plan, {
            "semantic": semantic,
            "surface_plan": plan,
            "confidence": confidence,
            "margin": margin,
            "known_token_ratio": known,
            "authorized_transform": norm_text(plan) in self.allowed.get(norm_text(semantic), set()),
        }


class Delexer:
    def __init__(self, store, language, authority_generation=None):
        self.s = store
        self.lang = language
        self.authority_generation = authority_generation
        self.salience = {
            row["atom_ref"]: float(row["salience"])
            for row in store.db.execute("SELECT * FROM discourse_entities")
        }

    def reference(self, surface, participant_frame: ParticipantFrame | None = None):
        rows = [
            row
            for row in self.s.db.execute(
                "SELECT * FROM reference_forms WHERE language IN (?, 'und') ORDER BY weight DESC",
                (self.lang,),
            ).fetchall()
            if norm_text(row["surface"]) == norm_text(surface)
        ]
        for row in rows:
            features = json.loads(row["features"])
            if participant_frame:
                resolved = participant_frame.resolve_requirement(features)
                if resolved:
                    return resolved
            # Bound references remain supported only for non-deictic reviewed forms.
            if row["bound_ref"] and not features.get("participant_role") and not features.get("person"):
                return str(row["bound_ref"])
            candidates = []
            required_type = features.get("required_type")
            typed = set()
            if required_type:
                from cemm.inference import Inference

                facts, _ = Inference(self.s, authority_generation=self.authority_generation).closure(
                    max_rounds=8, max_facts=500
                )
                typed = {
                    fact.args.get("role:instance")
                    for fact in facts
                    if fact.operator == "op:type"
                    and fact.stance == "support"
                    and fact.args.get("role:class") == required_type
                }
            for ref, score in self.salience.items():
                atom = self.s.atom(ref)
                metadata = {
                    key: value
                    for key, value in features.items()
                    if key not in {"kind", "required_type", "participant_role", "person", "possessive"}
                }
                if (
                    atom
                    and all(json.loads(atom["metadata"]).get(key) == value for key, value in metadata.items())
                    and (not features.get("kind") or atom["kind"] == features["kind"])
                    and (not required_type or ref in typed)
                ):
                    candidates.append((score, ref))
            candidates.sort(reverse=True)
            if candidates:
                if len(candidates) > 1 and candidates[0][0] - candidates[1][0] < 0.25:
                    raise AmbiguousReferent(
                        surface,
                        [{"ref": candidate[1], "score": candidate[0]} for candidate in candidates[:5]],
                    )
                return candidates[0][1]
        return None

    def run(self, text, participant_frame: ParticipantFrame | None = None):
        placeholder_map = {}
        reverse = {}
        uses = []
        next_index = 0
        output = []

        def placeholder(ref):
            nonlocal next_index
            if ref not in reverse:
                reverse[ref] = f"@A{next_index}"
                placeholder_map[reverse[ref]] = ref
                next_index += 1
            return reverse[ref]

        labels = self.s.db.execute(
            "SELECT DISTINCT surface FROM designation_index WHERE language IN (?, 'und') "
            "AND context_ref IS NULL ORDER BY length(surface) DESC",
            (self.lang,),
        ).fetchall()
        references = self.s.db.execute(
            "SELECT DISTINCT surface FROM reference_forms WHERE language IN (?, 'und') "
            "ORDER BY length(surface) DESC",
            (self.lang,),
        ).fetchall()
        for sentence in re.split(r"(?<=[.!?])\s+", text.strip()):
            candidates = []
            for kind, rows in (("ref", references), ("label", labels)):
                for row in rows:
                    phrase = str(row[0])
                    for match in re.finditer(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", sentence, flags=re.I):
                        candidates.append((match.start(), match.end(), kind, phrase))
            chosen = []
            for candidate in sorted(candidates, key=lambda item: (item[0], -(item[1] - item[0]), 0 if item[2] == "ref" else 1)):
                if not any(candidate[0] < other[1] and candidate[1] > other[0] for other in chosen):
                    chosen.append(candidate)
            position = 0
            pieces = []
            mentioned = []
            for start, end, kind, phrase in sorted(chosen):
                pieces.append(sentence[position:start])
                ref = (
                    self.reference(phrase, participant_frame)
                    if kind == "ref"
                    else self.s.resolve_label(phrase, self.lang)
                )
                if ref:
                    pieces.append(placeholder(ref))
                    mentioned.append(ref)
                    if kind == "label":
                        uses.append((phrase, ref))
                else:
                    pieces.append(sentence[start:end])
                position = end
            pieces.append(sentence[position:])
            output.append("".join(pieces))
            self.salience = {key: value * 0.55 for key, value in self.salience.items()}
            for ref in mentioned:
                self.salience[ref] = min(3, self.salience.get(ref, 0) + 1)
        return " ".join(output), placeholder_map, uses


class Interpreter:
    def __init__(self, store, pack, authority_generation=None, config=None):
        self.s = store
        self.pack = pack
        self.authority_generation = authority_generation
        self.config = config or Config()
        self.lang = pack.language
        self.codec = StructuredSemanticCodec(pack, self.config)
        self.compiler = ExactStructuredCompiler(store)
        self.settler = SemanticSettler(store, self.compiler, self.config)
        # Function-form authority is explicit language-package data, not an
        # accidental consequence of whichever examples happen to be present.
        self._function_words = {
            norm_text(value)
            for value in (pack.data.get("function_forms") or pack.data.get("grammar_tokens", []))
        }

    def _localize(self, clause, global_placeholders):
        order = []
        for placeholder in re.findall(r"@A\d+", clause):
            if placeholder not in order:
                order.append(placeholder)
        global_to_local = {value: f"@A{i}" for i, value in enumerate(order)}
        local = clause
        for global_placeholder, local_placeholder in sorted(global_to_local.items(), key=lambda item: -len(item[0])):
            local = local.replace(global_placeholder, local_placeholder)
        anchors = {
            local_placeholder: global_placeholders[global_placeholder]
            for global_placeholder, local_placeholder in global_to_local.items()
            if global_placeholder in global_placeholders
        }
        for placeholder, ref in anchors.items():
            atom = self.s.atom(ref)
            local = local.replace(placeholder, f"{placeholder}<{atom['kind'] if atom else 'atom'}>")
        return local, anchors

    def _known_surfaces(self):
        known = {
            norm_text(str(row[0]))
            for row in self.s.db.execute(
                "SELECT DISTINCT surface FROM designation_index WHERE language IN (?, 'und') AND context_ref IS NULL",
                (self.lang,),
            ).fetchall()
        }
        known.update(
            norm_text(str(row[0]))
            for row in self.s.db.execute(
                "SELECT DISTINCT surface FROM reference_forms WHERE language IN (?, 'und')",
                (self.lang,),
            ).fetchall()
        )
        return known

    def _find_unknown_surfaces(self, delex):
        known = self._known_surfaces()
        unknown = []
        seen = set()
        for match in re.finditer(r"[\wÀ-ÿ]+(?:[\wÀ-ÿ'-]*[\wÀ-ÿ])?", delex):
            word = match.group()
            if match.start() > 0 and delex[match.start() - 1] == "@":
                continue
            normalized = norm_text(word)
            if normalized in seen:
                continue
            seen.add(normalized)
            if normalized in known or normalized in self._function_words:
                continue
            unknown.append(word)
        return unknown

    def _candidate_unknown_kinds(self):
        kinds = set()
        for operator in self.pack.data.get("operators", []):
            for spec in self.s.roles(operator).values():
                expected = spec["filler_kind"]
                if expected == "state_value":
                    kinds.add("value")
                elif expected and expected not in {"atom", "app"} and not str(expected).startswith("literal:"):
                    kinds.add(str(expected))
        return sorted(kinds)

    def _unknown_form_trace(self, delex):
        candidates = self._candidate_unknown_kinds()
        return [
            {
                "surface": surface,
                "normalized": norm_text(surface),
                "semantic_kind_candidates": candidates,
            }
            for surface in self._find_unknown_surfaces(delex)
        ]

    @staticmethod
    def _clause_has_unknown(clause, unknown):
        normalized = {item["normalized"] for item in unknown}
        return any(
            norm_text(match.group()) in normalized
            for match in re.finditer(r"[\wÀ-ÿ]+(?:[\wÀ-ÿ'-]*[\wÀ-ÿ])?", clause)
        )

    def parse(self, text, participant_frame: ParticipantFrame | None = None):
        delex, global_placeholders, uses = Delexer(
            self.s, self.lang, self.authority_generation
        ).run(text, participant_frame)
        unknown = self._unknown_form_trace(delex)
        clauses = [
            clause.strip()
            for clause in re.split(r"(?<=[.!?])\s+", delex.strip())
            if clause.strip()
        ] or [delex]
        combined = {
            "force": None,
            "apps": [],
            "query": None,
            "directive": None,
            "describe": None,
        }
        news = []
        traces = []
        skipped = []
        for index, clause in enumerate(clauses):
            if self._clause_has_unknown(clause, unknown):
                skipped.append({"clause": clause, "reason": "unknown_form"})
                continue
            local, anchors = self._localize(clause, global_placeholders)
            candidates = self.codec.predict(
                local,
                anchors,
                self.s,
                top_k=10,
                participant_frame=participant_frame,
            )
            settled, trace = self.settler.settle(candidates, f"C{index}")
            trace["input"] = local
            traces.append(trace)
            if not settled:
                skipped.append({"clause": clause, "reason": "semantic_graph_unsettled", "trace": trace})
                continue
            packet, new_items = settled
            news += new_items
            force = packet.get("force")
            if combined["force"] and force != combined["force"]:
                return None, [], uses, {
                    "reason": "mixed_discourse_forces",
                    "clauses": traces,
                    "partial": bool(combined["apps"]),
                }
            combined["force"] = force
            if packet.get("query") or packet.get("describe") or packet.get("directive"):
                if len(clauses) > 1 or combined["apps"]:
                    return None, [], uses, {"reason": "mixed_embedded_act_not_yet_supported", "clauses": traces}
                combined.update(
                    {
                        "query": packet.get("query"),
                        "describe": packet.get("describe"),
                        "directive": packet.get("directive"),
                    }
                )
            else:
                combined["apps"].extend(packet.get("apps", []))

        stable = bool(combined["apps"] or combined["query"] or combined["describe"] or combined["directive"])
        status = "partial" if stable and (unknown or skipped) else "resolved" if stable else "unresolved"
        assessment = {
            "status": status,
            "grounded_refs": sorted(set(global_placeholders.values())),
            "unresolved_evidence": unknown,
            "blockers": sorted({item["reason"] for item in skipped}),
        }
        trace = {
            "structured_prediction": stable,
            "clauses": traces,
            "n_best": True,
            "delexicalized": delex,
            "grounded_anchors": dict(global_placeholders),
            "unknown_form_evidence": unknown,
            "skipped_clauses": skipped,
            "interpretation_assessment": assessment,
            "side_effect_free": True,
        }
        if not stable:
            trace["reason"] = "unknown_form" if unknown else "semantic_graph_unsettled"
            trace["learning_frontier"] = {"kind": trace["reason"], "items": unknown or skipped}
            return None, [], uses, trace
        return combined, news, uses, trace

    def delex_for_rule(self, text, participant_frame: ParticipantFrame | None = None):
        delex, placeholders, uses = Delexer(self.s, self.lang, self.authority_generation).run(
            text, participant_frame
        )
        return (*self._localize(delex, placeholders), uses)
