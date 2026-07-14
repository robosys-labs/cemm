from __future__ import annotations

from typing import Any

from ...types.packet_schemas import PACKET_SCHEMAS


def _check_type(value: Any, expected: dict, path: str) -> list[str]:
    errors: list[str] = []
    if value is None:
        return errors  # None is valid for non-required fields
    expected_type = expected.get("type", "")

    if expected_type == "string":
        if not isinstance(value, str):
            errors.append(f"{path}: expected string, got {type(value).__name__}")
        elif "enum" in expected and value not in expected["enum"]:
            errors.append(f"{path}: value {value!r} not in enum {expected['enum']}")
        elif "pattern" in expected:
            import re
            if not re.match(expected["pattern"], str(value)):
                errors.append(f"{path}: value {value!r} does not match pattern {expected['pattern']}")

    elif expected_type == "number":
        if not isinstance(value, (int, float)):
            errors.append(f"{path}: expected number, got {type(value).__name__}")
        else:
            if "minimum" in expected and value < expected["minimum"]:
                errors.append(f"{path}: {value} < minimum {expected['minimum']}")
            if "maximum" in expected and value > expected["maximum"]:
                errors.append(f"{path}: {value} > maximum {expected['maximum']}")

    elif expected_type == "boolean":
        if not isinstance(value, bool):
            errors.append(f"{path}: expected boolean, got {type(value).__name__}")

    elif expected_type == "array":
        if not isinstance(value, list):
            errors.append(f"{path}: expected array, got {type(value).__name__}")
        elif "items" in expected:
            for i, item in enumerate(value):
                errors.extend(_check_type(item, expected["items"], f"{path}[{i}]"))

    elif expected_type == "object":
        if not isinstance(value, dict):
            errors.append(f"{path}: expected object, got {type(value).__name__}")

    return errors


def validate_packet(packet: dict, packet_type: str) -> list[str]:
    schema = PACKET_SCHEMAS.get(packet_type)
    if schema is None:
        return [f"Unknown packet type: {packet_type}"]

    errors: list[str] = []

    if not isinstance(packet, dict):
        return [f"Packet must be a dict, got {type(packet).__name__}"]

    required = schema.get("required", [])
    for field in required:
        if field not in packet:
            errors.append(f"Missing required field: {field}")

    for key, value in packet.items():
        prop_schema = schema.get("properties", {}).get(key)
        if prop_schema:
            errors.extend(_check_type(value, prop_schema, key))

    return errors


def validate_packet_raise(packet: dict, packet_type: str) -> None:
    errors = validate_packet(packet, packet_type)
    if errors:
        raise ValueError(f"{packet_type} validation failed: {'; '.join(errors)}")
