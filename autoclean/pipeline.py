"""Orchestrates the full AutoClean pipeline: load -> profile -> detect -> LLM
plan -> validate -> execute -> report.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from autoclean.loader import load_data, save_data
from autoclean.profiler import profile_dataframe
from autoclean.issue_detector import detect_issues
from autoclean.llm_engine import get_cleaning_plan
from autoclean.validator import validate_plan
from autoclean.executor import execute_plan
from autoclean.report import generate_report


@dataclass
class PipelineResult:
    original_df: pd.DataFrame
    cleaned_df: pd.DataFrame
    report_markdown: str
    execution_log: list
    rejected_actions: list
    llm_error: str | None


def run_pipeline(input_path: str) -> PipelineResult:
    """Run the full cleaning pipeline on a file and return the result in-memory."""
    # 1. Load
    original_df = load_data(input_path)
    df = original_df.copy()

    # 2. Profile
    dataset_profile = profile_dataframe(df)

    # 3. Detect issues (rule-based, pre-LLM)
    annotated = detect_issues(df, dataset_profile)
    annotated_profile = {
        "row_count": dataset_profile["row_count"],
        "column_count": dataset_profile["column_count"],
        "duplicate_row_count": dataset_profile["duplicate_row_count"],
        "dataset_issues": annotated["dataset_issues"],
        "columns": annotated["columns"],
    }

    # 4. LLM decision engine
    raw_plan = get_cleaning_plan(annotated_profile)
    llm_error = raw_plan.get("error")

    # 5. Validate plan
    known_columns = list(df.columns)
    validation_result = validate_plan(raw_plan, known_columns)

    # 6. Execute
    cleaned_df, execution_log = execute_plan(df, validation_result.valid_actions)

    # 7. Report
    report_markdown = generate_report(
        original_df=original_df,
        cleaned_df=cleaned_df,
        execution_log=execution_log,
        rejected_actions=validation_result.rejected,
        llm_error=llm_error,
    )

    return PipelineResult(
        original_df=original_df,
        cleaned_df=cleaned_df,
        report_markdown=report_markdown,
        execution_log=execution_log,
        rejected_actions=validation_result.rejected,
        llm_error=llm_error,
    )


def run_and_save(input_path: str, output_path: str, report_path: str) -> PipelineResult:
    result = run_pipeline(input_path)
    save_data(result.cleaned_df, output_path)
    with open(report_path, "w") as f:
        f.write(result.report_markdown)
    return result
