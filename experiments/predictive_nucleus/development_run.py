"""Fixed public one-pair to two-pair diagnostic; never a G1 challenge.

Training and evaluation use already-opened deterministic factorial fixtures.
The same evaluator-authored atomic outcomes occur in both; episodes are not
independent draws. Model losses, sensor geometry and compute differ. Python
callbacks run in-process and do not provide an isolation or custody boundary.
The protocol is verified before any data are generated or model is fitted.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from hashlib import sha256
from itertools import product
import json
from math import fsum, isfinite
from pathlib import Path
from time import perf_counter, process_time

from .causal_replay import DevelopmentHistory, PublicReplay
from .joint_score import joint_log_loss, summarize_joint_log_loss
from .schedule_fixture import SensorEpisode
from .schedule_fixture import make_evaluator_episode as training_episode
from .schedule_fixture import sensor_view as training_view
from .sensor_controls import EventMemory, FullWorldEventMemory, NoChange
from .shared_training_smoke import collect_shared, collect_shared_development, tensorize
from .two_pair_fixture import make_evaluator_episode as evaluation_episode
from .two_pair_fixture import sensor_view as evaluation_view

PROTOCOL_PATH = Path(__file__).with_name("dev_composition_protocol_v2.json")
PROTOCOL_SHA256 = "d1cfc5f96fd9e78cba587d730bafbad88464e9607b9a1ecc0b81152a6dc29af3"
MODEL_NAMES = ("structured", "flat", "no_change", "local_memory_with_persistence")
ZERO_TRAIN_COLUMNS = (3, 4, 5, 9, 10, 11, 15, 16, 17, 21, 22, 23, 27, 28, 29, 35)


def read_protocol(path=PROTOCOL_PATH):
    """Require the exact frozen development plan, not the G0 challenge."""
    raw = Path(path).read_bytes()
    if sha256(raw).hexdigest() != PROTOCOL_SHA256:
        raise ValueError("development protocol hash mismatch")
    protocol = json.loads(raw)
    if (protocol["training"]["fixture"] != "schedule_fixture_with_observe_v1" or
            protocol["training"]["blocks"] != [0, 1] or protocol["training"]["cases_per_block"] != 32 or
            protocol["training"]["episodes"] != 64 or
            protocol["training"]["action_sequence"] != ["contact(A,B)", "observe(A,B)", "contact(B,A)",
                                                        "set(A,x)", "set(A,y)"] or
            protocol["evaluation"]["fixture"] != "two_pair_fixture" or
            protocol["evaluation"]["block"] != 0 or protocol["evaluation"]["cases"] != 64 or
            protocol["evaluation"]["scored_actions"] != [0, 1, 2, 3, 4] or
            protocol["source_parent"] != "afd8dc7b639558de85d7a45568df0d30a5788c1f" or
            protocol["evaluation"]["strata"] != {"contact_set": [0, 1, 3, 4], "observe": [2]} or
            protocol["model_seeds"] != [7, 11, 23, 37, 53] or protocol["model_updates"] != 200 or
            protocol["optimizer"] != "Adam" or protocol["learning_rate"] != 0.02 or
            protocol["cpu_threads"] != 1 or protocol["sensor_error_rate"] != 0.0 or
            protocol["flat_sensor_metadata_mode"] != "neutral" or protocol["flat_temperature"] != 1.0 or
            protocol["calibration"] != "NONE" or tuple(protocol["models"]) != MODEL_NAMES):
        raise ValueError("development protocol inventory mismatch")
    return protocol


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _fingerprint(tensors):
    """Hash names, dtype, shape, and CPU bytes; not a cross-host guarantee."""
    import torch
    digest = sha256()
    for name, tensor in sorted(tensors.items()):
        value = tensor.detach().cpu().contiguous()
        meta = _json([name, str(value.dtype), list(value.shape)]).encode()
        raw = bytes(value.view(torch.uint8).reshape(-1).tolist())
        digest.update(len(meta).to_bytes(8, "big")); digest.update(meta)
        digest.update(len(raw).to_bytes(8, "big")); digest.update(raw)
    return digest.hexdigest()


class _Recorder:
    """Record only the callback-delivered sensor input and committed forecast."""
    def __init__(self):
        self.history, self.forecasts, self.feedback_diagnostics = [], [], []
        self.predict_wall_seconds = 0.0
        self.receive_wall_seconds = 0.0

    def start(self, anchor):
        self.history.append(_json(anchor))
        self.ids = tuple(sorted(m["id"] for m in anchor["measurements"]))
        self._start(anchor)

    def predict(self, turn):
        self.history.append(_json(turn))
        before = perf_counter()
        status, reason, distribution = self._predict(turn["action"])
        self.predict_wall_seconds += perf_counter() - before
        self.forecasts.append((status, reason, distribution))

    def receive(self, feedback):
        self.history.append(_json(feedback))
        before = perf_counter()
        diagnostic = self._receive(feedback)
        self.feedback_diagnostics.append(diagnostic)
        self.receive_wall_seconds += perf_counter() - before


class _Structured(_Recorder):
    def __init__(self, kernel):
        super().__init__(); self.kernel = kernel

    def _start(self, anchor):
        from .uncertainty import EvidenceBelief
        self.model = EvidenceBelief(self.kernel, anchor, sensor_error_rate=0.0)
        if self.model.ids != self.ids:
            raise ValueError("structured identity order mismatch")

    def _predict(self, action):
        forecast = self.model.commit_action(action)
        world = defaultdict(float)
        for (_, bits), mass in forecast.states.items():
            world[bits] += mass
        return "PREDICTED", None, dict(world)

    def _receive(self, feedback):
        result = self.model.receive(feedback, f"public-{feedback['t']}")
        return {"status": result.status, "observed_probability": result.observed_probability,
                "retained_unconditioned_forecast": bool(feedback["measurements"]) and result.observed_probability < 1e-15}


class _Flat(_Recorder):
    def __init__(self, model):
        super().__init__(); self.model = model

    def _start(self, anchor):
        self.model.reset(anchor, sensor_error_rate=0.0, sensor_metadata_mode="neutral")
        if self.model.ids != self.ids:
            raise ValueError("flat identity order mismatch")

    def _predict(self, action):
        return "PREDICTED", None, self.model.commit(action, temperature=1.0)

    def _receive(self, feedback):
        self.model.receive(feedback)


class _NoChange(_Recorder):
    def _start(self, anchor):
        self.model = NoChange(); self.model.start(anchor)

    def predict(self, turn):
        self.history.append(_json(turn))
        before = perf_counter()
        bits = self.model.predict(turn)
        self.predict_wall_seconds += perf_counter() - before
        self.forecasts.append(("PREDICTED", None, {tuple(bits[k] for k in self.ids): 1.0}))

    def _receive(self, feedback):
        self.model.receive(feedback)


class _LocalMemory(_Recorder):
    def __init__(self, memory):
        super().__init__(); self.memory = memory

    def _start(self, anchor):
        self.model = FullWorldEventMemory(self.memory); self.model.start(anchor)

    def predict(self, turn):
        self.history.append(_json(turn))
        before = perf_counter()
        result = self.model.predict(turn)
        self.predict_wall_seconds += perf_counter() - before
        if tuple(result["ids"]) != self.ids:
            raise ValueError("control identity order mismatch")
        self.forecasts.append((result["status"], result["reason"], result["worlds"]))

    def _receive(self, feedback):
        self.model.receive(feedback)


def score_forecast(status, reason, distribution, truth):
    """Score represented joint probabilities; abstention is not probability 0."""
    if type(truth) is not tuple or not truth or any(type(bit) is not int or bit not in (0, 1) for bit in truth):
        raise ValueError("invalid evaluator truth")
    if status == "ABSTAIN":
        if distribution is not None:
            raise ValueError("abstention must not carry a world distribution")
        return {"status": status, "reason": reason, "map_world": None, "map_correct": None,
                "truth_probability": None, "joint_log_score": None, "joint_brier": None,
                "world_probabilities": None}
    if status != "PREDICTED" or type(distribution) is not dict or not distribution:
        raise ValueError("invalid forecast status")
    for state, probability in distribution.items():
        if (type(state) is not tuple or len(state) != len(truth) or
                any(type(bit) is not int or bit not in (0, 1) for bit in state) or
                type(probability) not in (float, int) or not isfinite(probability) or not 0 <= probability <= 1):
            raise ValueError("invalid represented world")
    if abs(fsum(distribution.values()) - 1.0) > 1e-6:
        raise ValueError("joint forecast must be normalized")
    best = min(distribution, key=lambda state: (-distribution[state], state))
    probability = float(distribution.get(truth, 0.0))
    brier = fsum((float(distribution.get(world, 0.0)) - float(world == truth)) ** 2
                 for world in product((0, 1), repeat=len(truth)))
    return {"status": status, "reason": reason, "map_world": list(best), "map_correct": best == truth,
            "truth_probability": probability, "joint_log_score": joint_log_loss(probability), "joint_brier": brier,
            "world_probabilities": [{"world": list(world), "probability": float(distribution.get(world, 0.0))}
                                    for world in product((0, 1), repeat=len(truth))]}


def _summary(rows):
    """Keep the denominator and represented-zero accounting explicit."""
    answered = [r for r in rows if r["status"] == "PREDICTED"]
    correct = sum(r["map_correct"] for r in answered)
    return {"queries": len(rows), "answered": len(answered), "abstained": len(rows) - len(answered),
            "coverage": len(answered) / len(rows), "correct": correct,
            "accuracy_answered": correct / len(answered) if answered else None,
            "correct_per_query": correct / len(rows), "wrong_per_query": (len(answered) - correct) / len(rows),
            "mean_joint_brier_answered": fsum(r["joint_brier"] for r in answered) / len(answered) if answered else None,
            "joint_log_loss": summarize_joint_log_loss([r["joint_log_score"] for r in answered]) if answered else None}


def _training_history(episode):
    """Insert one evaluator-owned observe(A,B) after the initial contact.

    Selection depends only on the public action operands. This constructs a
    public development trace, not a secret sensor stream or blind challenge.
    """
    from .world import Action, observe, step

    original = training_view(episode)
    first_action = original.learner_turn(0)["action"]
    participants = tuple(first_action["participants"])
    after_contact = episode.states[1]
    observed_state = step(after_contact, Action("observe"))
    if observed_state != after_contact:
        raise RuntimeError("observation changed evaluator state")
    measured = observe(observed_state, 2, participants)
    records = tuple((item["id"], item["bit"]) for item in measured["measurements"])
    observations = (*original._observations[:2], records, *original._observations[2:])
    actions = (original._action_records[0], ("observe", (), None), *original._action_records[1:])
    return DevelopmentHistory.from_sensor_view(SensorEpisode(observations, actions))


def _operand_ranks(history):
    """Public action operand positions in the flat model's sorted-ID order."""
    ids = tuple(sorted(m["id"] for m in history.learner_turn(0)["observation"]["measurements"]))
    return tuple((turn["action"]["kind"], tuple(ids.index(name) for name in turn["action"]["participants"]))
                 for turn in (history.learner_turn(i) for i in range(len(history.actions))))


def _rank_inventory(histories):
    counts = Counter(_operand_ranks(history) for history in histories)
    return [{"action_operand_ranks": [[kind, list(ranks)] for kind, ranks in pattern], "episodes": count}
            for pattern, count in sorted(counts.items())]


def _evaluate_case(episode, structured_kernel, flat_model, memory):
    """Replay the same public sensor history, then access evaluator-only truth."""
    history = DevelopmentHistory.from_sensor_view(evaluation_view(episode))
    agents = (_Structured(structured_kernel), _Flat(flat_model), _NoChange(), _LocalMemory(memory))
    PublicReplay.from_development_history(history).run(agents[0], agents[1])
    PublicReplay.from_development_history(history).run(agents[2], agents[3])
    if any(agent.history != agents[0].history for agent in agents[1:]):
        raise RuntimeError("models received different action or sensor records")
    if any(agent.ids != agents[0].ids or len(agent.forecasts) != 5 for agent in agents):
        raise RuntimeError("model forecasts or identities do not match the episode")
    rows = []
    for i in range(5):
        truth_by_id = episode.gold_after(i)  # evaluator-only; after both replay passes
        truth = tuple(truth_by_id[name] for name in agents[0].ids)
        action = history.learner_turn(i)["action"]
        scores = {name: score_forecast(*agent.forecasts[i], truth)
                  for name, agent in zip(MODEL_NAMES, agents)}
        scores["structured"]["feedback_diagnostic"] = agents[0].feedback_diagnostics[i]
        rows.append({"step": i, "action_kind": action["kind"], "action": action, "ids": list(agents[0].ids),
                     "truth": list(truth), "models": scores})
    return rows, [json.loads(item) for item in agents[0].history], {name: {"predict_wall_seconds": agent.predict_wall_seconds,
                         "receive_wall_seconds": agent.receive_wall_seconds}
                  for name, agent in zip(MODEL_NAMES, agents)}


def run():
    """Run exactly the public frozen development protocol, never a G1 gate."""
    protocol = read_protocol()
    import os
    import platform
    import resource
    import subprocess
    import torch
    from .flat_reference import FlatWorldGRU, fit_flat
    from .latent_model import fit_kernel

    if (torch.version.cuda is not None or torch.version.hip is not None or
            (hasattr(torch.backends, "mps") and torch.backends.mps.is_available()) or
            (hasattr(torch, "xpu") and torch.xpu.is_available())):
        raise RuntimeError("public diagnostic requires a CPU-only PyTorch installation")
    prior_threads = torch.get_num_threads()
    try:
        with torch.random.fork_rng(devices=[]):
            torch.set_num_threads(1)
            return _run_fixed(protocol, torch, FlatWorldGRU, fit_flat, fit_kernel, platform, resource, os, subprocess)
    finally:
        torch.set_num_threads(prior_threads)


def _run_fixed(protocol, torch, FlatWorldGRU, fit_flat, fit_kernel, platform, resource, os, subprocess):
    prep_start, prep_cpu = perf_counter(), process_time()
    episodes = [training_episode(case, block=block) for block in (0, 1) for case in range(32)]
    train_views = [_training_history(episode) for episode in episodes]
    records = [collect_shared_development(view) for view in train_views]
    train_inventory = {m["id"] for view in train_views for m in view.learner_turn(0)["observation"]["measurements"]}
    if len(train_inventory) != 6:
        raise RuntimeError("public training identity inventory drift")
    expected_train_ranks = Counter({
        (("contact", (1, 0)), ("observe", ()), ("contact", (0, 1)), ("set", (1,)), ("set", (1,))): 32,
        (("contact", (1, 2)), ("observe", ()), ("contact", (2, 1)), ("set", (1,)), ("set", (1,))): 32,
    })
    if Counter(_operand_ranks(history) for history in train_views) != expected_train_ranks:
        raise RuntimeError("public training operand-rank inventory drift")
    # The inserted observation changes the flat recurrent history but not the
    # structured immediate before/after contacts and sets of this curriculum.
    originals = [collect_shared(training_view(episode)) for episode in episodes]
    if any((new.contacts, new.interventions) != (old.contacts, old.interventions)
           for new, old in zip(records, originals)):
        raise RuntimeError("observe insertion changed original structured samples")
    batch, samples = tensorize(records)
    preprocessing = {"wall_seconds": perf_counter() - prep_start, "cpu_seconds": process_time() - prep_cpu}
    memory_start, memory_cpu = perf_counter(), process_time()
    memory = EventMemory.fit(train_views)
    memory_fit_cost = {"wall_seconds": perf_counter() - memory_start, "cpu_seconds": process_time() - memory_cpu}
    if (len(records), len(samples.contact), len(samples.intervention), samples.episodes) != (64, 128, 128, 64):
        raise RuntimeError("development training inventory drift")
    if (int(batch[2].sum()), int((batch[1] >= 0).sum()), int((batch[0][:, :, 32] != 0).sum())) != (320, 512, 64):
        raise RuntimeError("development observe or feedback inventory drift")
    zero_columns = tuple(i for i in range(batch[0].shape[-1]) if not bool((batch[0][:, :, i] != 0).any()))
    if zero_columns != ZERO_TRAIN_COLUMNS:
        raise RuntimeError("flat zero training feature columns drift")
    flat_inputs = {"flat_features": batch[0], "flat_targets": batch[1], "flat_valid": batch[2]}
    structured_inputs = {"structured_contact": samples.contact, "structured_episode": samples.episode_id,
                         "structured_set": samples.intervention}
    train_sequences = {(record.contacts, record.interventions) for record in records}
    train_contacts = {item for record in records for item in record.contacts}
    train_sets = {item for record in records for item in record.interventions}
    results, evaluation_inventory = [], None
    for seed in protocol["model_seeds"]:
        torch.manual_seed(seed)
        initial_flat = FlatWorldGRU()
        initial_zero_weights = initial_flat.cell.weight_ih.detach()[:, list(zero_columns)].clone()
        initial_observe_weights = initial_flat.cell.weight_ih.detach()[:, 32].clone()
        if initial_flat.param_count() != 1457 or initial_zero_weights.numel() != 336:
            raise RuntimeError("flat parameter inventory drift")
        start, cpu = perf_counter(), process_time()
        structured, structured_info = fit_kernel(samples, seed, steps=protocol["model_updates"])
        structured_cost = {"wall_seconds": perf_counter() - start, "cpu_seconds": process_time() - cpu}
        start, cpu = perf_counter(), process_time()
        flat, flat_info = fit_flat(batch, seed, max_steps=protocol["model_updates"],
                                   fixed_steps=protocol["model_updates"], wall_budget_seconds=3600.0)
        flat_cost = {"wall_seconds": perf_counter() - start, "cpu_seconds": process_time() - cpu}
        if structured_info["gradient_steps"] != 200 or flat_info["gradient_steps"] != 200:
            raise RuntimeError("fixed optimizer schedule drift")
        if (not all(isfinite(structured_info[name]) for name in ("train_marginal_nll", "train_set_nll")) or
                not isfinite(flat_info["training_sensor_nll"]) or
                any(not bool(torch.isfinite(parameter).all()) for model in (structured, flat)
                    for parameter in model.parameters())):
            raise RuntimeError("nonfinite fitted weights or training losses")
        unchanged = torch.equal(initial_zero_weights, flat.cell.weight_ih.detach()[:, list(zero_columns)])
        if not unchanged or flat.cell.weight_ih.grad is None or bool((flat.cell.weight_ih.grad[:, list(zero_columns)] != 0).any()):
            raise RuntimeError("flat zero-feature gradients or initial weights changed")
        kernel = structured.freeze()
        cases, costs, activated_zero_columns, evaluation_ranks = [], [], set(), []
        local_contact_overlap = local_set_overlap = 0
        evaluation_start, evaluation_cpu = perf_counter(), process_time()
        for case in range(64):
            episode = evaluation_episode(case, block=0)
            anchor = evaluation_view(episode).learner_turn(0)["observation"]
            case_inventory = {m["id"] for m in anchor["measurements"]}
            if (len(case_inventory) != 3 or case_inventory & train_inventory or
                    (evaluation_inventory is not None and case_inventory != evaluation_inventory)):
                raise RuntimeError("public evaluation identity inventory drift or overlap")
            evaluation_inventory = case_inventory
            rows, public_history, cost = _evaluate_case(episode, kernel, flat, memory)
            # Sample overlap is computed only after all four replay passes.
            observed_history = DevelopmentHistory.from_sensor_view(evaluation_view(episode))
            observed = collect_shared_development(observed_history)
            evaluation_ranks.append(observed_history)
            # The structured extractor groups contacts and sets separately;
            # this does not preserve their cross-type temporal interleaving.
            sequence_seen = (observed.contacts, observed.interventions) in train_sequences
            local_contact_overlap += sum(item in train_contacts for item in observed.contacts)
            local_set_overlap += sum(item in train_sets for item in observed.interventions)
            activated_zero_columns.update(column for features, _ in observed.flat_rows for column in zero_columns
                                          if features[column] != 0)
            cases.append({"case": case, "steps": rows, "public_history": public_history,
                          "structured_type_grouped_sequences_seen_in_training": sequence_seen}); costs.append(cost)
        if sum(case["structured_type_grouped_sequences_seen_in_training"] for case in cases) != 8:
            raise RuntimeError("public type-grouped structured-sample overlap inventory drift")
        if (local_contact_overlap, local_set_overlap) != (128, 128):
            raise RuntimeError("public local-sample overlap inventory drift")
        expected_eval_ranks = Counter({
            (("contact", (0, 2)), ("set", (2,)), ("observe", ()), ("contact", (2, 1)), ("set", (1,))): 64,
        })
        if Counter(_operand_ranks(history) for history in evaluation_ranks) != expected_eval_ranks:
            raise RuntimeError("public evaluation operand-rank inventory drift")
        if activated_zero_columns:
            raise RuntimeError("unexpected previously-untrained feature activation")
        evaluation_cost = {"wall_seconds": perf_counter() - evaluation_start,
                           "cpu_seconds": process_time() - evaluation_cpu}
        summaries = [{"step": step, "action_kind": cases[0]["steps"][step]["action_kind"],
                      "models": {name: _summary([case["steps"][step]["models"][name] for case in cases])
                                 for name in MODEL_NAMES}} for step in range(5)]
        strata = {name: {model: _summary([case["steps"][step]["models"][model]
                                          for case in cases for step in steps])
                          for model in MODEL_NAMES} for name, steps in protocol["evaluation"]["strata"].items()}
        kinds = {kind: {model: _summary([row["models"][model] for case in cases for row in case["steps"]
                                         if row["action_kind"] == kind]) for model in MODEL_NAMES}
                 for kind in ("contact", "set", "observe")}
        results.append({"model_seed": seed, "structured_training": structured_info, "flat_training": flat_info,
                        "flat_zero_training_columns": list(zero_columns), "flat_zero_column_weights_unchanged": unchanged,
                        "flat_zero_column_weight_count": int(initial_zero_weights.numel()),
                        "flat_zero_column_last_gradient_is_zero": True,
                        "flat_max_parameters_with_data_gradient": flat.param_count() - int(initial_zero_weights.numel()),
                        "flat_previously_zero_columns_activated_in_evaluation": sorted(activated_zero_columns),
                        "flat_observe_weights_changed_count": int((flat.cell.weight_ih.detach()[:, 32] != initial_observe_weights).sum()),
                        "evaluation_local_samples_in_training": {"contacts": local_contact_overlap,
                                                                  "sets": local_set_overlap},
                        "evaluation_action_operand_ranks": _rank_inventory(evaluation_ranks),
                        "structured_fit_cost": structured_cost, "flat_fit_cost": flat_cost,
                        "structured_weights_sha256": _fingerprint(structured.state_dict()),
                        "flat_weights_sha256": _fingerprint(flat.state_dict()),
                        "cases": cases, "summaries_by_step": summaries, "summaries_by_kind": kinds,
                        "summaries_by_stratum": strata, "evaluation_cost": evaluation_cost,
                        "inference_costs_by_case": costs})
    try:
        cpu_model = next((line.split(":", 1)[1].strip() for line in Path("/proc/cpuinfo").read_text().splitlines()
                          if line.lower().startswith("model name")), platform.processor() or "unknown")
    except OSError:
        cpu_model = platform.processor() or "unknown"
    try:
        execution_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        tracked_diff = subprocess.run(["git", "diff", "--quiet", "HEAD", "--"], check=False)
        tracked_tree_clean = {0: True, 1: False}.get(tracked_diff.returncode)
        untracked_present = bool(subprocess.check_output(
            ["git", "ls-files", "--others", "--exclude-standard"], text=True).strip())
    except (OSError, subprocess.CalledProcessError):
        execution_commit = None
        tracked_tree_clean = None
        untracked_present = None
    return {"status": "OPEN_PUBLIC_DEVELOPMENT_NOT_G1", "protocol_sha256": PROTOCOL_SHA256,
            "source_parent": protocol["source_parent"], "execution_commit": execution_commit,
            "tracked_tree_clean": tracked_tree_clean, "untracked_present": untracked_present,
            "github_sha": os.environ.get("GITHUB_SHA"),
            "train_evaluation_identity_intersection_count": len(train_inventory & evaluation_inventory),
            "independent_world_claim": False, "calibration": "NONE", "train_episodes": 64,
            "train_identity_blocks": 2, "evaluation_cases": 64, "evaluation_identity_blocks": 1,
            "evaluation_reuse": "The same 64 opened cases are reused across all model seeds; controls are not independent repeats.",
            "supervised_action_order": {"training": ["contact", "contact", "set", "set"],
                                        "evaluation": ["contact", "set", "contact", "set"]},
            "preprocessing": preprocessing, "memory_fit_cost": memory_fit_cost,
            "training_action_operand_ranks": _rank_inventory(train_views),
            "event_memory_table_sha256": sha256(_json(memory.rows).encode()).hexdigest(),
            "training_input_sha256": {"flat": _fingerprint(flat_inputs), "structured": _fingerprint(structured_inputs)},
            "training_sensor_history_sha256": sha256(_json([r.history for r in records]).encode()).hexdigest(),
            "training_counts": {"flat_measured_events": int(batch[2].sum()),
                                "flat_observed_bits": int((batch[1] >= 0).sum()),
                                "structured_contacts": len(samples.contact), "structured_sets": len(samples.intervention),
                                "structured_episode_groups": samples.episodes, "local_table_events": memory.eligible_events},
            "hardware": {"python": platform.python_version(), "torch": torch.__version__,
                         "cpu": cpu_model, "threads": torch.get_num_threads(),
                         "torch_config_sha256": sha256(torch.__config__.show().encode()).hexdigest(),
                         "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
                         "peak_rss_platform_units": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss},
            "limitations": protocol["constraints"], "results": results}


def main():
    print(json.dumps(run(), sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
