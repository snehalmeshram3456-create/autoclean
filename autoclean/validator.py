"""Validates LLM-generated cleaning plans against a strict schema and allow-list.

This is the safety boundary: the LLM may only request actions that are both
well-formed AND implemented in executor.py. Anything else is rejected.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ValidationError, field_validator

# Allow-list of actions the executor actually implements.
ALLOWED_ACTIONS = {
    "drop_duplicates",
    "drop_rows_if_missing",
    "impute_mean",
    "impute_median",
    "impute_mode",
    "impute_constant",
    "clip_outliers",
    "drop_column",
    "strip_whitespace",
    "normalize_casing",
    "standardize_date_format",
    "fix_dtype",
    "no_action",
}


class CleaningAction(BaseModel):
    column: str
    action: str
    reason: str
    # optional, action-specific parameters
    target_format: Optional[str] = None
    method: Optional[str] = None  # e.g. "iqr" or "zscore" for clip_outliers
    fill_value: Optional[str] = None  # for impute_constant
    target_dtype: Optional[str] = None  # for fix_dtype
    casing: Optional[str] = None  # "lower" | "upper" | "title" for normalize_casing

    @field_validator("action")
    @classmethod
    def action_must_be_allowed(cls, v: str) -> str:
        if v not in ALLOWED_ACTIONS:
            raise ValueError(f"Action '{v}' is not in the allowed action list")
        return v


class CleaningPlan(BaseModel):
    actions: list[CleaningAction]


class ValidationResult(BaseModel):
    valid_actions: list[CleaningAction]
    rejected: list[dict]  # {"raw": ..., "error": ...}


def validate_plan(raw_plan: dict, known_columns: list[str]) -> ValidationResult:
    """Validate a raw LLM JSON plan.

    - Structurally invalid actions are rejected individually (not all-or-nothing).
    - Actions referencing unknown columns are rejected.
    - Returns both valid actions (ready to execute) and rejected ones (for the report).
    """
    valid_actions: list[CleaningAction] = []
    rejected: list[dict] = []

    actions_raw = raw_plan.get("actions", []) if isinstance(raw_plan, dict) else []
    if not isinstance(actions_raw, list):
        return ValidationResult(
            valid_actions=[],
            rejected=[{"raw": raw_plan, "error": "Top-level 'actions' is not a list"}],
        )

    for item in actions_raw:
        try:
            action = CleaningAction(**item)
        except ValidationError as e:
            rejected.append({"raw": item, "error": str(e)})
            continue

        if action.column not in known_columns:
            rejected.append(
                {"raw": item, "error": f"Unknown column '{action.column}'"}
            )
            continue

        valid_actions.append(action)

    return ValidationResult(valid_actions=valid_actions, rejected=rejected)
