"""Sensor-only preparation for a proposed, unrun public development study.

This module prepares repeated views of the opened one-pair histories, not
independent episodes, a held-out challenge, model fits, or scored outcomes.
The flat-loss mask never changes the realized full-feedback input stream.
"""
from dataclasses import dataclass
from itertools import permutations

from .causal_replay import FullSensorHistory
from .development_run import _training_history
from .full_sensor_fixture import make_full_training_history
from .relabel_diagnostic import rename_history
from .schedule_fixture import make_evaluator_episode
from .shared_training_smoke import CollectedEpisode, collect_shared_full_sensor


@dataclass(frozen=True)
class PreparedEpisode:
    """Full sensor records and label views with mapping metadata for audit.

    A caller must pass only the intended records to each learner. This
    in-process container does not enforce that boundary or hide metadata.
    """
    history: FullSensorHistory
    full: CollectedEpisode
    masked: CollectedEpisode
    mapping: tuple


def rename_full_history(history, mapping):
    """Consistently relabel an explicit full-sensor history, preserving its type.

    The mapping must be a bijection among the existing anchor IDs; it does
    not generate new entities or change the physical observations or action
    order. Applying its inverse restores the exact immutable source history.
    """
    if type(history) is not FullSensorHistory or type(mapping) is not dict:
        raise ValueError("expected full sensor history and a mapping")
    ids = tuple(sorted(name for name, _ in history._observations[0]))
    if (any(type(key) is not str or type(value) is not str for key, value in mapping.items()) or
            set(mapping) != set(ids) or set(mapping.values()) != set(ids) or len(mapping) != len(ids)):
        raise ValueError("mapping must bijectively permute anchor IDs")
    observations = tuple(tuple((mapping[name], bit) for name, bit in observation)
                         for observation in history._observations)
    actions = tuple((kind, tuple(mapping[name] for name in participants), value)
                    for kind, participants, value in history._action_records)
    return FullSensorHistory(observations, actions)


def _prepare(history, partial, mapping):
    renamed_partial = rename_history(partial, mapping)
    renamed = rename_full_history(history, mapping)
    inverse = {value: key for key, value in mapping.items()}
    if rename_full_history(renamed, inverse) != history or rename_history(renamed_partial, inverse) != partial:
        raise RuntimeError("renaming did not round trip")
    if renamed._action_records != renamed_partial._action_records:
        raise RuntimeError("renamed action histories differ")
    if any(full[:len(old)] != old for full, old in zip(renamed._observations,
                                                        renamed_partial._observations, strict=True)):
        raise RuntimeError("original sensor records differ")
    record = collect_shared_full_sensor(renamed)
    ids = tuple(sorted(name for name, _ in renamed._observations[0]))
    masked_rows = []
    for i, (features, targets) in enumerate(record.flat_rows):
        retained = dict(renamed_partial._observations[i + 1])
        observed = dict(renamed._observations[i + 1])
        if any(observed.get(name) != bit for name, bit in retained.items()):
            raise RuntimeError("masked targets do not match full sensor values")
        if tuple(targets[:len(ids)]) != tuple(observed[name] for name in ids):
            raise RuntimeError("flat target order differs from sorted anchor IDs")
        mask = tuple(bit if j < len(ids) and ids[j] in retained else -1
                     for j, bit in enumerate(targets))
        masked_rows.append((features, mask))
    masked = CollectedEpisode(tuple(masked_rows), record.contacts, record.interventions, record.history)
    return PreparedEpisode(renamed, record, masked, tuple(sorted(mapping.items())))


def prepare_training(id_arm):
    """Prepare 64 public histories × six repeated or consistently renamed views.

    Each loss arm receives the same features and full feedback within its ID
    arm. The old visibility affects labels only. Metadata, evaluator states,
    case indices and latent orientation are not in either collected record.
    This function does not generate model weights or score predictions.
    """
    if id_arm not in ("repeated", "augmented"):
        raise ValueError("unknown ID arm")
    result = []
    for block in (0, 1):
        for case in range(32):
            partial = _training_history(make_evaluator_episode(case, block=block))
            history = make_full_training_history(case, block=block)
            ids = tuple(sorted(name for name, _ in history._observations[0]))
            mappings = list(permutations(ids)) if id_arm == "augmented" else [ids] * 6
            for names in mappings:
                result.append(_prepare(history, partial, dict(zip(ids, names, strict=True))))
    return tuple(result)
