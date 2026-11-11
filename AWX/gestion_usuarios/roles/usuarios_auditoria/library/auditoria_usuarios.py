#!/usr/bin/python
# -*- coding: utf-8 -*-
# Módulo del proyecto gestion_usuarios: auditoría local de cuentas y privilegios sudo.
# Compatible con Python 2.7 y 3.x (RHEL 7, SLES 12/15, Oracle Linux, Ubuntu, Solaris 11).

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: auditoria_usuarios
short_description: Audita cuentas locales (UID >= uid_minimo) y sus privilegios sudo.
description:
  - Lee /etc/passwd, /etc/shadow y /etc/group del servidor.
  - Obtiene los privilegios efectivos de sudo de cada cuenta con C(sudo -ll -U usuario),
    lo que incluye reglas por usuario, por grupo (%grupo), alias, includedir y LDAP/SSSD.
  - Clasifica el sudo en NINGUNO, LIMITADO o COMPLETO, lista los comandos permitidos,
    indica si se ejecutan sin contraseña (NOPASSWD) y marca comandos que permiten
    escalar a root (shells, editores, paginadores, intérpretes; ver GTFOBins).
  - Revisa estado y caducidad de la contraseña, llaves SSH autorizadas, último acceso,
    grupos privilegiados (docker, lxd, disk...) y cuentas con UID 0 distintas de root.
  - No modifica nada en el servidor. Requiere become (root).
options:
  uid_minimo: {type: int, default: 1000}
  uid_maximo: {type: int, default: 0, description: 0 = sin límite superior}
  excluir_usuarios: {type: list, elements: str, default: [nobody, nfsnobody]}
  dias_inactividad: {type: int, default: 90}
  cuentas_criticas: {type: list, elements: str, default: []}
  cuentas_servicio: {type: list, elements: str, default: []}
  uid_minimo_masivo: {type: int, default: 1000, description: UID desde el que aplica el forzado en bloque de la opción 2}
'''

RETURN = r'''
servidor: {description: Datos del servidor (SO, sudo, sshd, root, cuentas UID 0), type: dict}
usuarios: {description: Una entrada por cuenta auditada, type: list}
resumen: {description: Conteos para el reporte, type: dict}
hallazgos_servidor: {description: Hallazgos que no dependen de una cuenta, type: list}
reporte_texto: {description: Tabla legible para la salida del job, type: list}
'''

import base64
import datetime
import fnmatch
import hashlib
import io
import os
import re
import time

from ansible.module_utils.basic import AnsibleModule

ENV_C = {'LC_ALL': 'C', 'LANG': 'C'}

SHELLS_NO_INTERACTIVOS = set([
    '/sbin/nologin', '/usr/sbin/nologin', '/bin/false', '/usr/bin/false',
    '/sbin/shutdown', '/sbin/halt', '/bin/sync', '/usr/bin/nologin', '',
])

# Comandos que, permitidos por sudo, equivalen en la práctica a root o permiten
# escapar a una shell (referencia: https://gtfobins.github.io).
COMANDOS_ESCALAMIENTO = set([
    # shells y cambio de identidad
    'sh', 'bash', 'dash', 'zsh', 'ksh', 'csh', 'tcsh', 'fish', 'ash', 'busybox',
    'su', 'sudo', 'pkexec', 'runuser', 'chroot', 'nsenter', 'unshare',
    # gestión de cuentas y permisos
    'passwd', 'chpasswd', 'usermod', 'useradd', 'visudo', 'chmod', 'chown', 'chattr',
    'setfacl', 'crontab', 'at', 'mount', 'umount',
    # escritura arbitraria de archivos
    'cp', 'mv', 'dd', 'tee', 'install', 'ln', 'rsync', 'tar', 'zip', 'unzip', 'cpio',
    'sed', 'truncate', 'wget', 'curl', 'scp', 'sftp',
    # editores y paginadores (permiten !sh)
    'vi', 'vim', 'view', 'vimdiff', 'rvim', 'nano', 'pico', 'ed', 'emacs', 'joe',
    'less', 'more', 'most', 'pg', 'man',
    'journalctl', 'systemctl',
    # intérpretes y ejecutores
    'awk', 'gawk', 'mawk', 'nawk', 'perl', 'python', 'python2', 'python3', 'ruby',
    'lua', 'php', 'node', 'tclsh', 'expect', 'env', 'xargs', 'find', 'nice',
    'timeout', 'stdbuf', 'taskset', 'ionice', 'flock', 'watch', 'script', 'screen',
    'tmux', 'gdb', 'strace', 'ltrace', 'make', 'git', 'ssh', 'ftp', 'nmap', 'socat',
    'nc', 'ncat', 'openssl',
    # gestores de paquetes y contenedores
    'apt', 'apt-get', 'dpkg', 'yum', 'dnf', 'zypper', 'rpm', 'pip', 'pip3',
    'docker', 'podman', 'kubectl', 'ctr', 'crictl',
])

GRUPOS_EQUIVALENTES_ROOT = set(['docker', 'lxd', 'lxc', 'disk', 'podman'])
GRUPOS_SENSIBLES = set(['shadow', 'root', 'kmem', 'adm', 'systemd-journal', 'wheel', 'sudo', 'admin'])

SEVERIDADES = ['CRITICO', 'ALTO', 'MEDIO', 'BAJO', 'INFO']
# Días de anticipación para avisar que una contraseña va a vencer.
DIAS_AVISO_VENCIMIENTO = 14
MESES = {'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
         'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12}


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def leer_lineas(ruta):
    try:
        with io.open(ruta, 'r', encoding='utf-8', errors='replace') as f:
            return f.read().splitlines()
    except (IOError, OSError):
        return []


def hoy_dias():
    return int(time.time() // 86400)


def dias_a_fecha(dias):
    try:
        return (datetime.date(1970, 1, 1) + datetime.timedelta(days=int(dias))).isoformat()
    except (ValueError, OverflowError, TypeError):
        return ''


def entero(valor, defecto=None):
    try:
        return int(valor)
    except (ValueError, TypeError):
        return defecto


def hallazgo(lista, severidad, codigo, detalle):
    lista.append({'severidad': severidad, 'codigo': codigo, 'detalle': detalle})


# ---------------------------------------------------------------------------
# Archivos de cuentas
# ---------------------------------------------------------------------------
def leer_passwd():
    cuentas = []
    for linea in leer_lineas('/etc/passwd'):
        if not linea or linea[0] in '#+-':
            continue
        p = linea.split(':')
        if len(p) < 7:
            continue
        cuentas.append({'usuario': p[0], 'uid': entero(p[2], -1), 'gid': entero(p[3], -1),
                        'gecos': p[4], 'home': p[5], 'shell': p[6]})
    return cuentas


def leer_shadow():
    datos = {}
    for linea in leer_lineas('/etc/shadow'):
        if not linea or linea[0] in '#+-':
            continue
        p = linea.split(':')
        if len(p) < 2:
            continue
        p += [''] * (9 - len(p))
        datos[p[0]] = p
    return datos


def leer_grupos():
    por_gid, miembros = {}, {}
    for linea in leer_lineas('/etc/group'):
        if not linea or linea[0] in '#+-':
            continue
        p = linea.split(':')
        if len(p) < 4:
            continue
        gid = entero(p[2], -1)
        por_gid[gid] = p[0]
        for m in [x.strip() for x in p[3].split(',') if x.strip()]:
            miembros.setdefault(m, []).append(p[0])
    return por_gid, miembros


def estado_contrasena(hash_):
    """Devuelve (estado, algoritmo)."""
    if hash_ is None:
        return 'SIN_SHADOW', ''
    # VACIA      -> campo vacío: se entra SIN contraseña (crítico)
    # SIN_CLAVE  -> nunca se asignó clave ('!', '!!', '*', 'NP', 'UP'): solo acceso por llave
    # BLOQUEADA  -> tiene clave pero bloqueada ('!$6$...', '*LK*$5$...', '*LK*')
    # ACTIVA     -> clave utilizable
    if hash_ == '':
        return 'VACIA', ''
    h = hash_
    if h.startswith('*LK*'):
        return 'BLOQUEADA', ''
    bloqueada = h.startswith('!')
    h = h.lstrip('!')
    if h in ('', '*', 'x', 'NP', 'UP') or h.startswith('*'):
        return 'SIN_CLAVE', ''
    algoritmos = [('$y$', 'yescrypt'), ('$gy$', 'gost-yescrypt'), ('$7$', 'scrypt'),
                  ('$6$', 'sha512'), ('$5$', 'sha256'), ('$2', 'bcrypt'),
                  ('$md5', 'md5-sun'), ('$1$', 'md5'), ('$sha1$', 'sha1')]
    algoritmo = 'des' if len(h) == 13 else 'desconocido'
    for prefijo, nombre in algoritmos:
        if h.startswith(prefijo):
            algoritmo = nombre
            break
    return ('BLOQUEADA' if bloqueada else 'ACTIVA'), algoritmo


def caducidad(sh, hoy):
    """Interpreta los campos de /etc/shadow."""
    r = {'ultimo_cambio': '', 'dias_desde_cambio': None, 'max_dias': None,
         'contrasena_caduca': 'nunca', 'contrasena_expirada': False, 'dias_para_vencer': None,
         'debe_cambiar': False, 'cuenta_expira': 'nunca', 'cuenta_expirada': False}
    if not sh:
        return r
    ult, maxd, inact, exp = entero(sh[2]), entero(sh[4]), entero(sh[6]), entero(sh[7])
    if ult == 0:
        r['debe_cambiar'] = True
        r['ultimo_cambio'] = 'forzado (0)'
    elif ult is not None:
        r['ultimo_cambio'] = dias_a_fecha(ult)
        r['dias_desde_cambio'] = hoy - ult
    r['max_dias'] = maxd
    if ult and maxd is not None and 0 <= maxd < 99999:
        vence = ult + maxd
        r['contrasena_caduca'] = dias_a_fecha(vence)
        r['contrasena_expirada'] = hoy > vence
        r['dias_para_vencer'] = vence - hoy
        if inact is not None and inact >= 0 and hoy > vence + inact:
            r['cuenta_expirada'] = True
    if exp is not None and exp >= 0:
        r['cuenta_expira'] = dias_a_fecha(exp)
        if hoy >= exp:
            r['cuenta_expirada'] = True
    return r


# ---------------------------------------------------------------------------
# sudo
# ---------------------------------------------------------------------------
def clave_root(usuario):
    """True si su sudo completo solo funciona con la contraseña de root (targetpw/rootpw)."""
    s = usuario['sudo']
    return not s['nopasswd'] and s['requiere_clave'].startswith('root')


def separar_comandos(texto):
    """Separa una lista de comandos sudoers respetando comas escapadas (\\,)."""
    partes, actual, escape = [], '', False
    for ch in texto:
        if escape:
            actual += ch
            escape = False
        elif ch == '\\':
            actual += ch
            escape = True
        elif ch == ',':
            partes.append(actual.strip())
            actual = ''
        else:
            actual += ch
    if actual.strip():
        partes.append(actual.strip())
    return partes


def parsear_sudo(salida):
    """Interpreta 'sudo -ll -U' (formato largo) y, si no aplica, 'sudo -l -U' (corto)."""
    res = {'permitido': False, 'defaults': [], 'reglas': []}
    estado, regla, en_cmds = None, None, False
    lineas_cortas = []
    for cruda in salida.splitlines():
        s = cruda.strip()
        if s.startswith('Matching Defaults entries for'):
            estado = 'defaults'
            continue
        if s.startswith('Runas and Command-specific defaults for'):
            estado = 'cmddefaults'
            continue
        if re.match(r'^User \S+ may run the following commands', s):
            estado, res['permitido'] = 'reglas', True
            continue
        if re.match(r'^User \S+ is not allowed to run sudo', s):
            return res
        if estado == 'defaults':
            if s:
                res['defaults'].extend([x.strip() for x in s.split(',') if x.strip()])
            continue
        if estado != 'reglas' or not s:
            continue
        if s.startswith('Sudoers entry') or s.startswith('LDAP Role'):
            origen = s.split(':', 1)[1].strip() if ':' in s else ''
            if s.startswith('LDAP Role'):
                origen = 'LDAP: ' + origen
            regla = {'origen': origen, 'runas': 'root', 'runas_grupos': '', 'opciones': [], 'comandos': []}
            res['reglas'].append(regla)
            en_cmds = False
        elif regla is not None and s.startswith('RunAsUsers:'):
            regla['runas'] = s.split(':', 1)[1].strip()
        elif regla is not None and s.startswith('RunAsGroups:'):
            regla['runas_grupos'] = s.split(':', 1)[1].strip()
        elif regla is not None and s.startswith('Options:'):
            regla['opciones'] = [x.strip() for x in s.split(':', 1)[1].split(',') if x.strip()]
        elif regla is not None and s.startswith('Commands:'):
            en_cmds = True
        elif regla is not None and en_cmds:
            regla['comandos'].append(s)
        elif s.startswith('('):
            lineas_cortas.append(s)

    # Formato corto:  (runas) TAG: cmd1, cmd2, TAG: cmd3
    for s in lineas_cortas:
        m = re.match(r'^\(([^)]*)\)\s*(.*)$', s)
        if not m:
            continue
        runas = m.group(1)
        # Las etiquetas se heredan entre comandos de la misma línea hasta que otra
        # de la misma familia las reemplaza (PASSWD/NOPASSWD, EXEC/NOEXEC).
        tags = {}
        for cmd in separar_comandos(m.group(2)):
            tm = re.match(r'^((?:[A-Z_]+:\s*)+)(.*)$', cmd)
            if tm:
                for t in [x.strip() for x in tm.group(1).split(':') if x.strip()]:
                    familia = t[2:] if t.startswith('NO') else t
                    tags[familia] = t
                cmd = tm.group(2).strip()
            opciones = []
            if tags.get('PASSWD') == 'NOPASSWD':
                opciones.append('!authenticate')
            elif tags.get('PASSWD') == 'PASSWD':
                opciones.append('authenticate')
            if tags.get('EXEC') == 'NOEXEC':
                opciones.append('noexec')
            res['reglas'].append({'origen': '', 'runas': runas.split(':')[0].strip(),
                                  'runas_grupos': runas.split(':')[1].strip() if ':' in runas else '',
                                  'opciones': opciones, 'comandos': [cmd]})
    return res


SUBCOMANDOS_SYSTEMCTL_RIESGO = set(['status', 'show', 'cat', 'edit', 'help', 'list-units', 'list-unit-files',
                                    'list-timers', 'list-sockets', 'list-dependencies', 'list-jobs', 'link', 'enable'])


def comando_riesgoso(cmd, noexec):
    """Indica si un comando permitido por sudo permite obtener una shell root."""
    nombre = nombre_comando(cmd)
    if nombre not in COMANDOS_ESCALAMIENTO:
        return False
    if nombre == 'systemctl':
        # systemctl abre un paginador (less) o un editor en estos subcomandos.
        args = cmd.split()[1:]
        if not args or '*' in cmd or args[0] in SUBCOMANDOS_SYSTEMCTL_RIESGO or args[0].startswith('list-'):
            return not noexec
        return False
    if noexec and nombre not in ('sh', 'bash', 'dash', 'zsh', 'ksh', 'su', 'sudo', 'chmod', 'chown', 'cp', 'mv',
                                 'dd', 'tee', 'install', 'ln', 'passwd', 'chpasswd', 'usermod', 'useradd'):
        return False
    return True


def nombre_comando(cmd):
    c = cmd.lstrip('!').strip()
    c = re.sub(r'^(sha(224|256|384|512)|digest):\S+\s+', '', c)
    primero = c.split()[0] if c.split() else c
    return os.path.basename(primero)


def clasificar_sudo(datos):
    defaults = datos['defaults']
    auth_global = '!authenticate' not in defaults
    clave_destino = [d for d in ('targetpw', 'rootpw', 'runaspw') if d in defaults]
    r = {'nivel': 'NINGUNO', 'nopasswd': False, 'requiere_clave': '', 'comandos': [],
         'comandos_riesgo': [], 'comodines': False, 'reglas': [], 'origenes': []}
    if not datos['permitido']:
        return r
    completo = False
    for regla in datos['reglas']:
        ops = regla['opciones']
        sin_clave = ('!authenticate' in ops) or (not auth_global and 'authenticate' not in ops)
        noexec = 'noexec' in ops
        if sin_clave:
            r['nopasswd'] = True
        if regla['origen'] and regla['origen'] not in r['origenes']:
            r['origenes'].append(regla['origen'])
        r['reglas'].append({'origen': regla['origen'], 'runas': regla['runas'],
                            'sin_clave': sin_clave, 'noexec': noexec, 'comandos': regla['comandos']})
        for cmd in regla['comandos']:
            if cmd not in r['comandos']:
                r['comandos'].append(cmd)
            if cmd.startswith('!'):
                continue
            if cmd.strip() == 'ALL':
                completo = True
                continue
            if '*' in cmd or '?' in cmd:
                r['comodines'] = True
            if comando_riesgoso(cmd, noexec):
                if cmd not in r['comandos_riesgo']:
                    r['comandos_riesgo'].append(cmd)
    if completo:
        r['nivel'] = 'COMPLETO'
    elif r['comandos']:
        r['nivel'] = 'LIMITADO'
    if clave_destino and not r['nopasswd']:
        r['requiere_clave'] = 'root (' + ', '.join(clave_destino) + ')'
    elif not r['nopasswd']:
        r['requiere_clave'] = 'propia'
    return r


def fuentes_sudoers(usuario, grupos):
    """Líneas de sudoers locales que mencionan al usuario o a sus grupos (referencia rápida)."""
    archivos = ['/etc/sudoers']
    for d in ('/etc/sudoers.d',):
        try:
            for f in sorted(os.listdir(d)):
                if '.' in f or f.endswith('~'):
                    continue
                archivos.append(os.path.join(d, f))
        except OSError:
            pass
    patron_grupos = ['%' + g for g in grupos]
    encontrados = []
    for archivo in archivos:
        acumulada = ''
        for n, linea in enumerate(leer_lineas(archivo), 1):
            if linea.rstrip().endswith('\\'):
                acumulada += linea.rstrip()[:-1] + ' '
                continue
            completa = (acumulada + linea).strip()
            acumulada = ''
            if not completa or completa.startswith('#') or completa.startswith('Defaults'):
                continue
            tokens = re.split(r'[\s,=]+', completa)
            if (tokens and tokens[0] == usuario) or (tokens and tokens[0] in patron_grupos) or \
               (completa.startswith('User_Alias') and re.search(r'(^|[\s,=])' + re.escape(usuario) + r'($|[\s,])', completa)):
                encontrados.append('%s:%d: %s' % (archivo, n, completa[:200]))
    return encontrados


# ---------------------------------------------------------------------------
# SSH
# ---------------------------------------------------------------------------
def config_sshd(module):
    cfg = {}
    sshd = module.get_bin_path('sshd', opt_dirs=['/usr/sbin', '/usr/lib/ssh', '/usr/local/sbin'])
    if not sshd:
        return cfg
    rc, out, err = module.run_command([sshd, '-T'], environ_update=ENV_C)
    if rc != 0:
        rc, out, err = module.run_command([sshd, '-T', '-C', 'user=root,host=localhost,addr=127.0.0.1'],
                                          environ_update=ENV_C)
    if rc != 0:
        return cfg
    for linea in out.splitlines():
        partes = linea.strip().split(None, 1)
        if len(partes) == 2:
            clave = partes[0].lower()
            if clave in ('allowusers', 'allowgroups', 'denyusers', 'denygroups'):
                cfg.setdefault(clave, []).extend(partes[1].split())
            elif clave in ('permitrootlogin', 'passwordauthentication', 'pubkeyauthentication',
                           'authorizedkeysfile', 'usepam'):
                cfg[clave] = partes[1].strip()
    return cfg


def ssh_permitido(usuario, grupos, cfg):
    def coincide(patrones, valor):
        return any(fnmatch.fnmatch(valor, p.split('@')[0]) for p in patrones)
    if coincide(cfg.get('denyusers', []), usuario):
        return False, 'DenyUsers'
    if cfg.get('allowusers') and not coincide(cfg['allowusers'], usuario):
        return False, 'no está en AllowUsers'
    if any(coincide(cfg.get('denygroups', []), g) for g in grupos):
        return False, 'DenyGroups'
    if cfg.get('allowgroups') and not any(coincide(cfg['allowgroups'], g) for g in grupos):
        return False, 'ningún grupo en AllowGroups'
    return True, ''


def huella_llave(blob_b64):
    try:
        crudo = base64.b64decode(blob_b64)
        return 'SHA256:' + base64.b64encode(hashlib.sha256(crudo).digest()).decode('ascii').rstrip('=')
    except Exception:
        return ''


def llaves_autorizadas(usuario, home, cfg):
    rutas = (cfg.get('authorizedkeysfile') or '.ssh/authorized_keys .ssh/authorized_keys2').split()
    llaves, revisados = [], []
    tipos = re.compile(r'^(ssh-(rsa|ed25519|dss)|ecdsa-sha2-\S+|sk-\S+)$')
    for r in rutas:
        if r.lower() == 'none':
            continue
        r = r.replace('%%', '%').replace('%h', home).replace('%u', usuario)
        if not r.startswith('/'):
            r = os.path.join(home, r)
        if not os.path.isfile(r) or r in revisados:
            continue
        revisados.append(r)
        for linea in leer_lineas(r):
            linea = linea.strip()
            if not linea or linea.startswith('#'):
                continue
            campos = linea.split()
            for i, c in enumerate(campos):
                if tipos.match(c) and i + 1 < len(campos):
                    llaves.append({'tipo': c, 'huella': huella_llave(campos[i + 1]),
                                   'comentario': ' '.join(campos[i + 2:])[:80],
                                   'con_opciones': i > 0, 'archivo': r})
                    break
    return llaves


# ---------------------------------------------------------------------------
# Último acceso
# ---------------------------------------------------------------------------
def ultimo_acceso(module, usuario, hoy):
    for binario in ('lastlog2', 'lastlog'):
        ruta = module.get_bin_path(binario)
        if not ruta:
            continue
        rc, out, err = module.run_command([ruta, '-u', usuario], environ_update=ENV_C)
        if rc != 0:
            continue
        lineas = [l for l in out.splitlines() if l.strip() and not l.startswith('Username')]
        if not lineas:
            continue
        linea = lineas[-1]
        if 'Never logged in' in linea:
            return 'NUNCA', None
        m = re.search(r'(\w{3})\s+(\w{3})\s+(\d{1,2})\s+(\d{2}):(\d{2}):\d{2}\s+(?:[+-]\d{4}\s+)?(\d{4})', linea)
        if m and m.group(2) in MESES:
            try:
                f = datetime.date(int(m.group(6)), MESES[m.group(2)], int(m.group(3)))
                dias = hoy - (f - datetime.date(1970, 1, 1)).days
                return '%s %s:%s' % (f.isoformat(), m.group(4), m.group(5)), dias
            except ValueError:
                pass
        return linea.strip()[-40:], None
    return 'DESCONOCIDO', None


# ---------------------------------------------------------------------------
# Datos del servidor
# ---------------------------------------------------------------------------
def info_so(module):
    datos = {}
    for linea in leer_lineas('/etc/os-release'):
        if '=' in linea:
            k, v = linea.split('=', 1)
            datos[k] = v.strip().strip('"')
    if datos.get('PRETTY_NAME'):
        return datos['PRETTY_NAME']
    rc, out, err = module.run_command(['uname', '-srv'])
    return out.strip() if rc == 0 else ''


def main():
    module = AnsibleModule(
        argument_spec=dict(
            uid_minimo=dict(type='int', default=1000),
            uid_maximo=dict(type='int', default=0),
            excluir_usuarios=dict(type='list', elements='str', default=['nobody', 'nfsnobody']),
            dias_inactividad=dict(type='int', default=90),
            cuentas_criticas=dict(type='list', elements='str', default=[]),
            cuentas_servicio=dict(type='list', elements='str', default=[]),
            uid_minimo_masivo=dict(type='int', default=1000),
        ),
        supports_check_mode=True,
    )
    p = module.params
    hoy = hoy_dias()

    if os.geteuid() != 0:
        module.fail_json(msg='La auditoría requiere privilegios de root (become: true).')

    cuentas = leer_passwd()
    shadow = leer_shadow()
    grupos_por_gid, miembros = leer_grupos()
    sshd = config_sshd(module)
    sudo_bin = module.get_bin_path('sudo', opt_dirs=['/usr/bin', '/usr/local/bin', '/opt/csw/bin', '/usr/sbin'])
    version_sudo = ''
    if sudo_bin:
        rc, out, err = module.run_command([sudo_bin, '-V'], environ_update=ENV_C)
        version_sudo = out.splitlines()[0].strip() if rc == 0 and out else ''

    defaults_globales = []
    hallazgos_servidor = []
    if not os.path.isfile('/etc/sudoers'):
        pass
    elif not any(re.match(r'^[#@]includedir\s+/etc/sudoers\.d', l.strip()) for l in leer_lineas('/etc/sudoers')):
        hallazgo(hallazgos_servidor, 'INFO', 'SUDOERS_SIN_INCLUDEDIR',
                 '/etc/sudoers no incluye /etc/sudoers.d: las reglas por archivo no aplican.')
    if sshd.get('permitrootlogin', '').lower() == 'yes':
        hallazgo(hallazgos_servidor, 'MEDIO', 'SSH_ROOT_PERMITIDO', 'sshd permite login directo de root con contraseña (PermitRootLogin yes).')

    # --- root y cuentas UID 0 -----------------------------------------------
    cuentas_uid0 = []
    for c in cuentas:
        if c['uid'] == 0:
            sh = shadow.get(c['usuario'])
            est, alg = estado_contrasena(sh[1] if sh else None)
            cad = caducidad(sh, hoy)
            cuentas_uid0.append({'usuario': c['usuario'], 'estado_contrasena': est, 'algoritmo': alg,
                                 'ultimo_cambio': cad['ultimo_cambio'], 'contrasena_caduca': cad['contrasena_caduca'],
                                 'contrasena_expirada': cad['contrasena_expirada'], 'max_dias': cad['max_dias'],
                                 'shell': c['shell']})
            if c['usuario'] != 'root':
                hallazgo(hallazgos_servidor, 'CRITICO', 'UID0_NO_ROOT',
                         'La cuenta "%s" tiene UID 0 (privilegios de root).' % c['usuario'])
    root = next((x for x in cuentas_uid0 if x['usuario'] == 'root'), {})
    if root.get('contrasena_expirada'):
        hallazgo(hallazgos_servidor, 'ALTO', 'ROOT_CLAVE_EXPIRADA',
                 'La contraseña de root está expirada (venció %s).' % root.get('contrasena_caduca'))
    elif root.get('contrasena_caduca', 'nunca') != 'nunca':
        hallazgo(hallazgos_servidor, 'INFO', 'ROOT_CLAVE_CADUCA',
                 'La contraseña de root caduca el %s (use la opción 2 con "nunca caduca" si aplica).' % root.get('contrasena_caduca'))

    # --- cuentas de persona --------------------------------------------------
    usuarios = []
    for c in cuentas:
        if c['uid'] < p['uid_minimo'] or c['usuario'] in p['excluir_usuarios']:
            continue
        if c['uid'] in (65534, 4294967294, 4294967295):
            continue
        if p['uid_maximo'] and c['uid'] > p['uid_maximo']:
            continue
        u = c['usuario']
        h = []
        grupo_primario = grupos_por_gid.get(c['gid'], str(c['gid']))
        secundarios = sorted(set(miembros.get(u, [])) - set([grupo_primario]))
        todos_grupos = [grupo_primario] + secundarios
        sh = shadow.get(u)
        est, alg = estado_contrasena(sh[1] if sh else None)
        cad = caducidad(sh, hoy)
        interactivo = c['shell'] not in SHELLS_NO_INTERACTIVOS
        llaves = llaves_autorizadas(u, c['home'], sshd)
        ssh_ok, ssh_motivo = ssh_permitido(u, todos_grupos, sshd)
        acceso_txt, acceso_dias = ultimo_acceso(module, u, hoy)

        # sudo efectivo
        if sudo_bin:
            rc, out, err = module.run_command([sudo_bin, '-n', '-ll', '-U', u], environ_update=ENV_C)
            datos = parsear_sudo(out)
            if datos['permitido'] and not datos['reglas']:
                rc, out, err = module.run_command([sudo_bin, '-n', '-l', '-U', u], environ_update=ENV_C)
                datos = parsear_sudo(out)
            if not defaults_globales and datos['defaults']:
                defaults_globales = datos['defaults']
            sudo = clasificar_sudo(datos)
            if rc != 0 and not datos['permitido'] and 'not allowed' not in (out + err):
                sudo['error'] = (err or out).strip()[:200]
        else:
            sudo = clasificar_sudo({'permitido': False, 'defaults': [], 'reglas': []})
            sudo['nivel'] = 'SIN_SUDO_INSTALADO'
        if sudo['nivel'] in ('COMPLETO', 'LIMITADO'):
            sudo['fuentes_locales'] = fuentes_sudoers(u, todos_grupos)

        puede_entrar = interactivo and ssh_ok and not cad['cuenta_expirada'] and \
            (est in ('ACTIVA', 'VACIA') or len(llaves) > 0)

        # hallazgos
        if est == 'VACIA':
            hallazgo(h, 'CRITICO', 'CONTRASENA_VACIA', 'La cuenta no tiene contraseña: puede entrar sin clave.')
        if sudo['nivel'] == 'COMPLETO':
            if sudo['nopasswd']:
                hallazgo(h, 'ALTO', 'SUDO_COMPLETO_SIN_CLAVE', 'sudo ALL sin contraseña (NOPASSWD).')
            elif sudo['requiere_clave'].startswith('root'):
                hallazgo(h, 'MEDIO', 'SUDO_COMPLETO_CLAVE_ROOT', 'sudo ALL pero exige la contraseña de root (%s).' % sudo['requiere_clave'])
            else:
                hallazgo(h, 'ALTO', 'SUDO_COMPLETO', 'sudo ALL con su propia contraseña.')
            if any(x.startswith('!') for x in sudo['comandos']):
                hallazgo(h, 'INFO', 'SUDO_NEGACIONES', 'Las negaciones en una regla ALL (%s) se pueden evadir.'
                         % ', '.join(x for x in sudo['comandos'] if x.startswith('!')))
        elif sudo['nivel'] == 'LIMITADO':
            if sudo['comandos_riesgo']:
                hallazgo(h, 'ALTO', 'SUDO_ESCALAMIENTO', 'Comandos que permiten obtener root: ' + ', '.join(sudo['comandos_riesgo']))
            if sudo['comodines']:
                hallazgo(h, 'MEDIO', 'SUDO_COMODINES', 'Reglas con comodines (*) en los argumentos.')
        for g in todos_grupos:
            if g in GRUPOS_EQUIVALENTES_ROOT:
                hallazgo(h, 'ALTO', 'GRUPO_EQUIVALENTE_ROOT', 'Pertenece al grupo "%s" (equivale a root).' % g)
        if alg in ('md5', 'des', 'md5-sun', 'sha1') and est == 'ACTIVA':
            hallazgo(h, 'ALTO', 'HASH_DEBIL', 'Contraseña almacenada con algoritmo débil (%s).' % alg)
        # Con PAM, una contraseña vencida también impide entrar con llave.
        solo_llave = est != 'ACTIVA' and len(llaves) > 0
        if cad['contrasena_expirada'] and not cad['cuenta_expirada'] and (est == 'ACTIVA' or solo_llave):
            if solo_llave:
                hallazgo(h, 'ALTO', 'CONTRASENA_EXPIRADA', 'Contraseña vencida desde %s: la cuenta entra solo con llave '
                         'y ya no puede iniciar sesión.' % cad['contrasena_caduca'])
            else:
                hallazgo(h, 'MEDIO', 'CONTRASENA_EXPIRADA', 'Contraseña vencida desde %s.' % cad['contrasena_caduca'])
        dias_vence = cad['dias_para_vencer']
        if puede_entrar and not cad['contrasena_expirada'] and dias_vence is not None and dias_vence <= DIAS_AVISO_VENCIMIENTO:
            hallazgo(h, 'ALTO', 'CONTRASENA_POR_VENCER', 'La contraseña vence el %s (en %d días).%s' % (
                cad['contrasena_caduca'], dias_vence,
                ' La cuenta entra solo con llave: al vencer perderá el acceso.' if solo_llave else ''))
        if cad['cuenta_expirada']:
            hallazgo(h, 'INFO', 'CUENTA_EXPIRADA', 'Cuenta expirada/deshabilitada (%s).' % cad['cuenta_expira'])
        if puede_entrar and acceso_dias is not None and acceso_dias > p['dias_inactividad']:
            hallazgo(h, 'MEDIO', 'CUENTA_INACTIVA', 'Sin ingresar hace %d días (último: %s).' % (acceso_dias, acceso_txt))
        if puede_entrar and acceso_txt == 'NUNCA':
            hallazgo(h, 'BAJO', 'NUNCA_INGRESO', 'Cuenta habilitada que nunca ha iniciado sesión.')
        if est == 'ACTIVA' and interactivo and cad['contrasena_caduca'] == 'nunca' and not cad['debe_cambiar'] and not cad['cuenta_expirada']:
            hallazgo(h, 'BAJO', 'CONTRASENA_SIN_CADUCIDAD', 'La contraseña no caduca.')
        if any(l['con_opciones'] for l in llaves):
            hallazgo(h, 'INFO', 'LLAVE_CON_OPCIONES', 'Alguna llave SSH tiene opciones (command=, from=...).')

        # Misma regla que el forzado en bloque de la opción 2 (todos UID >= 1000).
        es_servicio = u in p['cuentas_servicio']
        forzaria = (p['uid_minimo_masivo'] <= c['uid'] < 65534 and u not in p['cuentas_criticas'] and not es_servicio
                    and interactivo and est == 'ACTIVA')

        h.sort(key=lambda x: SEVERIDADES.index(x['severidad']))
        usuarios.append({
            'usuario': u, 'uid': c['uid'], 'gid': c['gid'], 'nombre': c['gecos'],
            'home': c['home'], 'shell': c['shell'], 'shell_interactivo': interactivo,
            'grupo_primario': grupo_primario, 'grupos_secundarios': secundarios,
            'estado_contrasena': est, 'algoritmo_hash': alg,
            'ultimo_cambio': cad['ultimo_cambio'], 'dias_desde_cambio': cad['dias_desde_cambio'],
            'max_dias': cad['max_dias'], 'contrasena_caduca': cad['contrasena_caduca'],
            'contrasena_expirada': cad['contrasena_expirada'], 'debe_cambiar': cad['debe_cambiar'],
            'cuenta_expira': cad['cuenta_expira'], 'cuenta_expirada': cad['cuenta_expirada'],
            'llaves_ssh': llaves, 'ssh_permitido': ssh_ok, 'ssh_motivo': ssh_motivo,
            'puede_iniciar_sesion': puede_entrar,
            'ultimo_acceso': acceso_txt, 'dias_sin_acceso': acceso_dias,
            'sudo': sudo, 'hallazgos': h,
            'cuenta_servicio': es_servicio, 'forzaria_cambio': forzaria,
            'severidad_max': h[0]['severidad'] if h else '',
        })

    # --- resumen -------------------------------------------------------------
    todos_h = hallazgos_servidor + [x for u in usuarios for x in u['hallazgos']]
    resumen = {
        'usuarios': len(usuarios),
        # sudo completo con su propia clave o sin clave (privilegio real).
        'sudo_completo': len([u for u in usuarios if u['sudo']['nivel'] == 'COMPLETO' and not clave_root(u)]),
        # sudo completo que exige la clave de root (regla por defecto de SUSE: equivale a conocer root).
        'sudo_clave_root': len([u for u in usuarios if u['sudo']['nivel'] == 'COMPLETO' and clave_root(u)]),
        'sudo_limitado': len([u for u in usuarios if u['sudo']['nivel'] == 'LIMITADO']),
        'sin_sudo': len([u for u in usuarios if u['sudo']['nivel'] not in ('COMPLETO', 'LIMITADO')]),
        'sudo_sin_clave': len([u for u in usuarios if u['sudo']['nopasswd']]),
        'pueden_iniciar_sesion': len([u for u in usuarios if u['puede_iniciar_sesion']]),
        'forzaria_cambio': len([u for u in usuarios if u['forzaria_cambio']]),
        'cuentas_servicio': len([u for u in usuarios if u['cuenta_servicio']]),
        'bloqueadas': len([u for u in usuarios if u['estado_contrasena'] == 'BLOQUEADA']),
        'cuentas_uid0': len(cuentas_uid0),
    }
    for s in SEVERIDADES:
        resumen['hallazgos_' + s.lower()] = len([x for x in todos_h if x['severidad'] == s])

    servidor = {
        'sistema': info_so(module), 'sudo_version': version_sudo,
        'sudo_defaults': defaults_globales,
        'sudo_clave_destino': [d for d in ('targetpw', 'rootpw', 'runaspw') if d in defaults_globales],
        'sshd': sshd, 'root': root, 'cuentas_uid0': cuentas_uid0,
        'fecha_auditoria': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }

    # --- texto para la salida del job ---------------------------------------
    t = []
    t.append('%s | sudo: %s' % (servidor['sistema'], version_sudo or 'no instalado'))
    t.append('root: clave %s, último cambio %s, caduca %s' % (
        root.get('estado_contrasena', '?'), root.get('ultimo_cambio', '?'), root.get('contrasena_caduca', '?')))
    t.append('Usuarios UID >= %d: %d | sudo completo: %d | solo con clave de root: %d | limitado: %d | sin sudo: %d | NOPASSWD: %d' % (
        p['uid_minimo'], resumen['usuarios'], resumen['sudo_completo'], resumen['sudo_clave_root'],
        resumen['sudo_limitado'], resumen['sin_sudo'], resumen['sudo_sin_clave']))
    t.append('-' * 110)
    t.append('%-16s %6s %-9s %-4s %-10s %-11s %-6s %-17s %s' % (
        'USUARIO', 'UID', 'SUDO', 'NOPW', 'CLAVE', 'CADUCA', 'LLAVES', 'ULTIMO ACCESO', 'HALLAZGO'))
    for u in usuarios:
        t.append('%-16s %6d %-9s %-4s %-10s %-11s %-6d %-17s %s' % (
            u['usuario'][:16], u['uid'], u['sudo']['nivel'][:9], 'SI' if u['sudo']['nopasswd'] else '-',
            u['estado_contrasena'][:10], (u['contrasena_caduca'] or '')[:11], len(u['llaves_ssh']),
            (u['ultimo_acceso'] or '')[:17], u['severidad_max'] or '-'))
        if u['sudo']['nivel'] == 'LIMITADO':
            t.append('%18s comandos: %s' % ('', ', '.join(u['sudo']['comandos'])[:300]))
    for x in hallazgos_servidor:
        t.append('[%s] %s' % (x['severidad'], x['detalle']))

    module.exit_json(changed=False, servidor=servidor, usuarios=usuarios, resumen=resumen,
                     hallazgos_servidor=hallazgos_servidor, reporte_texto=t)


if __name__ == '__main__':
    main()
