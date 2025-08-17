# validate_bridge_inventory.py

# Table-specific required columns - Only important fields
required_columns = [
    "Year",
    "Province_Code",
    "Kabupaten_Code", 
    "Link_No",
    "Bridge_Number",
]

def validate_row(row, df_link=None):
    errors = {}
    
    # Year - Number
    try:
        val = float(row["Year"])
        if val < 1900 or val > 2100:
            errors["Year"] = "year out of valid range (1900-2100)"
    except:
        errors["Year"] = "invalid number" if row["Year"] else "missing"
    
    # Province_Code - Short Text
    if not row["Province_Code"]:
        errors["Province_Code"] = "missing"
    elif not str(row["Province_Code"]).isalpha() and not str(row["Province_Code"]).isdigit():
        errors["Province_Code"] = "invalid format"
    
    # Kabupaten_Code - Short Text
    if not row["Kabupaten_Code"]:
        errors["Kabupaten_Code"] = "missing"
    
    # Link_No - Short Text
    if not row["Link_No"]:
        errors["Link_No"] = "missing"
    else:
        link_no = str(row["Link_No"]).strip()
        prov_code = str(row["Province_Code"]).strip()
        if not link_no.isdigit():
            errors["Link_No"] = "invalid format"
        elif len(link_no) != 12:
            errors["Link_No"] = "invalid length"
        elif not link_no.startswith(prov_code):
            errors["Link_No"] = "does not start with province code"
    
    # Bridge_Number - Short Text
    if not row["Bridge_Number"]:
        errors["Bridge_Number"] = "missing"
    
    # Cross-table validation: Check if Link_No exists in Link table
    if df_link is not None and "Link_No" in df_link.columns:
        link_no = row.get("Link_No")
        if link_no and str(link_no).strip():
            if link_no not in df_link["Link_No"].values:
                errors["Link_No"] = f"Link_No '{link_no}' does not exist in Link table"
    
    return errors
