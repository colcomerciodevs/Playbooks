#!/usr/bin/env python3
# ============================================================
# SCRIPT: json_to_excel_ds2022.py
# AUTOR: Infraestructura Linux
# OBJETIVO:
#   - Convertir el archivo JSON generado por Ansible
#     (./Salidas_Playbooks/ds2022_result.json)
#     en un archivo Excel legible.
# SALIDA:
#   ./Salidas_Playbooks/ds2022_result.xlsx
# ============================================================

import os
import pandas as pd

# 1️⃣ Definir rutas
input_json = "./Salidas_Playbooks/ds2022_result.json"
output_xlsx = "./Salidas_Playbooks/ds2022_result.xlsx"

# 2️⃣ Validar existencia del JSON
if not os.path.exists(input_json):
    raise FileNotFoundError(f"❌ No se encuentra el archivo {input_json}")

# 3️⃣ Leer JSON
data = pd.read_json(input_json)

# 4️⃣ Renombrar columnas para formato de salida
data = data.rename(columns={
    "IP_INVENTARIO": "IP_INVENTARIO",
    "HOSTANME_INVENTARIO": "HOSTANME_INVENTARIO",
    "HOSTNAME": "HOSTNAME",
    "REQUIERE_ENROLAR_DS2022": "REQUIERE ENROLAR DS2022"
})

# 5️⃣ Exportar a Excel
with pd.ExcelWriter(output_xlsx, engine="openpyxl") as writer:
    data.to_excel(writer, index=False, sheet_name="Reporte_DS2022")

print(f"✅ Excel generado correctamente: {output_xlsx}")
