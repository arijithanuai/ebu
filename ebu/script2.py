import os
import django
import sys
import pandas as pd
import csv



# Setup Django environment
sys.path.append('/home/aditya/Desktop/Arijit/HanuAI2/excel project/pkrms_ebu')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pkrms_ebu.settings')
django.setup()


from ebu.models import Province, Kabupaten

 # change to your app name

# # Path to CSV file
# csv_file_path = 'ebu/admin_type_P.csv'  # adjust if in a subfolder

# # Read and insert into DB
# with open(csv_file_path, newline='', encoding='utf-8') as csvfile:
#     reader = csv.DictReader(csvfile)
#     for row in reader:
#         Province.objects.get_or_create(
#             pCode=row['pCode'].strip(),
#             admNameEng=row['admNameEng'].strip()
#         )

# print('✅ Provinces imported successfully.')

# =========================
# Import Kabupaten CSV
# =========================

df = pd.read_csv("ebu/kab.csv")

print(f"📦 Importing {len(df)} kabupaten rows...")

for index, row in df.iterrows():
    try:
        kab_code = str(row["kCode"]).strip()
        kab_name = row["admNameEng"].strip()
        province_code = str(row["province_id"]).strip()

        # Get related Province
        try:
            province = Province.objects.get(pCode=province_code)
        except Province.DoesNotExist:
            print(f"❌ Skipping row {index}: Province code {province_code} not found")
            continue

        # Create or update Kabupaten
        _, created = Kabupaten.objects.update_or_create(
            kCode=kab_code,
            defaults={
                'admNameEng': kab_name,
                'province': province
            }
        )

        if created:
            print(f"✅ Created Kabupaten: {kab_code} - {kab_name}")
        else:
            print(f"🔄 Updated Kabupaten: {kab_code} - {kab_name}")

    except Exception as e:
        print(f"❌ Error on row {index}: {e}")

print("✅ Kabupaten import finished.")
