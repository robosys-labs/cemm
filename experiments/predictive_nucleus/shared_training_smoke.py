"""Public feature-collection and one-step training wiring smoke, NOT evaluation.

The two PublicReplay callbacks *collect input features*, not neural predictions.
The resulting batches are trained offline, with unequal losses and compute.
The public factorial is enumerable, shared-identity and not independent data.
Python callbacks and offline source records are not a security boundary;
no challenge, calibration, custody, or performance claim is made.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json

from .causal_replay import PublicReplay
from .flat_data import event_features, initial_ids, readings, target_observation
from .schedule_fixture import make_evaluator_episode, sensor_view


def _encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


class _Collector:
    """Strict sequential collector for one public episode; never a predictor."""
    def __init__(self):
        self.ids = None
        self.current = None
        self.pending = None
        self.history = []

    def start(self, anchor):
        if self.ids is not None:
            raise RuntimeError("collector already started")
        if (type(anchor) is not dict or set(anchor) != {"t", "measurements"} or
                type(anchor["t"]) is not int or anchor["t"] != 0):
            raise ValueError("invalid initial anchor")
        self.ids = initial_ids(anchor)
        self.current = deepcopy(anchor)
        self.history.append(_encoded(anchor))

    def predict(self, turn):
        # PublicReplay uses this callback name; this is only feature capture.
        if self.ids is None or self.pending is not None:
            raise RuntimeError("invalid collector sequence")
        if (type(turn) is not dict or set(turn) != {"observation", "action"} or
                turn["observation"] != self.current or
                type(turn["observation"].get("t")) is not int):
            raise ValueError("input does not match previous observation")
        features = tuple(event_features(self.ids, turn["observation"], turn["action"]))
        action = deepcopy(turn["action"])
        pre = readings(turn["observation"])
        self.pending = (features, action, pre)
        self.history.append(_encoded(turn))

    def receive(self, feedback):
        if self.pending is None:
            raise RuntimeError("feedback before feature capture")
        if (type(feedback) is not dict or set(feedback) != {"t", "measurements"} or
                type(feedback["t"]) is not int or feedback["t"] != self.current["t"] + 1):
            raise ValueError("invalid feedback time or envelope")
        post = readings(feedback)
        if not set(post) <= set(self.ids):
            raise ValueError("unknown feedback identity")
        self._accept(self.pending, feedback, post)
        self.current = deepcopy(feedback)
        self.pending = None
        self.history.append(_encoded(feedback))


class _FlatCollector(_Collector):
    def __init__(self):
        super().__init__()
        self.rows = []

    def _accept(self, pending, feedback, post):
        self.rows.append((pending[0], tuple(target_observation(self.ids, feedback))))


class _StructuredCollector(_Collector):
    def __init__(self):
        super().__init__()
        self.contacts = []
        self.interventions = []

    def _accept(self, pending, feedback, post):
        _, action, pre = pending
        kind, ids = action["kind"], action["participants"]
        if kind == "contact" and len(ids) == 2 and len(set(ids)) == 2 and all(k in pre and k in post for k in ids):
            self.contacts.append((pre[ids[0]], pre[ids[1]], post[ids[0]], post[ids[1]]))
        elif kind == "set" and ids[0] in pre and ids[0] in post:
            self.interventions.append((pre[ids[0]], action["value"], post[ids[0]]))


@dataclass(frozen=True)
class CollectedEpisode:
    flat_rows: tuple
    contacts: tuple
    interventions: tuple
    history: tuple


def collect_shared(view):
    """Collect both batches from the same records; discard partials on failure.

    Local collectors never escape a failed replay. This cannot undo external
    callback effects or prevent another Python object reading the fixture.
    """
    return _collect_replay(PublicReplay(view))


def collect_shared_development(history):
    """Collect a validated development history using the opt-in replay path.

    This is sensor-only offline feature collection, not model prediction,
    authenticated custody, a scientific split, or model evaluation. The caller
    is responsible for specifying and validating the development history.
    """
    return _collect_replay(PublicReplay.from_development_history(history))


def _collect_replay(replay):
    flat, structured = _FlatCollector(), _StructuredCollector()
    replay.run(flat, structured)
    if (replay.state != "completed" or flat.pending is not None or structured.pending is not None or
            flat.history != structured.history):
        raise RuntimeError("incomplete or inconsistent public collection")
    return CollectedEpisode(tuple(flat.rows), tuple(structured.contacts),
                            tuple(structured.interventions), tuple(flat.history))


def tensorize(records):
    """Construct the existing offline model tensor inputs, grouped by episode."""
    import torch
    from .flat_data import FEATURES, MAX_ENTITIES
    from .latent_model import Samples

    if not records or any(type(r) is not CollectedEpisode or not r.flat_rows for r in records):
        raise ValueError("no collected episodes")
    steps, n = max(len(r.flat_rows) for r in records), len(records)
    x = torch.zeros((steps, n, FEATURES), dtype=torch.float32)
    y = torch.full((steps, n, MAX_ENTITIES), -1, dtype=torch.long)
    valid = torch.zeros((steps, n), dtype=torch.bool)
    contacts, episode_ids, interventions, groups = [], [], [], 0
    for b, record in enumerate(records):
        for t, (features, target) in enumerate(record.flat_rows):
            x[t, b] = torch.tensor(features, dtype=torch.float32)
            y[t, b] = torch.tensor(target, dtype=torch.long)
            valid[t, b] = True
        if record.contacts:
            contacts.extend(record.contacts)
            episode_ids.extend([groups] * len(record.contacts))
            groups += 1
        interventions.extend(record.interventions)
    if not contacts or not interventions or not ((y >= 0).any(dim=-1) & valid).any():
        raise ValueError("insufficient measured examples")
    structured = Samples(groups, torch.tensor(contacts, dtype=torch.long),
                         torch.tensor(episode_ids, dtype=torch.long),
                         torch.tensor(interventions, dtype=torch.long))
    return (x, y, valid), structured


def run_fixture():
    """Fit one update only to test wiring; use sequentially with CPU-only torch.

    Torch's RNG and thread settings are process-global, so restoration is not
    an isolation mechanism for concurrent calls.
    """
    import torch

    if (torch.version.cuda is not None or torch.version.hip is not None or
            (hasattr(torch.backends, "mps") and torch.backends.mps.is_available()) or
            (hasattr(torch, "xpu") and torch.xpu.is_available())):
        raise RuntimeError("smoke requires a CPU-only PyTorch installation")
    old_threads = torch.get_num_threads()
    try:
        with torch.random.fork_rng(devices=[]):
            torch.set_num_threads(1)
            return _run_fixture_once()
    finally:
        torch.set_num_threads(old_threads)


def _run_fixture_once():
    from time import perf_counter
    from hashlib import sha256
    from math import isfinite
    import platform
    import resource
    from pathlib import Path
    import torch
    from .flat_reference import FlatWorldGRU, fit_flat
    from .latent_model import ContactKernel, fit_kernel

    prep_start = perf_counter()
    records = [collect_shared(sensor_view(make_evaluator_episode(i))) for i in range(32)]
    batch, samples = tensorize(records)
    prep_seconds = perf_counter() - prep_start
    seed = 7
    torch.manual_seed(seed)
    structured_initial = ContactKernel()
    structured_before = {k: v.detach().clone() for k, v in structured_initial.state_dict().items()}
    torch.manual_seed(seed)
    flat_initial = FlatWorldGRU()
    flat_before = {k: v.detach().clone() for k, v in flat_initial.state_dict().items()}
    structured_start = perf_counter()
    structured, structured_info = fit_kernel(samples, seed, steps=1)
    structured_seconds = perf_counter() - structured_start
    flat, flat_info = fit_flat(batch, seed, max_steps=1, fixed_steps=1, wall_budget_seconds=1.0)
    def inspect(model, before):
        weights = list(model.state_dict().items())
        grads = [p.grad for p in model.parameters()]
        return {"finite_parameters": all(bool(torch.isfinite(v).all()) for _, v in weights),
                "finite_gradients": all(g is not None and bool(torch.isfinite(g).all()) for g in grads),
                "parameter_update": any(not torch.equal(v, before[k]) for k, v in weights),
                "nonzero_gradient": any(g is not None and bool((g != 0).any()) for g in grads)}
    structured_check, flat_check = inspect(structured, structured_before), inspect(flat, flat_before)
    structured_check["finite_training_losses"] = all(isfinite(structured_info[key]) for key in
                                                    ("train_marginal_nll", "train_set_nll"))
    flat_check["finite_training_loss"] = isfinite(flat_info["training_sensor_nll"])
    if not all(structured_check.values()) or not all(flat_check.values()):
        raise RuntimeError("nonfinite or absent smoke update")
    if structured_info["gradient_steps"] != 1 or flat_info["gradient_steps"] != 1:
        raise RuntimeError("unexpected smoke optimizer schedule")
    def fingerprint(tensors):
        digest = sha256()
        for name, tensor in sorted(tensors.items()):
            value = tensor.detach().cpu().contiguous()
            metadata = json.dumps([name, str(value.dtype), list(value.shape)], separators=(",", ":")).encode()
            raw = bytes(value.view(torch.uint8).reshape(-1).tolist())
            digest.update(len(metadata).to_bytes(8, "big"))
            digest.update(metadata)
            digest.update(len(raw).to_bytes(8, "big"))
            digest.update(raw)
        return digest.hexdigest()
    try:
        cpu = next((line.split(":", 1)[1].strip() for line in Path("/proc/cpuinfo").read_text().splitlines()
                    if line.lower().startswith("model name")), platform.processor() or "unknown")
    except OSError:
        cpu = platform.processor() or "unknown"
    tensors = {"flat_features": batch[0], "flat_targets": batch[1], "flat_valid": batch[2],
               "structured_contact": samples.contact, "structured_episode_id": samples.episode_id,
               "structured_intervention": samples.intervention}
    return {"status": "PUBLIC_ONE_STEP_WIRING_ONLY", "gate_g1": "NOT_RUN",
            "warning": "callbacks collect features, not forecasts; losses and compute are not matched",
            "episodes": len(records), "shared_identity_blocks": 1,
            "independent_world_claim": False, "events": int(batch[2].sum()),
            "observed_bits": int((batch[1] >= 0).sum()),
            "contact_samples": int(samples.contact.shape[0]),
            "set_samples": int(samples.intervention.shape[0]),
            "structured_episode_groups": samples.episodes,
            "structured_steps": structured_info["gradient_steps"],
            "flat_steps": flat_info["gradient_steps"],
            "structured_check": structured_check, "flat_check": flat_check,
            "preprocessing_seconds": prep_seconds,
            "structured_fit_call_seconds": structured_seconds,
            "flat_fit_seconds": flat_info["fit_seconds"],
            "flat_budget_overshoot_seconds": flat_info["overshoot_seconds"],
            "torch_version": torch.__version__, "threads": torch.get_num_threads(), "seed": seed,
            "python_version": platform.python_version(), "platform": platform.platform(),
            "cpu_model": cpu, "torch_config_sha256": sha256(torch.__config__.show().encode()).hexdigest(),
            "deterministic_algorithms_enabled": torch.are_deterministic_algorithms_enabled(),
            "tensor_sha256": {name: fingerprint({name: tensor}) for name, tensor in tensors.items()},
            "structured_weights_sha256": fingerprint(structured.state_dict()),
            "flat_weights_sha256": fingerprint(flat.state_dict()),
            "peak_rss_platform_units": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "structured_parameters": structured.param_count(), "flat_parameters": flat.param_count(),
            "structured_loss": "episode-level latent mixture + 0.3 mean set cross-entropy",
            "flat_loss": "mean measured-event marginal joint NLL"}


def main():
    print(json.dumps(run_fixture(), sort_keys=True))


if __name__ == "__main__":
    main()
