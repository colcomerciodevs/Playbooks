#!/usr/bin/env python3
# ============================================================
# Script: convert_json_to_excel.py
# Objetivo: Leer Salidas_Playbooks/version_sistemas.json y generar
#           un Excel en la misma carpeta con el contenido tabular.
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
except Exception as e:
    print("ERROR: Se requiere 'pandas' instalado. Instale con: pip install pandas openpyxl", file=sys.stderr)
    sys.exit(2)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(BASE_DIR, "Salidas_Playbooks")
JSON_PATH = os.path.join(OUT_DIR, "version_sistemas.json")
TS = datetime.now().strftime("%Y%m%d_%H%M%S")
XLSX_PATH = os.path.join(OUT_DIR, f"version_sistemas_{TS}.xlsx")

def main():
    if not os.path.exists(JSON_PATH):
        print(f"ERROR: No existe el archivo JSON esperado: {JSON_PATH}", file=sys.stderr)
        sys.exit(1)

    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        print("ERROR: El JSON no es una lista de objetos.", file=sys.stderr)
        sys.exit(1)

    # Validar columnas esperadas y normalizar
    rows = []
    for item in data:
        rows.append({
            "hostname": item.get("hostname", "N/A"),
            "ip": item.get("ip", "N/A"),
            "os_full_version": item.get("os_full_version", "N/A"),
        })

    df = pd.DataFrame(rows, columns=["hostname", "ip", "os_full_version"])

    # Guardar a Excel
    df.to_excel(XLSX_PATH, index=False)
    print(f"OK: Excel generado -> {XLSX_PATH}")

if __name__ == "__main__":
    main()
