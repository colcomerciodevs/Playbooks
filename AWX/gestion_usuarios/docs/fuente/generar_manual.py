#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Genera docs/Manual_de_Uso.pdf: guía para quien lanza los workflows en AWX.

Reutiliza estilos, IDs de AWX y la tabla de perfiles de generar_arquitectura.py, y lee
las cuentas críticas y de servicio de vars/comunes.yml, para no repetir datos.

Uso:  python3 -B docs/fuente/generar_manual.py   (requiere reportlab)
"""
import glob
import html
import importlib.util
import os
import re
import sys
import unicodedata

import yaml

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer

sys.dont_write_bytecode = True
AQUI = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('arq', os.path.join(AQUI, 'generar_arquitectura.py'))
arq = importlib.util.module_from_spec(spec)
spec.loader.exec_module(arq)
P, tabla, nota, Flujo, ID = arq.P, arq.tabla, arq.nota, arq.Flujo, arq.AWX_ID
SALIDA = os.path.join(arq.RAIZ, 'docs', 'Manual_de_Uso.pdf')
COMUNES = yaml.safe_load(open(os.path.join(arq.RAIZ, 'vars', 'comunes.yml'), encoding='utf-8'))
PERFILES = yaml.safe_load(open(os.path.join(arq.RAIZ, 'vars', 'perfiles.yml'), encoding='utf-8'))

# Colores de las columnas de resultado
DETIENE = '<font color="#B3261E"><b>SE DETIENE</b></font>'
OMITE = '<font color="#8A5A00"><b>SE OMITE</b></font>'
APLICA = '<font color="#1E6B3A"><b>SE APLICA</b></font>'


def wf(nombre):
    return '<b>%s</b> (ID %d)' % (nombre, ID[nombre])


def portada():
    return [
        P('En pocas palabras', 'h1'),
        P('Usted no entra a los servidores. Llena un formulario (la <b>encuesta</b>) en AWX, un aprobador lo revisa y AWX hace el trabajo '
          'en todos los servidores que usted indicó. Al final recibe un <b>informe</b> que muestra cómo quedó cada cuenta.'),
        Spacer(1, 3),
        Flujo([('1. Lanzar', 'elige el workflow\nen AWX'), ('2. Encuesta', 'ticket, servidores\ny usuarios'),
               ('3. Aprobación', 'admin revisa\n(máx. 4 horas)'), ('4. Ejecución', 'valida primero,\nluego aplica'),
               ('5. Informe', 'verifica cómo\nquedaron')],
              pies={2: 'Rechazada o vencida:\nno se cambia nada', 3: 'Si algo no cuadra:\nno se cambia nada'}),
        P('La regla de oro', 'h1'),
        nota('<b>Primero se valida todo, después se cambia.</b> Si una validación falla, el job termina con el mensaje '
             '<i>"No se modificó ningún servidor"</i>: ningún servidor quedó a medias. Corrija lo que dice el mensaje y vuelva a lanzar.'),
        Spacer(1, 6),
        P('Qué workflow lanzar', 'h1'),
        P('En AWX vaya a <b>Plantillas</b> y busque las que empiezan por <b>USUARIOS | WF</b>. Los workflows piden aprobación; '
          'las plantillas sueltas que cambian cuentas son solo para administradores.'),
        tabla(['Quiero…', 'Lanzo', 'Aprobación'], [
            ['Crear una cuenta que entra con contraseña', wf('USUARIOS | WF - Crear con contraseña'), 'Sí'],
            ['Crear el personal de QA o la cuenta del conector OIM', wf('USUARIOS | WF - Crear con contraseña')
             + ' con su catálogo (ver "Perfiles y catálogos")', 'Sí'],
            ['Crear una cuenta que entra con llave SSH (PuTTY)', wf('USUARIOS | WF - Crear con llave'), 'Sí'],
            ['Darle o cambiarle el perfil (sudo) a una cuenta que ya existe', 'El workflow de crear, con "Actualizar usuarios que ya existen" = SI', 'Sí'],
            ['Poner una contraseña nueva', wf('USUARIOS | WF - Cambiar contraseña'), 'Sí'],
            ['Obligar a cambiar la contraseña sin cambiarla yo (uno, un catálogo o todos)', wf('USUARIOS | WF - Forzar cambio de contraseña'), 'Sí'],
            ['Bloquear, reactivar o eliminar una cuenta', wf('USUARIOS | WF - Bloquear o eliminar'), 'Sí'],
            ['Revisar cómo están las cuentas (no cambia nada)', '<b>USUARIOS | 3 - Auditoría</b> (ID %d)' % ID['USUARIOS | 3 - Auditoría'], 'No'],
            ['Preparar un servidor nuevo para la automatización', '<b>USUARIOS | 0 - Relación de confianza</b> (ID %d). Solo administradores.' % ID['USUARIOS | 0 - Relación de confianza'], 'No'],
        ], [0.40, 0.47, 0.13]),
        PageBreak(),
    ]


def encuesta():
    return [
        P('Cómo llenar la encuesta', 'h1'),
        P('Los campos con <font color="#B3261E">*</font> son obligatorios. Cada pregunta trae una ayuda en AWX con el formato '
          '<b>[valor] efecto</b>. Estos campos aparecen en casi todos los workflows:'),
        tabla(['Campo', 'Qué escribir', 'Ejemplo'], [
            ['Ticket o justificación', 'Número de ticket y una frase de por qué. Es lo primero que lee el aprobador.', 'REQ-1234 alta de soporte zona norte'],
            ['Servidores o grupo del inventario', 'Uno o varios grupos o servidores, <b>separados por coma</b> (sin "·" ni espacios). '
             '<b>:!</b> excluye un servidor. No se acepta localhost.', 'GEOPOS<br/>GEOPOS,PPU<br/>srv1,srv2<br/>GEOPOS:!srv1'],
            ['Usuario(s)', 'Nombres de cuenta en minúscula, separados por coma.', 'jperez,mgomez'],
            ['Origen / Usuarios a incluir', '<b>encuesta</b> o <b>lista</b>: los que usted escribe. <b>catalogo</b>: una lista ya guardada en el proyecto '
             '(por ejemplo admins_linux o soporte_zona_norte).', 'catalogo → soporte_zona_norte'],
            ['Usuarios (al crear)', 'Una línea por persona: <font name="Mono" size="7.6">usuario;Nombre completo;grupo</font>. El grupo es opcional.',
             '<font name="Mono" size="7.6">jperez;Juan Pérez;soporte</font>'],
            ['Preguntas SI / NO', 'Deje el valor por defecto si no está seguro: es la opción segura.', '-'],
        ], [0.25, 0.47, 0.28]),
        Spacer(1, 4),
        nota('<b>Las preguntas que dicen "(si …)" solo se usan en ese caso.</b> AWX no puede ocultar preguntas, así que el formulario las muestra '
             'todas. Por ejemplo, "Catálogo (si origen = catalogo)" se ignora cuando el origen es encuesta.'),
    ]


def protecciones():
    criticas = COMUNES['usuarios_protegidos']
    personas = [c for c in criticas if c in ('root', 'tux', 'adminso', 'azureuser', 'opc', 'ec2-user', 'cloud-user', 'ubuntu')]
    automat = [c for c in criticas if c in ('ansible_test', 'iacolcoauto', 'awx')]
    sistema = [c for c in criticas if c not in personas + automat]
    return [
        P('Cuentas que el sistema protege', 'h1'),
        P('Hay tres tipos de cuentas que no se tratan como las de una persona normal. Conocerlos explica casi todos los '
          '"se detuvo" y "se omitió" que verá en los resultados.'),
        tabla(['Tipo', 'Cuáles son', 'Por qué se protegen'], [
            ['<b>Críticas</b>', 'Administradoras: %s.<br/>Automatización: %s.<br/>Sistema: %s.'
             % (', '.join(personas), ', '.join(automat), ', '.join(sistema)),
             'Si se tocan por error se puede perder el acceso a los servidores o romper la automatización.'],
            ['<b>De sistema o servicio</b>', 'Cualquier cuenta con número de usuario (UID) menor a %d.' % COMUNES['uid_minimo_humano'],
             'Las usa el sistema operativo o una aplicación, no una persona.'],
            ['<b>De aplicación</b>', 'Lista fija: %s. Tienen UID de persona, pero son de una aplicación.' % ', '.join(COMUNES['cuentas_servicio']),
             'Obligarlas a cambiar la contraseña detendría la aplicación.'],
        ], [0.18, 0.47, 0.35]),
        Spacer(1, 6),
        P('Dos palabras que verá en los resultados', 'h2'),
        tabla(['Palabra', 'Qué significa', 'Qué hacer'], [
            [DETIENE, 'El job termina sin cambiar <b>ningún</b> servidor. El mensaje dice qué cuenta o dato causó el problema.',
             'Corregir la encuesta (por ejemplo, quitar la cuenta) y lanzar de nuevo.'],
            [OMITE, 'Esa cuenta se salta y el resto sí se procesa. El resultado y el informe la listan con el motivo.',
             'Nada, si era lo esperado. Revise la lista de omitidas.'],
            [APLICA, 'Se hace el cambio.', '-'],
        ], [0.17, 0.55, 0.28]),
        Spacer(1, 6),
        P('Qué pasa con cada tipo de cuenta, según lo que pida', 'h2'),
        P('Lea la fila de lo que va a hacer y la columna del tipo de cuenta que incluyó.'),
        tabla(['Si pide…', 'Cuenta crítica (root, tux…)', 'Cuenta de sistema (UID &lt; %d)' % COMUNES['uid_minimo_humano'], 'La cuenta no existe en un servidor'], [
            ['<b>Crear</b> (1a / 1b)', DETIENE + '. No se crean ni modifican.',
             'Si ya existe y marcó Actualizar o Renovar llave: ' + DETIENE + '. Si no, ' + OMITE + ' (ya existe).', APLICA + ': se crea.'],
            ['<b>Cambiar contraseña</b> (2a)', 'Solo con <b>CONFIRMAR</b> y servidores concretos (no all ni comodines); si no, ' + DETIENE
             + '. Con CONFIRMAR: ' + APLICA + ' la clave nueva, pero "sin caducidad" y "forzar cambio" <b>se ignoran</b> (ver ejemplo 1).',
             OMITE, OMITE + ' en ese servidor; en los demás se aplica.'],
            ['<b>Forzar cambio</b> a una lista (2b)', DETIENE + '. Quite la cuenta de la lista.', OMITE,
             OMITE + '. Si la cuenta existe pero no tiene contraseña (solo llave o bloqueada): ' + DETIENE + '.'],
            ['<b>Forzar cambio</b> en bloque (2b: catálogo o todos UID ≥ %d)' % COMUNES['uid_minimo_humano'], OMITE, OMITE,
             'No aplica: solo se toman las cuentas que existen en cada servidor.'],
            ['<b>Bloquear, reactivar o eliminar</b> (4)', DETIENE + '.', OMITE, OMITE + ' en ese servidor.'],
            ['<b>Auditar</b> (3)', 'Se revisa, no se cambia.', 'Se revisa si su UID está en el rango pedido.',
             'En la verificación de un workflow aparece en "Cuentas no encontradas".'],
        ], [0.20, 0.30, 0.24, 0.26]),
        Spacer(1, 4),
        nota('<b>En bloque, además</b>, se omiten las cuentas de aplicación (%s), las que no tienen contraseña (entran solo con llave o están '
             'bloqueadas) y las que no pueden iniciar sesión. Así el cambio masivo nunca deja una aplicación o una cuenta de llave sin acceso.'
             % ', '.join(COMUNES['cuentas_servicio'])),
        Spacer(1, 4),
        nota('<b>Las cuentas de automatización</b> (%s) solo las crea la plantilla 0. Ninguna otra opción las toca.' % ', '.join(automat)),
        Spacer(1, 8),
    ]


def ejemplos():
    casos = [
        ('Cambiar la clave de root con "Forzar cambio" = SI',
         'Workflow Cambiar contraseña · Usuario: root · Servidores: srv-pos-01 · Confirmación: CONFIRMAR · Forzar cambio: SI',
         'La clave de root <b>sí cambia</b>. "Forzar cambio" <b>se ignora</b> solo para root: conserva su caducidad actual. '
         'El resultado lo dice en "Caducidad sin cambios (cuentas críticas): root". Así root no queda pidiendo cambio de clave en el próximo '
         'ingreso, lo que podría bloquear procesos que entran con ella.'),
        ('Cambiar la clave de root en todos los servidores',
         'Servidores: all (o GEOPOS*) · Usuario: root',
         '<b>Se detiene.</b> Para una cuenta crítica hay que indicar servidores concretos y escribir CONFIRMAR. Es para que un error de '
         'digitación no cambie root en todo el parque.'),
        ('Forzar el cambio de contraseña a todo el personal de GEOPOS',
         'Workflow Forzar cambio · Usuarios a incluir: todos_uid_1000 · Servidores: GEOPOS',
         'Se aplica a las cuentas de persona. Se <b>omiten solas</b>: root y demás críticas, pos y postgres, cuentas que solo entran con llave, '
         'cuentas sin shell, cuentas expiradas (deshabilitadas por fecha) y las que ya tienen un cambio forzado pendiente. El informe final lista a quién se le aplicó. <b>Consejo:</b> lance antes la auditoría y, en la hoja '
         '<b>Plan forzar cambio contraseña</b> del Excel, revise las filas REVISAR y CONFIRMAR (ver "El informe de auditoría").'),
        ('Bloquear a dos personas, pero se coló root en la lista',
         'Workflow Bloquear o eliminar · Usuarios: jperez,root · Acción: bloquear',
         '<b>Se detiene sin bloquear a nadie</b>, tampoco a jperez. El mensaje dice "No se permiten cuentas protegidas: root". Quite root y '
         'lance de nuevo.'),
        ('Crear un usuario que ya existe en algunos servidores',
         'Workflow Crear con contraseña · Usuarios: jperez;Juan Pérez · Actualizar usuarios que ya existen: NO',
         'Se crea donde no existe. Donde ya existe <b>se omite</b> y no se toca su contraseña. Con Actualizar = SI se le aplican grupos y '
         'perfil, pero la contraseña tampoco cambia.'),
        ('Eliminar una cuenta cuyo home no está en /home',
         'Acción: eliminar · Confirmación: CONFIRMAR',
         '<b>Se detiene.</b> Solo se eliminan de forma automática cuentas con home en /home o /export/home, para no borrar carpetas de '
         'aplicaciones. Ese caso lo hace un administrador a mano.'),
    ]
    salida = [P('Ejemplos: qué pasa si…', 'h1'),
              P('Casos reales para entender las reglas anteriores.')]
    for i, (titulo, pide, pasa) in enumerate(casos, 1):
        salida.append(KeepTogether([
            P('%d. %s' % (i, titulo), 'h2'),
            tabla(['Lo que se llena', 'Lo que pasa'], [[pide, pasa]], [0.38, 0.62]),
        ]))
    salida.append(PageBreak())
    return salida


def _sin_marcas(texto):
    return html.unescape(re.sub('<[^>]+>', '', texto)).strip()


def clave(texto):
    """Nombre del destino PDF de un título (enlaces del índice y marcadores)."""
    plano = unicodedata.normalize('NFKD', _sin_marcas(texto).lower()).encode('ascii', 'ignore').decode()
    return 's_' + re.sub('[^a-z0-9]+', '_', plano).strip('_')[:60]


def solo_contrasena(nombre):
    p = PERFILES['perfiles'].get(nombre, {})
    return bool(p.get('solo_contrasena')) or ('grupo_sudo' in p and not p.get('sudo_nopasswd'))


def catalogos():
    """Lee vars/catalogos/*.yml: nombre, descripción, usuarios, perfiles, grupos y método."""
    salida = []
    for ruta in sorted(glob.glob(os.path.join(arq.RAIZ, 'vars', 'catalogos', '*.yml'))):
        texto = open(ruta, encoding='utf-8').read()
        datos = yaml.safe_load(texto) or {}
        base = datos.get('catalogo_defaults', {}) or {}
        usuarios = datos.get('usuarios', []) or []
        perfiles = sorted({u.get('perfil', base.get('perfil', '')) for u in usuarios})
        grupos = sorted({u.get('grupo', base.get('grupo', '')) for u in usuarios})
        desc = re.search(r'^# Catálogo: (.*?)\.?\s*$', texto, re.M)
        if any(solo_contrasena(x) for x in perfiles if x):
            metodo = 'Solo contraseña (WF Crear con contraseña)'
        elif re.search(r'Uso recomendado: Método = llave', texto):
            metodo = 'Llave recomendada (WF Crear con llave)'
        else:
            metodo = 'Contraseña o llave'
        salida.append({
            'nombre': os.path.basename(ruta)[:-4], 'desc': desc.group(1) if desc else '', 'n': len(usuarios),
            'usuarios': [u['usuario'] for u in usuarios],
            'perfil': ', '.join(x for x in perfiles if x) or 'El de la encuesta' + (' (o el de cada cuenta)' if '' not in perfiles else ''),
            'grupo': ', '.join(g for g in grupos if g) or 'Uno con el nombre de cada usuario', 'metodo': metodo,
        })
    return salida


def receta(titulo, intro, campos, queda, cuidado):
    return [KeepTogether([
        P(titulo, 'h2'),
        P(intro),
        tabla(['Pregunta de la encuesta', 'Qué poner'], campos, [0.42, 0.58]),
        Spacer(1, 3),
        tabla(['Qué queda en cada servidor'], [[queda]], [1.0]),
        Spacer(1, 3),
        nota(cuidado),
    ]), Spacer(1, 6)]


def perfiles():
    perf = PERFILES['perfiles']
    qa, oim, geo = perf['perfil_qa'], perf['perfil_integracion_oim'], perf['perfil_soporte_geopos']
    cats = {c['nombre']: c for c in catalogos()}
    wf_clave = wf('USUARIOS | WF - Crear con contraseña')
    salida = [
        P('Perfiles y catálogos: cómo usarlos', 'h1'),
        P('Dos ideas bastan para usar esta sección:'),
        tabla(['Concepto', 'Qué es', 'Dónde vive'], [
            ['<b>Perfil</b>', 'Qué puede hacer la cuenta con sudo: nada, todo o una lista de comandos. Algunos perfiles traen opciones '
             'extra: una regla de sudo para todo un grupo, comandos prohibidos u opciones de sudo.', 'vars/perfiles.yml'],
            ['<b>Catálogo</b>', 'Una lista de cuentas ya guardada en el proyecto, con sus datos: nombre completo, grupo, perfil, shell y, si '
             'hace falta, entorno o contraseña sin caducidad. Evita escribir las cuentas a mano y equivocarse.', 'vars/catalogos/&lt;nombre&gt;.yml'],
        ], [0.14, 0.62, 0.24]),
        P('Quién manda cuando hay datos repetidos', 'h2'),
        P('Si el catálogo y la encuesta dicen cosas distintas, gana el dato más específico, en este orden:'),
        tabla(['Orden', 'Fuente', 'Ejemplo'], [
            ['1', 'El dato escrito en la cuenta dentro del catálogo', 'svc_oim tiene perfil: perfil_integracion_oim'],
            ['2', 'catalogo_defaults del catálogo (vale para todas sus cuentas)', 'soporte_qa: grupo soporte y perfil perfil_qa'],
            ['3', 'La encuesta: "Perfil de la cuenta", "Grupos secundarios"', 'Origen = encuesta y Perfil = perfil_auditor_linux'],
            ['4', 'El valor por defecto del proyecto', 'Perfil %s; grupo con el nombre del usuario' % PERFILES['perfil_por_defecto']],
        ], [0.08, 0.52, 0.40]),
        Spacer(1, 3),
        nota('<b>Lo que siempre sale de la encuesta:</b> los servidores, el método (contraseña o llave, según el workflow), la contraseña '
             'inicial, "Forzar cambio" (salvo cuentas con contraseña sin caducidad en el catálogo) y "Actualizar usuarios que ya existen". '
             'Con Origen = catalogo, la pregunta "Perfil de la cuenta" solo se usa para las cuentas del catálogo que no traen perfil.'),
        Spacer(1, 6),
        arq.perfiles_tabla(),
        Spacer(1, 6),
        P('Catálogos disponibles', 'h2'),
        P('Se eligen en la encuesta con Origen = <b>catalogo</b> y Catálogo = el nombre de la primera columna. Esta tabla se arma '
          'leyendo los archivos del proyecto.'),
        tabla(['Catálogo', 'Para qué', 'N.º', 'Perfil', 'Grupo primario', 'Método'],
              [['<font name="Mono" size="7.6">%s</font>' % c['nombre'], html.escape(c['desc'][:1].upper() + c['desc'][1:]), str(c['n']),
                c['perfil'], html.escape(c['grupo']), c['metodo']] for c in cats.values()],
              [0.20, 0.25, 0.05, 0.20, 0.13, 0.17]),
        Spacer(1, 3),
        nota('<b>Solo contraseña:</b> los perfiles cuyo sudo pide la contraseña del usuario (perfil_qa y perfil_integracion_oim) no se '
             'ofrecen en el workflow de llave, y si se intenta, el job se detiene sin cambiar nada: una cuenta con llave no tiene contraseña '
             'y nunca podría usar sudo.'),
        PageBreak(),
    ]

    salida += receta(
        'Receta: personal de QA (catálogo soporte_qa)',
        'Crea las %d cuentas de QA con perfil <b>perfil_qa</b>: sudo completo para el grupo <b>%s</b>, sin poder abrir una consola de root.'
        % (cats['soporte_qa']['n'], qa['grupo_sudo']),
        [['Workflow', wf_clave],
         ['Ticket o justificación', 'El ticket de la solicitud'],
         ['Servidores o grupo del inventario', 'Los servidores de QA, por ejemplo <font name="Mono" size="7.6">FSC_QA</font>'],
         ['Origen de la lista de usuarios', '<b>catalogo</b>'],
         ['Catálogo', '<b>soporte_qa</b>'],
         ['Contraseña inicial', 'La contraseña temporal (se entrega por un canal seguro)'],
         ['Forzar cambio de contraseña en el primer ingreso', '<b>SI</b>'],
         ['Perfil de la cuenta', 'Cualquiera: manda el del catálogo (perfil_qa)'],
         ['Actualizar usuarios que ya existen', '<b>SI</b> si algunas cuentas ya existen y deben quedar en el grupo %s con este sudo; '
          'si no, NO' % qa['grupo_sudo']]],
        'Cuenta con grupo primario <b>%s</b> y contraseña temporal que debe cambiar al entrar. Una sola regla de sudo para todo el grupo, '
        '<font name="Mono" size="7.6">/etc/sudoers.d/grupo_%s</font>: <font name="Mono" size="7.6">%%%s ALL=(ALL) ALL</font> excepto %s. '
        'sudo pide <b>la contraseña del propio usuario</b> y la recuerda unos 5 minutos. Pueden reiniciar servicios '
        '(<font name="Mono" size="7.6">sudo systemctl restart httpd</font>) y crear, editar o borrar archivos y permisos con sudo. No pueden '
        '<font name="Mono" size="7.6">sudo su -</font>, <font name="Mono" size="7.6">sudo -i</font>, <font name="Mono" size="7.6">sudo -s</font>, '
        'ni <font name="Mono" size="7.6">sudo bash</font>. Un script se ejecuta directo (<font name="Mono" size="7.6">sudo /ruta/script.sh</font>) '
        'y para escribir en un archivo de root se usa <font name="Mono" size="7.6">echo x | sudo tee archivo</font>.'
        % (qa['grupo_sudo'], qa['grupo_sudo'], qa['grupo_sudo'], ', '.join(qa['prohibidos'])),
        '<b>Tenga en cuenta:</b> (1) la regla es del <b>grupo</b>: la recibe todo miembro de %s en ese servidor, también quien ya estaba. '
        'Si alguno tenía sudo sin contraseña o podía usar sudo -i, puede dejar de hacerlo. (2) A una cuenta que ya existe no se le cambia la '
        'contraseña ni se le fuerza el cambio, aunque Actualizar = SI: use Cambiar contraseña o Forzar cambio con el catálogo soporte_qa. '
        '(3) Los prohibidos evitan entrar como root por descuido; no son una barrera de seguridad.' % qa['grupo_sudo'])

    salida += [Spacer(1, 4)] + receta(
        'Receta: cuenta del conector OIM (catálogo integracion_oim)',
        'Crea <b>%s</b>, la cuenta con la que el conector UNIX de Oracle Identity Manager administra cuentas, en reemplazo de root. '
        'Pruebe primero en <b>un solo servidor</b> y extienda cuando el equipo de OIM confirme.' % ', '.join(cats['integracion_oim']['usuarios']),
        [['Workflow', wf_clave],
         ['Ticket o justificación', 'El ticket del cambio de root a la cuenta de servicio'],
         ['Servidores o grupo del inventario', 'Un servidor de prueba; después, el resto'],
         ['Origen de la lista de usuarios', '<b>catalogo</b>'],
         ['Catálogo', '<b>integracion_oim</b>'],
         ['Contraseña inicial', 'La contraseña que usará el conector (se entrega a OIM por un canal seguro)'],
         ['Forzar cambio de contraseña en el primer ingreso', 'Cualquiera: el catálogo la deja sin caducidad y nunca fuerza el cambio'],
         ['Perfil de la cuenta', 'Cualquiera: manda el del catálogo (perfil_integracion_oim)'],
         ['Actualizar usuarios que ya existen', '<b>NO</b> (es una cuenta de servicio: con SI el job se detiene si ya existe)']],
        'Shell <font name="Mono" size="7.6">/bin/sh</font>, home propio, /usr/sbin en el PATH y prompt terminado en '
        '<font name="Mono" size="7.6">#</font> (bloque gestionado en ~/.profile). Contraseña <b>sin caducidad</b> y sin cambio forzado. '
        'sudo con su propia contraseña, <font name="Mono" size="7.6">%s</font>, con cualquier argumento: %s.'
        % (html.escape(', '.join(oim['defaults'])), ', '.join(oim['comandos_libres'])),
        '<b>Tenga en cuenta:</b> (1) con estos comandos (sh incluido) la cuenta <b>equivale a root</b>, como lo exige el conector; queda '
        'registrada en el log de sudo. (2) "Sin caducidad" solo se aplica al crearla: si ya existía, use Cambiar contraseña con "Contraseña '
        'sin caducidad" = SI y "Forzar cambio" = NO. (3) Está en cuentas_servicio, así que el forzado en bloque nunca la toca. (4) La carpeta '
        '/etc/connector_mirror_files no se crea hasta que OIM confirme que la usa. Para verificar en el servidor: '
        '<font name="Mono" size="7.6">chage -l svc_oim</font> (Password expires: never), '
        '<font name="Mono" size="7.6">su - svc_oim</font> y <font name="Mono" size="7.6">sudo -l</font>.')

    m = lambda t: '<font name="Mono" size="7.6">%s</font>' % html.escape(t)
    salida += [KeepTogether([
        P('Receta: soporte Geopos (perfil_soporte_geopos)', 'h2'),
        P('Para el personal que atiende las cajas y servidores Geopos: maneja los servicios Geopos, consulta logs, procesos, red y disco, '
          'y ejecuta los scripts de rifa y sonido, <b>sin poder volverse root</b>. Se elige como perfil en la encuesta: no tiene catálogo propio.'),
        tabla(['Pregunta de la encuesta', 'Qué poner'], [
            ['Workflow', wf_clave + '. Con ' + wf('USUARIOS | WF - Crear con llave') + ' es igual, sin las preguntas de contraseña.'],
            ['Ticket o justificación', 'El ticket de la solicitud, por ejemplo <i>REQ-1234 sudo soporte Geopos zona norte</i>'],
            ['Servidores o grupo del inventario', 'Los servidores o grupos Geopos, separados por coma. Ejemplo: ' + m('GEOPOS') + ' o '
             + m('GEOPOS:!srv-pos-01')],
            ['Origen de la lista de usuarios', '<b>catalogo</b> para todo un equipo, o <b>encuesta</b> para una o pocas personas'],
            ['Usuarios (si origen = encuesta)', 'Una línea por persona: ' + m('usuario;Nombre completo;grupo') + '. Ejemplo: '
             + m('jperez;Juan Pérez;soporte') + '. Vacío si el origen es catalogo.'],
            ['Catálogo (si origen = catalogo)', '<b>soporte_zona_norte</b> o <b>soporte_zona_centro</b>. Vacío si el origen es encuesta.'],
            ['Grupos secundarios', 'Vacío (solo si se los pidieron; se agregan si existen en el servidor)'],
            ['Permitir acceso SSH', '<b>SI</b>'],
            ['Contraseña inicial', 'La contraseña temporal (se entrega por un canal seguro). Solo la reciben las cuentas nuevas.'],
            ['Forzar cambio de contraseña en el primer ingreso', '<b>SI</b>'],
            ['Perfil de la cuenta', '<b>perfil_soporte_geopos</b>. Es la pregunta clave: esos catálogos no traen perfil, así que manda la encuesta.'],
            ['Actualizar usuarios que ya existen', '<b>SI</b> si alguien ya tiene cuenta y hay que cambiarle el sudo a este perfil (su contraseña no '
             'cambia). <b>NO</b> si solo se crean cuentas nuevas: las existentes se omiten.'],
        ], [0.36, 0.64]),
        Spacer(1, 3),
        P('Para revisar al terminar: en el resultado del job cada cuenta debe decir <i>perfil perfil_soporte_geopos (sudo limitado)</i>, y en el '
          'servidor <font name="Mono" size="7.6">sudo -l</font> con el usuario lista los comandos. Si un servicio no existe en un servidor, el '
          'resultado lo avisa y ese comando se omite allí.', 'c'),
        Spacer(1, 3),
        tabla(['Antes, como root', 'Ahora, con su usuario'], [
            [m('geopos status') + ' (y geopromotion, tomcat6-consola, -conciliacion, -turnos, -salida, -geogames)',
             m('sudo geopos status') + '. Acciones: ' + ', '.join(geo['acciones'])],
            [m('cat /geopos2/rifa/caja_geo>>/dev/ttyUSB0'), m('sudo tee -a /dev/ttyUSB0 < /geopos2/rifa/caja_geo > /dev/null')],
            [m('sh /geopos2/rifa/demonio.sh &'), m('sudo -b sh /geopos2/rifa/demonio.sh') + ' (-b lo deja en segundo plano; con & sudo no '
             'puede pedir la contraseña)'],
            [m('sh /root/demonio-sonido.sh &'), m('sudo -b sh /root/demonio-sonido.sh')],
            ['Logs', m('sudo tail -f /ruta/archivo.log') + ', ' + m('sudo grep ERROR /ruta/archivo.log') + ', ' + m('sudo zcat log.gz | grep x')],
            ['Procesos, red y disco', m('sudo lsof -i :8080') + ', ' + m('sudo ss -tulpn') + ', ' + m('sudo kill PID') + ', ' + m('sudo du -sh /ruta')],
            ['% de uso de discos y hora', m('df -h') + ' y ' + m('date') + ': <b>sin sudo</b>. Igual ' + m('ps') + ', ' + m('top') + ', '
             + m('free') + ', ' + m('uptime') + ' y ' + m('systemctl status servicio') + '.'],
        ], [0.40, 0.60]),
        Spacer(1, 3),
        nota('<b>Tenga en cuenta:</b> (1) con sudo puede usar: %s, con cualquier argumento, más los servicios y scripts de la tabla; '
             'cualquier otra cosa responde "not allowed". Por eso <b>no</b> funcionan sudo su -, sudo -i, sudo -s, sudo bash, sudo vi ni sudo less. '
             '(2) Los scripts van <b>exactamente</b> como en la tabla: otra ruta u otros argumentos se niegan. (3) Los dos scripts deben ser de '
             'root y nadie más debe poder modificarlos; si alguien puede editarlos, puede volverse root. Revíselo con '
             '<font name="Mono" size="7.6">ls -l /geopos2/rifa/demonio.sh</font>. (4) cat, tail y grep con sudo pueden leer cualquier archivo '
             'del servidor. (5) sudo pide la contraseña del propio usuario y la recuerda unos 5 minutos.' % ', '.join(geo['comandos_libres'])),
    ]), Spacer(1, 6)]

    salida += [
        KeepTogether([P('Otros catálogos', 'h2'), tabla(['Catálogo', 'Cómo se usa'], [
            ['admins_linux', 'Administradores con sudo completo. Use el workflow Crear con llave: reutiliza la llave guardada de cada persona.'],
            ['soporte_zona_norte, soporte_zona_centro', 'Personal de soporte con grupo soporte. El perfil es el que elija en la encuesta '
             '(%s si no cambia nada; perfil_soporte_geopos para soporte Geopos). Contraseña o llave.' % PERFILES['perfil_por_defecto']],
            ['cuentas_de_servicio', 'Cuentas de aplicaciones o plataformas. Cada cuenta trae su perfil. Contraseña o llave.'],
        ], [0.30, 0.70])]),
        P('Usar un perfil sin catálogo', 'h2'),
        P('Con Origen = <b>encuesta</b> escriba las cuentas en "Usuarios" (una por línea: usuario;Nombre completo;grupo) y elija el '
          '"Perfil de la cuenta". Sirve para una persona suelta. Por ejemplo, alguien nuevo de QA que aún no está en el catálogo: '
          '<font name="Mono" size="7.6">jperez;Juan Pérez (QA);soporte</font> con Perfil = perfil_qa. Si alguien va a repetirse, '
          'mejor pida que lo agreguen al catálogo.'),
        P('Cambiar o quitar el perfil de una cuenta', 'h2'),
        tabla(['Situación', 'Qué pasa'], [
            ['Catálogo con perfil', 'Manda el perfil del catálogo. Ejemplo: admins_linux siempre da perfil_admin_linux, aunque la encuesta diga otra cosa.'],
            ['Cambiar el perfil de una cuenta que ya existe', 'Workflow de crear con su usuario, el perfil nuevo y "Actualizar usuarios que ya existen" = SI. '
             'Se reemplaza su regla de sudo; contraseña, grupo primario y home no cambian.'],
            ['Un comando del perfil no está en un servidor', 'Ese comando se omite en ese servidor y el resultado lo avisa. El resto sí queda.'],
            ['Quitar el sudo a alguien', 'Workflow de crear con su usuario, perfil_estandar y "Actualizar usuarios que ya existen" = SI. '
             'Si el sudo le llega por el grupo %s (perfil_qa), hay que sacarlo del grupo: pídalo a un administrador.' % qa['grupo_sudo']],
            ['Bloquear o eliminar', 'También se le quita su regla de sudo propia.'],
            ['Reactivar', '<b>No</b> le devuelve el sudo. Vuelva a aplicar su perfil con el workflow de crear y Actualizar = SI.'],
        ], [0.33, 0.67]),
        P('Agregar personas a un catálogo o pedir un perfil nuevo', 'h2'),
        P('Los catálogos y perfiles son archivos del proyecto: los cambia un administrador, que luego sincroniza el proyecto en AWX. '
          'Envíe la lista con estos datos (solo usuario es obligatorio):'),
        tabla(['Campo', 'Qué es', 'Si no se indica'], [
            ['usuario', 'Nombre de la cuenta, en minúscula', '(obligatorio)'],
            ['nombre', 'Nombre completo o descripción', 'El usuario'],
            ['grupo / grupos', 'Grupo primario / grupos secundarios', 'Grupo con el nombre del usuario / ninguno'],
            ['perfil', 'Uno de los perfiles de la tabla', 'El de la encuesta'],
            ['shell, home, uid', 'Shell, carpeta personal y número de usuario fijos', '/bin/bash, /home/usuario y el siguiente libre'],
            ['entorno', 'Líneas para ~/.profile (PATH, prompt…)', 'Ninguna'],
            ['contrasena_sin_caducidad', 'true en cuentas de servicio: no caduca ni se fuerza el cambio', 'false'],
        ], [0.25, 0.45, 0.30], ['m', 'c', 'c']),
        PageBreak(),
    ]
    return salida


def llaves_y_resultados():
    return [
        P('Cuentas con llave SSH', 'h1'),
        tabla(['Pregunta', 'Respuesta'], [
            ['¿Dónde queda la llave?', 'En el almacén de AWX: /data/work/gestion_usuarios/keys/. Por persona hay tres archivos: la llave privada, '
             'la .pub y la <b>.ppk</b> para PuTTY. Se la entrega un administrador.'],
            ['¿Se crea una llave por servidor?', 'No. Cada persona tiene una sola llave que sirve en todos los servidores. Si ya tiene, se reutiliza.'],
            ['¿Y si la perdió o se la robaron?', 'Workflow Crear con llave, "RENOVAR LLAVE" = SI. Se crea una nueva y se guarda la anterior en _anteriores. '
             '<b>Ojo:</b> solo se reemplaza en los servidores indicados; en los demás sigue la anterior.'],
            ['¿Puede usar contraseña?', 'No. Una cuenta con llave no tiene contraseña y nunca caduca. Por eso, si tiene sudo, sudo no le pide clave.'],
        ], [0.27, 0.73]),
        P('Después de lanzar: cómo saber qué pasó', 'h1'),
        tabla(['Lo que ve en AWX', 'Qué significa'], [
            ['El workflow espera en "Aprobación"', 'Falta que admin apruebe. Si no lo hace en 4 horas o lo rechaza, termina sin cambios.'],
            ['El nodo 2 en rojo con "No se modificó ningún servidor"', 'Una validación detuvo el trabajo. Lea el mensaje: dice qué corregir.'],
            ['El nodo 2 en rojo sin ese mensaje', 'Falló un servidor mientras se aplicaba. El informe del cambio se genera igual: en la hoja '
             'Servidores está el error y en Detalle, qué cuentas alcanzaron a quedar aplicadas. Avise a un administrador con el número de job.'],
            ['Un servidor como "unreachable"', 'No respondió. Se omitió; los demás siguieron. Reintente solo ese servidor más tarde.'],
            ['Todo en verde', 'Revise el informe del cambio (nodo 2) y la verificación del nodo 3 (abajo).'],
        ], [0.38, 0.62]),
        Spacer(1, 5),
        PageBreak(),
        P('El informe del cambio (Excel)', 'h1'),
        P('Cada cambio (opciones 0, 1a, 1b, 2a, 2b y 4, solas o dentro de su workflow) deja <b>un archivo Excel</b> en '
          '/data/work/gestion_usuarios/reportes/ con lo que se pidió y lo que pasó en cada cuenta y servidor. Se llama según la operación: '
          '<font name="Mono" size="7.6">forzar_cambio_contrasena_&lt;fecha&gt;.xlsx</font>, cambio_contrasena, crear_usuarios_contrasena, '
          'crear_usuarios_llave, bloquear_cuentas, reactivar_cuentas, eliminar_cuentas o relacion_confianza. La ruta sale al final del job '
          '(y en Artefactos: informe_cambio). Se genera aunque un servidor falle a mitad; nunca incluye contraseñas ni hashes.'),
        tabla(['Hoja', 'Qué tiene'], [
            ['<b>Resumen</b>', 'Fecha, operación, servidores, lo que pidió la encuesta, ticket, quién lo lanzó y número de job. Luego, cuántos '
             'servidores terminaron, fallaron o no respondieron; cuántas cuentas cambiaron y cuántas no (con los motivos); cuántas se '
             'verificaron y qué sigue.'],
            ['<b>Por usuario</b>', 'Una fila por usuario: en qué servidores se aplicó, en cuáles no y por qué. Resultado APLICADO, PARCIAL, '
             'SIN CAMBIOS o REVISAR. Es la lista para avisar a cada persona.'],
            ['<b>Detalle</b>', 'Una fila por cuenta y servidor: resultado, motivo, si se verificó y el estado <b>ANTES</b> y <b>DESPUÉS</b> '
             '(contraseña, último cambio, vencimiento y expiración de la cuenta), grupos, UID y shell.'],
            ['<b>Servidores</b>', 'Cada servidor: OK, FALLÓ DURANTE EL CAMBIO (con el error) o SIN RESPUESTA, y cuántas cuentas cambió.'],
        ], [0.18, 0.82]),
        P('Resultado de cada cuenta', 'h2'),
        tabla(['Resultado', 'Qué significa'], [
            ['FORZADO', 'Conserva su contraseña, pero en el próximo ingreso el sistema le pedirá la actual y una nueva.'],
            ['CONTRASEÑA CAMBIADA', 'Se le asignó la contraseña nueva.'],
            ['CREADA / ACTUALIZADA / LLAVE RENOVADA / COMPLETADA', 'Alta nueva, cuenta existente actualizada, llave reemplazada o cuenta de automatización completada.'],
            ['BLOQUEADA / REACTIVADA / ELIMINADA', 'Resultado de la opción 4.'],
            ['OMITIDA', 'No se tocó a propósito: la columna Detalle dice por qué (crítica, de servicio, shell no interactivo, expirada, sin contraseña, cambio ya pendiente...).'],
            ['YA EXISTÍA / NO EXISTE', 'No había nada que hacer en ese servidor.'],
            ['NO APLICADO / SIN TERMINAR', 'El servidor falló antes de aplicarlo: vuelva a lanzar sobre ese servidor.'],
        ], [0.36, 0.64]),
        P('<b>Verificado</b>: después del cambio se vuelve a leer la cuenta. SÍ = quedó como se esperaba; NO = revisar; '
          '"No disponible" = Solaris (no se lee /etc/shadow).', 'c'),
        PageBreak(),
        P('El informe de auditoría (Excel)', 'h1'),
        P('Cada auditoría deja <b>un archivo Excel</b> en /data/work/gestion_usuarios/reportes/. La plantilla 3 sola genera '
          '<font name="Mono" size="7.6">auditoria_usuarios_&lt;fecha&gt;.xlsx</font> (todas las cuentas); el último nodo de un workflow genera '
          '<font name="Mono" size="7.6">verificacion_cambio_&lt;fecha&gt;.xlsx</font> (solo las cuentas que se cambiaron). Todas las hojas tienen '
          'filtros y la fila de títulos fija; las severidades van en color (CRÍTICO rojo, ALTO naranja, MEDIO amarillo). '
          'El resumen también sale al final de la salida del job.'),
        tabla(['Hoja', 'Qué tiene'], [
            ['<b>Resumen</b>', 'Una página para leer de arriba abajo, con cada cifra explicada: cobertura, sudo (total, sin contraseña, '
             'con la propia, con la de root, limitado), hallazgos por severidad y cuántas cuentas se forzarían en bloque, con los motivos.'],
            ['<b>Tipos de hallazgo</b>', '<b>Empiece aquí.</b> Una fila por tipo de problema: qué significa, qué se recomienda y en cuántos '
             'servidores y cuentas aparece.'],
            ['<b>Usuarios</b>', 'Una fila por usuario, sumando todos los servidores: en cuántos existe y puede entrar, último acceso, '
             'hallazgo más grave, sudo y estado de su contraseña.'],
            ['<b>Plan forzar cambio contraseña</b>', 'Prepara el cambio masivo (2b, UID ≥ 1000). Por usuario: una fila con los servidores donde '
             'SÍ se le forzaría y una por cada motivo de NO, con su <b>justificación</b>, los <b>indicios de cuenta de servicio</b> y una '
             '<b>recomendación</b>: REVISAR, CONFIRMAR, APLICAR, EXCLUIDA o CORREGIR.'],
            ['<b>Servidores</b>', 'Cada servidor: hostname real, IP, sistema, totales, estado de root, versión de sudo, AllowUsers/AllowGroups. '
             'Los que no respondieron aparecen con Estado SIN RESPUESTA.'],
            ['<b>Sudo</b>', 'Cuentas con sudo: total o limitado, qué contraseña pide, comandos permitidos y de qué regla sale.'],
            ['<b>Hallazgos</b>', 'Todos los hallazgos, uno por fila, de CRÍTICO a INFO.'],
            ['<b>Detalle</b>', 'Cada cuenta en cada servidor, con todos sus datos (lo más importante en las primeras columnas).'],
            ['<b>No encontradas</b>', 'Solo en la verificación de un workflow: cuentas que el cambio indicó y ya no existen (lo esperado tras eliminar).'],
        ], [0.18, 0.82]),
        P('Estado de la contraseña', 'h2'),
        tabla(['Lo que dice', 'Qué significa'], [
            ['Activa', 'Tiene contraseña y la puede usar.'],
            ['Bloqueada (tiene contraseña, no se puede usar)', 'Se bloqueó (opción 4 o passwd -l). Al reactivarla vuelve la misma contraseña.'],
            ['Sin contraseña: entra solo con llave', 'Nunca tuvo contraseña; entra con su llave SSH (cuentas creadas con 1b).'],
            ['Sin contraseña (cuenta sin inicio de sesión)', 'Cuenta de aplicación o del sistema, sin shell interactivo.'],
            ['Sin contraseña ni llave: no puede entrar', 'No tiene forma de iniciar sesión.'],
            ['Vacía: entra SIN contraseña', 'Riesgo crítico: cualquiera entra sin clave.'],
            ['… · vencida desde FECHA', 'La contraseña caducó. Ojo: también impide entrar con llave.'],
            ['… · debe cambiarla al ingresar', 'Tiene un cambio forzado pendiente.'],
            ['… · cuenta expirada', 'La cuenta está deshabilitada por fecha.'],
        ], [0.40, 0.60]),
        P('Plan forzar cambio contraseña: por qué NO se le forzaría', 'h2'),
        P('Mismas reglas que la opción 2b en bloque. La columna dice el primer motivo que aplica: <b>Cuenta crítica</b>, <b>Cuenta de sistema '
          '(UID &lt; 1000)</b>, <b>Cuenta de servicio (lista cuentas_servicio)</b>, <b>Shell no interactivo</b>, <b>Cuenta expirada</b>, <b>Contraseña bloqueada</b>, '
          '<b>Sin contraseña: solo llave</b>, <b>Sin contraseña</b>, <b>Contraseña vacía</b> o <b>Cambio forzado ya pendiente</b> (ya debe cambiarla al ingresar). Un usuario puede tener una fila SÍ y otra NO si su situación cambia según el servidor '
          '(por ejemplo, activa en unos y bloqueada en otros).'),
        nota('<b>Indicios de cuenta de servicio</b> (configurables en roles/usuarios_auditoria/vars/main.yml): nombre genérico o de aplicación '
             '(oracle, geopos, soporte...), nombre terminado en número (caja40, tesor2), descripción de servicio ("Usuario de monitoreo") y uso de '
             'llave SSH, porque si un proceso automático entra con esa llave, el cambio forzado lo interrumpe. Una cuenta sin descripción queda '
             'en CONFIRMAR. Los indicios solo orientan: lo que excluye de verdad es la lista cuentas_servicio.'),
        nota('<b>Cómo preparar el cambio masivo:</b> abra la hoja Plan forzar cambio contraseña, filtre Recomendación = REVISAR y CONFIRMAR y '
             'revise la lista. Si aparece una cuenta de aplicación (no de una persona), pida que la agreguen a cuentas_servicio en '
             'vars/comunes.yml y vuelva a auditar.'),
        PageBreak(),
    ]


def preguntas():
    return [
        P('Preguntas frecuentes', 'h1'),
        tabla(['Pregunta', 'Respuesta'], [
            ['Me equivoqué de servidores, ¿qué hago?', 'Si aún está en Aprobación, pida que la rechacen. Si ya se aplicó, use el workflow contrario '
             '(por ejemplo, bloquear lo que se creó por error).'],
            ['¿Por qué usar el workflow y no la plantilla 1a, 2a o 4?', 'Las plantillas que cambian cuentas están pensadas para usarse desde el workflow, para que '
             'siempre haya aprobación e informe.'],
            ['¿La contraseña queda en algún registro?', 'No. AWX la guarda cifrada y no aparece en la salida del job.'],
            ['¿Puedo poner varios servidores y grupos a la vez?', 'Sí, separados por coma: GEOPOS,PPU,srv1.'],
            ['El job dice "no existen en srvX: jperez"', 'Normal si jperez no tiene cuenta en ese servidor: se omite allí.'],
            ['Pedí "sin caducidad" y "forzar cambio" a la vez', 'Se detiene: son opuestas. Deje una en NO.'],
            ['¿Qué pasa con servidores antiguos (Python 2.6)?', 'Nada distinto para usted: los mismos workflows funcionan. Lo resolvió el administrador.'],
            ['¿Dónde está el detalle técnico?', 'En docs/Arquitectura_Gestion_Usuarios.pdf: cada encuesta, qué comandos ejecuta y los IDs de AWX.'],
        ], [0.36, 0.64]),
    ]


# Páginas de cada título, tomadas de la primera pasada: [(nivel, texto, clave, página)]
TITULOS = []


def referencia(titulos):
    """Primera hoja: accesos rápidos y contenido, con enlaces (las páginas salen de la primera pasada)."""
    pag = {t[2]: t[3] for t in titulos}

    def ir(texto, destino):
        k = clave(destino)
        return ('<a href="#%s" color="#1F3A5F"><u>%s</u></a>' % (k, texto), str(pag.get(k, '')))

    def fila(quiero, destino, texto=None):
        enlace, p = ir(texto or destino, destino)
        return [quiero, enlace, p]

    salida = [
        P('Manual de uso', 'titulo'),
        P('Gestión de usuarios Linux desde AWX · Para quien crea, cambia, bloquea o revisa cuentas', 'sub'),
        P('Accesos rápidos', 'h2'),
        tabla(['Quiero…', 'Vaya a', 'Pág.'], [
            fila('Entender cómo funciona en 1 minuto', 'En pocas palabras'),
            fila('Saber qué workflow lanzar', 'Qué workflow lanzar'),
            fila('Llenar bien la encuesta', 'Cómo llenar la encuesta'),
            fila('Crear el personal de QA', 'Receta: personal de QA (catálogo soporte_qa)', 'Receta: personal de QA'),
            fila('Crear la cuenta del conector OIM', 'Receta: cuenta del conector OIM (catálogo integracion_oim)', 'Receta: cuenta del conector OIM'),
            fila('Dar sudo de soporte Geopos', 'Receta: soporte Geopos (perfil_soporte_geopos)', 'Receta: soporte Geopos'),
            fila('Ver qué permisos da cada perfil', 'Perfiles de cuenta'),
            fila('Ver qué catálogos hay y cómo se usan', 'Catálogos disponibles'),
            fila('Cambiar o quitar el sudo a una cuenta', 'Cambiar o quitar el perfil de una cuenta'),
            fila('Saber por qué se detuvo o se omitió una cuenta', 'Cuentas que el sistema protege'),
            fila('Entender el informe Excel del cambio', 'El informe del cambio (Excel)'),
            fila('Entender la auditoría', 'El informe de auditoría (Excel)'),
        ], [0.45, 0.47, 0.08]),
        Spacer(1, 8),
        P('Contenido', 'h2'),
    ]
    filas = []
    for nivel, texto, k, p in titulos:
        if nivel == 1:
            filas.append(['<a href="#%s" color="#1F3A5F">%s</a>' % (k, html.escape(texto)), str(p)])
        elif k.startswith(('s_receta', 's_catalogos_disponibles', 's_perfiles_de_cuenta')):
            filas.append(['&nbsp;&nbsp;&nbsp;&nbsp;<a href="#%s" color="#1F3A5F">%s</a>' % (k, html.escape(texto)), str(p)])
    salida += [
        tabla(['Sección', 'Pág.'], filas or [['(se completa en la segunda pasada)', '']], [0.92, 0.08]),
        Spacer(1, 6),
        nota('<b>Para navegar:</b> los textos subrayados y el contenido son enlaces. El panel de <b>marcadores</b> del visor de PDF '
             'muestra todas las secciones, y el pie de cada página tiene un enlace para volver a esta hoja.'),
        PageBreak(),
    ]
    return salida


class Documento(SimpleDocTemplate):
    """Registra cada título h1/h2: destino para los enlaces, marcador del PDF y página para el contenido."""

    def afterFlowable(self, f):
        if isinstance(f, Paragraph) and f.style.name in ('h1', 'h2') and self.page > 1:
            texto = _sin_marcas(f.getPlainText())
            nivel = 1 if f.style.name == 'h1' else 2
            k = clave(texto)
            self.canv.bookmarkHorizontalAbsolute(k, self.frame._y + f.height + 6)
            self.canv.addOutlineEntry(texto, k, level=nivel - 1, closed=True)
            self.titulos.append((nivel, texto, k, self.page))


def pie(canvas, doc):
    canvas.saveState()
    canvas.setFont('Texto', 7.5)
    canvas.setFillColor(arq.GRIS)
    if doc.page == 1:
        canvas.bookmarkPage('indice')
        canvas.showOutline()  # el visor abre con el panel de marcadores
        canvas.drawString(16 * mm, 9 * mm, 'gestion_usuarios · Manual de uso')
    else:
        texto = 'gestion_usuarios · Manual de uso · ← Volver al índice'
        canvas.drawString(16 * mm, 9 * mm, texto)
        ancho = canvas.stringWidth(texto, 'Texto', 7.5)
        canvas.linkRect('', 'indice', (16 * mm, 8 * mm, 16 * mm + ancho, 12 * mm), relative=0, thickness=0)
    canvas.drawRightString(A4[0] - 16 * mm, 9 * mm, 'Página %d' % doc.page)
    canvas.restoreState()


def construir(titulos):
    historia = (referencia(titulos) + portada() + encuesta() + [PageBreak()] + protecciones() + ejemplos() + perfiles()
                + llaves_y_resultados() + preguntas())
    doc = Documento(SALIDA, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=15 * mm, bottomMargin=16 * mm,
                    title='Manual de uso de gestion_usuarios', author='gestion_usuarios', subject='Cómo usar los workflows de usuarios en AWX')
    doc.titulos = []
    doc.build(historia, onFirstPage=pie, onLaterPages=pie)
    return doc.titulos


def main():
    # Dos pasadas: la primera averigua en qué página queda cada título; la segunda escribe el contenido con esas páginas.
    # La hoja de referencia termina con salto de página, así que su largo no mueve las demás.
    titulos = construir([])
    final = construir(titulos)
    assert [t[3] for t in final] == [t[3] for t in titulos], 'las páginas cambiaron entre pasadas'
    print('Generado:', SALIDA)


if __name__ == '__main__':
    main()
