#!/usr/bin/env python3
"""
curl_audit_to_excel.py

Convierte el JSON consolidado generado por el playbook en un Excel (.xlsx)
con información MINIMA para responder a Ciber.

Requerimiento principal:
- SOLO colorear la celda de la columna "VERSION AFECTADA"
  - SI  -> ROJO
  - NO  -> VERDE

Rango vulnerable (según solicitud Ciber):
- curl 7.17.0 hasta 8.17.0 (inclusive)

Uso:
  python3 curl_audit_to_excel.py /ruta/curl_audit.json /ruta/curl_audit_report.xlsx
"""

import json
import re
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font


# Rango vulnerable (inclusive)
AFFECTED_MIN = (7, 17, 0)
AFFECTED_MAX = (8, 17, 0)

# Colores para la celda "VERSION AFECTADA"
RED = PatternFill("solid", fgColor="FFC7CE")     # rojo claro
GREEN = PatternFill("solid", fgColor="C6EFCE")   # verde claro


def normalize_version_to_tuple(version_str: str):
    """
    Extrae un patrón de versión desde un string y lo convierte a tupla (X,Y,Z).

    Ejemplos:
    - "7.29.0"           -> (7,29,0)
    - "7.29.0-59.el7"    -> (7,29,0)
    - "8.10.1-xyz"       -> (8,10,1)
    - "" / None          -> None
    """
    if not version_str:
        return None

    # Buscar "X.Y" o "X.Y.Z" dentro del string
    m = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", version_str)
    if not m:
        return None

    major = int(m.group(1))
    minor = int(m.group(2))
    patch = int(m.group(3)) if m.group(3) else 0

    return (major, minor, patch)


def is_version_affected(version_str: str) -> bool:
    """
    Retorna True si la versión cae dentro del rango vulnerable (inclusive).
    """
    t = normalize_version_to_tuple(version_str)
    if t is None:
        return False
    return AFFECTED_MIN <= t <= AFFECTED_MAX


def main():
    # Validar argumentos
    if len(sys.argv) < 3:
        print("Uso: python3 curl_audit_to_excel.py /path/curl_audit.json /path/curl_audit_report.xlsx")
        sys.exit(1)

    json_path = Path(sys.argv[1])
    xlsx_path = Path(sys.argv[2])

    # Leer JSON consolidado
    data = json.loads(json_path.read_text(encoding="utf-8"))

    # Crear Excel
    wb = Workbook()
    ws = wb.active
    ws.title = "curl_audit"

    # Columnas MINIMAS (sin Q1..Q5 ni Observación)
    headers = [
        "IP",
        "Hostname",
        "OS",
        "Curl Instalado",
        "Curl Version",
        "Libcurl Version",
        "Backend SSL",
        "Usa GnuTLS",
        "Usa libssh",
        "Soporta LDAP",
        "Soporta SFTP",
        "VERSION AFECTADA"
    ]

    # Escribir encabezados
    ws.append(headers)
    for c in ws[1]:
        c.font = Font(bold=True)

    # Escribir filas por host
    for row in data:
        installed = bool(row.get("curl_installed", False))
        curl_ver = row.get("curl_version", "") or ""

        # Solo es "AFECTADA" si está instalado y la versión está en rango
        affected = installed and is_version_affected(curl_ver)
        affected_text = "SI" if affected else "NO"

        excel_row = [
            row.get("ip_from_inventory", ""),
            row.get("hostname", ""),
            row.get("os", ""),
            installed,
            curl_ver,
            row.get("libcurl_version", ""),
            row.get("ssl_backend_hint", ""),
            bool(row.get("uses_gnutls", False)),
            bool(row.get("uses_libssh_or_libssh2", False)),
            bool(row.get("supports_ldap", False)),
            bool(row.get("supports_sftp", False)),
            affected_text
        ]

        ws.append(excel_row)

        # Colorear SOLO la celda "VERSION AFECTADA"
        affected_col_idx = headers.index("VERSION AFECTADA") + 1
        cell = ws.cell(row=ws.max_row, column=affected_col_idx)
        cell.fill = RED if affected_text == "SI" else GREEN

    # Guardar Excel
    wb.save(xlsx_path)
    print(f"Excel generado: {xlsx_path.resolve()}")


if __name__ == "__main__":
    main()
