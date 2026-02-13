#!/usr/bin/env python3
"""
curl_audit_to_excel.py

Convierte el JSON consolidado (generado por el playbook) a un Excel (.xlsx)
con enfoque directo para responder a Ciber:

- Columna: "VERSION AFECTADA" = SI / NO
  - SI (rojo) si la version detectada cae en rango 7.17.0 - 8.17.0 (inclusive)
  - NO (verde) en caso contrario

Incluye columnas alineadas a las preguntas solicitadas por Ciber:
1) curl/libcurl instalado
2) apps con libcurl embebido (requiere validación app)
3) backend libssh o GnuTLS
4) OAuth tokens vía curl (requiere validación app)
5) integraciones LDAP / SFTP (indicio por soporte)

Uso:
  python3 curl_audit_to_excel.py /ruta/curl_audit.json /ruta/curl_audit_report.xlsx
"""

import json
import re
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Alignment
from openpyxl.utils import get_column_letter

# Rango afectado informado por Ciber (inclusive)
AFFECTED_MIN = (7, 17, 0)
AFFECTED_MAX = (8, 17, 0)

# Estilos de color: SI en rojo, NO en verde
RED = PatternFill("solid", fgColor="FFC7CE")    # rojo claro
GREEN = PatternFill("solid", fgColor="C6EFCE")  # verde claro
HEADER = PatternFill("solid", fgColor="D9E1F2") # encabezado


def normalize_version_to_tuple(version_str: str):
    """
    Convierte strings como:
      - "7.29.0"
      - "7.29.0-59.el7"
      - "8.10.1-xyz"
    a una tupla (major, minor, patch), por ejemplo (7,29,0).

    Si no se puede, retorna None.
    """
    if not version_str:
        return None

    # Buscar el primer patrón "X.Y" o "X.Y.Z" dentro del string
    # Ej: "7.29.0-59.el7" => "7.29.0"
    m = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", version_str)
    if not m:
        return None

    major = int(m.group(1))
    minor = int(m.group(2))
    patch = int(m.group(3)) if m.group(3) is not None else 0

    return (major, minor, patch)


def is_version_affected(version_str: str) -> bool:
    """
    True si la versión está entre AFFECTED_MIN y AFFECTED_MAX (inclusive).
    """
    t = normalize_version_to_tuple(version_str)
    if t is None:
        return False
    return AFFECTED_MIN <= t <= AFFECTED_MAX


def autosize_columns(ws, max_width=70):
    """
    Ajuste simple del ancho de columnas según el contenido.
    """
    for col_idx in range(1, ws.max_column + 1):
        max_len = 0
        for row_idx in range(1, ws.max_row + 1):
            v = ws.cell(row=row_idx, column=col_idx).value
            if v is None:
                continue
            max_len = max(max_len, len(str(v)))
        ws.column_dimensions[get_column_letter(col_idx)].width = min(max_len + 2, max_width)


def main():
    if len(sys.argv) < 3:
        print("Uso: python3 curl_audit_to_excel.py /path/curl_audit.json /path/curl_audit_report.xlsx")
        sys.exit(1)

    json_path = Path(sys.argv[1])
    xlsx_path = Path(sys.argv[2])

    data = json.loads(json_path.read_text(encoding="utf-8"))

    wb = Workbook()
    ws = wb.active
    ws.title = "Auditoria_Curl"

    # Columnas orientadas a responder a Ciber
    headers = [
        "IP",
        "Hostname",
        "FQDN",
        "OS",
        "OS Version",
        "Kernel",

        # Evidencia curl/libcurl
        "Curl Instalado",
        "Curl Version",
        "Libcurl Version",

        # Backend / features (indicios)
        "Backend SSL Hint",
        "Usa GnuTLS",
        "Usa libssh/libssh2",
        "Soporta LDAP/LDAPS (indicio)",
        "Soporta SFTP (indicio)",
        "Soporta SCP (indicio)",

        # Vulnerabilidad
        "Rango Vulnerable",
        "VERSION AFECTADA (SI/NO)",

        # Respuesta directa a preguntas Ciber (en texto/booleanos)
        "Ciber Q1 - curl/libcurl instalado",
        "Ciber Q2 - libcurl embebido",
        "Ciber Q3 - backend libssh o GnuTLS",
        "Ciber Q4 - OAuth tokens via curl",
        "Ciber Q5 - LDAP/SFTP automatizado",

        # Observación/nota
        "Observacion"
    ]

    # Escribir encabezados
    ws.append(headers)
    for cell in ws[1]:
        cell.fill = HEADER
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center", vertical="center")

    # Escribir filas
    for row in data:
        installed = bool(row.get("curl_installed", False))
        curl_ver = row.get("curl_version", "") or ""
        affected = installed and is_version_affected(curl_ver)

        affected_text = "SI" if affected else "NO"

        # Observación clara para auditoría
        if affected:
            obs = "Curl dentro del rango vulnerable informado (7.17.0 - 8.17.0). Requiere actualizacion/mitigacion."
        else:
            obs = "Curl fuera del rango vulnerable o no instalado."

        excel_row = [
            row.get("ip_from_inventory", ""),
            row.get("hostname", ""),
            row.get("fqdn", ""),
            row.get("os", ""),
            row.get("os_version", ""),
            row.get("kernel", ""),

            installed,
            curl_ver,
            row.get("libcurl_version", ""),

            row.get("ssl_backend_hint", ""),
            bool(row.get("uses_gnutls", False)),
            bool(row.get("uses_libssh_or_libssh2", False)),
            bool(row.get("supports_ldap", False)),
            bool(row.get("supports_sftp", False)),
            bool(row.get("supports_scp", False)),

            row.get("affected_range", "7.17.0 - 8.17.0"),
            affected_text,

            # Respuestas a Ciber
            row.get("ciber_q1", ""),
            row.get("ciber_q2", ""),
            row.get("ciber_q3", ""),
            row.get("ciber_q4", ""),
            row.get("ciber_q5", ""),

            obs
        ]

        ws.append(excel_row)

        # Colorear la fila completa según "VERSION AFECTADA"
        fill = RED if affected_text == "SI" else GREEN
        current_row = ws.max_row
        for col in range(1, len(headers) + 1):
            ws.cell(row=current_row, column=col).fill = fill

    autosize_columns(ws)
    wb.save(xlsx_path)
    print(f"Excel generado: {xlsx_path.resolve()}")


if __name__ == "__main__":
    main()
