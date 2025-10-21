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
import os
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

# -------------------------------------------------------------------
# 1️⃣ Validar argumentos de entrada
# -------------------------------------------------------------------
# Se esperan exactamente 2 argumentos: el JSON de entrada y el Excel de salida
if len(sys.argv) != 3:
    print("Uso: python3 nessus_excel_report.py <input_json> <output_xlsx>")
    sys.exit(1)

# Asignamos los argumentos a variables legibles
json_file = sys.argv[1]
xlsx_file = sys.argv[2]

# Crear la carpeta destino si no existe (para evitar error al guardar)
os.makedirs(os.path.dirname(os.path.abspath(xlsx_file)), exist_ok=True)

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

# Validar que el JSON tenga formato de lista (lista de resultados por host)
if not isinstance(data, list):
    print("❌ El JSON no contiene una lista de resultados por host.")
    sys.exit(4)

# -------------------------------------------------------------------
# 3️⃣ Ordenar los datos (opcional, para un reporte más limpio)
# -------------------------------------------------------------------
# Se ordena por el nombre del host
try:
    data_sorted = sorted(data, key=lambda h: (h.get("host") or ""))
except Exception:
    data_sorted = data  # si falla, deja el orden original

# -------------------------------------------------------------------
# 4️⃣ Crear libro Excel y hoja principal
# -------------------------------------------------------------------
wb = Workbook()           # Crea un nuevo libro de Excel
ws = wb.active            # Obtiene la hoja activa
ws.title = "Reporte Nessus Agent"

# -------------------------------------------------------------------
# 5️⃣ Definir encabezados y estilos visuales
# -------------------------------------------------------------------
headers = [
    "Host",
    "OS Name",           # Nombre real del sistema (p.ej. Oracle Linux)
    "OS Family",         # Familia detectada por Ansible (RedHat, Debian, etc.)
    "Versión",
    "Agent Version",     # Versión del Nessus Agent
    "Agente Instalado",  # Estado de instalación
    "Servicio Activo",   # Estado del servicio systemd
    "Vinculado",         # Estado de vínculo con el Manager
    "Manager Host",      # Dirección del servidor Nessus Manager
    "Manager Port",      # Puerto de conexión (por defecto 8834)
    "Grupos",            # Grupos asignados durante el vínculo
    "Link Output",       # Salida del comando de link
    "Error",             # Mensaje de error si ocurrió
    "Timestamp",         # Fecha y hora de la ejecución
]

# Estilos para el encabezado (fondo azul, texto blanco y centrado)
header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
header_font = Font(bold=True, color="FFFFFF")
center_align = Alignment(horizontal="center", vertical="center")

# Inserta la fila de encabezado
ws.append(headers)

# Aplica el formato a cada celda del encabezado
for col_num, _ in enumerate(headers, start=1):
    cell = ws.cell(row=1, column=col_num)
    cell.fill = header_fill
    cell.font = header_font
    cell.alignment = center_align

# -------------------------------------------------------------------
# 6️⃣ Función auxiliar para normalizar valores vacíos
# -------------------------------------------------------------------
def nz(val, default="N/A"):
    """Devuelve el valor si existe, o 'N/A' si está vacío o None."""
    v = (val or "")
    v = v.strip() if isinstance(v, str) else v
    return v if v not in ("", None) else default

# Definir columnas donde se debe envolver texto (para textos largos)
long_cols = {"Link Output", "Error"}

# -------------------------------------------------------------------
# 7️⃣ Agregar filas con los datos del JSON
# -------------------------------------------------------------------
for host in data_sorted:
    row = [
        nz(host.get("host"), ""),
        nz(host.get("os_name")),                 # nombre real (Oracle Linux, etc.)
        nz(host.get("os_family")),
        nz(host.get("os_version")),
        nz(host.get("agent_version")),
        "✅" if host.get("installed") else "❌",
        "✅" if host.get("service_active") else "❌",
        "✅" if host.get("linked") else "❌",
        nz(host.get("manager_host")),
        nz(host.get("manager_port")),
        nz(host.get("groups")),
        nz(host.get("link_output")),
        nz(host.get("error")),
        nz(host.get("timestamp")),
    ]
    ws.append(row)

# -------------------------------------------------------------------
# 8️⃣ Ajustar formato de texto y ancho de columnas
# -------------------------------------------------------------------
# Envolver texto para columnas largas
wrap_align = Alignment(wrap_text=True, vertical="top")
for col_idx, title in enumerate(headers, start=1):
    if title in long_cols:
        for r in range(2, ws.max_row + 1):
            ws.cell(row=r, column=col_idx).alignment = wrap_align

# Ajustar automáticamente el ancho de cada columna
for col in ws.columns:
    max_length = 0
    column = col[0].column_letter
    for cell in col:
        try:
            if cell.value:
                max_length = max(max_length, len(str(cell.value)))
        except Exception:
            pass
    ws.column_dimensions[column].width = min(max_length + 2, 60)

# -------------------------------------------------------------------
# 9️⃣ Congelar encabezado y aplicar filtro automático
# -------------------------------------------------------------------
ws.freeze_panes = "A2"       # Deja fija la primera fila
ws.auto_filter.ref = ws.dimensions  # Activa filtro para todos los encabezados

# -------------------------------------------------------------------
# 🔟 Guardar el archivo Excel final
# -------------------------------------------------------------------
try:
    wb.save(xlsx_file)
    print(f"✅ Reporte Excel generado correctamente: {xlsx_file}")
except Exception as e:
    print(f"❌ Error al guardar Excel: {e}")
    sys.exit(5)
