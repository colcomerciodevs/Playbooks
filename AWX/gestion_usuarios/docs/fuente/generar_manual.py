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
         'Se aplica a las cuentas de persona. Se <b>omiten solas</b>: root y demás críticas, pos y postgres, cuentas que solo entran con llave, '
         'cuentas sin shell y cuentas expiradas (deshabilitadas por fecha). El informe final lista a quién se le aplicó. <b>Consejo:</b> lance antes la auditoría y, en la hoja '
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
            ['OMITIDA', 'No se tocó a propósito: la columna Detalle dice por qué (crítica, de servicio, shell no interactivo, expirada, sin contraseña...).'],
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
          '<b>Sin contraseña: solo llave</b>, <b>Sin contraseña</b> o <b>Contraseña vacía</b>. Un usuario puede tener una fila SÍ y otra NO si su situación cambia según el servidor '
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
