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

# 4️⃣ Renombrar/estandarizar columnas de salida
rename_map = {
    # Corrección del typo anterior
    "HOSTANME_INVENTARIO": "HOSTNAME_INVENTARIO",
    # Mantener nombres claros para reporte
    "REQUIERE_ENROLAR_DS2022": "REQUIERE ENROLAR DS2022",
    "DS_AGENT_REINICIO_OK": "REINICIO DS_AGENT OK",
    "DS_AGENT_ACTIVE": "DS_AGENT ACTIVE",
    "DS_AGENT_ENABLED": "DS_AGENT ENABLED",
    "TMXBC_ACTIVE": "TMXBC ACTIVE",
    "TMXBC_ENABLED": "TMXBC ENABLED",
}
data = data.rename(columns=rename_map)

# 5️⃣ Orden sugerido de columnas para mejor lectura
cols_pref = [
    "IP_INVENTARIO",
    "HOSTNAME_INVENTARIO",
    "HOSTNAME",
    "REQUIERE ENROLAR DS2022",
    "REINICIO DS_AGENT OK",
    "DS_AGENT ACTIVE",
    "DS_AGENT ENABLED",
    "TMXBC ACTIVE",
    "TMXBC ENABLED",
]
# Conservar cualquier columna adicional que pueda existir
cols_final = [c for c in cols_pref if c in data.columns] + [c for c in data.columns if c not in cols_pref]
data = data.reindex(columns=cols_final)

# 6️⃣ Exportar a Excel
with pd.ExcelWriter(output_xlsx, engine="openpyxl") as writer:
    data.to_excel(writer, index=False, sheet_name="Reporte_DS2022")

print(f"✅ Excel generado correctamente: {output_xlsx}")
