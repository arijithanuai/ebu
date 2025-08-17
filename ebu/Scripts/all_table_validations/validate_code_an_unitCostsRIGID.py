import pandas as pd
from typing import Any, Dict, Tuple, List


# Required columns for the CODE_AN_UnitCostsRIGID table (top 3 columns)
required_columns: List[str] = [
    "Province_Code",
    "Kabupaten_Code",
    "CODE",
]


# Field definitions based on the database schema
# Supported types: "Short Text", "Number"
field_definitions: Dict[str, Dict[str, Any]] = {
    "Province_Code": {"type": "Short Text"},
    "Kabupaten_Code": {"type": "Short Text"},
    "CODE": {"type": "Short Text"},
    "PerUnitCost": {"type": "Number", "range": (0, float("inf"))},
    "RehUnitCost": {"type": "Number", "range": (0, float("inf"))},
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
            return False, f"Value must be numeric, got {type(value).__name__}"

        rng = field_def.get("range")
        if isinstance(rng, tuple) and len(rng) == 2:
            min_v, max_v = rng
            if (min_v is not None and num < min_v) or (max_v is not None and num > max_v):
                return False, f"Value must be between {min_v} and {max_v}"
        return True, ""

    return True, ""


def validate_code_an_unit_costs_rigid(df: pd.DataFrame) -> pd.DataFrame:
    """
    Validate the CODE_AN_UnitCostsRIGID table.

    - Ensures required columns exist
    - Ensures required columns are non-empty per row
    - Validates data types for known fields
    - Handles empty database scenario

    Returns a DataFrame with the same columns as input plus:
    - Record_No: 1-based row number from the input DataFrame
    - Validation_Message: aggregated error message for the row
    If no errors, returns an empty DataFrame with the same shape.
    """
    errors: List[pd.Series] = []

    # Check if database is completely empty - DISABLED FOR NOW
    # if df.empty:
    #     return pd.DataFrame(
    #         [
    #             {
    #                 "Record_No": "EMPTY_DB",
    #                 "Validation_Message": "⚠️ WARNING: CODE_AN_UnitCostsRIGID table is completely empty - no data found",
    #             }
    #         ]
    #     )

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

    # 2) Row-wise validations
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
    "validate_code_an_unit_costs_rigid",
]
