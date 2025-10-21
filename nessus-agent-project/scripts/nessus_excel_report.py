#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generador de reporte Excel desde el JSON de resultados de despliegue Nessus Agent.

- Lee un JSON (lista de dicts) producido por Ansible con la clave `nessus_result` por host.
- Crea un Excel con columnas útiles para auditoría (incluye "Link Status" nueva).
- Aplica estilos básicos, autoajuste de columnas y filtros.

Uso:
    python3 nessus_excel_report.py <input_json> <output_xlsx>

Ejemplo:
    python3 nessus_excel_report.py ./Salidas_Playbooks/nessus_results.json ./Salidas_Playbooks/nessus_agent_reporte.xlsx

Autor: Infraestructura Linux - John Ballen
Fecha: 2025-10-21
"""

import sys
import json
import os
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

# -------------------------------------------------------------------
# 1) Validar argumentos de entrada
# -------------------------------------------------------------------
# Se esperan exactamente 2 argumentos: ruta al JSON de entrada y ruta al XLSX de salida
if len(sys.argv) != 3:
    print("Uso: python3 nessus_excel_report.py <input_json> <output_xlsx>")
    sys.exit(1)

json_file = sys.argv[1]
xlsx_file = sys.argv[2]

# Asegurar que la carpeta destino del XLSX exista para evitar errores al guardar
os.makedirs(os.path.dirname(os.path.abspath(xlsx_file)), exist_ok=True)

# -------------------------------------------------------------------
# 2) Leer archivo JSON generado por Ansible
# -------------------------------------------------------------------
# El JSON debe ser una lista de objetos (uno por host) con campos como:
# host, os_name, os_family, os_version, agent_version, installed, service_active,
# linked, link_status, manager_host, manager_port, groups, link_output, error, timestamp
try:
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)
except FileNotFoundError:
    print(f"❌ No se encontró el archivo: {json_file}")
    sys.exit(2)
except json.JSONDecodeError as e:
    print(f"❌ Error al decodificar JSON: {e}")
    sys.exit(3)

# Validación mínima de formato: esperamos una lista
if not isinstance(data, list):
    print("❌ El JSON no contiene una lista de resultados por host.")
    sys.exit(4)

# -------------------------------------------------------------------
# 3) Ordenar los datos por host (opcional, mejora legibilidad)
# -------------------------------------------------------------------
try:
    data_sorted = sorted(data, key=lambda h: (h.get("host") or ""))
except Exception:
    # Si algo falla en la ordenación, seguimos con los datos tal cual
    data_sorted = data

# -------------------------------------------------------------------
# 4) Crear libro Excel y hoja principal
# -------------------------------------------------------------------
wb = Workbook()        # Crea un nuevo libro de Excel
ws = wb.active         # Obtiene la hoja activa
ws.title = "Reporte Nessus Agent"

# -------------------------------------------------------------------
# 5) Definir encabezados y estilos visuales
# -------------------------------------------------------------------
# Se agrega "Link Status" como nueva columna para ver el estado textual del vínculo
headers = [
    "Host",
    "OS Name",           # Nombre real del sistema (p.ej. Oracle Linux)
    "OS Family",         # Familia (p.ej. RedHat, Debian, Suse)
    "Versión",           # Versión del SO (p.ej. 9.5)
    "Agent Version",     # Versión del Nessus Agent (p.ej. 11.0.1-el9)
    "Agente Instalado",  # ✅/❌ según 'installed'
    "Servicio Activo",   # ✅/❌ según 'service_active'
    "Vinculado",         # ✅/❌ según 'linked'
    "Link Status",       # Nuevo: texto de "Link status:" del 'agent status'
    "Manager Host",
    "Manager Port",
    "Grupos",
    "Link Output",       # Salida del comando de link o línea "Linked to: ..."
    "Error",             # STDERR del link si lo hubo
    "Timestamp",
]

# Estilo de encabezado: fondo azul y texto blanco centrado
header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
header_font = Font(bold=True, color="FFFFFF")
center_align = Alignment(horizontal="center", vertical="center")

# Escribir fila de encabezados
ws.append(headers)
for col_num, _ in enumerate(headers, start=1):
    cell = ws.cell(row=1, column=col_num)
    cell.fill = header_fill
    cell.font = header_font
    cell.alignment = center_align

# -------------------------------------------------------------------
# 6) Helper para valores vacíos y configuración de columnas con texto largo
# -------------------------------------------------------------------
def nz(val, default="N/A"):
    """
    Normaliza valores:
      - Si val es cadena vacía o None -> devuelve default ("N/A")
      - Si val existe -> devuelve su versión 'strip()' si es str, o directamente val
    """
    v = (val or "")
    v = v.strip() if isinstance(v, str) else v
    return v if v not in ("", None) else default

# Columnas que pueden contener texto largo: aplicaremos 'wrap_text'
LONG_TEXT_COLUMNS = {"Link Output", "Error"}

# -------------------------------------------------------------------
# 7) Volcar datos por fila
# -------------------------------------------------------------------
# Para cada host de la lista, se arma una fila con emojis para instalado/activo/vinculado
for host in data_sorted:
    row = [
        nz(host.get("host"), ""),            # Host
        nz(host.get("os_name")),             # OS Name (Oracle Linux, etc.)
        nz(host.get("os_family")),           # OS Family (RedHat, Debian, etc.)
        nz(host.get("os_version")),          # Versión del SO
        nz(host.get("agent_version")),       # Version del agente
        "✅" if host.get("installed") else "❌",
        "✅" if host.get("service_active") else "❌",
        "✅" if host.get("linked") else "❌",
        nz(host.get("link_status")),         # NUEVO: Link Status textual
        nz(host.get("manager_host")),
        nz(host.get("manager_port")),
        nz(host.get("groups")),
        nz(host.get("link_output")),         # Salida del link (si existe)
        nz(host.get("error")),               # Error del link (si existe)
        nz(host.get("timestamp")),           # Timestamp ISO
    ]
    ws.append(row)

# -------------------------------------------------------------------
# 8) Ajustes visuales: wrap para columnas largas y ancho automático
# -------------------------------------------------------------------
# Envolver texto para columnas con contenido potencialmente largo
wrap_align = Alignment(wrap_text=True, vertical="top")
for col_idx, title in enumerate(headers, start=1):
    if title in LONG_TEXT_COLUMNS:
        for r in range(2, ws.max_row + 1):
            ws.cell(row=r, column=col_idx).alignment = wrap_align

# Autoajuste de ancho de columna con límite superior (60)
for col in ws.columns:
    max_length = 0
    column = col[0].column_letter  # letra de columna (A, B, C, ...)
    for cell in col:
        try:
            if cell.value:
                max_length = max(max_length, len(str(cell.value)))
        except Exception:
            # Si algún valor no se puede medir, lo ignoramos
            pass
    ws.column_dimensions[column].width = min(max_length + 2, 60)

# -------------------------------------------------------------------
# 9) Usabilidad: congelar encabezado y aplicar autofiltro
# -------------------------------------------------------------------
ws.freeze_panes = "A2"          # Congela la primera fila
ws.auto_filter.ref = ws.dimensions  # Activa filtro en todas las columnas

# -------------------------------------------------------------------
# 10) Guardar el Excel final
# -------------------------------------------------------------------
try:
    wb.save(xlsx_file)
    print(f"✅ Reporte Excel generado correctamente: {xlsx_file}")
except Exception as e:
    print(f"❌ Error al guardar Excel: {e}")
    sys.exit(5)
