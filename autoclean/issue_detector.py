"""Rule-based pre-LLM issue detection. Flags candidate problems from the profile."""
from __future__ import annotations

import re

import pandas as pd

_DATE_PATTERNS = [
    re.compile(r"^\d{4}-\d{2}-\d{2}$"),           # 2023-01-05
    re.compile(r"^\d{2}/\d{2}/\d{4}$"),           # 01/05/2023
    re.compile(r"^\d{1,2}(st|nd|rd|th)? \w+ \d{4}$", re.IGNORECASE),  # 5th Jan 2023
    re.compile(r"^\w+ \d{1,2},? \d{4}$", re.IGNORECASE),  # Jan 5, 2023
]


def _detect_date_format_inconsistency(series: pd.Series) -> bool:
    non_null = series.dropna().astype(str)
    if non_null.empty:
        return False
    matched_patterns = set()
    for val in non_null.sample(min(30, len(non_null)), random_state=42):
        for i, pattern in enumerate(_DATE_PATTERNS):
            if pattern.match(val.strip()):
                matched_patterns.add(i)
                break
    return len(matched_patterns) > 1


def _detect_casing_inconsistency(series: pd.Series) -> bool:
    non_null = series.dropna().astype(str)
    if non_null.empty:
        return False
    variants = set()
    for val in non_null.unique()[:200]:
        variants.add(val.strip().lower())
    # If lowercasing collapses distinct values, casing is inconsistent
    return len(variants) < non_null.nunique()


def _detect_whitespace_issues(series: pd.Series) -> bool:
    non_null = series.dropna().astype(str)
    if non_null.empty:
        return False
    return non_null.apply(lambda v: v != v.strip()).any()


def detect_column_issues(series: pd.Series, col_profile: dict) -> list[str]:
    """Return a list of issue tags for one column, given its profile."""
    issues = []

    if col_profile["missing_pct"] > 0:
        issues.append("missing_values")

    if col_profile["unique_count"] <= 1 and len(series) > 1:
        issues.append("constant_column")

    is_text_col = pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series)
    if is_text_col:
        looks_numeric_pct = col_profile.get("looks_numeric_pct", 0)
        if 0 < looks_numeric_pct < 100:
            issues.append("mixed_types_numeric_and_text")

        if _detect_date_format_inconsistency(series):
            issues.append("inconsistent_date_format")

        if _detect_casing_inconsistency(series):
            issues.append("inconsistent_casing")

        if _detect_whitespace_issues(series):
            issues.append("leading_trailing_whitespace")

    numeric_stats = col_profile.get("numeric_stats")
    if numeric_stats and numeric_stats.get("outlier_count", 0) > 0:
        issues.append("outliers_present")

    return issues


def detect_issues(df: pd.DataFrame, dataset_profile: dict) -> dict:
    """Attach detected issue tags to each column's profile and flag dataset-level issues.

    Returns a dict: {"dataset_issues": [...], "columns": [profile_with_issues, ...]}
    """
    dataset_issues = []
    if dataset_profile["duplicate_row_count"] > 0:
        dataset_issues.append(
            f"{dataset_profile['duplicate_row_count']} duplicate rows detected"
        )

    enriched_columns = []
    for col_profile in dataset_profile["columns"]:
        col_name = col_profile["column"]
        issues = detect_column_issues(df[col_name], col_profile)
        enriched_columns.append({**col_profile, "issues_detected": issues})

    return {"dataset_issues": dataset_issues, "columns": enriched_columns}
