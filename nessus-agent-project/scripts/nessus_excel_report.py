#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generador de reporte Excel desde el JSON de resultados de despliegue Nessus Agent.

Uso:
    python3 nessus_excel_report.py <input_json> <output_xlsx>

Ejemplo:
    python3 nessus_excel_report.py ./output/nessus_results.json ./output/nessus_agent_reporte.xlsx

Autor: Infraestructura Linux - John Ballen
Fecha: 2025-10-21
"""

import sys
import json
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from datetime import datetime

# -------------------------------------------------------------------
# 1️⃣ Validar argumentos de entrada
# -------------------------------------------------------------------
if len(sys.argv) != 3:
    print("Uso: python3 nessus_excel_report.py <input_json> <output_xlsx>")
    sys.exit(1)

json_file = sys.argv[1]
xlsx_file = sys.argv[2]

# -------------------------------------------------------------------
# 2️⃣ Leer archivo JSON generado por Ansible
# -------------------------------------------------------------------
try:
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)
except FileNotFoundError:
    print(f"❌ No se encontró el archivo: {json_file}")
    sys.exit(2)
except json.JSONDecodeError as e:
    print(f"❌ Error al decodificar JSON: {e}")
    sys.exit(3)

# Validar formato esperado
if not isinstance(data, list):
    print("❌ El JSON no contiene una lista de resultados por host.")
    sys.exit(4)

# -------------------------------------------------------------------
# 3️⃣ Crear libro Excel y hoja principal
# -------------------------------------------------------------------
wb = Workbook()
ws = wb.active
ws.title = "Reporte Nessus Agent"

# -------------------------------------------------------------------
# 4️⃣ Definir encabezados y estilos
# -------------------------------------------------------------------
headers = [
    "Host",
    "OS Family",
    "Versión",
    "Agente Instalado",
    "Servicio Activo",
    "Vinculado",
    "Manager Host",
    "Manager Port",
    "Grupos",
    "Link Output",
    "Error",
    "Timestamp",
]

header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
header_font = Font(bold=True, color="FFFFFF")
center_align = Alignment(horizontal="center", vertical="center")

ws.append(headers)
for col_num, _ in enumerate(headers, start=1):
    cell = ws.cell(row=1, column=col_num)
    cell.fill = header_fill
    cell.font = header_font
    cell.alignment = center_align

# -------------------------------------------------------------------
# 5️⃣ Agregar filas con los datos del JSON
# -------------------------------------------------------------------
for host in data:
    ws.append([
        host.get("host", ""),
        host.get("os_family", ""),
        host.get("os_version", ""),
        "✅" if host.get("installed") else "❌",
        "✅" if host.get("service_active") else "❌",
        "✅" if host.get("linked") else "❌",
        host.get("manager_host", ""),
        host.get("manager_port", ""),
        host.get("groups", ""),
        host.get("link_output", "").strip(),
        host.get("error", "").strip(),
        host.get("timestamp", ""),
    ])

# -------------------------------------------------------------------
# 6️⃣ Ajustar ancho de columnas automáticamente
# -------------------------------------------------------------------
for col in ws.columns:
    max_length = 0
    column = col[0].column_letter
    for cell in col:
        try:
            if cell.value:
                max_length = max(max_length, len(str(cell.value)))
        except Exception:
            pass
    adjusted_width = min(max_length + 2, 60)  # ancho máximo 60 caracteres
    ws.column_dimensions[column].width = adjusted_width

# -------------------------------------------------------------------
# 7️⃣ Congelar encabezado y aplicar formato visual
# -------------------------------------------------------------------
ws.freeze_panes = "A2"
ws.auto_filter.ref = ws.dimensions

# -------------------------------------------------------------------
# 8️⃣ Guardar Excel
# -------------------------------------------------------------------
try:
    wb.save(xlsx_file)
    print(f"✅ Reporte Excel generado correctamente: {xlsx_file}")
except Exception as e:
    print(f"❌ Error al guardar Excel: {e}")
    sys.exit(5)
