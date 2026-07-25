"""Open compositional semantic codec for CEMM v1.

The model predicts discourse force, application topology, operators, typed
source pointers and query projection variables. Exact semantic validity remains
outside the network.
"""
from __future__ import annotations

import itertools
import math
import re as _re
from dataclasses import dataclass
from typing import Any

from cemm.config import Config
from cemm.model import isvar

try:
    import torch
    from torch import nn
except Exception as exc:
    raise SystemExit("pip install torch") from exc

torch.set_num_threads(1)

_TOK = _re.compile(r"@[A-Z]\d+<[^>]+>|@[A-Z]\d+|<[A-Za-z0-9_:.=-]+>|[\wÀ-ÿ:/?.!'-]+|[^\s]", _re.UNICODE)


def toks(value):
    return _TOK.findall(str(value))


MAX_APPS = 3
MAX_RULE_IF = 3
MAX_RULE_THEN = 3
CACHE: dict[tuple[str, str], tuple[Any, Any]] = {}


def logp(value):
    return math.log(max(1e-9, float(value)))


class Encoder(nn.Module):
    def __init__(self, vocab, d=64):
        super().__init__()
        self.emb = nn.Embedding(vocab, d, padding_idx=0)
        self.pos = nn.Embedding(160, d)
        layer = nn.TransformerEncoderLayer(d, 4, 128, dropout=0, batch_first=True)
        self.enc = nn.TransformerEncoder(layer, 2)

    def forward(self, values):
        positions = torch.arange(values.size(1), device=values.device)[None, :]
        hidden = self.enc(self.emb(values) + self.pos(positions), src_key_padding_mask=values.eq(0))
        mask = values.ne(0).float().unsqueeze(-1)
        return (hidden * mask).sum(1) / mask.sum(1).clamp_min(1)


class StructuredNet(nn.Module):
    def __init__(self, vocab, nforces, nops, nroles, nsrc, d=64):
        super().__init__()
        self.enc = Encoder(vocab, d)
        self.force = nn.Linear(d, nforces)
        self.presence = nn.Linear(d, MAX_APPS * 2)
        self.operators = nn.Linear(d, MAX_APPS * nops)
        self.bindings = nn.Linear(d, MAX_APPS * nroles * nsrc)
        self.describe = nn.Linear(d, nsrc)
        self.projection = nn.Linear(d, nsrc)
        self.nops = nops
        self.nroles = nroles
        self.nsrc = nsrc

    def forward(self, values):
        encoded = self.enc(values)
        return (
            self.force(encoded),
            self.presence(encoded).view(-1, MAX_APPS, 2),
            self.operators(encoded).view(-1, MAX_APPS, self.nops),
            self.bindings(encoded).view(-1, MAX_APPS, self.nroles, self.nsrc),
            self.describe(encoded),
            self.projection(encoded),
        )


class RuleNet(nn.Module):
    def __init__(self, vocab, nops, nroles, nsrc, d=64):
        super().__init__()
        self.enc = Encoder(vocab, d)
        self.kind = nn.Linear(d, 2)
        self.if_presence = nn.Linear(d, MAX_RULE_IF * 2)
        self.if_operators = nn.Linear(d, MAX_RULE_IF * nops)
        self.if_bindings = nn.Linear(d, MAX_RULE_IF * nroles * nsrc)
        self.then_presence = nn.Linear(d, MAX_RULE_THEN * 2)
        self.then_operators = nn.Linear(d, MAX_RULE_THEN * nops)
        self.then_bindings = nn.Linear(d, MAX_RULE_THEN * nroles * nsrc)
        self.nops = nops
        self.nroles = nroles
        self.nsrc = nsrc

    def forward(self, values):
        encoded = self.enc(values)
        return (
            self.kind(encoded),
            self.if_presence(encoded).view(-1, MAX_RULE_IF, 2),
            self.if_operators(encoded).view(-1, MAX_RULE_IF, self.nops),
            self.if_bindings(encoded).view(-1, MAX_RULE_IF, self.nroles, self.nsrc),
            self.then_presence(encoded).view(-1, MAX_RULE_THEN, 2),
            self.then_operators(encoded).view(-1, MAX_RULE_THEN, self.nops),
            self.then_bindings(encoded).view(-1, MAX_RULE_THEN, self.nroles, self.nsrc),
        )


@dataclass
class Candidate:
    packet: dict[str, Any]
    score: float
    trace: dict[str, Any]


class StructuredSemanticCodec:
    LEGACY_FORCE = {
        "assert": "claim",
        "query": "query",
        "describe": "description_request",
    }
    RULE_KINDS = ["definition", "entailment"]

    def __init__(self, pack, config=None, epochs=260):
        self.config = config or Config()
        self.pack = pack
        data = pack.data if hasattr(pack, "data") else pack
        self.sources = list(data["source_classes"])
        self.rule_sources = list(data["rule_sources"])
        self.operators = list(data["operators"])
        self.roles = list(data["roles"])
        examples = list(data.get("structured_examples", []))
        target_forces = {
            target.get("force") or self.LEGACY_FORCE[target.get("intent", "assert")]
            for target in (example["target"] for example in examples)
        }
        self.forces = list(data.get("forces", []))
        for force in sorted(target_forces):
            if force not in self.forces:
                self.forces.append(force)
        self.source_index = {value: index for index, value in enumerate(self.sources)}
        self.rule_source_index = {value: index for index, value in enumerate(self.rule_sources)}
        self.operator_index = {value: index for index, value in enumerate(self.operators)}
        self.role_index = {value: index for index, value in enumerate(self.roles)}
        self.force_index = {value: index for index, value in enumerate(self.forces)}
        texts = [example["input"] for example in examples] + [
            example["input"] for example in data.get("rule_examples", [])
        ]
        vocabulary = ["<pad>", "<unk>"] + sorted(
            {token.casefold() for text in texts for token in toks(text)}
        )
        self.vocabulary_index = {value: index for index, value in enumerate(vocabulary)}
        key = (data["pack_hash"], "structured-v5-force-query")
        if key in CACHE:
            self.net, self.rule_net = CACHE[key]
        else:
            self.net = self._train_struct(examples, epochs)
            self.rule_net = (
                self._train_rules(data.get("rule_examples", []), max(epochs, 320))
                if data.get("rule_examples")
                else None
            )
            CACHE[key] = (self.net, self.rule_net)

    def _tensor(self, texts):
        sequences = [
            [self.vocabulary_index.get(token.casefold(), 1) for token in toks(text)] or [1]
            for text in texts
        ]
        maximum = max(map(len, sequences))
        return torch.tensor([sequence + [0] * (maximum - len(sequence)) for sequence in sequences])

    def _target_force(self, target):
        return target.get("force") or self.LEGACY_FORCE[target.get("intent", "assert")]

    def _train_struct(self, examples, epochs):
        torch.manual_seed(self.config.structured_net_seed)
        net = StructuredNet(
            len(self.vocabulary_index),
            len(self.forces),
            len(self.operators),
            len(self.roles),
            len(self.sources),
        )
        optimizer = torch.optim.AdamW(net.parameters(), lr=0.008, weight_decay=1e-4)
        values = self._tensor([example["input"] for example in examples])
        forces = []
        presence = []
        operators = []
        bindings = []
        describes = []
        projections = []
        for example in examples:
            target = example["target"]
            forces.append(self.force_index[self._target_force(target)])
            p_rows = []
            o_rows = []
            b_rows = []
            for slot in range(MAX_APPS):
                application = target.get("apps", [])[slot] if slot < len(target.get("apps", [])) else None
                p_rows.append(1 if application else 0)
                o_rows.append(self.operator_index.get(application["operator"], 0) if application else 0)
                b_rows.append(
                    [
                        self.source_index.get(application.get("bindings", {}).get(role, "NONE"), 0)
                        if application
                        else 0
                        for role in self.roles
                    ]
                )
            presence.append(p_rows)
            operators.append(o_rows)
            bindings.append(b_rows)
            describes.append(self.source_index.get(target.get("describe_source", "NONE"), 0))
            projected = torch.zeros(len(self.sources), dtype=torch.float)
            for source in target.get("projection", []):
                if source in self.source_index:
                    projected[self.source_index[source]] = 1.0
            projections.append(projected)
        force_targets = torch.tensor(forces)
        presence_targets = torch.tensor(presence)
        operator_targets = torch.tensor(operators)
        binding_targets = torch.tensor(bindings)
        describe_targets = torch.tensor(describes)
        projection_targets = torch.stack(projections)
        for _ in range(epochs):
            optimizer.zero_grad()
            force_logits, p_logits, o_logits, b_logits, d_logits, q_logits = net(values)
            loss = (
                nn.functional.cross_entropy(force_logits, force_targets)
                + 0.8 * nn.functional.cross_entropy(p_logits.reshape(-1, 2), presence_targets.reshape(-1))
                + 0.7 * nn.functional.cross_entropy(d_logits, describe_targets)
                + 0.35 * nn.functional.binary_cross_entropy_with_logits(q_logits, projection_targets)
            )
            active = presence_targets.reshape(-1).bool()
            if active.any():
                loss += nn.functional.cross_entropy(
                    o_logits.reshape(-1, len(self.operators))[active],
                    operator_targets.reshape(-1)[active],
                )
            flat_binding_logits = b_logits.reshape(-1, len(self.sources))
            flat_binding_targets = binding_targets.reshape(-1)
            weights = torch.ones_like(flat_binding_targets, dtype=torch.float)
            weights[flat_binding_targets == self.source_index["NONE"]] = 0.12
            cross_entropy = nn.functional.cross_entropy(
                flat_binding_logits, flat_binding_targets, reduction="none"
            )
            loss += (cross_entropy * weights).sum() / weights.sum().clamp_min(1)
            loss.backward()
            optimizer.step()
        net.eval()
        return net

    def _train_rules(self, examples, epochs):
        torch.manual_seed(self.config.rule_net_seed)
        net = RuleNet(
            len(self.vocabulary_index),
            len(self.operators),
            len(self.roles),
            len(self.rule_sources),
        )
        optimizer = torch.optim.AdamW(net.parameters(), lr=0.008, weight_decay=1e-4)
        values = self._tensor([example["input"] for example in examples])
        kinds = []
        if_presence = []
        if_operators = []
        if_bindings = []
        then_presence = []
        then_operators = []
        then_bindings = []
        for example in examples:
            target = example["target"]
            kinds.append(self.RULE_KINDS.index(target.get("rule_kind", "definition")))

            def side(name, maximum):
                p_rows = []
                o_rows = []
                b_rows = []
                for slot in range(maximum):
                    application = target.get(name, [])[slot] if slot < len(target.get(name, [])) else None
                    p_rows.append(1 if application else 0)
                    o_rows.append(self.operator_index.get(application["operator"], 0) if application else 0)
                    b_rows.append(
                        [
                            self.rule_source_index.get(application.get("bindings", {}).get(role, "NONE"), 0)
                            if application
                            else 0
                            for role in self.roles
                        ]
                    )
                return p_rows, o_rows, b_rows

            a, b, c = side("if", MAX_RULE_IF)
            if_presence.append(a)
            if_operators.append(b)
            if_bindings.append(c)
            a, b, c = side("then", MAX_RULE_THEN)
            then_presence.append(a)
            then_operators.append(b)
            then_bindings.append(c)
        targets = tuple(
            torch.tensor(value)
            for value in (
                kinds,
                if_presence,
                if_operators,
                if_bindings,
                then_presence,
                then_operators,
                then_bindings,
            )
        )
        for _ in range(epochs):
            optimizer.zero_grad()
            outputs = net(values)
            loss = nn.functional.cross_entropy(outputs[0], targets[0])
            for p_logits, o_logits, b_logits, p_target, o_target, b_target in (
                (*outputs[1:4], *targets[1:4]),
                (*outputs[4:7], *targets[4:7]),
            ):
                loss += nn.functional.cross_entropy(p_logits.reshape(-1, 2), p_target.reshape(-1))
                active = p_target.reshape(-1).bool()
                if active.any():
                    loss += nn.functional.cross_entropy(
                        o_logits.reshape(-1, len(self.operators))[active],
                        o_target.reshape(-1)[active],
                    )
                flat_logits = b_logits.reshape(-1, len(self.rule_sources))
                flat_targets = b_target.reshape(-1)
                weights = torch.ones_like(flat_targets, dtype=torch.float)
                weights[flat_targets == self.rule_source_index["NONE"]] = 0.1
                loss += (
                    nn.functional.cross_entropy(flat_logits, flat_targets, reduction="none") * weights
                ).sum() / weights.sum().clamp_min(1)
            loss.backward()
            optimizer.step()
        net.eval()
        return net

    def _x(self, text):
        return self._tensor([text])

    @staticmethod
    def _source_value(source, anchors, participant_frame=None):
        if source == "NONE":
            return None
        if source == "FRAME_SPEAKER":
            return participant_frame.speaker_ref if participant_frame else "participant:user"
        if source == "FRAME_ADDRESSEE":
            return participant_frame.addressee_ref if participant_frame else "participant:system"
        if source.startswith("Q") and source[1:].isdigit():
            return f"?q{source[1:]}"
        if source.startswith("A"):
            return anchors.get("@" + source)
        if source.startswith("NEW_ENTITY_"):
            return {"new": "@X_ENTITY_" + source.rsplit("_", 1)[-1], "kind": "entity"}
        if source.startswith("NEW_EVENT_"):
            return {"new": "@X_EVENT_" + source.rsplit("_", 1)[-1], "kind": "event"}
        return None

    @staticmethod
    def _kind_ok(store, role_spec, value, *, allow_variable=False):
        if value is None:
            return False
        if allow_variable and isinstance(value, str) and isvar(value):
            return True
        expected = role_spec["filler_kind"]
        if expected == "state_value":
            if isinstance(value, dict) and "new" in value:
                return True
            if isinstance(value, dict) and ("literal" in value or "app" in value):
                return True
            return bool(isinstance(value, str) and store.atom(value))
        if isinstance(value, dict) and "new" in value:
            return expected in {None, "atom", value["kind"]} or expected == "atom"
        if isinstance(value, dict) and "literal" in value:
            return bool(expected and expected.startswith("literal:"))
        atom = store.atom(value) if isinstance(value, str) else None
        return bool(atom and (not expected or expected == "atom" or atom["kind"] == expected))

    def _choose_source(
        self,
        probabilities,
        store,
        spec,
        anchors,
        participant_frame=None,
        *,
        allow_none=True,
        allow_variable=False,
        alternative=0,
    ):
        valid = []
        for index in torch.argsort(probabilities, descending=True).tolist():
            source = self.sources[index]
            if source == "NONE" and allow_none:
                valid.append((source, float(probabilities[index])))
                continue
            value = self._source_value(source, anchors, participant_frame)
            if self._kind_ok(store, spec, value, allow_variable=allow_variable):
                valid.append((source, float(probabilities[index])))
        return valid[min(alternative, len(valid) - 1)] if valid else ("NONE", 0.0)

    def predict(self, text, anchors, store, top_k=8, participant_frame=None):
        with torch.no_grad():
            force_logits, p_logits, o_logits, b_logits, d_logits, q_logits = self.net(self._x(text))
            force_probabilities = torch.softmax(force_logits[0], -1)
            presence_probabilities = torch.softmax(p_logits[0], -1)
            operator_probabilities = torch.softmax(o_logits[0], -1)
            binding_probabilities = torch.softmax(b_logits[0], -1)
            describe_probabilities = torch.softmax(d_logits[0], -1)
            projection_probabilities = torch.sigmoid(q_logits[0])
        force_ids = torch.topk(force_probabilities, min(3, len(force_probabilities))).indices.tolist()
        candidates = []
        for force_id in force_ids:
            force = self.forces[force_id]
            base_score = logp(force_probabilities[force_id])
            if force == "description_request":
                for source_index in torch.topk(describe_probabilities, min(3, len(describe_probabilities))).indices.tolist():
                    source = self.sources[source_index]
                    value = self._source_value(source, anchors, participant_frame)
                    if value and not isinstance(value, dict) and not isvar(value):
                        candidates.append(
                            Candidate(
                                {"force": force, "apps": [], "query": None, "directive": None, "describe": value},
                                base_score + logp(describe_probabilities[source_index]),
                                {"force": force, "source": source},
                            )
                        )
                continue

            profiles = []
            for threshold in (0.52, 0.30):
                active = [slot for slot in range(MAX_APPS) if float(presence_probabilities[slot, 1]) >= threshold]
                if not active:
                    active = [0]
                profile = tuple(active)
                if profile not in profiles:
                    profiles.append(profile)
            for active in profiles:
                operator_choices = [
                    torch.topk(operator_probabilities[slot], min(2, len(self.operators))).indices.tolist()
                    for slot in active
                ]
                for operator_ids in itertools.product(*operator_choices):
                    applications = []
                    score = base_score
                    valid = True
                    for slot, operator_id in zip(active, operator_ids):
                        operator = self.operators[operator_id]
                        specs = store.roles(operator)
                        args = {}
                        score += logp(presence_probabilities[slot, 1]) + logp(operator_probabilities[slot, operator_id])
                        for role, spec in specs.items():
                            if role not in self.role_index:
                                if spec["required"]:
                                    valid = False
                                continue
                            role_probabilities = binding_probabilities[slot, self.role_index[role]]
                            source, probability = self._choose_source(
                                role_probabilities,
                                store,
                                spec,
                                anchors,
                                participant_frame,
                                allow_none=not bool(spec["required"]),
                                allow_variable=force == "query",
                            )
                            value = self._source_value(source, anchors, participant_frame)
                            if source != "NONE" and value is not None:
                                args[role] = value
                                score += logp(probability)
                            elif spec["required"]:
                                # Grounded claims may still use exact unique value→dimension completion.
                                if not (force != "query" and operator == "op:state" and role == "role:dimension"):
                                    valid = False
                        if valid:
                            applications.append({"operator": operator, "args": args, "stance": "support"})
                    if not valid or not applications:
                        continue

                    variable_sources = {
                        source
                        for application in applications
                        for value in application.get("args", {}).values()
                        for source in self.sources
                        if self._source_value(source, anchors, participant_frame) == value
                        and source.startswith("Q")
                    }
                    projected_sources = {
                        source
                        for source in variable_sources
                        if float(projection_probabilities[self.source_index[source]]) >= 0.45
                    } or variable_sources
                    projection = sorted(
                        self._source_value(source, anchors, participant_frame)
                        for source in projected_sources
                    )
                    variables = []
                    for application in applications:
                        specs = store.roles(application["operator"])
                        for role, value in application.get("args", {}).items():
                            if isinstance(value, str) and isvar(value):
                                variables.append(
                                    {
                                        "ref": value,
                                        "filler_kind": specs[role]["filler_kind"] or "atom",
                                        "role_ref": role,
                                    }
                                )
                    if force == "query":
                        packet = {
                            "force": force,
                            "apps": [],
                            "query": {
                                "restrictions": applications,
                                "variables": variables,
                                "projection": projection,
                            },
                            "directive": None,
                            "describe": None,
                        }
                    elif force == "directive":
                        packet = {
                            "force": force,
                            "apps": [],
                            "query": None,
                            "directive": {"content": applications},
                            "describe": None,
                        }
                    else:
                        packet = {
                            "force": force,
                            "apps": applications,
                            "query": None,
                            "directive": None,
                            "describe": None,
                        }
                    candidates.append(
                        Candidate(
                            packet,
                            score,
                            {
                                "force": force,
                                "active_slots": active,
                                "operators": [self.operators[index] for index in operator_ids],
                                "projection_sources": sorted(projected_sources),
                            },
                        )
                    )
        candidates.sort(key=lambda candidate: candidate.score, reverse=True)
        return candidates[:top_k]

    def predict_rules(self, text, anchors, store, top_k=5):
        if self.rule_net is None:
            return []
        with torch.no_grad():
            kind, if_presence, if_operators, if_bindings, then_presence, then_operators, then_bindings = self.rule_net(self._x(text))
            kind = torch.softmax(kind[0], -1)
            if_presence = torch.softmax(if_presence[0], -1)
            if_operators = torch.softmax(if_operators[0], -1)
            if_bindings = torch.softmax(if_bindings[0], -1)
            then_presence = torch.softmax(then_presence[0], -1)
            then_operators = torch.softmax(then_operators[0], -1)
            then_bindings = torch.softmax(then_bindings[0], -1)

        def source_value(source):
            if source.startswith("A"):
                return anchors.get("@" + source)
            if source.startswith("V"):
                return "?v" + source[1:]
            if source.startswith("E"):
                return "!e" + source[1:]
            return None

        output = []
        for kind_id in torch.topk(kind, min(2, len(kind))).indices.tolist():
            rule_kind = self.RULE_KINDS[kind_id]
            score = logp(kind[kind_id])
            sides = []
            valid = True
            for presence, operators, bindings, maximum in (
                (if_presence, if_operators, if_bindings, MAX_RULE_IF),
                (then_presence, then_operators, then_bindings, MAX_RULE_THEN),
            ):
                side = []
                for slot in range(maximum):
                    if float(presence[slot, 1]) < 0.45:
                        continue
                    operator_id = int(torch.argmax(operators[slot]))
                    operator = self.operators[operator_id]
                    specs = store.roles(operator)
                    args = {}
                    score += logp(presence[slot, 1]) + logp(operators[slot, operator_id])
                    for role, spec in specs.items():
                        if role not in self.role_index:
                            if spec["required"]:
                                valid = False
                            continue
                        probabilities = bindings[slot, self.role_index[role]]
                        selected = None
                        for source_index in torch.argsort(probabilities, descending=True).tolist():
                            source = self.rule_sources[source_index]
                            value = source_value(source)
                            if source == "NONE" and not spec["required"]:
                                selected = (None, float(probabilities[source_index]))
                                break
                            if isinstance(value, str) and (isvar(value) or value.startswith("!")):
                                selected = (value, float(probabilities[source_index]))
                                break
                            if value and self._kind_ok(store, spec, value):
                                selected = (value, float(probabilities[source_index]))
                                break
                        if selected and selected[0] is not None:
                            args[role] = selected[0]
                            score += logp(selected[1])
                        elif spec["required"]:
                            valid = False
                    side.append({"operator": operator, "args": args})
                sides.append(side)
            if valid and sides[0] and sides[1]:
                output.append({"rule_kind": rule_kind, "if": sides[0], "then": sides[1], "score": score})
        return sorted(output, key=lambda item: item["score"], reverse=True)[:top_k]
