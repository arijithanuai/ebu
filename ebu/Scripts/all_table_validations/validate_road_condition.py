import pandas as pd
from typing import Any, Dict, Tuple, List


# Required columns for the RoadCondition table
required_columns: List[str] = [
    "Year",
    "Province_Code",
    "Kabupaten_Code",
    "Link_No",
    "ChainageFrom",
    "ChainageTo",
]


# Field definitions inferred from the database design
# Supported types: "Short Text", "Number", "Yes/No"
field_definitions: Dict[str, Dict[str, Any]] = {
    "Year": {"type": "Number", "range": (0, float("inf"))},
    "Province_Code": {"type": "Short Text"},
    "Kabupaten_Code": {"type": "Short Text"},
    "Link_No": {"type": "Short Text"},
    "ChainageFrom": {"type": "Number"},
    "ChainageTo": {"type": "Number"},
    "DRP_From": {"type": "Number"},
    "Offset_From": {"type": "Number"},
    "DRP_To": {"type": "Number"},
    "Offset_To": {"type": "Number"},
    "Roughness": {"type": "Yes/No"},
    "Bleeding_area": {"type": "Number"},
    "Ravelling_area": {"type": "Number"},
    "Desintegration_area": {"type": "Number"},
    "CrackDep_area": {"type": "Number"},
    "Patching_area": {"type": "Number"},
    "OthCrack_area": {"type": "Number"},
    "Pothole_area": {"type": "Number"},
    "Rutting_area": {"type": "Number"},
    "EdgeDamage_area": {"type": "Number"},
    "Crossfall_area": {"type": "Number"},
    "Depressions_area": {"type": "Number"},
    "Erosion_area": {"type": "Number"},
    "Waviness_area": {"type": "Number"},
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

    if ftype == "Yes/No":
        acceptable_truthy = {True, 1, "1", "true", "True", "yes", "Yes", "y", "Y"}
        acceptable_falsy = {False, 0, "0", "false", "False", "no", "No", "n", "N"}
        if value in acceptable_truthy or value in acceptable_falsy:
            return True, ""
        # Also accept strings like "on"/"off"
        val_str = _normalize_str(value).lower()
        if val_str in {"on", "off"}:
            return True, ""
        return False, "Value must be Yes/No (boolean)"

    return True, ""


def validate_road_condition(df: pd.DataFrame, df_link: pd.DataFrame = None) -> pd.DataFrame:
    """
    Validate the RoadCondition table.

    - Ensures required columns exist
    - Ensures required columns are non-empty per row
    - Validates data types for known fields

    Returns a DataFrame with the same columns as input plus:
    - Record_No: 1-based row number from the input DataFrame
    - Validation_Message: aggregated error message for the row
    If no errors, returns an empty DataFrame with the same shape.
    """
    errors: List[pd.Series] = []

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

    # 3) Chainage sequence validation across groups of links
    # Group by Province_Code, Kabupaten_Code, and Year to check continuity across links
    group_keys: List[str] = [k for k in ["Province_Code", "Kabupaten_Code", "Year"] if k in df.columns]
    if "ChainageFrom" in df.columns and "ChainageTo" in df.columns and group_keys:
        grouped = df.groupby(group_keys, dropna=False, sort=False)
        for group_name, group in grouped:
            try:
                local = group.copy()
                local["__from"] = pd.to_numeric(local["ChainageFrom"], errors="coerce")
                local["__to"] = pd.to_numeric(local["ChainageTo"], errors="coerce")
                # Sort by Link_No first, then by ChainageFrom to maintain logical order
                local = local.sort_values(["Link_No", "__from"])

                if local.empty:
                    continue

                # Check if the first chainage starts at 0 for the entire group
                first_idx = local.index[0]
                if pd.isna(local.iloc[0]["__from"]) or local.iloc[0]["__from"] != 0:
                    r = df.loc[first_idx].copy()
                    r["Record_No"] = first_idx + 1
                    r["Validation_Message"] = f"ChainageFrom must start at 0 for the group {group_name}"
                    errors.append(r)

                # Check continuity across all links in the group
                prev_to = None
                prev_link_no = None
                for i, row_i in local.iterrows():
                    cf = row_i["__from"]
                    ct = row_i["__to"]
                    current_link_no = row_i["Link_No"]

                    if pd.isna(cf) or pd.isna(ct):
                        continue

                    # Check continuity - ChainageFrom should equal previous ChainageTo
                    # BUT ignore the first chainage of each link (when Link_No changes)
                    if prev_to is not None and prev_link_no is not None and current_link_no != prev_link_no:
                        # We're starting a new link, so don't check continuity for the first chainage
                        pass
                    elif prev_to is not None and cf != prev_to:
                        # Within the same link, check continuity
                        r = df.loc[i].copy()
                        r["Record_No"] = i + 1
                        r["Validation_Message"] = f"ChainageFrom ({cf}) must equal previous ChainageTo ({prev_to}) for continuous chainage within the same link"
                        errors.append(r)

                    prev_to = ct
                    prev_link_no = current_link_no
            except Exception:
                continue

    if errors:
        return pd.DataFrame(errors, columns=["Record_No"] + list(df.columns) + ["Validation_Message"])

    return pd.DataFrame(columns=["Record_No"] + list(df.columns) + ["Validation_Message"])


__all__ = [
    "required_columns",
    "field_definitions",
    "validate_road_condition",
]


