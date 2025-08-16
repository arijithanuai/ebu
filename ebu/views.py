from django.shortcuts import render, redirect
from django.http import JsonResponse
from .models import Province, Kabupaten, Link, User, DrpFile
from .forms import UserForm
import csv
import sys
from django.contrib import messages
import pandas as pd
from django.views.decorators.csrf import csrf_exempt
import io
from shapely import wkt
import json
from django.contrib.gis.geos import GEOSGeometry
from django.urls import reverse
import base64


def location_selector(request):
    provinces = Province.objects.all()

    if request.method == 'POST':
        # ---- Save user info from plain HTML form ----
        admcode = request.POST.get('admcode')
        lgName = request.POST.get('lgName')
        emailId = request.POST.get('emailId')
        phoneNumber = request.POST.get('phoneNumber')

        user_obj = User.objects.create(
            admcode=admcode,
            lgName=lgName,
            emailId=emailId,
            phoneNumber=phoneNumber
        )
    
        # ----- Save Excel Data -----
        excel_linkcodes = set()
        file_content = request.session.get('validated_file')
        if file_content:
            file_stream = io.BytesIO(file_content.encode('latin1'))
            df = pd.read_excel(file_stream)

            excel_linkcodes = set(df["Link_Code"].astype(str))

            links_to_create = [
                Link(
                    admCode=row["Adm_Code"],
                    linkNo=row["Link_No"],
                    linkCode=row["Link_Code"],
                    linkName=row["Link_Name"],
                    linkLengthOfficial=row["Link_Length_Official"],
                    linkLengthActual=row["Link_Length_Actual"],
                    status=row["Status"]
                )
                for _, row in df.iterrows()
            ]
            Link.objects.bulk_create(links_to_create, ignore_conflicts=True)
            del request.session['validated_file']
            messages.success(
                request,
                f"  Link data uploaded successfully! {len(links_to_create)} records saved."
            )

        # ----- Save TXT Data (match by linkCode) -----
        txt_content = request.session.get("validated_txt")
        if txt_content:
            txt_link_data = json.loads(txt_content)

            from .models import Alignment
            alignments_to_create = []

            # Get mapping: linkCode → Link object
            link_map = {
                l.linkCode: l
                for l in Link.objects.filter(linkCode__in=excel_linkcodes)
            }

            for linkcode, line_wkt in txt_link_data:
                if linkcode in link_map:
                    # Convert TXT WKT to GEOSGeometry
                    geom = GEOSGeometry(line_wkt, srid=4326)

                    alignments_to_create.append(
                        Alignment(admCode=admcode, linkNo=link_map[linkcode], linkGeometry=geom)
                    )

            if alignments_to_create:
                Alignment.objects.bulk_create(alignments_to_create, ignore_conflicts=True)
                messages.success(
                    request,
                    f"  Alignment data uploaded successfully! {len(alignments_to_create)} records saved."
                )
            else:
                messages.warning(
                    request,
                    "⚠ No matching LinkCode found between TXT and Excel data."
                )

            del request.session['validated_txt']

        if request.FILES.get("link_drpexcel"):
            drp_file = request.FILES["link_drpexcel"]
            DrpFile.objects.create(admCode=admcode, drpFile=drp_file)
            messages.success(request, f"✅ DRP file uploaded successfully: {drp_file.name}")


        return redirect('select_location')

    # GET request
    return render(request, 'pk.html', {'provinces': provinces})


def get_kabupatens(request):
    province_id = request.GET.get('province_id')
    kabupatens = Kabupaten.objects.filter(province_id=province_id).values('id', 'admNameEng', 'kCode')
    return JsonResponse(list(kabupatens), safe=False)

from openpyxl import load_workbook
from openpyxl.styles import PatternFill
import base64
from openpyxl import load_workbook
from openpyxl.styles import PatternFill
import base64

@csrf_exempt
def validate_link_excel(request):
    if request.method == "POST" and request.FILES.get("link_excel"):
        file = request.FILES["link_excel"]
        admcode_from_form = request.POST.get("admcode", "").strip()

        if not admcode_from_form:
            return JsonResponse({
                "valid": False,
                "message": " Please select Status/Province/Kabupaten first to generate AdmCode before uploading Excel."
            })

        try:
            df = pd.read_excel(file)
        except Exception as e:
            return JsonResponse({"valid": False, "message": f" Invalid Excel file: {e}"})

        required_cols = [
            "Adm_Code", "Link_No", "Link_Code", "Link_Name",
            "Link_Length_Official", "Link_Length_Actual", "Status"
        ]
        errors = []
        row_error_map = {}

        # --- Schema validation ---
        missing = [col for col in required_cols if col not in df.columns]
        extra = [col for col in df.columns if col not in required_cols]

        if missing or extra:
            msg = []
            if missing:
                msg.append(f" Missing/Invalid columns: {', '.join(missing)}")
            if extra:
                msg.append(f" Extra/Unexpected columns: {', '.join(extra)}")
            return JsonResponse({
                "valid": False,
                "message": " Excel schema invalid ❌<br>" + "<br>".join(msg),
                "template_excel_url": reverse("download_template_excel")
            })

        if df.empty:
            return JsonResponse({"valid": False, "message": " Excel file contains no data"})

        # --- AdmCode validation ---
        unique_admcodes = df["Adm_Code"].dropna().unique()
        if len(unique_admcodes) > 1:
            errors.append(" Excel file contains multiple different Adm_Code values.")
        else:
            excel_admcode = str(unique_admcodes[0]).strip()
            if excel_admcode != admcode_from_form:
                errors.append(f" Adm_Code in Excel ({excel_admcode}) does not match selected AdmCode ({admcode_from_form}).")

        # --- Row-level validation ---
        seen_linknos, seen_linkcodes = set(), set()
        for idx, row in df.iterrows():
            row_errors = []
            link_code = str(row.get("Link_Code", "Unknown"))

            # Missing values
            missing_vals = [col for col in required_cols if pd.isnull(row[col])]
            if missing_vals:
                row_errors.append(f"Missing {', '.join(missing_vals)}")

            # Link_No must be integer
            try:
                int(row["Link_No"])
            except Exception:
                row_errors.append("Link_No must be an integer")

            # Status must be B/P/K
            if str(row["Status"]).strip().upper() not in ["B", "P", "K"]:
                row_errors.append("Status must be one of B, P, K")

            # Length numeric
            for col in ["Link_Length_Official", "Link_Length_Actual"]:
                try:
                    float(row[col])
                except Exception:
                    row_errors.append(f"{col} must be numeric")

            # Duplicates
            link_no = str(row["Link_No"])
            if link_no in seen_linknos:
                row_errors.append(f"Duplicate Link_No {link_no}")
            else:
                seen_linknos.add(link_no)

            if link_code in seen_linkcodes:
                row_errors.append(f"Duplicate Link_Code {link_code}")
            else:
                seen_linkcodes.add(link_code)

            if row_errors:
                row_error_map[idx] = row_errors

        # --- If errors exist → build error Excel ---
        if errors or row_error_map:
            file.seek(0)
            wb = load_workbook(file)
            ws = wb.active

            # Ensure H col header is "Error_Notes"
            ws["H1"].value = "Error_Notes"

            red_fill = PatternFill(start_color="FF9999", end_color="FF9999", fill_type="solid")

            for idx, row in df.iterrows():
                excel_row = idx + 2
                if idx in row_error_map:
                    # highlight full row
                    for col_idx in range(1, 8):  # A–G
                        ws.cell(row=excel_row, column=col_idx).fill = red_fill
                    # write errors in H
                    ws[f"H{excel_row}"].value = "; ".join(row_error_map[idx])

            # Save to memory
            output = io.BytesIO()
            wb.save(output)
            output.seek(0)

            # Save as base64 in session
            request.session["error_excel"] = base64.b64encode(output.getvalue()).decode("utf-8")

            # Return row-wise errors also for frontend
            row_msgs = [f"❌ Row {i+2} (Link_Code {df.loc[i,'Link_Code']}): {', '.join(errs)}"
                        for i, errs in row_error_map.items()]

            return JsonResponse({
                "valid": False,
                "message": "Excel validation failed ❌<br>" + "<br>".join(errors + row_msgs),
                "error_excel_url": reverse("download_error_excel")
            })

        # --- ✅ Valid Excel ---
        file_stream = io.BytesIO()
        df.to_excel(file_stream, index=False)
        request.session['validated_file'] = file_stream.getvalue().decode('latin1')

        return JsonResponse({
            "valid": True,
            "message": f"✅ Link Excel file is valid ({len(df)} records)",
            "count": len(df)
        })

    return JsonResponse({"valid": False, "message": " No file uploaded"})

@csrf_exempt
def validate_map_txt(request):
    if request.method == "POST" and request.FILES.get("map_txt"):
        file = request.FILES["map_txt"]

        try:
            import csv
            from shapely import wkt
            csv.field_size_limit(sys.maxsize) 
            link_data = []

            reader = csv.DictReader(
                (line.decode("utf-8") for line in file),
                delimiter=";"
            )

            for row in reader:
                linkno = str(row["LinkId"]).strip()
                line_wkt = row["Line"].strip()

                # Validate WKT
                try:
                    geom = wkt.loads(line_wkt)
                    if geom.geom_type != "LineString":
                        return JsonResponse({"valid": False, "message": f"Invalid geometry type for LinkId {linkno}"})
                except Exception as e:
                    return JsonResponse({"valid": False, "message": f"Invalid WKT for LinkId {linkno}: {e}"})

                link_data.append((linkno, line_wkt))

            if not link_data:
                return JsonResponse({"valid": False, "message": "No valid link data found in TXT"})

            #   Compare with Excel linkCodes from session
            matched_count = 0
            file_content = request.session.get("validated_file")
            if file_content:
                import io, pandas as pd
                file_stream = io.BytesIO(file_content.encode('latin1'))
                df = pd.read_excel(file_stream)

                excel_linkcodes = set(df["Link_Code"].astype(str))
                matched_count = sum(1 for linkno, _ in link_data if linkno in excel_linkcodes)

            #   Store validated TXT in session
            request.session["validated_txt"] = json.dumps(link_data)

            return JsonResponse({
                "valid": True,
                "message": f"Alignment TXT file is valid   ({len(link_data)} records, {matched_count} matched with Excel)",
                "count": matched_count
            })

        except Exception as e:
            return JsonResponse({"valid": False, "message": f"Error reading TXT file: {e}"})

    return JsonResponse({"valid": False, "message": "No file uploaded"})


from django.http import HttpResponse
from openpyxl import Workbook, load_workbook
from openpyxl.styles import PatternFill
import io

def download_error_excel(request):
    error_excel_b64 = request.session.get("error_excel")
    if not error_excel_b64:
        return HttpResponse("No error Excel available", status=404)

    error_excel = base64.b64decode(error_excel_b64)

    response = HttpResponse(
        error_excel,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="ExcelErrors.xlsx"'
    return response

# Serve empty schema template
def download_template_excel(request):
    required_cols = [
        "Adm_Code", "Link_No", "Link_Code", "Link_Name",
        "Link_Length_Official", "Link_Length_Actual", "Status"
    ]
    wb = Workbook()
    ws = wb.active
    ws.append(required_cols)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    response = HttpResponse(
        output,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response['Content-Disposition'] = 'attachment; filename="excel_template.xlsx"'
    return response
