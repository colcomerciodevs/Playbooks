#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fuente única de las encuestas de AWX.
Genera awx/encuestas/*.json (formato survey_spec de la API de AWX): una por
plantilla (01..04) y una por workflow con aprobación (wf_*).
El PDF de arquitectura toma las preguntas de aquí: después de cambiar una encuesta,
regenérelo con  python3 -B docs/fuente/generar_arquitectura.py

Uso:  python3 awx/generar_encuestas.py
"""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
SINO = ['SI', 'NO']


def texto_awx(desc):
    """AWX muestra la ayuda en un solo párrafo (ignora los saltos de línea).
    Convierte cada línea '• valor → efecto' en '[valor] efecto' y las une con espacios."""
    partes = []
    for linea in desc.split('\n'):
        linea = linea.strip()
        if linea.startswith('• '):
            linea = linea[2:]
        if ' → ' in linea:
            valor, efecto = linea.split(' → ', 1)
            linea = '[%s] %s' % (valor, efecto[:1].upper() + efecto[1:])
        partes.append(linea)
    return ' '.join(x for x in partes if x)


def q(var, nombre, desc, tipo='text', req=False, default='', choices=None, mn=0, mx=1024):
    d = {'question_name': nombre, 'question_description': texto_awx(desc), 'required': req, 'type': tipo,
         'variable': var, 'min': mn, 'max': mx, 'default': default, 'choices': choices or [],
         'new_question': True}
    if tipo in ('integer', 'float'):
        d['default'] = default if default != '' else None
    return d


CATALOGOS = ['usuarios_generales', 'admins_linux', 'cuentas_de_servicio',
             'soporte_zona_norte', 'soporte_zona_centro']

OBJETIVO = q('objetivo', 'Servidores o grupo del inventario',
             'Grupo, servidor o patrón del inventario. No se permite localhost.\n'
             '• Ejemplos: GEOPOS · PPU · srv1,srv2 · GEOPOS:!srv1',
             req=True, mn=1)

ENCUESTAS = {
    '01_crear_usuarios': {
        'name': 'USUARIOS | 1 - Crear usuarios',
        'description': 'Alta de usuarios con contraseña o con llave SSH, grupos y sudo.',
        'spec': [
            OBJETIVO,
            q('crear_metodo_acceso', 'Método de acceso',
              '• contrasena → la cuenta entra con la contraseña inicial.\n'
              '• llave → entra solo con llave SSH (sin contraseña).',
              'multiplechoice', True, 'contrasena', ['contrasena', 'llave']),
            q('crear_origen', 'Origen de la lista de usuarios',
              '• encuesta → escriba los usuarios en el campo de abajo.\n'
              '• catalogo → se toman de un archivo de vars/catalogos/.',
              'multiplechoice', True, 'encuesta', ['encuesta', 'catalogo']),
            q('crear_usuarios_texto', 'Usuarios (si origen = encuesta)',
              'Solo si origen = encuesta. Una línea por usuario: usuario;Nombre completo;grupo (grupo opcional).\n'
              '• Ejemplo: jperez;Juan Pérez;soporte',
              'textarea', mx=20000),
            q('crear_catalogo', 'Catálogo (si origen = catalogo)',
              'Solo si origen = catalogo.\n'
              '• ⚠ El catálogo manda sobre esta encuesta: admins_linux da sudo COMPLETO sin contraseña.',
              'multiplechoice', False, '', CATALOGOS),
            q('crear_grupos_secundarios', 'Grupos secundarios',
              'Separados por coma. Solo se agregan si ya existen en el servidor.\n'
              '• No se permiten grupos privilegiados (wheel, sudo, root, docker…).'),
            q('crear_contrasena_inicial', 'Contraseña inicial (método contrasena)',
              'Solo con método contrasena. Mínimo 8 caracteres. Se asigna únicamente a cuentas nuevas.',
              'password', mx=128),
            q('crear_forzar_cambio', 'Forzar cambio de contraseña en el primer ingreso',
              'SI → el usuario debe cambiar la contraseña en su primer ingreso (recomendado).',
              'multiplechoice', True, 'SI', SINO),
            q('crear_llave_origen', 'Origen de la llave (método llave)',
              'Solo con método llave.\n'
              '• keys → reutiliza la llave guardada; si no tiene, crea una.\n'
              '• encuesta → usa la llave pegada abajo.',
              'multiplechoice', False, 'keys', ['keys', 'encuesta']),
            q('crear_llaves_texto', 'Llaves públicas (origen de llave = encuesta)',
              'Solo si origen de la llave = encuesta. Una línea por usuario.\n'
              '• Ejemplo: jperez;ssh-rsa AAAA... comentario',
              'textarea', mx=40000),
            q('crear_renovar_llave', '⚠ RENOVAR LLAVE (opción crítica)',
              'Deje NO salvo pérdida o robo de la llave.\n'
              '• SI → crea una llave nueva, archiva la anterior y la reemplaza solo en los servidores de este objetivo.',
              'multiplechoice', True, 'NO', SINO),
            q('crear_sudo_nivel', 'Nivel de sudo',
              '• ninguno → sin sudo.\n'
              '• completo → puede ejecutar todo como root.\n'
              '• limitado → solo los comandos indicados abajo.',
              'multiplechoice', True, 'ninguno', ['ninguno', 'completo', 'limitado']),
            q('crear_sudo_nopasswd', 'sudo sin contraseña (NOPASSWD)',
              'SI → sudo no pide contraseña.\n'
              '• Con método llave se aplica siempre (la cuenta no tiene contraseña).',
              'multiplechoice', True, 'NO', SINO),
            q('crear_sudo_comandos', 'Comandos sudo permitidos (nivel limitado)',
              'Solo con sudo limitado. Un comando por línea, con ruta completa.\n'
              '• Ejemplo: /usr/bin/systemctl restart httpd',
              'textarea', mx=20000),
            q('crear_actualizar_existentes', 'Actualizar usuarios que ya existen',
              '• NO → las cuentas que ya existen se omiten.\n'
              '• SI → se les agregan grupos, llave y sudo (no cambia su contraseña).',
              'multiplechoice', True, 'NO', SINO),
        ],
    },
    '02_cambiar_contrasena': {
        'name': 'USUARIOS | 2 - Cambiar contraseña',
        'description': 'Cambio de contraseña con política "nunca caduca" opcional (ej. root).',
        'spec': [
            OBJETIVO,
            q('contrasena_accion', 'Acción',
              '• cambiar → asigna la contraseña nueva.\n'
              '• solo_forzar_cambio → no toca la contraseña; obliga a cambiarla en el próximo ingreso.',
              'multiplechoice', True, 'cambiar', ['cambiar', 'solo_forzar_cambio']),
            q('contrasena_origen', 'Usuarios a incluir',
              '• lista → los usuarios escritos abajo.\n'
              '• catalogo → los del catálogo elegido.\n'
              '• todos_uid_1000 → todas las cuentas con UID ≥ 1000 de cada servidor.\n'
              'En bloque solo se permite solo_forzar_cambio. Revise antes la auditoría.',
              'multiplechoice', True, 'lista', ['lista', 'catalogo', 'todos_uid_1000']),
            q('contrasena_usuarios', 'Usuario(s) (si usuarios a incluir = lista)',
              'Solo si usuarios a incluir = lista. Separados por coma.\n'
              '• Ejemplo: jperez,soporte1'),
            q('contrasena_catalogo', 'Catálogo (si usuarios a incluir = catalogo)',
              'Solo si usuarios a incluir = catalogo.',
              'multiplechoice', False, '', CATALOGOS),
            q('contrasena_confirmar_critica', 'Confirmación para cuenta crítica',
              'Solo para root, tux, adminso y otras cuentas administradoras: escriba CONFIRMAR.\n'
              '• No se permite con objetivo all.'),
            q('contrasena_nueva', 'Nueva contraseña (acción cambiar)',
              'Solo con acción cambiar. Mínimo 8 caracteres. No aparece en la salida del job.',
              'password', mx=128),
            q('contrasena_confirmacion', 'Confirmar contraseña (acción cambiar)',
              'Repita la contraseña nueva.',
              'password', mx=128),
            q('contrasena_nunca_caduca', 'Contraseña sin caducidad (nunca expira)',
              '• SI → la contraseña no expira (para cuentas críticas). Requiere Forzar cambio = NO.\n'
              '• NO → conserva la política actual.',
              'multiplechoice', True, 'NO', SINO),
            q('contrasena_forzar_cambio', 'Forzar cambio en el próximo inicio de sesión',
              '• SI → debe cambiarla en el próximo ingreso (recomendado en cuentas personales).\n'
              '• Debe ser NO en cuentas críticas o con «sin caducidad».',
              'multiplechoice', True, 'SI', SINO),
            q('contrasena_desbloquear', 'Desbloquear la cuenta',
              'SI → reinicia intentos fallidos y quita una expiración vencida.\n'
              '• También revierte un bloqueo hecho con la opción 4.',
              'multiplechoice', True, 'NO', SINO),
        ],
    },
    '03_auditoria_usuarios': {
        'name': 'USUARIOS | 3 - Auditoría',
        'description': 'Inventario de cuentas UID >= 1000, permisos sudo (completo/limitado y comandos) y hallazgos.',
        'spec': [
            OBJETIVO,
            q('auditoria_uid_minimo', 'UID mínimo a auditar',
              'Se auditan las cuentas desde este UID. Por debajo suelen ser cuentas del sistema.',
              'integer', True, 1000, mn=0, mx=65535),
            q('auditoria_dias_inactividad', 'Días sin ingreso para reportar una cuenta como inactiva (solo informe)',
              'Solo para el reporte: no bloquea ni cambia nada.\n'
              '• Las cuentas sin ingresar en más de estos días aparecen como CUENTA_INACTIVA.',
              'integer', True, 90, mn=1, mx=3650),
        ],
    },
    '04_bloquear_eliminar_usuarios': {
        'name': 'USUARIOS | 4 - Bloquear o eliminar',
        'description': 'Bloqueo, reactivación o eliminación de cuentas, con respaldo del home.',
        'spec': [
            OBJETIVO,
            q('eliminar_usuarios', 'Usuario(s)', 'Separados por coma. No se aceptan cuentas críticas.', req=True, mn=1),
            q('eliminar_accion', 'Acción',
              '• bloquear → impide el ingreso y conserva el home (reversible).\n'
              '• reactivar → revierte el bloqueo.\n'
              '• eliminar → borra la cuenta y su home.',
              'multiplechoice', True, 'bloquear', ['bloquear', 'reactivar', 'eliminar']),
            q('eliminar_respaldar_home', 'Respaldar home antes de eliminar',
              'SI → antes de eliminar, comprime el home en /var/backups/usuarios_eliminados/.',
              'multiplechoice', True, 'SI', SINO),
            q('eliminar_confirmacion', 'Confirmación (solo para eliminar)', 'Solo para eliminar: escriba CONFIRMAR.'),
        ],
    },
}


# ---------------------------------------------------------------------------
# Workflows con aprobación: su encuesta es la de la plantilla que protegen,
# precedida por el ticket/justificación que verá quien aprueba.
# ---------------------------------------------------------------------------
TICKET = q('ticket_cambio', 'Ticket o justificación',
           'Número de ticket o RFC y motivo del cambio. Es lo primero que revisa quien aprueba.',
           req=True, mn=3, mx=300)

WORKFLOWS = {
    'wf_cambio_contrasena_aprobacion': {
        'name': 'USUARIOS | WF - Cambio de contraseña',
        'description': 'Aprobación -> cambio de contraseña -> auditoría de verificación.',
        'base': '02_cambiar_contrasena',
        'aprobacion': 'Aprobacion',
        'plantilla': 'USUARIOS | 2 - Cambiar contraseña',
    },
    'wf_crear_usuarios_aprobacion': {
        'name': 'USUARIOS | WF - Crear usuarios',
        'description': 'Aprobación -> creación de usuarios -> auditoría de verificación.',
        'base': '01_crear_usuarios',
        'aprobacion': 'Aprobacion',
        'plantilla': 'USUARIOS | 1 - Crear usuarios',
    },
    'wf_bloquear_eliminar_aprobacion': {
        'name': 'USUARIOS | WF - Bloquear o eliminar',
        'description': 'Aprobación -> bloqueo o eliminación -> auditoría de verificación.',
        'base': '04_bloquear_eliminar_usuarios',
        'aprobacion': 'Aprobacion',
        'plantilla': 'USUARIOS | 4 - Bloquear o eliminar',
    },
}
AUDITORIA = 'USUARIOS | 3 - Auditoría'
APROBACION_TIMEOUT_SEG = 4 * 3600   # 4 horas


def encuesta_workflow(clave):
    wf = WORKFLOWS[clave]
    return {'name': wf['name'], 'description': wf['description'],
            'spec': [TICKET] + ENCUESTAS[wf['base']]['spec']}


def main():
    os.makedirs(os.path.join(BASE, 'encuestas'), exist_ok=True)
    for clave in WORKFLOWS:
        with open(os.path.join(BASE, 'encuestas', clave + '.json'), 'w', encoding='utf-8') as f:
            json.dump(encuesta_workflow(clave), f, ensure_ascii=False, indent=2)
            f.write('\n')
    for archivo, enc in ENCUESTAS.items():
        with open(os.path.join(BASE, 'encuestas', archivo + '.json'), 'w', encoding='utf-8') as f:
            json.dump(enc, f, ensure_ascii=False, indent=2)
            f.write('\n')
    print('Encuestas generadas:', ', '.join(list(ENCUESTAS) + list(WORKFLOWS)))


if __name__ == '__main__':
    main()
