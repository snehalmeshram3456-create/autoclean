from autoclean.validator import validate_plan


KNOWN_COLUMNS = ["name", "age", "email"]


def test_valid_actions_pass():
    plan = {"actions": [
        {"column": "age", "action": "impute_mean", "reason": "missing values"},
    ]}
    result = validate_plan(plan, KNOWN_COLUMNS)
    assert len(result.valid_actions) == 1
    assert len(result.rejected) == 0


def test_unknown_column_rejected():
    plan = {"actions": [
        {"column": "ghost", "action": "impute_mean", "reason": "n/a"},
    ]}
    result = validate_plan(plan, KNOWN_COLUMNS)
    assert len(result.valid_actions) == 0
    assert len(result.rejected) == 1
    assert "Unknown column" in result.rejected[0]["error"]


def test_disallowed_action_rejected():
    plan = {"actions": [
        {"column": "age", "action": "delete_everything", "reason": "n/a"},
    ]}
    result = validate_plan(plan, KNOWN_COLUMNS)
    assert len(result.valid_actions) == 0
    assert len(result.rejected) == 1


def test_missing_required_field_rejected():
    plan = {"actions": [
        {"column": "age", "reason": "no action field"},
    ]}
    result = validate_plan(plan, KNOWN_COLUMNS)
    assert len(result.valid_actions) == 0
    assert len(result.rejected) == 1


def test_partial_validity_not_all_or_nothing():
    plan = {"actions": [
        {"column": "age", "action": "impute_mean", "reason": "ok"},
        {"column": "ghost", "action": "impute_mean", "reason": "bad column"},
    ]}
    result = validate_plan(plan, KNOWN_COLUMNS)
    assert len(result.valid_actions) == 1
    assert len(result.rejected) == 1


def test_malformed_top_level_structure():
    plan = {"not_actions": []}
    result = validate_plan(plan, KNOWN_COLUMNS)
    assert len(result.valid_actions) == 0
    assert len(result.rejected) == 0  # empty actions list, nothing to reject either
