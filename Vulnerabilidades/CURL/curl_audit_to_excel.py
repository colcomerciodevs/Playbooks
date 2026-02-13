#!/usr/bin/env python3
"""
Genera un Excel (.xlsx) a partir del JSON consolidado por el playbook de auditoría curl/libcurl.

Columnas:
- IP (inventario)
- hostname
- versión curl
- versión libcurl
- OS, versión OS, kernel
- hints: GnuTLS / libssh
- rango afectado
- Estado (AFECTADA / NO AFECTADA)

Regla de afectación solicitada:
- Afectada si curl_version está entre 7.17.0 y 8.17.0 (inclusive)
- Si está afectada: fila en ROJO
- Si no está afectada: fila en VERDE

Uso:
    python3 curl_audit_to_excel.py /ruta/curl_audit.json /ruta/curl_audit_report.xlsx
"""

import json
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Alignment
from openpyxl.utils import get_column_letter

# Rango de versiones afectadas (inclusive)
AFFECTED_MIN = (7, 17, 0)
AFFECTED_MAX = (8, 17, 0)

# Colores (estilo Excel típico de condicional)
RED = PatternFill("solid", fgColor="FFC7CE")     # rojo claro
GREEN = PatternFill("solid", fgColor="C6EFCE")   # verde claro
HEADER = PatternFill("solid", fgColor="D9E1F2")  # azul/gris claro para encabezado


def parse_semver(ver: str):
    """
    Convierte una versión '8.7.1' a tupla (8,7,1).
    Si no es parseable, retorna None.
    """
    if not ver or ver == "NOT_INSTALLED":
        return None

    # Tomamos máximo 3 componentes y rellenamos con 0 si faltan
    parts = ver.strip().split(".")
    if len(parts) < 2:
        return None

    try:
        nums = [int(p) for p in parts[:3]]
        while len(nums) < 3:
            nums.append(0)
        return tuple(nums[:3])
    except ValueError:
        return None


def is_affected(ver: str) -> bool:
    """
    Retorna True si ver está dentro del rango afectado (inclusive).
    """
    t = parse_semver(ver)
    if t is None:
        return False
    return AFFECTED_MIN <= t <= AFFECTED_MAX


def autosize_columns(ws, max_width=60):
    """
    Ajuste básico del ancho de columnas según el contenido.
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
    # Validación de argumentos
    if len(sys.argv) < 3:
        print("Usage: python3 curl_audit_to_excel.py /path/curl_audit.json /path/curl_audit_report.xlsx")
        sys.exit(1)

    in_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2])

    # Leer JSON
    data = json.loads(in_path.read_text(encoding="utf-8"))

    # Crear workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "curl_audit"

    # Definición de columnas: (Nombre visible, key JSON)
    columns = [
        ("IP (inventario)", "ip_from_inventory"),
        ("Host (inventario)", "inventory_name"),
        ("Hostname", "hostname"),
        ("FQDN", "fqdn"),
        ("OS", "os"),
        ("OS Version", "os_version"),
        ("Kernel", "kernel"),
        ("curl instalado", "curl_installed"),
        ("curl version", "curl_version"),
        ("libcurl version", "libcurl_version"),
        ("Backend hint", "ssl_backend_hint"),
        ("Usa GnuTLS", "uses_gnutls"),
        ("Menciona libssh/libssh2", "mentions_libssh"),
        ("Rango afectado", "affected_range"),
        ("Estado", None),  # calculado
    ]

    # Escribir encabezado
    ws.append([c[0] for c in columns])
    for col_idx in range(1, len(columns) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = HEADER
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center", vertical="center")

    # Escribir filas
    for row in data:
        ver = row.get("curl_version", "")
        installed = bool(row.get("curl_installed"))
        affected = installed and is_affected(ver)

        status = "AFECTADA" if affected else "NO AFECTADA"

        values = []
        for _, key in columns:
            if key is None:
                values.append(status)
            else:
                values.append(row.get(key, ""))

        ws.append(values)

        # Pintar fila completa según estado
        fill = RED if affected else GREEN
        r = ws.max_row
        for c in range(1, len(columns) + 1):
            ws.cell(row=r, column=c).fill = fill

    # Ajustar anchos
    autosize_columns(ws)

    # Guardar
    wb.save(out_path)
    print(f"Excel generado: {out_path.resolve()}")


if __name__ == "__main__":
    main()
