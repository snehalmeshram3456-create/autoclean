"""Generates a human-readable markdown report of a cleaning run."""
from __future__ import annotations

from datetime import datetime

import pandas as pd


def generate_report(
    original_df: pd.DataFrame,
    cleaned_df: pd.DataFrame,
    execution_log: list[dict],
    rejected_actions: list[dict],
    llm_error: str | None,
) -> str:
    lines = []
    lines.append("# AutoClean Report")
    lines.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    lines.append("## Summary")
    lines.append(f"- Rows before: {len(original_df)}")
    lines.append(f"- Rows after: {len(cleaned_df)}")
    lines.append(f"- Columns before: {len(original_df.columns)}")
    lines.append(f"- Columns after: {len(cleaned_df.columns)}")
    if llm_error:
        lines.append(f"- **LLM warning:** {llm_error} (fell back to rule-based/no cleaning for affected steps)")

    lines.append("\n## Actions Applied")
    applied = [e for e in execution_log if e["status"] == "applied"]
    if not applied:
        lines.append("_No actions were applied._")
    for e in applied:
        lines.append(f"\n### `{e['column']}` — {e['action']}")
        lines.append(f"- **Reason (LLM):** {e['reason']}")
        detail_str = ", ".join(f"{k}={v}" for k, v in e["detail"].items())
        lines.append(f"- **Result:** {detail_str}")

    skipped_or_failed = [e for e in execution_log if e["status"] != "applied"]
    if skipped_or_failed:
        lines.append("\n## Actions Skipped or Failed")
        for e in skipped_or_failed:
            lines.append(
                f"- `{e['column']}` — {e['action']} — **{e['status']}**: {e['detail'].get('error', '')}"
            )

    if rejected_actions:
        lines.append("\n## Actions Rejected by Validator")
        lines.append("_These were proposed by the LLM but rejected before execution "
                      "(invalid schema, unknown column, or disallowed action)._")
        for r in rejected_actions:
            lines.append(f"- Raw: `{r['raw']}` — Error: {r['error']}")

    return "\n".join(lines)
