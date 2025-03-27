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
worksheet = workbook.add_worksheet("Versiones RSYNC")

header_format = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC'})
vulnerable_format = workbook.add_format({'bg_color': '#FF8080'})
safe_format = workbook.add_format({'bg_color': '#C6EFCE'})

# ✅ Encabezados en orden: Hostname, IP, Versión, Estado
worksheet.write('A1', 'Hostname', header_format)
worksheet.write('B1', 'IP', header_format)
worksheet.write('C1', 'Versión RSYNC', header_format)
worksheet.write('D1', 'Estado', header_format)

row = 1
for host, info in data.items():
    ip = info.get("ip", "Desconocida")
    rsync_output = info.get("rsync_output", "")
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
    row += 1

worksheet.autofilter(0, 0, row - 1, 3)
worksheet.set_column('A:D', 30)
workbook.close()

print(f"Archivo Excel generado en '{excel_file}'")

