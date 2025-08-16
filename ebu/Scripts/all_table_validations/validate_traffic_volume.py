import pandas as pd
from typing import Any, Dict, Tuple, List
from datetime import datetime


# Required columns for the TrafficVolume table (important fields)
required_columns: List[str] = [
    "Year",
    "Province_Code",
    "Kabupaten_Code",
    "Link_No",
]


# Field definitions based on the database schema
# Supported types: "Short Text", "Number", "Yes/No"
field_definitions: Dict[str, Dict[str, Any]] = {
    "Year": {"type": "Number"},
    "Province_Code": {"type": "Short Text"},
    "Kabupaten_Code": {"type": "Short Text"},
    "Link_No": {"type": "Short Text"},
    "MarketDay": {"type": "Yes/No"},
    "TrafficCount": {"type": "Short Text"},
    "JourneyTime": {"type": "Number", "range": (0, float("inf"))},
    "AADT_MC": {"type": "Number", "range": (0, float("inf"))},
    "AADT_Car": {"type": "Number", "range": (0, float("inf"))},
    "AADT_Pickup": {"type": "Number", "range": (0, float("inf"))},
    "AADT_MicroTruck": {"type": "Number", "range": (0, float("inf"))},
    "AADT_Small_Bus": {"type": "Number", "range": (0, float("inf"))},
    "AADT_Large_Bus": {"type": "Number", "range": (0, float("inf"))},
    "AADT_Small_Truck": {"type": "Number", "range": (0, float("inf"))},
    "AADT_Medium_Truck": {"type": "Number", "range": (0, float("inf"))},
    "AADT_Large_Truck": {"type": "Number", "range": (0, float("inf"))},
    "AADT_Truck_Trailer": {"type": "Number", "range": (0, float("inf"))},
    "AADT_Semi_Trailer": {"type": "Number", "range": (0, float("inf"))},
    "AnalysisBaseYear": {"type": "Yes/No"},
    "SurveyBy": {"type": "Short Text"},
}


def _normalize_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    try:
        # pandas NA check without importing numpy here
        return pd.isna(value)  # type: ignore[arg-type]
    except Exception:
        return False


def validate_data_type(value: Any, field_name: str, field_def: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate a single value against the provided field definition.
    Empty values are considered valid here; required-ness is enforced separately.
    """
    if _is_empty(value):
        return True, ""

    ftype = field_def.get("type")

    if ftype == "Short Text":
        # Accept primitives convertible to text
        if not isinstance(value, (str, int, float)):
            return False, f"Value must be text, got {type(value).__name__}"
        return True, ""

    if ftype == "Number":
        try:
            num = float(value)
        except (TypeError, ValueError):
            # Special case for Year field
            if field_name == "Year":
                return False, "Enter a valid year"
            return False, f"Value must be numeric, got {type(value).__name__}"

        # Special validation for Year field
        if field_name == "Year":
            current_year = datetime.now().year
            if num <= 0:
                return False, "Enter a valid year"
            if num < 1900 or num > current_year:
                return False, "Enter a valid year"
            return True, ""

        rng = field_def.get("range")
        if isinstance(rng, tuple) and len(rng) == 2:
            min_v, max_v = rng
            if (min_v is not None and num < min_v) or (max_v is not None and num > max_v):
                return False, f"Value must be between {min_v} and {max_v}"
        return True, ""

    if ftype == "Yes/No":
        # Accept boolean values, 0/1, "Yes"/"No", "True"/"False"
        if isinstance(value, bool):
            return True, ""
        if isinstance(value, (int, float)) and value in [0, 1]:
            return True, ""
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in ["yes", "no", "true", "false", "1", "0"]:
                return True, ""
        return False, f"Value must be Yes/No, True/False, or 0/1, got {value}"

    return True, ""


def validate_traffic_volume(df: pd.DataFrame, df_link: pd.DataFrame = None) -> pd.DataFrame:
    """
    Validate the TrafficVolume table.

    - Ensures required columns exist
    - Ensures required columns are non-empty per row
    - Validates data types for known fields
    - Validates Link_No exists in Link table
    - Validates Link_No uniqueness (one record per link)
    - Handles empty database scenario

    Returns a DataFrame with the same columns as input plus:
    - Record_No: 1-based row number from the input DataFrame
    - Validation_Message: aggregated error message for the row
    If no errors, returns an empty DataFrame with the same shape.
    """
    errors: List[pd.Series] = []

    # Check if database is completely empty
    if df.empty:
        return pd.DataFrame(
            [
                {
                    "Record_No": "EMPTY_DB",
                    "Validation_Message": "⚠️ WARNING: TrafficVolume table is completely empty - no data found",
                }
            ]
        )

    # 1) Check for missing required columns (table schema level)
    missing_cols = [c for c in required_columns if c not in df.columns]
    if missing_cols:
        # Return a single-row dataframe describing the missing columns issue
        return pd.DataFrame(
            [
                {
                    "Record_No": "N/A",
                    **{col: None for col in df.columns},
                    "Validation_Message": f"Required columns missing: {', '.join(missing_cols)}",
                }
            ],
            columns=["Record_No"] + list(df.columns) + ["Validation_Message"],
        )

    # 2) Check Link_No uniqueness
    if "Link_No" in df.columns:
        link_no_counts = df["Link_No"].value_counts()
        duplicate_links = link_no_counts[link_no_counts > 1].index.tolist()
        if duplicate_links:
            for link_no in duplicate_links:
                duplicate_rows = df[df["Link_No"] == link_no]
                for idx, row in duplicate_rows.iterrows():
                    new_row = row.copy()
                    new_row["Record_No"] = idx + 1
                    new_row["Validation_Message"] = f"Link_No '{link_no}' is duplicated - only one record per link is allowed"
                    errors.append(new_row)

    # 3) Row-wise validations
    for idx, row in df.iterrows():
        row_errors: List[str] = []

        # Required column emptiness check
        for col in required_columns:
            if col in df.columns and _is_empty(row[col]):
                row_errors.append(f"{col} is required")

        # Data type checks for known fields
        for field_name, field_def in field_definitions.items():
            if field_name in df.columns:
                is_valid, msg = validate_data_type(row[field_name], field_name, field_def)
                if not is_valid:
                    row_errors.append(f"{field_name}: {msg}")

        # Cross-table validation: Check if Link_No exists in Link table
        if df_link is not None and "Link_No" in df.columns and "Link_No" in df_link.columns:
            link_no = row.get("Link_No")
            if not _is_empty(link_no):
                if link_no not in df_link["Link_No"].values:
                    row_errors.append(f"Link_No '{link_no}' does not exist in Link table")

        if row_errors:
            new_row = row.copy()
            new_row["Record_No"] = idx + 1
            new_row["Validation_Message"] = "; ".join(row_errors)
            errors.append(new_row)

    if errors:
        return pd.DataFrame(errors, columns=["Record_No"] + list(df.columns) + ["Validation_Message"])

    return pd.DataFrame(columns=["Record_No"] + list(df.columns) + ["Validation_Message"])


__all__ = [
    "required_columns",
    "field_definitions",
    "validate_traffic_volume",
]
