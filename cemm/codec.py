"""Open compositional semantic codec for CEMM v1.

Ported from v4 MVP (reference/mvp_v4/structured_codec.py).

No closed semantic-program classes are predicted.  The neural model predicts:
- intent (assert/query/describe)
- application-slot presence
- operator per slot
- role -> grounded-source bindings per slot

A separate structured rule model predicts antecedent/consequent graph slots using
variables/existentials/grounded anchors.  Exact semantic validation remains outside
these models.
"""
from __future__ import annotations

import itertools
import math
from dataclasses import dataclass
from typing import Any

from cemm.config import Config

# NOTE: v4's structured_codec.py uses its own TOK regex that handles @A1<entity>
# style anchors, which differs from cemm.model.toks. We keep the codec's original
# tokenizer to preserve training behavior.
import re as _re
_TOK = _re.compile(r"@[A-Z]\d+<[^>]+>|@[A-Z]\d+|<[A-Za-z0-9_:.=-]+>|[\wÀ-ÿ:/?.!'-]+|[^\s]", _re.UNICODE)
def toks(s): return _TOK.findall(str(s))

try:
    import torch
    from torch import nn
except Exception as exc:
    raise SystemExit("pip install torch") from exc

torch.set_num_threads(1)

MAX_APPS = 3
MAX_RULE_IF = 3
MAX_RULE_THEN = 3
CACHE: dict[tuple[str, str], tuple[Any, Any]] = {}


def logp(x):
    return math.log(max(1e-9, float(x)))


class Encoder(nn.Module):
    def __init__(self, vocab, d=64):
        super().__init__()
        self.emb = nn.Embedding(vocab, d, padding_idx=0)
        self.pos = nn.Embedding(160, d)
        layer = nn.TransformerEncoderLayer(d, 4, 128, dropout=0, batch_first=True)
        self.enc = nn.TransformerEncoder(layer, 2)

    def forward(self, x):
        p = torch.arange(x.size(1), device=x.device)[None, :]
        h = self.enc(self.emb(x) + self.pos(p), src_key_padding_mask=x.eq(0))
        m = x.ne(0).float().unsqueeze(-1)
        return (h * m).sum(1) / m.sum(1).clamp_min(1)


class StructuredNet(nn.Module):
    def __init__(self, vocab, nops, nroles, nsrc, d=64):
        super().__init__()
        self.enc = Encoder(vocab, d)
        self.intent = nn.Linear(d, 3)
        self.pres = nn.Linear(d, MAX_APPS * 2)
        self.ops = nn.Linear(d, MAX_APPS * nops)
        self.bind = nn.Linear(d, MAX_APPS * nroles * nsrc)
        self.describe = nn.Linear(d, nsrc)
        self.nops = nops
        self.nroles = nroles
        self.nsrc = nsrc

    def forward(self, x):
        z = self.enc(x)
        return (
            self.intent(z),
            self.pres(z).view(-1, MAX_APPS, 2),
            self.ops(z).view(-1, MAX_APPS, self.nops),
            self.bind(z).view(-1, MAX_APPS, self.nroles, self.nsrc),
            self.describe(z),
        )


class RuleNet(nn.Module):
    def __init__(self, vocab, nops, nroles, nsrc, d=64):
        super().__init__()
        self.enc = Encoder(vocab, d)
        self.kind = nn.Linear(d, 2)
        self.ip = nn.Linear(d, MAX_RULE_IF * 2)
        self.io = nn.Linear(d, MAX_RULE_IF * nops)
        self.ib = nn.Linear(d, MAX_RULE_IF * nroles * nsrc)
        self.tp = nn.Linear(d, MAX_RULE_THEN * 2)
        self.to_head = nn.Linear(d, MAX_RULE_THEN * nops)
        self.tb = nn.Linear(d, MAX_RULE_THEN * nroles * nsrc)
        self.nops = nops
        self.nroles = nroles
        self.nsrc = nsrc

    def forward(self, x):
        z = self.enc(x)
        return (
            self.kind(z),
            self.ip(z).view(-1, MAX_RULE_IF, 2),
            self.io(z).view(-1, MAX_RULE_IF, self.nops),
            self.ib(z).view(-1, MAX_RULE_IF, self.nroles, self.nsrc),
            self.tp(z).view(-1, MAX_RULE_THEN, 2),
            self.to_head(z).view(-1, MAX_RULE_THEN, self.nops),
            self.tb(z).view(-1, MAX_RULE_THEN, self.nroles, self.nsrc),
        )


@dataclass
class Candidate:
    packet: dict[str, Any]
    score: float
    trace: dict[str, Any]


class StructuredSemanticCodec:
    INTENTS = ["assert", "query", "describe"]
    RULE_KINDS = ["definition", "entailment"]

    def __init__(self, pack, config=None, epochs=260):
        self.config = config or Config()
        self.pack = pack
        d = pack.data if hasattr(pack, "data") else pack
        self.sources = d["source_classes"]
        self.rsrc = d["rule_sources"]
        self.ops = d["operators"]
        self.roles = d["roles"]
        self.si = {x: i for i, x in enumerate(self.sources)}
        self.rsi = {x: i for i, x in enumerate(self.rsrc)}
        self.oi = {x: i for i, x in enumerate(self.ops)}
        self.ri = {x: i for i, x in enumerate(self.roles)}
        texts = [x["input"] for x in d.get("structured_examples", [])] + [
            x["input"] for x in d.get("rule_examples", [])
        ]
        vocab = ["<pad>", "<unk>"] + sorted(
            {t.casefold() for x in texts for t in toks(x)}
        )
        self.vi = {x: i for i, x in enumerate(vocab)}
        key = (d["pack_hash"], "structured-v4")
        if key in CACHE:
            self.net, self.rnet = CACHE[key]
        else:
            self.net = self._train_struct(d.get("structured_examples", []), epochs)
            self.rnet = (
                self._train_rules(d.get("rule_examples", []), max(epochs, 320))
                if d.get("rule_examples")
                else None
            )
            CACHE[key] = (self.net, self.rnet)

    def _tensor(self, texts):
        seqs = [
            [self.vi.get(t.casefold(), 1) for t in toks(x)] or [1] for x in texts
        ]
        m = max(map(len, seqs))
        return torch.tensor([s + [0] * (m - len(s)) for s in seqs])

    def _train_struct(self, ex, epochs):
        torch.manual_seed(self.config.structured_net_seed)
        net = StructuredNet(
            len(self.vi), len(self.ops), len(self.roles), len(self.sources)
        )
        opt = torch.optim.AdamW(net.parameters(), lr=0.008, weight_decay=1e-4)
        X = self._tensor([x["input"] for x in ex])
        intents = []
        pres = []
        ops = []
        bind = []
        desc = []
        for x in ex:
            t = x["target"]
            intents.append(self.INTENTS.index(t["intent"]))
            ps = []
            os = []
            bs = []
            for j in range(MAX_APPS):
                a = t.get("apps", [])[j] if j < len(t.get("apps", [])) else None
                ps.append(1 if a else 0)
                os.append(self.oi.get(a["operator"], 0) if a else 0)
                row = []
                for r in self.roles:
                    row.append(
                        self.si.get(a.get("bindings", {}).get(r, "NONE"), 0)
                        if a
                        else 0
                    )
                bs.append(row)
            pres.append(ps)
            ops.append(os)
            bind.append(bs)
            desc.append(self.si.get(t.get("describe_source", "NONE"), 0))
        YI = torch.tensor(intents)
        YP = torch.tensor(pres)
        YO = torch.tensor(ops)
        YB = torch.tensor(bind)
        YD = torch.tensor(desc)
        for _ in range(epochs):
            opt.zero_grad()
            i, p, o, b, d = net(X)
            loss = (
                nn.functional.cross_entropy(i, YI)
                + 0.8 * nn.functional.cross_entropy(p.reshape(-1, 2), YP.reshape(-1))
                + 0.7 * nn.functional.cross_entropy(d, YD)
            )
            mask = YP.reshape(-1).bool()
            if mask.any():
                loss += nn.functional.cross_entropy(
                    o.reshape(-1, len(self.ops))[mask], YO.reshape(-1)[mask]
                )
            # Role NONE is useful but should not dominate grounded-role supervision.
            logits = b.reshape(-1, len(self.sources))
            targets = YB.reshape(-1)
            weights = torch.ones_like(targets, dtype=torch.float)
            weights[targets == self.si["NONE"]] = 0.12
            ce = nn.functional.cross_entropy(logits, targets, reduction="none")
            loss += (ce * weights).sum() / weights.sum().clamp_min(1)
            loss.backward()
            opt.step()
        net.eval()
        return net

    def _train_rules(self, ex, epochs):
        torch.manual_seed(self.config.rule_net_seed)
        net = RuleNet(len(self.vi), len(self.ops), len(self.roles), len(self.rsrc))
        opt = torch.optim.AdamW(net.parameters(), lr=0.008, weight_decay=1e-4)
        X = self._tensor([x["input"] for x in ex])
        kinds = []
        ips = []
        ios = []
        ibs = []
        tps = []
        tos = []
        tbs = []
        for x in ex:
            t = x["target"]
            kinds.append(self.RULE_KINDS.index(t.get("rule_kind", "definition")))

            def side(name, maxn):
                ps = []
                os = []
                bs = []
                for j in range(maxn):
                    a = t.get(name, [])[j] if j < len(t.get(name, [])) else None
                    ps.append(1 if a else 0)
                    os.append(self.oi.get(a["operator"], 0) if a else 0)
                    bs.append(
                        [
                            self.rsi.get(a.get("bindings", {}).get(r, "NONE"), 0)
                            if a
                            else 0
                            for r in self.roles
                        ]
                    )
                return ps, os, bs

            a, b, c = side("if", MAX_RULE_IF)
            ips.append(a)
            ios.append(b)
            ibs.append(c)
            a, b, c = side("then", MAX_RULE_THEN)
            tps.append(a)
            tos.append(b)
            tbs.append(c)
        YK = torch.tensor(kinds)
        YIP = torch.tensor(ips)
        YIO = torch.tensor(ios)
        YIB = torch.tensor(ibs)
        YTP = torch.tensor(tps)
        YTO = torch.tensor(tos)
        YTB = torch.tensor(tbs)
        for _ in range(epochs):
            opt.zero_grad()
            k, ip, io, ib, tp, to, tb = net(X)
            loss = nn.functional.cross_entropy(k, YK)
            for p, o, b, yp, yo, yb in (
                (ip, io, ib, YIP, YIO, YIB),
                (tp, to, tb, YTP, YTO, YTB),
            ):
                loss += nn.functional.cross_entropy(p.reshape(-1, 2), yp.reshape(-1))
                mask = yp.reshape(-1).bool()
                if mask.any():
                    loss += nn.functional.cross_entropy(
                        o.reshape(-1, len(self.ops))[mask], yo.reshape(-1)[mask]
                    )
                logits = b.reshape(-1, len(self.rsrc))
                targets = yb.reshape(-1)
                w = torch.ones_like(targets, dtype=torch.float)
                w[targets == self.rsi["NONE"]] = 0.1
                loss += (
                    nn.functional.cross_entropy(logits, targets, reduction="none") * w
                ).sum() / w.sum().clamp_min(1)
            loss.backward()
            opt.step()
        net.eval()
        return net

    def _x(self, text):
        return self._tensor([text])

    def _source_value(self, s, anchors, participant_frame=None):
        if s == "NONE":
            return None
        # USER/SYSTEM remain accepted only as compatibility aliases for frozen
        # v4-derived packs. Their runtime meaning is contextual, not lexical.
        if s in {"FRAME_SPEAKER", "USER"}:
            return participant_frame.speaker_ref if participant_frame else "participant:user"
        if s in {"FRAME_ADDRESSEE", "SYSTEM"}:
            return participant_frame.addressee_ref if participant_frame else "participant:system"
        if s.startswith("A"):
            return anchors.get("@" + s)
        if s.startswith("NEW_ENTITY_"):
            return {
                "new": "@X_ENTITY_" + s.rsplit("_", 1)[-1],
                "kind": "entity",
            }
        if s.startswith("NEW_EVENT_"):
            return {"new": "@X_EVENT_" + s.rsplit("_", 1)[-1], "kind": "event"}
        return None

    def _kind_ok(self, store, role_spec, v):
        if v is None:
            return False
        exp = role_spec["filler_kind"]
        if exp == "state_value":
            if isinstance(v, dict) and "new" in v:
                return True
            if isinstance(v, dict) and ("literal" in v or "app" in v):
                return True
            return bool(isinstance(v, str) and store.atom(v))
        if isinstance(v, dict) and "new" in v:
            return exp in {None, "atom", v["kind"]} or (exp == "atom")
        if isinstance(v, dict) and "literal" in v:
            return bool(exp and exp.startswith("literal:"))
        a = store.atom(v) if isinstance(v, str) else None
        return bool(a and (not exp or exp == "atom" or a["kind"] == exp))

    def _choose_source(self, probs, store, spec, anchors, participant_frame=None, allow_none=True, alt=0):
        vals = torch.argsort(probs, descending=True).tolist()
        valid = []
        for ix in vals:
            s = self.sources[ix]
            if s == "NONE" and allow_none:
                valid.append((s, float(probs[ix])))
                continue
            v = self._source_value(s, anchors, participant_frame)
            if self._kind_ok(store, spec, v):
                valid.append((s, float(probs[ix])))
        return valid[min(alt, len(valid) - 1)] if valid else ("NONE", 0.0)

    def predict(self, text, anchors, store, top_k=8, participant_frame=None):
        with torch.no_grad():
            ii, pp, oo, bb, dd = self.net(self._x(text))
            ii = torch.softmax(ii[0], -1)
            pp = torch.softmax(pp[0], -1)
            oo = torch.softmax(oo[0], -1)
            bb = torch.softmax(bb[0], -1)
            dd = torch.softmax(dd[0], -1)
        intent_ids = torch.topk(ii, min(2, len(ii))).indices.tolist()
        cands = []
        for iid in intent_ids:
            intent = self.INTENTS[iid]
            base = logp(ii[iid])
            if intent == "describe":
                for sx in torch.topk(dd, min(3, len(dd))).indices.tolist():
                    s = self.sources[sx]
                    v = self._source_value(s, anchors, participant_frame)
                    if v and not isinstance(v, dict):
                        cands.append(
                            Candidate(
                                {"apps": [], "query": None, "describe": v},
                                base + logp(dd[sx]),
                                {"intent": intent, "source": s},
                            )
                        )
                continue
            # Presence profile + one looser alternative gives N-best topology without program classes.
            profiles = []
            for threshold in (0.52, 0.30):
                active = [j for j in range(MAX_APPS) if float(pp[j, 1]) >= threshold]
                if not active:
                    active = [0]
                profile = tuple(active)
                if profile not in profiles:
                    profiles.append(profile)
            for active in profiles:
                op_choices = [
                    torch.topk(oo[j], min(2, len(self.ops))).indices.tolist()
                    for j in active
                ]
                for opids in itertools.product(*op_choices):
                    apps = []
                    score = base
                    ok = True
                    for j, oid in zip(active, opids):
                        op = self.ops[oid]
                        specs = store.roles(op)
                        args = {}
                        score += logp(pp[j, 1]) + logp(oo[j, oid])
                        for r, spec in specs.items():
                            if r not in self.ri:
                                if spec["required"] and not (
                                    op == "op:state" and r == "role:dimension"
                                ):
                                    ok = False
                                continue
                            rp = bb[j, self.ri[r]]
                            src, p = self._choose_source(
                                rp,
                                store,
                                spec,
                                anchors,
                                participant_frame,
                                allow_none=not bool(spec["required"]),
                            )
                            v = self._source_value(src, anchors, participant_frame)
                            if src != "NONE" and v is not None:
                                args[r] = v
                                score += logp(p)
                            elif spec["required"] and not (
                                op == "op:state" and r == "role:dimension"
                            ):
                                ok = False
                        if ok:
                            apps.append(
                                {"operator": op, "args": args, "stance": "support"}
                            )
                    if not ok:
                        continue
                    pkt = {
                        "apps": apps if intent == "assert" else [],
                        "query": apps[0] if intent == "query" and apps else None,
                        "describe": None,
                    }
                    cands.append(
                        Candidate(
                            pkt,
                            score,
                            {
                                "intent": intent,
                                "active_slots": active,
                                "operators": [self.ops[x] for x in opids],
                            },
                        )
                    )
        cands.sort(key=lambda c: c.score, reverse=True)
        return cands[:top_k]

    def predict_rules(self, text, anchors, store, top_k=5):
        if self.rnet is None:
            return []
        with torch.no_grad():
            k, ip, io, ib, tp, to, tb = self.rnet(self._x(text))
            k = torch.softmax(k[0], -1)
            ip = torch.softmax(ip[0], -1)
            io = torch.softmax(io[0], -1)
            ib = torch.softmax(ib[0], -1)
            tp = torch.softmax(tp[0], -1)
            to = torch.softmax(to[0], -1)
            tb = torch.softmax(tb[0], -1)

        def srcval(s):
            if s.startswith("A"):
                return anchors.get("@" + s)
            if s.startswith("V"):
                return "?v" + s[1:]
            if s.startswith("E"):
                return "!e" + s[1:]
            return None

        out = []
        for kid in torch.topk(k, min(2, len(k))).indices.tolist():
            kind = self.RULE_KINDS[kid]
            score = logp(k[kid])
            sides = []
            valid = True
            for pres, ops, bind, maxn in (
                (ip, io, ib, MAX_RULE_IF),
                (tp, to, tb, MAX_RULE_THEN),
            ):
                side = []
                for j in range(maxn):
                    if float(pres[j, 1]) < 0.45:
                        continue
                    oid = int(torch.argmax(ops[j]))
                    op = self.ops[oid]
                    specs = store.roles(op)
                    args = {}
                    score += logp(pres[j, 1]) + logp(ops[j, oid])
                    for r, spec in specs.items():
                        if r not in self.ri:
                            if spec["required"]:
                                valid = False
                            continue
                        rp = bind[j, self.ri[r]]
                        picked = None
                        for sx in torch.argsort(rp, descending=True).tolist():
                            s = self.rsrc[sx]
                            v = srcval(s)
                            if s == "NONE" and not spec["required"]:
                                picked = (None, float(rp[sx]))
                                break
                            if isinstance(v, str) and (
                                v.startswith("?") or v.startswith("!")
                            ):
                                picked = (v, float(rp[sx]))
                                break
                            if v and self._kind_ok(store, spec, v):
                                picked = (v, float(rp[sx]))
                                break
                        if picked and picked[0] is not None:
                            args[r] = picked[0]
                            score += logp(picked[1])
                        elif spec["required"]:
                            valid = False
                    side.append({"operator": op, "args": args})
                sides.append(side)
            if valid and sides[0] and sides[1]:
                out.append(
                    {"rule_kind": kind, "if": sides[0], "then": sides[1], "score": score}
                )
        return sorted(out, key=lambda x: x["score"], reverse=True)[:top_k]
