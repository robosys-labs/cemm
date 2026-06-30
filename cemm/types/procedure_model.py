"""Procedure and tool schema model types.

From cemm_original_work_subplans.md §7:
- ProcedureModel: multi-step procedure (schedule meeting, compute math, etc.)
- ToolSchemaModel: individual tool definition (calculator, calendar, etc.)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ConfirmationPolicy(str, Enum):
    ALWAYS = "always"
    RISKY_ONLY = "risky_only"
    NEVER = "never"


@dataclass
class ProcedureModel:
    model_id: str
    registry_key: str
    required_slots: list[str] = field(default_factory=list)
    optional_slots: list[str] = field(default_factory=list)
    preconditions: list[str] = field(default_factory=list)
    tool_sequence: list[str] = field(default_factory=list)
    confirmation_policy: ConfirmationPolicy = ConfirmationPolicy.RISKY_ONLY
    success_criteria: list[str] = field(default_factory=list)
    failure_modes: list[str] = field(default_factory=list)
    reliability_log_odds: float = 0.0
    version: str = "cemm.procedure_model.v1"


@dataclass
class ToolSchemaModel:
    model_id: str
    tool_id: str
    input_schema: str
    output_schema: str
    permission_required: str = "public"
    cost_estimate_ms: float = 0.0
    risk: float = 0.0
    reliability_log_odds: float = 0.0
    version: str = "cemm.tool_schema_model.v1"
