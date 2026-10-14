"""Generates a compact, LLM-friendly statistical profile of a DataFrame."""
from __future__ import annotations

import numpy as np
import pandas as pd

from config import MAX_SAMPLE_VALUES


def _sample_values(series: pd.Series, n: int = MAX_SAMPLE_VALUES) -> list:
    non_null = series.dropna()
    if non_null.empty:
        return []
    sample = non_null.sample(min(n, len(non_null)), random_state=42)
    return [str(v) for v in sample.tolist()]


def _numeric_profile(series: pd.Series) -> dict:
    numeric = pd.to_numeric(series, errors="coerce")
    valid = numeric.dropna()
    if valid.empty:
        return {}
    q1, q3 = valid.quantile(0.25), valid.quantile(0.75)
    iqr = q3 - q1
    lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    outliers = valid[(valid < lower) | (valid > upper)]
    return {
        "min": float(valid.min()),
        "max": float(valid.max()),
        "mean": round(float(valid.mean()), 4),
        "std": round(float(valid.std()), 4) if len(valid) > 1 else 0.0,
        "outlier_count": int(len(outliers)),
    }


def profile_column(series: pd.Series, col_name: str) -> dict:
    """Build a profile dict for a single column."""
    total = len(series)
    missing = int(series.isna().sum())
    missing_pct = round((missing / total) * 100, 2) if total else 0.0

    profile = {
        "column": col_name,
        "dtype": str(series.dtype),
        "missing_count": missing,
        "missing_pct": missing_pct,
        "unique_count": int(series.nunique(dropna=True)),
        "sample_values": _sample_values(series),
    }

    if pd.api.types.is_numeric_dtype(series):
        profile["numeric_stats"] = _numeric_profile(series)
    elif pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series):
        # Detect if the "object" column is actually numeric-looking but stored as text
        coerced = pd.to_numeric(series, errors="coerce")
        looks_numeric_pct = round(coerced.notna().sum() / max(total - missing, 1) * 100, 1)
        profile["looks_numeric_pct"] = looks_numeric_pct

    return profile


def profile_dataframe(df: pd.DataFrame) -> dict:
    """Build the full dataset profile: shape, duplicates, and per-column stats."""
    duplicate_rows = int(df.duplicated().sum())

    return {
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
        "duplicate_row_count": duplicate_rows,
        "columns": [profile_column(df[col], col) for col in df.columns],
    }
