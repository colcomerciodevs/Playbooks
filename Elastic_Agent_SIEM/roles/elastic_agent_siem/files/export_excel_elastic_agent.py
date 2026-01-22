#!/usr/bin/env python3
import json
import sys
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

GREEN = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")  # verde suave
RED   = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")  # rojo suave
HEADER= PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")  # azul suave

def autosize(ws):
    for col in range(1, ws.max_column + 1):
        max_len = 0
        col_letter = get_column_letter(col)
        for cell in ws[col_letter]:
            val = "" if cell.value is None else str(cell.value)
            if len(val) > max_len:
                max_len = len(val)
        ws.column_dimensions[col_letter].width = min(max_len + 2, 70)

def main():
    if len(sys.argv) != 3:
        print("Uso: export_excel_elastic_agent.py <input.json> <output.xlsx>", file=sys.stderr)
        sys.exit(2)

    in_json = sys.argv[1]
    out_xlsx = sys.argv[2]

    with open(in_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    wb = Workbook()
    ws = wb.active
    ws.title = "Elastic Agent"

    headers = [
        "Inventario (inventory_hostname)",
        "Hostname real (ansible_hostname)",
        "IP del inventario",
        "Reinicio OK",
        "Estado del servicio (is-active)",
        "OK (verde/rojo)",
        "Extracto de status"
    ]
    ws.append(headers)

    # Estilo header
    for c in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=c)
        cell.font = Font(bold=True)
        cell.fill = HEADER
        cell.alignment = Alignment(horizontal="center", vertical="center")

    # Filas
    for item in data:
        inventory_name = item.get("inventory_name", "N/A")
        hostname = item.get("hostname", "N/A")
        inventory_ip = item.get("inventory_ip", "N/A")

        restart_ok = bool(item.get("restart_ok", False))
        is_active = item.get("is_active", "unknown")
        ok = bool(item.get("ok", False))
        excerpt = item.get("status_excerpt", "")

        ws.append([
            inventory_name,
            hostname,
            inventory_ip,
            "SI" if restart_ok else "NO",
            is_active,
            "OK" if ok else "NO OK",
            excerpt
        ])

        row = ws.max_row
        fill_ok = GREEN if ok else RED

        # Colorear:
        # 4 = Reinicio OK
        # 5 = Estado
        # 6 = OK
        ws.cell(row=row, column=6).fill = fill_ok                 # OK (verde/rojo)
        ws.cell(row=row, column=5).fill = fill_ok                 # Estado is-active
        ws.cell(row=row, column=4).fill = GREEN if restart_ok else RED  # Reinicio OK

        # Alinear columnas principales
        for col in [1, 2, 3, 4, 5, 6]:
            ws.cell(row=row, column=col).alignment = Alignment(horizontal="center", vertical="center")

        # Extracto con wrap
        ws.cell(row=row, column=7).alignment = Alignment(wrap_text=True, vertical="top")

    autosize(ws)
    wb.save(out_xlsx)

if __name__ == "__main__":
    main()
