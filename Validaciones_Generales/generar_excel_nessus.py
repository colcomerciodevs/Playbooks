import json
import os
import xlsxwriter

# 📂 Directorios de salida
salida_dir = "Salidas_Playbooks"
os.makedirs(salida_dir, exist_ok=True)

# 📁 Archivos
json_file = os.path.join(salida_dir, "nessus_auditoria.json")
excel_file = os.path.join(salida_dir, "nessus_auditoria.xlsx")

# 📥 Cargar datos
with open(json_file, "r") as file:
    data = json.load(file)

# 📊 Crear archivo Excel
workbook = xlsxwriter.Workbook(excel_file)
worksheet = workbook.add_worksheet("Nessus Audit")

# 🖌️ Estilos
header_format = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC'})
installed_format = workbook.add_format({'bg_color': '#C6EFCE'})      # verde
not_installed_format = workbook.add_format({'bg_color': '#FFCCCC'})  # rojo claro
neutral_format = workbook.add_format({'bg_color': '#FFF2CC'})        # amarillo claro para 'N/A'

# 🧩 Encabezados
worksheet.write('A1', 'Hostname', header_format)
worksheet.write('B1', 'IP', header_format)
worksheet.write('C1', 'Versión NessusAgent', header_format)
worksheet.write('D1', 'Estado', header_format)
worksheet.write('E1', 'Estado Final', header_format)

# 📝 Escribir datos
row = 1
for item in data:
    hostname = item.get("hostname", "Desconocido")
    ip = item.get("ip", "N/A")
    version_str = item.get("version_nessusagent", "No instalado")
    estado = item.get("estado", "No instalado")
    estado_final = item.get("estado_final", "N/A")

    worksheet.write(row, 0, hostname)
    worksheet.write(row, 1, ip)
    worksheet.write(row, 2, version_str)

    # Estado inicial (D)
    fmt = installed_format if estado.lower() == "instalado" else not_installed_format
    worksheet.write(row, 3, estado, fmt)

    # Estado final (E)
    if estado_final.lower() == "desinstalado":
        final_fmt = installed_format
    elif estado_final.lower() == "instalado":
        final_fmt = not_installed_format
    else:
        final_fmt = neutral_format

    worksheet.write(row, 4, estado_final, final_fmt)

    row += 1

# 🧾 Ajustes visuales
worksheet.autofilter(0, 0, row - 1, 4)
worksheet.set_column('A:E', 35)
workbook.close()

print(f"✅ Archivo Excel generado en '{excel_file}'")

