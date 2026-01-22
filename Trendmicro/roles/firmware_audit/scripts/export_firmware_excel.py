import json
import sys
import pandas as pd

# Argumentos
json_file = sys.argv[1]
excel_file = sys.argv[2]

# Cargar JSON
with open(json_file, "r") as f:
    data = json.load(f)

# Crear DataFrame
df = pd.DataFrame(data)

# Orden fijo de columnas (por nombre, no por posición)
expected_columns = [
    "inventory_name",
    "hostname",
    "inventory_ip",
    "firmware",
    "secure_boot"
]

# Asegurar que todas existan (evita errores si alguna viene vacía)
for col in expected_columns:
    if col not in df.columns:
        df[col] = "N/A"

df = df[expected_columns]

# Renombrar columnas para Excel
df = df.rename(columns={
    "inventory_name": "Inventario",
    "hostname": "Hostname",
    "inventory_ip": "IP",
    "firmware": "Tipo de Sistema",
    "secure_boot": "Secure Boot"
})

# Exportar a Excel
df.to_excel(excel_file, index=False)

print(f"[OK] Reporte generado correctamente: {excel_file}")
