"""Post-hoc persistence counterfactual over an hash-verified public archive.

This reads already-produced probabilities. It does not fit a model or run a
challenge. The lifted forecast supplies persistence for nonparticipants from
latest delivered observations. It is not evidence that the flat GRU learned
persistence, or an independently held evaluation.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from hashlib import sha256
from itertools import product
import json
from math import fsum, isclose
from pathlib import Path
from zipfile import ZipFile

from .development_run import _summary, score_forecast

ARCHIVE = Path(__file__).with_name("results") / "public-composition-v2-1f6f5bb.zip"
ARCHIVE_SHA256 = "c0dc4f5e696d71b237242df67e7ecc8b8e941094e29afd0febfb47efce38b08f"
MEMBER = "public-composition-diagnostic.json"


def read_archive(path=ARCHIVE):
    """Verify the complete ZIP before accepting its sole expected member."""
    raw = Path(path).read_bytes()
    if sha256(raw).hexdigest() != ARCHIVE_SHA256:
        raise ValueError("public artifact SHA-256 mismatch")
    from io import BytesIO
    with ZipFile(BytesIO(raw)) as archive:
        if archive.namelist() != [MEMBER]:
            raise ValueError("unexpected public artifact inventory")
        return json.loads(archive.read(MEMBER))


def lift_distribution(ids, participants, latest, probabilities):
    """Marginalize nonparticipants, then impose latest-reading persistence."""
    if (len(ids) != len(set(ids)) or tuple(sorted(ids)) != tuple(ids) or
            len(participants) != len(set(participants)) or not participants or
            not set(participants) <= set(ids) or set(latest) != set(ids) or
            any(type(latest[x]) is not int or latest[x] not in (0, 1) for x in ids)):
        raise ValueError("invalid lifting context")
    expected = set(product((0, 1), repeat=len(ids)))
    if set(probabilities) != expected or any(not 0 <= p <= 1 for p in probabilities.values()):
        raise ValueError("invalid full-world distribution")
    if not isclose(fsum(probabilities.values()), 1.0, abs_tol=1e-6):
        raise ValueError("unnormalized full-world distribution")
    indices = tuple(ids.index(name) for name in participants)
    grouped = defaultdict(list)
    for world, probability in probabilities.items():
        grouped[tuple(world[i] for i in indices)].append(probability)
    lifted = {}
    for bits, masses in grouped.items():
        values = dict(latest)
        values.update(zip(participants, bits, strict=True))
        lifted[tuple(values[name] for name in ids)] = fsum(masses)
    total = fsum(lifted.values())
    return {world: mass / total for world, mass in lifted.items()}


def _readings(observation, ids=None):
    if (type(observation) is not dict or set(observation) != {"t", "measurements"} or
            type(observation["t"]) is not int or type(observation["measurements"]) is not list):
        raise ValueError("invalid observation")
    result = {}
    for item in observation["measurements"]:
        if (type(item) is not dict or set(item) != {"id", "bit"} or
                type(item["id"]) is not str or not item["id"] or item["id"] in result or
                type(item["bit"]) is not int or item["bit"] not in (0, 1)):
            raise ValueError("invalid measurement")
        result[item["id"]] = item["bit"]
    if ids is not None and not set(result) <= set(ids):
        raise ValueError("unknown measurement identity")
    return result


def audit_case(case):
    """Copy and annotate one case, consuming feedback only after each forecast."""
    result = deepcopy(case)
    history, steps = result["public_history"], result["steps"]
    if len(history) != 1 + 2 * len(steps):
        raise ValueError("misaligned public history")
    anchor = history[0]
    if anchor["t"] != 0:
        raise ValueError("invalid anchor time")
    latest = _readings(anchor)
    ids = tuple(sorted(latest))
    previous = anchor
    for i, step in enumerate(steps):
        turn, feedback = history[1 + 2 * i:3 + 2 * i]
        if (step["step"] != i or tuple(step["ids"]) != ids or
                turn != {"observation": previous, "action": step["action"]} or
                step["action_kind"] != step["action"]["kind"] or feedback["t"] != i + 1):
            raise ValueError("inconsistent public chronology")
        measured = _readings(feedback, ids)
        action = step["action"]
        members = action["participants"]
        if action["kind"] == "observe":
            step["persistence_lift"] = {"status": "NOT_SCORED", "reason": "observe has no participants"}
        elif action["kind"] in ("contact", "set"):
            original = step["models"]["flat"]
            worlds = original["world_probabilities"]
            probabilities = {tuple(item["world"]): item["probability"] for item in worlds}
            if len(probabilities) != len(worlds):
                raise ValueError("duplicate archived world")
            # Construct the counterfactual before consulting evaluator truth.
            lifted = lift_distribution(ids, members, latest, probabilities)
            truth = tuple(step["truth"])
            original_check = score_forecast("PREDICTED", None, probabilities, truth)
            if (original_check["map_world"] != original["map_world"] or
                    original_check["map_correct"] != original["map_correct"]):
                raise ValueError("archived flat MAP disagrees with distribution")
            score = score_forecast("PREDICTED", None, lifted, truth)
            was, now = original["map_correct"], score["map_correct"]
            change = ("corrected" if now and not was else "regressed" if was and not now else
                      "unchanged_correct" if now else "unchanged_incorrect")
            score.update({"change": change, "latest_readings_before_prediction": dict(latest),
                          "nonparticipant_readings_match_truth": all(latest[name] == truth[j]
                              for j, name in enumerate(ids) if name not in members)})
            step["persistence_lift"] = score
        else:
            raise ValueError("unexpected action")
        latest.update(measured)
        previous = feedback
    return result


def analyze(artifact):
    """Preserve each archived case and add scored post-hoc counterfactuals."""
    result = {key: deepcopy(value) for key, value in artifact.items() if key != "results"}
    result.update({"analysis": "POST_HOC_SUPPLIED_NONPARTICIPANT_PERSISTENCE",
                   "archive_sha256": ARCHIVE_SHA256,
                   "analysis_limitations": [
                       "Opened public cases, reused across seeds; no independent generalization claim.",
                       "Latest-reading persistence is supplied to the flat forecasts, not learned by the GRU.",
                       "Feedback is consumed only after each forecast; observe actions are not scored by this lift.",
                       "Comparisons do not establish matched compute or explain the entire model gap."]})
    result["results"] = []
    for run in artifact["results"]:
        output = {key: deepcopy(value) for key, value in run.items() if key != "cases"}
        output["cases"] = [audit_case(case) for case in run["cases"]]
        steps = [step for case in output["cases"] for step in case["steps"]]
        eligible = [step for step in steps if step["action_kind"] in ("contact", "set")]
        summaries = {}
        for group, rows in [("contact_set", eligible)] + [
            (f"step_{i}", [s for s in eligible if s["step"] == i])
            for i in sorted({s["step"] for s in eligible})
        ]:
            before = [s["models"]["flat"] for s in rows]
            after = [s["persistence_lift"] for s in rows]
            summaries[group] = {"original_flat": _summary(before), "persistence_lift": _summary(after),
                                "change_counts": dict(Counter(s["change"] for s in after)),
                                "nonparticipant_readings_match_truth": sum(
                                    s["nonparticipant_readings_match_truth"] for s in after)}
        output["post_hoc_summaries"] = summaries
        result["results"].append(output)
    return result


def main():
    print(json.dumps(analyze(read_archive()), sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
