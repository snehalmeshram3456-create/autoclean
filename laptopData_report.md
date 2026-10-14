# AutoClean Report

Generated: 2026-09-10 13:47:22

## Summary
- Rows before: 1303
- Rows after: 1303
- Columns before: 12
- Columns after: 11

## Actions Applied

### `Unnamed: 0` — drop_column
- **Reason (LLM):** unnecessary index column
- **Result:** column_dropped=Unnamed: 0

### `Company` — impute_mode
- **Reason (LLM):** missing categorical values
- **Result:** values_filled=30, fill_value=Lenovo

### `TypeName` — impute_mode
- **Reason (LLM):** missing categorical values
- **Result:** values_filled=30, fill_value=Notebook

### `Inches` — fix_dtype
- **Reason (LLM):** convert numeric string to float
- **Result:** target_dtype=float, new_nulls_introduced=1

### `ScreenResolution` — impute_mode
- **Reason (LLM):** missing values
- **Result:** values_filled=30, fill_value=Full HD 1920x1080

### `Cpu` — normalize_casing
- **Reason (LLM):** inconsistent casing
- **Result:** values_changed=1303, casing=title

### `Ram` — impute_mode
- **Reason (LLM):** missing values
- **Result:** values_filled=30, fill_value=8GB

### `Memory` — impute_mode
- **Reason (LLM):** missing values
- **Result:** values_filled=30, fill_value=256GB SSD

### `Gpu` — strip_whitespace
- **Reason (LLM):** leading/trailing whitespace
- **Result:** values_changed=44

### `Gpu` — normalize_casing
- **Reason (LLM):** inconsistent casing
- **Result:** values_changed=1257, casing=title

### `OpSys` — impute_mode
- **Reason (LLM):** missing values
- **Result:** values_filled=30, fill_value=Windows 10

### `Weight` — impute_mode
- **Reason (LLM):** missing values
- **Result:** values_filled=30, fill_value=2.2kg

### `Price` — clip_outliers
- **Reason (LLM):** outliers present
- **Result:** values_clipped=28, lower=-39213.2808, upper=150461.388

## Actions Rejected by Validator
_These were proposed by the LLM but rejected before execution (invalid schema, unknown column, or disallowed action)._
- Raw: `{'column': 'dataset', 'action': 'drop_duplicates', 'reason': 'duplicate rows detected'}` — Error: Unknown column 'dataset'