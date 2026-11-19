#!/usr/bin/python
# -*- coding: utf-8 -*-
# Genera un libro de Excel (.xlsx) solo con la biblioteca estándar de Python.
# Se ejecuta en el contenedor de AWX (localhost), no en los servidores.
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
module: generar_excel
short_description: Escribe un archivo .xlsx con varias hojas (encabezado fijo, filtros y anchos de columna).
options:
  destino: {type: path, required: true, description: Ruta del archivo .xlsx}
  hojas:
    type: list
    elements: dict
    required: true
    description: >-
      Lista de hojas. Cada una: nombre (máx. 31 caracteres), encabezados (lista) y filas (lista de listas).
      Opcional: anchos (lista de números), filtro (true por defecto), vacia, colores, estilos_fila,
      ajustar y fijar_columnas (ver hoja_xml).
'''

import os
import re
import tempfile
import zipfile
from xml.sax.saxutils import escape

from ansible.module_utils.basic import AnsibleModule

MAX_CELDA = 32767
# Caracteres de control que XML (y Excel) no aceptan.
INVALIDOS = re.compile(u'[\x00-\x08\x0b\x0c\x0e-\x1f]')


def columna(n):
    """0 -> A, 25 -> Z, 26 -> AA."""
    s = ''
    n += 1
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def texto(v):
    if v is None:
        return u''
    if isinstance(v, bool):
        return u'SÍ' if v else u'NO'
    try:
        t = u'%s' % v
    except UnicodeDecodeError:
        t = v.decode('utf-8', 'replace')
    return INVALIDOS.sub(u'', t)[:MAX_CELDA]


def celda(ref, v, estilo=0):
    s = u' s="%d"' % estilo if estilo else u''
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return u'<c r="%s"%s><v>%s</v></c>' % (ref, s, v)
    t = texto(v)
    if t == u'':
        return u'<c r="%s"%s/>' % (ref, s) if estilo else u''
    return u'<c r="%s"%s t="inlineStr"><is><t xml:space="preserve">%s</t></is></c>' % (ref, s, escape(t))


# Índices de cellXfs (ver ESTILOS).
E_NORMAL, E_ENCABEZADO, E_CELDA, E_TITULO, E_SECCION, E_AJUSTADO = 0, 1, 2, 3, 4, 5
COLORES = {'rojo': 6, 'naranja': 7, 'amarillo': 8, 'azul': 9, 'gris': 10, 'verde': 11}
ESTILOS_FILA = {'titulo': E_TITULO, 'seccion': E_SECCION}


def hoja_xml(h):
    """Devuelve (xml de la hoja, rango del filtro o None).
    Opciones de la hoja además de encabezados/filas/anchos/filtro/vacia:
      colores:        {encabezado o n.º de columna: {valor: color}} colorea esas celdas
                      (rojo, naranja, amarillo, azul, gris, verde).
      estilos_fila:   {"<n.º de fila desde 0>": "titulo" | "seccion"} para hojas tipo informe.
      ajustar:        índices de columna (desde 0) con texto ajustado en varias líneas.
      fijar_columnas: columnas fijas a la izquierda (además de la fila de encabezado)."""
    enc = h.get('encabezados') or []
    filas = h.get('filas') or []
    if enc and not filas:
        filas = [[h.get('vacia') or u'Sin datos.']]
    ncol = max([len(enc)] + [len(f) for f in filas]) or 1
    anchos = list(h.get('anchos') or [])
    while len(anchos) < ncol:
        i = len(anchos)
        largo = max([len(texto(enc[i])) if i < len(enc) else 0]
                    + [len(texto(f[i])) for f in filas[:500] if i < len(f)])
        anchos.append(min(max(largo + 2, 8), 60))
    # La columna se indica por su encabezado o por su número (desde 0, como texto en hojas sin encabezado).
    colores = {}
    for clave, valores in (h.get('colores') or {}).items():
        i = enc.index(clave) if clave in enc else (int(clave) if texto(clave).isdigit() else None)
        for valor, color in (valores or {}).items():
            if i is not None and color in COLORES:
                colores[(i, texto(valor))] = COLORES[color]
    estilos_fila = dict((int(k), ESTILOS_FILA.get(v, E_CELDA)) for k, v in (h.get('estilos_fila') or {}).items())
    ajustar = set(int(x) for x in h.get('ajustar') or [])
    fijas = int(h.get('fijar_columnas') or 0)

    partes = [u'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
              u'<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">']
    if enc and fijas:
        celda_sup = u'%s2' % columna(fijas)
        partes.append(u'<sheetViews><sheetView workbookViewId="0"><pane xSplit="%d" ySplit="1" topLeftCell="%s" '
                      u'activePane="bottomRight" state="frozen"/><selection pane="bottomRight" activeCell="%s" sqref="%s"/>'
                      u'</sheetView></sheetViews>' % (fijas, celda_sup, celda_sup, celda_sup))
    elif enc:
        partes.append(u'<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" '
                      u'state="frozen"/></sheetView></sheetViews>')
    else:
        partes.append(u'<sheetViews><sheetView workbookViewId="0" showGridLines="0"/></sheetViews>')
    partes.append(u'<cols>%s</cols>' % u''.join(
        u'<col min="%d" max="%d" width="%s" customWidth="1"/>' % (i + 1, i + 1, a) for i, a in enumerate(anchos)))
    partes.append(u'<sheetData>')
    fila_n = 0
    if enc:
        fila_n = 1
        partes.append(u'<row r="1">%s</row>' % u''.join(celda(columna(i) + u'1', v, E_ENCABEZADO) for i, v in enumerate(enc)))
    for n, f in enumerate(filas):
        fila_n += 1
        base = estilos_fila.get(n)
        celdas = []
        for i, v in enumerate(f):
            estilo = base or colores.get((i, texto(v))) or (E_AJUSTADO if i in ajustar else E_CELDA)
            celdas.append(celda(u'%s%d' % (columna(i), fila_n), v, estilo))
        partes.append(u'<row r="%d">%s</row>' % (fila_n, u''.join(celdas)))
    partes.append(u'</sheetData>')
    filtro = None
    if enc and h.get('filtro', True) and fila_n > 1:
        filtro = (columna(ncol - 1), fila_n)
        partes.append(u'<autoFilter ref="A1:%s%d"/>' % filtro)
    partes.append(u'<pageMargins left="0.5" right="0.5" top="0.6" bottom="0.6" header="0.3" footer="0.3"/>')
    partes.append(u'</worksheet>')
    return u''.join(partes), filtro


def _relleno(rgb):
    return u'<fill><patternFill patternType="solid"><fgColor rgb="FF%s"/><bgColor indexed="64"/></patternFill></fill>' % rgb


# Fuentes: 0 normal, 1 negrita blanca, 2 título, 3 negrita oscura.
# Rellenos: 2 encabezado, 3 sección, 4-9 colores (rojo, naranja, amarillo, azul, gris, verde).
ESTILOS = (u'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           u'<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
           u'<fonts count="4"><font><sz val="10"/><name val="Calibri"/><family val="2"/></font>'
           u'<font><b/><sz val="10"/><color rgb="FFFFFFFF"/><name val="Calibri"/><family val="2"/></font>'
           u'<font><b/><sz val="16"/><color rgb="FF1F3A5F"/><name val="Calibri"/><family val="2"/></font>'
           u'<font><b/><sz val="11"/><color rgb="FF1F3A5F"/><name val="Calibri"/><family val="2"/></font></fonts>'
           u'<fills count="10"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill>'
           + _relleno(u'1F3A5F') + _relleno(u'DCE6F1')
           + _relleno(u'F8CBAD') + _relleno(u'FCE4D6') + _relleno(u'FFF2CC') + _relleno(u'DDEBF7')
           + _relleno(u'EDEDED') + _relleno(u'E2EFDA')
           + u'</fills>'
           u'<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
           u'<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
           u'<cellXfs count="12">'
           u'<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
           u'<xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1" applyAlignment="1">'
           u'<alignment vertical="top" wrapText="1"/></xf>'
           u'<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="top"/></xf>'
           u'<xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0" applyFont="1"/>'
           u'<xf numFmtId="0" fontId="3" fillId="3" borderId="0" xfId="0" applyFont="1" applyFill="1" applyAlignment="1">'
           u'<alignment vertical="top" wrapText="1"/></xf>'
           u'<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>'
           + u''.join(u'<xf numFmtId="0" fontId="0" fillId="%d" borderId="0" xfId="0" applyFill="1" applyAlignment="1">'
                      u'<alignment vertical="top"/></xf>' % f for f in range(4, 10))
           + u'</cellXfs>'
           u'<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
           u'</styleSheet>')


def nombre_hoja(n, usados):
    n = re.sub(r'[\[\]:*?/\\]', '-', texto(n))[:31] or u'Hoja'
    base, i = n, 2
    while n.lower() in usados:
        n = (base[:28] + u'_%d' % i)
        i += 1
    usados.add(n.lower())
    return n


def escribir(destino, hojas):
    usados = set()
    nombres = [nombre_hoja(h.get('nombre'), usados) for h in hojas]
    xmls = [hoja_xml(h) for h in hojas]
    # Excel registra cada filtro como nombre definido _FilterDatabase de su hoja.
    filtros = u''.join(u'<definedName name="_xlnm._FilterDatabase" localSheetId="%d" hidden="1">'
                       u"'%s'!$A$1:$%s$%d</definedName>" % (i, escape(nombres[i].replace(u"'", u"''")), f[0], f[1])
                       for i, (_, f) in enumerate(xmls) if f)
    tipos = (u'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
             u'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
             u'<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
             u'<Default Extension="xml" ContentType="application/xml"/>'
             u'<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
             u'<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
             + u''.join(u'<Override PartName="/xl/worksheets/sheet%d.xml" '
                        u'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' % (i + 1)
                        for i in range(len(hojas)))
             + u'</Types>')
    rels = (u'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            u'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            u'<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
            u'Target="xl/workbook.xml"/></Relationships>')
    libro = (u'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
             u'<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
             u'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
             + u''.join(u'<sheet name="%s" sheetId="%d" r:id="rId%d"/>' % (escape(n, {'"': '&quot;'}), i + 1, i + 1)
                        for i, n in enumerate(nombres))
             + u'</sheets>'
             + (u'<definedNames>%s</definedNames>' % filtros if filtros else u'')
             + u'</workbook>')
    libro_rels = (u'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                  u'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                  + u''.join(u'<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
                             u'Target="worksheets/sheet%d.xml"/>' % (i + 1, i + 1) for i in range(len(hojas)))
                  + u'<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
                    u'Target="styles.xml"/>' % (len(hojas) + 1)
                  + u'</Relationships>')
    carpeta = os.path.dirname(destino) or '.'
    fd, tmp = tempfile.mkstemp(prefix='.excel_', suffix='.xlsx', dir=carpeta)
    os.close(fd)
    try:
        z = zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED)
        try:
            z.writestr('[Content_Types].xml', tipos.encode('utf-8'))
            z.writestr('_rels/.rels', rels.encode('utf-8'))
            z.writestr('xl/workbook.xml', libro.encode('utf-8'))
            z.writestr('xl/_rels/workbook.xml.rels', libro_rels.encode('utf-8'))
            z.writestr('xl/styles.xml', ESTILOS.encode('utf-8'))
            for i, (xml, _) in enumerate(xmls):
                z.writestr('xl/worksheets/sheet%d.xml' % (i + 1), xml.encode('utf-8'))
        finally:
            z.close()
        os.chmod(tmp, 0o640)
        os.rename(tmp, destino)
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
    return nombres


def main():
    module = AnsibleModule(argument_spec=dict(
        destino=dict(type='path', required=True),
        hojas=dict(type='list', elements='dict', required=True),
    ), supports_check_mode=True)
    if module.check_mode:
        module.exit_json(changed=False)
    nombres = escribir(module.params['destino'], module.params['hojas'])
    module.exit_json(changed=True, destino=module.params['destino'], hojas=nombres,
                     filas=[len(h.get('filas') or []) for h in module.params['hojas']])


if __name__ == '__main__':
    main()
