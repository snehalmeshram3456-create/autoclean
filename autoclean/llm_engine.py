"""Handles the Groq API call: builds the prompt from the issue-annotated profile,
requests a structured JSON cleaning plan, and retries on rate limits or bad JSON.
"""
from __future__ import annotations

import json
import time

from groq import Groq, APIStatusError

import config
from autoclean.validator import ALLOWED_ACTIONS

SYSTEM_PROMPT = f"""You are a data cleaning assistant. You will be given a JSON \
profile of a dataset (column stats and detected issues, NOT raw data).

Decide what cleaning actions to take. Respond with ONLY a JSON object, no \
preamble, no markdown code fences, in exactly this shape:

{{
  "actions": [
    {{
      "column": "<column name>",
      "action": "<one of: {', '.join(sorted(ALLOWED_ACTIONS))}>",
      "reason": "<short reason, one sentence>",
      "target_format": "<optional, e.g. YYYY-MM-DD, only for standardize_date_format>",
      "method": "<optional, 'iqr' or 'zscore', only for clip_outliers>",
      "fill_value": "<optional, only for impute_constant>",
      "target_dtype": "<optional, e.g. 'int', 'float', 'str', only for fix_dtype>",
      "casing": "<optional, 'lower'|'upper'|'title', only for normalize_casing>"
    }}
  ]
}}

Rules:
- Only propose one action per column per pass unless clearly independent (e.g. \
strip_whitespace AND normalize_casing can both apply to the same text column).
- If a column has no real issues, either omit it or use "no_action".
- Prefer imputation over dropping rows unless the column looks like a required \
identifier (email, id, key) with missing values.
- Use "drop_rows_if_missing" sparingly — it deletes data.
- Keep "reason" short and specific to the stats/issues given for that column.
- Do not invent columns that are not in the profile."""


def _build_user_prompt(annotated_profile: dict) -> str:
    return (
        "Dataset profile (stats and detected issues only, no raw rows):\n\n"
        + json.dumps(annotated_profile, indent=2)
    )


def _extract_json(text: str) -> dict:
    """Strip markdown fences if present and parse JSON."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
    return json.loads(cleaned.strip())


def get_cleaning_plan(annotated_profile: dict) -> dict:
    """Call Groq with the profile and return a raw parsed JSON plan dict.

    On repeated failure (rate limit, malformed JSON, no API key), returns
    {"actions": [], "error": "<reason>"} so the pipeline can fall back gracefully
    instead of crashing.
    """
    if not config.GROQ_API_KEY:
        return {"actions": [], "error": "GROQ_API_KEY not set"}

    client = Groq(api_key=config.GROQ_API_KEY)
    user_prompt = _build_user_prompt(annotated_profile)

    last_error = "unknown error"
    for attempt in range(config.LLM_MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model=config.GROQ_MODEL,
                temperature=config.LLM_TEMPERATURE,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            return _extract_json(content)

        except APIStatusError as e:
            last_error = f"Groq API error: {e}"
            if e.status_code == 429:
                # Rate limited — back off and retry
                wait = 2 ** attempt
                time.sleep(wait)
                continue
            break  # non-retryable API error

        except json.JSONDecodeError as e:
            last_error = f"Malformed JSON from LLM: {e}"
            time.sleep(1)
            continue

        except Exception as e:  # network errors, etc.
            last_error = f"Unexpected error calling Groq: {e}"
            time.sleep(1)
            continue

    return {"actions": [], "error": last_error}
