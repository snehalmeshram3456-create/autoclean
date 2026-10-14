import pandas as pd
import pytest

from autoclean.profiler import profile_dataframe
from autoclean.issue_detector import detect_issues


@pytest.fixture
def messy_df():
    return pd.DataFrame({
        "name": [" John Smith", "john smith", "Ann K.", "Bob Lee"],
        "age": [29, 29, 150, None],
        "signup_date": ["2023-01-05", "01/05/2023", "5th Jan 2023", "2023-01-06"],
        "city": ["New York", "new york", " Chicago ", "Boston"],
    })


def test_profile_dataframe_shape(messy_df):
    profile = profile_dataframe(messy_df)
    assert profile["row_count"] == 4
    assert profile["column_count"] == 4
    assert len(profile["columns"]) == 4


def test_missing_values_detected(messy_df):
    profile = profile_dataframe(messy_df)
    annotated = detect_issues(messy_df, profile)
    age_col = next(c for c in annotated["columns"] if c["column"] == "age")
    assert "missing_values" in age_col["issues_detected"]
    assert age_col["missing_pct"] == 25.0


def test_outliers_detected():
    # IQR needs a reasonable sample size to flag outliers meaningfully;
    # the 4-row messy_df fixture is too small for 150 to register.
    df = pd.DataFrame({"age": [29, 31, 28, 30, 32, 29, 31, 150]})
    profile = profile_dataframe(df)
    annotated = detect_issues(df, profile)
    age_col = next(c for c in annotated["columns"] if c["column"] == "age")
    assert "outliers_present" in age_col["issues_detected"]


def test_casing_and_whitespace_detected(messy_df):
    profile = profile_dataframe(messy_df)
    annotated = detect_issues(messy_df, profile)
    city_col = next(c for c in annotated["columns"] if c["column"] == "city")
    assert "inconsistent_casing" in city_col["issues_detected"]
    assert "leading_trailing_whitespace" in city_col["issues_detected"]


def test_date_format_inconsistency_detected(messy_df):
    profile = profile_dataframe(messy_df)
    annotated = detect_issues(messy_df, profile)
    date_col = next(c for c in annotated["columns"] if c["column"] == "signup_date")
    assert "inconsistent_date_format" in date_col["issues_detected"]


def test_duplicate_rows_detected():
    df = pd.DataFrame({"a": [1, 1, 2], "b": ["x", "x", "y"]})
    profile = profile_dataframe(df)
    assert profile["duplicate_row_count"] == 1
