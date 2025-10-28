#!/usr/bin/env python3
# =============================================================================
# scripts/export_audit_excel.py
# CONVERTIDOR DE AUDITORÍA ZABBIX → EXCEL (.xlsx)
#
# Descripción:
#   Lee el JSON generado por audit_zabbix.yml y exporta un archivo Excel
#   con columnas:
#     InventoryHostname, Hostname, IP,
#     Estado_Agent1, Estado_Agent2,
#     Version_Agent1, Version_Agent2, OS
#
# Uso:
#   python3 scripts/export_audit_excel.py <json_entrada> <excel_salida>
#
# Ejemplo:
#   python3 scripts/export_audit_excel.py \
#       Salidas_Playbooks/audit_zabbix_extended.json \
#       Salidas_Playbooks/Auditoria_Zabbix_Agentes.xlsx
#
# Requisitos:
#   pip install pandas openpyxl
# =============================================================================

import sys
import json
import pandas as pd
from pathlib import Path

def main():
    # 1️⃣ Validar parámetros
    if len(sys.argv) < 3:
        print("Uso: export_audit_excel.py <json_entrada> <excel_salida>")
        sys.exit(1)

    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])

    # 2️⃣ Validar existencia del JSON
    if not src.exists():
        print(f"❌ ERROR: No existe el archivo JSON: {src}")
        sys.exit(2)

    # 3️⃣ Leer JSON
    with src.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list) or len(data) == 0:
        print("❌ ERROR: El JSON no contiene registros válidos.")
        sys.exit(3)

    # 4️⃣ Columnas esperadas
    base_cols = [
        "InventoryHostname", "Hostname", "IP",
        "Estado_Agent1", "Estado_Agent2",
        "Version_Agent1", "Version_Agent2", "OS"
    ]

    # 5️⃣ Crear DataFrame ordenado
    df = pd.DataFrame(data)
    ordered_cols = [c for c in base_cols if c in df.columns] + \
                   [c for c in df.columns if c not in base_cols]
    df = df[ordered_cols]

    # 6️⃣ Exportar a Excel
    with pd.ExcelWriter(dst, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="AuditoriaZabbix")
        ws = writer.book["AuditoriaZabbix"]

        # 7️⃣ Ajustar ancho de columnas automáticamente
        for col in ws.columns:
            max_len = max((len(str(c.value)) if c.value else 0) for c in col)
            ws.column_dimensions[col[0].column_letter].width = min(max(12, max_len + 2), 60)

    # 8️⃣ Confirmar resultado
    print(f"✅ Exportado {len(df)} filas a {dst}")

if __name__ == "__main__":
    main()
