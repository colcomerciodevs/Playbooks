#!/usr/bin/env python3
import json, os, sys
from datetime import datetime

try:
    import xlsxwriter
except Exception as e:
    print("ERROR: Debe instalar 'xlsxwriter' (pip install xlsxwriter). Detalle:", e)
    sys.exit(1)

BASE = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(BASE, os.pardir))
OUT_DIR = os.path.join(PROJECT_DIR, "Salidas_Playbooks")

json_path = os.path.join(OUT_DIR, "zabbix_auditoria.json")
xlsx_path = os.path.join(OUT_DIR, f"zabbix_auditoria_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")

if not os.path.exists(json_path):
    print(f"No existe el JSON de entrada: {json_path}")
    sys.exit(0)

with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# Normalizar a lista
if isinstance(data, dict):
    rows = [data]
elif isinstance(data, list):
    rows = data
else:
    rows = []

wb = xlsxwriter.Workbook(xlsx_path)
ws = wb.add_worksheet("Zabbix-Agent2")

headers = ["hostname", "ip", "nueva_version_instalada", "version_zabbix_agent1", "version_zabbix_agent2", "estado_servicio_final"]
fmt_header = wb.add_format({"bold": True})
for c, h in enumerate(headers):
    ws.write(0, c, h, fmt_header)

for r, item in enumerate(rows, start=1):
    for c, h in enumerate(headers):
        ws.write(r, c, item.get(h, ""))

wb.close()
print(f"Excel generado: {xlsx_path}")
