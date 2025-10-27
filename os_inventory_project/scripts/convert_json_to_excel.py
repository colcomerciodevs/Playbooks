#!/usr/bin/env python3
# ============================================================
# Script: convert_json_to_excel.py
# Objetivo:
#   Leer Salidas_Playbooks/version_sistemas.json (lista de objetos)
#   y generar un Excel con columnas:
#     - inventory_name, hostname, ip, os_full_version
# Limpieza extra:
#   - Elimina saltos de línea y dobles espacios
#   - Quita espacios al inicio/fin en todas las celdas de texto
# Requisitos: pandas, openpyxl
# Uso:
#   python3 scripts/convert_json_to_excel.py
# ============================================================

import json
import os
import sys
from datetime import datetime

try:
    import pandas as pd
except Exception:
    print("ERROR: Se requiere 'pandas' instalado. Instale con: pip install pandas openpyxl", file=sys.stderr)
    sys.exit(2)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(BASE_DIR, "Salidas_Playbooks")
JSON_PATH = os.path.join(OUT_DIR, "version_sistemas.json")
TS = datetime.now().strftime("%Y%m%d_%H%M%S")
XLSX_PATH = os.path.join(OUT_DIR, f"version_sistemas_{TS}.xlsx")

def autosize_columns(ws, df, padding=2):
    from openpyxl.utils import get_column_letter
    for idx, col in enumerate(df.columns, start=1):
        header_len = len(str(col))
        body_len = max((len(str(x)) for x in df[col].astype(str)), default=0)
        width = min(max(header_len, body_len) + padding, 80)
        ws.column_dimensions[get_column_letter(idx)].width = width

# --- NUEVO: limpiador de texto seguro y uniforme ---
def clean_text(value, default="N/A"):
    if value is None:
        return default
    s = str(value)
    # Normaliza saltos de línea/tabs y colapsa espacios
    s = s.replace("\r", " ").replace("\n", " ").replace("\t", " ")
    s = " ".join(s.split())
    s = s.strip()
    return s if s else default

def main():
    if not os.path.exists(JSON_PATH):
        print(f"ERROR: No existe el archivo JSON esperado: {JSON_PATH}", file=sys.stderr)
        sys.exit(1)

    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        print("ERROR: El JSON no es una lista de objetos.", file=sys.stderr)
        sys.exit(1)

    # Normaliza cada fila (limpieza aplicada a todas las columnas)
    rows = []
    for item in data:
        rows.append({
            "inventory_name": clean_text(item.get("inventory_name")),
            "hostname":       clean_text(item.get("hostname")),
            "ip":             clean_text(item.get("ip")),
            "os_full_version":clean_text(item.get("os_full_version")),
        })

    df = pd.DataFrame(
        rows, columns=["inventory_name", "hostname", "ip", "os_full_version"]
    ).sort_values(by=["inventory_name", "hostname"], kind="stable", ignore_index=True)

    os.makedirs(OUT_DIR, exist_ok=True)

    with pd.ExcelWriter(XLSX_PATH, engine="openpyxl") as writer:
        sheet_name = "Inventario SO"
        df.to_excel(writer, index=False, sheet_name=sheet_name)

        ws = writer.sheets[sheet_name]
        ws.freeze_panes = "A2"

        last_col_letter = ws.cell(row=1, column=df.shape[1]).column_letter
        ws.auto_filter.ref = f"A1:{last_col_letter}{df.shape[0] + 1}"

        try:
            autosize_columns(ws, df)
        except Exception:
            pass

    print(f"OK: Excel generado -> {XLSX_PATH}")

if __name__ == "__main__":
    main()
