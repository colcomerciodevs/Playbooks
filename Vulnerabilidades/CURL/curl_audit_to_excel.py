#!/usr/bin/env python3
"""
curl_audit_to_excel.py

- Lee JSON consolidado (curl_audit.json)
- Genera Excel (curl_audit_report.xlsx)

Requerimientos:
1) VERSION AFECTADA (SI/NO)
2) Solo esa celda se colorea:
   - SI -> rojo
   - NO -> verde
3) No mostrar "true/false": usar SI/NO
4) Incluir evidencia:
   - Linea 1 de 'curl --version'
   - Linea 'Protocols:' de 'curl -V'
   - Linea 'Features:' de 'curl -V'
"""

import json
import re
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font
from openpyxl.utils import get_column_letter

# Rango vulnerable (inclusive)
AFFECTED_MIN = (7, 17, 0)
AFFECTED_MAX = (8, 17, 0)

RED = PatternFill("solid", fgColor="FFC7CE")
GREEN = PatternFill("solid", fgColor="C6EFCE")


def yn(value) -> str:
    """Convierte booleanos o valores truthy/falsy a SI/NO."""
    return "SI" if bool(value) else "NO"


def normalize_version(version_str: str):
    """
    Extrae X.Y o X.Y.Z y retorna (X,Y,Z).
    Si no se puede parsear, retorna None.
    """
    if not version_str:
        return None
    m = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", version_str)
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)), int(m.group(3) or 0))


def is_affected(version_str: str) -> bool:
    """True si la versión cae en el rango vulnerable."""
    t = normalize_version(version_str)
    if t is None:
        return False
    return AFFECTED_MIN <= t <= AFFECTED_MAX


def autosize(ws, max_width=80):
    """Autoajusta anchos (cosmético)."""
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
        print("Uso: python3 curl_audit_to_excel.py curl_audit.json curl_audit_report.xlsx")
        sys.exit(1)

    json_path = Path(sys.argv[1])
    xlsx_path = Path(sys.argv[2])

    data = json.loads(json_path.read_text(encoding="utf-8"))

    wb = Workbook()
    ws = wb.active
    ws.title = "curl_audit"

    # Columnas mínimas + evidencias
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
        "VERSION AFECTADA",
        "EVIDENCIA curl --version (linea 1)",
        "EVIDENCIA Protocols:",
        "EVIDENCIA Features:",
    ]

    ws.append(headers)

    # encabezado en negrita
    for cell in ws[1]:
        cell.font = Font(bold=True)

    for r in data:
        installed = bool(r.get("curl_installed", False))
        curl_ver = r.get("curl_version", "") or ""

        affected = installed and is_affected(curl_ver)
        affected_text = "SI" if affected else "NO"

        row = [
            r.get("ip_from_inventory", ""),
            r.get("hostname", ""),
            r.get("os", ""),

            yn(installed),
            curl_ver,
            r.get("libcurl_version", ""),
            r.get("backend_ssl", ""),

            yn(r.get("uses_gnutls", False)),
            yn(r.get("uses_libssh", False)),
            yn(r.get("supports_ldap", False)),
            yn(r.get("supports_sftp", False)),

            affected_text,

            r.get("evidence_curl_version_line", ""),
            r.get("evidence_protocols_line", ""),
            r.get("evidence_features_line", ""),
        ]

        ws.append(row)

        # colorear SOLO la celda VERSION AFECTADA
        idx = headers.index("VERSION AFECTADA") + 1
        cell = ws.cell(row=ws.max_row, column=idx)
        cell.fill = RED if affected_text == "SI" else GREEN

    autosize(ws)
    wb.save(xlsx_path)
    print(f"Excel generado: {xlsx_path.resolve()}")


if __name__ == "__main__":
    main()
