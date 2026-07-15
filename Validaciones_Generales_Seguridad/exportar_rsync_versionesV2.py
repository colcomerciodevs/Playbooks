import json
import os
import xlsxwriter
from packaging import version

salida_dir = "Salidas_Playbooks"
json_file = os.path.join(salida_dir, "rsync_versions.json")
excel_file = os.path.join(salida_dir, "rsync_versiones.xlsx")

with open(json_file, "r") as file:
    data = json.load(file)

workbook = xlsxwriter.Workbook(excel_file)
worksheet = workbook.add_worksheet("RSYNC Audit")

header_format = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC'})
vulnerable_format = workbook.add_format({'bg_color': '#FF8080'})
safe_format = workbook.add_format({'bg_color': '#C6EFCE'})
wrap_format = workbook.add_format({'text_wrap': True, 'valign': 'top'})

headers = [
    'Hostname',
    'IP',
    'Versión RSYNC',
    'Estado',
    'Uso detectado en',
    'Detalle uso en cron',
    'Detalle procesos',
    'Detalle scripts'
]

for col, header in enumerate(headers):
    worksheet.write(0, col, header, header_format)

row = 1
for host, info in data.items():
    ip = info.get("ip", "Desconocida")
    rsync_output = info.get("rsync_output", "")
    usos = info.get("uso_detectado_en", [])
    uso_str = ", ".join(usos) if usos else "No"

    cron_output = info.get("cron_output", "")
    proc_output = info.get("proc_output", "")
    scripts_output = info.get("scripts_output", "")

    worksheet.write(row, 0, host)
    worksheet.write(row, 1, ip)

    if "version" in rsync_output.lower():
        try:
            rsync_version = rsync_output.split()[2]
        except IndexError:
            rsync_version = "Desconocida"
    else:
        rsync_version = "No instalado"

    worksheet.write(row, 2, rsync_version)

    if rsync_version != "No instalado":
        try:
            if version.parse(rsync_version) < version.parse("3.4.0"):
                estado = "Vulnerable"
                fmt = vulnerable_format
            else:
                estado = "No vulnerable"
                fmt = safe_format
        except Exception:
            estado = "Versión no válida"
            fmt = vulnerable_format
    else:
        estado = "No instalado"
        fmt = safe_format

    worksheet.write(row, 3, estado, fmt)
    worksheet.write(row, 4, uso_str)
    worksheet.write(row, 5, cron_output, wrap_format)
    worksheet.write(row, 6, proc_output, wrap_format)
    worksheet.write(row, 7, scripts_output, wrap_format)

    row += 1

worksheet.autofilter(0, 0, row - 1, len(headers) - 1)
worksheet.set_column('A:A', 30)
worksheet.set_column('B:B', 20)
worksheet.set_column('C:D', 20)
worksheet.set_column('E:H', 50)

workbook.close()
print(f"✅ Excel generado: {excel_file}")
