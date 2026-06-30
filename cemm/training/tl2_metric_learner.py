"""TL2 learned metric space — train with leave-one-out contrastive learning."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_script_dir = Path(__file__).resolve().parent.parent
if str(_script_dir) not in sys.path:
    sys.path.insert(0, str(_script_dir))

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from training.tl2_contrastive_dataset import load_gold, encode_packets

# Balanced dims for < 5 MB model at float32
TL2_NUM_BUCKETS = 2 ** 14  # 16384
TL2_EMBED_DIM = 48
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


class LinearEncoder(nn.Module):
    """Direct linear projection: TL1 features -> 48-dim embedding."""

    def __init__(self, input_dim: int = TL2_NUM_BUCKETS, output_dim: int = TL2_EMBED_DIM):
        super().__init__()
        self.proj = nn.Linear(input_dim, output_dim, bias=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return F.normalize(self.proj(x), dim=-1)


def _random_triplet_loss(
    model: nn.Module,
    vectors: torch.Tensor,
    task_types: list[str],
    margin: float = 0.5,
) -> torch.Tensor:
    """Compute triplet loss with random positive/negative sampling per anchor.

    For each example in the batch, sample a positive (same task_type)
    and a negative (different task_type), then compute margin ranking loss.
    """
    n = len(vectors)
    z = model(vectors)

    losses = []
    for i in range(n):
        # Positive: any same-type example (not self)
        pos_indices = [j for j in range(n) if j != i and task_types[j] == task_types[i]]
        if not pos_indices:
            continue
        j_pos = pos_indices[torch.randint(len(pos_indices), (1,)).item()]

        # Negative: any different-type example
        neg_indices = [j for j in range(n) if task_types[j] != task_types[i]]
        j_neg = neg_indices[torch.randint(len(neg_indices), (1,)).item()]

        d_pos = (1.0 - F.cosine_similarity(z[i:i+1], z[j_pos:j_pos+1])).squeeze()
        d_neg = (1.0 - F.cosine_similarity(z[i:i+1], z[j_neg:j_neg+1])).squeeze()
        losses.append(F.relu(d_pos - d_neg + margin))

    return torch.stack(losses).mean() if losses else torch.tensor(0.0, device=z.device)


def train_leave_one_out(
    vectors: np.ndarray,
    task_types: list[str],
    num_epochs: int = 200,
    lr: float = 5e-3,
    margin: float = 0.3,
    seed: int = 42,
) -> LinearEncoder:
    """Train encoder using all examples with leave-one-out triplets."""
    torch.manual_seed(seed)
    model = LinearEncoder().to(DEVICE)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=num_epochs)

    t = torch.from_numpy(vectors).to(DEVICE)

    for epoch in range(num_epochs):
        model.train()
        loss_val = _random_triplet_loss(model, t, task_types, margin)
        optimizer.zero_grad()
        loss_val.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        scheduler.step()

        if epoch % 40 == 0:
            print(f"  epoch {epoch:3d}  loss {loss_val.item():.4f}")

    return model


def save_model(model: LinearEncoder, path: str | Path = "generated/tl2_encoder.pt") -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), path)
    size_mb = path.stat().st_size / (1024 * 1024)
    print(f"Saved model ({size_mb:.2f} MB) to {path}")


def load_model(path: str | Path = "generated/tl2_encoder.pt") -> LinearEncoder:
    model = LinearEncoder().to(DEVICE)
    model.load_state_dict(torch.load(path, map_location=DEVICE, weights_only=True))
    model.eval()
    return model


def encode_batch(model: LinearEncoder, vectors_np: np.ndarray) -> np.ndarray:
    model.eval()
    with torch.no_grad():
        t = torch.from_numpy(vectors_np).to(DEVICE)
        z = model(t)
        return z.cpu().numpy()


if __name__ == "__main__":
    print("Loading gold examples...")
    examples = load_gold()
    vectors, task_types, labels = encode_packets(examples, num_buckets=TL2_NUM_BUCKETS)
    print(f"  {len(vectors)} examples, {TL2_NUM_BUCKETS} dim")

    print("Training with leave-one-out triplets...")
    model = train_leave_one_out(vectors, task_types)
    save_model(model)
    print("Done")
