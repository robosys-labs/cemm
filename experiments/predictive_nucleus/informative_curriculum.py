"""Public equal-action-cost probe curriculum and one-update wiring only.

The simulator supplies known physics and noiseless sensors. The diagnostic
probe is authored, not discovered by the learner. No sealed challenge, learned
accuracy comparison, independent custody or G1 admission is provided here.
"""
from collections import Counter, defaultdict
from itertools import permutations, product
import json
from pathlib import Path
import platform
import resource
from time import perf_counter

from .schedule_fixture import SensorEpisode
from .world import Action, World, observe, step

QUERY_STEP = 5
N_CASES = 128


def make_history(case, *, informative, composition=False):
    if (type(case) is not int or not 0 <= case < N_CASES or
            type(informative) is not bool or type(composition) is not bool):
        raise ValueError("invalid public curriculum selection")
    initial = tuple((case >> shift) & 1 for shift in (6, 5, 4))
    orientation, x, y, reverse = ((case >> shift) & 1 for shift in (3, 2, 1, 0))
    ids = ("unit-a", "unit-b", "unit-c")
    a, b, c = ids
    left, right = (b, c) if composition else (a, b)
    probe = int(informative)
    query = (right, left) if reverse else (left, right)
    actions = (Action("set", (a,), probe), Action("set", (b,), probe), Action("contact", (a, b)),
               Action("set", (left,), x), Action("set", (right,), y), Action("contact", query),
               Action("observe"))
    world = World(ids, initial, orientation)
    observations = []
    for t in range(len(actions) + 1):
        if t:
            world = step(world, actions[t - 1])
        sensor = observe(world, t, ids if t % 2 == 0 else ids[::-1])
        observations.append(tuple((m["id"], m["bit"]) for m in sensor["measurements"]))
    records = tuple((a.kind, a.participants, a.value) for a in actions)
    return SensorEpisode(tuple(observations), records)


def rename(history, names):
    ids = tuple(sorted(n for n, _ in history._observations[0]))
    if type(names) is not tuple or len(names) != 3 or set(names) != set(ids):
        raise ValueError("expected a permutation of the anchor IDs")
    mapping = dict(zip(ids, names, strict=True))
    return SensorEpisode(tuple(tuple((mapping[n], bit) for n, bit in row) for row in history._observations),
                         tuple((k, tuple(mapping[n] for n in members), v) for k, members, v in history._action_records))


def histories(*, informative, composition=False):
    """128 public factorial cases times six related ID views, not 768 independent worlds."""
    result = []
    for case in range(N_CASES):
        original = make_history(case, informative=informative, composition=composition)
        ids = tuple(sorted(n for n, _ in original._observations[0]))
        result.extend(rename(original, names) for names in permutations(ids))
    return tuple(result)


def feasibility(records, *, query=QUERY_STEP):
    """Finite-fixture deterministic ceiling, grouping ONLY preforecast evidence.

    This evaluator statistic does not show that a learned model reaches the
    ceiling; it assumes a predictor can learn the fixture's outcome frequency.
    """
    groups = defaultdict(Counter)
    for history in records:
        if type(query) is not int or not 0 <= query < len(history.actions):
            raise ValueError("invalid query position")
        prefix = (tuple(tuple(sorted(r)) for r in history._observations[:query + 1]),
                  history._action_records[:query + 1])
        target = tuple(bit for _, bit in sorted(history._observations[query + 1]))
        groups[prefix][target] += 1
    if not groups:
        raise ValueError("no histories")
    count = sum(sum(v.values()) for v in groups.values())
    correct = sum(max(v.values()) for v in groups.values())
    return {"queries": count, "distinct_observable_prefixes": len(groups),
            "ambiguous_prefixes": sum(len(v) > 1 for v in groups.values()),
            "finite_fixture_max_correct": correct, "finite_fixture_map_ceiling": correct / count}


def model_factories():
    from .joint_objective import JointFlatGRU, JointKernel
    return {"kernel_supplied_persistence": lambda: JointKernel(persistence=True),
            "kernel_learned_persistence": JointKernel,
            "kernel_untied_roles": lambda: JointKernel(role_tying=False),
            "kernel_memory_reset": lambda: JointKernel(memory=False),
            "flat": JointFlatGRU,
            "flat_supplied_persistence": lambda: JointFlatGRU(persistence=True)}


def smoke():
    """One optimizer update per arm/condition, no held-out model scoring or tuning."""
    import torch
    from .joint_objective import batch_histories, fit
    if (torch.__version__ != "2.10.0+cpu" or torch.version.cuda is not None or torch.version.hip is not None):
        raise RuntimeError("wiring smoke requires PyTorch 2.10.0+cpu")
    old = (torch.get_num_threads(), torch.are_deterministic_algorithms_enabled(),
           torch.is_deterministic_algorithms_warn_only_enabled())
    started = perf_counter()
    results, ceilings = {}, {}
    try:
        with torch.random.fork_rng(devices=[]):
            torch.set_num_threads(1)
            torch.use_deterministic_algorithms(True)
            for informative in (False, True):
                condition = "informative" if informative else "uninformative"
                records = histories(informative=informative)
                batch = batch_histories(records)
                ceilings[condition] = {"training": feasibility(records),
                    "public_composition": feasibility(histories(informative=informative, composition=True))}
                results[condition] = {}
                for name, factory in model_factories().items():
                    torch.manual_seed(7)
                    result = fit(factory(), batch, updates=1, cpu_seconds=30.0)
                    if result["completed_updates"] != 1 or result["initial_weights_sha256"] == result["final_weights_sha256"]:
                        raise RuntimeError("one-update wiring failed")
                    results[condition][name] = result
                if len({r["training_input_sha256"] for r in results[condition].values()}) != 1:
                    raise RuntimeError("models received different histories")
            for name in model_factories():
                if results["informative"][name]["initial_weights_sha256"] != results["uninformative"][name]["initial_weights_sha256"]:
                    raise RuntimeError("condition initialization differs")
            try:
                cpu = next(line.split(":", 1)[1].strip() for line in Path("/proc/cpuinfo").read_text().splitlines()
                           if line.lower().startswith("model name"))
            except (OSError, StopIteration):
                cpu = platform.processor() or "unknown"
            return {"status": "PUBLIC_COMMON_OBJECTIVE_WIRING_ONLY", "gate_g1": "HOLD_REVISE",
                    "independent_scientific_review": False, "learned_evaluation_run": False,
                    "physical_factorial_cases_per_condition": N_CASES, "related_id_views_per_case": 6,
                    "actions_per_history": 7, "prequery_probe_actions": 3,
                    "prequery_reset_actions": 2, "query_step_zero_based": QUERY_STEP,
                    "observed_bits_per_history_including_anchor": 24,
                    "objective": "mean full-world NLL over all 5376 measured events per update",
                    "resource_claim": "common ceilings only; actual CPU/updates are reported, not equal consumed compute",
                    "ceilings": ceilings, "fits": results,
                    "environment": {"python": platform.python_version(), "torch": torch.__version__,
                        "cpu": cpu, "platform": platform.platform(), "intraop_threads": torch.get_num_threads(),
                        "interop_threads": torch.get_num_interop_threads(), "deterministic_algorithms": True,
                        "peak_rss": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                        "peak_rss_unit": "KiB" if platform.system() == "Linux" else "platform-dependent"},
                    "wall_seconds": perf_counter() - started}
    finally:
        torch.set_num_threads(old[0])
        torch.use_deterministic_algorithms(old[1], warn_only=old[2])


if __name__ == "__main__":
    print(json.dumps(smoke(), indent=2, sort_keys=True, allow_nan=False))
