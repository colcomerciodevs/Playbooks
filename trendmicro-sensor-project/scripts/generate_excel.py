#!/usr/bin/env python3
"""
Script: generate_excel.py
Objetivo:
  - Tomar el JSON consolidado generado por Ansible (con los resultados de instalación/validación)
  - Convertirlo en un archivo Excel con colores (verde si OK, naranja si REVISAR)
Uso:
  python3 generate_excel.py <input.json> <output.xlsx>
Dependencias:
  - openpyxl (para manejar Excel)
"""

import json
import sys
import openpyxl
from openpyxl.styles import PatternFill

# ===================== VALIDACIÓN DE ARGUMENTOS =====================
if len(sys.argv) < 3:
    print("Uso: python3 generate_excel.py <input.json> <output.xlsx>")
    sys.exit(1)

input_file = sys.argv[1]
output_file = sys.argv[2]

# ===================== LECTURA DEL JSON =====================
# Abrimos el archivo JSON con los resultados de Ansible
with open(input_file) as f:
    data = json.load(f)

# Si el archivo tiene un solo objeto (dict), lo convertimos a lista
# para procesarlo igual que si vinieran varios hosts
if isinstance(data, dict):
    data = [data]

# ===================== CREACIÓN DEL EXCEL =====================
wb = openpyxl.Workbook()          # Crear un nuevo workbook
ws = wb.active                    # Hoja activa
ws.title = "Reporte TrendMicro"   # Nombre de la hoja

# ===================== ENCABEZADOS =====================
headers = [
    "Host",
    "Version Before",
    "Release Before",
    "Version After",
    "Release After",
    "Service ds_agent",   # muestra active/running, etc.
    "Service vls_agent",  # active / inactive / no instalado
    "Service tmxbc",      # debe ser active para OK
    "Estado Final"
]
ws.append(headers)  # Primera fila con encabezados

# ===================== DEFINICIÓN DE COLORES =====================
green = PatternFill(start_color="92D050", end_color="92D050", fill_type="solid")   # Verde
orange = PatternFill(start_color="F4B084", end_color="F4B084", fill_type="solid") # Naranja

# ===================== NORMALIZADOR =====================
def norm(v):
    """Normaliza cualquier valor a str para Excel."""
    if v is None:
        return ""
    if isinstance(v, list):
        return " ".join(str(x) for x in v)
    if isinstance(v, dict):
        return json.dumps(v, ensure_ascii=False)
    return str(v)

# ===================== ITERACIÓN SOBRE LOS HOSTS =====================
for item in data:
    services_after = item.get("services_after", {}) or {}

    # Construimos cada fila con los datos del JSON (normalizados a str)
    row = [
        norm(item.get("host", "")),
        norm(item.get("ds_agent_version_before", "")),
        norm(item.get("ds_agent_release_before", "")),
        norm(item.get("ds_agent_version_after", "")),
        norm(item.get("ds_agent_release_after", "")),
        norm(services_after.get("ds_agent", "")),
        norm(services_after.get("vls_agent", "")),
        norm(services_after.get("tmxbc", "")),
        norm(item.get("estado_final", "")),
    ]

    ws.append(row)  # Añadimos la fila al Excel

    # ===================== COLOR DE ESTADO FINAL =====================
    estado_cell = ws.cell(row=ws.max_row, column=len(headers))  # Celda del estado final
    if row[-1] == "OK":
        estado_cell.fill = green
    else:
        estado_cell.fill = orange

# ===================== GUARDAR ARCHIVO =====================
wb.save(output_file)
print(f"Excel generado en {output_file}")
