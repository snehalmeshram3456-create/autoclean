"""Loads raw data files (CSV, XLSX, JSON) into a pandas DataFrame."""
from pathlib import Path

import chardet
import pandas as pd


def _detect_encoding(path: Path) -> str:
    with open(path, "rb") as f:
        raw = f.read(50000)
    result = chardet.detect(raw)
    return result.get("encoding") or "utf-8"


def load_data(file_path: str) -> pd.DataFrame:
    """Load a CSV, XLSX, or JSON file into a DataFrame.

    Raises:
        ValueError: unsupported file extension.
        FileNotFoundError: file does not exist.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    suffix = path.suffix.lower()

    if suffix == ".csv":
        encoding = _detect_encoding(path)
        try:
            df = pd.read_csv(path, encoding=encoding, sep=None, engine="python")
        except Exception:
            # Fall back to plain defaults if sniffing fails
            df = pd.read_csv(path, encoding=encoding)
    elif suffix in (".xlsx", ".xls"):
        df = pd.read_excel(path)
    elif suffix == ".json":
        df = pd.read_json(path)
    else:
        raise ValueError(
            f"Unsupported file type '{suffix}'. Supported: .csv, .xlsx, .xls, .json"
        )

    if df.empty:
        raise ValueError("Loaded file contains no data.")

    return df


def save_data(df: pd.DataFrame, output_path: str) -> None:
    """Save a DataFrame back out, matching the extension of output_path."""
    path = Path(output_path)
    suffix = path.suffix.lower()
    path.parent.mkdir(parents=True, exist_ok=True)

    if suffix == ".csv":
        df.to_csv(path, index=False)
    elif suffix in (".xlsx", ".xls"):
        df.to_excel(path, index=False)
    elif suffix == ".json":
        df.to_json(path, orient="records", indent=2)
    else:
        raise ValueError(f"Unsupported output file type '{suffix}'")
