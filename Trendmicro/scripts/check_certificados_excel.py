#!/usr/bin/env python3
import os
import sys
import pandas as pd

# Valores por defecto (compatibilidad)
default_input = "./Salidas_Playbooks/ds2022_result.json"
default_output = "./Salidas_Playbooks/ds2022_result.xlsx"

# Permitir argumentos: 1) input_json  2) output_xlsx
if len(sys.argv) >= 3:
    input_json = sys.argv[1]
    output_xlsx = sys.argv[2]
else:
    input_json = default_input
    output_xlsx = default_output

if not os.path.exists(input_json):
    raise FileNotFoundError(f"❌ No se encuentra el archivo {input_json}")

# Leer JSON
data = pd.read_json(input_json)

# Renombres + orden sugerido (incluyendo DS_AGENT_FORCE_KILL si existe)
rename_map = {
    "HOSTANME_INVENTARIO": "HOSTNAME_INVENTARIO",
    "REQUIERE_ENROLAR_DS2022": "REQUIERE ENROLAR DS2022",
    "DS_AGENT_REINICIO_OK": "REINICIO DS_AGENT OK",
    "DS_AGENT_ACTIVE": "DS_AGENT ACTIVE",
    "DS_AGENT_ENABLED": "DS_AGENT ENABLED",
    "TMXBC_ACTIVE": "TMXBC ACTIVE",
    "TMXBC_ENABLED": "TMXBC ENABLED",
}
data = data.rename(columns=rename_map)

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
    "DS_AGENT_FORCE_KILL",
]
cols_final = [c for c in cols_pref if c in data.columns] + [c for c in data.columns if c not in cols_pref]
data = data.reindex(columns=cols_final)

# Exportar a Excel con adornos si openpyxl está disponible
try:
    from openpyxl.utils import get_column_letter
    use_openpyxl = True
except Exception:
    use_openpyxl = False

with pd.ExcelWriter(output_xlsx, engine="openpyxl" if use_openpyxl else None) as writer:
    data.to_excel(writer, index=False, sheet_name="Reporte_DS2022")
    if use_openpyxl:
        ws = writer.book["Reporte_DS2022"]
        ws.auto_filter.ref = ws.dimensions
        ws.freeze_panes = "A2"
        for i, col in enumerate(data.columns, start=1):
            max_len = max([len(str(col))] + [len(str(x)) for x in data[col].astype(str).fillna("")])
            ws.column_dimensions[get_column_letter(i)].width = min(max_len + 2, 60)

print(f"✅ Excel generado correctamente: {output_xlsx}")
