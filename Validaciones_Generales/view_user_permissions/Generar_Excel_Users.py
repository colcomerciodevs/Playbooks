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

# Encabezados incluyendo Shell, Usuario Activo y Método de Bloqueo
headers = ['Host', 'IP', 'Ambiente', 'Grupo', 'Usuario', 'UID', 'Grupos', 'Shell',
           'Tiene Sudo', 'Comandos Permitidos', 'Usuario Activo', 'Método de Bloqueo']
for col, h in enumerate(headers):
    sheet.write(0, col, h)

fila = 1

# Procesar cada host
for host, valores in data.items():
    ip = valores.get('ip', '')
    ambiente = valores.get('ambiente', '')
    grupo = valores.get('grupo', '')

    for usuario_data in valores['usuarios']:
        partes = usuario_data.strip().split("###")
        if len(partes) != 4:
            continue

        id_info = partes[0].strip()
        sudo_info = partes[1].strip()
        shell = partes[2].strip()
        passwd_status = partes[3].strip()

        try:
            id_line = id_info.split()
            usuario = id_line[0].split('=')[1].split('(')[1][:-1]
            uid = [x for x in id_line if x.startswith("uid=")][0].split('=')[1].split('(')[0]
            grupo_matches = re.findall(r'\(([^)]+)\)', id_info)
            grupos = ','.join(sorted(set(grupo_matches)))

            # Determinar estado de usuario y método de bloqueo
            usuario_activo = 'SÍ'
            metodo_bloqueo = ''

            if shell.endswith('nologin') or shell.endswith('false') or 'shutdown' in shell:
                usuario_activo = 'NO'
                metodo_bloqueo = 'Shell'
            elif uid.isdigit() and int(uid) < 1000:
                usuario_activo = 'NO'
                metodo_bloqueo = 'UID < 1000'
            elif any(b in passwd_status for b in ['LK', '*', '!', '!!', 'NP']):
                usuario_activo = 'SÍ (solo llave privada SSH)'
                metodo_bloqueo = 'passwd -S / shadow'

        except Exception:
            continue

        tiene_sudo = 'NO'
        comandos = ''

        if 'may run the following commands' in sudo_info or '(ALL)' in sudo_info:
            comandos_permitidos = [l.strip() for l in sudo_info.splitlines() if l.strip().startswith('(')]
            comandos = '\n'.join(comandos_permitidos)

            tiene_all_all = any('(ALL) ALL' in c or '(ALL) NOPASSWD: ALL' in c for c in comandos_permitidos)
            tiene_restringidos = any('!' in c for c in comandos_permitidos)

            if tiene_all_all and not tiene_restringidos and len(comandos_permitidos) == 1:
                tiene_sudo = 'SÍ'
            elif tiene_restringidos:
                tiene_sudo = 'SÍ (limitado con restricciones)'
            else:
                tiene_sudo = 'SÍ (limitado)'
        elif any(x in sudo_info for x in ['NO_SUDO', 'not allowed to run sudo']):
            tiene_sudo = 'NO'
            comandos = ''
        else:
            comandos = '\n'.join([l.strip() for l in sudo_info.splitlines() if l.strip().startswith('(')])
            tiene_sudo = 'SÍ (limitado)'

        # Escribir datos al Excel
        sheet.write(fila, 0, host)
        sheet.write(fila, 1, ip)
        sheet.write(fila, 2, ambiente)
        sheet.write(fila, 3, grupo)
        sheet.write(fila, 4, usuario)
        sheet.write(fila, 5, uid)
        sheet.write(fila, 6, grupos)
        sheet.write(fila, 7, shell)
        sheet.write(fila, 8, tiene_sudo)
        sheet.write(fila, 9, comandos)
        sheet.write(fila, 10, usuario_activo)
        sheet.write(fila, 11, metodo_bloqueo)
        fila += 1

# Cerrar archivo Excel
workbook.close()
print("✅ Excel generado correctamente: Salidas_Playbooks/usuarios_permisos.xlsx")
