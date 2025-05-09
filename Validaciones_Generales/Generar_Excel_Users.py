#!/usr/bin/env python3
import json
import re
import xlsxwriter

# Leer el JSON generado por Ansible
with open('Salidas_Playbooks/usuarios_permisos.json') as f:
    data = json.load(f)

# Crear el archivo Excel
workbook = xlsxwriter.Workbook('Salidas_Playbooks/usuarios_permisos.xlsx')
sheet = workbook.add_worksheet("Permisos")

# Definir encabezados
headers = ['Host', 'IP', 'Ambiente', 'Usuario', 'UID', 'Grupos', 'Tiene Sudo', 'Comandos Permitidos']
for col, h in enumerate(headers):
    sheet.write(0, col, h)

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

            # Extraer nombres de grupos usando regex para evitar duplicados y errores
            grupo_matches = re.findall(r'\(([^)]+)\)', id_info)
            grupos = ','.join(sorted(set(grupo_matches)))

        except Exception:
            continue

        # Clasificar permisos sudo
        tiene_sudo = 'NO'
        comandos = ''

        if 'may run the following commands' in sudo_info or '(ALL)' in sudo_info:
            comandos_permitidos = [l.strip() for l in sudo_info.splitlines() if l.strip().startswith('(')]
            comandos = '\n'.join(comandos_permitidos)

            if '!/sbin/su' in sudo_info:
                tiene_sudo = 'SÍ (restringido: no puede usar su)'
            elif len(comandos_permitidos) == 1 and (
                '(ALL) ALL' in comandos_permitidos[0] or '(ALL) NOPASSWD: ALL' in comandos_permitidos[0]
            ):
                tiene_sudo = 'SÍ'
            else:
                tiene_sudo = 'SÍ (limitado)'

        elif (
            'NO_SUDO' in sudo_info
            or 'is not allowed to run sudo' in sudo_info
            or 'may not run sudo' in sudo_info
            or 'not allowed to run sudo' in sudo_info
        ):
            tiene_sudo = 'NO'
            comandos = ''
        else:
            tiene_sudo = 'SÍ (limitado)'
            comandos = '\n'.join([l.strip() for l in sudo_info.splitlines() if l.strip().startswith('(')])

        # Escribir fila
        sheet.write(fila, 0, host)
        sheet.write(fila, 1, ip)
        sheet.write(fila, 2, ambiente)
        sheet.write(fila, 3, usuario)
        sheet.write(fila, 4, uid)
        sheet.write(fila, 5, grupos)
        sheet.write(fila, 6, tiene_sudo)
        sheet.write(fila, 7, comandos)
        fila += 1

# Cerrar y guardar el archivo
workbook.close()
print("✅ Excel generado correctamente: Salidas_Playbooks/usuarios_permisos.xlsx")
