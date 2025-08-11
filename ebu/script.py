import os
import django
import sys
import pandas as pd

# Setup Django environment
sys.path.append('/home/aditya/Desktop/Arijit/HanuAI2/excel project/pkrms_ebu')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pkrms_ebu.settings')
django.setup()

from ebu.models import Province, Kabupaten

df = pd.read_csv("ebu/kab.csv")

print(f"📦 Importing {len(df)} rows...")

for index, row in df.iterrows():
    try:
        kab_code = str(row["kCode"]).strip()
        kab_name = str(row["admNameEng"]).strip()
        province_code = str(row["province_id"]).strip()

        province, _ = Province.objects.get_or_create(
            pCode=province_code
        )

        Kabupaten.objects.create(
            kCode=kab_code,
            admNameEng=kab_name,
            province=province
        )

        print(f"✅ Inserted Kabupaten: {kab_code} - {kab_name}")

    except Exception as e:
        print(f"❌ Error on row {index}: {e}")

print("✅ All Done!")
