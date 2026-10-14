"""Applies validated cleaning actions to a DataFrame. Pure pandas, no LLM calls here."""
from __future__ import annotations

import pandas as pd

from autoclean.validator import CleaningAction

_DATE_FORMAT_MAP = {
    "YYYY-MM-DD": "%Y-%m-%d",
    "MM/DD/YYYY": "%m/%d/%Y",
    "DD/MM/YYYY": "%d/%m/%Y",
}


class ExecutionLog(dict):
    """Simple record of what happened when applying one action."""


def _drop_duplicates(df: pd.DataFrame, action: CleaningAction) -> tuple[pd.DataFrame, ExecutionLog]:
    before = len(df)
    df = df.drop_duplicates()
    return df, ExecutionLog(rows_removed=before - len(df))


def _drop_rows_if_missing(df: pd.DataFrame, action: CleaningAction) -> tuple[pd.DataFrame, ExecutionLog]:
    before = len(df)
    df = df.dropna(subset=[action.column])
    return df, ExecutionLog(rows_removed=before - len(df))


def _impute_mean(df: pd.DataFrame, action: CleaningAction) -> tuple[pd.DataFrame, ExecutionLog]:
    col = action.column
    numeric = pd.to_numeric(df[col], errors="coerce")
    fill = numeric.mean()
    count = int(df[col].isna().sum())
    df[col] = numeric.fillna(fill)
    return df, ExecutionLog(values_filled=count, fill_value=round(float(fill), 4))


def _impute_median(df: pd.DataFrame, action: CleaningAction) -> tuple[pd.DataFrame, ExecutionLog]:
    col = action.column
    numeric = pd.to_numeric(df[col], errors="coerce")
    fill = numeric.median()
    count = int(df[col].isna().sum())
    df[col] = numeric.fillna(fill)
    return df, ExecutionLog(values_filled=count, fill_value=round(float(fill), 4))


def _impute_mode(df: pd.DataFrame, action: CleaningAction) -> tuple[pd.DataFrame, ExecutionLog]:
    col = action.column
    mode_vals = df[col].mode(dropna=True)
    if mode_vals.empty:
        return df, ExecutionLog(values_filled=0, note="no mode available")
    fill = mode_vals.iloc[0]
    count = int(df[col].isna().sum())
    df[col] = df[col].fillna(fill)
    return df, ExecutionLog(values_filled=count, fill_value=str(fill))


def _impute_constant(df: pd.DataFrame, action: CleaningAction) -> tuple[pd.DataFrame, ExecutionLog]:
    col = action.column
    fill = action.fill_value if action.fill_value is not None else ""
    count = int(df[col].isna().sum())
    df[col] = df[col].fillna(fill)
    return df, ExecutionLog(values_filled=count, fill_value=fill)


def _clip_outliers(df: pd.DataFrame, action: CleaningAction) -> tuple[pd.DataFrame, ExecutionLog]:
    col = action.column
    numeric = pd.to_numeric(df[col], errors="coerce")
    q1, q3 = numeric.quantile(0.25), numeric.quantile(0.75)
    iqr = q3 - q1
    lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    clipped_count = int(((numeric < lower) | (numeric > upper)).sum())
    df[col] = numeric.clip(lower=lower, upper=upper)
    return df, ExecutionLog(values_clipped=clipped_count, lower=round(float(lower), 4), upper=round(float(upper), 4))


def _drop_column(df: pd.DataFrame, action: CleaningAction) -> tuple[pd.DataFrame, ExecutionLog]:
    df = df.drop(columns=[action.column])
    return df, ExecutionLog(column_dropped=action.column)


def _strip_whitespace(df: pd.DataFrame, action: CleaningAction) -> tuple[pd.DataFrame, ExecutionLog]:
    col = action.column
    before = df[col].astype(str)
    df[col] = df[col].apply(lambda v: v.strip() if isinstance(v, str) else v)
    changed = int((before != df[col].astype(str)).sum())
    return df, ExecutionLog(values_changed=changed)


def _normalize_casing(df: pd.DataFrame, action: CleaningAction) -> tuple[pd.DataFrame, ExecutionLog]:
    col = action.column
    casing = action.casing or "lower"
    before = df[col].astype(str)

    def apply_case(v):
        if not isinstance(v, str):
            return v
        if casing == "upper":
            return v.upper()
        if casing == "title":
            return v.title()
        return v.lower()

    df[col] = df[col].apply(apply_case)
    changed = int((before != df[col].astype(str)).sum())
    return df, ExecutionLog(values_changed=changed, casing=casing)


def _standardize_date_format(df: pd.DataFrame, action: CleaningAction) -> tuple[pd.DataFrame, ExecutionLog]:
    col = action.column
    target = action.target_format or "YYYY-MM-DD"
    out_fmt = _DATE_FORMAT_MAP.get(target, "%Y-%m-%d")

    parsed = pd.to_datetime(df[col], errors="coerce", format="mixed")
    failed = int(parsed.isna().sum() - df[col].isna().sum())
    df[col] = parsed.dt.strftime(out_fmt)
    return df, ExecutionLog(target_format=target, unparseable_values=max(failed, 0))


def _fix_dtype(df: pd.DataFrame, action: CleaningAction) -> tuple[pd.DataFrame, ExecutionLog]:
    col = action.column
    target = (action.target_dtype or "str").lower()
    before_na = int(df[col].isna().sum())

    try:
        if target in ("int", "int64"):
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
        elif target in ("float", "float64"):
            df[col] = pd.to_numeric(df[col], errors="coerce")
        elif target in ("str", "string", "object"):
            df[col] = df[col].astype(str)
        elif target in ("bool", "boolean"):
            df[col] = df[col].astype(bool)
        else:
            return df, ExecutionLog(error=f"Unsupported target_dtype '{target}'")
    except Exception as e:
        return df, ExecutionLog(error=f"fix_dtype failed: {e}")

    after_na = int(df[col].isna().sum())
    return df, ExecutionLog(target_dtype=target, new_nulls_introduced=max(after_na - before_na, 0))


def _no_action(df: pd.DataFrame, action: CleaningAction) -> tuple[pd.DataFrame, ExecutionLog]:
    return df, ExecutionLog(note="no action taken")


_ACTION_DISPATCH = {
    "drop_duplicates": _drop_duplicates,
    "drop_rows_if_missing": _drop_rows_if_missing,
    "impute_mean": _impute_mean,
    "impute_median": _impute_median,
    "impute_mode": _impute_mode,
    "impute_constant": _impute_constant,
    "clip_outliers": _clip_outliers,
    "drop_column": _drop_column,
    "strip_whitespace": _strip_whitespace,
    "normalize_casing": _normalize_casing,
    "standardize_date_format": _standardize_date_format,
    "fix_dtype": _fix_dtype,
    "no_action": _no_action,
}


def execute_plan(df: pd.DataFrame, actions: list[CleaningAction]) -> tuple[pd.DataFrame, list[dict]]:
    """Apply each validated action in sequence. Returns (cleaned_df, execution_log).

    A failure in one action is caught and logged, not fatal to the rest of the plan.
    """
    execution_log = []

    for action in actions:
        handler = _ACTION_DISPATCH.get(action.action)
        if handler is None:
            execution_log.append({
                "column": action.column,
                "action": action.action,
                "reason": action.reason,
                "status": "skipped",
                "detail": {"error": "No executor implemented for this action"},
            })
            continue

        try:
            df, detail = handler(df, action)
            execution_log.append({
                "column": action.column,
                "action": action.action,
                "reason": action.reason,
                "status": "applied",
                "detail": dict(detail),
            })
        except Exception as e:
            execution_log.append({
                "column": action.column,
                "action": action.action,
                "reason": action.reason,
                "status": "failed",
                "detail": {"error": str(e)},
            })

    return df, execution_log
