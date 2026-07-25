"""Bounded active semantic workspace for CEMM v1.

Runtime/cognitive bookkeeping is supplied as typed cycle artifacts and is never
injected into world semantics as synthetic self-state facts.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

from cemm.config import Config
from cemm.model import Fact

try:
    import torch
    from torch import nn
except Exception as exc:
    raise SystemExit("pip install torch") from exc

torch.set_num_threads(1)


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


def workspace_model(cache):
    if cache is None:
        raise ValueError("Workspace requires the Runtime-owned bounded model cache")
    key = "workspace-v1-final"
    existing = cache.get(key)
    if existing is not None:
        return existing
    torch.manual_seed(7)
    random.seed(7)
    net = WorkspaceNet()
    optimizer = torch.optim.AdamW(net.parameters(), lr=0.01)
    # Train once at runtime construction from structural relevance signals.
    x_train, y_train = [], []
    for _ in range(96):
        sequence, target = [], []
        for _slot in range(8):
            overlap = random.random()
            self_relevance = random.choice([0.0, 1.0])
            confidence = random.uniform(0.5, 1.0)
            derived = random.choice([0.0, 1.0])
            salience = random.random()
            recency = random.random()
            sequence.append([overlap, self_relevance, confidence, derived, salience, recency])
            target.append(2.4*overlap + 0.7*self_relevance + 0.35*confidence + 0.25*salience + 0.15*recency - 0.08*derived)
        x_train.append(sequence); y_train.append(target)
    values = torch.tensor(x_train, dtype=torch.float32)
    targets = torch.tensor(y_train, dtype=torch.float32)
    for _ in range(55):
        optimizer.zero_grad(); loss = nn.functional.mse_loss(net(values), targets); loss.backward(); optimizer.step()
    net.eval(); cache.put(key, net); return net


class Workspace:
    def __init__(self, store, config: Config | None = None, cache=None):
        self.s = store
        self.config = config or Config()
        self.top_k = self.config.workspace_top_k
        self.cache = cache

    @staticmethod
    def _query_values(query):
        if not query:
            return []
        if query.get("operator"):
            raise ValueError("workspace queries require QueryStructure.restrictions")
        restrictions = query.get("restrictions", ())
        return [
            value
            for restriction in restrictions
            for value in restriction.get("args", {}).values()
            if isinstance(value, str) and not value.startswith("?")
        ]

    def build(self, facts, query=None, proof_refs=(), required_facts=(), cycle_turn=0):
        context = {self.s.symbol("self.ref"), *self._query_values(query)}
        discourse = {
            row["atom_ref"]: (float(row["salience"]), int(row["last_turn"]))
            for row in self.s.db.execute(
                "SELECT * FROM discourse_entities ORDER BY last_turn DESC,salience DESC LIMIT ?",
                (self.top_k * 4,),
            )
        }
        all_facts = list(facts)
        existing = {fact.ref for fact in all_facts}
        required_facts = tuple(required_facts)[: self.config.workspace_max_required]
        all_facts.extend(fact for fact in required_facts if fact.ref not in existing)
        vectors = []
        for fact in all_facts:
            refs = {fact.operator} | {
                str(value) for value in fact.args.values() if isinstance(value, str)
            }
            overlap = len(refs & context) / max(1, len(context))
            self_relevance = float(self.s.symbol("self.ref") in refs)
            salience = max([discourse.get(ref, (0, 0))[0] for ref in refs] or [0])
            last_turn = max([discourse.get(ref, (0, 0))[1] for ref in refs] or [0])
            vectors.append(
                [
                    overlap,
                    self_relevance,
                    float(fact.confidence),
                    float(fact.derived),
                    min(1, salience / 3),
                    1 / (1 + max(0, cycle_turn - last_turn)),
                ]
            )
        if not vectors:
            return [], {"selected": [], "top_k": self.top_k}
        model = workspace_model(self.cache)
        with torch.no_grad():
            scores = model(torch.tensor([vectors], dtype=torch.float32))[0].tolist()
        hard_ordered = sorted(set(proof_refs) | {fact.ref for fact in required_facts})
        hard = set(hard_ordered[: self.config.workspace_max_required])
        if len(hard) > self.config.workspace_max_required:
            raise ValueError("hard-required workspace set exceeds bounded limit")
        ranked = sorted(
            zip(all_facts, scores, vectors),
            key=lambda item: (item[0].ref not in hard, -item[1], item[0].ref),
        )
        selected = []
        for fact, score, vector in ranked:
            if len(selected) >= self.top_k and fact.ref not in hard:
                continue
            selected.append(
                WorkspaceSlot(
                    fact.ref,
                    fact,
                    float(score),
                    {
                        "overlap": vector[0],
                        "self": vector[1],
                        "confidence": vector[2],
                        "derived": vector[3],
                        "salience": vector[4],
                        "recency": vector[5],
                    },
                )
            )
        return selected, {
            "top_k": self.top_k,
            "selected": [
                {
                    "ref": item.ref,
                    "operator": item.fact.operator,
                    "score": round(item.score, 4),
                    "features": item.features,
                    "hard_required": item.ref in hard,
                }
                for item in selected
            ],
        }
