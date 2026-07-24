"""Bounded semantic workspace for CEMM v1.

Ported from v4 MVP (cemm_mvp.py lines 517-556).

The Workspace selects a bounded set of salient facts (plus session self-state
slots) to keep in attention for the current turn. A small transformer ranks
candidate facts by overlap with the query, self-reference, confidence,
derived-ness, discourse salience, and recency.

Weakness #5 (synthetic training): The workspace ranking model is trained on
synthetically generated feature vectors with hand-tuned weights. This is
sufficient for the MVP but production deployments should retrain on real
semantic attention patterns gathered from actual discourse before relying on
the ranking for user-facing behavior.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

from cemm.config import Config
from cemm.store import Store
from cemm.selfstate import SessionSelf
from cemm.model import norm_text, toks, stable, canonical, Fact

try:
    import torch
    from torch import nn
except Exception as exc:
    raise SystemExit("pip install torch") from exc

torch.set_num_threads(1)

# Module-level cache for the workspace ranking net (mirrors v4 MODEL_CACHE).
MODEL_CACHE: dict[str, "WorkspaceNet"] = {}


@dataclass
class WorkspaceSlot:
    ref: str
    fact: Fact
    score: float
    features: dict[str, float]


class WorkspaceNet(nn.Module):
    def __init__(self, d=24):
        super().__init__()
        self.proj = nn.Linear(6, d)
        layer = nn.TransformerEncoderLayer(d, 4, 48, dropout=0, batch_first=True)
        self.enc = nn.TransformerEncoder(layer, 1)
        self.out = nn.Linear(d, 1)

    def forward(self, x):
        return self.out(self.enc(self.proj(x))).squeeze(-1)


def workspace_model():
    k = "workspace-v3"
    if k in MODEL_CACHE:
        return MODEL_CACHE[k]
    torch.manual_seed(7)
    random.seed(7)
    net = WorkspaceNet()
    opt = torch.optim.AdamW(net.parameters(), lr=0.01)
    X = []
    Y = []
    for _ in range(96):
        seq = []
        target = []
        for _j in range(8):
            overlap = random.random()
            selfish = random.choice([0.0, 1.0])
            conf = random.uniform(0.5, 1)
            derived = random.choice([0.0, 1.0])
            sal = random.random()
            recent = random.random()
            seq.append([overlap, selfish, conf, derived, sal, recent])
            target.append(
                2.4 * overlap
                + 0.7 * selfish
                + 0.35 * conf
                + 0.25 * sal
                + 0.15 * recent
                - 0.08 * derived
            )
        X.append(seq)
        Y.append(target)
    X = torch.tensor(X, dtype=torch.float32)
    Y = torch.tensor(Y, dtype=torch.float32)
    for _ in range(55):
        opt.zero_grad()
        q = net(X)
        loss = nn.functional.mse_loss(q, Y)
        loss.backward()
        opt.step()
    net.eval()
    MODEL_CACHE[k] = net
    return net


class Workspace:
    def __init__(self, s: Store, selfstate: SessionSelf, config: Config | None = None):
        self.s = s
        self.selfstate = selfstate
        self.config = config or Config()
        self.top_k = self.config.workspace_top_k

    def build(self, facts, query=None, proof_refs=()):
        context = {self.s.symbol("self.ref")}
        if query:
            for v in query.get("args", {}).values():
                if isinstance(v, str):
                    context.add(v)
        discourse = {
            r["atom_ref"]: (float(r["salience"]), int(r["last_turn"]))
            for r in self.s.db.execute("SELECT * FROM discourse_entities")
        }
        allfacts = list(facts) + self.selfstate.slots()
        vecs = []
        for f in allfacts:
            refs = {f.operator} | {
                str(v) for v in f.args.values() if isinstance(v, str)
            }
            overlap = len(refs & context) / max(1, len(context))
            selfish = float(self.s.symbol("self.ref") in refs)
            sal = max([discourse.get(r, (0, 0))[0] for r in refs] or [0])
            recent = max([discourse.get(r, (0, 0))[1] for r in refs] or [0])
            vecs.append(
                [
                    overlap,
                    selfish,
                    float(f.confidence),
                    float(f.derived),
                    min(1, sal / 3),
                    1 / (1 + max(0, self.selfstate.turn - recent)),
                ]
            )
        if not vecs:
            return [], {"selected": [], "top_k": self.top_k}
        model = workspace_model()
        with torch.no_grad():
            scores = model(torch.tensor([vecs], dtype=torch.float32))[0].tolist()
        hard = set(proof_refs)
        ranked = sorted(
            zip(allfacts, scores, vecs),
            key=lambda x: (x[0].ref not in hard, -x[1], x[0].ref),
        )
        selected = []
        for f, score, v in ranked:
            if len(selected) >= self.top_k and f.ref not in hard:
                continue
            selected.append(
                WorkspaceSlot(
                    f.ref,
                    f,
                    float(score),
                    {
                        "overlap": v[0],
                        "self": v[1],
                        "confidence": v[2],
                        "derived": v[3],
                        "salience": v[4],
                        "recency": v[5],
                    },
                )
            )
        return selected, {
            "top_k": self.top_k,
            "selected": [
                {
                    "ref": x.ref,
                    "operator": x.fact.operator,
                    "score": round(x.score, 4),
                    "features": x.features,
                }
                for x in selected
            ],
        }
