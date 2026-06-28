from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum


class EntityType(str, Enum):
    PERSON = "person"
    PLACE = "place"
    ORGANIZATION = "organization"
    EVENT = "event"
    OBJECT = "object"
    CONCEPT = "concept"
    DOCUMENT = "document"
    SYSTEM = "system"
    MODEL = "model"
    UNKNOWN = "unknown"


@dataclass
class Entity:
    id: str
    type: EntityType
    name: str
    aliases: list[str]
    confidence: float
    created_from_signal_id: str
    created_at: float
    updated_at: float
    version: str = "erca.entity.v1"
