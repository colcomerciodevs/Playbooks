# Proyecto Ansible - Creación de Usuarios con Llave SSH

## Descripción

Este proyecto permite crear usuarios de sistema operativo de forma automatizada mediante Ansible, configurando acceso por llave SSH y aplicando permisos básicos de seguridad sobre el directorio home, `.ssh` y `authorized_keys`.

El proyecto está diseñado para ser reutilizable. No está ligado a un usuario específico como `seti_monitor`; cualquier usuario futuro puede ser agregado modificando únicamente el archivo de variables correspondiente.

El caso inicial contempla la creación del usuario `seti_monitor`, requerido para tareas de observabilidad y monitoreo, con acceso de solo lectura a nivel de sistema operativo y sin privilegios administrativos.

---

## Alcance funcional

Este proyecto realiza las siguientes acciones:

- Crea grupos de sistema operativo.
- Crea usuarios en servidores Linux.
- Crea usuarios en servidores Solaris 11.
- Genera llaves SSH automáticamente en el nodo Ansible o AWX.
- Instala la llave pública en el archivo `authorized_keys` del usuario.
- Bloquea el acceso por contraseña.
- Aplica permisos seguros sobre:
  - Directorio home.
  - Directorio `.ssh`.
  - Archivo `authorized_keys`.
- Configura privilegios sudo por usuario (opcional, ver más abajo).
- Permite ejecutar sobre grupos específicos del inventario, por ejemplo:
  - Oracle.
  - MySQL.
  - Linux.
  - Solaris 11.

---

## Estructura del proyecto

```text
Nube/
├── ansible.cfg
├── collections.yml
├── inventory.ini
├── crear_usuarios.yml          # Playbook principal: crea usuarios
├── eliminar_usuarios.yml       # Playbook: elimina usuarios
├── README.md
├── keys/                       # Llaves SSH generadas
├── tasks/
│   ├── task_crear_usuarios.yml
│   ├── task_generar_llaves_ssh.yml
│   ├── task_instalar_llaves_ssh.yml
│   ├── task_aplicar_permisos.yml
│   ├── task_aplicar_sudo.yml   # Configura sudo por usuario
│   └── task_eliminar_usuarios.yml
├── templates/
│   └── sudoers_usuario.j2      # Plantilla del archivo /etc/sudoers.d/<usuario>
└── vars/
    ├── vars_usuarios.yml        # Definición de usuarios
    ├── vars_llaves_ssh.yml      # Configuración de llaves
    └── vars_politica_acceso.yml # Permisos y política de sudo
```

---

## Definición de usuarios

Los usuarios se definen en `vars/vars_usuarios.yml`. Campos disponibles:

| Campo            | Obligatorio | Por defecto              | Descripción                                              |
|------------------|-------------|--------------------------|----------------------------------------------------------|
| `username`       | Sí          | -                        | Nombre del usuario.                                      |
| `group`          | No          | `username`               | Grupo primario. Si se omite, se crea uno con su nombre.  |
| `comment`        | No          | `username`               | Comentario / nombre completo (GECOS).                    |
| `uid`            | No          | (automático)             | UID específico.                                          |
| `shell_linux`    | No          | `/bin/bash`              | Shell en servidores Linux.                               |
| `shell_solaris`  | No          | `/usr/bin/sh`            | Shell en servidores Solaris 11.                          |
| `home`           | No          | `/home/<username>`       | Directorio home.                                         |
| `create_home`    | No          | `true`                   | Crear el home.                                           |
| `state`          | No          | `present`                | `present` o `absent`.                                    |
| `generar_llave`  | No          | `true`                   | Generar e instalar llave SSH.                            |
| `sudo`           | No          | `false`                  | Si el usuario tiene privilegios sudo.                    |
| `sudo_nopasswd`  | No          | `false`                  | Si sudo se concede sin pedir contraseña.                 |
| `sudo_commands`  | No          | (según política)         | Lista de comandos específicos permitidos vía sudo.       |

### Grupo igual al usuario

Para que el grupo sea propio del usuario, basta con **omitir** el campo `group`.
El rol usa `item.group | default(item.username)`, por lo que creará un grupo con
el mismo nombre del usuario.

---

## Configuración de sudo

El privilegio sudo se gestiona por usuario y de forma idempotente. La tarea
`task_aplicar_sudo.yml` escribe un archivo en `/etc/sudoers.d/<usuario>` y lo
**valida con `visudo -cf`** antes de aplicarlo, evitando dejar el servidor con
un sudoers inválido. Si un usuario tiene `sudo: false` o `state: absent`, su
archivo en `/etc/sudoers.d/` se elimina.

### Precedencia de comandos

Cuando un usuario tiene `sudo: true`, los comandos concedidos se deciden así:

1. Si define `sudo_commands`, se usan esos comandos.
2. Si no, y `permisos.sudo_readonly` es `true`, se usan `permisos.readonly_commands`.
3. Si no, se concede `ALL`.

### Política global (`vars/vars_politica_acceso.yml`)

```yaml
permisos:
  sudo_readonly: false          # true = sudo limitado a readonly_commands por defecto
  readonly_commands:            # comandos permitidos cuando sudo_readonly es true
    - /usr/bin/cat
    - /usr/bin/journalctl
  home_mode: "0750"
  ssh_dir_mode: "0700"
  authorized_keys_mode: "0600"
```

### Ejemplos

```yaml
# Sudo completo, sin contraseña (recomendado si password está bloqueado)
- username: oalvarez
  sudo: true
  sudo_nopasswd: true

# Sin sudo (comportamiento por defecto)
- username: dgonzalez
  sudo: false

# Sudo limitado a comandos específicos
- username: jmonitor
  sudo: true
  sudo_nopasswd: true
  sudo_commands:
    - /usr/bin/systemctl status *
    - /usr/bin/journalctl
```

> **Importante:** Si los usuarios tienen la contraseña bloqueada (`password_lock`),
> conceder sudo **sin** `sudo_nopasswd: true` hará que sudo pida una contraseña
> inexistente y el usuario no podrá ejecutar nada. Para esos casos use
> `sudo_nopasswd: true`.

---

## Ejecución

```bash
# Crear usuarios
ansible-playbook crear_usuarios.yml

# Modo verificación (sin aplicar cambios) - recomendado primero
ansible-playbook crear_usuarios.yml --check --diff

# Eliminar usuarios
ansible-playbook eliminar_usuarios.yml
```

---

## Consideraciones de seguridad

Por defecto, el usuario creado queda con las siguientes características:

```text
Acceso por SSH: Sí
Acceso por contraseña: No
Sudo: No (configurable por usuario)
Privilegios administrativos: No
Uso esperado: Consulta de métricas y monitoreo
```

- En **Solaris 11**, verifique que `/etc/sudoers` incluya la línea
  `#includedir /etc/sudoers.d` y que `visudo` esté en `/usr/bin/`. Si no,
  ajuste el `validate` de las tareas SunOS en `task_aplicar_sudo.yml`.
- Conceda `NOPASSWD: ALL` únicamente a quien realmente lo requiera; para
  perfiles de monitoreo prefiera `sudo_commands` acotados.
