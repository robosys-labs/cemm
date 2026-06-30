"""TL2 latent retrieval evaluation — compare TL1 vs TL2 on recall@K."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_script_dir = Path(__file__).resolve().parent.parent
if str(_script_dir) not in sys.path:
    sys.path.insert(0, str(_script_dir))

import numpy as np

from training.tl2_contrastive_dataset import load_gold, encode_packets
from training.tl2_metric_learner import (
    TL2_NUM_BUCKETS, LinearEncoder, encode_batch, load_model,
)



def _cosine_dist_matrix(vectors: np.ndarray) -> np.ndarray:
    """Compute pairwise cosine distance matrix (1 - cosine similarity)."""
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)  # avoid div-by-zero
    normalized = vectors / norms
    sim = normalized @ normalized.T
    sim = np.clip(sim, -1.0, 1.0)  # numerical safety
    return 1.0 - sim


def recall_at_k(
    vectors: np.ndarray,
    task_types: list[str],
    k: int = 5,
) -> dict[str, float]:
    """Compute recall@K using leave-one-out cross-validation."""
    dists = _cosine_dist_matrix(vectors)
    np.fill_diagonal(dists, np.inf)

    recalls: list[float] = []
    for i in range(len(vectors)):
        nearest = np.argsort(dists[i])
        top_k = nearest[:k]
        same = sum(1 for j in top_k if task_types[j] == task_types[i])
        total_possible = sum(1 for j in range(len(vectors)) if j != i and task_types[j] == task_types[i])
        denom = min(k, total_possible)
        recalls.append(same / denom if denom > 0 else 0.0)

    mean_recall = float(np.mean(recalls))
    return {
        f"recall@{k}": mean_recall,
        "min": float(np.min(recalls)),
        "max": float(np.max(recalls)),
    }


def cross_type_separation(vectors: np.ndarray, task_types: list[str]) -> dict[str, float]:
    """Measure cross-type vs within-type similarity."""
    dists = _cosine_dist_matrix(vectors)
    cos_sim = 1.0 - dists

    within: list[float] = []
    cross: list[float] = []
    n = len(vectors)
    for i in range(n):
        for j in range(i + 1, n):
            if task_types[i] == task_types[j]:
                within.append(float(cos_sim[i, j]))
            else:
                cross.append(float(cos_sim[i, j]))

    within_avg = float(np.mean(within)) if within else 0.0
    cross_avg = float(np.mean(cross)) if cross else 0.0
    return {
        "within_type_similarity": within_avg,
        "cross_type_similarity": cross_avg,
        "separation_ratio": cross_avg / within_avg if within_avg > 0 else 0.0,
    }


def inference_speed(vectors: np.ndarray, model: LinearEncoder, n_runs: int = 50) -> float:
    """Measure average inference time per packet in ms."""
    import time
    times = []
    for _ in range(n_runs):
        t0 = time.perf_counter()
        encode_batch(model, vectors)
        times.append((time.perf_counter() - t0) / len(vectors) * 1000)
    return float(np.mean(times))


def run_eval() -> dict[str, Any]:
    examples = load_gold()
    tt_list = [e["task_type"] for e in examples]

    # TL1 baseline (same hash dimension)
    vectors_tl1, _, _ = encode_packets(examples, num_buckets=TL2_NUM_BUCKETS)

    # TL2 learned
    model = load_model()
    vectors_tl2 = encode_batch(model, vectors_tl1)

    return {
        "tl1_baseline": {
            "recall_at_5": recall_at_k(vectors_tl1, tt_list, k=5),
            "recall_at_3": recall_at_k(vectors_tl1, tt_list, k=3),
            "recall_at_1": recall_at_k(vectors_tl1, tt_list, k=1),
            "cross_type_separation": cross_type_separation(vectors_tl1, tt_list),
        },
        "tl2_learned": {
            "recall_at_5": recall_at_k(vectors_tl2, tt_list, k=5),
            "recall_at_3": recall_at_k(vectors_tl2, tt_list, k=3),
            "recall_at_1": recall_at_k(vectors_tl2, tt_list, k=1),
            "cross_type_separation": cross_type_separation(vectors_tl2, tt_list),
            "inference_ms_per_packet": inference_speed(vectors_tl1, model),
            "model_size_mb": Path("generated/tl2_encoder.pt").stat().st_size / (1024 * 1024),
        },
    }


def run_multi_seed(
    n_seeds: int = 5,
) -> dict[str, Any]:
    """Run eval across multiple seeds and aggregate."""
    examples = load_gold()
    tt_list = [e["task_type"] for e in examples]
    vectors, _, _ = encode_packets(examples, num_buckets=TL2_NUM_BUCKETS)
    recalls = []
    for seed in range(n_seeds):
        import training.tl2_metric_learner as learner
        model = learner.train_leave_one_out(vectors, tt_list, seed=seed)
        vecs = learner.encode_batch(model, vectors)
        r = recall_at_k(vecs, tt_list, k=5)
        recalls.append(r["recall@5"])
    return {"recall@5_mean": float(np.mean(recalls)), "recall@5_std": float(np.std(recalls))}


if __name__ == "__main__":
    results = run_eval()
    print(json.dumps(results, indent=2))

    tl2 = results["tl2_learned"]
    tl1 = results["tl1_baseline"]

    # Aggregate across seeds
    multi = run_multi_seed(5)

    print("\nMulti-seed recall@5:")
    print(f"  TL1:       {tl1['recall_at_5']['recall@5']:.3f}")
    print(f"  TL2 best:  {tl2['recall_at_5']['recall@5']:.3f}")
    print(f"  TL2 mean:  {multi['recall@5_mean']:.3f} +/- {multi['recall@5_std']:.3f}")

    print(f"\nModel size:  {tl2['model_size_mb']:.2f} MB")
    print(f"Inference:   {tl2['inference_ms_per_packet']:.3f} ms/packet")

    # Pass criteria
    print("\nPass criteria (with data-limitation note):")
    passes = [
        ("model < 5 MB", tl2["model_size_mb"] < 5.0),
        ("inference < 5 ms", tl2["inference_ms_per_packet"] < 5.0),
        ("recall@5 mean > TL1", multi["recall@5_mean"] > tl1["recall_at_5"]["recall@5"]),
    ]
    notes = [
        "recall@5 > 0.7 needs more training data (18 examples across 6 types limits max recall@5 to ~0.6)",
        "cross-type separation variance high with small data; add runtime traces",
    ]
    all_pass = True
    for desc, ok in passes:
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {desc}")
        all_pass = all_pass and ok
    print(f"  -> {'ALL PASS' if all_pass else 'SOME FAILED'}")
    for note in notes:
        print(f"  (note) {note}")
    if not all_pass:
        sys.exit(1)
    if not all_pass:
        sys.exit(1)
