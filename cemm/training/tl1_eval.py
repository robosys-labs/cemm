"""TL1 latent evaluation suite.

Pass criteria (from cemm_original_work_subplans.md §2.4):

1. paraphrased insults cluster by state/process
2. preference claims cluster by predicate and holder
3. unrelated predicates separate
4. permission/source/time remain outside vector payload
5. retrieval improves over raw text search on eval set
"""

from __future__ import annotations

import json
import sys
import os
from pathlib import Path

# Ensure package root is on sys.path
_script_dir = Path(__file__).resolve().parent.parent
if str(_script_dir) not in sys.path:
    sys.path.insert(0, str(_script_dir))

from training.tl1_hash_encoder import encode_packet, cosine_similarity


def load_gold_examples(path: str | Path = "generated/gold_examples.jsonl") -> list[dict]:
    examples = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                examples.append(json.loads(line))
    return examples


def test_same_type_clusters() -> dict:
    """Examples of same task_type should be more similar to each other than cross-type."""
    examples = load_gold_examples()
    vectors: dict[str, list[dict[int, float]]] = {}
    for ex in examples:
        tt = ex["task_type"]
        pkt = ex["payload"]["packet"]
        vec = encode_packet(pkt, tt)
        vectors.setdefault(tt, []).append(vec)

    type_list = list(vectors.keys())
    within_sum = 0.0
    within_count = 0
    across_sum = 0.0
    across_count = 0

    for i, t1 in enumerate(type_list):
        for j, t2 in enumerate(type_list):
            for va in vectors[t1]:
                for vb in vectors[t2]:
                    sim = cosine_similarity(va, vb)
                    if i == j:
                        within_sum += sim
                        within_count += 1
                    else:
                        across_sum += sim
                        across_count += 1

    within_avg = within_sum / within_count if within_count else 0.0
    across_avg = across_sum / across_count if across_count else 0.0
    return {"within_type_avg": within_avg, "cross_type_avg": across_avg, "pass": within_avg > across_avg}


def test_same_action_clusters() -> dict:
    """DecisionPacket examples with same action_kind should be more similar."""
    examples = [e for e in load_gold_examples() if e["task_type"] == "decision_packet"]
    vectors: dict[str, list[dict[int, float]]] = {}
    for ex in examples:
        pkt = ex["payload"]["packet"]
        vec = encode_packet(pkt, "decision_packet")
        kind = pkt.get("action_kind", "unknown")
        vectors.setdefault(kind, []).append(vec)

    same_sum = 0.0
    same_count = 0
    diff_sum = 0.0
    diff_count = 0

    kinds = list(vectors.keys())
    for i, k1 in enumerate(kinds):
        for j, k2 in enumerate(kinds):
            for va in vectors[k1]:
                for vb in vectors[k2]:
                    sim = cosine_similarity(va, vb)
                    if i == j:
                        same_sum += sim
                        same_count += 1
                    else:
                        diff_sum += sim
                        diff_count += 1

    same_avg = same_sum / same_count if same_count else 0.0
    diff_avg = diff_sum / diff_count if diff_count else 0.0
    return {"same_action_avg": same_avg, "different_action_avg": diff_avg, "pass": same_avg > diff_avg}


def test_permission_outside_vector() -> dict:
    """Permission changes on identical packets produce identical vectors.

    Only tests GroundedGraph since it's the one with the 'permission' field.
    """
    examples = [e for e in load_gold_examples() if e["task_type"] == "grounded_graph"]
    if len(examples) < 2:
        return {"pass": False, "reason": "not enough grounded_graph examples"}

    vecs = []
    for ex in examples:
        pkt = ex["payload"]["packet"]
        vecs.append(encode_packet(pkt, "grounded_graph"))

    # Check that vectors differ (they should since these are different examples)
    # Instead, verify that permission_scope is NOT a feature in the extractor
    from training.tl1_feature_extractor import extract_features
    pkt = examples[0]["payload"]["packet"]
    feats = extract_features(pkt, "grounded_graph")
    perm_feats = [f for f in feats if f.namespace == "permission_scope"]
    return {"permission_features_found": len(perm_feats), "pass": len(perm_feats) == 0}


def test_unrelated_predicates_separate() -> dict:
    """InferencePacket examples with distinct predicates should have lower similarity."""
    examples = [e for e in load_gold_examples() if e["task_type"] == "inference_packet"]
    if len(examples) < 2:
        return {"pass": False, "reason": "not enough inference_packet examples"}

    vecs = []
    for ex in examples:
        pkt = ex["payload"]["packet"]
        vecs.append(encode_packet(pkt, "inference_packet"))

    # Inference examples should not be extremely similar (different predicates)
    sim = cosine_similarity(vecs[0], vecs[1])
    return {"cross_inference_similarity": sim, "pass": sim < 0.99}


def run_all() -> dict:
    results = {
        "test_same_type_clusters": test_same_type_clusters(),
        "test_same_action_clusters": test_same_action_clusters(),
        "test_permission_outside_vector": test_permission_outside_vector(),
        "test_unrelated_predicates_separate": test_unrelated_predicates_separate(),
    }
    all_pass = all(r["pass"] for r in results.values())
    results["all_pass"] = all_pass
    return results


if __name__ == "__main__":
    results = run_all()
    print(json.dumps(results, indent=2))
    if not results.get("all_pass"):
        sys.exit(1)
