from django.shortcuts import render, redirect
from django.http import JsonResponse
from .models import Province, Kabupaten, Link, User
from .forms import UserForm

def location_selector(request):
    provinces = Province.objects.all()

    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            form.save()  # ✅ Save user to DB
            return redirect('select_location')  # or any success page
        else:
            print("Form errors:", form.errors)  # ✅ Print form errors for debug
    else:
        form = UserForm()

    return render(request, 'pk.html', {'provinces': provinces, 'form': form})

def get_kabupatens(request):
    province_id = request.GET.get('province_id')
    kabupatens = Kabupaten.objects.filter(province_id=province_id).values('id', 'admNameEng', 'kCode')
    return JsonResponse(list(kabupatens), safe=False)

import pandas as pd
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def validate_link_excel(request):
    if request.method == "POST" and request.FILES.get("link_excel"):
        file = request.FILES["link_excel"]
        
        # Step 1: Check if it's an Excel file
        try:
            df = pd.read_excel(file)
        except Exception as e:
            return JsonResponse({"valid": False, "message": f"Invalid Excel file: {e}"})
        
        # Step 2: Check required columns
        required_cols = ["Adm_Code", "Link_No", "Link_Code", "Link_Name", "Link_Length_Official", "Link_Length_Actual", "Status"]
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            return JsonResponse({"valid": False, "message": f"Missing columns: {', '.join(missing)}"})

         # Step 2: Check required columns
        required_cols = ["Adm_Code", "Link_No", "Link_Code", "Link_Name", "Link_Length_Official", "Link_Length_Actual", "Status"]
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            return JsonResponse({"valid": False, "message": f"Missing columns: {', '.join(missing)}"})

        # Step 3: Check if table is empty
        if df.empty:
            return JsonResponse({"valid": False, "message": "Excel file contains no data"})

        # Step 4: Check for missing fields in required columns
        # This will find rows with *any* NaN/empty in the required columns
        incomplete_rows = df[df[required_cols].isnull().any(axis=1)]
        if not incomplete_rows.empty:
            # Get unique Link_No values for rows with missing data
            bad_links = incomplete_rows["Link_No"].dropna().unique().tolist()
            return JsonResponse({
                "valid": False,
                "message": f"Missing data in required fields for Link_No(s): {', '.join(map(str, bad_links))}"
            })
        # Step 5: Passed validation
        return JsonResponse({"valid": True, "message": "Link Excel file is valid ✅"})

    return JsonResponse({"valid": False, "message": "No file uploaded"})

import io
from .models import Link

def save_link_excel(request):
    if request.method == "POST":
        file_content = request.session.get('validated_file')
        if not file_content:
            return JsonResponse({"success": False, "message": "No validated file found"})

        # Convert back to DataFrame
        file_stream = io.BytesIO(file_content.encode('latin1'))
        df = pd.read_excel(file_stream)

        objs = [
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
        Link.objects.bulk_create(objs, ignore_conflicts=True)

        # Clear stored file
        del request.session['validated_file']

        return JsonResponse({"success": True, "message": f"Saved {len(objs)} records"})
    return JsonResponse({"success": False, "message": "Invalid request"})

