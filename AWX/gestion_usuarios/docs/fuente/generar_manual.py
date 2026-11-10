#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Genera docs/Manual_Gestion_Usuarios_AWX.pdf

Las preguntas de las encuestas se toman de awx/generar_encuestas.py y los
conflictos de IP se calculan desde inventario/*.ini, así el manual siempre
coincide con el proyecto.

Uso:   python3 docs/fuente/generar_manual.py
Requiere: Python 3 + playwright (pip install playwright && playwright install chromium).
Sin playwright se genera solo docs/fuente/manual.html: ábralo en Chrome y use
Imprimir -> Guardar como PDF (tamaño Carta, márgenes predeterminados, con gráficos de fondo).
"""
import collections
import datetime
import html
import importlib.util
import os
import re

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, '..', '..'))
SALIDA_HTML = os.path.join(AQUI, 'manual.html')
SALIDA_PDF = os.path.join(RAIZ, 'docs', 'Manual_Gestion_Usuarios_AWX.pdf')
VERSION = '1.0'

spec = importlib.util.spec_from_file_location('enc', os.path.join(RAIZ, 'awx', 'generar_encuestas.py'))
enc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(enc)
ENCUESTAS = enc.ENCUESTAS

e = html.escape


# ---------------------------------------------------------------------------
# Datos calculados
# ---------------------------------------------------------------------------
def resumen_inventario(ruta):
    """Grupos del inventario con su cantidad de servidores y usuario de conexión."""
    grupos, orden, grupo = {}, [], None
    for linea in open(ruta, encoding='utf-8', errors='replace'):
        l = linea.split('#')[0].strip()
        if not l or l.startswith(';'):
            continue
        m = re.match(r'^\[(.+)\]$', l)
        if m:
            grupo = m.group(1)
            if ':' not in grupo and grupo not in grupos:
                grupos[grupo] = []
                orden.append(grupo)
            continue
        if grupo and ':' not in grupo:
            partes = l.split()
            vars_host = dict(p.split('=', 1) for p in partes[1:] if '=' in p)
            grupos[grupo].append((partes[0], vars_host))
    filas = []
    for g in orden:
        gv = os.path.join(os.path.dirname(ruta), 'group_vars', g + '.yml')
        usuario_grupo = None
        if os.path.isfile(gv):
            m = re.search(r'^ansible_user:\s*(\S+)', open(gv, encoding='utf-8').read(), re.M)
            usuario_grupo = m.group(1) if m else None
        usuarios = collections.Counter(v.get('ansible_user', usuario_grupo or '(credencial de AWX)') for _, v in grupos[g])
        locales = [h for h, v in grupos[g] if v.get('ansible_connection') == 'local']
        filas.append((g, len(grupos[g]), usuarios, locales))
    return filas


# ---------------------------------------------------------------------------
# Piezas de HTML
# ---------------------------------------------------------------------------
def tabla(encabezados, filas, clase=''):
    h = ''.join('<th>%s</th>' % c for c in encabezados)
    b = ''.join('<tr>%s</tr>' % ''.join('<td>%s</td>' % c for c in f) for f in filas)
    return '<table class="%s"><thead><tr>%s</tr></thead><tbody>%s</tbody></table>' % (clase, h, b)


def campos(filas):
    """Tabla de dos columnas Campo -> Valor para pantallas de AWX."""
    return tabla(['Campo en AWX', 'Qué poner'], filas, 'campos')


def nota(tipo, titulo, texto):
    iconos = {'info': 'i', 'alerta': '!', 'peligro': '!', 'ok': '✓'}
    return ('<div class="nota %s"><div class="ico">%s</div><div><b class="tt">%s</b>%s</div></div>'
            % (tipo, iconos[tipo], titulo, texto))


def pasos(items):
    return '<ol class="pasos">%s</ol>' % ''.join('<li>%s</li>' % i for i in items)


def formulario(clave, respuestas, titulo_ejemplo):
    """Maqueta de la encuesta de AWX diligenciada."""
    encuesta = ENCUESTAS[clave]
    filas = []
    for q in encuesta['spec']:
        if q['variable'] not in respuestas:
            continue
        valor = respuestas[q['variable']]
        if q['type'] == 'password':
            control = '<div class="ctl pwd">••••••••••••</div>'
        elif q['type'] == 'multiplechoice':
            control = '<div class="ctl sel">%s<span>▾</span></div>' % e(valor)
        elif q['type'] == 'textarea':
            control = '<div class="ctl area">%s</div>' % '<br>'.join(e(x) for x in valor.split('\n'))
        else:
            control = '<div class="ctl">%s</div>' % e(str(valor))
        req = '<i>*</i>' if q['required'] else ''
        filas.append('<div class="fila"><label>%s%s</label>%s</div>' % (e(q['question_name']), req, control))
    omitidas = len(encuesta['spec']) - len(filas)
    pie = ('<div class="pie">Las %d preguntas restantes se dejan con su valor por defecto.</div>' % omitidas) if omitidas else ''
    return ('<div class="form"><div class="barra"><span class="pt"></span><span class="pt"></span><span class="pt"></span>'
            'Lanzar: %s</div><div class="sub">%s</div>%s%s<div class="btn">Lanzar ▸</div></div>'
            % (e(encuesta['name']), e(titulo_ejemplo), ''.join(filas), pie))


def chip(sev):
    return '<span class="sev %s">%s</span>' % (sev, sev.replace('CRITICO', 'CRÍTICO'))


# ---------------------------------------------------------------------------
# Diagramas (SVG en línea)
# ---------------------------------------------------------------------------
SVG_FLUJO = '''
<svg viewBox="0 0 680 230" class="diag" role="img" aria-label="Flujo de una ejecución">
 <defs><marker id="fl" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#5b6475"/></marker></defs>
 <g font-family="Inter" font-size="12.5" text-anchor="middle">
  <rect x="4" y="30" width="120" height="74" rx="10" fill="#eef3fb" stroke="#b9c8e4"/>
  <text x="64" y="58" font-weight="600" fill="#1d2a44">Operador</text>
  <text x="64" y="76" fill="#46526a">llena la</text><text x="64" y="92" fill="#46526a">encuesta</text>
  <line x1="124" y1="67" x2="160" y2="67" stroke="#5b6475" stroke-width="1.6" marker-end="url(#fl)"/>
  <rect x="162" y="30" width="150" height="74" rx="10" fill="#1f3a68"/>
  <text x="237" y="52" font-size="11" fill="#b9cbf0">PASO 1 · en AWX</text>
  <text x="237" y="72" font-weight="600" fill="#fff">Validar respuestas</text>
  <text x="237" y="90" fill="#d7e1f5">(localhost)</text>
  <line x1="312" y1="67" x2="348" y2="67" stroke="#5b6475" stroke-width="1.6" marker-end="url(#fl)"/>
  <text x="330" y="58" font-size="10.5" fill="#2f7d4a">OK</text>
  <rect x="350" y="30" width="160" height="74" rx="10" fill="#1f3a68"/>
  <text x="430" y="52" font-size="11" fill="#b9cbf0">PASO 2 · en servidores</text>
  <text x="430" y="72" font-weight="600" fill="#fff">Aplicar cambios</text>
  <text x="430" y="90" fill="#d7e1f5">solo en el «objetivo»</text>
  <line x1="510" y1="67" x2="546" y2="67" stroke="#5b6475" stroke-width="1.6" marker-end="url(#fl)"/>
  <rect x="548" y="30" width="128" height="74" rx="10" fill="#e8f4ec" stroke="#a9d3b6"/>
  <text x="612" y="52" font-size="11" fill="#2f7d4a">PASO 3</text>
  <text x="612" y="72" font-weight="600" fill="#1d3a26">Resumen</text>
  <text x="612" y="90" fill="#3b5a44">y reporte</text>
  <line x1="237" y1="104" x2="237" y2="150" stroke="#b3261e" stroke-width="1.6" stroke-dasharray="4 3" marker-end="url(#fl)"/>
  <text x="250" y="132" font-size="10.5" text-anchor="start" fill="#b3261e">dato inválido</text>
  <rect x="122" y="152" width="230" height="62" rx="10" fill="#fdecea" stroke="#efb3ad"/>
  <text x="237" y="177" font-weight="600" fill="#8c1d18">El job se detiene</text>
  <text x="237" y="196" fill="#8c1d18">Ningún servidor se modifica</text>
 </g>
</svg>'''

SVG_AWX = '''
<svg viewBox="0 0 680 270" class="diag" role="img" aria-label="Piezas de AWX">
 <defs><marker id="fa" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#5b6475"/></marker></defs>
 <g font-family="Inter" font-size="12.5">
  <g>
   <rect x="4" y="10" width="200" height="66" rx="10" fill="#eef3fb" stroke="#b9c8e4"/>
   <circle cx="26" cy="32" r="12" fill="#1f3a68"/><text x="26" y="36.5" fill="#fff" font-size="12" font-weight="700" text-anchor="middle">1</text>
   <text x="46" y="37" font-weight="600" fill="#1d2a44">Credenciales</text>
   <text x="18" y="60" fill="#46526a" font-size="11.5">Git · Máquina (SSH) · SMTP</text>
  </g>
  <g>
   <rect x="4" y="100" width="200" height="66" rx="10" fill="#eef3fb" stroke="#b9c8e4"/>
   <circle cx="26" cy="122" r="12" fill="#1f3a68"/><text x="26" y="126.5" fill="#fff" font-size="12" font-weight="700" text-anchor="middle">2</text>
   <text x="46" y="127" font-weight="600" fill="#1d2a44">Proyecto</text>
   <text x="18" y="150" fill="#46526a" font-size="11.5">El repositorio Git</text>
  </g>
  <g>
   <rect x="4" y="190" width="200" height="66" rx="10" fill="#eef3fb" stroke="#b9c8e4"/>
   <circle cx="26" cy="212" r="12" fill="#1f3a68"/><text x="26" y="216.5" fill="#fff" font-size="12" font-weight="700" text-anchor="middle">3</text>
   <text x="46" y="217" font-weight="600" fill="#1d2a44">Inventarios</text>
   <text x="18" y="240" fill="#46526a" font-size="11.5">Leídos desde el proyecto</text>
  </g>
  <line x1="204" y1="43" x2="262" y2="110" stroke="#5b6475" stroke-width="1.5" marker-end="url(#fa)"/>
  <line x1="204" y1="133" x2="262" y2="133" stroke="#5b6475" stroke-width="1.5" marker-end="url(#fa)"/>
  <line x1="204" y1="223" x2="262" y2="156" stroke="#5b6475" stroke-width="1.5" marker-end="url(#fa)"/>
  <rect x="264" y="56" width="216" height="156" rx="12" fill="#1f3a68"/>
  <circle cx="288" cy="80" r="12" fill="#fff"/><text x="288" y="84.5" fill="#1f3a68" font-size="12" font-weight="700" text-anchor="middle">4</text>
  <text x="308" y="85" font-weight="600" fill="#fff">Plantillas de trabajo</text>
  <text x="280" y="106" fill="#d7e1f5" font-size="11.5">Una por opción (1, 2, 3 y 4)</text>
  <rect x="280" y="122" width="184" height="72" rx="8" fill="#2c4f8a"/>
  <circle cx="300" cy="142" r="11" fill="#ffd47a"/><text x="300" y="146.5" fill="#1f3a68" font-size="12" font-weight="700" text-anchor="middle">5</text>
  <text x="318" y="147" font-weight="600" fill="#fff">Encuesta</text>
  <text x="292" y="170" fill="#d7e1f5" font-size="11.5">El formulario que</text>
  <text x="292" y="185" fill="#d7e1f5" font-size="11.5">diligencia el operador</text>
  <line x1="480" y1="134" x2="522" y2="134" stroke="#5b6475" stroke-width="1.5" marker-end="url(#fa)"/>
  <rect x="524" y="88" width="152" height="92" rx="10" fill="#e8f4ec" stroke="#a9d3b6"/>
  <circle cx="546" cy="110" r="12" fill="#2f7d4a"/><text x="546" y="114.5" fill="#fff" font-size="12" font-weight="700" text-anchor="middle">6</text>
  <text x="566" y="115" font-weight="600" fill="#1d3a26">Permisos</text>
  <text x="538" y="140" fill="#3b5a44" font-size="11.5">Equipos que pueden</text>
  <text x="538" y="156" fill="#3b5a44" font-size="11.5">ejecutar cada</text>
  <text x="538" y="172" fill="#3b5a44" font-size="11.5">plantilla</text>
 </g>
</svg>'''

CSS = r'''
@page { size: Letter; margin: 20mm 17mm 18mm 17mm;
  @top-left { content: "Gestión de usuarios Linux con Ansible y AWX"; font: 600 8pt Inter; color: #7a8396; }
  @top-right { content: "Manual de implementación y operación"; font: 8pt Inter; color: #7a8396; }
  @bottom-right { content: counter(page) " / " counter(pages); font: 600 8pt Inter; color: #7a8396; }
  @bottom-left { content: "Proyecto gestion_usuarios · v__VERSION__"; font: 8pt Inter; color: #9aa1af; } }
@page :first { margin: 0; @top-left{content:none} @top-right{content:none} @bottom-right{content:none} @bottom-left{content:none} }
:root { --az: #1f3a68; --az2: #2c4f8a; --tx: #1c2433; --mut: #5b6475; --bd: #d9dee7; --fondo: #f4f6fa; }
* { box-sizing: border-box; }
html { font: 10.2pt/1.5 Inter, "DejaVu Sans", sans-serif; color: var(--tx); -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { margin: 0; }
h1 { font: 700 21pt/1.2 "Inter Display", Inter, sans-serif; color: var(--az); margin: 0 0 4mm; break-before: page; letter-spacing: -0.01em; }
h1 .num { display: inline-block; min-width: 11mm; color: #9fb3d8; }
h2 { font: 650 13.5pt/1.3 Inter; color: var(--az); margin: 7mm 0 2.5mm; break-after: avoid; }
h3 { font: 650 11pt/1.3 Inter; margin: 5mm 0 2mm; break-after: avoid; color: #24314d; }
p { margin: 0 0 2.6mm; } ul { margin: 0 0 3mm; padding-left: 5mm; } li { margin: 0 0 1.2mm; }
.lead { font-size: 11pt; color: #3a4558; max-width: 165mm; }
code, pre { font-family: "DejaVu Sans Mono", monospace; }
code { font-size: 8.6pt; background: #eef1f6; padding: 0.2mm 1.2mm; border-radius: 1mm; color: #23304a; }
pre { font-size: 8.3pt; line-height: 1.45; background: #f3f5f9; border: 1px solid var(--bd); border-left: 3px solid var(--az2); border-radius: 2mm; padding: 3mm 4mm; white-space: pre-wrap; break-inside: avoid; margin: 0 0 3.5mm; }
table { width: 100%; border-collapse: collapse; margin: 0 0 4mm; font-size: 9pt; break-inside: auto; }
thead { display: table-header-group; }
tr { break-inside: avoid; }
th { background: var(--az); color: #fff; font-weight: 600; text-align: left; padding: 1.8mm 2.4mm; }
td { padding: 1.7mm 2.4mm; border-bottom: 1px solid var(--bd); vertical-align: top; }
tbody tr:nth-child(even) td { background: #f7f8fb; }
table.campos td:first-child { width: 33%; font-weight: 600; color: #2a3550; }
table.compacta { font-size: 8.3pt; }
table.anexo td:nth-child(1){width:4%} table.anexo td:nth-child(2){width:45%} table.anexo td:nth-child(3){width:26%} table.anexo td:nth-child(4){width:14%}
table.anexo code{font-size:7.6pt} table.compacta td, table.compacta th { padding: 1.2mm 2mm; }
.nota { display: flex; gap: 3mm; border-radius: 2.5mm; padding: 3mm 4mm; margin: 0 0 4mm; break-inside: avoid; font-size: 9.6pt; }
.nota .ico { flex: 0 0 6mm; height: 6mm; border-radius: 50%; color: #fff; font-weight: 700; text-align: center; line-height: 6mm; font-size: 9.5pt; }
.nota .tt { display: block; margin-bottom: 0.6mm; }
.nota.info { background: #edf3fc; border: 1px solid #c7d7f1; } .nota.info .ico { background: #2c5fb8; }
.nota.alerta { background: #fff5e3; border: 1px solid #f1d39b; } .nota.alerta .ico { background: #c27a00; }
.nota.peligro { background: #fdeceb; border: 1px solid #f0bcb7; } .nota.peligro .ico { background: #b3261e; }
.nota.ok { background: #eaf6ee; border: 1px solid #b9dfc5; } .nota.ok .ico { background: #2f7d4a; }
ol.pasos { list-style: none; counter-reset: p; padding: 0; margin: 0 0 4mm; }
ol.pasos > li { counter-increment: p; position: relative; padding: 0 0 0 10mm; margin: 0 0 2.4mm; min-height: 7mm; }
ol.pasos > li::before { content: counter(p); position: absolute; left: 0; top: -0.3mm; width: 6.4mm; height: 6.4mm; border-radius: 50%; background: var(--az); color: #fff; font-weight: 700; font-size: 9pt; text-align: center; line-height: 6.4mm; }
.diag { width: 100%; height: auto; display: block; margin: 2mm 0 5mm; }
.tarjetas { display: grid; grid-template-columns: 1fr 1fr; gap: 4mm; margin: 2mm 0 5mm; }
.tarjeta { border: 1px solid var(--bd); border-radius: 3mm; padding: 4mm; break-inside: avoid; background: #fff; }
.tarjeta .n { display: inline-block; width: 8mm; height: 8mm; border-radius: 2mm; background: var(--az); color: #fff; font-weight: 700; text-align: center; line-height: 8mm; margin-right: 2mm; }
.tarjeta h4 { display: inline; font-size: 11pt; margin: 0; color: var(--az); }
.tarjeta p { margin: 2.5mm 0 1.5mm; font-size: 9.4pt; color: #3a4558; }
.tarjeta .pb { font-size: 8.2pt; color: var(--mut); }
.form { border: 1px solid #c9d0dc; border-radius: 3mm; overflow: hidden; margin: 2mm 0 5mm; break-inside: avoid; box-shadow: 0 1mm 3mm rgba(20,40,80,.08); background: #fff; }
.form .barra { background: #263043; color: #e8ecf3; font-size: 9pt; font-weight: 600; padding: 2mm 4mm; }
.form .pt { display: inline-block; width: 2.2mm; height: 2.2mm; border-radius: 50%; background: #5c677d; margin-right: 1.3mm; }
.form .sub { background: #f2f4f8; color: var(--mut); font-size: 8.6pt; padding: 1.6mm 4mm; border-bottom: 1px solid #e1e5ec; }
.form .fila { display: grid; grid-template-columns: 62mm 1fr; gap: 3mm; padding: 1.7mm 4mm; align-items: center; }
.form label { font-size: 8.8pt; font-weight: 600; color: #2b3650; } .form label i { color: #c0392b; font-style: normal; margin-left: 0.6mm; }
.form .ctl { border: 1px solid #c7cedb; border-radius: 1.5mm; padding: 1.3mm 2.5mm; font: 8.8pt "DejaVu Sans Mono", monospace; background: #fbfcfe; min-height: 6.5mm; color: #17305e; }
.form .ctl.sel { display: flex; justify-content: space-between; font-family: Inter; font-weight: 600; }
.form .ctl.sel span { color: #8090a8; }
.form .ctl.pwd { letter-spacing: 0.4mm; color: #556; }
.form .ctl.area { line-height: 1.5; }
.form .pie { font-size: 8.2pt; color: var(--mut); padding: 1mm 4mm 0; font-style: italic; }
.form .btn { margin: 2.5mm 4mm 3mm auto; width: max-content; background: #2c5fb8; color: #fff; font-weight: 600; font-size: 8.8pt; padding: 1.5mm 5mm; border-radius: 1.5mm; }
.sev { display: inline-block; padding: 0.2mm 2.2mm; border-radius: 9mm; font-size: 7.8pt; font-weight: 700; white-space: nowrap; }
.sev.CRITICO { background: #fde3e1; color: #a3231b; } .sev.ALTO { background: #ffecd6; color: #a15400; }
.sev.MEDIO { background: #fff5c9; color: #7d6300; } .sev.BAJO { background: #e1f2e5; color: #2a6435; } .sev.INFO { background: #e6ebf2; color: #45546b; }
.dos { display: grid; grid-template-columns: 1fr 1fr; gap: 5mm; }
.captura { width: 100%; border: 1px solid var(--bd); border-radius: 2mm; display: block; margin: 1mm 0 1.5mm; }
.pie-img { font-size: 8.4pt; color: var(--mut); margin-bottom: 4mm; }
.ruta { font-family: "DejaVu Sans Mono", monospace; font-size: 8.6pt; }
/* Portada */
.portada { height: 279.4mm; width: 215.9mm; background: #172c52; color: #fff; position: relative; padding: 32mm 22mm; overflow: hidden; }
.portada .franja { position: absolute; right: -40mm; top: -30mm; width: 150mm; height: 150mm; border-radius: 50%; background: #213d6e; }
.portada .franja2 { position: absolute; right: 20mm; bottom: -70mm; width: 120mm; height: 120mm; border-radius: 50%; background: #1c3562; }
.portada .eti { position: relative; font-size: 10pt; letter-spacing: 0.25em; text-transform: uppercase; color: #9fb7e3; font-weight: 600; }
.portada .tit { position: relative; display: block; font: 700 33pt/1.12 "Inter Display", Inter; margin: 8mm 0 6mm; letter-spacing: -0.015em; }
.portada .sub { position: relative; font-size: 13pt; color: #cdd9ef; max-width: 140mm; line-height: 1.45; }
.portada .ops { position: relative; margin-top: 22mm; display: grid; grid-template-columns: 1fr 1fr; gap: 4mm; max-width: 160mm; }
.portada .op { border: 1px solid #3a5a90; border-radius: 3mm; padding: 4mm 5mm; background: rgba(255,255,255,0.04); }
.portada .op b { display: block; font-size: 22pt; color: #ffd47a; line-height: 1; margin-bottom: 1.5mm; }
.portada .op span { font-size: 10.5pt; color: #e6ecf7; }
.portada .meta { position: absolute; left: 22mm; bottom: 24mm; font-size: 9.5pt; color: #9fb7e3; line-height: 1.6; }
/* Índice */
.indice { break-before: page; }
.indice h1 { break-before: avoid; }
.indice ol { list-style: none; padding: 0; margin: 0; }
.indice li { display: flex; align-items: baseline; padding: 1.5mm 0; border-bottom: 1px dotted #c9cfda; font-size: 10.6pt; }
.indice li .t { flex: 1; } .indice li .n { color: var(--az); font-weight: 600; width: 10mm; }
.indice li .pg { font-weight: 600; color: var(--mut); }
.indice li.sec { padding-left: 10mm; font-size: 9.6pt; color: #3a4558; border-bottom-style: none; padding-top: 0.5mm; padding-bottom: 0.5mm; }
.indice a { color: inherit; text-decoration: none; }
'''


def construir(paginas=None):
    paginas = paginas or {}

    def pg(ancla):
        return str(paginas.get(ancla, ''))

    grupos_inv = resumen_inventario(os.path.join(RAIZ, 'inventario', 'hosts.ini'))
    total_hosts = sum(n for _, n, _, _ in grupos_inv)
    hosts_locales = [h for _, _, _, loc in grupos_inv for h in loc]

    capitulos = [
        ('c1', '1', 'Qué hace el proyecto', []),
        ('c2', '2', 'Cómo funciona una ejecución', []),
        ('c3', '3', 'Antes de empezar', []),
        ('c4', '4', 'Estructura del proyecto', []),
        ('c5', '5', 'Configurar AWX paso a paso', [('c5p1', 'Paso 1 · Subir el proyecto a Git'), ('c5p2', 'Paso 2 · Credenciales'),
                                                  ('c5p3', 'Paso 3 · Proyecto'), ('c5p4', 'Paso 4 · Inventario'),
                                                  ('c5p5', 'Paso 5 · Plantillas de trabajo'), ('c5p6', 'Paso 6 · Encuestas'),
                                                  ('c5p7', 'Paso 7 · Permisos')]),
        ('c6', '6', 'Uso diario: cómo diligenciar cada opción', [('c61', 'Opción 1 · Crear usuarios'), ('c62', 'Opción 2 · Cambiar contraseña'),
                                                                ('c63', 'Opción 3 · Auditoría'), ('c64', 'Opción 4 · Bloquear o eliminar')]),
        ('c7', '7', 'Cómo leer la auditoría', []),
        ('c8', '8', 'Seguridad y buenas prácticas', []),
        ('c9', '9', 'Solución de problemas', []),
        ('c10', '10', 'Uso por línea de comandos', []),
        ('aA', 'A', 'Anexo A · Todas las preguntas de las encuestas', []),
        ('aB', 'B', 'Anexo B · Grupos del inventario', []),
        ('aC', 'C', 'Anexo C · Cambios frente a los proyectos anteriores', []),
    ]
    indice = []
    for ancla, num, titulo, subs in capitulos:
        indice.append('<li><span class="n">%s</span><span class="t"><a href="#%s">%s</a></span><span class="pg">%s</span></li>'
                      % (num, ancla, e(titulo), pg(ancla)))
        for sa, st in subs:
            indice.append('<li class="sec"><span class="t"><a href="#%s">%s</a></span><span class="pg">%s</span></li>' % (sa, e(st), pg(sa)))

    def h1(ancla):
        for a, num, titulo, _ in capitulos:
            if a == ancla:
                return '<h1 id="%s"><span class="num">%s</span>%s</h1>' % (a, num, e(titulo.split('· ')[-1]) if a.startswith('a') else e(titulo))

    # --- Anexo A
    tipos = {'text': 'Texto', 'textarea': 'Área de texto', 'password': 'Contraseña', 'integer': 'Entero',
             'multiplechoice': 'Opción múltiple'}
    anexo_a = []
    for clave, enc_ in ENCUESTAS.items():
        filas = []
        for i, q in enumerate(enc_['spec'], 1):
            opciones = ' / '.join(q['choices']) if q['choices'] else ''
            defecto = '' if q['default'] in ('', None) else str(q['default'])
            filas.append([
                str(i),
                '<b>%s</b>%s<br><span style="color:#5b6475">%s</span>' % (
                    e(q['question_name']), ' <span style="color:#c0392b">*</span>' if q['required'] else '',
                    e(q['question_description']).replace('\n', '<br>')),
                '<code>%s</code>' % q['variable'].replace('_', '_<wbr>'),
                tipos.get(q['type'], q['type']) + (('<br><span style="color:#5b6475">%s</span>' % e(opciones)) if opciones else ''),
                '<code>%s</code>' % e(defecto) if defecto else '—'])
        anexo_a.append('<h3>%s</h3>' % e(enc_['name']))
        anexo_a.append(tabla(['#', 'Pregunta y ayuda (* = obligatoria)', 'Variable', 'Tipo', 'Por defecto'], filas, 'compacta anexo'))

    # --- Anexo B
    filas_b = []
    for g, n, usuarios, locales in grupos_inv:
        u = ', '.join(('<code>%s</code>' % e(k) if not k.startswith('(') else e(k)) + (' (%d)' % c if len(usuarios) > 1 else '')
                      for k, c in usuarios.most_common())
        nota_g = ('⚠ ' + ', '.join(locales) + ': conexión local') if locales else ''
        filas_b.append(['<b>%s</b>' % e(g), str(n), u, nota_g])
    anexo_b = tabla(['Grupo (valor para «Servidores o grupo»)', 'Servidores', 'Usuario de conexión', 'Observación'], filas_b, 'compacta')

    H = []
    a = H.append
    # ======================= PORTADA =======================
    a('''<section class="portada"><div class="franja"></div><div class="franja2"></div>
<div class="eti">Manual de implementación y operación</div>
<div class="tit">Gestión de usuarios Linux<br>con Ansible y AWX</div>
<div class="sub">Crear cuentas, cambiar contraseñas con política «nunca caduca», auditar permisos sudo y dar de baja usuarios, todo desde encuestas de AWX.</div>
<div class="ops">
 <div class="op"><b>1</b><span>Crear usuarios<br>con contraseña o con llave SSH</span></div>
 <div class="op"><b>2</b><span>Cambiar contraseña<br>con opción «nunca caduca»</span></div>
 <div class="op"><b>3</b><span>Auditoría de usuarios<br>y permisos sudo</span></div>
 <div class="op"><b>4</b><span>Bloquear o eliminar<br>usuarios</span></div>
</div>
<div class="meta">Proyecto <b>gestion_usuarios</b> · Versión %s · %s<br>Linux (RHEL / Oracle / SLES / Ubuntu) y Solaris 11</div>
</section>''' % (VERSION, datetime.date.today().strftime('%d/%m/%Y')))

    # ======================= ÍNDICE =======================
    a('<section class="indice"><h1>Contenido</h1><ol>%s</ol></section>' % ''.join(indice))

    # ======================= 1 =======================
    a(h1('c1'))
    a('<p class="lead">Este proyecto reúne en un solo lugar la gestión de cuentas de los servidores Linux. Cada operación es una <b>plantilla de AWX con su propia encuesta</b>: el operador llena un formulario y AWX hace el trabajo en los servidores elegidos.</p>')
    a('<div class="tarjetas">')
    for n, t, d, pb in [
        ('1', 'Crear usuarios', 'Alta de una o varias cuentas con <b>contraseña inicial</b> o con <b>llave SSH</b>. Define grupo, grupos secundarios y sudo: ninguno, completo o limitado a ciertos comandos.', '01_crear_usuarios.yml'),
        ('2', 'Cambiar contraseña', 'Cambia la clave de cualquier usuario (incluido <b>root</b>). Puede dejarla <b>sin caducidad</b> para que el hardening no la venza, forzar el cambio en el próximo ingreso o desbloquear la cuenta.', '02_cambiar_contrasena.yml'),
        ('3', 'Auditoría', 'Lista las cuentas con UID ≥ 1000 y dice si tienen sudo <b>completo, limitado o ninguno</b>, con qué comandos, si es sin contraseña y de dónde sale la regla. Entrega reporte HTML y CSV.', '03_auditoria_usuarios.yml'),
        ('4', 'Bloquear o eliminar', 'Bloqueo reversible (conserva el home) o eliminación con respaldo del home. Para eliminar hay que escribir CONFIRMAR.', '04_bloquear_eliminar_usuarios.yml')]:
        a('<div class="tarjeta"><span class="n">%s</span><h4>%s</h4><p>%s</p><div class="pb ruta">%s</div></div>' % (n, t, d, pb))
    a('</div>')
    a('<h2>Protecciones incluidas</h2><ul>'
      '<li><b>Nada se ejecuta sin «objetivo».</b> Si la encuesta no indica servidores o grupo, el job no toca ningún servidor.</li>'
      '<li><b>Cuentas protegidas.</b> root, las cuentas del sistema y las que usa AWX para conectarse (<code>ansible_test</code>, <code>adminso</code>, <code>tux</code>, <code>azureuser</code>) no se pueden crear, bloquear ni eliminar.</li>'
      '<li><b>Cuentas de servicio intactas.</b> Por debajo del UID 1000 no se cambian contraseñas ni se eliminan cuentas, salvo autorización explícita.</li>'
      '<li><b>Contraseñas protegidas.</b> AWX las guarda cifradas y no aparecen en la salida del job.</li>'
      '<li><b>sudo validado.</b> Cada regla se revisa con <code>visudo</code> antes de instalarla: una regla mal escrita no se aplica.</li>'
      '<li><b>Una llave por usuario, en todos los servidores.</b> Las llaves viven en <code>keys/</code>: si el usuario ya tiene, se reutiliza; solo se genera una nueva si no tiene o si se marca la opción crítica «Renovar llave».</li>'
      '<li><b>La auditoría es de solo lectura.</b> No cambia nada en los servidores.</li></ul>')

    # ======================= 2 =======================
    a(h1('c2'))
    a('<p class="lead">Las cuatro opciones siguen el mismo recorrido de tres pasos. Lo importante: <b>primero se revisan las respuestas</b> y solo si todo está bien se entra a los servidores.</p>')
    a(SVG_FLUJO)
    a(tabla(['Paso', 'Dónde ocurre', 'Qué pasa'], [
        ['<b>1 · Validar</b>', 'Dentro de AWX', 'Se revisan formato de usuarios, contraseña y confirmación, llaves SSH, comandos sudo y cuentas protegidas. Si algo está mal, el job falla con un mensaje que explica qué corregir.'],
        ['<b>2 · Aplicar</b>', 'Servidores del «objetivo»', 'Se ejecutan los cambios en cada servidor del grupo o lista indicada. Cada servidor se procesa por separado: si uno falla, los demás continúan.'],
        ['<b>3 · Resumir</b>', 'Salida del job', 'Cada servidor muestra qué se hizo (creados, ya existentes, contraseñas cambiadas). La auditoría además genera reportes HTML y CSV.']]))
    a(nota('info', 'El campo «Servidores o grupo del inventario»', 'Acepta un grupo (<code>GEOPOS</code>, <code>PPU</code>, <code>OCI_PEOPLE_PRD</code>…), un servidor (<code>ktuno-n0</code>), varios separados por coma (<code>srv1,srv2</code>) o combinaciones: <code>grupo1:grupo2</code> (ambos grupos) y <code>grupo:!servidor</code> (el grupo excepto un servidor). Respete mayúsculas y minúsculas.'))

    # ======================= 3 =======================
    a(h1('c3'))
    a('<p class="lead">Tres puntos que conviene revisar antes de publicar el proyecto en AWX.</p>')
    a(nota('peligro', 'Acción 1 · Proteger el repositorio: contiene las llaves privadas',
           'La carpeta <code>keys/</code> (antes <code>con_LLave/keys/</code>) es el almacén oficial de llaves: 10 usuarios con su llave privada, pública y <code>.ppk</code>. Por eso el repositorio debe ser <b>privado</b>, con acceso solo para el equipo de infraestructura, y el token con permiso de escritura debe usarlo únicamente AWX (credencial «Git - publicar llaves», Paso 2.4).'))
    a(nota('alerta', 'Acción 2 · Revisar los servidores con conexión local',
           'En <code>inventario/hosts.ini</code> %s tiene <code>ansible_connection=local</code>. En AWX eso no significa «ese servidor»: significa <b>dentro del contenedor de AWX</b>, así que al incluir su grupo el job fallará en ese host (o auditará el contenedor). Para usarlo desde AWX quite esa variable y deje su <code>ansible_host</code>, o exclúyalo en el objetivo: <code>PPU:!%s</code>.'
           % (', '.join('<code>%s</code>' % h for h in hosts_locales) or 'ningún servidor', hosts_locales[0] if hosts_locales else 'servidor')))
    a(nota('alerta', 'Acción 3 · Revisar el usuario de conexión por grupo',
           'El usuario con el que AWX entra a cada servidor sale de <code>inventario/group_vars/</code> (<code>ansible_test</code> en GEOPOS, PPU, PPU_GEOPOS e INFRA2_0; <code>adminso</code> en OCI_PEOPLE; <code>tux</code> en manhatan) o del propio <code>hosts.ini</code> (<code>tux</code> en hardening_linux). Ese valor <b>tiene prioridad</b> sobre el usuario de la credencial. AZURE y GEOPOS_MARCAR no definen usuario: usan el de la credencial. El detalle por grupo está en el <b>Anexo B</b>.'))
    a('<h2>Requisitos</h2>')
    a(tabla(['Dónde', 'Qué se necesita'], [
        ['<b>AWX</b>', 'AWX 21 o superior, o Ansible Automation Platform 2.x. Execution Environment con ansible-core 2.14 o superior (el predeterminado <code>awx-ee</code> sirve).'],
        ['<b>Colecciones</b>', 'AWX instala solo <code>ansible.posix</code>, <code>community.crypto</code> y <code>community.general</code> al sincronizar el proyecto. Necesita salida a Galaxy o una credencial de Automation Hub. Sin Internet: use un EE propio que ya las incluya.'],
        ['<b>Servidores</b>', 'La cuenta de conexión debe poder usar sudo (sin contraseña, o con la contraseña en la credencial). Python 2.7 o 3.x, que Ansible ya exige.'],
        ['<b>Sistemas</b>', 'RHEL / Oracle / Rocky 7-9, SLES 12/15, Ubuntu/Debian y Solaris 11. Solaris está programado pero no se ha probado en un equipo real: valídelo primero en uno de prueba.']], 'campos'))

    # ======================= 4 =======================
    a(h1('c4'))
    a('<p class="lead">Los playbooks quedan en la raíz del repositorio (AWX los busca ahí). La lógica vive en roles y los datos editables en <code>vars/</code>, <code>files/</code> e <code>inventario/</code>.</p>')
    a('''<pre>gestion_usuarios/
├── 01_crear_usuarios.yml              ← opción 1
├── 02_cambiar_contrasena.yml          ← opción 2
├── 03_auditoria_usuarios.yml          ← opción 3
├── 04_bloquear_eliminar_usuarios.yml  ← opción 4
├── ansible.cfg
├── collections/requirements.yml       ← colecciones que AWX instala solo
├── inventario/
│   ├── hosts.ini                      ← INVENTARIO 2026 (%d servidores)
│   └── group_vars/                    ← usuario de conexión por grupo
├── vars/
│   ├── comunes.yml                    ← cuentas protegidas, UID mínimo
│   └── catalogos/                     ← listas de usuarios reutilizables
├── keys/                              ← llaves por usuario: &lt;usuario&gt;, .pub y .ppk
│   └── _anteriores/                   ← llaves reemplazadas por una renovación
├── roles/                             ← la lógica de cada opción
├── awx/
│   ├── encuestas/*.json               ← encuestas listas para importar
│   ├── generar_encuestas.py           ← fuente única de las encuestas
│   └── configurar_awx.yml             ← crea todo en AWX automáticamente
└── docs/                              ← este manual</pre>''' % total_hosts)
    a('<h2>¿Qué archivo toco para…?</h2>')
    a(tabla(['Necesito…', 'Archivo', 'Después'], [
        ['Agregar una lista de usuarios reutilizable (p. ej. una zona nueva)', '<code>vars/catalogos/&lt;nombre&gt;.yml</code>', 'Agregar el nombre en <code>awx/generar_encuestas.py</code>, ejecutarlo y recargar la encuesta 1.'],
        ['Cargar la llave que ya tiene un usuario', '<code>keys/&lt;usuario&gt;</code>, <code>keys/&lt;usuario&gt;.pub</code> (y <code>.ppk</code>)', 'Commit. La opción 1 la usará en vez de generar una.'],
        ['Proteger una nueva cuenta de conexión de AWX', '<code>vars/comunes.yml</code> → <code>usuarios_protegidos</code>', 'Hacer commit; AWX lo toma al siguiente job.'],
        ['Cambiar una pregunta de una encuesta', '<code>awx/generar_encuestas.py</code>', 'Ejecutarlo, recargar la encuesta y regenerar este manual.'],
        ['Agregar servidores o grupos', '<code>inventario/hosts.ini</code> (y <code>group_vars/&lt;grupo&gt;.yml</code> si el grupo usa otro usuario de conexión)', 'Commit y sincronizar el inventario en AWX.']]))
    a('<h3>Formato de un catálogo de usuarios</h3>')
    a('''<pre>catalogo_defaults:          # aplica a todos (opcional)
  grupo: soporte
usuarios:
  - usuario: jperez
    nombre: "Juan Pérez"
  - usuario: jmonitor
    nombre: "Usuario de monitoreo"
    sudo: limitado            # ninguno | completo | limitado
    sudo_nopasswd: true
    sudo_comandos:
      - /usr/bin/systemctl restart httpd
      - /usr/bin/tail -n 200 /var/log/messages</pre>''')
    a('<p>Campos opcionales por usuario: <code>grupo</code>, <code>grupos</code>, <code>uid</code>, <code>shell</code>, <code>home</code>, <code>llave_publica</code>, <code>sudo</code>, <code>sudo_nopasswd</code>, <code>sudo_comandos</code>. Lo que se define en el usuario reemplaza lo de <code>catalogo_defaults</code> y lo de la encuesta.</p>')

    # ======================= 5 =======================
    a(h1('c5'))
    a('<p class="lead">AWX necesita seis piezas, que se crean en este orden. Las tres de la izquierda alimentan a cada plantilla; la encuesta va dentro de la plantilla; los permisos dicen quién puede usarla.</p>')
    a(SVG_AWX)
    a(nota('ok', '¿Prefiere hacerlo automático?', 'El playbook <code>awx/configurar_awx.yml</code> crea el proyecto, los inventarios, el tipo de credencial SMTP y las cuatro plantillas con sus encuestas (ver el final del Paso 6). Se recomienda hacerlo a mano la primera vez para entender cada pieza.'))

    a('<h2 id="c5p1">Paso 1 · Subir el proyecto a Git</h2>')
    a(pasos([
        'Cree un repositorio (GitLab, GitHub, Bitbucket, Gitea…).',
        'Suba <b>el contenido</b> de la carpeta <code>gestion_usuarios/</code> a la <b>raíz</b> del repositorio, de modo que <code>01_crear_usuarios.yml</code> quede en la raíz.',
        'Verifique que no se suban llaves privadas: el archivo <code>.gitignore</code> ya excluye <code>keys/</code>, <code>llaves_generadas/</code>, <code>*.ppk</code> y los reportes.',
        'Corrija los conflictos de IP del Anexo B y haga commit.']))

    a('<h2 id="c5p2">Paso 2 · Credenciales</h2><p>Menú <b>Resources → Credentials → Add</b>.</p>')
    a('<h3>2.1 Acceso al repositorio (solo si es privado)</h3>')
    a(campos([['Name', '<code>Git - gestion_usuarios</code>'], ['Credential Type', 'Source Control'],
              ['Username / Password o SCM Private Key', 'Usuario de servicio o <i>deploy key</i> de solo lectura']]))
    a('<h3>2.2 Conexión a los servidores</h3>')
    a(campos([['Name', '<code>Linux - ansible_test</code>'], ['Credential Type', 'Machine'], ['Username', '<code>ansible_test</code>'],
              ['SSH Private Key', 'La llave privada de la cuenta de automatización'], ['Privilege Escalation Method', '<code>sudo</code>'],
              ['Privilege Escalation Password', 'Solo si sudo pide contraseña']]))
    a(nota('info', 'Si cada grupo usa una cuenta distinta', 'Cree una credencial Machine por cuenta (<code>adminso</code>, <code>tux</code>…) y use plantillas o inventarios separados por grupo, o elimine <code>ansible_user</code> de los <code>group_vars</code> y deje que lo defina la credencial.'))
    a('<h3>2.3 Correo para la auditoría (opcional)</h3>')
    a('<p>Primero cree el <b>tipo</b> de credencial en <b>Administration → Credential Types → Add</b>, con nombre <code>SMTP - Reportes gestion_usuarios</code>:</p>')
    a('<div class="dos"><div><b>Input configuration</b><pre>fields:\n  - {id: smtp_servidor, type: string,\n     label: Servidor SMTP}\n  - {id: smtp_puerto, type: string,\n     label: Puerto, default: "25"}\n  - {id: smtp_usuario, type: string,\n     label: Usuario (opcional)}\n  - {id: smtp_clave, type: string,\n     label: Contraseña, secret: true}\n  - {id: smtp_seguridad, type: string,\n     label: Seguridad, default: try}\n  - {id: smtp_remitente, type: string,\n     label: Remitente}\nrequired: [smtp_servidor]</pre></div>'
      '<div><b>Injector configuration</b><pre>extra_vars:\n  smtp_servidor: \'{{ smtp_servidor }}\'\n  smtp_puerto: \'{{ smtp_puerto | default("25") }}\'\n  smtp_usuario: \'{{ smtp_usuario | default("") }}\'\n  smtp_clave: \'{{ smtp_clave | default("") }}\'\n  smtp_seguridad: \'{{ smtp_seguridad |\n                     default("try") }}\'\n  auditoria_correo_remitente:\n    \'{{ smtp_remitente |\n       default("ansible-awx@empresa.local") }}\'</pre></div></div>')
    a('<p>Después cree la credencial <code>SMTP - Correo corporativo</code> de ese tipo con los datos del servidor de correo.</p>')
    a('<h3>2.4 Publicar llaves nuevas en Git (necesaria para el método llave)</h3>')
    a('<p>Cuando la opción 1 genera una llave (usuario nuevo o renovación), AWX la sube a <code>keys/</code> del repositorio. Así la siguiente ejecución, en cualquier servidor, <b>reutiliza esa misma llave</b>. Sin esta credencial, AWX se niega a generar llaves, porque se perderían al terminar el job.</p>')
    a('<div class="dos"><div><b>Credential Type → Input configuration</b><pre>fields:\n  - {id: llaves_git_url, type: string,\n     label: URL HTTPS del repositorio}\n  - {id: llaves_git_rama, type: string,\n     label: Rama, default: main}\n  - {id: llaves_git_usuario, type: string,\n     label: Usuario}\n  - {id: llaves_git_token, type: string,\n     label: Token de escritura, secret: true}\nrequired: [llaves_git_url, llaves_git_usuario,\n           llaves_git_token]</pre></div>'
      '<div><b>Injector configuration</b><pre>extra_vars:\n  llaves_git_url: \'{{ llaves_git_url }}\'\n  llaves_git_rama: \'{{ llaves_git_rama |\n                     default("main") }}\'\n  llaves_git_usuario: \'{{ llaves_git_usuario }}\'\n  llaves_git_token: \'{{ llaves_git_token }}\'</pre></div></div>')
    a(campos([['Tipo (Administration → Credential Types)', '<code>Git - publicar llaves</code>, con la configuración de arriba'],
              ['Credencial (Resources → Credentials)', '<code>Git - publicar llaves gestion_usuarios</code>'],
              ['URL HTTPS del repositorio', 'La misma del proyecto, en HTTPS (p. ej. <code>https://git.empresa.local/infra/gestion_usuarios.git</code>)'],
              ['Usuario / Token', 'Cuenta de servicio con permiso de <b>push</b> en la rama (en GitLab: Project Access Token con <code>write_repository</code>; en GitHub: token con <i>Contents: write</i>)']]))
    a(nota('info', 'Rama protegida', 'Si la rama <code>main</code> está protegida, permita el push a esa cuenta de servicio o el job fallará con «push rechazado» sin tocar servidores.'))

    a('<h2 id="c5p3">Paso 3 · Proyecto</h2><p>Menú <b>Resources → Projects → Add</b>.</p>')
    a(campos([['Name', '<code>Gestion de usuarios Linux</code>'], ['Organization', 'La suya (p. ej. <code>Default</code>)'],
              ['Execution Environment', 'El predeterminado o el suyo'], ['Source Control Type', 'Git'],
              ['Source Control URL', 'URL del repositorio'], ['Source Control Branch', '<code>main</code>'],
              ['Source Control Credential', '<code>Git - gestion_usuarios</code> (si aplica)'],
              ['Options', '☑ Clean · ☑ Update Revision on Launch']]))
    a('<p>Guarde y espere a que la sincronización termine en verde. Si falla instalando colecciones, revise el acceso a Galaxy (capítulo 3).</p>')

    a('<h2 id="c5p4">Paso 4 · Inventario</h2>')
    a('<p>Todo el proyecto usa un solo archivo: <code>inventario/hosts.ini</code> (INVENTARIO 2026, %d servidores en %d grupos).</p>' % (total_hosts, len(grupos_inv)))
    a(pasos([
        '<b>Resources → Inventories → Add → Add inventory</b>. Name: <code>Inventario 2026</code>. Guardar.',
        'Pestaña <b>Sources → Add</b>: Name <code>Inventario 2026 - desde proyecto</code>, Source <b>Sourced from a Project</b>, Project <code>Gestion de usuarios Linux</code>, Inventory file <code>inventario/hosts.ini</code>.',
        'Marque ☑ Overwrite, ☑ Overwrite variables y ☑ Update on launch. Guardar y pulsar <b>Sync</b>.',
        'Compruebe en <b>Hosts</b> que aparezcan los %d servidores y en <b>Groups</b> los grupos (<code>GEOPOS</code>, <code>PPU</code>, <code>OCI_PEOPLE_PRD</code>…).' % total_hosts]))
    a(nota('info', 'Variables por grupo', 'Los archivos de <code>inventario/group_vars/</code> se cargan solos porque están junto a los <code>.ini</code>.'))

    a('<h2 id="c5p5">Paso 5 · Plantillas de trabajo</h2>')
    a('<p>Menú <b>Resources → Templates → Add → Add job template</b>. Cree las cuatro con esta configuración común:</p>')
    a(campos([['Job Type', 'Run'], ['Inventory', '<code>Inventario 2026</code>'],
              ['Project', '<code>Gestion de usuarios Linux</code>'],
              ['Credentials', '<code>Linux - ansible_test</code>. En la plantilla 1 agregue <code>Git - publicar llaves gestion_usuarios</code>; en la 3, <code>SMTP - Correo corporativo</code>'],
              ['Limit', 'Vacío, con ☑ Prompt on launch (opcional)'], ['Verbosity', '0 (Normal)'], ['Forks', '20'],
              ['Options', '☑ <b>Privilege Escalation</b> · ☐ Concurrent jobs']]))
    a(tabla(['Name (nombre de la plantilla)', 'Playbook'], [
        ['<b>USUARIOS | 1 - Crear usuarios</b>', '<code>01_crear_usuarios.yml</code>'],
        ['<b>USUARIOS | 2 - Cambiar contraseña</b>', '<code>02_cambiar_contrasena.yml</code>'],
        ['<b>USUARIOS | 3 - Auditoría</b>', '<code>03_auditoria_usuarios.yml</code>'],
        ['<b>USUARIOS | 4 - Bloquear o eliminar</b>', '<code>04_bloquear_eliminar_usuarios.yml</code>']]))

    a('<h2 id="c5p6">Paso 6 · Encuestas</h2>')
    a('<p>Cada plantilla lleva su encuesta. Las preguntas exactas están en el <b>Anexo A</b> y en <code>awx/encuestas/*.json</code>. Elija una de estas tres formas de cargarlas:</p>')
    a(tabla(['Forma', 'Cuándo usarla', 'Cómo'], [
        ['<b>A · A mano en la UI</b>', 'Para entender cada pregunta', 'En la plantilla: pestaña <b>Survey → Add</b>. Cree las preguntas del Anexo A en orden, con el nombre de <b>variable exacto</b>. Al final active <b>Survey Enabled</b>.'],
        ['<b>B · Por API</b>', 'Rápido y sin errores de digitación', 'Ver comandos abajo.'],
        ['<b>C · Todo como código</b>', 'Para recrear AWX completo', 'Ejecutar <code>awx/configurar_awx.yml</code> (ver abajo).']]))
    a(nota('info', 'Consejos para la UI', 'En opción múltiple escriba una opción por línea y marque la predeterminada. En las áreas de texto suba <i>Maximum length</i> a 20000 para poder pegar varias llaves. Los campos tipo <b>Password</b> quedan cifrados y aparecen como <code>$encrypted$</code>.'))
    a('<h3>B · Carga por API</h3>')
    a('''<pre>AWX=https://awx.empresa.local
TOKEN=&lt;token personal&gt;     # Users → su usuario → Tokens → Add (scope Write)
ID=$(curl -sk -H "Authorization: Bearer $TOKEN" \\
  "$AWX/api/v2/job_templates/?name=USUARIOS%20|%201%20-%20Crear%20usuarios" | jq '.results[0].id')

curl -sk -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \\
  --data @awx/encuestas/01_crear_usuarios.json "$AWX/api/v2/job_templates/$ID/survey_spec/"

curl -sk -X PATCH -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \\
  --data '{"survey_enabled": true}' "$AWX/api/v2/job_templates/$ID/"</pre>''')
    a('<p>Repita con los otros tres archivos JSON y sus plantillas.</p>')
    a('<h3>C · Todo como código</h3>')
    a('''<pre>ansible-galaxy collection install awx.awx
export CONTROLLER_HOST=https://awx.empresa.local
export CONTROLLER_OAUTH_TOKEN=&lt;token&gt;
ansible-playbook awx/configurar_awx.yml \\
  -e awx_repo_url=https://git.empresa.local/infra/gestion_usuarios.git \\
  -e awx_credencial_maquina="Linux - ansible_test" \\
  -e awx_credencial_scm="Git - gestion_usuarios" \\
  -e awx_credencial_smtp="SMTP - Correo corporativo"</pre>''')
    a('<p>Las credenciales Machine y Source Control deben existir antes. El playbook se puede repetir sin problema: actualiza lo que haya cambiado.</p>')

    a('<h2 id="c5p7" style="break-before: page; margin-top: 0">Paso 7 · Permisos</h2>')
    a('<p>En <b>Access → Teams</b> cree los equipos y asígneles roles en la pestaña <b>Access</b> de cada plantilla:</p>')
    a(tabla(['Equipo', 'Plantillas', 'Rol'], [
        ['Soporte Linux - Operadores', '1, 2 y 4', 'Execute'], ['Seguridad - Auditores', '3', 'Execute'],
        ['Infraestructura - Administradores', 'Todas, más proyecto e inventarios', 'Admin']]))
    a(nota('ok', 'Recomendado para cambiar la clave de root en producción', 'Cree un <b>Workflow</b> con un nodo de <b>aprobación</b> antes de la plantilla 2 (<b>Templates → Add → Add workflow template → Approval node</b>). Así un segundo responsable aprueba cada cambio. Active también <b>Notifications</b> en las plantillas 2 y 4.'))

    # ======================= 6 =======================
    a(h1('c6'))
    a('<p class="lead">Ejemplos reales de cómo llenar cada encuesta. Las preguntas que no aparecen se dejan con su valor por defecto.</p>')
    a('<h2 id="c61">Opción 1 · Crear usuarios</h2>')
    a('<h3>Ejemplo A · Tres técnicos de soporte con contraseña</h3>')
    a(formulario('01_crear_usuarios', {
        'objetivo': 'GEOPOS', 'crear_metodo_acceso': 'contrasena', 'crear_origen': 'encuesta',
        'crear_usuarios_texto': 'jperez;Juan Pérez\nmgomez;María Gómez\nlrojas;Luis Rojas', 'crear_grupo_primario': 'soporte',
        'crear_contrasena_inicial': 'x', 'crear_forzar_cambio': 'SI', 'crear_sudo_nivel': 'ninguno'}, 'Cuentas personales, clave temporal que deben cambiar al entrar'))
    a('<p><b>Formato de la lista:</b> una línea por usuario, <code>usuario;Nombre completo;grupo</code>. El grupo es opcional: si se omite se usa el «Grupo primario» de la encuesta, y si ese también está vacío, un grupo con el mismo nombre del usuario.</p>')
    a('<h3>Ejemplo B · Toda una zona desde el catálogo</h3>')
    a('<p>Origen = <code>catalogo</code>, Catálogo = <code>usuarios_zona_centro</code>, Método = <code>contrasena</code>, contraseña inicial y forzar cambio = <code>SI</code>. El catálogo ya trae <code>grupo: soporte</code>.</p>')
    a('<h3>Ejemplo C · Administrador con llave SSH y sudo completo</h3>')
    a(formulario('01_crear_usuarios', {
        'objetivo': 'PPU', 'crear_metodo_acceso': 'llave', 'crear_origen': 'encuesta',
        'crear_usuarios_texto': 'jcantor;Administrador Linux - Amaris', 'crear_llave_origen': 'keys',
        'crear_renovar_llave': 'NO', 'crear_sudo_nivel': 'completo'}, 'Acceso solo por llave: jcantor ya tiene llave en keys/, se reutiliza'))
    a(nota('info', 'Con método llave', 'La contraseña queda bloqueada y sin caducidad, y el sudo se configura <b>sin contraseña</b> automáticamente (la cuenta no tiene clave que digitar). Como <code>jcantor</code> ya tiene llave en <code>keys/</code>, se instala esa misma: el usuario entra con la llave que ya conoce.'))
    a('<h3>Ejemplo D · Usuario de monitoreo con sudo limitado</h3>')
    a(formulario('01_crear_usuarios', {
        'objetivo': 'PPU_GEOPOS', 'crear_metodo_acceso': 'contrasena', 'crear_usuarios_texto': 'jmonitor;Usuario de monitoreo',
        'crear_contrasena_inicial': 'x', 'crear_sudo_nivel': 'limitado', 'crear_sudo_nopasswd': 'SI',
        'crear_sudo_comandos': '/usr/bin/systemctl restart httpd\n/usr/bin/tail -n 200 /var/log/messages'}, 'Solo puede ejecutar dos comandos como root'))
    a(nota('alerta', 'Comandos que nunca debe dar por sudo', 'Escriba cada comando con <b>ruta absoluta</b>. Evite <code>less</code>, <code>more</code>, <code>vi</code>, <code>journalctl</code>, <code>systemctl status</code>, <code>find</code>, <code>awk</code>, <code>python</code>, <code>tar</code> o <code>cp</code>: todos permiten abrir una shell de root. La auditoría los marca como hallazgo ALTO.'))
    a('<h3>Llaves SSH: reutilizar, generar o renovar</h3>')
    a('<p>Con «Origen de la llave = <b>keys</b>» (valor por defecto) cada usuario tiene <b>una sola llave</b>, guardada en <code>keys/</code>, y es la misma en todos los servidores:</p>')
    a(tabla(['Situación del usuario', '«Renovar llave»', 'Qué pasa'], [
        ['Ya tiene llave en <code>keys/</code>', 'NO', '<b>Se reutiliza</b> esa llave. No se genera nada.'],
        ['No tiene llave en <code>keys/</code>', 'NO / SI', 'Se <b>genera</b> una (RSA 4096, con <code>.ppk</code> si hay puttygen), se guarda en <code>keys/</code> y se <b>publica en Git</b> antes de tocar servidores.'],
        ['Ya tiene llave en <code>keys/</code>', '<b style="color:#a3231b">SI</b>', 'Se genera una <b>nueva</b>. La anterior se mueve a <code>keys/_anteriores/&lt;usuario&gt;_&lt;fecha&gt;</code>. En los servidores del objetivo se <b>retira la llave anterior</b> y se instala la nueva, también si la cuenta ya existía.']]))
    a(nota('peligro', '«Renovar llave» es una opción crítica',
           'Úsela solo si la llave se perdió o pudo quedar expuesta. Afecta únicamente a los servidores del «objetivo» de esa ejecución: en los demás servidores el usuario seguirá entrando <b>solo con la llave anterior</b>, que ya no estará en <code>keys/</code> sino en <code>keys/_anteriores/</code>. Para renovar por completo, ejecute con un objetivo que incluya <b>todos</b> los servidores donde existe el usuario. Después entregue la nueva llave privada al usuario por un canal seguro.'))
    a(nota('info', 'Origen «encuesta»', 'Sirve cuando la persona genera su propio par y entrega solo la pública: se pega en la encuesta (<code>usuario;ssh-rsa AAAA...</code>) y no se guarda en <code>keys/</code>. «Renovar llave» no aplica en este caso.'))
    a('<h3>¿Y si el usuario ya existe?</h3>')
    a('<p>Con «Actualizar usuarios que ya existen = NO» (valor por defecto) se omite y se informa. Con <b>SI</b> se le agregan grupos, llave y regla sudo; nunca se cambian su contraseña, home, shell, UID ni grupo primario.</p>')

    a('<h2 id="c62">Opción 2 · Cambiar contraseña</h2>')
    a('<h3>Ejemplo · Clave de root sin caducidad</h3>')
    a(formulario('02_cambiar_contrasena', {
        'objetivo': 'PPU_GEOPOS', 'contrasena_usuarios': 'root', 'contrasena_nueva': 'x', 'contrasena_confirmacion': 'x',
        'contrasena_nunca_caduca': 'SI', 'contrasena_quitar_expiracion_cuenta': 'NO', 'contrasena_forzar_cambio': 'NO',
        'contrasena_desbloquear': 'SI', 'contrasena_permitir_cuentas_servicio': 'NO'}, 'Caso típico: el hardening vence la clave de root cada 90 días'))
    a('<h3>Qué hace en cada servidor</h3>')
    a(pasos([
        '<b>Cambia la clave</b> con <code>chpasswd</code>, que la recibe por entrada estándar: no aparece en procesos ni en logs, y el servidor genera el hash con su propio algoritmo (SHA-512 o yescrypt).',
        '<b>Quita la caducidad</b> con <code>chage -m 0 -M 99999 -I -1</code>. Desde ese momento <code>chage -l root</code> muestra <i>Password expires: never</i>, aunque el hardening tenga <code>PASS_MAX_DAYS 90</code>. Si la cuenta ya estaba así, no hace nada.',
        '<b>Desbloquea</b>: reinicia los intentos fallidos (<code>faillock</code> o <code>pam_tally2</code>) y quita una expiración de cuenta ya vencida.',
        '<b>Verifica</b> en <code>/etc/shadow</code> que la fecha de último cambio sea la de hoy y muestra el resultado de <code>chage -l</code>.']))
    a(tabla(['Pregunta', 'Cuándo responder SI'], [
        ['Contraseña sin caducidad', 'Cuentas críticas (root, cuentas de aplicación) que no pueden vencer. Es la opción por defecto.'],
        ['Quitar también la fecha de expiración de la cuenta', 'Solo si la cuenta tenía una fecha de vencimiento y debe quedar permanente.'],
        ['Forzar cambio en el próximo inicio', 'Cuentas personales donde el usuario debe poner su propia clave. No se puede junto con «sin caducidad» ni sobre root.'],
        ['Permitir cuentas de servicio', 'Casi nunca. Habilita cambiar claves de cuentas con UID entre 1 y 999.']]))
    a(nota('alerta', 'Después de cambiar la clave de root', 'Regístrela en la bóveda de contraseñas corporativa. Si la clave no cumple la política de complejidad del servidor, el job falla en ese servidor con el mensaje del sistema, sin mostrar la clave. Si cambió la clave de la cuenta con la que se conecta AWX y la credencial usa contraseña, actualícela (el job avisa).'))

    a('<h2 id="c63">Opción 3 · Auditoría</h2>')
    a(formulario('03_auditoria_usuarios', {
        'objetivo': 'GEOPOS', 'auditoria_uid_minimo': '1000', 'auditoria_dias_inactividad': '90',
        'auditoria_detalle_salida': 'resumido', 'auditoria_enviar_correo': 'SI',
        'auditoria_correo_destinatarios': 'seguridad@empresa.com, infra@empresa.com', 'auditoria_copiar_a_host': ''}, 'Revisión mensual de una zona'))
    a(nota('alerta', 'Conserve los reportes', 'AWX borra el contenedor al terminar el job. Si no activa el correo ni «Copiar reportes a servidor», los archivos HTML y CSV se pierden (la salida del job sí queda).'))

    a('<h2 id="c64">Opción 4 · Bloquear o eliminar</h2>')
    a(formulario('04_bloquear_eliminar_usuarios', {
        'objetivo': 'GEOPOS_MARCAR', 'eliminar_usuarios': 'lrojas', 'eliminar_accion': 'bloquear'}, 'Retiro temporal de un técnico'))
    a(tabla(['Acción', 'Qué hace', 'Cómo revertir'], [
        ['<b>bloquear</b>', 'Bloquea la clave, expira la cuenta (impide también entrar con llave) y retira su regla sudo. Conserva el home y sus archivos.', 'Opción 2 con «Desbloquear = SI» y una clave nueva. La regla sudo se vuelve a crear con la opción 1.'],
        ['<b>eliminar</b>', 'Respalda el home en <code>/var/backups/usuarios_eliminados/</code>, retira sudo y borra la cuenta y su home. Exige escribir <code>CONFIRMAR</code>.', 'Crear de nuevo y restaurar el respaldo.']]))

    # ======================= 7 =======================
    a(h1('c7'))
    a('<h2>Dónde ver los resultados</h2>')
    a(tabla(['Lugar', 'Qué contiene'], [
        ['<b>Salida del job</b>', 'Una tabla por servidor y un consolidado con todas las cuentas que tienen sudo y los hallazgos críticos y altos.'],
        ['<b>Artifacts del job</b>', 'Conteos por servidor (<code>auditoria_usuarios.servidores</code>), útiles para encadenar en un Workflow.'],
        ['<b>Correo</b>', 'Reporte HTML y CSV adjuntos, si se activó.'],
        ['<b>Servidor de reportes</b>', 'HTML y CSV en <code>/var/reportes/auditoria_usuarios/</code>, si se indicó «Copiar reportes a servidor».']], 'campos'))
    a('<img class="captura" src="ejemplo_reporte.png" alt="Reporte de auditoría">')
    a('<div class="pie-img">Parte superior del reporte HTML (ejemplo con cuentas de prueba). Más abajo siguen la tabla de cuentas con sudo, con sus comandos y el archivo que da el permiso, y el detalle por servidor. Cada tabla tiene un buscador. El CSV abre directo en Excel (separado por punto y coma).</div>')
    a('<h2>Niveles de sudo</h2>')
    a('<p>El permiso se obtiene con <code>sudo -ll -U &lt;usuario&gt;</code>, que devuelve lo que la cuenta <b>realmente puede hacer</b>, venga de una línea propia, de un grupo (<code>%wheel</code>, <code>%admins</code>), de un alias, de <code>/etc/sudoers.d</code> o de LDAP/SSSD.</p>')
    a(tabla(['Nivel', 'Significado'], [
        ['<b style="color:#a3231b">COMPLETO</b>', 'Alguna regla concede <code>ALL</code>: puede hacer cualquier cosa como root. Las excepciones del tipo <code>ALL, !/bin/su</code> no lo limitan en la práctica.'],
        ['<b style="color:#a15400">LIMITADO</b>', 'Solo los comandos listados. Si alguno permite abrir una shell (editores, paginadores, intérpretes), se marca en rojo y genera hallazgo ALTO.'],
        ['<b style="color:#5b6475">NINGUNO</b>', 'No puede usar sudo.']]))
    a(nota('info', 'Caso SUSE: todos aparecen con sudo COMPLETO', 'SLES trae por defecto <code>Defaults targetpw</code> y <code>ALL ALL=(ALL) ALL</code>: cualquier usuario puede usar sudo, pero debe digitar la <b>clave de root</b>. El reporte lo muestra como «Clave exigida: root (targetpw)» y lo clasifica MEDIO, no ALTO.'))
    a('<h2>Hallazgos</h2>')
    hall = [
        ('CRITICO', 'UID0_NO_ROOT', 'Otra cuenta además de root tiene UID 0 (es root con otro nombre).'),
        ('CRITICO', 'CONTRASENA_VACIA', 'La cuenta entra sin contraseña.'),
        ('ALTO', 'SUDO_COMPLETO_SIN_CLAVE', 'Sudo ALL sin contraseña (NOPASSWD).'),
        ('ALTO', 'SUDO_COMPLETO', 'Sudo ALL con su propia contraseña.'),
        ('ALTO', 'SUDO_ESCALAMIENTO', 'Sudo limitado, pero a comandos que permiten obtener root.'),
        ('ALTO', 'GRUPO_EQUIVALENTE_ROOT', 'Pertenece a docker, lxd, disk u otro grupo que equivale a root.'),
        ('ALTO', 'HASH_DEBIL', 'Clave guardada con MD5 o DES.'),
        ('ALTO', 'ROOT_CLAVE_EXPIRADA', 'La clave de root está vencida (use la opción 2).'),
        ('MEDIO', 'SUDO_COMPLETO_CLAVE_ROOT', 'Sudo ALL que exige la clave de root (targetpw/rootpw).'),
        ('MEDIO', 'SUDO_COMODINES', 'Reglas con * en los argumentos.'),
        ('MEDIO', 'CONTRASENA_EXPIRADA', 'La clave del usuario está vencida.'),
        ('MEDIO', 'CUENTA_INACTIVA', 'Cuenta habilitada sin ingresar hace más de N días.'),
        ('MEDIO', 'SSH_ROOT_PERMITIDO', 'sshd permite entrar directo como root (PermitRootLogin yes).'),
        ('BAJO', 'NUNCA_INGRESO', 'Cuenta habilitada que nunca ha iniciado sesión.'),
        ('BAJO', 'CONTRASENA_SIN_CADUCIDAD', 'Cuenta personal con clave que no caduca.'),
        ('INFO', 'Otros', 'SUDO_NEGACIONES, CUENTA_EXPIRADA, LLAVE_CON_OPCIONES, ROOT_CLAVE_CADUCA, SUDOERS_SIN_INCLUDEDIR.')]
    a(tabla(['Severidad', 'Código', 'Significado'], [[chip(s), '<code>%s</code>' % c, d] for s, c, d in hall], 'compacta'))
    a('<h2>Otras columnas útiles</h2>')
    a(tabla(['Columna', 'Qué indica'], [
        ['Acceso', 'Si la cuenta puede iniciar sesión hoy: shell interactiva, permitida por AllowUsers/AllowGroups de SSH, no expirada y con clave activa o llave SSH.'],
        ['Contraseña', '<b>ACTIVA</b> (utilizable) · <b>BLOQUEADA</b> · <b>SIN_CLAVE</b> (nunca se asignó; solo entra con llave) · <b>VACIA</b> (entra sin clave).'],
        ['Caduca', 'Fecha en que vence la clave, o «nunca».'],
        ['Llaves', 'Cantidad de llaves SSH autorizadas (al pasar el mouse se ve el comentario de cada una).'],
        ['Último acceso', 'Según <code>lastlog</code>. «NUNCA» si nunca ha entrado.']], 'campos'))

    # ======================= 8 =======================
    a(h1('c8'))
    a('<ul>'
      '<li><b>Contraseñas solo por encuesta.</b> Nunca las escriba en archivos del repositorio. Desde la línea de comandos use un archivo cifrado con <code>ansible-vault</code>.</li>'
      '<li><b>No suba la verbosidad</b> de las plantillas 1 y 2 por encima de 2 en producción: aunque las tareas sensibles están ocultas (<code>no_log</code>), es mejor no arriesgar.</li>'
      '<li><b>El repositorio guarda llaves privadas.</b> Manténgalo privado, con acceso solo para infraestructura, y use un token de escritura exclusivo para AWX. Entregue cada llave privada a su dueño por un canal seguro (nunca por correo sin cifrar).</li>'
      '<li><b>«Renovar llave» solo cuando haga falta</b> (llave perdida o expuesta), y con un objetivo que incluya todos los servidores donde existe el usuario.</li>'
      '<li><b>«Nunca caduca» es una excepción a la política.</b> Documente para qué cuentas se aplica (root y cuentas de aplicación) y ejecute la auditoría periódicamente para revisarlas.</li>'
      '<li><b>Aprobación para root.</b> Use un Workflow con nodo de aprobación para cambiar la clave de root en producción.</li>'
      '<li><b>Pruebe antes de un cambio masivo.</b> Lance la plantilla con <b>Job Type = Check</b> sobre un servidor: muestra qué cambiaría sin aplicarlo. Los cambios de contraseña no se simulan, y en la opción 1 las tareas que dependen de una cuenta aún no creada pueden marcar error en ese modo (en la ejecución real no ocurre).</li>'
      '<li><b>Auditoría periódica.</b> Programe la plantilla 3 (<b>Schedules</b>) cada mes con envío por correo.</li></ul>')

    # ======================= 9 =======================
    a(h1('c9'))
    a(tabla(['Síntoma', 'Causa y solución'], [
        ['<b>«Could not match supplied host pattern»</b> y el job no hace nada', 'El valor de «Servidores o grupo» no existe en el inventario elegido. Revise mayúsculas (<code>OCI_PEOPLE_PRD</code>; la lista está en el Anexo B) y que el inventario esté sincronizado.'],
        ['Falla en una tarea <b>«Preparar | Validar…»</b>', 'La encuesta tiene un dato inválido; el mensaje dice cuál. No se tocó ningún servidor.'],
        ['<b>«Missing sudo password»</b>', 'La cuenta de conexión pide contraseña para sudo: agréguela en la credencial (Privilege Escalation Password).'],
        ['<b>«chpasswd falló … BAD PASSWORD»</b>', 'La clave no cumple la política de complejidad o de historial del servidor. Use una más fuerte.'],
        ['<b>«couldn\'t resolve module/action ansible.posix.authorized_key»</b>', 'No se instalaron las colecciones: sincronice el proyecto y revise el acceso a Galaxy o Automation Hub.'],
        ['Aviso <b>«sudoers no lee /etc/sudoers.d»</b>', 'Falta <code>#includedir /etc/sudoers.d</code> en <code>/etc/sudoers</code>. La regla se creó pero no aplica hasta agregar esa línea.'],
        ['El usuario con llave <b>no puede entrar</b>', 'Revise que su grupo esté permitido en AllowGroups/AllowUsers de sshd (la auditoría lo muestra en «Acceso»). El proyecto agrega el grupo <code>ssh_access</code> automáticamente si existe.'],
        ['<b>«Hay que generar llaves … el contenedor se borra»</b>', 'La plantilla 1 no tiene la credencial «Git - publicar llaves» (Paso 2.4). Es intencional: sin ella la llave se perdería y la próxima vez se generaría otra. No se modificó ningún servidor.'],
        ['<b>«No se pudieron publicar las llaves … push rechazado»</b>', 'El token no tiene permiso de escritura o la rama está protegida. Corrija y vuelva a lanzar: no se modificó ningún servidor.'],
        ['<b>Solaris 11</b>', 'Programado pero no probado en equipo real; valide en uno de prueba. Las cuentas de solo llave se dejan con <code>passwd -N</code>, porque en Solaris <code>passwd -l</code> también bloquea el acceso por llave.']], 'campos'))

    # ======================= 10 =======================
    a(h1('c10'))
    a('<p>Todo lo anterior también funciona sin AWX, pasando las respuestas de la encuesta como variables <code>-e</code>.</p>')
    a('''<pre>ansible-galaxy collection install -r collections/requirements.yml

# Auditoría
ansible-playbook -i inventario/hosts.ini 03_auditoria_usuarios.yml -e objetivo=GEOPOS

# Crear desde catálogo (contraseña desde archivo cifrado)
ansible-playbook -i inventario/hosts.ini 01_crear_usuarios.yml \\
  -e objetivo=GEOPOS -e crear_origen=catalogo -e crear_catalogo=usuarios_zona_centro \\
  -e @secretos.yml --ask-vault-pass

# Clave de root sin caducidad
ansible-playbook -i inventario/hosts.ini 02_cambiar_contrasena.yml \\
  -e objetivo=PPU_GEOPOS -e contrasena_usuarios=root -e contrasena_nunca_caduca=SI \\
  -e @secretos.yml --ask-vault-pass</pre>''')
    a('<p><code>secretos.yml</code> se crea con <code>ansible-vault create secretos.yml</code> y define <code>crear_contrasena_inicial</code>, <code>contrasena_nueva</code> y <code>contrasena_confirmacion</code>. Los reportes de la auditoría quedan en <code>reportes/</code>.</p>')

    # ======================= Anexos =======================
    a(h1('aA'))
    a('<p>Generado desde <code>awx/generar_encuestas.py</code>, la misma fuente de los archivos JSON. La columna «Variable» debe escribirse exactamente igual en AWX.</p>')
    a(''.join(anexo_a))
    a(h1('aB'))
    a('<p>Calculado desde <code>inventario/hosts.ini</code>. El nombre del grupo es lo que se escribe en «Servidores o grupo del inventario». El inventario no tiene IP duplicadas ni nombres repetidos.</p>')
    a(anexo_b)
    a(h1('aC'))
    a(tabla(['Antes', 'Ahora'], [
        ['Contraseñas <code>Soporte2025$</code> / <code>Soporte2026$</code> en texto plano', 'Campo cifrado de la encuesta'],
        ['Llaves en <code>con_LLave/keys/</code>, solo para ese proyecto', 'Las mismas llaves en <code>keys/</code>, usadas por la opción 1 en cualquier servidor'],
        ['Servidores fijos en cada playbook (<code>ktuno-nuevo</code>, <code>AZURE</code>, <code>PPU_GEOPOS</code>…)', 'Campo «Servidores o grupo» en la encuesta'],
        ['Dos proyectos separados (con contraseña / con llave)', 'Una sola opción 1 con «Método de acceso»'],
        ['Dos inventarios distintos, con 40 servidores con IP en conflicto', 'Un solo <code>inventario/hosts.ini</code> (INVENTARIO 2026), sin conflictos'],
        ['<code>chage -d 0</code> a todos los usuarios de la zona en cada ejecución', 'Solo a cuentas recién creadas'],
        ['<code>exclusive: true</code> en las llaves (borraba otras llaves del usuario)', 'Configurable; por defecto no borra'],
        ['Se generaba una llave nueva en cada ejecución (o se perdía en AWX)', 'Se reutiliza la llave existente; solo se genera si falta o si se marca «Renovar llave», y se publica en Git'],
        ['Eliminar sin respaldo ni protección', 'Bloqueo reversible o eliminación con respaldo, confirmación y cuentas protegidas'],
        ['<code>desbloquear_user_pos.yml</code> solo para <code>pos</code>', 'Opción 2 con cualquier usuario'],
        ['Sin auditoría', 'Opción 3 con reporte HTML/CSV, niveles de sudo y hallazgos']]))

    return '<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Manual - Gestión de usuarios Linux con AWX</title><style>%s%s</style></head><body>%s</body></html>' % (
        fuentes_ttf(), CSS.replace('__VERSION__', VERSION), '\n'.join(H))


def fuentes_ttf():
    """Si existe docs/fuente/fuentes/ con Inter en TrueType, se usa en lugar de la Inter OTF del
    sistema: Chromium incrusta las OTF (CFF) como Type 3, que algunos visores muestran borrosas."""
    carpeta = os.path.join(AQUI, 'fuentes')
    reglas = []
    for familia, archivo, peso, estilo in [('Inter', 'Inter-Regular', 400, 'normal'), ('Inter', 'Inter-Italic', 400, 'italic'),
                                           ('Inter', 'Inter-Medium', 500, 'normal'), ('Inter', 'Inter-SemiBold', 600, 'normal'),
                                           ('Inter', 'Inter-Bold', 700, 'normal'), ('Inter Display', 'InterDisplay-Bold', 700, 'normal')]:
        ruta = os.path.join(carpeta, archivo + '.ttf')
        if os.path.isfile(ruta):
            reglas.append("@font-face{font-family:'%s';src:url('file://%s') format('truetype');font-weight:%d;font-style:%s}"
                          % (familia, ruta, peso, estilo))
    return '\n'.join(reglas)


def paginas_de_anclas(pdf):
    """Busca en qué página quedó cada título para llenar el índice."""
    import logging
    import pdfplumber
    logging.getLogger('pdfminer').setLevel(logging.ERROR)
    titulos = {}
    caps = ['c1', 'c2', 'c3', 'c4', 'c5', 'c6', 'c7', 'c8', 'c9', 'c10', 'aA', 'aB', 'aC']
    textos = {
        'c1': 'Qué hace el proyecto', 'c2': 'Cómo funciona una ejecución', 'c3': 'Antes de empezar',
        'c4': 'Estructura del proyecto', 'c5': 'Configurar AWX paso a paso', 'c5p1': 'Paso 1 · Subir el proyecto a Git',
        'c5p2': 'Paso 2 · Credenciales', 'c5p3': 'Paso 3 · Proyecto', 'c5p4': 'Paso 4 · Inventario',
        'c5p5': 'Paso 5 · Plantillas de trabajo', 'c5p6': 'Paso 6 · Encuestas', 'c5p7': 'Paso 7 · Permisos',
        'c6': 'Uso diario: cómo diligenciar cada opción', 'c61': 'Opción 1 · Crear usuarios', 'c62': 'Opción 2 · Cambiar contraseña',
        'c63': 'Opción 3 · Auditoría', 'c64': 'Opción 4 · Bloquear o eliminar', 'c7': 'Cómo leer la auditoría',
        'c8': 'Seguridad y buenas prácticas', 'c9': 'Solución de problemas', 'c10': 'Uso por línea de comandos',
        'aA': 'Todas las preguntas de las encuestas', 'aB': 'Grupos del inventario', 'aC': 'Cambios frente a los proyectos anteriores'}
    with pdfplumber.open(pdf) as doc:
        paginas = [(p.extract_text() or '') for p in doc.pages]
    for ancla, texto in textos.items():
        for i, t in enumerate(paginas[2:], 3):   # se salta portada e índice
            lineas = [l.strip() for l in t.splitlines()]
            if any(l.endswith(texto) and len(l) <= len(texto) + 4 for l in lineas):
                titulos[ancla] = i
                break
    return titulos


def main():
    with open(SALIDA_HTML, 'w', encoding='utf-8') as f:
        f.write(construir())
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print('playwright no está instalado: se generó solo %s (imprímalo a PDF desde Chrome).' % SALIDA_HTML)
        return
    with sync_playwright() as p:
        nav = p.chromium.launch()
        pag = nav.new_page()
        for vuelta in (1, 2):   # 1: maqueta; 2: índice con números de página
            pag.goto('file://' + SALIDA_HTML)
            pag.wait_for_load_state('networkidle')
            pag.evaluate('document.fonts.ready')
            pag.pdf(path=SALIDA_PDF, prefer_css_page_size=True, print_background=True, outline=True, tagged=True)
            if vuelta == 1:
                try:
                    with open(SALIDA_HTML, 'w', encoding='utf-8') as f:
                        f.write(construir(paginas_de_anclas(SALIDA_PDF)))
                except ImportError:
                    break
        nav.close()
    print('PDF generado:', SALIDA_PDF)


if __name__ == '__main__':
    main()
