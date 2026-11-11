#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fuente única de las encuestas de AWX.
Genera awx/encuestas/*.json (formato survey_spec de la API de AWX): una por
plantilla y una por workflow con aprobación (wf_*), más plantillas.json con el
playbook y las variables fijas (extra vars) de cada plantilla.
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


CATALOGOS = ['admins_linux', 'cuentas_de_servicio', 'soporte_zona_norte', 'soporte_zona_centro']

# ---------------------------------------------------------------------------
# Preguntas (cada una se define una vez y se reutiliza en las encuestas)
# ---------------------------------------------------------------------------
OBJETIVO = q('objetivo', 'Servidores o grupo del inventario',
             'Grupo, servidor o patrón del inventario. No se permite localhost.\n'
             '• Ejemplos: GEOPOS · PPU · srv1,srv2 · GEOPOS:!srv1',
             req=True, mn=1)

C_ORIGEN = q('crear_origen', 'Origen de la lista de usuarios',
             '• encuesta → escriba los usuarios en el campo de abajo.\n'
             '• catalogo → se toman de un archivo de vars/catalogos/.',
             'multiplechoice', True, 'encuesta', ['encuesta', 'catalogo'])
C_USUARIOS = q('crear_usuarios_texto', 'Usuarios (si origen = encuesta)',
               'Una línea por usuario: usuario;Nombre completo;grupo (grupo opcional).\n'
               '• Ejemplo: jperez;Juan Pérez;soporte',
               'textarea', mx=20000)
C_CATALOGO = q('crear_catalogo', 'Catálogo (si origen = catalogo) · el catálogo define sudo y grupos',
               '⚠ El catálogo manda sobre esta encuesta: admins_linux da sudo COMPLETO sin contraseña.',
               'multiplechoice', False, '', CATALOGOS)
C_GRUPOS = q('crear_grupos_secundarios', 'Grupos secundarios',
             'Separados por coma. Solo se agregan si ya existen en el servidor.\n'
             '• No se permiten grupos privilegiados (wheel, sudo, root, docker…).')
C_SSH = q('crear_permitir_ssh', 'Permitir acceso SSH',
          '• SI → lo agrega al grupo ssh_access (si existe en el servidor) y al final de la línea AllowUsers de sshd_config (si existe esa línea). Lo que no exista se ignora.\n'
          '• NO → no toca el acceso SSH; si el servidor lo restringe, la cuenta no podrá entrar por SSH.',
          'multiplechoice', True, 'SI', SINO)
C_CLAVE = q('crear_contrasena_inicial', 'Contraseña inicial',
            'Mínimo 8 caracteres. Se asigna únicamente a cuentas nuevas. No aparece en la salida del job.',
            'password', True, mn=8, mx=128)
C_FORZAR = q('crear_forzar_cambio', 'Forzar cambio de contraseña en el primer ingreso',
             'SI → el usuario debe cambiar la contraseña en su primer ingreso (recomendado).',
             'multiplechoice', True, 'SI', SINO)
C_RENOVAR = q('crear_renovar_llave', '⚠ RENOVAR LLAVE (opción crítica)',
              'Deje NO salvo pérdida o robo de la llave. Si el usuario ya tiene llave, se reutiliza.\n'
              '• SI → crea una llave nueva, archiva la anterior y la reemplaza solo en los servidores de este objetivo.',
              'multiplechoice', True, 'NO', SINO)
C_SUDO = q('crear_sudo_nivel', 'Nivel de sudo',
           '• ninguno → sin sudo.\n'
           '• completo → puede ejecutar todo como root.\n'
           '• limitado → solo los comandos indicados abajo.',
           'multiplechoice', True, 'ninguno', ['ninguno', 'completo', 'limitado'])
C_SUDO_COMANDOS = q('crear_sudo_comandos', 'Comandos sudo permitidos (si nivel = limitado)',
                    'Un comando por línea, con ruta completa.\n'
                    '• Ejemplo: /usr/bin/systemctl restart httpd',
                    'textarea', mx=20000)
C_NOPASSWD = q('crear_sudo_nopasswd', 'sudo sin contraseña (NOPASSWD)',
               'SI → sudo no pide contraseña.',
               'multiplechoice', True, 'NO', SINO)
C_ACTUALIZAR = q('crear_actualizar_existentes', 'Actualizar usuarios que ya existen',
                 '• NO → las cuentas que ya existen se omiten.\n'
                 '• SI → se les agregan grupos, llave y sudo (no cambia su contraseña).',
                 'multiplechoice', True, 'NO', SINO)

P_USUARIOS = q('contrasena_usuarios', 'Usuario(s)',
               'Uno o varios separados por coma.\n'
               '• Ejemplo: jperez,soporte1',
               req=True, mn=1)
P_CRITICA = q('contrasena_confirmar_critica', 'Confirmación para cuenta crítica',
              'Solo para root, tux, adminso y otras cuentas administradoras: escriba CONFIRMAR.\n'
              '• No se permite con objetivo all.')
P_NUEVA = q('contrasena_nueva', 'Nueva contraseña',
            'Mínimo 8 caracteres. No aparece en la salida del job.',
            'password', True, mn=8, mx=128)
P_CONFIRMACION = q('contrasena_confirmacion', 'Confirmar contraseña',
                   'Repita la contraseña nueva.',
                   'password', True, mn=8, mx=128)
P_NUNCA = q('contrasena_nunca_caduca', 'Contraseña sin caducidad (no se aplica a cuentas críticas)',
            '• SI → la contraseña no expira. Requiere Forzar cambio = NO.\n'
            '• NO → conserva la política actual.\n'
            'No se aplica a cuentas críticas (root, tux, adminso…): conservan su configuración actual.',
            'multiplechoice', True, 'NO', SINO)
P_FORZAR = q('contrasena_forzar_cambio', 'Forzar cambio en el próximo inicio de sesión (no se aplica a cuentas críticas)',
             '• SI → debe cambiarla en el próximo ingreso (recomendado en cuentas personales).\n'
             '• Debe ser NO si marcó «sin caducidad».\n'
             'No se aplica a cuentas críticas (root, tux, adminso…): conservan su configuración actual.',
             'multiplechoice', True, 'SI', SINO)
P_DESBLOQUEAR = q('contrasena_desbloquear', 'Desbloquear la cuenta',
                  'SI → reinicia intentos fallidos y quita una expiración vencida.\n'
                  '• También revierte un bloqueo hecho con la opción 4.',
                  'multiplechoice', True, 'NO', SINO)
F_ORIGEN = q('contrasena_origen', 'Usuarios a incluir',
             '• lista → los usuarios escritos abajo.\n'
             '• catalogo → los del catálogo elegido.\n'
             '• todos_uid_1000 → todas las cuentas con UID ≥ 1000 de cada servidor.\n'
             'En bloque se excluyen cuentas críticas, de servicio y sin contraseña. Revise antes la auditoría.',
             'multiplechoice', True, 'lista', ['lista', 'catalogo', 'todos_uid_1000'])
F_USUARIOS = q('contrasena_usuarios', 'Usuario(s) (si usuarios a incluir = lista)',
               'Uno o varios separados por coma. No se aceptan cuentas críticas.\n'
               '• Ejemplo: jperez,soporte1')
F_CATALOGO = q('contrasena_catalogo', 'Catálogo (si usuarios a incluir = catalogo)',
               'Archivo de vars/catalogos/ con los usuarios a incluir.',
               'multiplechoice', False, '', CATALOGOS)

# ---------------------------------------------------------------------------
# Plantillas: encuesta, playbook y variables fijas (extra vars de la plantilla en AWX)
# ---------------------------------------------------------------------------
ENCUESTAS = {
    '00_relacion_confianza': {
        'name': 'USUARIOS | 0 - Relación de confianza',
        'description': 'Crea o completa las cuentas de automatización (iacolcoauto, ansible_test). Prerrequisito de las demás opciones.',
        'spec': [
            OBJETIVO,
            q('relacion_usuario', 'Usuario de conexión',
              'Usuario con el que se entra hoy a los servidores (por ejemplo tux o adminso). Debe poder usar sudo.',
              req=True, mn=1, mx=32),
            q('relacion_clave', 'Contraseña de conexión',
              'Contraseña SSH de ese usuario. No aparece en la salida del job.',
              'password', True, mn=1, mx=128),
            q('relacion_clave_sudo', 'Contraseña de sudo (si es distinta)',
              'Déjela vacía si sudo usa la misma contraseña de conexión.',
              'password', mx=128),
        ],
    },
    '01a_crear_con_contrasena': {
        'name': 'USUARIOS | 1a - Crear con contraseña',
        'description': 'Alta de usuarios con contraseña inicial, grupos y sudo.',
        'spec': [OBJETIVO, C_ORIGEN, C_USUARIOS, C_CATALOGO, C_GRUPOS, C_SSH, C_CLAVE, C_FORZAR,
                 C_SUDO, C_SUDO_COMANDOS, C_NOPASSWD, C_ACTUALIZAR],
    },
    '01b_crear_con_llave': {
        'name': 'USUARIOS | 1b - Crear con llave',
        'description': 'Alta de usuarios con llave SSH del almacén (se reutiliza o se crea), grupos y sudo.',
        'spec': [OBJETIVO, C_ORIGEN, C_USUARIOS, C_CATALOGO, C_GRUPOS, C_SSH, C_RENOVAR,
                 C_SUDO, C_SUDO_COMANDOS, C_ACTUALIZAR],
    },
    '02a_cambiar_contrasena': {
        'name': 'USUARIOS | 2a - Cambiar contraseña',
        'description': 'Asigna una contraseña nueva, con caducidad y desbloqueo opcionales.',
        'spec': [OBJETIVO, P_USUARIOS, P_CRITICA, P_NUEVA, P_CONFIRMACION, P_NUNCA, P_FORZAR, P_DESBLOQUEAR],
    },
    '02b_forzar_cambio': {
        'name': 'USUARIOS | 2b - Forzar cambio de contraseña',
        'description': 'Conserva la contraseña actual y obliga a cambiarla en el próximo ingreso. Admite operación en bloque.',
        'spec': [OBJETIVO, F_ORIGEN, F_USUARIOS, F_CATALOGO, P_DESBLOQUEAR],
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

# Lo que cada plantilla fija en sus extra vars (la encuesta no lo pregunta).
PLANTILLAS = {
    '00_relacion_confianza': {'playbook': '00_relacion_confianza.yml', 'fijas': {}},
    '01a_crear_con_contrasena': {'playbook': '01_crear_usuarios.yml', 'fijas': {'crear_metodo_acceso': 'contrasena'}},
    '01b_crear_con_llave': {'playbook': '01_crear_usuarios.yml', 'fijas': {'crear_metodo_acceso': 'llave'}},
    '02a_cambiar_contrasena': {'playbook': '02_cambiar_contrasena.yml',
                               'fijas': {'contrasena_accion': 'cambiar', 'contrasena_origen': 'lista'}},
    '02b_forzar_cambio': {'playbook': '02_cambiar_contrasena.yml',
                          'fijas': {'contrasena_accion': 'solo_forzar_cambio', 'contrasena_nunca_caduca': 'NO'}},
    '03_auditoria_usuarios': {'playbook': '03_auditoria_usuarios.yml', 'fijas': {}},
    '04_bloquear_eliminar_usuarios': {'playbook': '04_bloquear_eliminar_usuarios.yml', 'fijas': {}},
}

# ---------------------------------------------------------------------------
# Workflows con aprobación: su encuesta es la de la plantilla que protegen,
# precedida por el ticket/justificación que verá quien aprueba.
# ---------------------------------------------------------------------------
TICKET = q('ticket_cambio', 'Ticket o justificación',
           'Número de ticket o RFC y motivo del cambio. Es lo primero que revisa quien aprueba.',
           req=True, mn=3, mx=300)

WORKFLOWS = {
    'wf_crear_con_contrasena': {'name': 'USUARIOS | WF - Crear con contraseña', 'base': '01a_crear_con_contrasena',
                                'description': 'Aprobación -> creación de usuarios con contraseña -> auditoría de verificación.'},
    'wf_crear_con_llave': {'name': 'USUARIOS | WF - Crear con llave', 'base': '01b_crear_con_llave',
                           'description': 'Aprobación -> creación de usuarios con llave -> auditoría de verificación.'},
    'wf_cambiar_contrasena': {'name': 'USUARIOS | WF - Cambiar contraseña', 'base': '02a_cambiar_contrasena',
                              'description': 'Aprobación -> cambio de contraseña -> auditoría de verificación.'},
    'wf_forzar_cambio': {'name': 'USUARIOS | WF - Forzar cambio de contraseña', 'base': '02b_forzar_cambio',
                         'description': 'Aprobación -> forzar cambio de contraseña -> auditoría de verificación.'},
    'wf_bloquear_eliminar': {'name': 'USUARIOS | WF - Bloquear o eliminar', 'base': '04_bloquear_eliminar_usuarios',
                             'description': 'Aprobación -> bloqueo, reactivación o eliminación -> auditoría de verificación.'},
}
AUDITORIA = 'USUARIOS | 3 - Auditoría'
APROBACION_TIMEOUT_SEG = 4 * 3600   # 4 horas


def encuesta_workflow(clave):
    wf = WORKFLOWS[clave]
    return {'name': wf['name'], 'description': wf['description'],
            'spec': [TICKET] + ENCUESTAS[wf['base']]['spec']}


def escribir(nombre, datos):
    with open(os.path.join(BASE, 'encuestas', nombre + '.json'), 'w', encoding='utf-8') as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
        f.write('\n')


def main():
    carpeta = os.path.join(BASE, 'encuestas')
    os.makedirs(carpeta, exist_ok=True)
    generados = set(ENCUESTAS) | set(WORKFLOWS) | {'plantillas'}
    for archivo in os.listdir(carpeta):
        if archivo.endswith('.json') and archivo[:-5] not in generados:
            os.remove(os.path.join(carpeta, archivo))
    for clave, enc in ENCUESTAS.items():
        escribir(clave, enc)
    for clave in WORKFLOWS:
        escribir(clave, encuesta_workflow(clave))
    escribir('plantillas', {
        'plantillas': {ENCUESTAS[k]['name']: dict(PLANTILLAS[k], encuesta=k + '.json') for k in ENCUESTAS},
        'workflows': {w['name']: {'plantilla': ENCUESTAS[w['base']]['name'], 'encuesta': k + '.json',
                                  'auditoria': AUDITORIA, 'aprobacion_timeout_seg': APROBACION_TIMEOUT_SEG}
                      for k, w in WORKFLOWS.items()},
    })
    print('Encuestas generadas:', ', '.join(list(ENCUESTAS) + list(WORKFLOWS)))


if __name__ == '__main__':
    main()
