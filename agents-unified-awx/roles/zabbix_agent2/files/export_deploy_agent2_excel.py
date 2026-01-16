#!/usr/bin/env python3
import json
import sys
from pathlib import Path

try:
    import xlsxwriter
except Exception as e:
    print("ERROR: Debe instalar 'xlsxwriter' (pip install xlsxwriter). Detalle:", e)
    sys.exit(1)

def main():
    if len(sys.argv) != 3:
        print("Uso: python3 export_deploy_agent2_excel.py <input.json> <output.xlsx>")
        sys.exit(1)

    json_file = Path(sys.argv[1])
    xlsx_file = Path(sys.argv[2])

    if not json_file.exists():
        print(f"No existe el JSON de entrada: {json_file}")
        sys.exit(2)

    data = json.loads(json_file.read_text(encoding="utf-8"))

    # Normalizar a lista
    if isinstance(data, dict):
        rows = [data]
    elif isinstance(data, list):
        rows = data
    else:
        rows = []

    wb = xlsxwriter.Workbook(str(xlsx_file))
    ws = wb.add_worksheet("Zabbix-Agent2")

    headers = [
        "hostname", "ip", "nueva_version_instalada",
        "version_zabbix_agent1", "version_zabbix_agent2",
        "estado_servicio_final"
    ]

    fmt_header = wb.add_format({"bold": True})
    for c, h in enumerate(headers):
        ws.write(0, c, h, fmt_header)

    for r, item in enumerate(rows, start=1):
        for c, h in enumerate(headers):
            ws.write(r, c, item.get(h, ""))

    for i in range(len(headers)):
        ws.set_column(i, i, 24)

    wb.close()
    print(f"Excel generado: {xlsx_file}")
    sys.exit(0)

if __name__ == "__main__":
    main()
