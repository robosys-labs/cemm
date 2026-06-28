from __future__ import annotations
from ..store.store import Store
from ..types.model import Model, ModelStatus
from ..types.permission import Permission, PermissionScope
import time


class ModelPromoter:
    def __init__(self, store: Store) -> None:
        self._store = store

    def promote(self, model_id: str) -> tuple[bool, str]:
        model = self._store.models.get(model_id)
        if model is None:
            return False, f"Model {model_id} not found"
        if model.status != ModelStatus.CANDIDATE:
            return False, f"Model {model_id} is {model.status.value}, not candidate"

        if model.confidence < 0.6:
            return False, f"Confidence {model.confidence:.2f} below threshold 0.6"

        if not model.evidence_signal_ids:
            return False, "No evidence signals"

        if model.trust < 0.5:
            return False, f"Trust {model.trust:.2f} below threshold 0.5"

        if model.permission and not model.permission.may_store:
            return False, "Permission does not allow storage"

        old_status = model.status
        model.status = ModelStatus.ACTIVE
        model.updated_at = time.time()
        self._store.models.put(model)

        self_state = self._store.self_store.latest()
        if self_state:
            if model.id not in self_state.learned_model_ids:
                self_state.learned_model_ids.append(model.id)
            self_state.updated_at = time.time()
            self._store.self_store.put(self_state)

        return True, f"Promoted {model.name} from {old_status.value} to active"

    def reject(self, model_id: str, reason: str = "Manual rejection") -> tuple[bool, str]:
        model = self._store.models.get(model_id)
        if model is None:
            return False, f"Model {model_id} not found"
        model.status = ModelStatus.REJECTED
        model.updated_at = time.time()
        self._store.models.put(model)
        return True, f"Rejected {model.name}: {reason}"

    def can_promote(self, model: Model) -> tuple[bool, str]:
        if model.status != ModelStatus.CANDIDATE:
            return False, f"Status is {model.status.value}"
        if model.confidence < 0.6:
            return False, f"Confidence {model.confidence:.2f} < 0.6"
        evidence_count = len(model.evidence_signal_ids)
        if evidence_count < 1:
            return False, "No evidence signals"
        if model.permission and not model.permission.may_store:
            return False, "Store permission denied"
        return True, "Ready for promotion"
