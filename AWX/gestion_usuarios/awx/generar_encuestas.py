#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fuente única de las encuestas de AWX.
Genera awx/encuestas/*.json (formato survey_spec de la API de AWX): una por
plantilla (01..04) y una por workflow con aprobación (wf_*).
El manual PDF toma las preguntas de aquí: después de cambiar una encuesta,
regenérelo con  python3 docs/fuente/generar_manual.py

Uso:  python3 awx/generar_encuestas.py
"""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
SINO = ['SI', 'NO']


def q(var, nombre, desc, tipo='text', req=False, default='', choices=None, mn=0, mx=1024):
    d = {'question_name': nombre, 'question_description': desc, 'required': req, 'type': tipo,
         'variable': var, 'min': mn, 'max': mx, 'default': default, 'choices': choices or [],
         'new_question': True}
    if tipo in ('integer', 'float'):
        d['default'] = default if default != '' else None
    return d


OBJETIVO = q('objetivo', 'Servidores o grupo del inventario',
             'Grupo (ej. GEOPOS, PPU, OCI_PEOPLE_PRD), servidor, o patrón Ansible: grupo1:grupo2, grupo:!servidor, srv1,srv2.',
             req=True, mn=1)

ENCUESTAS = {
    '01_crear_usuarios': {
        'name': 'USUARIOS | 1 - Crear usuarios',
        'description': 'Alta de usuarios con contraseña o con llave SSH, grupos y sudo.',
        'spec': [
            OBJETIVO,
            q('crear_metodo_acceso', 'Método de acceso',
              'contrasena: cuenta con contraseña inicial. llave: solo acceso con llave SSH (la contraseña queda bloqueada).',
              'multiplechoice', True, 'contrasena', ['contrasena', 'llave']),
            q('crear_origen', 'Origen de la lista de usuarios',
              'encuesta: los usuarios se escriben abajo. catalogo: se toman de un archivo de vars/catalogos/ del proyecto.',
              'multiplechoice', True, 'encuesta', ['encuesta', 'catalogo']),
            q('crear_usuarios_texto', 'Usuarios (si origen = encuesta)',
              'Una línea por usuario:  usuario;Nombre completo;grupo(opcional)\nEj: jperez;Juan Pérez;soporte',
              'textarea', mx=20000),
            q('crear_catalogo', 'Catálogo (si origen = catalogo)',
              'Archivo de vars/catalogos/. El catálogo manda sobre esta encuesta: usuarios_llave_admin_linux otorga sudo COMPLETO sin contraseña.',
              'multiplechoice', False, '',
              ['usuarios_zona_norte', 'usuarios_zona_centro', 'usuarios_individuales',
               'usuarios_llave_admin_linux', 'usuarios_llave_servicio']),
            q('crear_grupos_secundarios', 'Grupos secundarios',
              'Separados por coma. Solo se agregan los que ya existen en el servidor. No se permiten grupos privilegiados (wheel, sudo, root, docker...).'),
            q('crear_contrasena_inicial', 'Contraseña inicial (método contrasena)',
              'Obligatoria con método contrasena. Solo se asigna a cuentas nuevas. AWX la guarda cifrada.',
              'password', mx=128),
            q('crear_forzar_cambio', 'Forzar cambio de contraseña en el primer ingreso',
              'Recomendado SI para cuentas personales.', 'multiplechoice', True, 'SI', SINO),
            q('crear_llave_origen', 'Origen de la llave (método llave)',
              'keys: usa la llave guardada del usuario; si no tiene, genera una nueva y la guarda. encuesta: usa la llave pública pegada abajo.',
              'multiplechoice', False, 'keys', ['keys', 'encuesta']),
            q('crear_llaves_texto', 'Llaves públicas (origen de llave = encuesta)',
              'Una línea por usuario:  usuario;ssh-rsa AAAA... comentario', 'textarea', mx=40000),
            q('crear_renovar_llave', '⚠ RENOVAR LLAVE (opción crítica)',
              'SI genera una llave NUEVA aunque el usuario ya tenga una. La anterior se archiva y se retira de los servidores del objetivo. En servidores NO incluidos en el objetivo el usuario seguirá entrando solo con la llave anterior. Deje NO salvo pérdida o compromiso de la llave.',
              'multiplechoice', True, 'NO', SINO),
            q('crear_sudo_nivel', 'Nivel de sudo',
              'ninguno | completo (ALL) | limitado (solo los comandos indicados abajo).',
              'multiplechoice', True, 'ninguno', ['ninguno', 'completo', 'limitado']),
            q('crear_sudo_nopasswd', 'sudo sin contraseña (NOPASSWD)',
              'Con método llave se aplica SI automáticamente (la cuenta no tiene contraseña).',
              'multiplechoice', True, 'NO', SINO),
            q('crear_sudo_comandos', 'Comandos sudo permitidos (nivel limitado)',
              'Un comando por línea, con ruta absoluta. Ej:\n/usr/bin/systemctl restart httpd\n/usr/bin/tail -f /var/log/messages',
              'textarea', mx=20000),
            q('crear_actualizar_existentes', 'Actualizar usuarios que ya existen',
              'NO: se omiten. SI: se les agregan grupos, llave y regla sudo (no se cambia su contraseña, home ni shell).',
              'multiplechoice', True, 'NO', SINO),
        ],
    },
    '02_cambiar_contrasena': {
        'name': 'USUARIOS | 2 - Cambiar contraseña',
        'description': 'Cambio de contraseña con política "nunca caduca" opcional (ej. root).',
        'spec': [
            OBJETIVO,
            q('contrasena_usuarios', 'Usuario(s)', 'Uno o varios separados por coma. Ej: jperez  o  jperez,soporte1',
              req=True, mn=1),
            q('contrasena_confirmar_critica', 'Confirmación para cuenta crítica',
              'Solo para root, tux, adminso y otras cuentas administradoras: escriba CONFIRMAR. No se permite con objetivo all.'),
            q('contrasena_nueva', 'Nueva contraseña', 'AWX la guarda cifrada y no aparece en la salida del job.',
              'password', True, mn=8, mx=128),
            q('contrasena_confirmacion', 'Confirmar contraseña', 'Debe coincidir con la anterior.',
              'password', True, mn=8, mx=128),
            q('contrasena_nunca_caduca', 'Contraseña sin caducidad (nunca expira)',
              'SI: chage -m 0 -M 99999 -I -1. Para cuentas críticas que el hardening haría caducar; requiere "Forzar cambio" en NO. NO: conserva la política actual.',
              'multiplechoice', True, 'NO', SINO),
            q('contrasena_forzar_cambio', 'Forzar cambio en el próximo inicio de sesión',
              'Recomendado SI para cuentas personales. Excluyente con "sin caducidad". En cuentas críticas debe ser NO.',
              'multiplechoice', True, 'SI', SINO),
            q('contrasena_desbloquear', 'Desbloquear la cuenta',
              'Reinicia intentos fallidos (faillock/pam_tally2) y quita una expiración de cuenta ya vencida. También revierte un bloqueo hecho con la opción 4.',
              'multiplechoice', True, 'NO', SINO),
        ],
    },
    '03_auditoria_usuarios': {
        'name': 'USUARIOS | 3 - Auditoría',
        'description': 'Inventario de cuentas UID >= 1000, permisos sudo (completo/limitado y comandos) y hallazgos.',
        'spec': [
            OBJETIVO,
            q('auditoria_uid_minimo', 'UID mínimo a auditar', 'Por debajo de este UID son cuentas de servicio.',
              'integer', True, 1000, mn=0, mx=65535),
            q('auditoria_dias_inactividad', 'Días sin ingreso para marcar cuenta inactiva', '',
              'integer', True, 90, mn=1, mx=3650),
            q('auditoria_detalle_salida', 'Detalle en la salida del job',
              'resumido: tabla por servidor. completo: además los hallazgos de cada usuario.',
              'multiplechoice', True, 'resumido', ['resumido', 'completo']),
        ],
    },
    '04_bloquear_eliminar_usuarios': {
        'name': 'USUARIOS | 4 - Bloquear o eliminar',
        'description': 'Bloqueo, reactivación o eliminación de cuentas, con respaldo del home.',
        'spec': [
            OBJETIVO,
            q('eliminar_usuarios', 'Usuario(s)', 'Uno o varios separados por coma.', req=True, mn=1),
            q('eliminar_accion', 'Acción',
              'bloquear: bloquea clave y expira la cuenta (conserva el home). reactivar: revierte el bloqueo. eliminar: borra cuenta y home.',
              'multiplechoice', True, 'bloquear', ['bloquear', 'reactivar', 'eliminar']),
            q('eliminar_respaldar_home', 'Respaldar home antes de eliminar',
              'Se guarda en /var/backups/usuarios_eliminados/ del servidor.', 'multiplechoice', True, 'SI', SINO),
            q('eliminar_confirmacion', 'Confirmación (solo para eliminar)', 'Escriba CONFIRMAR para eliminar.'),
        ],
    },
}


# ---------------------------------------------------------------------------
# Workflows con aprobación: su encuesta es la de la plantilla que protegen,
# precedida por el ticket/justificación que verá quien aprueba.
# ---------------------------------------------------------------------------
TICKET = q('ticket_cambio', 'Ticket o justificación',
           'Número de ticket / RFC y motivo del cambio. Es lo primero que revisa quien aprueba.',
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
