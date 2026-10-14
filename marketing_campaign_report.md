# AutoClean Report

Generated: 2026-09-03 14:09:41

## Summary
- Rows before: 2240
- Rows after: 2240
- Columns before: 29
- Columns after: 27

## Actions Applied

### `Year_Birth` — clip_outliers
- **Reason (LLM):** outliers present
- **Result:** values_clipped=3, lower=1932.0, upper=2004.0

### `Income` — impute_median
- **Reason (LLM):** missing values
- **Result:** values_filled=24, fill_value=51381.5

### `MntWines` — clip_outliers
- **Reason (LLM):** outliers present
- **Result:** values_clipped=35, lower=-697.0, upper=1225.0

### `MntFruits` — clip_outliers
- **Reason (LLM):** outliers present
- **Result:** values_clipped=227, lower=-47.0, upper=81.0

### `MntMeatProducts` — clip_outliers
- **Reason (LLM):** outliers present
- **Result:** values_clipped=175, lower=-308.0, upper=556.0

### `MntFishProducts` — clip_outliers
- **Reason (LLM):** outliers present
- **Result:** values_clipped=223, lower=-67.5, upper=120.5

### `MntSweetProducts` — clip_outliers
- **Reason (LLM):** outliers present
- **Result:** values_clipped=248, lower=-47.0, upper=81.0

### `MntGoldProds` — clip_outliers
- **Reason (LLM):** outliers present
- **Result:** values_clipped=207, lower=-61.5, upper=126.5

### `NumDealsPurchases` — clip_outliers
- **Reason (LLM):** outliers present
- **Result:** values_clipped=86, lower=-2.0, upper=6.0

### `NumWebPurchases` — clip_outliers
- **Reason (LLM):** outliers present
- **Result:** values_clipped=4, lower=-4.0, upper=12.0

### `NumCatalogPurchases` — clip_outliers
- **Reason (LLM):** outliers present
- **Result:** values_clipped=23, lower=-6.0, upper=10.0

### `NumWebVisitsMonth` — clip_outliers
- **Reason (LLM):** outliers present
- **Result:** values_clipped=8, lower=-3.0, upper=13.0

### `Z_CostContact` — drop_column
- **Reason (LLM):** constant column
- **Result:** column_dropped=Z_CostContact

### `Z_Revenue` — drop_column
- **Reason (LLM):** constant column
- **Result:** column_dropped=Z_Revenue

### `Dt_Customer` — standardize_date_format
- **Reason (LLM):** inconsistent date format
- **Result:** target_format=YYYY-MM-DD, unparseable_values=0