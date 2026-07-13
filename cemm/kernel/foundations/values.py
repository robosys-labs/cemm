"""Kernel value foundations — typed behavior for canonical value types.

Import boundary: model + schema submodules only. No engine imports.

Each type has canonical identity, normalization, comparison, query,
contradiction, serialization, and public-surface rules.

Types (SEMANTIC_FOUNDATIONS.md §2):
    boolean, enum, text, identifier, quantity + unit,
    set, ordered sequence, time point and interval,
    coordinate and reference frame, probability/distribution
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Iterator, Protocol


# ── Type kind enum ─────────────────────────────────────────────────


class ValueKind(str, Enum):
    BOOLEAN = "boolean"
    ENUM = "enum"
    TEXT = "text"
    IDENTIFIER = "identifier"
    QUANTITY = "quantity"
    SET = "set"
    ORDERED_SEQUENCE = "ordered_sequence"
    TIME_POINT = "time_point"
    TIME_INTERVAL = "time_interval"
    COORDINATE = "coordinate"
    PROBABILITY = "probability"
    DISTRIBUTION = "distribution"


# ── Value type protocol ────────────────────────────────────────────


class ValueTypeBehavior(Protocol):
    """Protocol for typed value behavior.

    Each kernel value type implements:
    - canonical identity
    - normalization
    - comparison
    - query
    - contradiction
    - serialization
    - public-surface rules
    """
    kind: ValueKind

    def normalize(self, raw: Any) -> Any: ...
    def identity_hash(self, normalized: Any) -> str: ...
    def compare(self, a: Any, b: Any) -> int: ...
    def contradicts(self, a: Any, b: Any) -> bool: ...
    def serialize(self, normalized: Any) -> str: ...
    def public_surface(self, normalized: Any) -> str: ...


# ── Boolean ────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class BooleanType:
    """Boolean value type with strict true/false semantics."""
    kind: ValueKind = ValueKind.BOOLEAN

    def normalize(self, raw: Any) -> bool:
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, str):
            lower = raw.strip().lower()
            if lower in ("true", "1", "yes"):
                return True
            if lower in ("false", "0", "no"):
                return False
        if isinstance(raw, (int, float)):
            return bool(raw)
        raise ValueError(f"Cannot normalize {raw!r} as boolean")

    def identity_hash(self, normalized: bool) -> str:
        return f"bool:{normalized}"

    def compare(self, a: bool, b: bool) -> int:
        if a == b:
            return 0
        return -1 if a is False else 1

    def contradicts(self, a: bool, b: bool) -> bool:
        return a is not b

    def serialize(self, normalized: bool) -> str:
        return "true" if normalized else "false"

    def public_surface(self, normalized: bool) -> str:
        return self.serialize(normalized)


# ── Enum ───────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class EnumType:
    """Enum value type with a fixed vocabulary."""
    kind: ValueKind = ValueKind.ENUM
    allowed_values: frozenset[str] = field(default_factory=frozenset)

    def normalize(self, raw: Any) -> str:
        if not isinstance(raw, str):
            raise ValueError(f"Enum value must be string, got {type(raw)}")
        lower = raw.strip().lower()
        if self.allowed_values and lower not in self.allowed_values:
            raise ValueError(f"Enum value {raw!r} not in allowed values")
        return lower

    def identity_hash(self, normalized: str) -> str:
        return f"enum:{normalized}"

    def compare(self, a: str, b: str) -> int:
        if a == b:
            return 0
        return -1 if a < b else 1

    def contradicts(self, a: str, b: str) -> bool:
        return a != b

    def serialize(self, normalized: str) -> str:
        return normalized

    def public_surface(self, normalized: str) -> str:
        return normalized


# ── Text ───────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class TextType:
    """Text value type with normalization rules."""
    kind: ValueKind = ValueKind.TEXT
    max_length: int | None = None

    def normalize(self, raw: Any) -> str:
        if not isinstance(raw, str):
            raise ValueError(f"Text value must be string, got {type(raw)}")
        normalized = raw.strip()
        if self.max_length is not None and len(normalized) > self.max_length:
            raise ValueError(f"Text exceeds max_length {self.max_length}")
        return normalized

    def identity_hash(self, normalized: str) -> str:
        import hashlib
        return f"text:{hashlib.sha256(normalized.encode('utf-8')).hexdigest()[:16]}"

    def compare(self, a: str, b: str) -> int:
        if a == b:
            return 0
        return -1 if a < b else 1

    def contradicts(self, a: str, b: str) -> bool:
        return a != b

    def serialize(self, normalized: str) -> str:
        return normalized

    def public_surface(self, normalized: str) -> str:
        return normalized


# ── Identifier ─────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class IdentifierType:
    """Identifier value type with namespace-qualified identity."""
    kind: ValueKind = ValueKind.IDENTIFIER
    namespace: str = ""

    def normalize(self, raw: Any) -> str:
        if not isinstance(raw, str):
            raise ValueError(f"Identifier must be string, got {type(raw)}")
        normalized = raw.strip().lower()
        if not normalized:
            raise ValueError("Identifier cannot be empty")
        return normalized

    def identity_hash(self, normalized: str) -> str:
        ns = self.namespace or "default"
        return f"id:{ns}:{normalized}"

    def compare(self, a: str, b: str) -> int:
        if a == b:
            return 0
        return -1 if a < b else 1

    def contradicts(self, a: str, b: str) -> bool:
        return a != b

    def serialize(self, normalized: str) -> str:
        ns = self.namespace or "default"
        return f"{ns}:{normalized}"

    def public_surface(self, normalized: str) -> str:
        return normalized


# ── Quantity + unit ────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class Quantity:
    """A quantity value with unit."""
    value: float
    unit: str

    def __post_init__(self) -> None:
        if not self.unit:
            raise ValueError("Quantity requires a unit")


@dataclass(frozen=True, slots=True)
class QuantityType:
    """Quantity value type with unit compatibility."""
    kind: ValueKind = ValueKind.QUANTITY
    compatible_units: frozenset[str] = field(default_factory=frozenset)

    def normalize(self, raw: Any) -> Quantity:
        if isinstance(raw, Quantity):
            q = raw
        elif isinstance(raw, (int, float)) and len(self.compatible_units) == 1:
            q = Quantity(float(raw), next(iter(self.compatible_units)))
        elif isinstance(raw, (tuple, list)) and len(raw) == 2:
            q = Quantity(float(raw[0]), str(raw[1]))
        else:
            raise ValueError(f"Cannot normalize {raw!r} as quantity")
        if self.compatible_units and q.unit not in self.compatible_units:
            raise ValueError(f"Unit {q.unit!r} not compatible")
        return q

    def identity_hash(self, normalized: Quantity) -> str:
        return f"qty:{normalized.value}:{normalized.unit}"

    def compare(self, a: Quantity, b: Quantity) -> int:
        if a.unit != b.unit:
            raise ValueError(f"Cannot compare quantities with different units: {a.unit} vs {b.unit}")
        if a.value == b.value:
            return 0
        return -1 if a.value < b.value else 1

    def contradicts(self, a: Quantity, b: Quantity) -> bool:
        if a.unit != b.unit:
            return False  # Different units don't contradict
        return a.value != b.value

    def serialize(self, normalized: Quantity) -> str:
        return f"{normalized.value} {normalized.unit}"

    def public_surface(self, normalized: Quantity) -> str:
        return self.serialize(normalized)


# ── Set ────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class SetType:
    """Set value type with unordered, deduplicated elements."""
    kind: ValueKind = ValueKind.SET
    element_type: str = "text"  # ValueKind name for elements

    def normalize(self, raw: Any) -> frozenset[Any]:
        if isinstance(raw, (set, frozenset)):
            return frozenset(raw)
        if isinstance(raw, (list, tuple)):
            return frozenset(raw)
        if isinstance(raw, dict):
            return frozenset(raw.keys())
        raise ValueError(f"Cannot normalize {raw!r} as set")

    def identity_hash(self, normalized: frozenset[Any]) -> str:
        import hashlib
        elements = sorted(str(e) for e in normalized)
        return f"set:{hashlib.sha256('|'.join(elements).encode()).hexdigest()[:16]}"

    def compare(self, a: frozenset[Any], b: frozenset[Any]) -> int:
        if a == b:
            return 0
        # Subset < superset
        if a < b:
            return -1
        if b < a:
            return 1
        return 0  # Incomparable but not equal

    def contradicts(self, a: frozenset[Any], b: frozenset[Any]) -> bool:
        # Sets contradict if they are disjoint
        return a.isdisjoint(b)

    def serialize(self, normalized: frozenset[Any]) -> str:
        return "{" + ", ".join(sorted(str(e) for e in normalized)) + "}"

    def public_surface(self, normalized: frozenset[Any]) -> str:
        return self.serialize(normalized)


# ── Ordered sequence ───────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class OrderedSequenceType:
    """Ordered sequence value type."""
    kind: ValueKind = ValueKind.ORDERED_SEQUENCE
    element_type: str = "text"

    def normalize(self, raw: Any) -> tuple[Any, ...]:
        if isinstance(raw, (list, tuple)):
            return tuple(raw)
        if isinstance(raw, (set, frozenset)):
            raise ValueError("Cannot normalize unordered set as ordered sequence")
        raise ValueError(f"Cannot normalize {raw!r} as ordered sequence")

    def identity_hash(self, normalized: tuple[Any, ...]) -> str:
        import hashlib
        elements = "|".join(str(e) for e in normalized)
        return f"seq:{hashlib.sha256(elements.encode()).hexdigest()[:16]}"

    def compare(self, a: tuple[Any, ...], b: tuple[Any, ...]) -> int:
        if a == b:
            return 0
        # Lexicographic comparison
        for x, y in zip(a, b):
            if x != y:
                return -1 if str(x) < str(y) else 1
        return -1 if len(a) < len(b) else 1

    def contradicts(self, a: tuple[Any, ...], b: tuple[Any, ...]) -> bool:
        # Sequences contradict if they differ at any position
        if len(a) != len(b):
            return True
        return any(x != y for x, y in zip(a, b))

    def serialize(self, normalized: tuple[Any, ...]) -> str:
        return "[" + ", ".join(str(e) for e in normalized) + "]"

    def public_surface(self, normalized: tuple[Any, ...]) -> str:
        return self.serialize(normalized)


# ── Time point ─────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class TimePointType:
    """Time point value type with UTC normalization."""
    kind: ValueKind = ValueKind.TIME_POINT

    def normalize(self, raw: Any) -> datetime:
        if isinstance(raw, datetime):
            if raw.tzinfo is None:
                return raw.replace(tzinfo=timezone.utc)
            return raw.astimezone(timezone.utc)
        if isinstance(raw, str):
            # ISO 8601 parsing
            dt = datetime.fromisoformat(raw)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        raise ValueError(f"Cannot normalize {raw!r} as time point")

    def identity_hash(self, normalized: datetime) -> str:
        return f"tp:{normalized.isoformat()}"

    def compare(self, a: datetime, b: datetime) -> int:
        if a == b:
            return 0
        return -1 if a < b else 1

    def contradicts(self, a: datetime, b: datetime) -> bool:
        return a != b

    def serialize(self, normalized: datetime) -> str:
        return normalized.isoformat()

    def public_surface(self, normalized: datetime) -> str:
        return normalized.isoformat()


# ── Time interval ──────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class TimeInterval:
    """A time interval with start and end."""
    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise ValueError("Interval end before start")

    def contains(self, point: datetime) -> bool:
        return self.start <= point <= self.end

    def overlaps(self, other: "TimeInterval") -> bool:
        return not (self.end < other.start or other.end < self.start)


@dataclass(frozen=True, slots=True)
class TimeIntervalType:
    """Time interval value type."""
    kind: ValueKind = ValueKind.TIME_INTERVAL

    def normalize(self, raw: Any) -> TimeInterval:
        if isinstance(raw, TimeInterval):
            return raw
        if isinstance(raw, (tuple, list)) and len(raw) == 2:
            tp = TimePointType()
            return TimeInterval(tp.normalize(raw[0]), tp.normalize(raw[1]))
        raise ValueError(f"Cannot normalize {raw!r} as time interval")

    def identity_hash(self, normalized: TimeInterval) -> str:
        return f"ti:{normalized.start.isoformat()}/{normalized.end.isoformat()}"

    def compare(self, a: TimeInterval, b: TimeInterval) -> int:
        if a.start != b.start:
            return -1 if a.start < b.start else 1
        if a.end != b.end:
            return -1 if a.end < b.end else 1
        return 0

    def contradicts(self, a: TimeInterval, b: TimeInterval) -> bool:
        # Intervals contradict if they don't overlap
        return not a.overlaps(b)

    def serialize(self, normalized: TimeInterval) -> str:
        return f"{normalized.start.isoformat()}/{normalized.end.isoformat()}"

    def public_surface(self, normalized: TimeInterval) -> str:
        return self.serialize(normalized)


# ── Coordinate and reference frame ─────────────────────────────────


@dataclass(frozen=True, slots=True)
class Coordinate:
    """A coordinate in a reference frame."""
    values: tuple[float, ...]
    frame: str = "default"

    def __post_init__(self) -> None:
        if not self.values:
            raise ValueError("Coordinate requires at least one value")


@dataclass(frozen=True, slots=True)
class CoordinateType:
    """Coordinate value type with reference frame."""
    kind: ValueKind = ValueKind.COORDINATE
    dimensions: int = 2
    default_frame: str = "default"

    def normalize(self, raw: Any) -> Coordinate:
        if isinstance(raw, Coordinate):
            if len(raw.values) != self.dimensions:
                raise ValueError(f"Expected {self.dimensions}D, got {len(raw.values)}D")
            return raw
        if isinstance(raw, (tuple, list)):
            vals = tuple(float(v) for v in raw)
            if len(vals) != self.dimensions:
                raise ValueError(f"Expected {self.dimensions}D, got {len(vals)}D")
            return Coordinate(vals, self.default_frame)
        raise ValueError(f"Cannot normalize {raw!r} as coordinate")

    def identity_hash(self, normalized: Coordinate) -> str:
        import hashlib
        val_str = ",".join(f"{v:.10f}" for v in normalized.values)
        return f"coord:{normalized.frame}:{hashlib.sha256(val_str.encode()).hexdigest()[:16]}"

    def compare(self, a: Coordinate, b: Coordinate) -> int:
        if a.frame != b.frame:
            raise ValueError(f"Cannot compare coordinates in different frames: {a.frame} vs {b.frame}")
        for va, vb in zip(a.values, b.values):
            if va != vb:
                return -1 if va < vb else 1
        return 0

    def contradicts(self, a: Coordinate, b: Coordinate) -> bool:
        if a.frame != b.frame:
            return False
        return a.values != b.values

    def serialize(self, normalized: Coordinate) -> str:
        return f"{normalized.frame}({','.join(str(v) for v in normalized.values)})"

    def public_surface(self, normalized: Coordinate) -> str:
        return self.serialize(normalized)


# ── Probability ────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class ProbabilityType:
    """Probability value type in [0, 1]."""
    kind: ValueKind = ValueKind.PROBABILITY

    def normalize(self, raw: Any) -> float:
        if isinstance(raw, (int, float)):
            val = float(raw)
            if val < 0.0 or val > 1.0:
                raise ValueError(f"Probability must be in [0, 1], got {val}")
            return val
        raise ValueError(f"Cannot normalize {raw!r} as probability")

    def identity_hash(self, normalized: float) -> str:
        return f"prob:{normalized:.6f}"

    def compare(self, a: float, b: float) -> int:
        if abs(a - b) < 1e-12:
            return 0
        return -1 if a < b else 1

    def contradicts(self, a: float, b: float) -> bool:
        # Probabilities contradict if one is ~0 and the other is ~1
        return (a < 1e-6 and b > 1.0 - 1e-6) or (b < 1e-6 and a > 1.0 - 1e-6)

    def serialize(self, normalized: float) -> str:
        return f"{normalized:.6f}"

    def public_surface(self, normalized: float) -> str:
        return self.serialize(normalized)


# ── Distribution ───────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class Distribution:
    """A discrete probability distribution."""
    outcomes: tuple[str, ...]
    probabilities: tuple[float, ...]
    kind_name: str = "categorical"

    def __post_init__(self) -> None:
        if len(self.outcomes) != len(self.probabilities):
            raise ValueError("Outcomes and probabilities must have same length")
        total = sum(self.probabilities)
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"Probabilities must sum to 1.0, got {total}")


@dataclass(frozen=True, slots=True)
class DistributionType:
    """Distribution value type."""
    kind: ValueKind = ValueKind.DISTRIBUTION

    def normalize(self, raw: Any) -> Distribution:
        if isinstance(raw, Distribution):
            return raw
        if isinstance(raw, dict):
            outcomes = tuple(sorted(raw.keys()))
            probs = tuple(raw[k] for k in outcomes)
            return Distribution(outcomes, probs)
        raise ValueError(f"Cannot normalize {raw!r} as distribution")

    def identity_hash(self, normalized: Distribution) -> str:
        import hashlib
        parts = [f"{o}:{p:.6f}" for o, p in zip(normalized.outcomes, normalized.probabilities)]
        return f"dist:{hashlib.sha256('|'.join(parts).encode()).hexdigest()[:16]}"

    def compare(self, a: Distribution, b: Distribution) -> int:
        if a.outcomes != b.outcomes:
            return -1 if a.outcomes < b.outcomes else 1
        for pa, pb in zip(a.probabilities, b.probabilities):
            if abs(pa - pb) > 1e-12:
                return -1 if pa < pb else 1
        return 0

    def contradicts(self, a: Distribution, b: Distribution) -> bool:
        if a.outcomes != b.outcomes:
            return True
        # Contradict if probability mass is concentrated on different outcomes
        for pa, pb in zip(a.probabilities, b.probabilities):
            if (pa > 0.9 and pb < 0.1) or (pb > 0.9 and pa < 0.1):
                return True
        return False

    def serialize(self, normalized: Distribution) -> str:
        parts = [f"{o}={p:.4f}" for o, p in zip(normalized.outcomes, normalized.probabilities)]
        return f"dist({'; '.join(parts)})"

    def public_surface(self, normalized: Distribution) -> str:
        return self.serialize(normalized)


# ── Registry ───────────────────────────────────────────────────────


def default_value_types() -> dict[str, ValueTypeBehavior]:
    """Get the default registry of kernel value types."""
    return {
        ValueKind.BOOLEAN.value: BooleanType(),
        ValueKind.ENUM.value: EnumType(),
        ValueKind.TEXT.value: TextType(),
        ValueKind.IDENTIFIER.value: IdentifierType(),
        ValueKind.QUANTITY.value: QuantityType(),
        ValueKind.SET.value: SetType(),
        ValueKind.ORDERED_SEQUENCE.value: OrderedSequenceType(),
        ValueKind.TIME_POINT.value: TimePointType(),
        ValueKind.TIME_INTERVAL.value: TimeIntervalType(),
        ValueKind.COORDINATE.value: CoordinateType(),
        ValueKind.PROBABILITY.value: ProbabilityType(),
        ValueKind.DISTRIBUTION.value: DistributionType(),
    }
