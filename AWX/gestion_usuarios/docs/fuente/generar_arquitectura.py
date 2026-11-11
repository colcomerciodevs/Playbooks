#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Genera docs/Arquitectura_Gestion_Usuarios.pdf.

Las preguntas y sus valores por defecto se toman de awx/generar_encuestas.py.
Si se agrega una pregunta sin explicarla en EFECTO, el script falla.

Uso:  python3 -B docs/fuente/generar_arquitectura.py   (requiere reportlab)
"""
import html
import importlib.util
import os
import sys

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Flowable, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

sys.dont_write_bytecode = True
RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SALIDA = os.path.join(RAIZ, 'docs', 'Arquitectura_Gestion_Usuarios.pdf')
spec = importlib.util.spec_from_file_location('enc', os.path.join(RAIZ, 'awx', 'generar_encuestas.py'))
enc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(enc)

FUENTES = {
    'Texto': '/usr/share/fonts/dejavu-sans-fonts/DejaVuSansCondensed.ttf',
    'Negrita': '/usr/share/fonts/dejavu-sans-fonts/DejaVuSansCondensed-Bold.ttf',
    'Mono': '/usr/share/fonts/dejavu-sans-mono-fonts/DejaVuSansMono.ttf',
}
for nombre, ruta in FUENTES.items():
    pdfmetrics.registerFont(TTFont(nombre, ruta))
pdfmetrics.registerFontFamily('Texto', normal='Texto', bold='Negrita', italic='Texto', boldItalic='Negrita')

AZUL = colors.HexColor('#1F3A5F')
GRIS = colors.HexColor('#5B6573')
LINEA = colors.HexColor('#D5DAE1')
FONDO = colors.HexColor('#EEF2F7')
AMBAR = colors.HexColor('#FFF4DC')
ANCHO = A4[0] - 32 * mm

E = {
    'titulo': ParagraphStyle('titulo', fontName='Negrita', fontSize=21, leading=26, textColor=AZUL),
    'sub': ParagraphStyle('sub', fontName='Texto', fontSize=10.5, leading=15, textColor=GRIS, spaceAfter=8),
    'h1': ParagraphStyle('h1', fontName='Negrita', fontSize=14.5, leading=19, textColor=AZUL, spaceBefore=4, spaceAfter=5),
    'h2': ParagraphStyle('h2', fontName='Negrita', fontSize=10.5, leading=14, textColor=AZUL, spaceBefore=9, spaceAfter=4),
    'p': ParagraphStyle('p', fontName='Texto', fontSize=9.5, leading=13.5, spaceAfter=5),
    'c': ParagraphStyle('c', fontName='Texto', fontSize=8.5, leading=11.2),
    'cb': ParagraphStyle('cb', fontName='Negrita', fontSize=8.5, leading=11.2),
    'ch': ParagraphStyle('ch', fontName='Negrita', fontSize=8.5, leading=11.2, textColor=colors.white),
    'm': ParagraphStyle('m', fontName='Mono', fontSize=7.6, leading=10.4),
}


def P(texto, estilo='p'):
    return Paragraph(texto, E[estilo])


def tabla(encabezado, filas, anchos, estilos_columna=None):
    estilos_columna = estilos_columna or ['c'] * len(encabezado)
    datos = [[P(h, 'ch') for h in encabezado]]
    for fila in filas:
        datos.append([P(v, estilos_columna[i]) for i, v in enumerate(fila)])
    t = Table(datos, colWidths=[a * ANCHO for a in anchos], repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), AZUL),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LINEBELOW', (0, 0), (-1, -1), 0.4, LINEA),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
        ('LEFTPADDING', (0, 0), (-1, -1), 4), ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
    ]))
    return t


def nota(texto):
    t = Table([[P(texto, 'c')]], colWidths=[ANCHO])
    t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), AMBAR), ('LEFTPADDING', (0, 0), (-1, -1), 7),
                           ('RIGHTPADDING', (0, 0), (-1, -1), 7), ('TOPPADDING', (0, 0), (-1, -1), 5),
                           ('BOTTOMPADDING', (0, 0), (-1, -1), 6)]))
    return t


class Flujo(Flowable):
    """Cajas conectadas con flechas. Cada caja: (título, detalle)."""

    def __init__(self, cajas, alto=17 * mm, pies=None):
        super().__init__()
        self.cajas, self.alto_caja, self.pies = cajas, alto, pies or {}
        self.width = ANCHO
        self.height = alto + (10 * mm if self.pies else 2 * mm)

    def wrap(self, *_):
        return self.width, self.height

    def draw(self):
        c, n = self.canv, len(self.cajas)
        flecha = 7 * mm
        ancho = (self.width - flecha * (n - 1)) / n
        y = self.height - self.alto_caja
        for i, (titulo, detalle) in enumerate(self.cajas):
            x = i * (ancho + flecha)
            c.setFillColor(FONDO)
            c.setStrokeColor(AZUL)
            c.setLineWidth(0.8)
            c.roundRect(x, y, ancho, self.alto_caja, 2.2 * mm, fill=1, stroke=1)
            c.setFillColor(AZUL)
            c.setFont('Negrita', 8.3)
            c.drawCentredString(x + ancho / 2, y + self.alto_caja - 6 * mm, titulo)
            c.setFillColor(GRIS)
            c.setFont('Texto', 7.2)
            for j, linea in enumerate(detalle.split('\n')):
                c.drawCentredString(x + ancho / 2, y + self.alto_caja - 10.2 * mm - j * 3.3 * mm, linea)
            if i < n - 1:
                xa = x + ancho + 1 * mm
                xb = x + ancho + flecha - 1 * mm
                ym = y + self.alto_caja / 2
                c.setStrokeColor(AZUL)
                c.setFillColor(AZUL)
                c.line(xa, ym, xb - 1.5 * mm, ym)
                p = c.beginPath()
                p.moveTo(xb, ym)
                p.lineTo(xb - 2 * mm, ym + 1.2 * mm)
                p.lineTo(xb - 2 * mm, ym - 1.2 * mm)
                p.close()
                c.drawPath(p, fill=1, stroke=0)
            if i in self.pies:
                c.setFillColor(GRIS)
                c.setFont('Texto', 7.2)
                for j, linea in enumerate(self.pies[i].split('\n')):
                    c.drawCentredString(x + ancho / 2, y - 3.6 * mm - j * 3.2 * mm, linea)


# ---------------------------------------------------------------------------
# Qué provoca cada pregunta. La clave es la variable de la encuesta.
# ---------------------------------------------------------------------------
EFECTO = {
    'objetivo': 'En qué servidores se aplica: grupo, servidor o patrón. Debe existir en el inventario y no puede ser localhost.',
    'relacion_usuario': 'Usuario con el que se entra hoy al servidor (tux, adminso…). Debe poder usar sudo.',
    'relacion_clave': 'Contraseña SSH de ese usuario. AWX la guarda cifrada.',
    'relacion_clave_sudo': 'Solo si sudo pide una contraseña distinta a la de conexión.',
    'ticket_cambio': 'Número de ticket y motivo. Lo revisa quien aprueba.',
    'crear_origen': '<b>encuesta</b>: usuarios escritos abajo. <b>catalogo</b>: usuarios de un archivo de vars/catalogos/.',
    'crear_usuarios_texto': 'Una línea por usuario: <font name="Mono" size="7.6">usuario;Nombre completo;grupo</font>.',
    'crear_catalogo': 'Archivo a usar. El catálogo manda sobre la encuesta: admins_linux da sudo completo sin contraseña.',
    'crear_permitir_ssh': 'SI: agrega al grupo ssh_access (si existe) y al final de la línea AllowUsers de sshd_config (si existe). NO: no toca SSH.',
    'crear_grupos_secundarios': 'Se agregan si ya existen en el servidor. No se aceptan grupos privilegiados.',
    'crear_contrasena_inicial': 'Clave de las cuentas nuevas, mínimo 8 caracteres. AWX la guarda cifrada.',
    'crear_forzar_cambio': 'SI: el usuario debe cambiar la clave en su primer ingreso.',
    'crear_renovar_llave': 'NO: reutiliza la llave guardada (o crea una si no tiene). SI: crea llave nueva, archiva la anterior y la reemplaza solo en los servidores del objetivo.',
    'crear_sudo_nivel': '<b>ninguno</b>, <b>completo</b> (ALL) o <b>limitado</b> (solo los comandos indicados).',
    'crear_sudo_nopasswd': 'SI: sudo sin pedir clave. (En 1b se aplica siempre que haya sudo, porque la cuenta no tiene clave.)',
    'crear_sudo_comandos': 'Un comando por línea con ruta absoluta (nivel limitado).',
    'crear_actualizar_existentes': 'NO: las cuentas existentes se omiten. SI: se les aplica grupos, llave y sudo; su clave no cambia.',
    'contrasena_origen': '<b>lista</b>: los escritos. <b>catalogo</b>: los de un catálogo. <b>todos_uid_1000</b>: todas las cuentas UID ≥ 1000 de cada servidor. En bloque se omiten cuentas críticas, de servicio y sin clave.',
    'contrasena_usuarios': 'Cuentas, separadas por coma. En 2b solo si usuarios a incluir = lista.',
    'contrasena_catalogo': 'Archivo de vars/catalogos/ (si usuarios a incluir = catalogo).',
    'contrasena_confirmar_critica': 'Escribir CONFIRMAR para root, tux, adminso y similares. No se admite con all ni comodines.',
    'contrasena_nueva': 'Nueva clave, mínimo 8 caracteres. AWX la guarda cifrada.',
    'contrasena_confirmacion': 'Debe ser igual a la anterior.',
    'contrasena_nunca_caduca': 'SI: la clave no expira. Exige "Forzar cambio" en NO.',
    'contrasena_forzar_cambio': 'SI: debe cambiarla en el próximo ingreso. En cuentas críticas debe ser NO.',
    'contrasena_desbloquear': 'SI: reinicia intentos fallidos y quita una expiración vencida.',
    'auditoria_uid_minimo': 'Audita las cuentas desde este UID.',
    'auditoria_dias_inactividad': 'Solo informa: las cuentas sin ingreso en más de estos días aparecen como inactivas en el reporte. No bloquea ni modifica nada.',
    'eliminar_usuarios': 'Cuentas a procesar, separadas por coma. No se aceptan cuentas críticas.',
    'eliminar_accion': '<b>bloquear</b>, <b>reactivar</b> o <b>eliminar</b>.',
    'eliminar_respaldar_home': 'SI: comprime el home antes de borrarlo.',
    'eliminar_confirmacion': 'Escribir CONFIRMAR. Solo se exige para eliminar.',
}


def encuesta(clave):
    filas = []
    for q in enc.ENCUESTAS[clave]['spec']:
        if q['variable'] not in EFECTO:
            raise SystemExit('Falta explicar la pregunta: ' + q['variable'])
        defecto = q['default']
        if q['type'] == 'password':
            valor = '(se digita)'
        elif defecto in ('', None):
            valor = 'vacío'
        else:
            valor = str(defecto)
        nombre = html.escape(q['question_name']) + (' <font color="#B3261E">*</font>' if q['required'] else '')
        filas.append([nombre, html.escape(valor), EFECTO[q['variable']]])
    return tabla(['Pregunta', 'Por defecto', 'Qué provoca'], filas, [0.33, 0.12, 0.55])


def comandos(filas):
    datos = [[html.escape(a), html.escape(b), html.escape(c)] for a, b, c in filas]
    return tabla(['Dónde', 'Comando', 'Cuándo se ejecuta'], datos, [0.13, 0.57, 0.30], ['c', 'm', 'c'])


def seccion(titulo, intro, playbook, rol, nodos, clave, cmds, detiene, extra=None):
    bloque = [P(titulo, 'h1'), P(intro),
              tabla(['Playbook', 'Rol', 'Dónde se usa'], [[playbook, rol, nodos]], [0.38, 0.22, 0.40])]
    salida = [KeepTogether(bloque), P('Encuesta', 'h2'), encuesta(clave),
              P('Comandos que ejecuta, en orden', 'h2'), comandos(cmds), P('Se detiene sin cambiar nada si', 'h2'), P(detiene)]
    if extra:
        salida.append(extra)
    salida.append(PageBreak())
    return salida


VERIFICAR = [('Servidor', 'getent passwd', 'Verificación, solo lectura.')]
VERIFICAR_SSH = [('Servidor', 'sshd -t', 'Verificación: si sshd_config tiene AllowUsers y Permitir SSH = SI.')]
CUENTA = [
    ('Servidor', 'getent passwd ; getent group', 'Siempre.'),
    ('Servidor', '≈ groupadd GRUPO', 'Si el grupo primario no existe.'),
    ('Servidor', '≈ useradd -c "Nombre" -g GRUPO -G GRUPOS -s /bin/bash -d /home/U -m U', 'Cuenta nueva.'),
    ('Servidor', '≈ usermod -a -G GRUPOS U', 'Cuenta existente con Actualizar = SI.'),
    ('Servidor', '≈ chown U:GRUPO /home/U ; chmod 0750 /home/U', 'Cuenta nueva.'),
    ('Servidor', '≈ usermod -a -G ssh_access U', 'Permitir SSH = SI y el grupo existe.'),
    ('Servidor', '≈ agrega U al final de la última línea AllowUsers de /etc/ssh/sshd_config (respaldo y validación con sshd -t)', 'Permitir SSH = SI, existe la línea y U no está.'),
    ('Servidor', 'systemctl reload sshd', 'Si se modificó AllowUsers.'),
]
SUDO = [
    ('Servidor', "grep -Eq '^[#@]includedir[[:space:]]+/etc/sudoers\\.d' /etc/sudoers", 'Sudo distinto de ninguno.'),
    ('Servidor', '≈ escribe /etc/sudoers.d/U (0440), validado con: visudo -cf <archivo>', 'Sudo distinto de ninguno.'),
    ('Servidor', '≈ rm -f /etc/sudoers.d/U', 'Sudo = ninguno y el archivo lo creó este proyecto.'),
]
CREAR_CLAVE = VERIFICAR + VERIFICAR_SSH + CUENTA + [
    ('Servidor', 'chpasswd   (recibe U:clave por entrada estándar)', 'Cuenta nueva.'),
    ('Servidor', 'chage -d 0 U', 'Cuenta nueva con Forzar cambio = SI.'),
] + SUDO
CREAR_LLAVE = VERIFICAR + VERIFICAR_SSH + [
    ('Contenedor', 'ssh-keygen -q -t rsa -b 4096 -N "" -C U@ansible -f <tmp>/U', 'El usuario no tiene llave, o Renovar = SI.'),
    ('Contenedor', 'generar_ppk (módulo del proyecto) -> U.ppk', 'Llave nueva, o le falta el .ppk.'),
    ('Contenedor', 'mv keys/U{,.pub,.ppk} keys/_anteriores/U_<fecha>*', 'Renovar = SI.'),
    ('Contenedor', 'mv <tmp>/U{,.pub,.ppk} /data/work/gestion_usuarios/keys/', 'Llave nueva o renovada.'),
] + CUENTA + [
    ('Servidor', '≈ usermod -L U', 'Cuenta nueva (queda sin contraseña).'),
    ('Servidor', 'chage -m 0 -M 99999 -I -1 -E -1 U', 'Cuenta nueva.'),
    ('Servidor', '≈ quita la llave anterior de ~U/.ssh/authorized_keys', 'Renovar = SI.'),
    ('Servidor', '≈ agrega la llave pública a ~U/.ssh/authorized_keys', 'Siempre.'),
] + SUDO
DESBLOQUEO = [
    ('Servidor', 'faillock --user U --reset ; pam_tally2 --user U --reset', 'Desbloquear = SI, el que exista.'),
    ('Servidor', 'chage -E -1 U', 'Desbloquear = SI y la cuenta está vencida.'),
]
CAMBIAR = VERIFICAR + [
    ('Servidor', 'chpasswd   (recibe U:clave por entrada estándar)', 'Siempre.'),
    ('Servidor', 'chage -m 0 -M 99999 -I -1 U', 'Nunca caduca = SI.'),
    ('Servidor', 'chage -d 0 U', 'Forzar cambio = SI.'),
] + DESBLOQUEO + [
    ('Servidor', 'getent shadow ; chage -l U', 'Siempre, para comprobar el cambio. Resultado de shadow oculto.'),
]
FORZAR = VERIFICAR + [
    ('Servidor', 'getent shadow', 'Siempre: comprueba que cada cuenta tenga clave y aplica las exclusiones. Resultado oculto.'),
    ('Servidor', 'chage -d 0 U', 'Siempre (no cambia la contraseña).'),
] + DESBLOQUEO + [
    ('Servidor', 'chage -l U', 'Siempre, para mostrar el estado final.'),
]
RELACION = [
    ('Servidor', 'getent passwd ; getent group ; sshd -t', 'Verificación, solo lectura (sshd -t solo si hay AllowUsers).'),
    ('Servidor', '≈ comenta "Defaults requiretty" en /etc/sudoers (validado con visudo)', 'Si existe esa línea.'),
    ('Servidor', '≈ agrega "#includedir /etc/sudoers.d" a /etc/sudoers (validado con visudo)', 'Si no está.'),
    ('Servidor', '≈ useradd -s /bin/bash -m -p "*" U ; usermod -a -G ssh_access U', 'Cuenta nueva; el grupo solo si existe.'),
    ('Servidor', '≈ escribe /etc/sudoers.d/U con: U ALL=(ALL) NOPASSWD: ALL (validado con visudo)', 'Siempre.'),
    ('Servidor', '≈ agrega las llaves públicas a ~U/.ssh/authorized_keys', 'Siempre (no borra otras llaves).'),
    ('Servidor', 'chage -m 0 -M 99999 -I -1 -E -1 U', 'Si la cuenta tiene caducidad.'),
    ('Servidor', '≈ agrega U al final de la última línea AllowUsers ; systemctl reload sshd', 'Si existe la línea y U no está.'),
]
AUDITORIA = [
    ('Servidor', 'lee /etc/passwd, /etc/shadow, /etc/group, /etc/sudoers, /etc/os-release', 'Siempre. No muestra los hashes.'),
    ('Servidor', 'lee ~U/.ssh/authorized_keys', 'Por cada cuenta.'),
    ('Servidor', 'uname -srv ; sudo -V ; sshd -T', 'Por servidor.'),
    ('Servidor', 'sudo -n -ll -U U   (o sudo -n -l -U U)', 'Por cada cuenta.'),
    ('Servidor', 'lastlog2 -u U   (o lastlog -u U)', 'Por cada cuenta.'),
    ('Contenedor', 'genera auditoria_usuarios_<fecha>.html y .csv en /data/work/gestion_usuarios/reportes/', 'Al final.'),
]
BLOQUEAR = [
    ('Servidor', 'getent passwd', 'Verificación, solo lectura.'),
    ('Servidor', '≈ rm -f /etc/sudoers.d/U', 'Bloquear o eliminar.'),
    ('Servidor', 'usermod -L -e 1970-01-02 U', 'Bloquear.'),
    ('Servidor', 'faillock --user U --reset ; pam_tally2 --user U --reset', 'Reactivar, el que exista.'),
    ('Servidor', 'getent shadow', 'Reactivar. Resultado oculto.'),
    ('Servidor', 'chage -E -1 U', 'Reactivar, si la cuenta está vencida.'),
    ('Servidor', 'usermod -U U', 'Reactivar, si tiene una clave real bloqueada.'),
    ('Servidor', '≈ mkdir -p -m 0700 /var/backups/usuarios_eliminados', 'Eliminar con respaldo.'),
    ('Servidor', 'tar -czf /var/backups/usuarios_eliminados/U_<fecha>.tar.gz -C /home U', 'Eliminar con respaldo.'),
    ('Servidor', '≈ userdel -r U', 'Eliminar.'),
]


# IDs en AWX (awxtest.coldecom.com). Si se recrea un objeto en AWX, actualice este dato.
AWX_ID = {
    'USUARIOS | 0 - Relación de confianza': 60,
    'USUARIOS | 1a - Crear con contraseña': 47,
    'USUARIOS | 1b - Crear con llave': 58,
    'USUARIOS | 2a - Cambiar contraseña': 48,
    'USUARIOS | 2b - Forzar cambio de contraseña': 59,
    'USUARIOS | 3 - Auditoría': 49,
    'USUARIOS | 4 - Bloquear o eliminar': 50,
    'USUARIOS | WF - Crear con contraseña': 54,
    'USUARIOS | WF - Crear con llave': 61,
    'USUARIOS | WF - Cambiar contraseña': 52,
    'USUARIOS | WF - Forzar cambio de contraseña': 63,
    'USUARIOS | WF - Bloquear o eliminar': 56,
}

QUE_HACE_WF = {
    'wf_crear_con_contrasena': 'Pide aprobación, crea cuentas con contraseña inicial y audita.',
    'wf_crear_con_llave': 'Pide aprobación, crea cuentas con llave SSH del almacén y audita.',
    'wf_cambiar_contrasena': 'Pide aprobación, asigna una contraseña nueva y audita.',
    'wf_forzar_cambio': 'Pide aprobación, obliga a cambiar la contraseña (también en bloque) y audita.',
    'wf_bloquear_eliminar': 'Pide aprobación, bloquea, reactiva o elimina y audita.',
}


def portada():
    s = [P('Arquitectura de gestion_usuarios', 'titulo'),
         P('Versión 1.0 · Gestión de usuarios Linux desde AWX: qué hace cada workflow, plantilla y encuesta, y qué comandos ejecuta.', 'sub'),
         P('Cómo funciona', 'h1'),
         P('Una persona llena una encuesta en AWX. Si la operación cambia algo, un aprobador la revisa. '
           'Después AWX ejecuta un playbook que valida todo primero y solo entonces aplica el cambio en los servidores.'),
         Spacer(1, 3),
         Flujo([('Encuesta', 'el operador\nindica qué hacer'), ('Workflow', 'ordena\nlos pasos'), ('Aprobación', 'admin revisa\n(máx. 4 horas)'),
                ('Plantilla', 'une playbook,\ninventario y llave'), ('Playbook y rol', 'validan\ny ejecutan'), ('Servidores', 'se aplica\nel cambio')]),
         P('Workflows: lo que normalmente se lanza', 'h1'),
         P('Cada workflow tiene tres nodos y su encuesta es la de la plantilla que protege, más el ticket. La plantilla 3 (auditoría) no tiene workflow porque no modifica nada, y la 0 (relación de confianza) tampoco.'),
         tabla(['ID', 'Workflow', 'Qué hace', 'Plantilla del nodo 2', 'Preguntas'],
               [[str(AWX_ID[w['name']]), w['name'], QUE_HACE_WF[k],
                 '%s (ID %d)' % (enc.ENCUESTAS[w['base']]['name'].split('| ')[1], AWX_ID[enc.ENCUESTAS[w['base']]['name']]),
                 str(len(enc.ENCUESTAS[w['base']]['spec']) + 1)]
                for k, w in enc.WORKFLOWS.items()], [0.06, 0.28, 0.31, 0.22, 0.13]),
         Spacer(1, 7),
         Flujo([('1. Aprobación', 'revisa ticket, objetivo\ny usuarios'), ('2. Plantilla', 'aplica el cambio\nsolicitado'), ('3. Auditoría', 'verifica cómo\nquedaron las cuentas')],
               pies={0: 'Rechazada o vencida:\ntermina sin cambios', 1: 'Si falla, no\ncorre la auditoría'}),
         P('El ticket y las demás respuestas se pasan a los nodos. La auditoría usa el mismo objetivo y sus valores por defecto.'),
         P('Plantillas', 'h1'),
         tabla(['ID', 'Plantilla', 'Playbook', 'Valores fijos', 'Preguntas'],
               [[str(AWX_ID[e['name']]), e['name'], 'AWX/gestion_usuarios/' + enc.PLANTILLAS[k]['playbook'],
                 ', '.join('%s=%s' % x for x in enc.PLANTILLAS[k]['fijas'].items()) or '-', str(len(e['spec']))]
                for k, e in enc.ENCUESTAS.items()], [0.06, 0.24, 0.32, 0.25, 0.13], ['c', 'c', 'c', 'm', 'c']),
         P('Los valores fijos van en las variables de la plantilla: la encuesta no los pregunta y quien lanza no los puede cambiar.', 'c'),
         Spacer(1, 4),
         P('Todas usan: proyecto <b>Playbooks-Corbeta</b>, inventario <b>Inventario 2026 - Gestion Usuarios</b>, entorno '
           '<b>Corbeta AWX-EE</b> y grupo de instancias <b>Container_Group_Corbeta</b>. Todas salvo la 0 usan la credencial '
           '<b>SSH Private Key - ECDSA</b>; la 0 se conecta con el usuario y la contraseña de su encuesta.'),
         PageBreak(),
         P('Qué pasa dentro de cada ejecución', 'h1'),
         P('Las plantillas que modifican siguen tres etapas. Si la etapa 1 o 2 falla, no se cambia ningún servidor.'),
         Flujo([('1. Validar', 'en el contenedor:\nrevisa la encuesta'), ('2. Verificar', 'en los servidores:\nsolo lectura'), ('3. Aplicar', 'en los servidores:\nhace los cambios')]),
         P('Un servidor que no responde se omite y queda indicado en el resultado del job. Si una verificación falla en un servidor, se detienen todos.'),
         P('Dónde queda cada cosa', 'h1'),
         tabla(['Qué', 'Dónde'], [
             ['Llaves de usuarios (privada, .pub y .ppk)', '/data/work/gestion_usuarios/keys/'],
             ['Llaves reemplazadas', '/data/work/gestion_usuarios/keys/_anteriores/'],
             ['Reportes de auditoría (HTML y CSV)', '/data/work/gestion_usuarios/reportes/'],
             ['Respaldos de home eliminados', '/var/backups/usuarios_eliminados/ en cada servidor'],
             ['Reglas sudo', '/etc/sudoers.d/&lt;usuario&gt; en cada servidor'],
             ['Catálogos de usuarios', 'vars/catalogos/ del proyecto'],
             ['Cuentas críticas, cuentas de servicio y grupos prohibidos', 'vars/comunes.yml del proyecto'],
             ['Llaves públicas de las cuentas de automatización', 'roles/usuarios_automatizacion/files/'],
         ], [0.5, 0.5]),
         P('Protecciones principales', 'h1'),
         tabla(['Regla', 'Cómo se aplica'], [
             ['Cuentas críticas', 'root, tux, adminso y demás administradoras no se crean, bloquean ni eliminan. Cambiar su clave exige CONFIRMAR y un objetivo concreto.'],
             ['Cuentas de servicio', 'Las cuentas con UID menor a 1000 no se modifican.'],
             ['Grupos privilegiados', 'wheel, sudo, root, docker y similares no se pueden asignar.'],
             ['Secretos', 'Las claves no aparecen en la salida del job.'],
             ['Sudo', 'Cada regla se valida con visudo antes de instalarse.'],
         ], [0.25, 0.75]),
         P('Cómo leer los comandos', 'h1'),
         P('<b>U</b> es el usuario y <b>GRUPO</b> su grupo. El signo <b>≈</b> indica que Ansible hace esa acción con un módulo y se muestra el comando equivalente. '
           'Todo corre con sudo en el servidor. En Solaris 11 algunos comandos cambian (por ejemplo, <font name="Mono" size="8">passwd -l</font> para bloquear). '
           'En las encuestas, <font color="#B3261E">*</font> marca los campos obligatorios.'),
         PageBreak()]
    return s


def pie(canvas, doc):
    canvas.saveState()
    canvas.setFont('Texto', 7.5)
    canvas.setFillColor(GRIS)
    canvas.drawString(16 * mm, 9 * mm, 'gestion_usuarios · Arquitectura v1.0')
    canvas.drawRightString(A4[0] - 16 * mm, 9 * mm, 'Página %d' % doc.page)
    canvas.restoreState()


def main():
    historia = portada()
    historia += seccion(
        'Opción 0 · Relación de confianza', 'Crea o completa las cuentas de automatización iacolcoauto y ansible_test: llaves, sudo sin '
        'contraseña, sin caducidad y acceso SSH. Es el prerrequisito de las demás opciones.',
        '00_relacion_confianza.yml', 'usuarios_automatizacion', 'Plantilla 0 (ID 60), sin workflow', '00_relacion_confianza', RELACION,
        'el objetivo no existe, falta el usuario o la contraseña de conexión, el servidor no es Linux, o sshd_config tiene errores.',
        nota('<b>Conexión.</b> Usa el usuario y la contraseña de la encuesta, no la credencial de AWX, para poder entrar donde ansible_test '
             'aún no existe. No elimina ni recrea cuentas: si ya existen, solo completa lo que falte. Las llaves públicas están en '
             'roles/usuarios_automatizacion/files/.'))
    historia += seccion(
        'Opción 1a · Crear con contraseña', 'Crea cuentas con contraseña inicial, sus grupos y su nivel de sudo.',
        '01_crear_usuarios.yml', 'usuarios_crear', 'Plantilla 1a (ID 47) y WF - Crear con contraseña (ID 54)', '01a_crear_con_contrasena', CREAR_CLAVE,
        'el objetivo no existe, un usuario es crítico o inválido, un grupo es privilegiado, la contraseña es corta, '
        'se quiere actualizar una cuenta de servicio, o sshd_config tiene errores (cuando hay que tocar AllowUsers).')
    historia += seccion(
        'Opción 1b · Crear con llave', 'Crea cuentas que entran solo con llave SSH, con sus grupos y su nivel de sudo.',
        '01_crear_usuarios.yml', 'usuarios_crear', 'Plantilla 1b (ID 58) y WF - Crear con llave (ID 61)', '01b_crear_con_llave', CREAR_LLAVE,
        'el objetivo no existe, un usuario es crítico o inválido, un grupo es privilegiado, no se puede escribir en la '
        'carpeta de llaves, se quiere actualizar una cuenta de servicio, o sshd_config tiene errores (cuando hay que tocar AllowUsers).',
        nota('<b>Llaves.</b> Todas viven en /data/work/gestion_usuarios/keys. Si el usuario ya tiene llave se reutiliza en cualquier servidor; '
             'solo se genera otra si no tiene o si se marca Renovar. Con sudo, la regla queda sin contraseña porque la cuenta no tiene clave.'))
    historia += seccion(
        'Opción 2a · Cambiar contraseña', 'Asigna una contraseña nueva a una o varias cuentas, con caducidad y desbloqueo opcionales.',
        '02_cambiar_contrasena.yml', 'usuarios_contrasena', 'Plantilla 2a (ID 48) y WF - Cambiar contraseña (ID 52)', '02a_cambiar_contrasena', CAMBIAR,
        'las claves no coinciden o son cortas, se pide "nunca caduca" y "forzar cambio" a la vez, o se intenta cambiar una cuenta crítica '
        'sin CONFIRMAR o con all.')
    historia += seccion(
        'Opción 2b · Forzar cambio de contraseña', 'Conserva la contraseña actual y obliga a cambiarla en el próximo ingreso. Se puede aplicar a una lista, a un catálogo o a todas las cuentas UID ≥ 1000.',
        '02_cambiar_contrasena.yml', 'usuarios_contrasena', 'Plantilla 2b (ID 59) y WF - Forzar cambio de contraseña (ID 63)', '02b_forzar_cambio', FORZAR,
        'la lista incluye una cuenta crítica, o una cuenta de la lista no tiene contraseña (solo llave o bloqueada): '
        'si se le forzara el cambio no podría entrar.',
        nota('<b>En bloque</b> (catálogo o todos UID ≥ 1000) se omiten, sin detener el job: cuentas críticas, cuentas de servicio '
             '(lista cuentas_servicio en vars/comunes.yml), shells no interactivos y cuentas sin contraseña. Antes de lanzarlo, '
             'ejecute la auditoría: la columna "Se le forzaría el cambio" muestra exactamente a quiénes se aplicaría.'))
    historia += seccion(
        'Opción 3 · Auditoría', 'Revisa cuentas, contraseñas, llaves, último acceso y sudo. No modifica los servidores.',
        '03_auditoria_usuarios.yml', 'usuarios_auditoria', 'Plantilla 3 (ID 49) y último nodo de los 5 workflows', '03_auditoria_usuarios', AUDITORIA,
        'el objetivo no existe o no se puede crear la carpeta de reportes.')
    historia += seccion(
        'Opción 4 · Bloquear, reactivar o eliminar', 'Bloquea una cuenta de forma reversible, la reactiva o la elimina con respaldo.',
        '04_bloquear_eliminar_usuarios.yml', 'usuarios_eliminar', 'Plantilla 4 (ID 50) y WF - Bloquear o eliminar (ID 56)', '04_bloquear_eliminar_usuarios', BLOQUEAR,
        'un usuario es crítico, falta CONFIRMAR para eliminar, o el home está fuera de /home o /export/home.',
        nota('<b>Reactivar no restaura sudo.</b> Si la cuenta lo tenía, use la opción 1a o 1b con "Actualizar usuarios que ya existen".'))
    historia.pop()

    doc = SimpleDocTemplate(SALIDA, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=15 * mm, bottomMargin=16 * mm,
                            title='Arquitectura de gestion_usuarios', author='gestion_usuarios', subject='Workflows, plantillas, encuestas y comandos')
    doc.build(historia, onFirstPage=pie, onLaterPages=pie)
    print('Generado:', SALIDA)


if __name__ == '__main__':
    main()
