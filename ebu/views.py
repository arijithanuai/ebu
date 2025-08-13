from django.shortcuts import render, redirect
from django.http import JsonResponse
from .models import Province, Kabupaten, Link, User
from .forms import UserForm
import csv
import sys
from django.contrib import messages

from shapely import wkt
import json

from .models import User
from django.contrib.gis.geos import GEOSGeometry
from shapely import wkt as shapely_wkt

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
        
        # # ----- DRP File Save (Optional) -----
        # drp_file = request.FILES.get('link_drpexcel')
        # if drp_file:
        #     drp.objects.create(admCode=admcode, drpFile=drp_file)
        #     messages.success(request, "  DRP file uploaded successfully!")
        # else:
        #     messages.info(request, "ℹ No DRP file uploaded.")

            
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

        return redirect('select_location')

    # GET request
    return render(request, 'pk.html', {'provinces': provinces})


def get_kabupatens(request):
    province_id = request.GET.get('province_id')
    kabupatens = Kabupaten.objects.filter(province_id=province_id).values('id', 'admNameEng', 'kCode')
    return JsonResponse(list(kabupatens), safe=False)

import pandas as pd
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


import io

@csrf_exempt
def validate_link_excel(request):
    if request.method == "POST" and request.FILES.get("link_excel"):
        file = request.FILES["link_excel"]
        admcode_from_form = request.POST.get("admcode", "").strip()  # <-- Get admcode sent via JS

        # Ensure AdmCode is selected before proceeding
        if not admcode_from_form:
            return JsonResponse({
                "valid": False,
                "message": "Please select Status/Province/Kabupaten first to generate AdmCode before uploading Excel."
            })

        try:
            df = pd.read_excel(file)
        except Exception as e:
            return JsonResponse({"valid": False, "message": f"Invalid Excel file: {e}"})

        required_cols = [
            "Adm_Code", "Link_No", "Link_Code", "Link_Name",
            "Link_Length_Official", "Link_Length_Actual", "Status"
        ]
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            return JsonResponse({"valid": False, "message": f"Missing columns: {', '.join(missing)}"})

        if df.empty:
            return JsonResponse({"valid": False, "message": "Excel file contains no data"})

        # Ensure all rows have same Adm_Code
        unique_admcodes = df["Adm_Code"].dropna().unique()
        if len(unique_admcodes) > 1:
            return JsonResponse({"valid": False, "message": "Excel file contains multiple different Adm_Code values."})

        excel_admcode = str(unique_admcodes[0]).strip()

        # Compare with selected AdmCode
        if excel_admcode != admcode_from_form:
            return JsonResponse({
                "valid": False,
                "message": f"Adm_Code in Excel ({excel_admcode}) does not match selected AdmCode ({admcode_from_form})."
            })

        # Check for missing required data in rows
        incomplete_rows = df[df[required_cols].isnull().any(axis=1)]
        if not incomplete_rows.empty:
            bad_links = incomplete_rows["Link_Code"].dropna().unique().tolist()
            return JsonResponse({
                "valid": False,
                "message": f"Missing data for Link_Code(s): {', '.join(map(str, bad_links))}"
            })

        #   Store file in session for later use
        file_stream = io.BytesIO()
        df.to_excel(file_stream, index=False)
        request.session['validated_file'] = file_stream.getvalue().decode('latin1')

        return JsonResponse({
            "valid": True,
            "message": f"Link Excel file is valid   ({len(df)} records)",
            "count": len(df)
        })

    return JsonResponse({"valid": False, "message": "No file uploaded"})


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
                try:
                    geom = wkt.loads(line_wkt)
                    if geom.geom_type != "LineString":
                        return JsonResponse({"valid": False, "message": f"Invalid geometry type for LinkNo {linkno}"})
                except Exception as e:
                    return JsonResponse({"valid": False, "message": f"Invalid WKT for LinkNo {linkno}: {e}"})
                link_data.append((linkno, line_wkt))

            if not link_data:
                return JsonResponse({"valid": False, "message": "No valid link data found in TXT"})

            # Store validated TXT in session
            request.session["validated_txt"] = json.dumps(link_data)

            return JsonResponse({"valid": True, "message": f"Map TXT file is valid   ({len(link_data)} records found)", "count": len(link_data)})

        except Exception as e:
            return JsonResponse({"valid": False, "message": f"Error reading TXT file: {e}"})

    return JsonResponse({"valid": False, "message": "No file uploaded"})
