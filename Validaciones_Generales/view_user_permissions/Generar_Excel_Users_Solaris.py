#!/usr/bin/env python3
import json
import re
import xlsxwriter

# Leer el JSON generado por Ansible
with open('Salidas_Playbooks/usuarios_permisos_solaris.json') as f:
    data = json.load(f)

# Crear el archivo Excel
workbook = xlsxwriter.Workbook('Salidas_Playbooks/usuarios_permisos_solaris.xlsx')
sheet = workbook.add_worksheet("Permisos_Solaris")

# Encabezados
headers = ['Host', 'IP', 'Ambiente', 'Usuario', 'UID', 'Grupos', 'Tiene Sudo', 'Comandos Permitidos']
for col, header in enumerate(headers):
    sheet.write(0, col, header)

fila = 1

# Procesar cada host
for host, valores in data.items():
    ip = valores.get('ip', '')
    ambiente = valores.get('ambiente', '')

    for entrada in valores['usuarios']:
        partes = entrada.strip().split("###")
        if len(partes) != 2:
            continue

        id_info = partes[0].strip()
        sudo_info = partes[1].strip()

        try:
            # Extraer usuario y UID
            id_line = id_info.split()
            usuario = id_line[0].split('=')[1].split('(')[1][:-1]
            uid = [x for x in id_line if x.startswith("uid=")][0].split('=')[1].split('(')[0]

            # Extraer grupos
            grupo_matches = re.findall(r'\(([^)]+)\)', id_info)
            grupos = ','.join(sorted(set(grupo_matches)))

        except Exception:
            continue

        # Evaluar sudo y comandos permitidos
        tiene_sudo = 'NO'
        comandos = 'NO_SUDO'

        if sudo_info and "NO_SUDO" not in sudo_info:
            lines = sudo_info.splitlines()
            sudo_lines = [line.strip() for line in lines if re.search(r'\bALL\s*=\s*\(.*\)', line)]

            if sudo_lines:
                tiene_sudo = 'SÍ'
                comandos = '\n'.join([
                    line.split(None, 1)[1] if len(line.split(None, 1)) > 1 else line
                    for line in sudo_lines
                ])
            else:
                tiene_sudo = 'Desconocido'
                comandos = sudo_info.strip()

        # Escribir fila en Excel
        sheet.write(fila, 0, host)
        sheet.write(fila, 1, ip)
        sheet.write(fila, 2, ambiente)
        sheet.write(fila, 3, usuario)
        sheet.write(fila, 4, uid)
        sheet.write(fila, 5, grupos)
        sheet.write(fila, 6, tiene_sudo)
        sheet.write(fila, 7, comandos)
        fila += 1

# Cerrar y guardar Excel
workbook.close()
print("✅ Excel generado correctamente: Salidas_Playbooks/usuarios_permisos_solaris.xlsx")
