"""ConstructionSignatureIndex — indexed search for construction schemas.
"""

from __future__ import annotations

from typing import Any
from collections import defaultdict


class ConstructionSignatureIndex:
    """Indexes construction schemas by signature and language.
    
    A construction signature typically includes slot patterns, 
    ordering/dependency constraints, and language tag.
    """
    
    def __init__(self) -> None:
        self._by_language: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self._by_signature: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self._by_slot_count: dict[int, list[dict[str, Any]]] = defaultdict(list)
    
    def index_construction(self, language: str, construction: dict[str, Any]) -> None:
        self._by_language[language].append(construction)
        
        sig = construction.get("signature", "")
        if sig:
            self._by_signature[sig].append(construction)
        
        slots = construction.get("slots", [])
        self._by_slot_count[len(slots)].append(construction)
    
    def by_language(self, language: str) -> list[dict[str, Any]]:
        return list(self._by_language.get(language, []))
    
    def by_signature(self, signature: str) -> list[dict[str, Any]]:
        return list(self._by_signature.get(signature, []))
    
    def clear(self) -> None:
        self._by_language.clear()
        self._by_signature.clear()
        self._by_slot_count.clear()
