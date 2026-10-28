"""Unrun public factorial diagnostic, not a G1 or independent challenge.

The source protocol must be committed and hash-locked before this runner can
be enabled. Forecasts share realized histories in a cooperative in-process
replay; this is not an isolation boundary. No gold is passed to a learner.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from hashlib import sha256
from itertools import permutations
import json
from pathlib import Path
from time import perf_counter, process_time
from math import ceil, fsum, isfinite

from .causal_replay import PublicReplay
from .development_run import (_Flat, _LocalMemory, _NoChange, _Recorder,
                              _Structured, _fingerprint, _json, _summary,
                              score_forecast)
from .factorial_training_data import prepare_training, rename_full_history
from .full_sensor_evaluation import full_sensor_evaluation_view
from .history_memory import HistoryMemory
from .relabel_diagnostic import compare_forecasts
from .role_history_memory import RoleHistoryMemory
from .sensor_controls import EventMemory
from .shared_training_smoke import tensorize
from .two_pair_fixture import make_evaluator_episode

# Exact independently reviewed protocol committed before this runner.
PROTOCOL_SHA256 = "2386a03847e85a75a259b0f87f03070f1643c53ca932c12abdd386cb59147377"
PROTOCOL_PATH = Path(__file__).with_name("full_sensor_paired_protocol_v2.json")
PROTOCOL_COMMIT = "a05b2a774e4ac9daa43afa201af66a3f470e14ea"
ARMS = (("repeated", "masked"), ("repeated", "full"),
        ("augmented", "masked"), ("augmented", "full"))
SEEDS = (7, 11, 23, 37, 53)
MODELS = ("structured", "flat", "no_change", "local_memory_with_persistence",
          "literal_history_memory", "role_normalized_history_memory")


def read_protocol(path=PROTOCOL_PATH):
    """Fail closed until this exact development protocol has been frozen."""
    if PROTOCOL_SHA256 is None:
        raise RuntimeError("factorial protocol is not frozen")
    raw = Path(path).read_bytes()
    if sha256(raw).hexdigest() != PROTOCOL_SHA256:
        raise ValueError("factorial protocol hash mismatch")
    protocol = json.loads(raw)
    for name, expected in protocol["source_file_sha256"].items():
        if Path(name).name != name or sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() != expected:
            raise ValueError(f"source file hash mismatch: {name}")
    return protocol


class _HistoryRecorder(_Recorder):
    def __init__(self, memory):
        super().__init__()
        self.memory = memory

    def _start(self, anchor):
        self.model = self.memory.new_predictor()
        self.model.start(anchor)

    def predict(self, turn):
        self.history.append(_json(turn))
        before = perf_counter()
        result = self.model.predict(turn)
        self.predict_wall_seconds += perf_counter() - before
        if tuple(result["ids"]) != self.ids:
            raise ValueError("memory identity order mismatch")
        self.forecasts.append((result["status"], result["reason"], result["worlds"]))

    def _receive(self, feedback):
        self.model.receive(feedback)


class _MeasuredConsumer:
    """Measure each callback without changing its delivered payload."""
    def __init__(self, consumer):
        self.consumer = consumer
        self.calls = []

    def start(self, anchor):
        self.consumer.start(anchor)

    def _invoke(self, name, payload):
        start, cpu = perf_counter(), process_time()
        result = getattr(self.consumer, name)(payload)
        self.calls.append({"phase": name, "wall_seconds": perf_counter() - start,
                           "cpu_seconds": process_time() - cpu})
        return result

    def predict(self, turn):
        return self._invoke("predict", turn)

    def receive(self, feedback):
        return self._invoke("receive", feedback)


def _replay(history, fit):
    """Pair consumers and ensure all received the same recorded sensor history."""
    agents = (_Structured(fit["kernel"]), _Flat(fit["flat"]), _NoChange(),
              _LocalMemory(fit["event"]), _HistoryRecorder(fit["literal"]),
              _HistoryRecorder(fit["role"]))
    measured = tuple(_MeasuredConsumer(agent) for agent in agents)
    for left, right in ((0, 1), (2, 3), (4, 5)):
        PublicReplay.from_full_sensor_history(history).run(measured[left], measured[right])
    if any(agent.ids != agents[0].ids or agent.history != agents[0].history or
           len(agent.forecasts) != 5 for agent in agents):
        raise RuntimeError("replay histories or identities differ")
    if any(len(item.calls) != 10 for item in measured):
        raise RuntimeError("missing callback measurements")
    return agents, measured


def _check_batches(prepared, torch):
    """Check common inputs, masks, and identical structured samples before fit."""
    batches, structured = {}, None
    for id_arm in ("repeated", "augmented"):
        records = prepared[id_arm]
        if len(records) != 384:
            raise ValueError("wrong episode inventory")
        histories = [record.history for record in records]
        for target in ("masked", "full"):
            batch, samples = tensorize([getattr(record, target) for record in records])
            if (batch[0].dtype != torch.float32 or batch[1].dtype != torch.int64 or batch[2].dtype != torch.bool or
                    samples.contact.dtype != torch.int64 or samples.episode_id.dtype != torch.int64 or
                    samples.intervention.dtype != torch.int64 or not bool(torch.isfinite(batch[0]).all())):
                raise ValueError("training tensor dtype or finiteness mismatch")
            if (int(batch[2].sum()), int((batch[1] >= 0).sum()),
                    samples.episodes, len(samples.contact), len(samples.intervention)) != (
                        1920, 3072 if target == "masked" else 5760, 384, 768, 768):
                raise ValueError("wrong training sample inventory")
            if target == "full":
                first = batches[(id_arm, "masked")][0]
                if not torch.equal(batch[0], first[0]) or not torch.equal(batch[2], first[2]):
                    raise ValueError("loss masks changed inputs or valid events")
                if not bool(((first[1] == -1) | (first[1] == batch[1])).all()):
                    raise ValueError("masked target is not an actual full reading")
            current = (samples.contact, samples.episode_id, samples.intervention)
            if structured is not None and any(not torch.equal(a, b) for a, b in zip(current, structured)):
                raise ValueError("structured samples differ between arms")
            structured = current
            batches[(id_arm, target)] = (batch, samples, histories)
    return batches


def _prepare_evaluation(prepared):
    """Build and validate public evaluator sensor histories before fitting."""
    training_ids = {name for record in prepared["repeated"] for name, _ in record.history._observations[0]}
    episodes = []
    for case in range(64):
        episode = make_evaluator_episode(case, block=0)
        history = full_sensor_evaluation_view(episode)
        ids = {name for name, _ in history._observations[0]}
        if len(ids) != 3 or ids & training_ids or len(history.actions) != 5:
            raise ValueError("evaluation identity or action inventory mismatch")
        if any(len(obs) != 3 or {name for name, _ in obs} != ids for obs in history._observations):
            raise ValueError("evaluation full-sensor inventory mismatch")
        if [record[0] for record in history._action_records] != ["contact", "set", "observe", "contact", "set"]:
            raise ValueError("evaluation action order mismatch")
        episodes.append((episode, history))
    return episodes


def _lineage(protocol):
    """Check tracked source lineage; untracked files remain explicitly reported."""
    import os
    import subprocess
    root = Path(__file__).resolve().parents[2]
    if os.environ.get("PYTHONHASHSEED") != "0":
        raise RuntimeError("PYTHONHASHSEED=0 required at process startup")
    def git(*args):
        return subprocess.run(["git", "-C", str(root), *args], check=True,
                              capture_output=True, text=True).stdout.strip()
    if subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor",
                       protocol["source_parent"], "HEAD"], capture_output=True).returncode:
        raise RuntimeError("protocol source parent is not an ancestor")
    for args in (("diff", "--quiet"), ("diff", "--cached", "--quiet")):
        if subprocess.run(["git", "-C", str(root), *args], capture_output=True).returncode:
            raise RuntimeError("tracked tree is not clean")
    source_dir = Path(__file__).resolve().parent
    paths = [source_dir / name for name in protocol["source_file_sha256"]]
    paths.extend((Path(__file__).resolve(), PROTOCOL_PATH.resolve()))
    for path in paths:
        relative = str(path.relative_to(root))
        result = subprocess.run(["git", "-C", str(root), "show", f"HEAD:{relative}"], capture_output=True)
        if result.returncode or result.stdout != path.read_bytes():
            raise RuntimeError(f"source file is uncommitted or differs from HEAD: {relative}")
    runner_path = str(Path(__file__).resolve().relative_to(root))
    protocol_path = str(PROTOCOL_PATH.resolve().relative_to(root))
    runner_commit = git("log", "-1", "--format=%H", "--", runner_path)
    protocol_commit = git("log", "-1", "--format=%H", "--", protocol_path)
    if (not runner_commit or protocol_commit != PROTOCOL_COMMIT or runner_commit == protocol_commit or
            subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor", protocol_commit,
                            runner_commit], capture_output=True).returncode):
        raise RuntimeError("protocol commit must precede runner commit")
    return {"source_parent": protocol["source_parent"], "execution_commit": git("rev-parse", "HEAD"),
            "protocol_commit": protocol_commit, "runner_commit": runner_commit,
            "runner_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
            "tracked_tree_clean": True,
            "untracked_present": bool(git("ls-files", "--others", "--exclude-standard"))}


def _record_progress(output, record):
    with (output / "progress.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(_json(record) + "\n")


def _check_initializations(torch):
    from .flat_reference import FlatWorldGRU
    from .latent_model import ContactKernel
    results = {}
    for seed in SEEDS:
        values = []
        for _ in ARMS:
            torch.manual_seed(seed)
            values.append(_fingerprint(FlatWorldGRU().state_dict()))
        if len(set(values)) != 1:
            raise RuntimeError("unpaired flat initialization")
        torch.manual_seed(seed)
        results[str(seed)] = {"flat": values[0], "structured": _fingerprint(ContactKernel().state_dict())}
    return results


def _save_checkpoint(output, torch, id_arm, target, seed, name, model):
    path = output / f"{id_arm}-{target}-{seed}-{name}.pt"
    torch.save(model.state_dict(), path)
    reloaded = torch.load(path, map_location="cpu", weights_only=True)
    original = model.state_dict()
    fingerprint = _fingerprint(original)
    if (set(reloaded) != set(original) or any(
            original[key].shape != reloaded[key].shape or original[key].dtype != reloaded[key].dtype or
            not torch.equal(original[key].detach().cpu(), reloaded[key]) for key in original) or
            _fingerprint(reloaded) != fingerprint):
        raise RuntimeError("checkpoint round-trip mismatch")
    result = {"path": path.name, "sha256": sha256(path.read_bytes()).hexdigest(),
              "weight_fingerprint": fingerprint}
    _record_progress(output, {"phase": "checkpoint_verified", "arm": f"{id_arm}/{target}/{seed}",
                              "model": name, "checkpoint": result})
    return result


def _fit_all(batches, output, torch, initial_by_seed):
    """Finish every neural fit before control fitting or any evaluation score."""
    from .flat_reference import FlatWorldGRU, fit_flat
    from .latent_model import fit_kernel
    fits, metadata = {}, {}
    for seed in SEEDS:
        for id_arm, target in ARMS:
            batch, samples, _ = batches[(id_arm, target)]
            key = f"{id_arm}/{target}/{seed}"
            torch.manual_seed(seed)
            initial = _fingerprint(FlatWorldGRU().state_dict())
            if initial_by_seed[str(seed)]["flat"] != initial:
                raise ValueError("unpaired flat initialization")
            _record_progress(output, {"phase": "fit_started", "arm": key, "model": "structured"})
            start, cpu = perf_counter(), process_time()
            structured, sinfo = fit_kernel(samples, seed, steps=200, learning_rate=0.02)
            structured_cost = {"wall_seconds": perf_counter() - start, "cpu_seconds": process_time() - cpu}
            if sinfo["gradient_steps"] != 200 or not all(isfinite(sinfo[k]) for k in ("train_marginal_nll", "train_set_nll")):
                raise RuntimeError("structured fit incomplete or nonfinite")
            if any(not bool(torch.isfinite(value).all()) for value in structured.state_dict().values()):
                raise RuntimeError("nonfinite structured weights")
            _record_progress(output, {"phase": "fit_finished", "arm": key, "model": "structured", "cost": structured_cost})
            paths = {"structured": _save_checkpoint(output, torch, id_arm, target, seed, "structured", structured)}
            _record_progress(output, {"phase": "fit_started", "arm": key, "model": "flat"})
            start, cpu = perf_counter(), process_time()
            flat, finfo = fit_flat(batch, seed, max_steps=200, fixed_steps=200,
                                   wall_budget_seconds=3600.0, learning_rate=0.02)
            flat_cost = {"wall_seconds": perf_counter() - start, "cpu_seconds": process_time() - cpu}
            if finfo["gradient_steps"] != 200 or not isfinite(finfo["training_sensor_nll"]):
                raise RuntimeError("flat fit incomplete or nonfinite")
            _record_progress(output, {"phase": "fit_finished", "arm": key, "model": "flat", "cost": flat_cost})
            if any(not bool(torch.isfinite(value).all()) for value in flat.state_dict().values()):
                raise RuntimeError("nonfinite flat weights")
            paths["flat"] = _save_checkpoint(output, torch, id_arm, target, seed, "flat", flat)
            fits[(id_arm, target, seed)] = {"kernel": structured.freeze(), "flat": flat}
            metadata[key] = {"initial_flat_fingerprint": initial, "structured_training": sinfo,
                             "flat_training": finfo, "structured_cost": structured_cost,
                             "flat_cost": flat_cost,
                             "checkpoints": paths}
            _record_progress(output, {"phase": "checkpoints_verified", "arm": key, "checkpoints": paths})
    return fits, metadata


def _fit_controls(batches, fits, output):
    """Fit controls once per ID arm, shared across target arms and seeds."""
    metadata = {}
    for id_arm in ("repeated", "augmented"):
        histories = batches[(id_arm, "full")][2]
        controls, info = {}, {}
        for name, factory in (("event", EventMemory.fit), ("literal", HistoryMemory.fit_full_sensor),
                              ("role", RoleHistoryMemory.fit)):
            _record_progress(output, {"phase": "control_fit_started", "id_arm": id_arm, "model": name})
            start, cpu = perf_counter(), process_time()
            table = factory(histories)
            cost = {"wall_seconds": perf_counter() - start, "cpu_seconds": process_time() - cpu}
            controls[name] = table
            rows = table.rows if name == "event" else (table._rows if name == "literal" else table._memory._rows)
            count = table.eligible_events if name == "event" else (table.complete_targets if name == "literal" else table._memory.complete_targets)
            if count != (1536 if name == "event" else 1920):
                raise ValueError("control target inventory mismatch")
            info[name] = {"cost": cost, "entries": len(rows), "targets": count,
                          "table_sha256": sha256(_json(rows).encode()).hexdigest()}
            _record_progress(output, {"phase": "control_fit_finished", "id_arm": id_arm, "model": name, **info[name]})
        for target in ("masked", "full"):
            for seed in SEEDS:
                fits[(id_arm, target, seed)].update(controls)
        metadata[id_arm] = info
    return metadata


def _evaluate_case(episode, history, fits):
    """All arm/seed/permutation replays complete before any truth access."""
    original_ids = tuple(sorted(name for name, _ in history._observations[0]))
    replays = []
    identity_agents, shared_history = {}, {}
    for names in permutations(original_ids):
        mapping = dict(zip(original_ids, names))
        renamed = rename_full_history(history, mapping)
        if rename_full_history(renamed, {v: k for k, v in mapping.items()}) != history:
            raise RuntimeError("evaluation history did not round-trip")
        for id_arm, target in ARMS:
            for seed in SEEDS:
                agents, measured = _replay(renamed, fits[(id_arm, target, seed)])
                if names not in shared_history:
                    shared_history[names] = agents[0].history
                elif agents[0].history != shared_history[names]:
                    raise RuntimeError("delivered histories differ across fits")
                if names == original_ids:
                    identity_agents[(id_arm, target, seed)] = agents
                replays.append((mapping, id_arm, target, seed, agents, measured))
    # The evaluator, including its records, remains inspectable in-process.
    truth_original = [episode.gold_after(i) for i in range(5)]
    rows = []
    for mapping, id_arm, target, seed, agents, measured in replays:
        inverse = {v: k for k, v in mapping.items()}
        ids = agents[0].ids
        steps = []
        for index, truth in enumerate(truth_original):
            renamed_truth = tuple(truth[inverse[name]] for name in ids)
            scores = {}
            original_truth = tuple(truth[name] for name in original_ids)
            for name, agent in zip(MODELS, agents, strict=True):
                score = score_forecast(*agent.forecasts[index], renamed_truth)
                score["feedback_diagnostic"] = agent.feedback_diagnostics[index]
                original_agent = identity_agents[(id_arm, target, seed)][MODELS.index(name)]
                score["renaming_comparison"] = compare_forecasts(
                    original_agent.forecasts[index], agent.forecasts[index], original_ids, mapping, original_truth)
                scores[name] = score
            steps.append({"step": index, "action": json.loads(agents[0].history[1 + 2 * index])["action"],
                          "ids": list(ids), "truth": list(renamed_truth), "models": scores})
        rows.append({"id_arm": id_arm, "target": target, "seed": seed, "mapping": mapping,
                     "public_history": [json.loads(item) for item in agents[0].history], "steps": steps,
                     "callbacks": {name: item.calls for name, item in zip(MODELS, measured, strict=True)}})
    return {"original_ids": original_ids, "case_rows": rows}


def _aggregate_case(result, rows, callback_times, paired):
    """Collect common-query summaries and paired flat regressions/fixes."""
    flat = defaultdict(dict)
    for entry in result["case_rows"]:
        id_arm, target, seed = entry["id_arm"], entry["target"], entry["seed"]
        mapping_key = tuple(sorted(entry["mapping"].items()))
        for step in entry["steps"]:
            index = step["step"]
            for name, score in step["models"].items():
                rows[(id_arm, target, seed, index, name)].append(
                    {k: v for k, v in score.items() if k not in ("world_probabilities", "renaming_comparison")})
                callbacks = entry["callbacks"][name]
                for phase, offset in (("predict", 0), ("receive", 1)):
                    call = callbacks[2 * index + offset]
                    if call["phase"] != phase or not all(isfinite(call[k]) and call[k] >= 0
                                                         for k in ("wall_seconds", "cpu_seconds")):
                        raise ValueError("invalid callback timing")
                    callback_times[(id_arm, target, seed, index, name, phase)].append(call["wall_seconds"])
            outcome = step["models"]["flat"]["map_correct"]
            if type(outcome) is not bool:
                raise ValueError("flat forecast unexpectedly abstained")
            flat[(seed, mapping_key, index)][(id_arm, target)] = outcome
    for (seed, mapping, step), outcomes in flat.items():
        if step == 2:
            continue
        if set(outcomes) != set(ARMS):
            raise ValueError("missing paired flat outcome")
        contrasts = (("target/repeated", ("repeated", "masked"), ("repeated", "full")),
                     ("target/augmented", ("augmented", "masked"), ("augmented", "full")),
                     ("id/masked", ("repeated", "masked"), ("augmented", "masked")),
                     ("id/full", ("repeated", "full"), ("augmented", "full")))
        for label, before_key, after_key in contrasts:
            before, after = outcomes[before_key], outcomes[after_key]
            counts = paired[(seed, label)]
            counts["queries"] += 1
            counts["before_correct"] += before
            counts["after_correct"] += after
            counts["fixed"] += after and not before
            counts["regressed"] += before and not after


def _results_summary(rows, callback_times, paired):
    expected_scores = {(a, m, seed, step, model) for a, m in ARMS for seed in SEEDS
                       for step in range(5) for model in MODELS}
    expected_timing = {(*key, phase) for key in expected_scores for phase in ("predict", "receive")}
    expected_paired = {(seed, label) for seed in SEEDS
                       for label in ("target/repeated", "target/augmented", "id/masked", "id/full")}
    if set(rows) != expected_scores or set(callback_times) != expected_timing or set(paired) != expected_paired:
        raise RuntimeError("summary key inventory mismatch")
    summaries = []
    for key, value in sorted(rows.items()):
        if len(value) != 384:
            raise RuntimeError("incomplete summary denominator")
        summaries.append({"id_arm": key[0], "target": key[1], "seed": key[2], "step": key[3],
                          "model": key[4], **_summary(value)})
    latency = []
    for key, values in sorted(callback_times.items()):
        if len(values) != 384:
            raise RuntimeError("incomplete callback timing denominator")
        values.sort()
        latency.append({"id_arm": key[0], "target": key[1], "seed": key[2], "step": key[3],
                        "model": key[4], "phase": key[5], "calls": len(values),
                        "p95_wall_seconds": values[ceil(.95 * len(values)) - 1]})
    contrasts = []
    for (seed, name), counts in sorted(paired.items()):
        if counts["queries"] != 1536:
            raise RuntimeError("incomplete paired contrast denominator")
        contrasts.append({"seed": seed, "contrast": name, **counts,
                          "difference": (counts["after_correct"] - counts["before_correct"]) / counts["queries"]})
    interactions = []
    primary = []
    for seed in SEEDS:
        arm_counts = {}
        for id_arm, target in ARMS:
            values = [item for step in (0, 1, 3, 4)
                      for item in rows[(id_arm, target, seed, step, "flat")]]
            if len(values) != 1536 or any(type(item["map_correct"]) is not bool for item in values):
                raise RuntimeError("primary score denominator or status mismatch")
            correct = sum(item["map_correct"] for item in values)
            arm_counts[(id_arm, target)] = correct
            primary.append({"seed": seed, "id_arm": id_arm, "target": target,
                            "queries": 1536, "correct": correct, "accuracy": correct / 1536})
        repeated, augmented = paired[(seed, "target/repeated")], paired[(seed, "target/augmented")]
        if (repeated["before_correct"] != arm_counts[("repeated", "masked")] or
                repeated["after_correct"] != arm_counts[("repeated", "full")] or
                augmented["before_correct"] != arm_counts[("augmented", "masked")] or
                augmented["after_correct"] != arm_counts[("augmented", "full")]):
            raise RuntimeError("paired totals disagree with primary summaries")
        interactions.append({"seed": seed, "difference_in_differences":
                             ((augmented["after_correct"] - augmented["before_correct"]) -
                              (repeated["after_correct"] - repeated["before_correct"])) / 1536})
    return summaries, latency, primary, contrasts, interactions


def _write_failure(output, phase, exc, completed_cases):
    """Best-effort incomplete record; remove any partial success artifacts."""
    (output / "COMPLETE").unlink(missing_ok=True)
    (output / "report.json").unlink(missing_ok=True)
    checkpoints = sorted(path.name for path in output.glob("*.pt"))
    expected = [f"{id_arm}-{target}-{seed}-{name}.pt"
                for seed in SEEDS for id_arm, target in ARMS for name in ("structured", "flat")]
    (output / "FAILED.json").write_text(_json({
        "status": "INCOMPLETE", "phase": phase, "type": type(exc).__name__, "message": str(exc),
        "completed_cases": completed_cases, "missing_cases": [n for n in range(64) if n not in completed_cases],
        "present_checkpoint_files": checkpoints, "missing_checkpoint_files": sorted(set(expected) - set(checkpoints)),
        "checkpoint_note": "present files may be incomplete; verified checkpoints are listed in progress log",
        "progress_log": "progress.jsonl" if (output / "progress.jsonl").exists() else None,
        "partial_case_records": "cases.jsonl" if (output / "cases.jsonl").exists() else None}), encoding="utf-8")


def run(output_dir):
    """Run only a reviewed, frozen protocol; never overwrite prior outputs."""
    protocol = read_protocol()
    import platform
    import resource
    import torch

    if (torch.__version__ != "2.10.0+cpu" or not platform.python_version().startswith("3.13.") or
            torch.get_default_dtype() != torch.float32):
        raise RuntimeError("unapproved Python or PyTorch version")
    if (torch.version.cuda is not None or torch.version.hip is not None or
            (hasattr(torch.backends, "mps") and torch.backends.mps.is_available()) or
            (hasattr(torch, "xpu") and torch.xpu.is_available())):
        raise RuntimeError("CPU-only PyTorch required")
    lineage = _lineage(protocol)
    output = Path(output_dir).resolve()
    if output.is_relative_to(Path(__file__).resolve().parents[2]):
        raise ValueError("output directory must be outside the source tree")
    output.mkdir(parents=False, exist_ok=False)
    old_threads, old_deterministic = torch.get_num_threads(), torch.are_deterministic_algorithms_enabled()
    old_warn_only = torch.is_deterministic_algorithms_warn_only_enabled()
    started, cpu_started = perf_counter(), process_time()
    phase, completed_cases = "preparation", []
    restored = False
    try:
        with torch.random.fork_rng(devices=[]):
            torch.set_num_threads(1)
            torch.use_deterministic_algorithms(True)
            prepared = {name: prepare_training(name) for name in ("repeated", "augmented")}
            batches = _check_batches(prepared, torch)
            evaluation = _prepare_evaluation(prepared)
            initializations = _check_initializations(torch)
            sensor_fingerprints = {
                name: sha256(_json([record.full.history for record in prepared[name]]).encode()).hexdigest()
                for name in ("repeated", "augmented")}
            sensor_fingerprints["evaluation"] = sha256(_json([
                [history._observations, history._action_records] for _, history in evaluation]).encode()).hexdigest()
            fingerprints, feature_counts = {}, {}
            for id_arm, target in ARMS:
                batch, samples, _ = batches[(id_arm, target)]
                fingerprints[f"{id_arm}/{target}"] = _fingerprint({
                    "features": batch[0], "targets": batch[1], "valid": batch[2],
                    "contacts": samples.contact, "episode_ids": samples.episode_id,
                    "interventions": samples.intervention})
                feature_counts[f"{id_arm}/{target}"] = [int(torch.count_nonzero(batch[0][:, :, i]))
                                                           for i in range(batch[0].shape[-1])]
            preprocessing = {"wall_seconds": perf_counter() - started, "cpu_seconds": process_time() - cpu_started,
                             "warmup": "none"}
            phase = "neural_fitting"
            fits, metadata = _fit_all(batches, output, torch, initializations)
            phase = "control_fitting"
            controls = _fit_controls(batches, fits, output)
            phase = "evaluation"
            rows, callback_times, paired = defaultdict(list), defaultdict(list), defaultdict(Counter)
            evaluation_start, evaluation_cpu = perf_counter(), process_time()
            with (output / "cases.jsonl").open("x", encoding="utf-8") as stream:
                for case, (episode, history) in enumerate(evaluation):
                    _record_progress(output, {"phase": "case_started", "case": case})
                    result = _evaluate_case(episode, history, fits)
                    result["case"] = case
                    stream.write(_json(result) + "\n")
                    stream.flush()
                    _aggregate_case(result, rows, callback_times, paired)
                    completed_cases.append(case)
                    _record_progress(output, {"phase": "case_finished", "case": case})
            replay_cost = {"wall_seconds": perf_counter() - evaluation_start,
                           "cpu_seconds": process_time() - evaluation_cpu}
            phase = "verification"
            summaries, latency, primary, contrasts, interactions = _results_summary(rows, callback_times, paired)
            if len(metadata) != 20 or len(completed_cases) != 64:
                raise RuntimeError("incomplete output inventory")
            for record in metadata.values():
                for checkpoint in record["checkpoints"].values():
                    if sha256((output / checkpoint["path"]).read_bytes()).hexdigest() != checkpoint["sha256"]:
                        raise ValueError("checkpoint hash changed")
            try:
                cpu_model = next((line.split(":", 1)[1].strip() for line in Path("/proc/cpuinfo").read_text().splitlines()
                                  if line.lower().startswith("model name")), platform.processor() or "unknown")
            except OSError:
                cpu_model = platform.processor() or "unknown"
            case_hash = sha256()
            with (output / "cases.jsonl").open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    case_hash.update(chunk)
            report = {"status": "PUBLIC_DEVELOPMENT_NOT_G1", "protocol_sha256": PROTOCOL_SHA256,
                      "protocol": protocol, "lineage": lineage, "fits": metadata, "controls": controls,
                      "initial_fingerprints": initializations, "training_tensor_fingerprints": fingerprints,
                      "training_nonzero_counts_by_feature": feature_counts,
                      "sensor_history_fingerprints": sensor_fingerprints,
                      "preprocessing": preprocessing, "evaluation_cost": replay_cost,
                      "cases_sha256": case_hash.hexdigest(), "summaries": summaries, "callback_p95": latency,
                      "primary": primary, "paired_contrasts": contrasts, "interactions": interactions,
                      "environment": {"python": platform.python_version(), "torch": torch.__version__,
                                      "platform": platform.platform(), "cpu_model": cpu_model,
                                      "torch_config_sha256": sha256(torch.__config__.show().encode()).hexdigest(),
                                      "threads": torch.get_num_threads(), "inter_op_threads": torch.get_num_interop_threads(),
                                      "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
                                      "peak_rss_platform_units": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                                      "peak_rss_unit": ("KiB" if platform.system() == "Linux" else
                                                        "bytes" if platform.system() == "Darwin" else "platform-defined")},
                      "wall_seconds": perf_counter() - started, "cpu_seconds": process_time() - cpu_started}
            phase = "restore_runtime"
            torch.set_num_threads(old_threads)
            torch.use_deterministic_algorithms(old_deterministic, warn_only=old_warn_only)
            restored = True
            phase = "publication"
            (output / "report.json").write_text(_json(report), encoding="utf-8")
            (output / "COMPLETE").write_text(sha256(_json(report).encode()).hexdigest() + "\n", encoding="ascii")
            return report
    except BaseException as exc:
        try:
            _write_failure(output, phase, exc, completed_cases)
        except OSError:
            pass
        raise
    finally:
        if not restored:
            torch.set_num_threads(old_threads)
            torch.use_deterministic_algorithms(old_deterministic, warn_only=old_warn_only)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True)
    run(parser.parse_args().output_dir)
