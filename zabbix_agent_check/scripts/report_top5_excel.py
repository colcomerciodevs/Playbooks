#!/usr/bin/env python3
import json, sys
from pathlib import Path
import xlsxwriter

if len(sys.argv) != 3:
    print("Uso: python3 report_top5_excel.py <input.json> <output.xlsx>")
    sys.exit(1)

json_file, xlsx_file = Path(sys.argv[1]), Path(sys.argv[2])
if not json_file.exists():
    print(f"No existe el archivo {json_file}")
    sys.exit(2)

data = json.loads(json_file.read_text())

wb = xlsxwriter.Workbook(xlsx_file)
ws = wb.add_worksheet("Top5_Monitores")

headers = [
    "InventoryHostname", "Hostname", "IP",
    "Reinicio_Zabbix", "Estado_Zabbix",
    "Version_Zabbix", "Monitores_Creados"
]

fmt_bold = wb.add_format({"bold": True, "bg_color": "#C9DAF8"})
for col, h in enumerate(headers):
    ws.write(0, col, h, fmt_bold)

for row, item in enumerate(data, 1):
    for col, key in enumerate(headers):
        ws.write(row, col, item.get(key, ""))

for i in range(len(headers)):
    ws.set_column(i, i, 22)

wb.close()
print(f"Excel generado: {xlsx_file}")
