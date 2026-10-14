# AutoClean

LLM-driven automated data cleaning. Profiles your dataset statistically, sends
a compact summary to Groq's free-tier LLM to decide what cleaning actions to
take, validates those decisions, then executes them deterministically with
pandas. Produces a cleaned file plus a markdown audit report.

See `architecture.md` for the full design.

## Setup

```bash
cd autoclean
pip install -r requirements.txt
cp .env.example .env
# edit .env and paste your free Groq API key (https://console.groq.com/keys)
```

## Usage

```bash
python cli.py data.csv
```

Optional flags:

```bash
python cli.py data.csv --output cleaned.csv --report report.md
```

This produces:
- `data_cleaned.csv` — the cleaned dataset
- `data_report.md` — what was changed and why (LLM's stated reasoning per action)

Supports `.csv`, `.xlsx`/`.xls`, and `.json` input files.

## How it works

1. **Load** — reads the file into a DataFrame.
2. **Profile** — computes per-column stats (missing %, dtype, outliers, samples) — no raw rows leave this step.
3. **Detect** — rule-based checks flag candidate issues (duplicates, mixed types, inconsistent dates/casing, outliers).
4. **LLM decision** — the profile + issues (not the raw data) are sent to Groq (`openai/gpt-oss-20b` by default), which returns a structured JSON cleaning plan.
5. **Validate** — every proposed action is checked against a strict schema and an allow-list of implemented operations before anything runs.
6. **Execute** — validated actions are applied with plain pandas.
7. **Report** — a markdown report records every action taken, the LLM's reasoning, and anything rejected.

If the Groq API key is missing or the API is unreachable, the pipeline still
runs — it just applies no LLM-driven actions and notes this in the report.

## Project structure

```
autoclean/
├── autoclean/
│   ├── loader.py          # file reading/writing
│   ├── profiler.py        # stats generation
│   ├── issue_detector.py  # rule-based flags
│   ├── llm_engine.py       # Groq API calls + prompt
│   ├── validator.py        # pydantic schema + action allow-list
│   ├── executor.py         # cleaning operations
│   └── pipeline.py         # orchestration
├── cli.py                  # CLI entry point
├── config.py                # env/config loading
├── tests/
├── .env.example
├── requirements.txt
└── architecture.md
```

## Supported cleaning actions

`drop_duplicates`, `drop_rows_if_missing`, `impute_mean`, `impute_median`,
`impute_mode`, `impute_constant`, `clip_outliers`, `drop_column`,
`strip_whitespace`, `normalize_casing`, `standardize_date_format`, `fix_dtype`,
`no_action`.
