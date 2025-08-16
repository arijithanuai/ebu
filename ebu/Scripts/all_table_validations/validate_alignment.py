# validate_alignment.py
import pandas as pd
import numpy as np
import re

# Required columns for Alignment table
required_columns = [
    "Link_No"  # main check
]

# Field definitions with data types
field_definitions = {
    "Province_Code": {"type": "Short Text"},
    "Kabupaten_Code": {"type": "Short Text"},
    "Link_No": {"type": "Short Text"},
    "Chainage": {"type": "Number", "numeric": True},
    "Chainage_RB": {"type": "Number", "numeric": True},
    "GPSPoint_North_Deg": {"type": "Number", "numeric": True},
    "GPSPoint_North_Min": {"type": "Number", "numeric": True},
    "GPSPoint_North_Sec": {"type": "Number", "numeric": True},
    "GPSPoint_East_Deg": {"type": "Number", "numeric": True},
    "GPSPoint_East_Min": {"type": "Number", "numeric": True},
    "GPSPoint_East_Sec": {"type": "Number", "numeric": True},
    # "Section_WKT_LineString": {"type": "Short Text"},
    "East": {"type": "Number", "numeric": True},
    "North": {"type": "Number", "numeric": True},
    "Hemis_NS": {"type": "Short Text"}
}

def normalize_number_for_comparison(value):
    """
    Normalize a number for comparison by removing decimals and trailing zeros.
    Returns the integer part as a string with trailing zeros removed.
    """
    if pd.isna(value) or value == "":
        return ""
    
    try:
        float_val = float(value)
        int_val = int(float_val)
        str_val = str(int_val)
        return str_val
    except (ValueError, TypeError):
        return ""

def first_two_digits(value):
    """Return the first two digits of the integer part of a numeric value as a string.
    If fewer than two digits exist, return whatever is available. Empty string on invalid.
    """
    base = normalize_number_for_comparison(value)
    if base == "":
        return ""
    return base[:2]

def validate_link_length_consistency(df_alignment, link_df):
    """
    Validate that the last Chainage_RB value for each Link_No in alignment
    has the same first two digits as the Link_Length_Actual from the link table.
    Decimals are ignored. Trailing zeros do not affect the comparison.
    """
    errors = []
    
    if "Link_No" in df_alignment.columns and "Chainage_RB" in df_alignment.columns:
        alignment_max_chainage = df_alignment.groupby("Link_No")["Chainage_RB"].max()
        
        for link_no, max_chainage in alignment_max_chainage.items():
            if pd.isna(link_no) or link_no == "":
                continue
            
            link_row = link_df[link_df["Link_No"].astype(str) == str(link_no)]
            if link_row.empty:
                continue
            
            link_length_actual = link_row.iloc[0]["Link_Length_Actual"]
            
            chainage_prefix = first_two_digits(max_chainage)
            length_prefix = first_two_digits(link_length_actual)
            
            if chainage_prefix and length_prefix and chainage_prefix != length_prefix:
                max_chainage_row = df_alignment[
                    (df_alignment["Link_No"].astype(str) == str(link_no)) &
                    (df_alignment["Chainage_RB"] == max_chainage)
                ]
                
                if not max_chainage_row.empty:
                    row_idx = max_chainage_row.index[0]
                    error_msg = (
                        f"First two digits of last Chainage_RB ({max_chainage}) "
                        f"do not match first two digits of Link_Length_Actual ({link_length_actual}) "
                        f"for Link_No {link_no}"
                    )
                    errors.append({
                        "row_index": row_idx,
                        "error": error_msg,
                        "link_no": link_no,
                        "chainage_rb": max_chainage,
                        "link_length_actual": link_length_actual
                    })
    
    return errors

def validate_link_length_official_consistency(df_alignment, link_df):
    """
    Validate that the last Chainage_RB value (in meters) for each Link_No in alignment
    matches the Link_Length_Official (in km) from the link table.
    Chainage_RB is in meters, Link_Length_Official is in km, so we convert km to meters for comparison.
    """
    errors = []
    
    if "Link_No" in df_alignment.columns and "Chainage_RB" in df_alignment.columns:
        alignment_max_chainage = df_alignment.groupby("Link_No")["Chainage_RB"].max()
        
        for link_no, max_chainage in alignment_max_chainage.items():
            if pd.isna(link_no) or link_no == "":
                continue
            
            link_row = link_df[link_df["Link_No"].astype(str) == str(link_no)]
            if link_row.empty:
                continue
            
            # Check if Link_Length_Official column exists
            if "Link_Length_Official" not in link_row.columns:
                continue
                
            link_length_official = link_row.iloc[0]["Link_Length_Official"]
            
            # Skip if Link_Length_Official is null or empty
            if pd.isna(link_length_official) or link_length_official == "":
                continue
            
            try:
                # Convert Link_Length_Official from km to meters for comparison
                link_length_official_meters = float(link_length_official) * 1000
                
                # Skip validation for links 1.5 km or shorter
                if link_length_official <= 1.5:
                    continue
                
                max_chainage_meters = float(max_chainage)
                
                # Compare with tolerance for floating point precision
                # Allow for close matches - use 1500 meters tolerance
                tolerance = 1500.0  # 1500 meters tolerance
                if abs(max_chainage_meters - link_length_official_meters) > tolerance:
                    max_chainage_row = df_alignment[
                        (df_alignment["Link_No"].astype(str) == str(link_no)) &
                        (df_alignment["Chainage_RB"] == max_chainage)
                    ]
                    
                    if not max_chainage_row.empty:
                        row_idx = max_chainage_row.index[0]
                        error_msg = (
                            f"Last Chainage_RB ({max_chainage} m) does not match "
                            f"Link_Length_Official ({link_length_official} km = {link_length_official_meters:.0f} m) "
                            f"within tolerance of {tolerance:.1f} m for Link_No {link_no}"
                        )
                        errors.append({
                            "row_index": row_idx,
                            "error": error_msg,
                            "link_no": link_no,
                            "chainage_rb": max_chainage,
                            "link_length_official": link_length_official,
                            "link_length_official_meters": link_length_official_meters
                        })
            except (ValueError, TypeError):
                # Skip if conversion fails
                continue
    
    return errors

def validate_data_type(value, field_name, field_def):
    """
    Validate data type for a specific field
    """
    if pd.isna(value) or value == "":
        return True, ""  # Allow empty/null values
    
    field_type = field_def["type"]
    
    if field_type == "Short Text":
        if not isinstance(value, (str, int, float)):
            return False, f"Value must be text, got {type(value).__name__}"
        
        str_value = str(value).strip()
        
        if "max_length" in field_def and len(str_value) > field_def["max_length"]:
            return False, f"Text too long (max {field_def['max_length']} characters)"
        
        if "valid_values" in field_def and str_value not in field_def["valid_values"]:
            return False, f"Invalid value. Must be one of: {field_def['valid_values']}"
        
        return True, ""
    
    elif field_type == "Number":
        try:
            num_value = float(value)
        except (ValueError, TypeError):
            return False, f"Value must be numeric, got {type(value).__name__}"
        
        if "range" in field_def:
            min_val, max_val = field_def["range"]
            if num_value < min_val or num_value > max_val:
                return False, f"Value must be between {min_val} and {max_val}"
        
        return True, ""
    
    return True, ""

def validate_alignment(df_alignment, link_df):
    """
    Validate alignment data including data types and referential integrity.
    Returns a DataFrame of invalid rows.
    """
    errors = []
    
    for idx, row in df_alignment.iterrows():
        row_errors = []
        
        # Validate data types for each field
        for field_name, field_def in field_definitions.items():
            if field_name in df_alignment.columns:
                value = row[field_name]
                is_valid, error_msg = validate_data_type(value, field_name, field_def)
                if not is_valid:
                    row_errors.append(f"{field_name}: {error_msg}")
        
        # Validate Link_No exists in Link table
        if "Link_No" in df_alignment.columns:
            link_no = str(row["Link_No"]).strip()
            if link_no and link_no not in link_df["Link_No"].astype(str).values:
                row_errors.append("Link_No not found in Link table")
        
        # Validate GPS coordinate consistency
        if all(field in df_alignment.columns for field in ["GPSPoint_North_Deg", "GPSPoint_North_Min", "GPSPoint_North_Sec"]):
            try:
                north_deg = float(row["GPSPoint_North_Deg"]) if pd.notna(row["GPSPoint_North_Deg"]) else 0
                north_min = float(row["GPSPoint_North_Min"]) if pd.notna(row["GPSPoint_North_Min"]) else 0
                north_sec = float(row["GPSPoint_North_Sec"]) if pd.notna(row["GPSPoint_North_Sec"]) else 0
                
                if north_deg == 0 and north_min == 0 and north_sec == 0:
                    row_errors.append("GPS North coordinates cannot all be zero")
            except (ValueError, TypeError):
                row_errors.append("Invalid GPS North coordinates")
        
        if all(field in df_alignment.columns for field in ["GPSPoint_East_Deg", "GPSPoint_East_Min", "GPSPoint_East_Sec"]):
            try:
                east_deg = float(row["GPSPoint_East_Deg"]) if pd.notna(row["GPSPoint_East_Deg"]) else 0
                east_min = float(row["GPSPoint_East_Min"]) if pd.notna(row["GPSPoint_East_Min"]) else 0
                east_sec = float(row["GPSPoint_East_Sec"]) if pd.notna(row["GPSPoint_East_Sec"]) else 0
                
                if east_deg == 0 and east_min == 0 and east_sec == 0:
                    row_errors.append("GPS East coordinates cannot all be zero")
            except (ValueError, TypeError):
                row_errors.append("Invalid GPS East coordinates")
        
        # # Validate WKT LineString format
        # if "Section_WKT_LineString" in df_alignment.columns:
        #     wkt_value = str(row["Section_WKT_LineString"]).strip()
        #     if wkt_value and wkt_value != "":
        #         if not wkt_value.upper().startswith("LINESTRING"):
        #             row_errors.append("Section_WKT_LineString must start with 'LINESTRING'")
        #         elif not re.match(r'^LINESTRING\s*\([^)]+\)$', wkt_value, re.IGNORECASE):
        #             row_errors.append("Invalid WKT LineString format")
        
        # If there are any errors for this row, add to errors list
        if row_errors:
            new_row = row.copy()
            new_row["Validation_Message"] = "; ".join(row_errors)
            new_row["Record_No"] = idx + 1
            errors.append(new_row)

    # Add cross-table validation for Link_Length_Actual consistency (first two digits only)
    # Temporarily disabled by request
    # length_consistency_errors = validate_link_length_consistency(df_alignment, link_df)
    # for error_info in length_consistency_errors:
    #     row_idx = error_info["row_index"]
    #     if row_idx < len(df_alignment):
    #         row = df_alignment.iloc[row_idx]
    #         new_row = row.copy()
    #         new_row["Validation_Message"] = error_info["error"]
    #         new_row["Record_No"] = row_idx + 1
    #         errors.append(new_row)

    # Add cross-table validation for Link_Length_Official consistency (Chainage_RB in meters vs Link_Length_Official in km)
    length_official_consistency_errors = validate_link_length_official_consistency(df_alignment, link_df)
    for error_info in length_official_consistency_errors:
        row_idx = error_info["row_index"]
        if row_idx < len(df_alignment):
            row = df_alignment.iloc[row_idx]
            new_row = row.copy()
            new_row["Validation_Message"] = error_info["error"]
            new_row["Record_No"] = row_idx + 1
            errors.append(new_row)

    if errors:
        return pd.DataFrame(errors, columns=["Record_No"] + list(df_alignment.columns) + ["Validation_Message"])
    else:
        return pd.DataFrame(columns=["Record_No"] + list(df_alignment.columns) + ["Validation_Message"])
