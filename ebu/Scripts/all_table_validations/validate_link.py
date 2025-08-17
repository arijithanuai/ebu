# validate_link.py

# Table-specific required columns - Only important fields
required_columns = [
    "Province_Code",
    "Kabupaten_Code", 
    "Link_No",
    "Link_Code",
    "Link_Name",
    "Link_Length_Official",
    "Link_Length_Actual",
]

def validate_row(row):
    errors = {}
    
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
    
    # Link_Code - Short Text
    if not row["Link_Code"]:
        errors["Link_Code"] = "missing"
    
    # Link_Name - Short Text
    if not row["Link_Name"]:
        errors["Link_Name"] = "missing"
    
    # Link_Length_Official - Number
    try:
        val = float(row["Link_Length_Official"])
        if val < 0:
            errors["Link_Length_Official"] = "negative not allowed"
    except:
        errors["Link_Length_Official"] = "invalid number" if row["Link_Length_Official"] else "missing"
    
    # Link_Length_Actual - Number
    try:
        val = float(row["Link_Length_Actual"])
        if val < 0:
            errors["Link_Length_Actual"] = "negative not allowed"
    except:
        errors["Link_Length_Actual"] = "invalid number" if row["Link_Length_Actual"] else "missing"
    
    return errors
