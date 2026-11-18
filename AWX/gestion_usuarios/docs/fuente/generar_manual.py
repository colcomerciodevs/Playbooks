#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Genera docs/Manual_de_Uso.pdf: guía para quien lanza los workflows en AWX.

Reutiliza estilos, IDs de AWX y la tabla de perfiles de generar_arquitectura.py, y lee
las cuentas críticas y de servicio de vars/comunes.yml, para no repetir datos.

Uso:  python3 -B docs/fuente/generar_manual.py   (requiere reportlab)
"""
import importlib.util
import os
import sys

import yaml

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, PageBreak, SimpleDocTemplate, Spacer

sys.dont_write_bytecode = True
AQUI = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('arq', os.path.join(AQUI, 'generar_arquitectura.py'))
arq = importlib.util.module_from_spec(spec)
spec.loader.exec_module(arq)
P, tabla, nota, Flujo, ID = arq.P, arq.tabla, arq.nota, arq.Flujo, arq.AWX_ID
SALIDA = os.path.join(arq.RAIZ, 'docs', 'Manual_de_Uso.pdf')
COMUNES = yaml.safe_load(open(os.path.join(arq.RAIZ, 'vars', 'comunes.yml'), encoding='utf-8'))

# Colores de las columnas de resultado
DETIENE = '<font color="#B3261E"><b>SE DETIENE</b></font>'
OMITE = '<font color="#8A5A00"><b>SE OMITE</b></font>'
APLICA = '<font color="#1E6B3A"><b>SE APLICA</b></font>'


def wf(nombre):
    return '<b>%s</b> (ID %d)' % (nombre, ID[nombre])


def portada():
    return [
        P('Manual de uso', 'titulo'),
        P('Gestión de usuarios Linux desde AWX · Para quien crea, cambia, bloquea o revisa cuentas', 'sub'),
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
         'Se aplica a las cuentas de persona. Se <b>omiten solas</b>: root y demás críticas, pos y postgres, cuentas que solo entran con llave '
         'y cuentas sin shell. El informe final lista a quién se le aplicó. <b>Consejo:</b> lance antes la auditoría y mire la columna '
         '"Se le forzaría el cambio".'),
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


def perfiles():
    return [
        P('Perfiles de cuenta: qué permisos recibe', 'h1'),
        P('Al crear una cuenta se elige su <b>perfil</b>. El perfil decide qué puede hacer como administrador (sudo). No se escriben '
          'comandos a mano: si ningún perfil sirve, pida que se agregue uno.'),
        arq.perfiles_tabla(),
        Spacer(1, 6),
        tabla(['Situación', 'Qué pasa'], [
            ['Catálogo con perfil', 'Manda el perfil del catálogo. Ejemplo: admins_linux siempre da perfil_admin_linux, aunque la encuesta diga otra cosa.'],
            ['Un servicio de Geopos no está en un servidor', 'Ese comando se omite en ese servidor y el resultado lo avisa. El resto sí queda.'],
            ['Quitar el sudo a alguien', 'Workflow de crear con su usuario, perfil_estandar y "Actualizar usuarios que ya existen" = SI.'],
            ['Bloquear o eliminar', 'También se le quita la regla de sudo.'],
            ['Reactivar', '<b>No</b> le devuelve el sudo. Vuelva a aplicar su perfil con el workflow de crear y Actualizar = SI.'],
        ], [0.33, 0.67]),
        PageBreak(),
    ]


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
            ['El nodo 2 en rojo sin ese mensaje', 'Falló un servidor mientras se aplicaba. Avise a un administrador con el número de job.'],
            ['Un servidor como "unreachable"', 'No respondió. Se omitió; los demás siguieron. Reintente solo ese servidor más tarde.'],
            ['Todo en verde', 'Revise el informe del nodo 3 (abajo).'],
        ], [0.38, 0.62]),
        Spacer(1, 5),
        P('El informe de verificación', 'h2'),
        P('El último nodo revisa <b>solo las cuentas que se cambiaron</b> y deja dos archivos en /data/work/gestion_usuarios/reportes/: '
          '<font name="Mono" size="7.6">verificacion_cambio_&lt;fecha&gt;.html</font> (para leer) y <font name="Mono" size="7.6">.csv</font> (para Excel). '
          'Muestran la operación, el ticket y, por cada servidor (nombre en el inventario, hostname real e IP) y cada cuenta, su estado: '
          'contraseña, caducidad, bloqueo, sudo y acceso SSH. A root y a las cuentas con UID 0 no se les marca su sudo como hallazgo, porque ya son administradoras. '
          'La sección "Cuentas no encontradas" confirma, por ejemplo, que una cuenta eliminada ya no existe. El resumen también sale al final '
          'de la salida del job.'),
        P('La plantilla 3 sola hace la <b>auditoría general</b> (todas las cuentas) y genera auditoria_usuarios_&lt;fecha&gt;.'),
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


def pie(canvas, doc):
    canvas.saveState()
    canvas.setFont('Texto', 7.5)
    canvas.setFillColor(arq.GRIS)
    canvas.drawString(16 * mm, 9 * mm, 'gestion_usuarios · Manual de uso')
    canvas.drawRightString(A4[0] - 16 * mm, 9 * mm, 'Página %d' % doc.page)
    canvas.restoreState()


def main():
    historia = portada() + encuesta() + [PageBreak()] + protecciones() + ejemplos() + perfiles() + llaves_y_resultados() + preguntas()
    doc = SimpleDocTemplate(SALIDA, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=15 * mm, bottomMargin=16 * mm,
                            title='Manual de uso de gestion_usuarios', author='gestion_usuarios', subject='Cómo usar los workflows de usuarios en AWX')
    doc.build(historia, onFirstPage=pie, onLaterPages=pie)
    print('Generado:', SALIDA)


if __name__ == '__main__':
    main()
