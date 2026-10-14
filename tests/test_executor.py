import pandas as pd

from autoclean.validator import CleaningAction
from autoclean.executor import execute_plan


def test_drop_duplicates():
    df = pd.DataFrame({"a": [1, 1, 2]})
    action = CleaningAction(column="a", action="drop_duplicates", reason="dupes")
    cleaned, log = execute_plan(df, [action])
    assert len(cleaned) == 2
    assert log[0]["status"] == "applied"


def test_impute_median():
    df = pd.DataFrame({"age": [10, 20, None]})
    action = CleaningAction(column="age", action="impute_median", reason="missing")
    cleaned, log = execute_plan(df, [action])
    assert cleaned["age"].isna().sum() == 0
    assert cleaned["age"].iloc[2] == 15.0


def test_clip_outliers():
    df = pd.DataFrame({"age": [10, 12, 11, 13, 1000]})
    action = CleaningAction(column="age", action="clip_outliers", reason="outlier", method="iqr")
    cleaned, log = execute_plan(df, [action])
    assert cleaned["age"].max() < 1000


def test_strip_whitespace_and_casing():
    df = pd.DataFrame({"city": [" Chicago ", "new york", "BOSTON"]})
    actions = [
        CleaningAction(column="city", action="strip_whitespace", reason="ws"),
        CleaningAction(column="city", action="normalize_casing", reason="case", casing="title"),
    ]
    cleaned, log = execute_plan(df, actions)
    assert list(cleaned["city"]) == ["Chicago", "New York", "Boston"]
    assert all(e["status"] == "applied" for e in log)


def test_drop_rows_if_missing():
    df = pd.DataFrame({"email": ["a@x.com", None, "b@x.com"]})
    action = CleaningAction(column="email", action="drop_rows_if_missing", reason="required field")
    cleaned, log = execute_plan(df, [action])
    assert len(cleaned) == 2


def test_unimplemented_action_is_skipped_not_fatal():
    df = pd.DataFrame({"a": [1, 2]})
    action = CleaningAction.model_construct(column="a", action="no_action", reason="test")
    # simulate a bogus action name bypassing validation (shouldn't happen in practice)
    action.action = "totally_made_up"
    cleaned, log = execute_plan(df, [action])
    assert log[0]["status"] == "skipped"
    assert len(cleaned) == 2  # df untouched


def test_standardize_date_format():
    df = pd.DataFrame({"d": ["2023-01-05", "01/05/2023", "5th Jan 2023"]})
    action = CleaningAction(
        column="d", action="standardize_date_format", reason="mixed formats",
        target_format="YYYY-MM-DD",
    )
    cleaned, log = execute_plan(df, [action])
    assert all(cleaned["d"] == "2023-01-05")
