#!/usr/bin/env python3
import json
import sys
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

GREEN = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
RED   = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
HEADER= PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")

def autosize(ws):
    for col in range(1, ws.max_column + 1):
        max_len = 0
        col_letter = get_column_letter(col)
        for cell in ws[col_letter]:
            val = "" if cell.value is None else str(cell.value)
            if len(val) > max_len:
                max_len = len(val)
        ws.column_dimensions[col_letter].width = min(max_len + 2, 60)

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

    headers = ["Hostname", "IP", "Reinicio OK", "Estado (is-active)", "OK (verde/rojo)", "Status excerpt"]
    ws.append(headers)

    for c in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=c)
        cell.font = Font(bold=True)
        cell.fill = HEADER
        cell.alignment = Alignment(horizontal="center", vertical="center")

    for item in data:
        hostname = item.get("hostname", "N/A")
        ip = item.get("ip", "N/A")
        restart_ok = bool(item.get("restart_ok", False))
        is_active = item.get("is_active", "unknown")
        ok = bool(item.get("ok", False))
        excerpt = item.get("status_excerpt", "")

        ws.append([
            hostname,
            ip,
            "SI" if restart_ok else "NO",
            is_active,
            "OK" if ok else "NO OK",
            excerpt
        ])

        row = ws.max_row
        fill_ok = GREEN if ok else RED

        ws.cell(row=row, column=5).fill = fill_ok   # OK
        ws.cell(row=row, column=4).fill = fill_ok   # is-active
        ws.cell(row=row, column=3).fill = GREEN if restart_ok else RED

        for col in [1, 2, 3, 4, 5]:
            ws.cell(row=row, column=col).alignment = Alignment(horizontal="center")

        ws.cell(row=row, column=6).alignment = Alignment(wrap_text=True, vertical="top")

    autosize(ws)
    wb.save(out_xlsx)

if __name__ == "__main__":
    main()
