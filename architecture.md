# Architecture: AutoClean — LLM-Driven Automated Data Cleaning

## 1. Overview

AutoClean ingests a raw dataset (CSV/Excel/JSON), profiles it statistically, sends a **compact summary** of detected issues to an LLM (via Groq's free API), receives a structured **cleaning plan** back, executes that plan with deterministic code, and outputs a cleaned dataset plus a human-readable report.

The LLM never touches raw data directly — it only sees aggregated statistics/samples and returns *decisions*. All actual data manipulation happens in Python (pandas), keeping the LLM cheap, fast, and free-tier-friendly.

**Why this split:** Groq's free tier has strict rate limits (requests/min and tokens/min) and a max context size. Dumping an entire dataset into a prompt is slow, expensive, and often impossible for large files. Profiling first means one (or a few) small LLM calls per dataset instead of one per row.

---

## 2. High-Level Flow

```
Raw File (CSV/XLSX/JSON)
        │
        ▼
 [1] Data Loader          → pandas DataFrame
        │
        ▼
 [2] Profiler              → column stats, missing %, dtypes, outliers,
                              duplicates, sample values, cardinality
        │
        ▼
 [3] Issue Detector        → rule-based flags (nulls, mixed types,
                              inconsistent casing, date formats, outliers)
        │
        ▼
 [4] LLM Decision Engine   → sends compact JSON profile + issues to Groq
                              (Llama 3.1/3.3 via Groq API)
                              → returns structured JSON "cleaning plan"
        │
        ▼
 [5] Plan Validator        → schema-checks LLM output; rejects/repairs
                              invalid or unsafe actions
        │
        ▼
 [6] Cleaning Executor     → applies plan step-by-step using pandas
                              (deterministic, no LLM involved here)
        │
        ▼
 [7] Report Generator      → before/after diff, actions taken, reasoning
        │
        ▼
Cleaned File + cleaning_report.md/json
```

---

## 3. Components

### 3.1 Data Loader
- Reads CSV, XLSX, or JSON into a pandas DataFrame.
- Handles encoding detection (`chardet`) and delimiter sniffing for CSV.
- Preserves an untouched copy of the original for diffing later.

### 3.2 Profiler
Produces a compact, LLM-friendly JSON summary per column — **not raw rows**:
```json
{
  "column": "signup_date",
  "dtype": "object",
  "missing_pct": 4.2,
  "unique_count": 812,
  "sample_values": ["2023-01-05", "01/05/2023", "5th Jan 2023"],
  "issues_detected": ["inconsistent_date_format"]
}
```
- Numeric columns: min/max/mean/std/quartiles, outlier count (IQR or z-score).
- Categorical/text columns: top-N values, cardinality, casing inconsistencies.
- Whole-dataset stats: row count, duplicate row count, duplicate key candidates.

### 3.3 Issue Detector (rule-based, pre-LLM)
Deterministic checks that flag candidate problems *before* asking the LLM anything, so the LLM is reasoning over a short issue list instead of raw stats:
- Missing values (per column %)
- Duplicate rows / near-duplicate rows
- Mixed data types within a column
- Inconsistent formatting (dates, phone numbers, casing, whitespace)
- Outliers (IQR/z-score based)
- Constant or near-constant columns
- Suspicious column names (unnamed, duplicated headers)

### 3.4 LLM Decision Engine (Groq)
- Sends **only the profiler output + detected issues** (a few KB of JSON), never the full dataset.
- Model: a Groq-hosted free-tier model (e.g. Llama 3.1 8B/70B or Llama 3.3 70B — pick the smallest that gives reliable JSON).
- Prompt instructs the LLM to return a **strict JSON action plan**, e.g.:
```json
{
  "actions": [
    {
      "column": "signup_date",
      "action": "standardize_date_format",
      "target_format": "YYYY-MM-DD",
      "reason": "Mixed date formats detected across 3+ patterns"
    },
    {
      "column": "age",
      "action": "clip_outliers",
      "method": "iqr",
      "reason": "12 values exceed 1.5*IQR, likely data entry errors"
    },
    {
      "column": "email",
      "action": "drop_rows_if_missing",
      "reason": "Email is a required identifier; imputing is unsafe"
    }
  ]
}
```
- Uses Groq's JSON mode / low temperature for reliable structured output.
- Retry logic with backoff for rate-limit (429) responses — important since free tier has req/min caps.
- Batches multiple columns into one call rather than one call per column, to conserve request quota.

### 3.5 Plan Validator
- Validates the LLM's JSON against a schema (pydantic model) — action names must be from an allow-list of implemented operations.
- Rejects or flags actions on columns/values that don't exist, or actions with no implementation.
- If validation fails, either re-prompts the LLM once with the error, or falls back to a safe default (e.g. skip that column, log a warning) — never silently guesses.
- This is the safety boundary: the LLM can *suggest*, but only whitelisted, validated actions ever execute.

### 3.6 Cleaning Executor
- Pure pandas/Python — maps each validated action to a function:
  `standardize_date_format`, `clip_outliers`, `drop_rows_if_missing`, `impute_mean`, `impute_median`, `impute_mode`, `strip_whitespace`, `normalize_casing`, `drop_duplicates`, `fix_dtype`, etc.
- Executes actions sequentially, logging before/after state per column.
- Idempotent where possible so the pipeline can be re-run safely.

### 3.7 Report Generator
- Produces `cleaning_report.md` (or `.json`) summarizing:
  - Rows/columns before vs. after
  - Every action taken, which column, and the LLM's stated reasoning
  - Values changed count per column
  - Any actions the validator rejected and why
- This is the audit trail — critical since an LLM is making decisions on real data.

---

## 4. Tech Stack

| Layer | Choice |
|---|---|
| Language | Python 3.11+ |
| Data handling | pandas, numpy |
| LLM provider | Groq API (free tier) — `groq` Python SDK |
| Model | Llama 3.1/3.3 (Groq-hosted) |
| Schema validation | pydantic |
| CLI/Interface | Typer or argparse (CLI first); optional Streamlit UI later |
| File I/O | pandas + openpyxl (xlsx), chardet (encoding) |
| Config/secrets | `.env` + python-dotenv for `GROQ_API_KEY` |

---

## 5. Handling Groq Free-Tier Constraints

- **Rate limits:** batch column profiles into as few requests as possible (ideally 1 request per dataset unless it's very wide); implement exponential backoff on 429s.
- **Context limits:** never send raw rows in bulk — only aggregated stats + a handful of sample values per column (e.g. 5 samples max).
- **Reliability:** since free-tier models can occasionally return malformed JSON, always validate and have a deterministic rule-based fallback plan if the LLM call fails entirely (so the tool still cleans *something* even with zero LLM availability).

---

## 6. Folder Structure

```
autoclean/
├── autoclean/
│   ├── loader.py          # file reading
│   ├── profiler.py        # stats generation
│   ├── issue_detector.py  # rule-based flags
│   ├── llm_engine.py       # Groq API calls + prompt templates
│   ├── validator.py        # pydantic schema + action allow-list
│   ├── executor.py         # actual cleaning operations
│   ├── report.py           # report generation
│   └── pipeline.py         # orchestrates steps 1-7
├── cli.py                  # entry point
├── config.py                # env/config loading
├── tests/
├── .env.example
├── requirements.txt
└── architecture.md
```

---

## 7. Future Extensions
- Streamlit/web UI for uploading files and reviewing the LLM's plan before applying it (human-in-the-loop approval step).
- Support for user-defined cleaning rules that override LLM suggestions.
- Caching LLM responses for identical profiles to save free-tier quota on repeated runs.
