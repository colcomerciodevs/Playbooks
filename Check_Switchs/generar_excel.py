#!/usr/bin/env python3
import xlsxwriter
import sys
import os

host = sys.argv[1]
output_dir = "/data/work/Salida_Check_Ports_Switchs/"
file_path = os.path.join(output_dir, f"{host}_salida.xlsx")

# Crear workbook
workbook = xlsxwriter.Workbook(file_path)

# Leer contenido de los tres archivos
comandos = {
    'sfpshow': f"{output_dir}/{host}_sfpshow.txt",
    'porterrshow': f"{output_dir}/{host}_porterrshow.txt",
    'switchshow': f"{output_dir}/{host}_switchshow.txt"
}

for hoja, archivo in comandos.items():
    worksheet = workbook.add_worksheet(hoja)
    if os.path.exists(archivo):
        with open(archivo, 'r') as f:
            for i, linea in enumerate(f):
                worksheet.write(i, 0, linea.strip())
    else:
        worksheet.write(0, 0, f"No data: {archivo}")

workbook.close()
