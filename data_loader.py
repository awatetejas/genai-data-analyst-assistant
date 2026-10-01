
import pandas as pd
from pathlib import Path


SUPPORTED_EXTENSIONS = {".csv", ".xlsx"}


def load_dataset(uploaded_file):
    """Load a CSV or Excel file into a Pandas DataFrame."""

    extension = Path(uploaded_file.name).suffix.lower()

    if extension == ".csv":
        df = pd.read_csv(uploaded_file)
    elif extension == ".xlsx":
        df = pd.read_excel(uploaded_file)
    else:
        raise ValueError(
            "Unsupported file format. Upload a CSV or XLSX file."
        )

    if df.empty:
        raise ValueError("The uploaded file contains no data.")

    # Normalize column names for consistent processing.
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.replace(" ", "_")
        .str.lower()
    )

    return df


def profile_dataset(df):
    """Return a basic data-quality and structure report."""

    return {
        "rows": len(df),
        "columns": len(df.columns),
        "duplicate_rows": int(df.duplicated().sum()),
        "missing_values": int(df.isna().sum().sum()),
        "column_names": df.columns.tolist(),
        "data_types": df.dtypes.astype(str).to_dict(),
    }