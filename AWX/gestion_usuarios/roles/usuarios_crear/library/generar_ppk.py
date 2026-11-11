#!/usr/bin/python
# -*- coding: utf-8 -*-
# Módulo del proyecto gestion_usuarios: crea el .ppk (PuTTY v3, sin cifrar) a
# partir de una llave privada RSA en formato OpenSSH. No requiere puttygen.
# Se ejecuta en el controlador; ni la llave ni su contenido viajan en los
# parámetros o en el resultado.

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import base64
import hashlib
import hmac
import os
import struct

from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = r"""
module: generar_ppk
short_description: Crea un .ppk de PuTTY v3 desde una llave privada OpenSSH RSA
options:
  path:
    description: Ruta de la llave privada OpenSSH (RSA, sin frase de paso).
    required: true
    type: path
  dest:
    description: Ruta del .ppk. Si ya existe no se modifica.
    required: true
    type: path
author: gestion_usuarios
"""


def leer(datos, pos):
    largo = struct.unpack('>I', datos[pos:pos + 4])[0]
    return datos[pos + 4:pos + 4 + largo], pos + 4 + largo


def cadena(valor):
    return struct.pack('>I', len(valor)) + valor


def entero(valor):
    valor = valor.lstrip(b'\0')
    if valor and bytearray(valor)[0] & 0x80:
        valor = b'\0' + valor
    return cadena(valor)


def lineas(valor):
    texto = base64.b64encode(valor).decode('ascii')
    return [texto[i:i + 64] for i in range(0, len(texto), 64)]


def construir_ppk(texto):
    cuerpo = ''.join(x for x in texto.splitlines() if '-----' not in x)
    datos = base64.b64decode(cuerpo)
    if not datos.startswith(b'openssh-key-v1\0'):
        raise ValueError('La llave no está en formato OpenSSH.')
    pos = 15
    cifrado, pos = leer(datos, pos)
    _kdf, pos = leer(datos, pos)
    _opciones, pos = leer(datos, pos)
    pos += 4
    _publica, pos = leer(datos, pos)
    privada, pos = leer(datos, pos)
    if cifrado != b'none':
        raise ValueError('La llave tiene frase de paso; no se puede convertir.')

    pos = 8
    tipo, pos = leer(privada, pos)
    if tipo != b'ssh-rsa':
        raise ValueError('Solo se admiten llaves RSA.')
    n, pos = leer(privada, pos)
    e, pos = leer(privada, pos)
    d, pos = leer(privada, pos)
    iqmp, pos = leer(privada, pos)
    p, pos = leer(privada, pos)
    q, pos = leer(privada, pos)
    comentario, pos = leer(privada, pos)

    pub = cadena(b'ssh-rsa') + entero(e) + entero(n)
    pri = entero(d) + entero(p) + entero(q) + entero(iqmp)
    mac = hmac.new(b'', cadena(b'ssh-rsa') + cadena(b'none') + cadena(comentario) + cadena(pub) + cadena(pri),
                   hashlib.sha256).hexdigest()
    salida = ['PuTTY-User-Key-File-3: ssh-rsa', 'Encryption: none', 'Comment: ' + comentario.decode('utf-8'),
              'Public-Lines: %d' % len(lineas(pub))] + lineas(pub)
    salida += ['Private-Lines: %d' % len(lineas(pri))] + lineas(pri) + ['Private-MAC: ' + mac]
    return '\n'.join(salida) + '\n'


def main():
    module = AnsibleModule(argument_spec=dict(path=dict(type='path', required=True),
                                              dest=dict(type='path', required=True)),
                           supports_check_mode=True)
    ruta, destino = module.params['path'], module.params['dest']
    if os.path.exists(destino):
        module.exit_json(changed=False, dest=destino)
    if module.check_mode:
        module.exit_json(changed=True, dest=destino)
    try:
        with open(ruta) as archivo:
            contenido = construir_ppk(archivo.read())
        descriptor = os.open(destino, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, 'w') as archivo:
            archivo.write(contenido)
    except (IOError, OSError, ValueError, struct.error) as error:
        module.fail_json(msg='No se pudo crear %s: %s' % (destino, error))
    module.exit_json(changed=True, dest=destino)


if __name__ == '__main__':
    main()
