import json
import sys
import pandas as pd

json_file = sys.argv[1]
excel_file = sys.argv[2]

with open(json_file) as f:
    data = json.load(f)

df = pd.DataFrame(data)

df.columns = [
    "Inventario",
    "Hostname",
    "IP",
    "Tipo de Sistema",
    "Secure Boot"
]

df.to_excel(excel_file, index=False)

print(f"Reporte generado: {excel_file}")
