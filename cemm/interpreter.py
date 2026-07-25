"""Interpreter, SurfaceCodec, and Delexer for CEMM v1.

Ported from v4 MVP (cemm_mvp.py lines 275-440).

The Interpreter wires together the Delexer (surface -> delexicalized clauses),
the StructuredSemanticCodec (neural semantic prediction), the
ExactStructuredCompiler (exact validation), and the SemanticSettler (N-best
recurrent settling) to turn natural language into structured semantic packets.
"""
from __future__ import annotations

import json
import re

from cemm.config import Config
from cemm.store import Store
from cemm.codec import StructuredSemanticCodec
from cemm.compiler import ExactStructuredCompiler
from cemm.settler import SemanticSettler
from cemm.context import ParticipantFrame
from cemm.model import toks, norm_text, stable, lit, isvar, isexist, canonical, AmbiguousReferent

try:
    import torch
    from torch import nn
except Exception as exc:
    raise SystemExit("pip install torch") from exc

torch.set_num_threads(1)

# Module-level cache for trained surface classifiers (mirrors v4 MODEL_CACHE).
MODEL_CACHE: dict[tuple[str, str], "SurfaceCodec"] = {}


class TransformerClassifier(nn.Module):
    def __init__(self, vocab, ncls, d=48):
        super().__init__()
        self.emb = nn.Embedding(vocab, d, padding_idx=0)
        self.pos = nn.Embedding(128, d)
        layer = nn.TransformerEncoderLayer(d, 4, 96, dropout=0, batch_first=True)
        self.enc = nn.TransformerEncoder(layer, 1)
        self.out = nn.Linear(d, ncls)

    def forward(self, x):
        p = torch.arange(x.size(1), device=x.device)[None, :]
        h = self.enc(self.emb(x) + self.pos(p), src_key_padding_mask=x.eq(0))
        mask = x.ne(0).float().unsqueeze(-1)
        z = (h * mask).sum(1) / mask.sum(1).clamp_min(1)
        return self.out(z)


def train_classifier(examples, key, label_key, seed=11, epochs=120):
    labels = sorted({x[label_key] for x in examples})
    li = {x: i for i, x in enumerate(labels)}
    vocab = ["<pad>", "<unk>"] + sorted(
        {t.casefold() for x in examples for t in toks(x[key])}
    )
    vi = {x: i for i, x in enumerate(vocab)}
    seqs = [[vi.get(t.casefold(), 1) for t in toks(x[key])] for x in examples]
    m = max(map(len, seqs))
    X = torch.tensor([s + [0] * (m - len(s)) for s in seqs])
    Y = torch.tensor([li[x[label_key]] for x in examples])
    torch.manual_seed(seed)
    net = TransformerClassifier(len(vocab), len(labels))
    opt = torch.optim.AdamW(net.parameters(), lr=0.01)
    for _ in range(epochs):
        opt.zero_grad()
        loss = nn.functional.cross_entropy(net(X), Y)
        loss.backward()
        opt.step()
    net.eval()
    return {"labels": labels, "vi": vi, "train_texts": [x[key] for x in examples]}, net


def predict_classifier(meta, net, text):
    seq = [meta["vi"].get(t.casefold(), 1) for t in toks(text)]
    known = sum(i != 1 for i in seq) / max(1, len(seq))
    x = torch.tensor([seq or [1]])
    with torch.no_grad():
        p = torch.softmax(net(x), -1)[0]
        vals, idx = torch.topk(p, min(2, len(p)))
    label = meta["labels"][int(idx[0])]
    margin = float(vals[0] - (vals[1] if len(vals) > 1 else 0))
    return label, float(vals[0]), margin, known


class SurfaceCodec:
    def __init__(self, pack):
        ex = pack.data.get("realization_examples", [])
        self.meta, self.net = train_classifier(ex, "semantic", "surface_plan", 23, 110)
        self.allowed = {}
        for x in ex:
            self.allowed.setdefault(norm_text(x["semantic"]), set()).add(
                norm_text(x["surface_plan"])
            )

    @classmethod
    def get(cls, pack, cache=None):
        key = (pack.hash, "surface-v4")
        if cache is not None:
            existing = cache.get(key)
            if existing is not None:
                return existing
            val = cls(pack)
            cache.put(key, val)
            return val
        if key not in MODEL_CACHE:
            MODEL_CACHE[key] = cls(pack)
        return MODEL_CACHE[key]

    def realize(self, semantic):
        plan, p, m, k = predict_classifier(self.meta, self.net, semantic)
        authorized = norm_text(plan) in self.allowed.get(norm_text(semantic), set())
        return plan, {
            "semantic": semantic,
            "surface_plan": plan,
            "confidence": p,
            "margin": m,
            "known_token_ratio": k,
            "authorized_transform": authorized,
        }


class Delexer:
    def __init__(self, s, lang, authority_generation=None):
        self.s = s
        self.lang = lang
        self.authority_generation = authority_generation
        self.sal = {
            r["atom_ref"]: float(r["salience"])
            for r in s.db.execute("SELECT * FROM discourse_entities")
        }

    def reference(self, surf, participant_frame: ParticipantFrame | None = None):
        rows = [
            r
            for r in self.s.db.execute(
                "SELECT * FROM reference_forms WHERE language IN (?, 'und') ORDER BY weight DESC",
                (self.lang,),
            ).fetchall()
            if norm_text(r["surface"]) == norm_text(surf)
        ]
        for r in rows:
            f = json.loads(r["features"])
            if participant_frame:
                resolved = participant_frame.resolve_requirement(f)
                if resolved:
                    return resolved
            if r["bound_ref"]:
                return str(r["bound_ref"])
            cs = []
            required_type = f.get("required_type")
            typed = set()
            if required_type:
                from cemm.inference import Inference

                facts, _ = Inference(
                    self.s, authority_generation=self.authority_generation
                ).closure(max_rounds=8, max_facts=500)
                typed = {
                    x.args.get("role:instance")
                    for x in facts
                    if x.operator == "op:type"
                    and x.stance == "support"
                    and x.args.get("role:class") == required_type
                }
            for ref, score in self.sal.items():
                a = self.s.atom(ref)
                meta = {k: v for k, v in f.items() if k not in {"kind", "required_type"}}
                if a and all(
                    json.loads(a["metadata"]).get(k) == v for k, v in meta.items()
                ) and (not f.get("kind") or a["kind"] == f["kind"]) and (
                    not required_type or ref in typed
                ):
                    cs.append((score, ref))
            cs.sort(reverse=True)
            if cs:
                if len(cs) > 1 and cs[0][0] - cs[1][0] < 0.25:
                    raise AmbiguousReferent(
                        surf, [{"ref": x[1], "score": x[0]} for x in cs[:5]]
                    )
                return cs[0][1]
        return None

    def run(self, text, participant_frame: ParticipantFrame | None = None):
        phmap = {}
        rev = {}
        uses = []
        nexti = 0
        out = []

        def ph(ref):
            nonlocal nexti
            if ref not in rev:
                rev[ref] = f"@A{nexti}"
                phmap[rev[ref]] = ref
                nexti += 1
            return rev[ref]

        labels = self.s.db.execute(
            "SELECT DISTINCT surface FROM designation_index WHERE language IN (?, 'und') AND context_ref IS NULL ORDER BY length(surface) DESC",
            (self.lang,),
        ).fetchall()
        refs = self.s.db.execute(
            "SELECT DISTINCT surface FROM reference_forms WHERE language IN (?, 'und') ORDER BY length(surface) DESC",
            (self.lang,),
        ).fetchall()
        for sent in re.split(r"(?<=[.!?])\s+", text.strip()):
            cand = []
            for typ, rows in (("ref", refs), ("label", labels)):
                for row in rows:
                    q = str(row[0])
                    for m in re.finditer(
                        r"(?<!\w)" + re.escape(q) + r"(?!\w)", sent, flags=re.I
                    ):
                        cand.append((m.start(), m.end(), typ, q))
            chosen = []
            for c in sorted(
                cand, key=lambda x: (x[0], -(x[1] - x[0]), 0 if x[2] == "ref" else 1)
            ):
                if not any(c[0] < x[1] and c[1] > x[0] for x in chosen):
                    chosen.append(c)
            pos = 0
            pieces = []
            mentioned = []
            for a, b, typ, q in sorted(chosen):
                pieces.append(sent[pos:a])
                ref = self.reference(q, participant_frame) if typ == "ref" else self.s.resolve_label(q, self.lang)
                if ref:
                    pieces.append(ph(ref))
                    mentioned.append(ref)
                    uses.append((q, ref)) if typ == "label" else None
                else:
                    pieces.append(sent[a:b])
                pos = b
            pieces.append(sent[pos:])
            out.append("".join(pieces))
            self.sal = {k: v * 0.55 for k, v in self.sal.items()}
            for ref in mentioned:
                self.sal[ref] = min(3, self.sal.get(ref, 0) + 1)
        return " ".join(out), phmap, uses


class Interpreter:
    def __init__(self, s, pack, authority_generation=None, config=None):
        self.s = s
        self.pack = pack
        self.authority_generation = authority_generation
        self.config = config or Config()
        self.lang = pack.language
        self.codec = StructuredSemanticCodec(pack, self.config)
        self.compiler = ExactStructuredCompiler(s)
        self.settler = SemanticSettler(s, self.compiler, self.config)
        # Build function-word set from training examples: words that appear in
        # training inputs as raw text (not placeholders) are syntactic markers,
        # not content words to be acquired.
        self._function_words = set()
        d = pack.data if hasattr(pack, "data") else pack
        for ex in d.get("structured_examples", []) + d.get("rule_examples", []):
            for m in re.finditer(r"[\wÀ-ÿ]+(?:[\wÀ-ÿ'-]*[\wÀ-ÿ])?", ex.get("input", "")):
                word = m.group()
                if not word.startswith("@"):
                    self._function_words.add(norm_text(word))

    def _localize(self, clause, global_ph):
        order = []
        for g in re.findall(r"@A\d+", clause):
            if g not in order:
                order.append(g)
        g2l = {g: f"@A{i}" for i, g in enumerate(order)}
        local = clause
        for g, l in sorted(g2l.items(), key=lambda x: -len(x[0])):
            local = local.replace(g, l)
        anchors = {l: global_ph[g] for g, l in g2l.items() if g in global_ph}
        for l, ref in anchors.items():
            a = self.s.atom(ref)
            kind = a["kind"] if a else "atom"
            local = local.replace(l, f"{l}<{kind}>")
        return local, anchors

    def _find_unknown_surfaces(self, delex):
        """Find content-word tokens in delexicalized text that have no designation.

        Scans the delexicalized text for word tokens that are not placeholders,
        not function words (syntactic markers from training examples), and not
        already known via designation_index or reference_forms.
        """
        # Gather all known surfaces (normalized)
        known = set()
        for r in self.s.db.execute(
            "SELECT DISTINCT surface FROM designation_index "
            "WHERE language IN (?, 'und') AND context_ref IS NULL",
            (self.lang,),
        ).fetchall():
            known.add(norm_text(str(r[0])))
        for r in self.s.db.execute(
            "SELECT DISTINCT surface FROM reference_forms "
            "WHERE language IN (?, 'und')",
            (self.lang,),
        ).fetchall():
            known.add(norm_text(str(r[0])))
        unknown = []
        seen = set()
        for m in re.finditer(r"[\wÀ-ÿ]+(?:[\wÀ-ÿ'-]*[\wÀ-ÿ])?", delex):
            word = m.group()
            # Regex word matching starts after '@', so explicitly ignore
            # placeholder bodies such as A0/A1.
            if word.startswith("@") or (m.start() > 0 and delex[m.start() - 1] == "@"):
                continue
            nw = norm_text(word)
            if nw in seen:
                continue
            seen.add(nw)
            if nw in known or nw in self._function_words:
                continue
            unknown.append(word)
        return unknown

    def _candidate_unknown_kinds(self):
        kinds = set()
        for op in self.pack.data.get("operators", []):
            for spec in self.s.roles(op).values():
                exp = spec["filler_kind"]
                if exp == "state_value":
                    kinds.add("value")
                elif exp and exp not in {"atom", "app"} and not str(exp).startswith("literal:"):
                    kinds.add(str(exp))
        return sorted(kinds)

    def _unknown_form_trace(self, delex):
        """Return cycle-local unknown-form evidence; never mutate the store."""
        unknown = self._find_unknown_surfaces(delex)
        candidates = self._candidate_unknown_kinds()
        return [
            {
                "surface": surf,
                "normalized": norm_text(surf),
                "semantic_kind_candidates": candidates,
            }
            for surf in unknown
        ]

    def parse(self, text, participant_frame: ParticipantFrame | None = None):
        delex, ph, uses = Delexer(self.s, self.lang, self.authority_generation).run(text, participant_frame)
        unknown = self._unknown_form_trace(delex)
        if unknown:
            return None, [], uses, {
                "reason": "unknown_form",
                "unknown_form_evidence": unknown,
                "semantic_kind_candidate_set": sorted({k for item in unknown for k in item["semantic_kind_candidates"]}),
                "learning_frontier": {"kind": "unknown_form", "items": unknown},
                "side_effect_free": True,
            }
        clauses = [
            x.strip() for x in re.split(r"(?<=[.!?])\s+", delex.strip()) if x.strip()
        ]
        combined = {"apps": [], "query": None, "describe": None}
        news = []
        traces = []
        for i, clause in enumerate(clauses or [delex]):
            local, anchors = self._localize(clause, ph)
            cands = self.codec.predict(local, anchors, self.s, top_k=10, participant_frame=participant_frame)
            settled, trace = self.settler.settle(cands, f"C{i}")
            trace["input"] = local
            traces.append(trace)
            if not settled:
                return None, [], uses, {"reason": "semantic_graph_unsettled", "clauses": traces}
            pkt, nw = settled
            news += nw
            if pkt.get("query") or pkt.get("describe"):
                if len(clauses) > 1 or combined["apps"]:
                    return None, [], uses, {"reason": "mixed_query_document", "clauses": traces}
                combined["query"], combined["describe"] = pkt.get("query"), pkt.get("describe")
            else:
                combined["apps"].extend(pkt.get("apps", []))
        return combined, news, uses, {"structured_prediction": True, "clauses": traces, "n_best": True}

    def delex_for_rule(self, text, participant_frame: ParticipantFrame | None = None):
        delex, ph, uses = Delexer(self.s, self.lang, self.authority_generation).run(text, participant_frame)
        return (*self._localize(delex, ph), uses)

